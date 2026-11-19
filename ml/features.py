"""Community/project text utilities. Survey ML preprocessing lives in ml.survey."""
import math
import re
import unicodedata

ALIASES = {"ml": "machine learning", "machine-learning": "machine learning", "js": "javascript", "node": "node.js", "nodejs": "node.js", "scikit learn": "scikit-learn", "sklearn": "scikit-learn", "ai": "artificial intelligence"}

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
    return len(left & right) / len(left | right) if left | right else 0.0
