import io
import tempfile
import unittest
from pathlib import Path

from docx import Document

import server
from server import extract_resume


def make_resume(*paragraphs):
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    buffer.filename = "student-resume.docx"
    return buffer


class ResumeProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(self.temp_directory.name) / "test.sqlite3"
        server.app.config["TESTING"] = True
        with server.app.app_context():
            server.init_db()
        self.client = server.app.test_client()
        response = self.client.post(
            "/register",
            data={"email": "student@example.edu", "password": "strong-pass"},
        )
        self.assertEqual(response.status_code, 302)

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_does_not_infer_domain_or_branch_from_unstructured_text(self):
        result = extract_resume(
            make_resume(
                "Alex Student",
                "B.Tech Computer Science student interested in campus collaboration and research.",
            )
        )

        self.assertEqual(result["name"], "Alex Student")
        self.assertEqual(result["branch"], "")
        self.assertEqual(result["domain"], "")

    def test_extracts_explicit_profile_labels(self):
        result = extract_resume(
            make_resume(
                "Alex Student",
                "Branch: Computer Science and Engineering",
                "Year: 3",
                "Skills: Python, Django, SQL",
                "Machine learning and data science projects",
            )
        )

        self.assertEqual(result["branch"], "Computer Science And Engineering")
        self.assertEqual(result["academic_year"], "3")
        self.assertIn("Python", result["skills"])
        self.assertEqual(result["domain"], "AI / ML")

    def test_upload_preserves_manual_edits_and_saves_suggestions(self):
        resume = make_resume(
            "Resume Name",
            "Branch: Computer Science and Engineering",
            "Year: 2",
            "Skills: Python, Django, SQL",
            "Interests: Machine Learning, Research",
            "Machine learning internship",
        )
        response = self.client.post(
            "/profile",
            data={
                "action": "extract_resume",
                "name": "Name Entered By Student",
                "city": "Pune",
                "resume": (resume, "student-resume.docx"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('value="Name Entered By Student"', page)
        self.assertIn('value="Computer Science And Engineering"', page)
        self.assertIn('value="Python, Django, SQL, Machine Learning"', page)
        self.assertIn('value="Pune"', page)

        response = self.client.post(
            "/profile",
            data={
                "action": "save_profile",
                "name": "Name Entered By Student",
                "branch": "Computer Science And Engineering",
                "year": "2",
                "skills": "Python, Django, SQL",
                "interests": "Machine Learning, Research",
                "domain": "AI / ML",
                "experience": "Intermediate",
                "project_type": "AI/ML Application",
                "city": "Pune",
                "phone": "",
                "github": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            user_id = session["user_id"]
        with server.app.app_context():
            saved_profile = server.db().execute(
                "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
        self.assertEqual(saved_profile["name"], "Name Entered By Student")
        self.assertEqual(saved_profile["skills"], "Python, Django, SQL")


if __name__ == "__main__":
    unittest.main()