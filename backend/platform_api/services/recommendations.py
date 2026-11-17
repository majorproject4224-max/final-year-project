"""Inference only: requests never train a model or invent fallback percentages."""
from functools import lru_cache
import joblib
import numpy as np
import pandas as pd
import sklearn
from django.conf import settings
from rest_framework.exceptions import APIException
from ml.features import profile_text, pair_features, project_features

class ModelsUnavailable(APIException):
    status_code = 503
    default_code = "models_unavailable"
    default_detail = "Recommendations are temporarily unavailable. The saved ML models need to be prepared."

@lru_cache(maxsize=1)
def load_models():
    try:
        bundle = joblib.load(settings.ML_MODEL_PATH)
        metadata = bundle["metadata"]
        if metadata["schema_version"] != 2 or metadata["dependencies"]["scikit-learn"] != sklearn.__version__:
            raise ValueError("Model dependency/schema mismatch.")
        return bundle
    except (OSError, ValueError, KeyError, ImportError, EOFError):
        raise ModelsUnavailable()

def candidate_indices(source, candidates, project_candidates=False):
    bundle = load_models()
    texts = [profile_text({"skills": c["required_skills"], "interests": c.get("required_interests", [])}) if project_candidates else profile_text(c) for c in candidates]
    source_vector = bundle["vectorizer"].transform([profile_text(source)])
    if source_vector.nnz == 0:
        return [], None
    matrix = bundle["vectorizer"].transform(texts)
    nearest = np.argsort(bundle["clusters"].transform(source_vector)[0])[:2]
    clusters = bundle["clusters"].predict(matrix)
    similarities = (matrix @ source_vector.T).toarray().ravel()
    # Expand beyond the nearest groups when tags overlap, preserving multidisciplinary candidates.
    selected = [i for i in range(len(candidates)) if matrix[i].nnz and (clusters[i] in nearest or similarities[i] > 0)]
    selected.sort(key=lambda i: (clusters[i] not in nearest, -similarities[i], i))
    return selected[:200], int(nearest[0])

def probabilities(source, candidates, kind="users"):
    bundle = load_models()
    features = [pair_features(source, c) if kind == "users" else project_features(source, c) for c in candidates]
    names = bundle["user_features"] if kind == "users" else bundle["project_features"]
    return bundle[kind].predict_proba(pd.DataFrame(features, columns=names))[:, list(bundle[kind].classes_).index(1)]

def notice():
    metadata = load_models()["metadata"]
    return "Development match scores learned from synthetic rubric labels; not validated probabilities of team success." if metadata["synthetic"] else "Model estimates; a match score is not a guarantee of successful collaboration."
