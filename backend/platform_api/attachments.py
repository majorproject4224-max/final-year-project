"""Small, private chat attachments. Binary content never enters chat JSON/events."""

from io import BytesIO
from pathlib import PurePosixPath
import unicodedata
import warnings
from zipfile import BadZipFile, ZipFile
from bson import ObjectId
from django.core.files.uploadhandler import FileUploadHandler
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_MESSAGE_BYTES = 10 * 1024 * 1024
MAX_FILES = 3
MAX_IMAGE_PIXELS = 12_000_000
IMAGE_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".zip": "application/zip",
}


class BoundedChatUploadHandler(FileUploadHandler):
    """Stop oversized multipart streams before temporary files grow without bound."""

    def __init__(self, request):
        super().__init__(request)
        self.total = self.count = self.current = 0

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.count += 1
        self.current = 0
        if self.count > MAX_FILES or self.field_name != "attachments":
            raise ValidationError("Attach up to 3 files using the attachments field.")

    def receive_data_chunk(self, raw_data, start):
        self.current += len(raw_data)
        self.total += len(raw_data)
        if self.current > MAX_FILE_BYTES or self.total > MAX_MESSAGE_BYTES:
            raise ValidationError("Files must be at most 5 MB each and 10 MB per message.")
        return raw_data

    def file_complete(self, file_size):
        return None


class ChatMultiPartParser(MultiPartParser):
    def parse(self, stream, media_type=None, parser_context=None):
        request = parser_context["request"]._request
        request.upload_handlers.insert(0, BoundedChatUploadHandler(request))
        return super().parse(stream, media_type, parser_context)


def safe_filename(name):
    name = PurePosixPath(str(name).replace("\\", "/")).name
    name = "".join(c for c in name if not unicodedata.category(c).startswith("C")).strip(" .")
    suffix = PurePosixPath(name).suffix.lower()
    return (name[: -len(suffix)] if suffix else name)[:120] + suffix


def clean_image(raw, expected_format):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format != expected_format:
                    raise ValueError("The image contents do not match its filename.")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Choose an image with at most 12 million pixels.")
                if getattr(source, "is_animated", False):
                    raise ValueError(
                        "Please send a still image; animated images are not supported."
                    )
                source.load()
                picture = ImageOps.exif_transpose(source).convert(
                    "RGB" if expected_format == "JPEG" else "RGBA"
                )
                # Re-encode pixel data only, removing EXIF/GPS and appended content.
                picture.info.clear()
                output = BytesIO()
                picture.save(output, format=expected_format)
                return output.getvalue(), picture.width, picture.height
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ValueError("This image is damaged or too large to process.") from error


def validate_document(raw, suffix):
    if suffix == ".pdf" and not raw.startswith(b"%PDF-"):
        raise ValueError("This file does not contain a PDF.")
    if suffix in {".txt", ".csv"}:
        try:
            decoded = raw.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError("Text and CSV attachments must use UTF-8 encoding.") from error
        if "\x00" in decoded:
            raise ValueError("This file contains binary data, not text.")
    required_parts = {
        ".docx": "word/document.xml",
        ".xlsx": "xl/workbook.xml",
        ".pptx": "ppt/presentation.xml",
    }
    if suffix in {*required_parts, ".zip"}:
        try:
            # Inspect directory metadata only. Never extract or execute uploaded archives.
            with ZipFile(BytesIO(raw)) as archive:
                if len(archive.infolist()) > 2000:
                    raise ValueError("This archive contains too many files.")
                if suffix in required_parts and not {
                    "[Content_Types].xml",
                    required_parts[suffix],
                }.issubset(archive.namelist()):
                    raise ValueError("The document contents do not match its filename.")
        except BadZipFile as error:
            raise ValueError("This document or ZIP archive is damaged.") from error


def prepare_attachments(files):
    if len(files) > MAX_FILES:
        raise ValidationError("Attach up to 3 files per message.")
    attachments, original_total, stored_total = [], 0, 0
    for upload in files:
        name = safe_filename(upload.name)
        suffix = PurePosixPath(name).suffix.lower()
        if suffix not in IMAGE_FORMATS and suffix not in DOCUMENT_TYPES:
            raise ValidationError(
                "Use JPG, PNG, WebP, PDF, DOCX, XLSX, PPTX, TXT, CSV or ZIP files."
            )
        raw = upload.read(MAX_FILE_BYTES + 1)
        original_total += len(raw)
        if not raw or len(raw) > MAX_FILE_BYTES or original_total > MAX_MESSAGE_BYTES:
            raise ValidationError(
                "Files must not be empty, and must be at most 5 MB each / 10 MB total."
            )
        row = {"id": str(ObjectId()), "name": name, "is_image": suffix in IMAGE_FORMATS}
        try:
            if row["is_image"]:
                raw, row["width"], row["height"] = clean_image(raw, IMAGE_FORMATS[suffix])
                row["content_type"] = Image.MIME[IMAGE_FORMATS[suffix]]
            else:
                validate_document(raw, suffix)
                row["content_type"] = DOCUMENT_TYPES[suffix]
        except ValueError as error:
            raise ValidationError(str(error)) from error
        stored_total += len(raw)
        if len(raw) > MAX_FILE_BYTES or stored_total > MAX_MESSAGE_BYTES:
            raise ValidationError("The processed images are too large. Choose smaller images.")
        attachments.append({**row, "size": len(raw), "data": raw})
    return attachments


def attachment_metadata(row):
    return {key: value for key, value in row.items() if key != "data"}
