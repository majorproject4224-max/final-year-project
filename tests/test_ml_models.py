"""Saved-model checks; the CI training step creates the artifact beforehand."""

import unittest
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from ml.features import (
    profile_text,
    pair_features,
    project_features,
    USER_FEATURES,
    PROJECT_FEATURES,
)
from ml.train import split_pairs
from ml.data import clean_profiles, load_table, STUDENT_COLUMNS, PROJECT_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


class SavedModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = joblib.load(ROOT / "ml/models/recommender.joblib")
        cls.students = clean_profiles(load_table(ROOT / "dataset/students.csv", STUDENT_COLUMNS))
        cls.projects = clean_profiles(
            load_table(ROOT / "dataset/projects.csv", PROJECT_COLUMNS), True
        )

    def test_saved_preprocessing_and_cluster_prediction(self):
        vector = self.bundle["vectorizer"].transform([profile_text(s) for s in self.students[:10]])
        labels = self.bundle["clusters"].predict(vector)
        self.assertEqual(len(labels), 10)
        self.assertTrue(np.all((labels >= 0) & (labels < self.bundle["metadata"]["selected_k"])))
        self.assertGreater(vector.nnz, 0)

    def test_classifiers_and_probability_order(self):
        for kind, features, names in (
            (
                "users",
                [pair_features(self.students[0], s) for s in self.students[1:21]],
                USER_FEATURES,
            ),
            (
                "projects",
                [project_features(self.students[0], p) for p in self.projects[:20]],
                PROJECT_FEATURES,
            ),
        ):
            scores = self.bundle[kind].predict_proba(pd.DataFrame(features, columns=names))[:, 1]
            self.assertTrue(np.all((scores >= 0) & (scores <= 1)))
            self.assertGreater(
                np.ptp(scores), 0, "The model must distinguish different candidates."
            )
            order = np.argsort(-scores)
            self.assertTrue(np.all(np.diff(scores[order]) <= 0))

    def test_entity_split_has_no_shared_users_or_projects(self):
        for name, project in (("matching_data", False), ("project_matches", True)):
            frame = pd.read_csv(ROOT / f"dataset/{name}.csv")
            train, test = split_pairs(frame, project)
            if project:
                for column in ("user_id", "project_id"):
                    self.assertFalse(set(frame.loc[train, column]) & set(frame.loc[test, column]))
            else:
                training = set(frame.loc[train, "user1_id"]) | set(frame.loc[train, "user2_id"])
                testing = set(frame.loc[test, "user1_id"]) | set(frame.loc[test, "user2_id"])
                self.assertFalse(training & testing)
