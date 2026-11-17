import io
import unittest
import sys
from pathlib import Path
from docx import Document
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from platform_api.resume import extract_resume

class ResumeTests(unittest.TestCase):
    def test_resume_suggestions_extract_explicit_data(self):
        document = Document()
        document.add_paragraph("Name: Asha Student")
        document.add_paragraph("Branch: Computer Science")
        document.add_paragraph("Year: 3")
        document.add_paragraph("Skills: Python, Django")
        stream = io.BytesIO()
        document.save(stream)
        stream.seek(0)
        stream.name = "resume.docx"
        values = extract_resume(stream)
        self.assertEqual(values["academic_year"], "3")
        self.assertIn("Python", values["skills"])

    def test_invalid_upload_fails_clearly(self):
        stream = io.BytesIO(b"broken")
        stream.name = "resume.exe"
        with self.assertRaises(ValueError):
            extract_resume(stream)
