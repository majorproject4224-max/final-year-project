"""Shared, deterministic feature engineering for training and API inference."""
import math
import re
import unicodedata

ALIASES = {"ml": "machine learning", "machine-learning": "machine learning", "js": "javascript", "node": "node.js", "nodejs": "node.js", "scikit learn": "scikit-learn", "sklearn": "scikit-learn", "ai": "artificial intelligence"}
EXPERIENCE = {"beginner": 0, "intermediate": 1, "advanced": 2}
USER_FEATURES = ["skill_similarity", "interest_similarity", "domain_similarity", "experience_compatibility", "project_type_match", "availability_compatibility"]
PROJECT_FEATURES = ["skill_coverage", "interest_similarity", "domain_similarity", "experience_fit", "project_type_match", "availability_fit"]

def normalize_text(value):
    if value is None or isinstance(value, float) and math.isnan(value):
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).strip().casefold().split())

def normalize_items(values):
    if values is None or isinstance(values, float) and math.isnan(values):
        return []
    if isinstance(values, str):
        values = re.split(r"[,;|]", values)
    return sorted({ALIASES.get(normalize_text(v), normalize_text(v)) for v in values if normalize_text(v)})

def normalize_domain(value):
    text = normalize_text(value)
    return {"software": "backend development", "ai/ml": "ai / ml", "ai & ml": "ai / ml", "machine learning": "ai / ml"}.get(text, text)

def jaccard_similarity(left, right):
    left, right = set(normalize_items(left)), set(normalize_items(right))
    union = left | right
    return len(left & right) / len(union) if union else 0.0

def experience_rank(profile, key="experience"):
    return EXPERIENCE.get(normalize_text(profile.get(key, profile.get("experience_level"))), 0)

def equal_present(left, right):
    return float(bool(normalize_text(left)) and normalize_text(left) == normalize_text(right))

def hours(profile, key="availability_hours"):
    return max(1.0, float(profile.get(key, 8) or 8))

def profile_text(profile):
    # Prefix whole normalized tags: "machine learning" stays one feature.
    tags = []
    for field, prefix in (("skills", "skill"), ("interests", "interest")):
        tags.extend(prefix + "_" + re.sub(r"\s+", "_", item) for item in normalize_items(profile.get(field)))
    return " ".join(tags)

def pair_features(left, right):
    gap = abs(experience_rank(left) - experience_rank(right))
    return {
        "skill_similarity": jaccard_similarity(left.get("skills"), right.get("skills")),
        "interest_similarity": jaccard_similarity(left.get("interests"), right.get("interests")),
        "domain_similarity": equal_present(normalize_domain(left.get("domain")), normalize_domain(right.get("domain"))),
        "experience_compatibility": 1.0 - gap / 2,
        "project_type_match": equal_present(left.get("preferred_project_type"), right.get("preferred_project_type")),
        "availability_compatibility": min(hours(left), hours(right)) / max(hours(left), hours(right)),
    }

def project_features(student, project):
    skills, required = set(normalize_items(student.get("skills"))), set(normalize_items(project.get("required_skills")))
    return {
        "skill_coverage": len(skills & required) / len(required) if required else 0.0,
        "interest_similarity": jaccard_similarity(student.get("interests"), project.get("required_interests")),
        "domain_similarity": equal_present(normalize_domain(student.get("domain")), normalize_domain(project.get("domain"))),
        "experience_fit": 1 - max(0, experience_rank(project, "required_experience") - experience_rank(student)) / 2,
        "project_type_match": equal_present(student.get("preferred_project_type"), project.get("project_type")),
        "availability_fit": min(1.0, hours(student) / hours(project, "expected_hours")),
    }

def explain_pair(left, right):
    reasons = []
    for field, name in (("skills", "shared_skills"), ("interests", "shared_interests")):
        shared = sorted(set(normalize_items(left.get(field))) & set(normalize_items(right.get(field))))
        if shared:
            reasons.append({"feature": name, "items": shared})
    if equal_present(normalize_domain(left.get("domain")), normalize_domain(right.get("domain"))):
        reasons.append({"feature": "same_domain", "value": left["domain"]})
    if equal_present(left.get("preferred_project_type"), right.get("preferred_project_type")):
        reasons.append({"feature": "same_project_type", "value": left["preferred_project_type"]})
    return reasons

def explain_project(student, project):
    shared = sorted(set(normalize_items(student.get("skills"))) & set(normalize_items(project.get("required_skills"))))
    missing = sorted(set(normalize_items(project.get("required_skills"))) - set(shared))
    reasons = [{"feature": "required_skills_matched", "items": shared}] if shared else []
    if missing:
        reasons.append({"feature": "skills_to_learn", "items": missing})
    if equal_present(normalize_domain(student.get("domain")), normalize_domain(project.get("domain"))):
        reasons.append({"feature": "same_domain", "value": project["domain"]})
    if project_features(student, project)["availability_fit"] == 1:
        reasons.append({"feature": "availability", "value": "Weekly availability meets the project requirement"})
    return reasons
