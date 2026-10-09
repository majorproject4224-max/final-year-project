from __future__ import annotations
import json, os, sqlite3
from functools import wraps
from pathlib import Path
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import joblib
import pandas as pd
from backend.platform_api.resume import extract_resume as parse_resume

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "connect.db"
LEVEL = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-before-production")
MODEL = joblib.load(ROOT / "ml/models/random_forest_compatibility.joblib")
FEATURES = MODEL["features"]
METRICS = json.loads((ROOT / "ml/evaluation/random_forest_metrics.json").read_text())
DEMO = pd.read_excel(ROOT / "dataset/students.xlsx").fillna("")

DOMAINS = ["AI / ML", "Data Science", "Web Development", "Mobile Development", "Backend Development", "Cybersecurity"]
def extract_resume(upload):
    suggestions = parse_resume(upload)
    return {
        "name": suggestions["name"],
        "branch": suggestions["branch"],
        "academic_year": suggestions["academic_year"],
        "skills": ", ".join(suggestions["skills"]),
        "interests": ", ".join(suggestions["interests"]),
        "domain": suggestions["domain"],
        "experience": suggestions["experience"],
        "project_type": suggestions["preferred_project_type"],
        "city": suggestions["city"],
        "phone": suggestions["phone"],
        "github": suggestions["github"],
        "share_contact": 0,
    }

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH); g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(error=None):
    connection = g.pop("db", None)
    if connection: connection.close()

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS profiles (
      id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, name TEXT NOT NULL, branch TEXT, academic_year INTEGER,
      skills TEXT, interests TEXT, domain TEXT, experience TEXT, project_type TEXT, city TEXT, is_demo INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS projects (
      id INTEGER PRIMARY KEY, owner_id INTEGER, title TEXT NOT NULL, description TEXT NOT NULL, skills TEXT,
      domain TEXT, project_type TEXT, status TEXT DEFAULT 'Open', FOREIGN KEY(owner_id) REFERENCES users(id));
    """)
    existing = {row["name"] for row in con.execute("PRAGMA table_info(profiles)")}
    for column, definition in [("phone", "TEXT"), ("github", "TEXT"), ("share_contact", "INTEGER DEFAULT 0")]:
        if column not in existing:
            con.execute(f"ALTER TABLE profiles ADD COLUMN {column} {definition}")
    if not con.execute("SELECT 1 FROM profiles WHERE is_demo=1 LIMIT 1").fetchone():
        for row in DEMO.sample(16, random_state=42).itertuples(index=False):
            con.execute("INSERT INTO profiles (name,branch,academic_year,skills,interests,domain,experience,project_type,city,is_demo) VALUES (?,?,?,?,?,?,?,?,?,1)",
             (row.student_name,row.branch,int(row.academic_year),row.skills,row.interests,row.domain,row.experience_level,row.preferred_project_type,row.city))
        con.executemany("INSERT INTO projects (title,description,skills,domain,project_type) VALUES (?,?,?,?,?)", [
          ("Campus Event App","Build a mobile app for college events and registrations.","Python,UI/UX,Firebase","Mobile Development","Mobile Application"),
          ("Student Analytics Dashboard","Analyse academic and club activity trends.","Python,SQL,Power BI","Data Science","Data Analysis"),
          ("Secure File Sharing","Create a privacy-first peer file sharing platform.","Python,Cybersecurity,SQL","Cybersecurity","Web Application")])
    con.commit()

def words(text): return {x.strip().casefold() for x in str(text or "").split(",") if x.strip()}
def jaccard(a,b):
    a,b=words(a),words(b)
    return len(a & b)/len(a | b) if a | b else 0
def feature_vector(source, candidate):
    same_domain = source["domain"] == candidate["domain"]
    gap = abs(LEVEL.get(source["experience"],0)-LEVEL.get(candidate["experience"],0))
    return {"skill_similarity":jaccard(source["skills"],candidate["skills"]), "interest_similarity":jaccard(source["interests"],candidate["interests"]),
     "domain_similarity":float(same_domain), "experience_compatibility":{0:1,1:.65,2:.25}.get(gap,.25),
     "previous_collaboration":0, "project_similarity":1 if source["project_type"]==candidate["project_type"] else (.5 if same_domain else 0)}
def score(source, candidate):
    frame=pd.DataFrame([feature_vector(source,candidate)],columns=FEATURES)
    return round(float(MODEL["model"].predict_proba(frame)[0,1])*100,1)
def current_profile():
    if "user_id" not in session: return None
    return db().execute("SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)).fetchone()
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session: return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    return redirect(url_for("dashboard") if current_profile() else url_for("login"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form["email"].strip().lower(); password=request.form["password"]
        if len(password)<6: flash("Use a password with at least 6 characters."); return render_template("register.html")
        try:
            cur=db().execute("INSERT INTO users (email,password_hash) VALUES (?,?)",(email,generate_password_hash(password))); db().commit()
            session["user_id"]=cur.lastrowid; return redirect(url_for("profile"))
        except sqlite3.IntegrityError: flash("That email is already registered.")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        user=db().execute("SELECT * FROM users WHERE email=?",(request.form["email"].strip().lower(),)).fetchone()
        if user and check_password_hash(user["password_hash"],request.form["password"]):
            session["user_id"]=user["id"]; return redirect(url_for("dashboard"))
        flash("Incorrect email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    profile=current_profile()
    if request.method=="POST":
        form_profile = dict(profile) if profile else {}
        field_names = {"name": "name", "branch": "branch", "academic_year": "year", "skills": "skills", "interests": "interests", "domain": "domain", "experience": "experience", "project_type": "project_type", "city": "city", "phone": "phone", "github": "github"}
        for profile_key, form_key in field_names.items():
            if form_key in request.form:
                form_profile[profile_key] = request.form.get(form_key, "").strip()
        form_profile["share_contact"] = int("share_contact" in request.form)

        if request.form.get("action") == "extract_resume":
            upload = request.files.get("resume")
            if not upload or not upload.filename:
                flash("Choose a PDF or DOCX resume first."); return render_template("profile.html", profile=form_profile, domains=DOMAINS)
            try:
                extracted = extract_resume(upload)
            except ValueError as error:
                flash(str(error)); return render_template("profile.html", profile=form_profile, domains=DOMAINS)
            for key, value in extracted.items():
                if value and not form_profile.get(key):
                    form_profile[key] = value
            flash("Resume analysed. Review the suggested details, then save your profile.")
            return render_template("profile.html", profile=form_profile, domains=DOMAINS)

        if form_profile.get("domain") not in DOMAINS:
            flash("Choose a valid domain."); return render_template("profile.html", profile=form_profile, domains=DOMAINS)
        try:
            academic_year = int(form_profile.get("academic_year", ""))
        except (TypeError, ValueError):
            academic_year = 0
        if academic_year not in range(1, 5):
            flash("Choose your academic year."); return render_template("profile.html", profile=form_profile, domains=DOMAINS)
        required_fields = ("name", "branch", "skills", "interests", "experience", "project_type", "city")
        if any(not form_profile.get(key) for key in required_fields):
            flash("Complete the required profile fields before saving."); return render_template("profile.html", profile=form_profile, domains=DOMAINS)
        if form_profile.get("experience") not in LEVEL:
            flash("Choose a valid experience level."); return render_template("profile.html", profile=form_profile, domains=DOMAINS)
        data=(session["user_id"],form_profile["name"],form_profile["branch"],academic_year,form_profile["skills"],form_profile["interests"],form_profile["domain"],form_profile["experience"],form_profile["project_type"],form_profile["city"],form_profile.get("phone", ""),form_profile.get("github", ""),form_profile["share_contact"])
        db().execute("INSERT INTO profiles (user_id,name,branch,academic_year,skills,interests,domain,experience,project_type,city,phone,github,share_contact) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET name=excluded.name,branch=excluded.branch,academic_year=excluded.academic_year,skills=excluded.skills,interests=excluded.interests,domain=excluded.domain,experience=excluded.experience,project_type=excluded.project_type,city=excluded.city,phone=excluded.phone,github=excluded.github,share_contact=excluded.share_contact",data); db().commit()
        flash("Profile saved."); return redirect(url_for("dashboard"))
    return render_template("profile.html", profile=profile, domains=DOMAINS)

@app.route("/dashboard")
@login_required
def dashboard():
    profile=current_profile()
    if not profile: return redirect(url_for("profile"))
    candidates=db().execute("SELECT profiles.*, users.email AS email FROM profiles LEFT JOIN users ON users.id=profiles.user_id WHERE profiles.id!=?",(profile["id"],)).fetchall()
    teammates=sorted([dict(row, score=score(profile,row)) for row in candidates],key=lambda x:x["score"],reverse=True)[:8]
    projects=db().execute("SELECT projects.*, profiles.name AS owner FROM projects LEFT JOIN profiles ON profiles.user_id=projects.owner_id WHERE status='Open'").fetchall()
    suggested=[]
    for project in projects:
        virtual={"skills":project["skills"],"interests":project["description"],"domain":project["domain"],"experience":profile["experience"],"project_type":project["project_type"]}
        suggested.append(dict(project,score=score(profile,virtual)))
    suggested.sort(key=lambda x:x["score"],reverse=True)
    return render_template("dashboard.html", profile=profile, teammates=teammates, projects=suggested, metrics=METRICS)

@app.route("/projects/new", methods=["GET","POST"])
@login_required
def new_project():
    if not current_profile(): return redirect(url_for("profile"))
    if request.method=="POST":
        if request.form["domain"] not in DOMAINS:
            flash("Choose a valid domain."); return render_template("project_form.html", domains=DOMAINS)
        db().execute("INSERT INTO projects (owner_id,title,description,skills,domain,project_type) VALUES (?,?,?,?,?,?)",(session["user_id"],request.form["title"],request.form["description"],request.form["skills"],request.form["domain"],request.form["project_type"])); db().commit()
        flash("Project posted."); return redirect(url_for("dashboard"))
    return render_template("project_form.html", domains=DOMAINS)

with app.app_context(): init_db()
if __name__=="__main__": app.run(debug=True)
