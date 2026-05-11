"""
File storage logic: save uploaded files to the uploads/ directory.
"""
import os
import uuid
from datetime import date

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


def ensure_uploads_dir() -> None:
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def save_uploaded_file(file_bytes: bytes, original_filename: str) -> str:
    """
    Save raw bytes to uploads/<YYYY-MM>/<uuid>_<original_filename>.
    Returns the absolute path of the saved file.
    """
    ensure_uploads_dir()

    month_dir = os.path.join(UPLOADS_DIR, date.today().strftime("%Y-%m"))
    os.makedirs(month_dir, exist_ok=True)

    ext = os.path.splitext(original_filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(month_dir, unique_name)

    with open(dest_path, "wb") as fh:
        fh.write(file_bytes)

    return os.path.abspath(dest_path)


def file_exists(path: str) -> bool:
    return os.path.isfile(path)


def read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()
