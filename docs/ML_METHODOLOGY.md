# Real-data ML methodology

This document replaces the synthetic-pair experiment. The official title remains **ConnectAI: AI/ML-Based Social Connection Recommendation Platform**.

## Question and defensible target

We ask: based on technologies someone has used, what languages might they want to use next, and which people offer a reciprocal learning opportunity?

The original Stack Overflow Developer Survey 2024 contains actual self-reported `LanguageWantToWorkWith` answers. Each selected language is 1; each unselected language in an answered multi-select response is 0. This means selected/not selected, not compatible/incompatible. An entirely unanswered target is excluded. We do not create person-pair labels, pretend people know one another, or train on application/presentation accounts.

The survey question includes continuing technologies already used; desired does not necessarily mean new learning. People can explicitly enter their own interests, which are never overwritten by model output.

## Source and field selection

The publisher's original release contains 65,437 responses and 114 columns. We use current languages, databases, web frameworks, cloud platforms, coding years and desired languages because they directly describe technical activity/preferences. Names, contact information, gender, salary, country and application-domain labels are not features. See [source/license/checksum](../dataset/README.md) and [exact field mapping](../README.md#2-original-dataset-and-profile-attributes).

55,752 responses have an observed desired-language answer and some current technology input. Missing-target and no-current-technology exclusion counts overlap. There are 1,105 repeated normalized input rows; these are grouped, not split across evaluation partitions.

## Preprocessing, in order

1. Verify the raw CSV against the publisher's Git LFS SHA-256; preserve unchanged bytes.
2. Validate required columns and unique/nonmissing respondent IDs. CSV and Excel reading share this validation.
3. Treat actual nulls and missing markers as unanswered. Never manufacture source corruption.
4. Split multi-select fields at semicolons; trim whitespace, casefold, deduplicate, normalize documented aliases. Preserve punctuation in C++, C#, HTML/CSS and Node.js.
5. Parse YearsCode. `Less than 1 year` becomes 0.5; `More than 50 years` becomes 51, a documented approximation. Invalid/non-finite/out-of-range values become missing in ingestion. The API rejects invalid user numbers.
6. Exclude missing target answers. Do not substitute arbitrary negative targets.
7. Hash normalized input profiles into groups. Split groups approximately 70/30 into outer training/test using seed 42. Split only the training portion for internal validation using seed 43. Exact respondent counts are in [results](RESULTS.md).
8. Fit a binary technology vocabulary and coding-years median **on training data only**. Use the learned encoder unchanged at validation, test and inference. Unknown technologies are ignored by the learned vocabulary and exposed in profile-quality information.
9. Keep an explicit missing flag for each input field. Empty categorical lists mean unknown, not proven absence of skill. Numeric missingness gets the training median plus an indicator.
10. Select up to 16 frequent desired-language labels with at least 100 positive training examples. This is a fixed, training-only scope rule. Other target languages are outside this evaluation.

`ml/survey.py` is the shared contract. No synthetic-data generator is part of the supported pipeline.

## Outer 70:30 protocol and final refit

Of 55,752 eligible original survey responses, 38,993 are training and 16,759 are test. The ratio is applied to identical-input groups, so row percentages are 69.94%/30.06%. Group overlap is zero.

The training portion alone is divided into 31,228 internal fitting rows and 7,765 internal validation rows. Vocabulary, imputation and candidate models learn only from internal fitting rows during selection. Target-language scope is selected there too. Validation chooses k, forest settings and decision thresholds; it never includes the outer test rows.

Once those choices are locked, a fresh encoder, K-Means and Random Forest are fitted on **all 38,993 outer training rows**. The final encoder can use every training row, but no test row. Final test results come from this refitted model. Baseline prevalence is also recomputed on all training rows, keeping its validation-chosen threshold fixed. The saved bundle records this protocol and final fit count; tests check each saved forest tree used that count.

Five presentation accounts and all new website registrations are excluded from all survey partitions. They are stored in MongoDB and only consume saved models for inference. The pipeline reads the verified survey file, not the live account database.

## K-Means: unsupervised learning

K-Means repeatedly assigns each vector to a nearby centre and updates centres to reduce within-group squared distance. Here it receives L2-normalized binary current-technology vectors. Coding years and missing flags are excluded from clustering so they do not create artificial experience/missingness groups. Cluster numbers have no predefined domain labels.

We fit k = 2, 3, 4, 5, 6, 8 and 10 on training rows using k-means++, n_init=10, max_iter=300, random_state=42. We choose the highest validation silhouette on a fixed-seed sample of up to 1,500 rows; ties prefer smaller k. Inertia is plotted as an elbow diagnostic, not claimed as a second independent selection rule.

Selected k=2; internal-validation silhouette 0.0700; test silhouette 0.0611. This is **weak separation**, not evidence of clear expert categories. Discovery searches nearby groups and permits observed reciprocal/technology overlaps across groups.

## Random Forest: supervised learning

A decision tree asks feature questions and reaches a leaf containing observed answers. A forest fits many randomized trees and averages their estimated probabilities. Our multi-output classifier predicts whether each supported language was selected in a respondent's actual desired-language answer.

Inputs: current technology indicators, coding years and missing flags. Targets: actual desired-language selections. Desired-language fields are never passed as RF input, preventing direct target leakage.

We compare 80/160 trees, depth 12/20, and minimum leaf sizes 5/15 in the five declared combinations. Each candidate uses `max_features=sqrt` and seed 42. A global threshold is chosen from 0.25, 0.35, 0.45, 0.50, 0.55, 0.65 using validation micro F1. Selected: 160 trees, depth 20, leaf size 5, threshold 0.35. No test performance determines selection.

The measured learning curve refits preprocessing/model using 10%, 25%, 50% and 100% of internal fitting groups, inside the outer 70%. Internal validation remains fixed; outer test rows are not used in the curve. Random Forest has no epochs or gradient-descent loss; we do not invent such charts.

## Basic evaluation vocabulary

| Quantity | Meaning in this experiment |
|---|---|
| TP | Language was selected; model predicts selected |
| TN | Language was not selected; model predicts not selected |
| FP | Model predicts selected, but respondent did not select it |
| FN | Respondent selected it, but model misses it |
| Correct / wrong | TP+TN / FP+FN, across person-language decisions |
| Accuracy | Correct / all binary decisions; many negatives can inflate it |
| Precision | TP / (TP+FP): how often a predicted selection is right |
| Recall | TP / (TP+FN): how many actual selections were found |
| F1 | Harmonic mean of precision and recall; micro aggregates decisions |
| Macro F1 | Average F1 across target languages, including less common ones |
| Exact-profile accuracy | All 16 language decisions right for the same respondent |
| MSE | Mean squared difference between probability and actual 0/1 answer |
| RMSE | Square root of probability MSE; lower is better |
| Silhouette | Cluster cohesion/separation, roughly −1 to 1; near zero indicates overlap |
| Inertia | Within-cluster squared distance; decreases as k increases |

MSE/RMSE are valid here because they compare **probabilities to binary outcomes**, not arbitrary class numbers. RF probabilities are estimates, not proven calibrated probabilities. We do not reinterpret them as social-success confidence.

Compare both baselines: training-label prevalence and predicting continuation of current languages. RF test micro F1=0.6969 versus continuation=0.7051; RF probability MSE=0.1141 versus continuation=0.1580. The forest does not beat every baseline on every metric.

## Incomplete and irregular records

Naturally incomplete test records are evaluated separately from complete records. These groups have different label distributions, so this comparison alone does not show that missingness causes a metric change.

A separate stress experiment masks 0%, 10%, 30%, 50% and 100% of input fields, keeping test labels unchanged. At each rate we report coverage, abstentions and performance only on supported rows. This avoids hiding the cost of refusing predictions. At 100% masking, all 16,759 profiles abstain; no accuracy/F1 is claimed for zero predictions.

Constructed parser tests cover nulls, duplicate/case variants, aliases, negative years, nonnumeric values, infinity, missing schemas and unknown technology names. They are clearly labelled tests, not original survey rows. API validation rejects malformed inputs, while offline ingestion records invalid values as missing for an audit.

## Live reciprocal discovery and explanations

An example: A has used Python and wants JavaScript; B has used JavaScript and wants Python. Explanations show both intersections. Having used a technology does not establish proficiency or teaching ability; users discuss that themselves.

Discovery score = 100 × (0.35 × A-interest coverage by B + 0.25 × B-interest coverage by A + 0.25 × current-technology Jaccard similarity + 0.15 × learned preference affinity).

These weights are transparent product choices, **not labels used to train RF** and not statistically optimized social-ranking results. Learned affinity averages A's predicted preference for B's listed languages, with unsupported targets contributing zero. This creates an explicit scope limitation. Candidate retrieval uses K-Means and expands for observed comparisons. Existing connections, ignored people and inactive accounts are excluded.

Explanations come from current profiles. Model-predicted interests are labelled separately from stated interests. Missing/unsupported source technology profiles receive no ML score. Candidate profiles without supported current technologies are omitted. The UI shows input completeness, which is not model confidence.

Project suggestions use observed requirement coverage. Activity suggestions use separate community interests/location. Neither is falsely presented as a supervised outcome model.

## Reproducibility and measurement scope

Run `python -m ml.train --download` in Codespaces. The bundle persists the fitted encoder, clusters, classifier, targets, threshold, provenance and dependency versions. Report JSON stores parameter trials, split sizes, source audit, test/baseline metrics, curves and robustness results. A local split manifest records IDs/groups; source-derived rows are available as CSV/Excel through `python -m ml.export_data`.

This is one fixed grouped holdout, not repeated cross-validation or a causal user study. The self-selected survey is not representative of all students/community members. We cannot evaluate successful social connections from it. The whole ranking needs consented real interaction outcomes, user feedback and a separate evaluation protocol before stronger claims.
