"""One preprocessing contract for real survey training and live profile inference.

Missing answers stay missing. No field is inferred from a person's name, college,
gender, location, previous synthetic domain or demonstration account.
"""

import hashlib
import json
import math
import re
from collections import Counter

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction import DictVectorizer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Normalizer

FIELD_MAP = {
    "languages": "LanguageHaveWorkedWith",
    "databases": "DatabaseHaveWorkedWith",
    "frameworks": "WebframeHaveWorkedWith",
    "platforms": "PlatformHaveWorkedWith",
}
TARGET = "LanguageWantToWorkWith"
PROFILE_FIELDS = [*FIELD_MAP, "years_code", "wanted_languages"]
MISSING = {"", "na", "n/a", "nan", "null", "none", "<na>"}
ALIASES = {"js": "javascript", "ts": "typescript", "nodejs": "node.js", "node js": "node.js", "reactjs": "react", "react.js": "react", "postgres": "postgresql", "mongo": "mongodb"}


def is_missing(value):
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return False
    return bool(pd.isna(value)) or str(value).strip().casefold() in MISSING


def tags(value):
    if is_missing(value):
        return []
    values = re.split(r"[;,|]", value) if isinstance(value, str) else value
    if not isinstance(values, (list, tuple, set)):
        raise ValueError("Technology answers must be text or a list of text.")
    result = set()
    for item in values:
        if is_missing(item):
            continue
        if not isinstance(item, str):
            raise ValueError("Each technology must be text.")
        text = " ".join(item.strip().casefold().split())
        result.add(ALIASES.get(text, text))
    return sorted(result)


def years(value):
    if is_missing(value):
        return None
    text = str(value).strip().casefold()
    if text == "less than 1 year":
        return 0.5
    if text == "more than 50 years":
        return 51.0
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) and 0 <= result <= 51 else None


def clean_profile(profile):
    return {
        **{field: tags(profile.get(field)) for field in FIELD_MAP},
        "years_code": years(profile.get("years_code")),
        "wanted_languages": tags(profile.get("wanted_languages")),
    }


def current_technologies(profile):
    return sorted({item for field in FIELD_MAP for item in tags(profile.get(field))})


def observed_profile(profile):
    return bool(current_technologies(profile))


def technology_dict(profile):
    return {f"{field}:{item}": 1.0 for field in FIELD_MAP for item in tags(profile.get(field))}


class SurveyEncoder(BaseEstimator, TransformerMixin):
    """Learn vocabulary/median only on training respondents; ignore unseen tags.

    RF sees binary technologies, train-median coding years, and missing flags.
    Clustering uses L2-normalized technology vectors only, so missingness and
    years cannot create artificial 'expert' or 'missing profile' clusters.
    """

    def fit(self, rows, y=None):
        rows = list(rows)
        self.vocabulary_ = DictVectorizer(sparse=True).fit([technology_dict(r) for r in rows])
        self.imputer_ = SimpleImputer(strategy="median", keep_empty_features=True).fit(self.numeric(rows))
        return self

    @staticmethod
    def numeric(rows):
        return np.array([[years(r.get("years_code")) if years(r.get("years_code")) is not None else np.nan] for r in rows])

    def transform(self, rows):
        rows = list(rows)
        tech = self.vocabulary_.transform([technology_dict(r) for r in rows])
        numeric = self.numeric(rows)
        missing = np.array([[float(not tags(r.get(f))) for f in FIELD_MAP] for r in rows])
        return sparse.hstack([tech, self.imputer_.transform(numeric), np.isnan(numeric).astype(float), missing], format="csr")

    def cluster_matrix(self, rows):
        matrix = self.vocabulary_.transform([technology_dict(r) for r in rows])
        return Normalizer().transform(matrix)

    def supported(self, profile):
        return bool(self.cluster_matrix([profile]).nnz)

    def feature_names(self):
        return [*self.vocabulary_.get_feature_names_out(), "years_code", "years_code_missing", *[f"{f}_missing" for f in FIELD_MAP]]

    def options(self):
        return {f: sorted(key.split(":", 1)[1] for key in self.vocabulary_.vocabulary_ if key.startswith(f + ":")) for f in FIELD_MAP}


def read_survey(path):
    frame = pd.read_excel(path) if str(path).endswith(".xlsx") else pd.read_csv(path, low_memory=False)
    columns = ["ResponseId", *FIELD_MAP.values(), "YearsCode", TARGET]
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError("Missing required source columns: " + ", ".join(missing))
    if frame["ResponseId"].isna().any() or frame["ResponseId"].duplicated().any():
        raise ValueError("Respondent IDs must be present and unique.")
    records, preview = [], []
    for row in frame[columns].to_dict("records"):
        profile = clean_profile({**{key: row[column] for key, column in FIELD_MAP.items()}, "years_code": row["YearsCode"], "wanted_languages": row[TARGET]})
        # Exact normalized input profiles form a group, including different labels.
        # They must never appear on both sides of evaluation splits.
        inputs = {key: profile[key] for key in [*FIELD_MAP, "years_code"]}
        group = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        records.append({**profile, "response_id": str(row["ResponseId"]), "group": group, "target_observed": not is_missing(row[TARGET])})
    eligible = [r for r in records if r["target_observed"] and r["wanted_languages"] and observed_profile(r)]
    counts = Counter(r["group"] for r in eligible)
    audit = {
        "raw_rows": len(frame), "raw_columns": len(frame.columns),
        "source_missing_counts": {c: int(frame[c].isna().sum()) for c in columns},
        "source_missing_percent": {c: round(float(frame[c].isna().mean() * 100), 3) for c in columns},
        "invalid_years_nonmissing": sum(not is_missing(v) and years(v) is None for v in frame["YearsCode"]),
        "missing_target_excluded": sum(not r["target_observed"] or not r["wanted_languages"] for r in records),
        "no_current_technology_excluded": sum(not observed_profile(r) for r in records),
        "eligible_rows": len(eligible), "unique_input_groups": len(counts),
        "repeated_input_rows": sum(n - 1 for n in counts.values()),
        "exclusion_counts_can_overlap": True,
    }
    # Real examples with missingness first. No injected dirt is labelled as source data.
    selected = frame.index[frame[columns[1:]].isna().any(axis=1)].tolist()[:8] + list(frame.index[:4])
    for index in dict.fromkeys(selected):
        raw = {c: None if is_missing(frame.at[index, c]) else str(frame.at[index, c]) for c in columns}
        preview.append({"raw": raw, "cleaned": {k: records[index][k] for k in PROFILE_FIELDS}, "target_observed": records[index]["target_observed"]})
    return eligible, audit, preview


def positive_probabilities(model, matrix):
    outputs = model.predict_proba(matrix)
    return np.column_stack([p[:, list(classes).index(1)] if 1 in classes else np.zeros(matrix.shape[0]) for p, classes in zip(outputs, model.classes_)])
