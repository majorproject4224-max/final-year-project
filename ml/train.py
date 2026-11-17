"""Offline training, entity-disjoint evaluation, and versioned model persistence."""

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    silhouette_score,
    ndcg_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from ml.data import load_table, clean_profiles, validate_pairs, STUDENT_COLUMNS, PROJECT_COLUMNS
from ml.features import (
    USER_FEATURES,
    PROJECT_FEATURES,
    profile_text,
    pair_features,
    project_features,
)


def classification_metrics(labels, predicted):
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predicted, average="binary", zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(labels, predicted)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "confusion_matrix": confusion_matrix(labels, predicted, labels=[0, 1]).tolist(),
    }


def split_pairs(frame, project=False, seed=42):
    left, right = ("user_id", "project_id") if project else ("user1_id", "user2_id")
    users = sorted(set(frame[left]) | (set() if project else set(frame[right])))
    train_users, test_users = train_test_split(users, test_size=0.25, random_state=seed)
    train_right, test_right = (
        train_test_split(sorted(set(frame[right])), test_size=0.25, random_state=seed)
        if project
        else (train_users, test_users)
    )
    train = frame[left].isin(train_users) & frame[right].isin(train_right)
    test = frame[left].isin(test_users) & frame[right].isin(test_right)
    if not train.any() or not test.any():
        raise ValueError("Insufficient pairs for an entity-disjoint split.")
    if (
        frame.loc[train, "compatibility_label"].nunique() < 2
        or frame.loc[test, "compatibility_label"].nunique() < 2
    ):
        raise ValueError("Both labels are required in training and testing.")
    return train, test


def train_classifier(frame, features, names, project=False):
    train, test = split_pairs(frame, project)
    model = Pipeline(
        [
            ("missing", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=180,
                    max_depth=10,
                    min_samples_leaf=3,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ]
    )
    x = pd.DataFrame(features, columns=names)
    y = frame.compatibility_label.astype(int)
    model.fit(x.loc[train], y.loc[train])
    scores = model.predict_proba(x.loc[test])[:, list(model.classes_).index(1)]
    report = classification_metrics(y.loc[test], scores >= 0.5)
    report.update(
        {
            "training_pairs": int(train.sum()),
            "test_pairs": int(test.sum()),
            "excluded_cross_partition_pairs": int((~(train | test)).sum()),
            "actual_test_students": len(
                set(frame.loc[test, "user_id" if project else "user1_id"])
                | (set() if project else set(frame.loc[test, "user2_id"]))
            ),
            "test_label_counts": {str(k): int(v) for k, v in y.loc[test].value_counts().items()},
            "split": "Students and projects disjoint"
            if project
            else "Both endpoints of student pairs disjoint",
            "baseline_majority": classification_metrics(
                y.loc[test], np.full(int(test.sum()), int(y.loc[train].mean() >= 0.5))
            ),
            "baseline_similarity": classification_metrics(
                y.loc[test], x.loc[test, "skill_coverage" if project else "skill_similarity"] >= 0.5
            ),
            "feature_importance": dict(
                zip(names, model.named_steps["classifier"].feature_importances_.tolist())
            ),
            "warning": "Synthetic rubric labels; these results measure rubric reproduction, not real collaboration success.",
        }
    )
    # Ranking evaluation is restricted to candidates with observed held-out labels.
    heldout = frame.loc[test].copy()
    heldout["model_score"] = scores
    query = "user_id" if project else "user1_id"
    ranking = []
    for _, group in heldout.groupby(query):
        if len(group) < 2 or not group.compatibility_label.sum():
            continue
        top = group.sort_values("model_score", ascending=False).head(5)
        ranking.append(
            {
                "precision_at_5": float(top.compatibility_label.sum() / len(top)),
                "recall_at_5": float(
                    top.compatibility_label.sum() / group.compatibility_label.sum()
                ),
                "ndcg_at_5": float(
                    ndcg_score([group.compatibility_label.values], [group.model_score.values], k=5)
                ),
            }
        )
    report["ranking"] = {
        "eligible_queries": len(ranking),
        "candidate_scope": "held-out labeled pairs only",
        **(
            {key: float(np.mean([r[key] for r in ranking])) for key in ranking[0]}
            if ranking
            else {}
        ),
    }
    return model, report


def train(data_dir, output_dir, extension="xlsx"):
    sources = {
        name: data_dir / f"{name}.{extension}"
        for name in ("students", "projects", "matching_data", "project_matches")
    }
    students = clean_profiles(load_table(sources["students"], STUDENT_COLUMNS))
    projects = clean_profiles(load_table(sources["projects"], PROJECT_COLUMNS), True)
    users = {p["user_id"]: p for p in students}
    project_map = {p["project_id"]: p for p in projects}
    pairs = validate_pairs(
        load_table(
            sources["matching_data"],
            {"user1_id", "user2_id", "compatibility_label", "label_source"},
        ),
        users,
    )
    project_pairs = validate_pairs(
        load_table(
            sources["project_matches"],
            {"user_id", "project_id", "compatibility_label", "label_source"},
        ),
        users,
        project_map,
    )
    sources_of_labels = sorted(set(pairs.label_source) | set(project_pairs.label_source))
    synthetic = any("synthetic" in str(source) for source in sources_of_labels)
    texts = [profile_text(p) for p in students]
    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[\w.+#/-]+\b", sublinear_tf=True)
    matrix = vectorizer.fit_transform(texts)
    if matrix.shape[1] < 2 or len(set(texts)) < 3:
        raise ValueError("At least three distinct, informative profiles are needed for clustering.")
    clustering = []
    candidates = []
    for k in range(2, min(10, len(set(texts)) - 1) + 1):
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = model.fit_predict(matrix)
        if len(set(labels)) < 2:
            continue
        silhouette = float(
            silhouette_score(matrix, labels, sample_size=min(1000, len(students)), random_state=42)
        )
        clustering.append({"k": k, "silhouette": silhouette, "inertia": float(model.inertia_)})
        candidates.append((silhouette, model))
    if not candidates:
        raise ValueError("Could not select a valid clustering model.")
    _, cluster_model = max(candidates, key=lambda item: item[0])
    user_features = [
        pair_features(users[row.user1_id], users[row.user2_id]) for row in pairs.itertuples()
    ]
    project_vectors = [
        project_features(users[row.user_id], project_map[row.project_id])
        for row in project_pairs.itertuples()
    ]
    user_model, user_report = train_classifier(pairs, user_features, USER_FEATURES)
    project_model, project_report = train_classifier(
        project_pairs, project_vectors, PROJECT_FEATURES, True
    )
    metadata = {
        "schema_version": 2,
        "seed": 42,
        "synthetic": synthetic,
        "label_sources": sources_of_labels,
        "dependencies": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        "data_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sources.items()
        },
        "students": len(students),
        "projects": len(projects),
        "cluster_selection": "Highest silhouette among k=2..10; no preset cluster labels",
        "selected_k": int(cluster_model.n_clusters),
        "cluster_candidates": clustering,
        "user_classifier": user_report,
        "project_classifier": project_report,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "metadata": metadata,
        "vectorizer": vectorizer,
        "clusters": cluster_model,
        "users": user_model,
        "projects": project_model,
        "user_features": USER_FEATURES,
        "project_features": PROJECT_FEATURES,
    }
    joblib.dump(bundle, output_dir / "recommender.joblib", compress=3)
    evaluation = output_dir.parent / "evaluation"
    evaluation.mkdir(parents=True, exist_ok=True)
    (evaluation / "metrics.json").write_text(json.dumps(metadata, indent=2), encoding="utf8")
    print(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "dataset")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "ml/models")
    parser.add_argument("--format", choices=["xlsx", "csv"], default="xlsx")
    args = parser.parse_args()
    train(args.data_dir, args.output_dir, args.format)
