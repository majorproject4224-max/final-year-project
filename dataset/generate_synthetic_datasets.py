"""Reproducible development fixtures, NEVER real students or observed team outcomes.
Profile attributes are sampled from documented overlapping skill pools. Labels are
deterministic rubric decisions; their source and audit score are retained per row.
"""
import argparse
import random
import sys
from pathlib import Path
import pandas as pd
from openpyxl.styles import Font, PatternFill

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.features import pair_features, project_features

POOLS = [
    ("AI / ML", ["Python", "Machine Learning", "Pandas", "Scikit-learn", "SQL"], ["AI", "Research", "Data Science"], "AI/ML Application"),
    ("Web Development", ["JavaScript", "React", "HTML", "CSS", "Git"], ["UI/UX", "Web Development", "Accessibility"], "Web Application"),
    ("Backend Development", ["Python", "Django", "REST API", "SQL", "Git"], ["Backend", "Open Source", "Cloud"], "Web Application"),
    ("Data Science", ["Python", "Pandas", "SQL", "Power BI", "Statistics"], ["Analytics", "Research", "Data Science"], "Data Analysis"),
    ("Cybersecurity", ["Python", "Linux", "Networking", "Cybersecurity", "Git"], ["Security", "CTF", "Open Source"], "Security Tool"),
    ("Mobile Development", ["Java", "Kotlin", "Firebase", "Git", "UI/UX"], ["Mobile Apps", "Accessibility", "Startups"], "Mobile Application"),
    ("Cloud / DevOps", ["Linux", "Docker", "Python", "Git", "AWS"], ["Cloud", "Automation", "Open Source"], "Developer Tool"),
]
SCENARIOS = [
    ("Campus research assistant", 0, ["Python", "Machine Learning", "React"], ["Research", "AI"]),
    ("Accessible campus portal", 1, ["React", "HTML", "CSS"], ["Accessibility", "UI/UX"]),
    ("Project collaboration API", 2, ["Python", "Django", "REST API"], ["Backend", "Open Source"]),
    ("Library usage analysis", 3, ["Python", "Pandas", "Statistics"], ["Analytics", "Research"]),
    ("Security log explorer", 4, ["Python", "Linux", "React"], ["Security", "Analytics"]),
    ("Campus navigation app", 5, ["Kotlin", "Firebase", "UI/UX"], ["Mobile Apps", "Accessibility"]),
    ("Student deployment toolkit", 6, ["Docker", "Python", "Git"], ["Automation", "Open Source"]),
    ("Research data dashboard", 3, ["Pandas", "React", "SQL"], ["Research", "UI/UX"]),
    ("Open-source issue matcher", 0, ["Python", "Scikit-learn", "Git"], ["Open Source", "AI"]),
    ("Event booking service", 2, ["Django", "SQL", "React"], ["Backend", "Web Development"]),
    ("Mobile safety companion", 5, ["Kotlin", "Networking", "Firebase"], ["Mobile Apps", "Security"]),
    ("Cloud cost explorer", 6, ["AWS", "Pandas", "React"], ["Cloud", "Analytics"]),
]

def user_rubric(features):
    score = sum(features[k] * w for k, w in zip(features, [.30, .25, .10, .10, .10, .15]))
    label = int(features["skill_similarity"] >= .15 and features["interest_similarity"] > 0 and score >= .48)
    return score, label

def project_rubric(features):
    score = sum(features[k] * w for k, w in zip(features, [.45, .15, .10, .10, .10, .10]))
    label = int(features["skill_coverage"] >= .5 and features["availability_fit"] >= .5 and score >= .58)
    return score, label

def write_table(rows, folder, name):
    frame = pd.DataFrame(rows)
    frame.to_csv(folder / f"{name}.csv", index=False)
    with pd.ExcelWriter(folder / f"{name}.xlsx", engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Synthetic data")
        sheet = writer.sheets["Synthetic data"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="203B36")
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = min(45, max(18, len(str(column[0].value)) + 3))

def generate(folder, seed=4224):
    rng = random.Random(seed)
    folder.mkdir(parents=True, exist_ok=True)
    students = []
    for index in range(420):
        pool = POOLS[index % len(POOLS)]
        other = rng.choice([p for p in POOLS if p != pool])
        skills = rng.sample(pool[1], rng.randint(2, 5))
        interests = rng.sample(pool[2], 2)
        if index % 3 == 0:
            skills += rng.sample(other[1], 2)
            interests += rng.sample(other[2], 1)
        students.append({
            "user_id": f"S{index+1:04}", "student_name": f"Demo Student {index+1:03}",
            "academic_year": rng.randint(1, 4), "branch": "Computer Science and Engineering",
            "skills": ",".join(sorted(set(skills))), "interests": ",".join(sorted(set(interests))),
            "domain": pool[0], "experience": rng.choice(["Beginner", "Intermediate", "Advanced"]),
            "projects_completed": rng.randint(0, 6), "preferred_project_type": pool[3],
            "availability_hours": rng.choice([4, 6, 8, 10, 12]), "data_source": "synthetic_profile_v2",
        })
    projects = []
    for index in range(84):
        title, pool_id, skills, interests = SCENARIOS[index % len(SCENARIOS)]
        pool = POOLS[pool_id]
        projects.append({
            "project_id": f"P{index+1:03}", "title": f"{title} — scenario {index+1}",
            "domain": pool[0], "required_skills": ",".join(skills), "required_interests": ",".join(interests),
            "required_experience": rng.choice(["Beginner", "Intermediate", "Advanced"]),
            "team_size": rng.randint(2, 6), "project_type": pool[3], "expected_hours": rng.choice([4, 6, 8, 10]),
            "data_source": "synthetic_project_scenario_v2",
        })
    user_pairs = []
    combinations = [(a, b) for a in range(len(students)) for b in range(a+1, len(students))]
    for a, b in rng.sample(combinations, 6000):
        features = pair_features(students[a], students[b])
        score, label = user_rubric(features)
        user_pairs.append({"user1_id": students[a]["user_id"], "user2_id": students[b]["user_id"], **features, "rubric_score": score, "compatibility_label": label, "label_source": "synthetic_user_rubric_v2"})
    project_pairs = []
    for a, b in rng.sample([(a, b) for a in range(len(students)) for b in range(len(projects))], 6000):
        features = project_features(students[a], projects[b])
        score, label = project_rubric(features)
        project_pairs.append({"user_id": students[a]["user_id"], "project_id": projects[b]["project_id"], **features, "rubric_score": score, "compatibility_label": label, "label_source": "synthetic_project_rubric_v2"})
    for name, rows in (("students", students), ("projects", projects), ("matching_data", user_pairs), ("project_matches", project_pairs)):
        write_table(rows, folder, name)
        print(f"{name}: {len(rows)} synthetic rows")
    return students, projects

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dataset")
    args = parser.parse_args()
    generate(args.output)
