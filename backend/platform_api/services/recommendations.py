"""Inference only; synthetic compatibility artifacts are intentionally rejected."""
from functools import lru_cache
import joblib
import sklearn
from django.conf import settings
from rest_framework.exceptions import APIException

class ModelsUnavailable(APIException):
    status_code = 503
    default_code = "models_unavailable"
    default_detail = "The real-data recommendation model is not ready. Please try again after offline training."

@lru_cache(maxsize=1)
def load_models():
    try:
        bundle = joblib.load(settings.ML_MODEL_PATH)
        metadata = bundle["metadata"]
        if metadata["schema_version"] != 3 or metadata["synthetic"] or metadata["dependencies"]["scikit-learn"] != sklearn.__version__:
            raise ValueError("Model schema or dependency mismatch")
        return bundle
    except (OSError, ValueError, KeyError, ImportError, EOFError):
        raise ModelsUnavailable()

def notice():
    return "Discovery scores combine technology overlap, reciprocal interests and survey-trained language preferences. They are not probabilities of successful friendship or teamwork."
