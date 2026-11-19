"""Interpretable discovery using learned preferences and reciprocal comparisons.

Weights below are product ranking choices, NOT supervised compatibility labels.
Never train a classifier on the scores produced by this module.
"""
import numpy as np
from ml.survey import FIELD_MAP, current_technologies, tags, positive_probabilities


def profile_quality(profile, encoder=None):
    missing = [field for field in FIELD_MAP if not tags(profile.get(field))]
    if profile.get("years_code") is None:
        missing.append("years_code")
    known = current_technologies(profile)
    unsupported = []
    if encoder is not None:
        vocabulary = {key.split(":", 1)[1] for key in encoder.vocabulary_.vocabulary_}
        unsupported = sorted(set(known) - vocabulary)
    return {"missing_fields": missing, "observed_input_fields": 5 - len(missing), "total_input_fields": 5, "unsupported_technologies": unsupported}


def preference_estimates(bundle, profile):
    encoder = bundle["encoder"]
    if not encoder.supported(profile):
        return {}
    scores = positive_probabilities(bundle["preferences"], encoder.transform([profile]))[0]
    return dict(zip(bundle["labels"], map(float, scores)))


def compare_people(source, candidate, estimates):
    left, right = set(current_technologies(source)), set(current_technologies(candidate))
    source_wants, target_wants = set(tags(source.get("wanted_languages"))), set(tags(candidate.get("wanted_languages")))
    learn = source_wants & set(tags(candidate.get("languages")))
    offer = target_wants & set(tags(source.get("languages")))
    shared = left & right
    forward = len(learn) / len(source_wants) if source_wants else 0
    reverse = len(offer) / len(target_wants) if target_wants else 0
    similarity = len(shared) / len(left | right) if left | right else 0
    candidate_languages = tags(candidate.get("languages"))
    learned = sum(estimates.get(x, 0.0) for x in candidate_languages) / len(candidate_languages) if candidate_languages else 0
    # Inferred preference never overwrites an explicit answer.
    score = 0.35 * forward + 0.25 * reverse + 0.25 * similarity + 0.15 * learned
    explanations = []
    for feature, values in [("you_want_they_use", learn), ("they_want_you_use", offer), ("shared_technologies", shared)]:
        if values:
            explanations.append({"feature": feature, "items": sorted(values)})
    inferred = sorted(x for x in candidate_languages if estimates.get(x, 0) >= 0.5 and x not in source_wants)
    if inferred:
        explanations.append({"feature": "predicted_interest", "items": inferred})
    return {"match_score": round(score * 100, 1), "score_label": "discovery score", "explanations": explanations,
            "reciprocal_learning": bool(learn and offer), "observed_overlap": bool(learn or offer or shared),
            "components": {"your_interest_coverage": forward, "their_interest_coverage": reverse, "technology_similarity": similarity, "learned_preference_affinity": learned}}


def recommend_people(bundle, source, candidates):
    encoder = bundle["encoder"]
    quality = profile_quality(source, encoder)
    if not encoder.supported(source):
        return [], {"profile_quality": quality, "detail": "Add technologies you have used in My profile. Empty or unsupported profiles do not receive ML scores."}
    source_vector = encoder.cluster_matrix([source])
    nearest = np.argsort(bundle["clusters"].transform(source_vector)[0])[:2]
    estimates = preference_estimates(bundle, source)
    results = []
    for index, candidate in enumerate(candidates):
        if not encoder.supported(candidate):
            continue
        comparison = compare_people(source, candidate, estimates)
        cluster = int(bundle["clusters"].predict(encoder.cluster_matrix([candidate]))[0])
        # Explicit reciprocal links can cross clusters; unlike similar-only discovery.
        if cluster not in nearest and not comparison["observed_overlap"]:
            continue
        if not comparison["observed_overlap"] and comparison["components"]["learned_preference_affinity"] < bundle["threshold"]:
            continue
        results.append({**comparison, "candidate_index": index, "cluster": cluster})
    results.sort(key=lambda row: (-row["match_score"], row["candidate_index"]))
    return results[:12], {"profile_quality": quality, "candidate_cluster": int(nearest[0]),
        "predicted_interests": [{"language": name, "preference_probability": round(score, 4), "source": "survey-trained model"} for name, score in sorted(estimates.items(), key=lambda x: -x[1])[:5]],
        "detail": "No supported suggestions yet. You can still browse People." if not results else ""}


def project_match(profile, project):
    current = set(current_technologies(profile))
    required = set(tags(project.get("required_skills")))
    matched = current & required
    explanations = []
    if matched:
        explanations.append({"feature": "required_skills_matched", "items": sorted(matched)})
    if required - current:
        explanations.append({"feature": "skills_to_learn", "items": sorted(required - current)})
    return {"match_score": round(100 * len(matched) / len(required), 1) if required else 0,
            "score_label": "skill coverage", "explanations": explanations}
