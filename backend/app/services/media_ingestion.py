from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from config_loader import MediaCategory

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
}
AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".ogg",
    ".m4a",
    ".wma",
    ".m4b",
}
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tiff",
    ".svg",
}


def save_uploaded_file(
    file_storage: FileStorage,
    *,
    destination_dir: Path | str,
    preferred_name: Optional[str] = None,
) -> Path:
    """Persist an uploaded file to the destination directory and return its path."""
    dest_dir = Path(destination_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    original_name = preferred_name or file_storage.filename or "uploaded_file"
    safe_name = secure_filename(original_name)
    if not safe_name:
        safe_name = f"upload_{uuid.uuid4().hex}"

    target_path = dest_dir / safe_name
    stem, suffix = target_path.stem, target_path.suffix
    counter = 1
    while target_path.exists():
        target_path = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    file_storage.save(target_path)
    return target_path


def delete_media_file_record(cursor, media_id: str) -> bool:
    """Delete a media record from the database."""
    cursor.execute("DELETE FROM media_items WHERE id = %s RETURNING id", (media_id,))
    return cursor.fetchone() is not None


def generate_file_metadata(
    file_path: Path | str,
    *,
    category: MediaCategory,
    title: Optional[str] = None,
    description: Optional[str] = None,
    uploader: Optional[str] = None,
    media_type: Optional[str] = None,
    mime_type: Optional[str] = None,
    original_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Create metadata payload for an uploaded file aligned with maintenance scanner output."""
    path = Path(file_path)
    stat = path.stat()
    file_size = stat.st_size
    modified_iso = datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z"
    scanned_at = datetime.utcnow().isoformat() + "Z"

    file_hash = _compute_sha256(path)
    signature_source = f"{file_size}:{int(stat.st_mtime)}:{path}"
    scanner_signature = hashlib.sha1(signature_source.encode("utf-8")).hexdigest()

    detected_media_type = _detect_media_type(path.suffix.lower(), media_type or category.media_type)

    metadata: Dict[str, Any] = {
        "title": title or path.stem,
        "description": description,
        "filename": path.name,
        "originalFilename": original_filename or path.name,
        "category": category.key,
        "categoryLabel": category.label,
        "rootPath": category.root_path,
        "relativePath": _relative_to(path, category.root_path),
        "mediaType": detected_media_type,
        "storageFormat": category.storage_format,
        "fileSize": file_size,
        "fileExtension": path.suffix.lower(),
        "lastModified": modified_iso,
        "scannerSignature": scanner_signature,
        "fileHash": file_hash,
        "sourcePath": str(path),
        "scannedAt": scanned_at,
        "ingestedVia": "upload",
        "ingestedAt": scanned_at,
        "mimeType": mime_type,
    }

    if uploader:
        metadata["uploadedBy"] = uploader

    return metadata


def _detect_media_type(extension: str, fallback: Optional[str]) -> str:
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in AUDIO_EXTENSIONS:
        return "audio"
    if extension in IMAGE_EXTENSIONS:
        return "image"
    return fallback or "unknown"


def _compute_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _relative_to(path: Path, root: str) -> str:
    root_path = Path(root)
    try:
        return str(path.relative_to(root_path))
    except ValueError:
        return path.name
