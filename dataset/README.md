# Dataset provenance and reuse

**Publisher:** Stack Exchange, Inc. **Dataset:** Stack Overflow Developer Survey 2024.

- [Original release archive](https://github.com/StackExchange/Survey/tree/main/packages/archive/2024)
- [Survey methodology](https://survey.stackoverflow.co/2024/methodology)
- [Original technology questions](https://survey.stackoverflow.co/2024/technology)
- [Publisher license/attribution statement](https://github.com/StackExchange/Survey#license-and-data-attribution)

Original data is licensed under **Open Database License 1.0 (ODbL)**; individual contents under **Database Contents License 1.0 (DbCL)**. Source-derived exports and example tables here retain those terms and attribution. They are provided without affiliation with or endorsement by Stack Overflow. [ODbL text](https://opendatacommons.org/licenses/odbl/1-0/) · [DbCL text](https://opendatacommons.org/licenses/dbcl/1-0/).

The downloader pins official repository revision `9dd5c163b7ec09ce5503f711c37a99dbd80ff3c7`. `results.csv` is 159,525,875 bytes with SHA-256:

```text
7f2c2dbf6989d00b80a7351de4bb3af4b52b21cc52d5c947891bbc4f4e5cbe49
```

The original schema SHA-256 is:

```text
d9c03fd43949dd9b0fea4847894c4011a6fe3c4390d5d8c48e078a8bfe623833
```

```bash
.venv/bin/python -m ml.download_survey
.venv/bin/python -m ml.train
.venv/bin/python -m ml.export_data
```

The raw file remains unchanged in ignored `dataset/raw/stackoverflow2024/`. The downloader saves `source.json`. Downloading directly from the original publisher is preferable to an unattributed Kaggle mirror; this satisfies the requirement for an original public website dataset.

`processed/survey2024_profiles.csv` and `.xlsx` contain the normalized eligible cohort with original anonymous response IDs and outer 70:30 train/test membership and an internal tuning_role column. Missing inputs are still visible; imputation happens inside the saved training encoder. `survey_profile_options.json` is the training-observed vocabulary used for website suggestions. No raw survey respondent becomes an application account.

The original survey has 65,437 rows/114 columns. There are real unanswered fields. 9,685 missing desired-language answers are excluded instead of becoming invented negative labels. The eligible cohort has 55,752 rows. See [audit JSON](../ml/evaluation/survey2024/data_audit.json), [preprocessing examples](../ml/evaluation/survey2024/preprocessing_examples.json) and [Excel examples](../docs/evidence/survey2024/preprocessing_examples.xlsx).

The former generated students/projects and pair-label datasets are retired from the supported tree. They remain in Git history solely as earlier prototype work. Fictional presentation accounts live separately in backend test/presentation fixtures and are never read by this ML pipeline.

## The 70:30 split and website accounts

The split is made on groups of identical normalized survey inputs: 70% of groups for training, 30% for final testing. Within the training portion, 80% is used to fit candidates and 20% for validation/setting selection. After selection, preprocessing and both final models are refitted on the entire outer 70%. The outer test rows never select settings. Different group sizes make the actual row percentages approximate; measured counts are in [results](../docs/RESULTS.md).

The exported split column is train or test. tuning_role is fit or validation for training rows, and test_not_used_for_tuning for test rows. Five fictional website accounts and all new registrations stay in MongoDB and are absent from this source-data export, model fitting, validation and test scoring.
