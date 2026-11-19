"""Checks against the saved real-data artifact; never retrain in a request."""
import json
import unittest
from pathlib import Path
import joblib
import numpy as np
from ml.survey import positive_probabilities
from ml.discovery import recommend_people
from ml.download_survey import FILES, checksum

ROOT = Path(__file__).resolve().parents[1]

class SavedSurveyModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / 'ml/models/survey-recommender.joblib'
        if not cls.path.exists():
            raise RuntimeError('Run the verified real-data training pipeline before model tests.')
        cls.bundle = joblib.load(cls.path)
        cls.report = json.loads((ROOT / 'ml/evaluation/survey2024/metrics.json').read_text())

    def test_provenance_and_saved_model_identity(self):
        self.assertFalse(self.bundle['metadata']['synthetic'])
        self.assertEqual(self.bundle['metadata']['source_sha256'], FILES['results.csv'])
        self.assertEqual(self.bundle['metadata']['schema_version'], 3)
        self.assertEqual(checksum(self.path), self.report['model_sha256'])
        self.assertEqual(self.report['group_overlap'], 0)

    def test_saved_forest_was_refitted_on_all_outer_training_rows(self):
        protocol = self.bundle["metadata"]["split_protocol"]
        count = self.report["splits"]["train"]["rows"]
        self.assertEqual(protocol["train_fraction"], 0.7)
        self.assertEqual(protocol["test_fraction"], 0.3)
        self.assertTrue(protocol["final_refit_on_all_training_rows"])
        self.assertFalse(protocol["website_accounts_included"])
        self.assertEqual(protocol["final_fit_rows"], count)
        self.assertEqual(set(self.report["splits"]), {"train", "test"})
        self.assertEqual(self.report["validation_setup"]["fit_rows"] + self.report["validation_setup"]["validation_rows"], count)
        for tree in self.bundle["preferences"].estimators_:
            self.assertEqual(tree.tree_.weighted_n_node_samples[0], count)

    def test_shared_encoder_cluster_and_rf_predictions(self):
        rows = [{'languages': ['Python'], 'databases': ['PostgreSQL'], 'years_code': 3}, {'languages': ['JavaScript'], 'frameworks': ['React'], 'years_code': None}]
        encoder = self.bundle['encoder']
        labels = self.bundle['clusters'].predict(encoder.cluster_matrix(rows))
        self.assertTrue(np.all((labels >= 0) & (labels < self.bundle['clusters'].n_clusters)))
        scores = positive_probabilities(self.bundle['preferences'], encoder.transform(rows))
        self.assertEqual(scores.shape, (2, len(self.bundle['labels'])))
        self.assertTrue(np.all(np.isfinite(scores)))
        self.assertTrue(np.all((scores >= 0) & (scores <= 1)))
        self.assertFalse(np.allclose(scores[0], scores[1]))

    def test_empty_and_unseen_profiles_abstain_and_rank_is_stable(self):
        candidates = [{'languages': ['Python'], 'wanted_languages': ['JavaScript']}, {'languages': ['JavaScript'], 'wanted_languages': ['Python']}]
        for source in [{}, {'languages': ['not-a-survey-technology']}]:
            ranked, details = recommend_people(self.bundle, source, candidates)
            self.assertEqual(ranked, [])
            self.assertIn('Add technologies', details['detail'])
        ranked, _ = recommend_people(self.bundle, {'languages': ['Python'], 'wanted_languages': ['JavaScript']}, candidates)
        scores = [r['match_score'] for r in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(any(r['reciprocal_learning'] for r in ranked))
