# Teacher demonstration: evidence before claims

Use GitHub Codespaces. Nothing needs installing on the office laptop. Keep the official title **ConnectAI: AI/ML-Based Social Connection Recommendation Platform**.

## 1. Show the original source

Open the official [Stack Overflow 2024 archive](https://github.com/StackExchange/Survey/tree/main/packages/archive/2024) and [methodology](https://survey.stackoverflow.co/2024/methodology). Explain that the source contains anonymous real survey responses, not your application's users. Show `dataset/README.md`, the raw checksum and `dataset/raw/stackoverflow2024/schema.csv` in Codespaces.

```bash
sha256sum dataset/raw/stackoverflow2024/results.csv
.venv/bin/python -m ml.export_data
```

Open the exported `dataset/processed/survey2024_profiles.xlsx`. Show the real response IDs, original missing counts, cleaned inputs and split membership. The original raw CSV remains unchanged.

## 2. Explain why the attributes changed

Show **My profile**. Match each technology question to the exact survey column listed under the field. Account names/contact details are not model inputs. Community settings support volunteering separately. The old generated academic/domain/experience features are no longer used for ML.

## 3. Show preprocessing and null handling

Open README preprocessing figures and `ml/evaluation/survey2024/data_audit.json`.

- Original dataset: 65,437 responses; 9,685 missing desired-language answers.
- Those missing targets are excluded, not invented as incompatible labels.
- A real missing technology answer becomes an empty unknown list with a missing flag.
- Coding years are numeric; missing input uses the training median, 11, plus an indicator.
- The original file has no nonmissing invalid YearsCode values. Negative/infinite/nonnumeric examples are separate constructed tests.
- Train/validation/test groups do not share identical normalized input profiles.

Use `docs/evidence/survey2024/02-preprocessing-examples.png` and the Excel examples for before/after evidence. Explain that lowercase/aliases prevent `Python` and `python` becoming different skills.

## 4. Explain both actual ML models

**K-Means:** groups similar technology vectors without predefined labels. Show the silhouette/elbow plot. k=2 was best among the candidates, but silhouette≈0.063 is low: the groups overlap.

**Random Forest:** learns actual wanted-language answers using current technologies and coding years. It is not trained on manually created person-pair scores. Show the parameter table with the selected row: 160 trees, depth 20, minimum leaf size 5, threshold 0.35.

Show the learning curve. Explain that the forest trains many trees; it has no neural-network epochs. The plotted points are actual fits with increasing training data.

## 5. Explain the results simply

Use **How it works** in the app and the README result table:

- Correct: 150,664; wrong: 28,136 person-language decisions.
- Accuracy per language: 84.26%; micro F1: 0.6963.
- MSE: 0.1154; RMSE: 0.3396. Lower probability error is better.
- Exact all-language profile accuracy: 17.61%, a harder different measure.
- A continuation baseline has higher F1 (0.7048). The forest has lower probability error. State both.

Do not say “84% of friendships are successful.” We did not measure friendship outcomes.

## 6. Demonstrate behavior with imperfect input

Use a disposable test account, not another person's profile.

1. Save an empty technology profile. Dashboard asks for technology information and displays no ML score.
2. Enter `Python, python, JS` in the language field. After saving, the API normalizes/deduplicates the answers.
3. Leave databases/platforms/coding years blank. Recommendations may still work from supported remaining technologies; the completeness indicator shows missing inputs.
4. Try a negative coding-years value. Form/API validation rejects it.
5. Show the stress-test table: deliberately hiding all input fields causes all predictions to abstain. Do not call this artificially masked table the original dataset's null statistics.

## 7. Show the project-specific contribution

Open a recommended person's explanation: “You want to use; they have used” and the reverse direction. These lists come from actual application profile comparisons. Marked fictional accounts are only UI examples; they were never used to train the model.

Explain that reciprocal learning discovery can find complementary partners as well as similar ones. The score combines observed comparisons and a learned preference signal with documented weights. The published model metrics evaluate desired-language predictions; the people score ranks profile matches.

Then demonstrate connection acceptance, chat/file sharing, a project application and an individually organized drive. Project scores are observed technology coverage; activity suggestions are explicit-interest matching.

## 8. Be ready for these questions

**Why not friendship labels?** The chosen public survey does not contain them. Inventing them would repeat the original problem. We use its actual target and clearly limit the claim.

**Why K-Means and Random Forest?** They provide understandable unsupervised grouping and supervised preference prediction. We compare/tune them rather than claim they are always best.

**What is new versus the reference?** This implementation adds a reproducible original-data pipeline, reciprocal technology explanations, observed-versus-predicted distinction, completeness-aware abstention and measured evidence. The underlying algorithms/reciprocal idea are established research, which we cite.

**What is implemented?** Original-data preprocessing and model evaluation, explainable technology discovery, connection acceptance, projects and teams, community activities, and private chat with file sharing. Show the completed checks in [VERIFICATION.md](VERIFICATION.md). Deployment is performed only on the project owner's instruction.
