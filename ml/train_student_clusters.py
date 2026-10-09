"""Train profile clusters and choose k by silhouette score."""
from pathlib import Path
import json
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from platform_api.matching import profile_text

STUDENTS_PATH = ROOT / "dataset" / "students.xlsx"
MODEL_PATH = ROOT / "ml" / "models" / "student_clusters.joblib"
METRICS_PATH = ROOT / "ml" / "evaluation" / "student_cluster_metrics.json"


def main():
    students = pd.read_excel(STUDENTS_PATH)
    required = {"user_id", "skills", "interests", "domain"}
    missing = required - set(students.columns)
    if missing:
        raise ValueError(f"Missing required student columns: {sorted(missing)}")
    texts = [profile_text(student) for student in students.to_dict("records")]
    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[\w.+#/-]+\b", min_df=2, sublinear_tf=True)
    matrix = vectorizer.fit_transform(texts)
    upper_k = min(10, len(students) - 1)
    candidates = []
    for cluster_count in range(2, upper_k + 1):
        candidate_model = KMeans(n_clusters=cluster_count, random_state=42, n_init=20)
        labels = candidate_model.fit_predict(matrix)
        if len(set(labels)) < 2:
            continue
        silhouette = silhouette_score(
            matrix,
            labels,
            sample_size=min(1000, len(students)),
            random_state=42,
        )
        candidates.append((silhouette, cluster_count, candidate_model))
    if not candidates:
        raise ValueError("Not enough distinct student profiles to select clusters.")
    best_score, best_k, best_model = max(candidates, key=lambda result: result[0])
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": best_model}, MODEL_PATH)
    metrics = {
        "dataset_rows": int(len(students)),
        "candidate_k": [
            {"k": int(k), "silhouette_score": round(float(score), 6)}
            for score, k, _ in candidates
        ],
        "selected_k": int(best_k),
        "selected_silhouette_score": round(float(best_score), 6),
        "selection_method": "maximum silhouette score over k=2..min(10,n-1)",
        "cluster_sizes": {
            str(int(cluster)): int(count)
            for cluster, count in zip(*np.unique(best_model.labels_, return_counts=True))
        },
        "data_source": "reproducible synthetic prototype dataset; not real students",
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Saved model: {MODEL_PATH}")


if __name__ == "__main__":
    main()
