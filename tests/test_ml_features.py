import unittest

from backend.platform_api.matching import normalize_items, pair_features, profile_text


class MatchingFeatureTests(unittest.TestCase):
    def test_skill_and_interest_normalization_is_shared_by_pair_features(self):
        left = {
            "skills": ["Python", " ML ", "python"],
            "interests": ["Research", "AI"],
            "domain": "AI / ML",
            "experience": "Intermediate",
            "preferred_project_type": "AI/ML Application",
        }
        right = {
            "skills": ["PYTHON", "Machine Learning"],
            "interests": ["ai", " research "],
            "domain": "AI / ML",
            "experience": "Intermediate",
            "preferred_project_type": "AI/ML Application",
        }

        self.assertEqual(normalize_items(left["skills"]), ["machine learning", "python"])
        features = pair_features(left, right)
        self.assertEqual(features["skill_similarity"], 1.0)
        self.assertEqual(features["interest_similarity"], 1.0)
        self.assertEqual(features["domain_similarity"], 1.0)
        self.assertEqual(features["experience_compatibility"], 1.0)
        self.assertEqual(features["project_similarity"], 1.0)
        self.assertIn("machine learning", profile_text(left))


if __name__ == "__main__":
    unittest.main()