"""Create reproducible synthetic datasets for connecT AI Phase 1."""
from pathlib import Path
import random
import sys
import pandas as pd
from openpyxl.styles import Font, PatternFill

ROOT=Path(__file__).parent
STUDENTS=ROOT/"students.xlsx"
MATCHES=ROOT/"matching_data.xlsx"
sys.path.insert(0, str(ROOT.parent / "backend"))
from platform_api.matching import pair_features

rng=random.Random(20260823)
first="Aarav Aditi Aditya Akash Ananya Anika Arjun Arnav Aryan Bhavya Deepak Dev Diya Ishaan Isha Kavya Kiran Manish Meera Nandini Neha Nikhil Pooja Pranav Priya Rahul Riya Rohan Saanvi Shivam Sneha Tanvi Varun Ved Vikram Yash".split()
last="Agarwal Bansal Chatterjee Das Gupta Iyer Jain Kapoor Khan Kulkarni Mehta Menon Mishra Nair Patel Rao Reddy Roy Shah Sharma Singh Srivastava Verma Yadav".split()
cities="Bengaluru Chennai Delhi Hyderabad Jaipur Kochi Kolkata Lucknow Mumbai Pune".split()
personas=[
 ("AI & ML",["Python","Machine Learning","Pandas","Scikit-learn","SQL"],["AI","Data Science","Research"],"AI / ML","AI/ML Application"),
 ("Web Development",["JavaScript","React","HTML/CSS","Node.js","Git"],["Web Development","UI/UX","Startups"],"Web Development","Web Application"),
 ("Backend Development",["Python","Django","REST API","SQL","Git"],["Backend","Cloud","Open Source"],"Software","Web Application"),
 ("Data Science",["Python","Pandas","SQL","Power BI","Machine Learning"],["Data Science","Analytics","AI"],"Data Science","Data Analysis"),
 ("Cybersecurity",["Python","Linux","Networking","Cybersecurity","Git"],["Security","CTF","Open Source"],"Cybersecurity","Security Tool"),
 ("Mobile Development",["Java","Kotlin","Firebase","Git","UI/UX"],["Mobile Apps","UI/UX","Startups"],"Mobile Development","Mobile Application"),
]
def pick_items(items,n):
    return ",".join(sorted(rng.sample(items,n)))
rows=[]
for i in range(1,1001):
    branch,base_skills,base_interests,domain,project_type=rng.choice(personas)
    year=rng.choices([1,2,3,4],[12,27,34,27])[0]
    experience="Beginner" if year==1 else rng.choices(["Beginner","Intermediate","Advanced"],[20,65,15] if year==2 else [8,67,25])[0]
    projects=max(0,min(8,year-1+rng.choice([0,1,1,2])))
    skills=pick_items(base_skills,rng.choice([3,4,5]))
    interests=pick_items(base_interests,rng.choice([2,2,3]))
    rows.append({"user_id":f"U{i:04d}","student_name":f"{rng.choice(first)} {rng.choice(last)}","branch":branch,"academic_year":year,"skills":skills,"interests":interests,"domain":domain,"experience_level":experience,"projects_completed":projects,"preferred_project_type":project_type,"city":rng.choice(cities),"availability_hours_per_week":rng.choice([4,6,8,10,12,15]),"collaboration_style":rng.choice(["Structured","Flexible","Research-oriented","Fast-paced"])})
students=pd.DataFrame(rows)
pairs=set(); match_rows=[]
while len(match_rows)<1500:
    a,b=rng.sample(range(len(students)),2)
    key=tuple(sorted((a,b)))
    if key in pairs: continue
    pairs.add(key); u=students.iloc[a]; v=students.iloc[b]
    prior=1 if (u.city==v.city and rng.random()<0.16) else 0
    features=pair_features(
        {"skills":u.skills,"interests":u.interests,"domain":u.domain,"experience":u.experience_level,"preferred_project_type":u.preferred_project_type},
        {"skills":v.skills,"interests":v.interests,"domain":v.domain,"experience":v.experience_level,"preferred_project_type":v.preferred_project_type},
        previous_collaboration=prior,
    )
    score=.34*features["skill_similarity"]+.25*features["interest_similarity"]+.16*features["domain_similarity"]+.12*features["experience_compatibility"]+.08*features["project_similarity"]+.05*features["previous_collaboration"]
    label=1 if score>=.52 else 0
    match_rows.append({"user1_id":u.user_id,"user2_id":v.user_id,**features,"compatibility_score_rule":round(score,3),"compatibility_label":label})
matches=pd.DataFrame(match_rows)
def write(df,path,sheet):
    with pd.ExcelWriter(path,engine="openpyxl") as w:
        df.to_excel(w,sheet_name=sheet,index=False)
        ws=w.sheets[sheet]; ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
        for cell in ws[1]:
            cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="1F4E78")
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width=min(max(len(str(c.value or "")) for c in col)+2,30)
write(students,STUDENTS,"Students")
write(matches,MATCHES,"Compatibility Matches")
print(f"students={len(students)}, unique_ids={students.user_id.nunique()}, duplicate_rows={students.duplicated().sum()}")
print(f"matches={len(matches)}, label_counts={matches.compatibility_label.value_counts().sort_index().to_dict()}, duplicate_pairs={matches.duplicated(['user1_id','user2_id']).sum()}")
