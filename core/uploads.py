from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class UploadValidationError(RuntimeError):
    pass


def _normalized_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _validate_filename(file: FileStorage) -> str:
    original_name = secure_filename(file.filename or '')
    if not original_name:
        raise UploadValidationError('A valid file name is required.')
    return original_name


def save_uploaded_file(
    file: FileStorage,
    upload_folder: str,
    *,
    allowed_extensions: set[str],
    allowed_mime_prefixes: tuple[str, ...] = (),
    allowed_mime_types: set[str] | None = None,
) -> str:
    original_name = _validate_filename(file)
    extension = _normalized_extension(original_name)
    if extension not in allowed_extensions:
        raise UploadValidationError('That file type is not allowed.')

    mimetype = (file.mimetype or '').lower()
    if allowed_mime_types and mimetype not in allowed_mime_types:
        raise UploadValidationError('Uploaded file MIME type is not allowed.')
    if allowed_mime_prefixes and not any(mimetype.startswith(prefix) for prefix in allowed_mime_prefixes):
        raise UploadValidationError('Uploaded file MIME type is not allowed.')

    Path(upload_folder).mkdir(parents=True, exist_ok=True)
    stored_name = f'{uuid4().hex}{extension}'
    destination = Path(upload_folder) / stored_name
    file.save(destination)
    return stored_name


def is_public_upload(filename: str, *, allowed_extensions: set[str]) -> bool:
    safe_name = secure_filename(filename or '')
    if not safe_name:
        return False
    return _normalized_extension(safe_name) in allowed_extensions
