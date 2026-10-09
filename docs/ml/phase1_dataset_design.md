# connecT AI Dataset and ML Evaluation

## Data Provenance

The prototype Excel data is synthetic, reproducible, and must not be described as real student data. `dataset/generate_synthetic_datasets.py` uses a fixed Python random seed to create fictional student profiles and student pairs. The names are demo-only fictional names; no real university records are included.

Files:

- `dataset/students.xlsx`: 1,000 synthetic student profiles.
- `dataset/matching_data.xlsx`: 1,500 unique student-pair rows.
- `ml/models/random_forest_compatibility.joblib`: supervised compatibility classifier.
- `ml/models/student_clusters.joblib`: vectorizer and K-Means model.
- `ml/evaluation/random_forest_metrics.json`: latest user-disjoint holdout metrics.
- `ml/evaluation/student_cluster_metrics.json`: candidate k silhouette scores and selected cluster count.

## Student Fields

The student dataset contains synthetic `user_id`, `student_name`, `branch`, `academic_year`, `skills`, `interests`, `domain`, `experience_level`, `projects_completed`, `preferred_project_type`, `city`, `availability_hours_per_week`, and `collaboration_style` values.

## Pair Features and Label

The matching dataset contains `user1_id`, `user2_id`, skill and interest Jaccard similarities, domain similarity, experience compatibility, previous collaboration, project similarity, an audit-only `compatibility_score_rule`, and `compatibility_label`.

The label is deterministic, not randomly assigned. A pair is labeled compatible when:

```text
0.34 * skill_similarity
+ 0.25 * interest_similarity
+ 0.16 * domain_similarity
+ 0.12 * experience_compatibility
+ 0.08 * project_similarity
+ 0.05 * previous_collaboration >= 0.52
```

`compatibility_score_rule` is excluded from model features to avoid direct target leakage. The model learns to reproduce this synthetic rule. Therefore, high held-out scores do not demonstrate that the model predicts actual team success.

Skill normalization trims whitespace, case-folds values, removes duplicates, and supports documented aliases such as `ML` to `machine learning`. The API normalizes profiles before persisting them and uses the same normalization in inference.

## Random Forest Evaluation

Training is implemented in `ml/train_compatibility_model.py`. The split is made by unique student IDs, not pair rows. A pair is retained only when both users fall entirely in the training partition or entirely in the test partition. This prevents the same student from appearing on both sides. Cross-partition pairs are excluded from that evaluation.

Latest recorded run:

- 1,500 total pair rows.
- 756 training users and 959 training pairs.
- 189 held-out users and 65 held-out pairs.
- 476 cross-partition pairs excluded.
- Held-out labels: 53 incompatible and 12 compatible.
- Accuracy: 1.0000; compatible-class F1: 1.0000; confusion matrix: `[[53, 0], [0, 12]]`.

This result is explicitly limited: only 65 synthetic held-out pairs were scored, and their labels come from the deterministic rule above. It is not a real-student performance estimate and should not be presented as model accuracy for deployment. The class supports are small and the synthetic personas are simplified.

## K-Means Evaluation

`ml/train_student_clusters.py` normalizes skills and interests, adds the profile domain as a token, applies TF-IDF, and evaluates K-Means for `k=2..10` (bounded by dataset size). It selects the candidate with the highest silhouette score; cluster names are not hard-coded.

For the checked-in synthetic dataset, the selected result is `k=6`, silhouette `0.524659`. The score list and cluster sizes are saved in `ml/evaluation/student_cluster_metrics.json`. These are profile groupings in the synthetic development set, not proof that six natural categories exist at a university.

The API assigns a profile to a cluster to narrow candidate users, then ranks candidates with the Random Forest. It exposes the cluster ID and candidate count for inspection. Cluster membership is not itself a compatibility probability.

## Project Recommendations

There is no separately trained student-to-project classifier yet because the current labeled dataset contains student pairs, not student-project outcomes. Project discovery therefore uses transparent skill coverage and domain matching. Project-owner teammate suggestions use the student-pair Random Forest score plus a separately visible required-skill coverage component. The API identifies these ranking methods instead of presenting project ranking as a trained project classifier.

## Reproducibility

From the repository root in WSL:

```bash
.venv/bin/python dataset/generate_synthetic_datasets.py
.venv/bin/python ml/train_student_clusters.py
.venv/bin/python ml/train_compatibility_model.py
```

Model fitting is offline. API requests load saved artifacts; they do not retrain models.

## Data Collection Needed for Valid Evaluation

A credible real-world model needs consented student profiles and outcomes such as accepted invitations, completed collaborations, or explicit post-project feedback. Labels should be defined before training, captured with consent, de-duplicated, and split by user or time to prevent leakage. Track class balance and compare the model against transparent baselines. Do not automatically retrain from unreviewed clicks or recommendation exposure.
