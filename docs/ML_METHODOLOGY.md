# ML methodology and dataset card

## Purpose and boundaries

The system helps students discover potential connections, projects and teammates. It combines **unsupervised candidate discovery** with **supervised ranking**. Neither model establishes whether two real people will collaborate well.

The current development dataset contains 420 fictional student profiles, 84 project scenarios, 6,000 student pairs and 6,000 student–project pairs. Every row records synthetic provenance. No real university data, scraped student profiles or private résumé data is included.

## Reproducible data design

`dataset/generate_synthetic_datasets.py` uses random seed 4224. Attributes are sampled from seven documented, overlapping technical skill pools. One third of profiles mix skills and interests from another pool. The project set varies twelve curated campus/project scenarios across experience and time requirements.

This is structured synthetic scenario generation, not random compatibility labels. Names are “Demo Student …”. All four tables are exported to both CSV and formatted Excel with a header, filter and frozen top row.

Tables:

- `students`: user ID, fictional name, branch/year, skills, interests, domain, experience, completed-project count, preferred type, hours and source.
- `projects`: ID/title, domain, required skills/interests/experience, team size, type, hours and source.
- `matching_data`: two student IDs, six auditable comparison features, rubric score, compatibility label and label source.
- `project_matches`: student/project IDs, six comparisons, rubric score, label and source.

Academic year and completed-project count are stored for profile context; they are not automatically added as classifier features without evidence that they predict useful outcomes. Previous collaboration/history is absent from the synthetic feature set because no such evidence exists.

## Label source

Student-pair rubric:

```text
score = .30 × skill Jaccard
      + .25 × interest Jaccard
      + .10 × same domain
      + .10 × experience compatibility
      + .10 × same preferred project type
      + .15 × availability compatibility

label = 1 only if score ≥ .48,
                  skill Jaccard ≥ .15,
                  and interest Jaccard > 0
```

Student–project rubric:

```text
score = .45 × required-skill coverage
      + .15 × interest Jaccard
      + .10 × same domain
      + .10 × experience fit
      + .10 × project-type match
      + .10 × availability fit

label = 1 only if score ≥ .58,
                  skill coverage ≥ .50,
                  and availability fit ≥ .50
```

The labels are deterministic judgments under these explicit development assumptions. They are **not observed collaboration outcomes**. The Random Forest learns these labels; the inference service does not calculate a rubric percentage and present it as ML.

## Preprocessing and features

Shared functions in `ml/features.py` are used during data preparation, training and API inference.

1. Pandas loads Excel or CSV; required columns and duplicate IDs are validated.
2. Empty/missing values are handled explicitly. Required profile attributes and numeric bounds are validated.
3. Tag normalization uses Unicode normalization, trimming, case folding, repeated-space cleanup, alias mapping, deduplication and sorting.
4. Aliases include ML → machine learning and JS → javascript. Aliases are a documented vocabulary map, not model cluster labels. Different technologies such as SQL and MySQL remain distinct unless explicitly mapped.
5. Pair references, binary labels, provenance and duplicate/reversed student pairs are checked.
6. Training recomputes features from raw profiles rather than trusting the pair table's feature/audit columns.
7. The supervised pipeline contains a median imputer fitted only to training features. Numeric comparisons already lie in [0,1]; Random Forest does not require scaling.
8. TF-IDF normalizes clustering vectors; no arbitrary numeric scaling is added.

For sets A and B, Jaccard = |A ∩ B| / |A ∪ B|, with empty comparisons returning zero.

| Student–student feature | Definition |
|---|---|
| skill_similarity | Jaccard of normalized skill sets |
| interest_similarity | Jaccard of normalized interest sets |
| domain_similarity | 1 for equal nonempty normalized domains |
| experience_compatibility | 1 − absolute experience-rank gap / 2 |
| project_type_match | 1 for equal nonempty normalized preferred types |
| availability_compatibility | smaller weekly availability / larger availability |

| Student–project feature | Definition |
|---|---|
| skill_coverage | matched required skills / number of required skills |
| interest_similarity | student/project interest Jaccard |
| domain_similarity | equal nonempty normalized domains |
| experience_fit | 1 − max(0, required rank − student rank) / 2 |
| project_type_match | preferred type equals offered type |
| availability_fit | min(1, student hours / requested hours) |

Coverage is directional: possessing two of a project's four required skills gives 0.5 regardless of unrelated extra skills. Experience uses Beginner=0, Intermediate=1, Advanced=2. The profile form collects hours to avoid inventing availability.

## K-Means

Clustering uses TF-IDF over whole normalized skill and interest tags such as `skill_machine_learning`. A saved vectorizer preserves the training vocabulary and transformation. Domain category labels are not given to K-Means.

For k from 2 to 10, train K-Means with seed 42 and n_init=10. Record silhouette and inertia. Select the highest silhouette. These are internal clustering diagnostics, not an external accuracy score.

At inference, use the nearest two clusters and expand candidates when tags overlap, allowing multidisciplinary matches. Rank at most 200 candidates from a bounded pool of 2,000 database records. The UI returns up to 12 candidates meeting the classifier’s 0.5 decision threshold, rather than recommending a model-predicted negative. An empty result points to manual browsing. This is suitable for a demonstration, not an exhaustive large-campus index. Unknown-only profile vocabulary produces an honest empty result.

## Random Forest

There are two classifiers: student–student and student–project. The latter is also used for project-owner teammate recommendations, comparing each candidate **to the actual project requirements**.

Each uses 180 trees, maximum depth 10, minimum leaf size 3, balanced class weights, seed 42 and one CPU thread. Hyperparameters are fixed before evaluation. This model handles nonlinear feature combinations and bounded structured data, and its feature importances aid inspection. They do not establish causation.

## Evaluation design

Randomly splitting pair rows can put the same student in training and testing. We instead partition student IDs first (75%/25%), then keep only pairs whose endpoints both belong to the corresponding partition. Cross-partition pairs are excluded.

For student–project classification, both student IDs and project IDs are separately disjoint. The held-out set is not used to fit the Random Forest or its imputer. Both labels must be present or training stops.

Report accuracy, precision, recall, F1, confusion matrices, training/test counts, class prevalence and two baselines: always-majority and a skill-similarity/coverage threshold. Accuracy alone is misleading for imbalanced labels.

Ranking precision/recall/NDCG at 5 is calculated only within held-out labeled candidates per query, for queries with at least two candidates and a positive label. Precision divides by the number actually retrieved if fewer than five exist. This is **not a full-catalog, end-to-end retrieval evaluation**.

K-Means and TF-IDF are fitted on the full unlabeled profile table for descriptive clustering. Their output is not a supervised feature. Consequently the reported classifier holdout metrics remain independent of clustering, but do not evaluate the full candidate-generation pipeline on unseen people. A future external evaluation must fit candidate-generation artifacts only on its training population.

A single fixed entity split is used; cross-validation and confidence intervals are not claimed. Future work should use repeated entity/group-disjoint splits when real labels are sufficient. Related synthetic project scenarios may appear on both sides despite disjoint IDs, limiting generalization claims.

## Offline training and inference

```bash
python dataset/generate_synthetic_datasets.py
python ml/train.py
# Or train from equivalent CSV tables:
python ml/train.py --format csv
```

Outputs:

- `ml/models/recommender.joblib`: vectorizer, K-Means, two RF pipelines, feature lists and metadata.
- `ml/evaluation/metrics.json`: actual measured metrics, versions and input-file hashes.

The bundle is generated in GitHub Actions and committed for deployment. Input hashes identify the exact training workbooks. Spreadsheet container timestamps may vary between regeneration runs even when rows and seeds match, so reproducibility means identical data values and metrics under the pinned environment, not necessarily byte-identical XLSX files.

The API loads artifacts once per process and checks schema and scikit-learn version. Missing/incompatible artifacts return HTTP 503. It never trains on a recommendation request or invents fallback percentages. Only trusted, repository-generated Joblib files should be loaded.

## Explanations and cold start

Reasons list actual shared skills/interests, required skills matched/missing, domain/type agreement and sufficient hours. These are **feature comparisons**, not SHAP explanations or claims that a specific reason caused the score.

New students can receive content-based recommendations without interaction history after completing skills/interests. An incomplete profile or unsupported vocabulary produces guidance to add information or browse manually.

## Replacing synthetic labels

The app records genuine saved/ignored/view interactions, applications, membership decisions and feedback from verified shared completed projects. A click, ignored card or accepted invitation is not automatically a positive/negative compatibility label.

Before training on real data: obtain consent, define a stable outcome and observation window, remove direct identifiers from exported training data, distinguish unobserved outcomes from negatives, review class balance, use temporal/entity separation and retain provenance. Start with explicitly consented completed-project collaboration ratings, with a documented threshold and human review. Train offline and compare to baselines before publishing an updated artifact. No online retraining occurs now.

## Limitations

- All current labels come from an explicit synthetic rubric. Perfect scores can reflect learning its simple rules.
- The generator's technical pools influence apparent cluster structure. The resulting seven groups are not evidence of seven natural groups at a university.
- Sparse held-out positives and reused scenario families restrict conclusions.
- Shared technical interests do not measure communication, reliability, teamwork or inclusion.
- Match scores are uncalibrated model outputs, not established success probabilities.
- Vocabulary coverage and candidate caps can omit relevant students.
- No real-user study, fairness study, probability calibration, longitudinal evaluation or production load test has been performed.

These limitations belong in the viva/report, next to the metrics.
