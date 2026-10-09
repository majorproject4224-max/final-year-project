"""connecT AI: student teammate recommendations powered by Random Forest."""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent
LEVEL = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
def split(value): return {x.strip().casefold() for x in str(value).split(",") if x.strip()}
def jaccard(a, b):
    a, b = split(a), split(b)
    return round(len(a & b) / len(a | b), 3) if a | b else 0.0

class Recommender:
    def __init__(self):
        self.students = pd.read_excel(ROOT / "dataset/students.xlsx").fillna("")
        pairs = pd.read_excel(ROOT / "dataset/matching_data.xlsx").fillna(0)
        self.bundle = joblib.load(ROOT / "ml/models/random_forest_compatibility.joblib")
        self.features = self.bundle["features"]
        self.history = {tuple(sorted((r.user1_id, r.user2_id))): int(r.previous_collaboration) for r in pairs.itertuples(index=False)}
    def recommendations(self, user_id):
        source_rows = self.students[self.students.user_id == user_id]
        if source_rows.empty: raise KeyError(user_id)
        source = source_rows.iloc[0]
        candidates = self.students[self.students.user_id != user_id]
        vectors, records = [], []
        for _, c in candidates.iterrows():
            gap = abs(LEVEL.get(str(source.experience_level), 0) - LEVEL.get(str(c.experience_level), 0))
            same_domain = source.domain == c.domain
            vector = {"skill_similarity": jaccard(source.skills, c.skills), "interest_similarity": jaccard(source.interests, c.interests), "domain_similarity": float(same_domain), "experience_compatibility": {0: 1.0, 1: 0.65, 2: 0.25}.get(gap, 0.25), "previous_collaboration": float(self.history.get(tuple(sorted((source.user_id, c.user_id))), 0)), "project_similarity": 1.0 if source.preferred_project_type == c.preferred_project_type else (0.5 if same_domain else 0.0)}
            shared_skills, shared_interests = sorted(split(source.skills) & split(c.skills)), sorted(split(source.interests) & split(c.interests))
            reasons = (["Shared skills: " + ", ".join(shared_skills[:3]).title()] if shared_skills else []) + (["Common interests: " + ", ".join(shared_interests[:2]).title()] if shared_interests else []) + (["Same domain: " + c.domain] if same_domain else [])
            vectors.append(vector); records.append({"name": c.student_name, "branch": c.branch, "year": int(c.academic_year), "city": c.city, "experience": c.experience_level, "project": c.preferred_project_type, "reasons": reasons[:3] or ["Complementary experience and project preference"]})
        probabilities = self.bundle["model"].predict_proba(pd.DataFrame(vectors, columns=self.features))[:, 1]
        for row, probability in zip(records, probabilities): row["score"] = round(float(probability) * 100, 1)
        return sorted(records, key=lambda row: row["score"], reverse=True)[:8]
    def students_for_select(self):
        return [{"id": r.user_id, "name": r.student_name, "branch": r.branch, "year": int(r.academic_year), "skills": r.skills, "interests": r.interests} for r in self.students.itertuples(index=False)]

REC = Recommender()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT / "web"), **kwargs)
    def do_GET(self):
        request = urlparse(self.path)
        if request.path == "/api/students": return self.send_json({"students": REC.students_for_select()})
        if request.path == "/api/metrics": return self.send_json(json.loads((ROOT / "ml/evaluation/random_forest_metrics.json").read_text()))
        if request.path == "/api/recommendations":
            try: return self.send_json({"items": REC.recommendations(parse_qs(request.query).get("student_id", [""])[0])})
            except KeyError: return self.send_json({"error": "Select a valid student."}, 400)
        if request.path == "/": self.path = "/index.html"
        return super().do_GET()
    def send_json(self, data, status=200):
        body = json.dumps(data).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
if __name__ == "__main__":
    print("Open http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
