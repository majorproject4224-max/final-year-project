SKILL_ALIASES = {
    "ml": "machine learning",
    "machine-learning": "machine learning",
    "js": "javascript",
    "node": "node.js",
    "scikit learn": "scikit-learn",
}


def normalize_items(values):
    if isinstance(values, str):
        values = values.split(",")
    normalized = set()
    for value in values:
        item = " ".join(str(value).strip().casefold().split())
        if item:
            normalized.add(SKILL_ALIASES.get(item, item))
    return sorted(normalized)


def jaccard_similarity(left, right):
    left_items = set(normalize_items(left))
    right_items = set(normalize_items(right))
    union = left_items | right_items
    return len(left_items & right_items) / len(union) if union else 0.0


def experience_compatibility(left, right):
    rank = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
    difference = abs(rank.get(left, 0) - rank.get(right, 0))
    return {0: 1.0, 1: 0.65, 2: 0.25}[difference]


def profile_text(profile):
    features = normalize_items(profile.get("skills", [])) + normalize_items(profile.get("interests", []))
    domain = " ".join(str(profile.get("domain", "")).casefold().split())
    if domain:
        features.append(f"domain_{domain.replace(' ', '_')}")
    return " ".join(features)


def pair_features(source, candidate, previous_collaboration=0.0):
    source_skills = set(normalize_items(source.get("skills", [])))
    candidate_skills = set(normalize_items(candidate.get("skills", [])))
    source_interests = set(normalize_items(source.get("interests", [])))
    candidate_interests = set(normalize_items(candidate.get("interests", [])))
    same_domain = source.get("domain") == candidate.get("domain")
    same_project_type = (
        source.get("preferred_project_type") == candidate.get("preferred_project_type")
    )
    return {
        "skill_similarity": jaccard_similarity(source_skills, candidate_skills),
        "interest_similarity": jaccard_similarity(source_interests, candidate_interests),
        "domain_similarity": float(same_domain),
        "experience_compatibility": experience_compatibility(source.get("experience"), candidate.get("experience")),
        "previous_collaboration": float(previous_collaboration),
        "project_similarity": 1.0 if same_project_type else (0.5 if same_domain else 0.0),
    }


def explain_pair(source, candidate):
    source_skills = set(normalize_items(source.get("skills", [])))
    candidate_skills = set(normalize_items(candidate.get("skills", [])))
    source_interests = set(normalize_items(source.get("interests", [])))
    candidate_interests = set(normalize_items(candidate.get("interests", [])))
    explanations = []
    shared_skills = sorted(source_skills & candidate_skills)
    shared_interests = sorted(source_interests & candidate_interests)
    if shared_skills:
        explanations.append({"feature": "shared_skills", "items": shared_skills})
    if shared_interests:
        explanations.append({"feature": "shared_interests", "items": shared_interests})
    if source.get("domain") == candidate.get("domain"):
        explanations.append({"feature": "same_domain", "value": source.get("domain")})
    if source.get("preferred_project_type") == candidate.get("preferred_project_type"):
        explanations.append({"feature": "same_project_type", "value": source.get("preferred_project_type")})
    return explanations