from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.exceptions import ValidationError
from .attachments import MAX_FILE_BYTES, prepare_attachments, safe_filename


def image_file(name="sketch.png"):
    stream = BytesIO()
    Image.new("RGB", (120, 80), "#198b65").save(stream, format="PNG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")


class AttachmentValidationTests(SimpleTestCase):
    def test_image_is_decoded_and_reencoded_without_appended_content(self):
        original = image_file()
        raw = original.read() + b"<script>untrusted appended data</script>"
        file = SimpleUploadedFile("sketch.png", raw, content_type="text/html")
        result = prepare_attachments([file])[0]
        self.assertEqual(result["content_type"], "image/png")
        self.assertEqual((result["width"], result["height"]), (120, 80))
        self.assertNotIn(b"<script>", result["data"])
        self.assertEqual(result["size"], len(result["data"]))

    def test_unsupported_empty_corrupt_and_mislabelled_files_are_rejected(self):
        for name, raw in [
            ("bad.svg", b"<svg/>"),
            ("bad.html", b"<script/>"),
            ("program.exe", b"MZ"),
            ("empty.txt", b""),
            ("bad.png", b"not an image"),
            ("bad.pdf", b"not a PDF"),
            ("bad.docx", b"not a zip"),
            ("binary.txt", b"abc\x00def"),
            ("non-utf8.csv", b"\xff\xfe"),
        ]:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                prepare_attachments([SimpleUploadedFile(name, raw)])
        wrong_name = image_file("not-jpeg.jpg")
        with self.assertRaises(ValidationError):
            prepare_attachments([wrong_name])

    def test_size_count_and_decoded_pixel_limits(self):
        with self.assertRaises(ValidationError):
            prepare_attachments([SimpleUploadedFile("large.txt", b"a" * (MAX_FILE_BYTES + 1))])
        with self.assertRaises(ValidationError):
            prepare_attachments([image_file() for _ in range(4)])
        with self.assertRaises(ValidationError):
            prepare_attachments(
                [SimpleUploadedFile("large.txt", b"a" * MAX_FILE_BYTES) for _ in range(3)]
            )
        with (
            patch("platform_api.attachments.MAX_IMAGE_PIXELS", 100),
            self.assertRaises(ValidationError),
        ):
            prepare_attachments([image_file()])

    def test_text_office_and_archive_checks_and_safe_filename(self):
        text = prepare_attachments([SimpleUploadedFile("notes.txt", b"Milestone one\n")])[0]
        self.assertFalse(text["is_image"])
        self.assertEqual(text["data"], b"Milestone one\n")
        self.assertEqual(safe_filename("../folder\\report\r\n\u202e.pdf"), "report.pdf")
        archive = BytesIO()
        with ZipFile(archive, "w") as zip_file:
            zip_file.writestr("notes.txt", "Plain file, never extracted by the server")
        prepare_attachments([SimpleUploadedFile("project.zip", archive.getvalue())])
        with self.assertRaises(ValidationError):
            prepare_attachments([SimpleUploadedFile("pretend.docx", archive.getvalue())])
