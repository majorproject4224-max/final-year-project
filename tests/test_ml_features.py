"""Constructed unit-test fixtures are not model-training observations."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from ml.survey import tags, years, read_survey, SurveyEncoder, FIELD_MAP, TARGET
from ml.train_survey import split_rows, tuning_rows, evaluate
from ml.discovery import compare_people, project_match

class SurveyPreprocessingTests(unittest.TestCase):
    def test_aliases_missing_and_irregular_values(self):
        self.assertEqual(tags(' JS ; javascript ; Python ; PYTHON '), ['javascript', 'python'])
        for value in [None, float('nan'), pd.NA, '', 'NA', 'null']:
            self.assertEqual(tags(value), [])
        self.assertEqual(tags(['C++', 'C#', 'NodeJS']), ['c#', 'c++', 'node.js'])
        with self.assertRaises(ValueError): tags([42])
        self.assertEqual(years('Less than 1 year'), 0.5)
        self.assertEqual(years('More than 50 years'), 51)
        for value in ['many', -3, 1000, float('inf'), None]: self.assertIsNone(years(value))

    def test_original_schema_null_targets_and_csv_excel_parity(self):
        base = {'ResponseId': 1, **{c: None for c in FIELD_MAP.values()}, 'YearsCode': 'bad', TARGET: 'Rust'}
        base['LanguageHaveWorkedWith'] = 'Python;Python'
        frame = pd.DataFrame([base, {**base, 'ResponseId': 2, TARGET: None}])
        with tempfile.TemporaryDirectory() as tmp:
            outputs = []
            for suffix in ['csv', 'xlsx']:
                path = Path(tmp) / ('survey.' + suffix)
                frame.to_csv(path, index=False) if suffix == 'csv' else frame.to_excel(path, index=False)
                rows, audit, _ = read_survey(path)
                self.assertEqual(len(rows), 1)
                self.assertEqual(audit['missing_target_excluded'], 1)
                self.assertEqual(audit['invalid_years_nonmissing'], 2)
                self.assertIsNone(rows[0]['years_code'])
                outputs.append(rows)
            self.assertEqual(outputs[0], outputs[1])
            frame.drop(columns=[TARGET]).to_csv(path.with_suffix('.csv'), index=False)
            with self.assertRaises(ValueError): read_survey(path.with_suffix('.csv'))

    def test_preprocessing_learns_only_training_vocabulary_and_median(self):
        encoder = SurveyEncoder().fit([{'languages': ['python'], 'years_code': 2}, {'languages': ['java'], 'years_code': 4}])
        before = dict(encoder.vocabulary_.vocabulary_)
        matrix = encoder.transform([{'languages': ['unseen'], 'years_code': None}])
        self.assertEqual(before, encoder.vocabulary_.vocabulary_)
        self.assertEqual(encoder.imputer_.statistics_[0], 3)
        self.assertTrue(np.isfinite(matrix.toarray()).all())
        self.assertFalse(encoder.supported({}))
        self.assertFalse(encoder.supported({'languages': ['unseen']}))

    def test_duplicate_input_groups_never_cross_splits(self):
        rows = [{'group': str(i // 2), 'response_id': str(i)} for i in range(60)]
        parts = split_rows(rows)
        self.assertEqual(set(parts), {"train", "test"})
        self.assertEqual(len(parts["train"]), 42)
        self.assertEqual(len(parts["test"]), 18)
        groups = {name: {r["group"] for r in part} for name, part in parts.items()}
        self.assertFalse(groups["train"] & groups["test"])
        self.assertEqual(parts, split_rows(rows))
        self.assertEqual({r["response_id"] for part in parts.values() for r in part}, {r["response_id"] for r in rows})

    def test_internal_validation_is_only_inside_outer_training(self):
        rows = [{"group": str(i // 2), "response_id": str(i)} for i in range(200)]
        outer = split_rows(rows)
        tuning = tuning_rows(outer["train"])
        fit = {r["group"] for r in tuning["fit"]}
        validation = {r["group"] for r in tuning["validation"]}
        test = {r["group"] for r in outer["test"]}
        self.assertFalse(fit & validation)
        self.assertFalse((fit | validation) & test)
        self.assertEqual(fit | validation, {r["group"] for r in outer["train"]})
        self.assertEqual(len(tuning["fit"]) + len(tuning["validation"]), len(outer["train"]))

    def test_reciprocal_reasons_and_project_coverage_use_real_comparisons(self):
        a = {'languages': ['Python'], 'wanted_languages': ['Rust']}
        b = {'languages': ['Rust'], 'wanted_languages': ['Python']}
        match = compare_people(a, b, {'rust': 0.4})
        self.assertTrue(match['reciprocal_learning'])
        self.assertEqual(match['explanations'][0]['items'], ['rust'])
        self.assertEqual(match['explanations'][1]['items'], ['python'])
        self.assertFalse(compare_people(a, {}, {})['reciprocal_learning'])
        self.assertEqual(project_match(a, {'required_skills': ['Python', 'Java']})['match_score'], 50)

    def test_probability_error_and_correct_wrong_counts(self):
        actual = np.array([[0, 1], [1, 0]])
        probability = np.array([[0.2, 0.8], [0.4, 0.3]])
        measured = evaluate(actual, probability)
        self.assertEqual(measured['correct'], 3)
        self.assertEqual(measured['wrong'], 1)
        self.assertAlmostEqual(measured['probability_mse'], (0.04 + 0.04 + 0.36 + 0.09) / 4)
