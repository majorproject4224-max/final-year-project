"""Real-data experiment; run python -m ml.train_survey --download in Codespaces.

Supervised target: respondents' desired languages, NOT successful friendships.
"""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import time

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_squared_error, precision_score, recall_score, silhouette_score
from sklearn.model_selection import GroupShuffleSplit

from ml.download_survey import ROOT, FILES, checksum, download
from ml.survey import FIELD_MAP, TARGET, SurveyEncoder, positive_probabilities, read_survey

SEED = 42
REPORT_DIR = ROOT / "ml" / "evaluation" / "survey2024"
MODEL_PATH = ROOT / "ml" / "models" / "survey-recommender.joblib"


def save_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def grouped_partition(rows, test_size, seed, names):
    groups = np.array([r["group"] for r in rows])
    left, right = next(GroupShuffleSplit(
        n_splits=1, test_size=test_size, random_state=seed
    ).split(rows, groups=groups))
    result = {name: [rows[i] for i in indices] for name, indices in zip(names, (left, right))}
    assert not {r["group"] for r in result[names[0]]} & {r["group"] for r in result[names[1]]}
    return result


def split_rows(rows):
    """Outer 70:30 split by identical-input group; website accounts never enter here."""
    return grouped_partition(rows, 0.3, SEED, ("train", "test"))


def tuning_rows(training_rows):
    """Choose settings inside the outer 70%; never inspect the outer test set."""
    return grouped_partition(training_rows, 0.2, SEED + 1, ("fit", "validation"))


def target_matrix(rows, labels):
    return np.array([[int(label in r["wanted_languages"]) for label in labels] for r in rows], dtype=np.uint8)


def evaluate(y, probability, threshold=0.5):
    predicted = (probability >= threshold).astype(np.uint8)
    tn, fp, fn, tp = confusion_matrix(y.ravel(), predicted.ravel(), labels=[0, 1]).ravel()
    correct, wrong = int(tp + tn), int(fp + fn)
    mse = float(mean_squared_error(y, probability))
    return {
        "per_label_accuracy": correct / (correct + wrong),
        "exact_profile_accuracy": float(accuracy_score(y, predicted)),
        "precision_micro": float(precision_score(y, predicted, average="micro", zero_division=0)),
        "recall_micro": float(recall_score(y, predicted, average="micro", zero_division=0)),
        "f1_micro": float(f1_score(y, predicted, average="micro", zero_division=0)),
        "f1_macro": float(f1_score(y, predicted, average="macro", zero_division=0)),
        "probability_mse": mse, "probability_rmse": float(np.sqrt(mse)),
        "correct": correct, "wrong": wrong, "correct_wrong_ratio": correct / wrong if wrong else None,
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "positive_label_rate": float(y.mean()), "respondents": len(y), "binary_decisions": int(y.size), "threshold": threshold,
    }


def forest(parameters):
    return RandomForestClassifier(**parameters, random_state=SEED, n_jobs=2)


def select_threshold(y, probability):
    scores = [{"threshold": t, "f1_micro": evaluate(y, probability, t)["f1_micro"]} for t in [0.25, 0.35, 0.45, 0.5, 0.55, 0.65]]
    return max(scores, key=lambda r: (r["f1_micro"], r["threshold"]))["threshold"], scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--max-rows", type=int, help="Diagnostic subset only; output explicitly labelled.")
    args = parser.parse_args()
    raw_dir = ROOT / "dataset" / "raw" / "stackoverflow2024"
    if args.download:
        download(raw_dir)
    raw_path = raw_dir / "results.csv"
    if not raw_path.exists() or checksum(raw_path) != FILES["results.csv"]:
        raise SystemExit("Original data is absent/unverified. Run python -m ml.download_survey first.")
    started = time.perf_counter()
    rows, audit, preview = read_survey(raw_path)
    if args.max_rows:
        if args.max_rows < 1000:
            raise SystemExit("Use at least 1000 real rows for a diagnostic run.")
        rows = [rows[i] for i in np.random.default_rng(SEED).permutation(len(rows))[:args.max_rows]]
    save_json(REPORT_DIR / "data_audit.json", audit)
    save_json(REPORT_DIR / "preprocessing_examples.json", preview)
    print(f"Source {audit['raw_rows']} real responses; {len(rows)} eligible rows in run.", flush=True)
    outer_parts = split_rows(rows)
    tuning = tuning_rows(outer_parts["train"])
    parts = {"train": tuning["fit"], "validation": tuning["validation"]}
    selection_counts = {name: len(part) for name, part in tuning.items()}
    print(f"Outer train/test: {len(outer_parts['train'])}/{len(outer_parts['test'])}; internal fit/validation: {selection_counts}", flush=True)
    encoder = SurveyEncoder().fit(parts["train"])
    x = {name: encoder.transform(values) for name, values in parts.items()}
    z = {name: encoder.cluster_matrix(values) for name, values in parts.items()}
    counts = {}
    for row in parts["train"]:
        for label in row["wanted_languages"]:
            counts[label] = counts.get(label, 0) + 1
    # Fixed scope rule, chosen before examining validation/test outcomes.
    labels = sorted(counts, key=lambda label: (-counts[label], label))[:16]
    labels = [label for label in labels if 100 <= counts[label] < len(parts["train"])]
    if len(labels) < 2:
        raise ValueError("Insufficient observed target support.")
    y = {name: target_matrix(values, labels) for name, values in parts.items()}
    save_json(REPORT_DIR / "split_manifest.json", {name: {"response_ids": [r["response_id"] for r in part], "groups": sorted({r["group"] for r in part})} for name, part in outer_parts.items()})

    save_json(REPORT_DIR / "tuning_manifest.json", {name: {"response_ids": [r["response_id"] for r in part], "groups": sorted({r["group"] for r in part})} for name, part in tuning.items()})

    cluster_trials, cluster_models = [], []
    valid_z = z["validation"][np.asarray(z["validation"].getnnz(axis=1)).ravel() > 0]
    for k in [2, 3, 4, 5, 6, 8, 10]:
        model = KMeans(n_clusters=k, n_init=10, random_state=SEED, max_iter=300).fit(z["train"])
        assignments = model.predict(valid_z)
        score = float(silhouette_score(valid_z, assignments, sample_size=min(1500, len(assignments)), random_state=SEED)) if len(set(assignments)) > 1 else -1.0
        cluster_trials.append({"k": k, "validation_silhouette": score, "train_inertia": float(model.inertia_), "iterations": int(model.n_iter_)})
        cluster_models.append(model)
        print(f"K-Means k={k}, validation silhouette={score:.4f}", flush=True)
    best_cluster = max(range(len(cluster_trials)), key=lambda i: cluster_trials[i]["validation_silhouette"])
    clusters = cluster_models[best_cluster]

    candidates = [
        {"n_estimators": 80, "max_depth": 12, "min_samples_leaf": 5},
        {"n_estimators": 160, "max_depth": 12, "min_samples_leaf": 5},
        {"n_estimators": 80, "max_depth": 20, "min_samples_leaf": 5},
        {"n_estimators": 160, "max_depth": 20, "min_samples_leaf": 5},
        {"n_estimators": 160, "max_depth": 20, "min_samples_leaf": 15},
    ]
    best_model, best_score, trials = None, -1, []
    for parameters in candidates:
        tick = time.perf_counter()
        model = forest(parameters).fit(x["train"], y["train"])
        probability = positive_probabilities(model, x["validation"])
        threshold, threshold_trials = select_threshold(y["validation"], probability)
        metrics = evaluate(y["validation"], probability, threshold)
        trial = {"parameters": parameters, "validation": metrics, "threshold_search": threshold_trials, "fit_and_validation_seconds": round(time.perf_counter() - tick, 3)}
        trials.append(trial)
        print(f"RF {parameters}: validation F1={metrics['f1_micro']:.4f}, threshold={threshold}", flush=True)
        if metrics["f1_micro"] > best_score:
            best_model, best_score, best_trial = model, metrics["f1_micro"], trial
    threshold, parameters = best_trial["validation"]["threshold"], best_trial["parameters"]
    # Sample-size curves, not neural-network epochs. Refit preprocessing per subset.
    learning_curve = []
    for fraction in [0.1, 0.25, 0.5, 1.0]:
        if fraction == 1:
            partial_encoder, model, subset = encoder, best_model, parts["train"]
        else:
            groups = sorted({r["group"] for r in parts["train"]})
            np.random.default_rng(SEED).shuffle(groups)
            chosen = set(groups[:max(1, int(len(groups) * fraction))])
            subset = [r for r in parts["train"] if r["group"] in chosen]
            partial_encoder = SurveyEncoder().fit(subset)
            model = forest(parameters).fit(partial_encoder.transform(subset), target_matrix(subset, labels))
        a = evaluate(target_matrix(subset, labels), positive_probabilities(model, partial_encoder.transform(subset)), threshold)
        b = evaluate(y["validation"], positive_probabilities(model, partial_encoder.transform(parts["validation"])), threshold)
        learning_curve.append({"train_rows": len(subset), "train_f1": a["f1_micro"], "validation_f1": b["f1_micro"]})

    # Lock every selection before touching the outer test data.
    selection_prevalence = y["train"].mean(axis=0)
    baseline_threshold, _ = select_threshold(y["validation"], np.tile(selection_prevalence, (len(parts["validation"]), 1)))
    # Refit preprocessing and both final models on ALL of the outer 70%.
    parts = outer_parts
    encoder = SurveyEncoder().fit(parts["train"])
    x = {name: encoder.transform(values) for name, values in parts.items()}
    z = {name: encoder.cluster_matrix(values) for name, values in parts.items()}
    y = {name: target_matrix(values, labels) for name, values in parts.items()}
    best_model = forest(parameters).fit(x["train"], y["train"])
    clusters = KMeans(n_clusters=cluster_trials[best_cluster]["k"], n_init=10, random_state=SEED, max_iter=300).fit(z["train"])
    counts = {label: int(y["train"][:, i].sum()) for i, label in enumerate(labels)}
    print(f"Final models refitted on all {len(parts['train'])} training responses; evaluating untouched 30% test portion.", flush=True)

    probability = positive_probabilities(best_model, x["test"])
    test_metrics = evaluate(y["test"], probability, threshold)
    train_metrics = evaluate(y["train"], positive_probabilities(best_model, x["train"]), threshold)
    prevalence = y["train"].mean(axis=0)
    baselines = {
        "training_prevalence": evaluate(y["test"], np.tile(prevalence, (len(parts["test"]), 1)), baseline_threshold),
        "continue_current_languages": evaluate(y["test"], np.array([[float(label in row["languages"]) for label in labels] for row in parts["test"]])),
    }
    per_label = [{"language": label, "support": int(y["test"][:, i].sum()), "f1": float(f1_score(y["test"][:, i], probability[:, i] >= threshold, zero_division=0)), "mse": float(mean_squared_error(y["test"][:, i], probability[:, i]))} for i, label in enumerate(labels)]
    robustness = []
    for rate in [0.0, 0.1, 0.3, 0.5, 1.0]:
        rng, masked = np.random.default_rng(SEED), []
        for row in parts["test"]:
            copy = dict(row)
            for field in FIELD_MAP:
                if rng.random() < rate:
                    copy[field] = []
            if rng.random() < rate:
                copy["years_code"] = None
            masked.append(copy)
        supported = np.array([encoder.supported(row) for row in masked])
        item = {"artificial_field_mask_rate": rate, "supported_rows": int(supported.sum()), "abstained_rows": int((~supported).sum()), "coverage": float(supported.mean()), "metrics_supported_only": None}
        if supported.any():
            item["metrics_supported_only"] = evaluate(y["test"][supported], positive_probabilities(best_model, encoder.transform([r for r, valid in zip(masked, supported) if valid])), threshold)
        robustness.append(item)
    missing_fields = np.array([sum(not row[f] for f in FIELD_MAP) + int(row["years_code"] is None) for row in parts["test"]])
    quality_bands = [{"group": name, "rows": int(mask.sum()), "metrics": evaluate(y["test"][mask], probability[mask], threshold) if mask.any() else None} for name, mask in [("complete_inputs", missing_fields == 0), ("naturally_missing_inputs", missing_fields > 0)]]
    test_z = z["test"][np.asarray(z["test"].getnnz(axis=1)).ravel() > 0]
    assignments = clusters.predict(test_z)
    test_silhouette = float(silhouette_score(test_z, assignments, sample_size=min(1500, len(assignments)), random_state=SEED)) if len(set(assignments)) > 1 else None
    metadata = {
        "split_protocol": {"train_fraction": 0.7, "test_fraction": 0.3, "grouped": True, "internal_validation_fraction_of_train": 0.2, "final_refit_on_all_training_rows": True, "final_fit_rows": len(parts["train"]), "website_accounts_included": False},
        "schema_version": 3, "synthetic": False, "source": "Stack Overflow Developer Survey 2024",
        "source_sha256": FILES["results.csv"], "target": TARGET,
        "task": "Self-reported desired programming languages; not interpersonal compatibility",
        "run_kind": "diagnostic_subset" if args.max_rows else "full_verified_release",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(), "random_state": SEED,
        "dependencies": {name: importlib.metadata.version(name) for name in ["scikit-learn", "pandas", "numpy", "scipy", "joblib"]},
    }
    report = {"metadata": metadata, "audit": audit,
        "splits": {name: {"rows": len(part), "unique_groups": len({r['group'] for r in part})} for name, part in parts.items()},
        "validation_setup": {"inside_training_only": True, "fit_rows": selection_counts["fit"], "validation_rows": selection_counts["validation"], "final_refit_rows": len(parts["train"]), "learning_curve_scope": "Subsets of the internal fit portion, evaluated on internal validation; outer test unused."},
        "group_overlap": 0, "target_labels": labels, "target_train_support": {label: counts[label] for label in labels},
        "preprocessing": {"numeric_train_median": float(encoder.imputer_.statistics_[0]), "technology_feature_count": len(encoder.vocabulary_.vocabulary_), "feature_count": x['train'].shape[1]},
        "clustering": {"selected_k": clusters.n_clusters, "selection": "Highest internal-validation silhouette within the 70% training portion; then refit all 70%; ties prefer smaller k", "candidates": cluster_trials, "test_silhouette": test_silhouette},
        "parameter_search": trials, "selected_parameters": {**parameters, "threshold": threshold, "random_state": SEED, "max_features": "sqrt"},
        "train": train_metrics, "validation": best_trial["validation"], "test": test_metrics,
        "baselines": baselines, "per_label": per_label, "learning_curve": learning_curve,
        "natural_missingness_evaluation": quality_bands, "artificial_masking_stress_test": robustness,
        "feature_importance": sorted([{"feature": str(n), "importance": float(v)} for n, v in zip(encoder.feature_names(), best_model.feature_importances_)], key=lambda r: -r["importance"])[:20],
        "duration_seconds": round(time.perf_counter() - started, 2),
        "limitations": ["Self-selected, self-reported 2024 survey; not a university cohort.", "Missing desired-language answers excluded, never labelled negative.", "Only training-selected frequent target languages evaluated.", "Metrics measure language preferences, not successful friendships/teams.", "Live ranking weights are design choices needing a user study.", "Technology use does not establish teaching ability."]}
    best_model.n_jobs = 1
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"metadata": metadata, "encoder": encoder, "clusters": clusters, "preferences": best_model, "labels": labels, "threshold": threshold}, MODEL_PATH, compress=3)
    report["model_sha256"] = checksum(MODEL_PATH)
    save_json(REPORT_DIR / "metrics.json", report)
    save_json(ROOT / "dataset" / "survey_profile_options.json", {**encoder.options(), "wanted_languages": encoder.options()["languages"], "source": metadata["source"]})
    from ml.report import generate_report
    generate_report(report, preview)
    print(json.dumps({"test": test_metrics, "model": str(MODEL_PATH), "seconds": report["duration_seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
