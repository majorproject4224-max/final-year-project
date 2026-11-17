import tempfile
import unittest
from pathlib import Path
import pandas as pd
from ml.features import normalize_items, pair_features, project_features, explain_pair
from ml.data import load_table, validate_pairs
from ml.train import split_pairs


class FeatureTests(unittest.TestCase):
    def test_normalization_missing_values_and_aliases(self):
        self.assertEqual(
            normalize_items(["Python", "python ", "ML", "Machine Learning"]),
            ["machine learning", "python"],
        )
        self.assertEqual(normalize_items(float("nan")), [])
        self.assertEqual(pair_features({}, {})["domain_similarity"], 0)
        self.assertEqual(explain_pair({}, {}), [])

    def test_requirement_coverage_is_directional_and_explanations_use_data(self):
        student = {"skills": ["Python", "React", "SQL"], "interests": ["Research"]}
        project = {"required_skills": ["Python", "Django"], "required_interests": ["Research"]}
        self.assertEqual(project_features(student, project)["skill_coverage"], 0.5)
        self.assertEqual(explain_pair(student, {"skills": ["python"]})[0]["items"], ["python"])

    def test_csv_and_excel_parity_and_missing_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            frame = pd.DataFrame([{"user_id": "S1", "skills": "Python,ML"}])
            csv, excel = Path(folder) / "students.csv", Path(folder) / "students.xlsx"
            frame.to_csv(csv, index=False)
            frame.to_excel(excel, index=False)
            self.assertEqual(
                load_table(csv, {"user_id"}).to_dict("records"),
                load_table(excel, {"user_id"}).to_dict("records"),
            )
            with self.assertRaises(ValueError):
                load_table(csv, {"absent"})

    def test_pair_validation_rejects_reversed_duplicates_and_unknown_ids(self):
        pairs = pd.DataFrame(
            [
                {
                    "user1_id": "A",
                    "user2_id": "B",
                    "compatibility_label": 1,
                    "label_source": "review",
                },
                {
                    "user1_id": "B",
                    "user2_id": "A",
                    "compatibility_label": 1,
                    "label_source": "review",
                },
            ]
        )
        with self.assertRaises(ValueError):
            validate_pairs(pairs, {"A": {}, "B": {}})
        with self.assertRaises(ValueError):
            validate_pairs(pairs.head(1), {"A": {}})

    def test_entity_disjoint_split_has_no_shared_students(self):
        frame = pd.DataFrame(
            [
                {"user1_id": str(a), "user2_id": str(b), "compatibility_label": (a + b) % 2}
                for a in range(40)
                for b in range(a + 1, 40)
            ]
        )
        train, test = split_pairs(frame)
        train_ids = set(frame.loc[train, "user1_id"]) | set(frame.loc[train, "user2_id"])
        test_ids = set(frame.loc[test, "user1_id"]) | set(frame.loc[test, "user2_id"])
        self.assertFalse(train_ids & test_ids)


if __name__ == "__main__":
    unittest.main()
