# Dataset design

The original Phase 1 dataset design has been superseded by the implemented, provenance-tracked four-table dataset.

See [ML methodology and dataset card](../ML_METHODOLOGY.md), [actual results](../RESULTS.md) and [the reproducible generator](../../dataset/generate_synthetic_datasets.py).

The active artifacts are `students`, `projects`, `matching_data` and `project_matches`, each in CSV and Excel. The active model is `ml/models/recommender.joblib`. Earlier separate clustering/classifier artifacts remain only in Git history.
