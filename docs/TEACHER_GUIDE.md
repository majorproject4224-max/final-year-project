# ConnectAI presentation: a simple walkthrough

Use GitHub Codespaces and the website. The title is **ConnectAI: AI/ML-Based Social Connection Recommendation Platform**.

## Start with this explanation

“ConnectAI helps people discover technology learning partners. We trained models using real anonymous Stack Overflow 2024 survey responses. We use 70% for training and 30% for testing. Our five website accounts and all new registrations are completely separate: they receive recommendations from the saved models.”

## 1. Show where the data came from

Open the [original publisher archive](https://github.com/StackExchange/Survey/tree/main/packages/archive/2024), then [our dataset card](../dataset/README.md). The source contains 65,437 real responses. The usable cohort contains 55,752 responses after excluding missing wanted-language answers and records without current technologies.

In the Codespace file explorer, open the cleaned CSV or download the Excel file under dataset/processed. The columns split and tuning_role show exactly which rows belong to training, testing and internal validation. These anonymous survey response IDs are not website account IDs.

## 2. Explain 70:30 using study material and an exam

| Part | Measured rows | Explanation |
|---|---:|---|
| Training, approximately 70% | 38,993 | Examples used to learn patterns |
| Testing, approximately 30% | 16,759 | Final exam on different responses |
| Five website accounts | 5 | Application users; outside both parts |

Duplicate cleaned inputs stay together, which makes row percentages slightly different from exactly 70:30. No identical-input group occurs in both parts.

Inside the 70%, we temporarily use 31,228 rows to fit candidate models and 7,765 for validation. Think of validation as a practice test to choose settings. Then the final models learn again from **all 38,993 training rows**. The outer 30% never chooses settings.

## 3. Show preprocessing

Open the README missing-values chart and [before/after snapshot](evidence/survey2024/02-preprocessing-examples.png).

- Python and python become the same value; duplicates and extra spaces are removed.
- JS becomes javascript through an explicit alias rule.
- Blank technology answers remain unknown, with missing-field indicators.
- Missing coding years use the training median, 11, with a missing indicator.
- A missing desired-language answer is excluded; we do not invent the correct answer.
- Negative/nonnumeric/infinite examples are deliberate parser tests. They are labelled separately from the original survey.

Explain that the encoder learns vocabulary and replacement values only from training data. The same saved encoder processes test data and website inputs.

## 4. Explain the two models

**K-Means:** “It groups profiles with similar technologies without being told category names.” It repeatedly assigns profiles to nearby centres and updates the centres. We tried 2, 3, 4, 5, 6, 8 and 10 groups. The selected value is 2. Test silhouette is 0.0611; near zero means these technology groups overlap.

**Random Forest:** “Many trees learn questions about current technologies and coding years. Their predictions are combined to estimate wanted languages.” Each training row has actual survey answers. A recorded selected language is 1 and an unselected language in an answered target is 0. Missing entire target answers are excluded.

The highlighted settings are 160 trees, maximum depth 20, minimum leaf size 5 and decision cutoff 0.35. These won among the settings we tried using internal validation, not the final test set.

## 5. Explain the results in ordinary language

| Measure | Result | What to say |
|---|---:|---|
| Correct / wrong | 226,278 / 41,866 | Number of right and wrong person-language decisions |
| Accuracy | 84.39% | Correct decisions divided by all decisions |
| Precision | 66.64% | How often a predicted wanted language was actually wanted |
| Recall | 73.04% | How many of the actually wanted languages were found |
| F1 | 0.6969 | A balance between precision and recall; higher is better |
| MSE / RMSE | 0.1141 / 0.3377 | Probability errors; lower is better |

Small teaching example, not a measured result: if 10 languages are predicted wanted and 8 are right, precision is 8/10. If the person actually wanted 12 and we found 8, recall is 8/12. F1 combines both. Here “micro” means counting all person-language decisions together.

MSE example: prediction 0.8, actual answer 1 gives error squared of 0.04. Average squared errors across the test set; take the square root to get RMSE.

The simple “continue current languages” rule gets F1 0.7051, compared with the forest at 0.6969. The forest has MSE 0.1141, compared with 0.1580. State both results. Accuracy alone can be misleading when many languages are not selected.

These are **wanted-language prediction results**, not a percentage of successful friendships. Exact whole-profile accuracy (18.32%) means every evaluated language decision was right for that person; it is a harder measure.

## 6. Read each chart

- **Missing values:** longer bars mean more unanswered original cells.
- **Parameter table:** green highlights the selected settings and measured internal-validation F1.
- **Learning curve:** right means more fitting rows; higher F1 is better. Blue uses fitting rows, green uses internal validation. A large gap can suggest overfitting. Random Forest does not train in neural-network epochs.
- **Confusion matrix:** diagonal cells are correct. Off-diagonal cells mean a wrongly suggested or missed language.
- **Cluster plot:** higher silhouette means more separate groups; near zero means overlap. Inertia is how spread out profiles are within groups.
- **Missing-input stress test:** deliberately hide fields and measure what changes. When all fields are hidden, all 16,759 test profiles receive no prediction. We ask for information instead of inventing a score.

[All measured figures with explanations](RESULTS.md).

## 7. Demonstrate the five website profiles

Open MongoDB in the Codespace sidebar, then connect_ai → profiles → Documents. Show the presentation profiles. This database stores live application records; it is not the 70:30 survey dataset.

Sign in with the privately supplied account details. Show recommendations and their explanations, connections, chat/file sharing, a project application and a community activity. Aarav and Priya already have a connection; use another unconnected profile to demonstrate a new request.

A reciprocal example is “I have used Python and want JavaScript; you have used JavaScript and want Python.” The explanation comes from the two website profiles, not an invented training label. Having used a technology does not automatically establish teaching ability.

## 8. Demonstrate incomplete input

Use your own disposable test account. Save an empty technology profile: the dashboard asks for more information and gives no ML score. Enter a supported language while leaving other fields blank: the system can use the remaining information. A negative coding-years entry is rejected. The published screenshots show these checked behaviors.

## Questions the teacher may ask

**Do the five accounts train the model?** No. They are live application examples. All model fitting, validation and testing read only the verified survey file.

**Why is there validation if the split is 70:30?** Validation is a temporary practice portion inside the 70%. The final models are refitted on the full 70%; the 30% remains the final exam.

**What is new compared with the reference?** Source-aligned profiles, a reproducible real-data experiment, reciprocal learning explanations, a distinction between stated and predicted interests, and clear empty-input behavior. See [references](REFERENCES.md).

**What is implemented?** Accounts/profiles, explainable discovery, connection acceptance, project teams, community activities and private chat/file sharing. [Cloud checks](VERIFICATION.md) record the completed tests. Deployment happens only on the project owner's instruction.
