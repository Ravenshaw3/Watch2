from __future__ import annotations

import json
import logging
import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.core.enhanced_scanner import EnhancedMediaScanner
from config_loader import load_media_config, MediaCategory
from postgres_config import get_db_connection

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE = LOG_DIR / "media_deletions.log"

STATUS_AVAILABLE = "available"
STATUS_MISSING = "missing"


class MediaMaintenanceError(RuntimeError):
    """Raised when the media maintenance scanner cannot complete."""


@dataclass
class CategoryResult:
    category: str
    root_path: str
    files_found: int = 0
    files_scanned: int = 0
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    missing: int = 0
    missing_paths: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    limited: bool = False
    dry_run: bool = False
    root_exists: bool = True
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "root_path": self.root_path,
            "files_found": self.files_found,
            "files_scanned": self.files_scanned,
            "added": self.added,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "missing": self.missing,
            "missing_paths": self.missing_paths,
            "errors": self.errors,
            "limited": self.limited,
            "dry_run": self.dry_run,
            "root_exists": self.root_exists,
            "notes": self.notes,
        }


def run_media_maintenance_scan(
    *,
    categories: Optional[Sequence[str]] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Run the maintenance scanner across configured media directories."""
    config = load_media_config()
    category_models = _select_categories(config.categories, categories)
    if not category_models:
        raise MediaMaintenanceError("No categories matched the requested selection")

    if limit is not None and limit <= 0:
        raise MediaMaintenanceError("limit must be a positive integer when provided")

    scanner = EnhancedMediaScanner()
    scanned_at = datetime.utcnow().isoformat() + "Z"

    totals = {
        "added": 0,
        "updated": 0,
        "unchanged": 0,
        "missing": 0,
        "files_scanned": 0,
        "files_found": 0,
        "categories": len(category_models),
        "logged_missing": 0,
    }

    summary: Dict[str, Any] = {
        "scanned_at": scanned_at,
        "dry_run": dry_run,
        "config_version": config.version,
        "selected_categories": [cat.key for cat in category_models],
        "categories": {},
        "totals": totals,
    }

    conn = get_db_connection()
    cursor = conn.cursor()
    deletion_logs: List[Dict[str, Any]] = []
    try:
        for category in category_models:
            category_result, category_logs = _scan_category(
                scanner=scanner,
                cursor=cursor,
                category=category,
                scanned_at=scanned_at,
                dry_run=dry_run,
                limit=limit,
            )
            summary["categories"][category.key] = category_result.to_dict()

            totals["added"] += category_result.added
            totals["updated"] += category_result.updated
            totals["unchanged"] += category_result.unchanged
            totals["missing"] += category_result.missing
            totals["files_scanned"] += category_result.files_scanned
            totals["files_found"] += category_result.files_found

            if not dry_run:
                deletion_logs.extend(category_logs)

        if dry_run:
            conn.rollback()
        else:
            _sync_media_settings(cursor, category_models)
            conn.commit()
            totals["logged_missing"] = len(deletion_logs)
            if deletion_logs:
                _write_deletion_log(deletion_logs)
    except Exception as exc:
        conn.rollback()
        logger.exception("Media maintenance scan failed: %s", exc)
        raise
    finally:
        cursor.close()
        conn.close()

    return summary


def _scan_category(
    *,
    scanner: EnhancedMediaScanner,
    cursor,
    category: MediaCategory,
    scanned_at: str,
    dry_run: bool,
    limit: Optional[int],
) -> Tuple[CategoryResult, List[Dict[str, Any]]]:
    root_path = category.root_path
    result = CategoryResult(
        category=category.key,
        root_path=root_path,
        dry_run=dry_run,
    )

    if not os.path.isdir(root_path):
        result.root_exists = False
        result.errors.append("root_path_missing")
        return result, []

    scanner_config = {
        "key": category.key,
        "root_path": root_path,
        "storage_format": category.storage_format,
        "include_patterns": category.include_patterns,
        "exclude_patterns": category.exclude_patterns,
        "hierarchy": {
            "levels": [{"name": level} for level in category.hierarchy_levels]
        } if category.hierarchy_levels else {},
    }

    scan_result = scanner.scan_directory(scanner_config)
    items = scan_result.items
    result.files_found = scan_result.files_found

    if limit is not None and len(items) > limit:
        items = items[:limit]
        result.limited = True
        result.notes.append(f"processing limited to first {limit} files")

    result.files_scanned = len(items)

    existing_records = _load_existing_records(cursor, category.key)
    processed_paths: set[str] = set()
    deletion_logs: List[Dict[str, Any]] = []

    for item in items:
        normalized_path = _normalise_path(item.file_path)
        processed_paths.add(normalized_path)

        try:
            file_stat = os.stat(item.file_path)
        except FileNotFoundError:
            result.errors.append("file_missing_during_scan")
            continue
        except PermissionError:
            result.errors.append("permission_denied")
            continue

        metadata = _build_metadata(
            item=item,
            category=category,
            file_stat=file_stat,
            scanned_at=scanned_at,
        )
        existing = existing_records.pop(normalized_path, None)

        if existing is None:
            result.added += 1
            if not dry_run:
                cursor.execute(
                    """
                    INSERT INTO media_items (title, description, media_type, source_path, status, metadata, duration_seconds)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        metadata["title"],
                        None,
                        metadata["mediaType"],
                        metadata["sourcePath"],
                        STATUS_AVAILABLE,
                        json.dumps(metadata),
                        metadata.get("durationSeconds"),
                    ),
                )
            continue

        needs_update = _record_needs_update(existing, metadata)
        if needs_update:
            result.updated += 1
            if not dry_run:
                cursor.execute(
                    """
                    UPDATE media_items
                    SET title = %s,
                        media_type = %s,
                        status = %s,
                        metadata = %s::jsonb,
                        duration_seconds = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        metadata["title"],
                        metadata["mediaType"],
                        STATUS_AVAILABLE,
                        json.dumps(metadata),
                        metadata.get("durationSeconds"),
                        existing["id"],
                    ),
                )
        else:
            result.unchanged += 1
            if not dry_run and existing.get("status") != STATUS_AVAILABLE:
                cursor.execute(
                    """
                    UPDATE media_items
                    SET status = %s,
                        metadata = %s::jsonb,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        STATUS_AVAILABLE,
                        json.dumps(metadata),
                        existing["id"],
                    ),
                )

    if existing_records:
        missing_paths = [_original_path(row) for row in existing_records.values()]
        result.missing = len(missing_paths)
        result.missing_paths = missing_paths[:25]

        if not dry_run:
            for row in existing_records.values():
                metadata = _ensure_metadata(row.get("metadata"))
                if "missing_since" not in metadata:
                    metadata["missing_since"] = scanned_at
                metadata["last_seen"] = scanned_at
                cursor.execute(
                    """
                    UPDATE media_items
                    SET status = %s,
                        metadata = %s::jsonb,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        STATUS_MISSING,
                        json.dumps(metadata),
                        row["id"],
                    ),
                )
                deletion_logs.append(
                    {
                        "timestamp": scanned_at,
                        "category": category.key,
                        "path": row["source_path"],
                        "previous_status": row.get("status"),
                        "action": "marked_missing",
                    }
                )
    return result, deletion_logs


def _select_categories(
    categories: Iterable[MediaCategory],
    requested: Optional[Sequence[str]],
) -> List[MediaCategory]:
    if not requested:
        return list(categories)

    requested_set = {key.strip() for key in requested if key and key.strip()}
    return [cat for cat in categories if cat.key in requested_set]


def _load_existing_records(cursor, category_key: str) -> Dict[str, Dict[str, Any]]:
    cursor.execute(
        """
        SELECT id, title, media_type, status, source_path, metadata, duration_seconds
        FROM media_items
        WHERE metadata->>'category' = %s
        """,
        (category_key,),
    )
    rows = cursor.fetchall() or []
    records: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        metadata = _ensure_metadata(row.get("metadata"))
        row["metadata"] = metadata
        normalized = _normalise_path(row["source_path"])
        records[normalized] = row
    return records


def _build_metadata(
    *,
    item,
    category: MediaCategory,
    file_stat: os.stat_result,
    scanned_at: str,
) -> Dict[str, Any]:
    file_size = file_stat.st_size
    mtime = datetime.utcfromtimestamp(file_stat.st_mtime).isoformat() + "Z"
    signature_source = f"{file_size}:{int(file_stat.st_mtime)}:{item.file_path}"
    scanner_signature = hashlib.sha1(signature_source.encode("utf-8")).hexdigest()

    metadata = dict(item.metadata or {})
    metadata.update(
        {
            "title": item.title or Path(item.file_path).stem,
            "filename": item.filename,
            "category": category.key,
            "rootPath": category.root_path,
            "relativePath": os.path.relpath(item.file_path, category.root_path),
            "mediaType": metadata.get("media_type") or category.media_type,
            "storageFormat": category.storage_format,
            "fileSize": file_size,
            "lastModified": mtime,
            "scannerSignature": scanner_signature,
            "scannedAt": scanned_at,
            "sourcePath": item.file_path,
        }
    )
    metadata.pop("media_type", None)
    return metadata


def _record_needs_update(existing: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
    existing_meta = _ensure_metadata(existing.get("metadata"))

    if existing.get("title") != metadata["title"]:
        return True
    if existing.get("media_type") != metadata.get("mediaType"):
        return True
    if existing.get("status") != STATUS_AVAILABLE:
        return True
    if existing_meta.get("scannerSignature") != metadata.get("scannerSignature"):
        return True
    if existing_meta.get("storageFormat") != metadata.get("storageFormat"):
        return True
    if existing_meta.get("relativePath") != metadata.get("relativePath"):
        return True
    return False


def _ensure_metadata(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalise_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _original_path(row: Dict[str, Any]) -> str:
    path = row.get("source_path")
    return path or ""


def _sync_media_settings(cursor, categories: Sequence[MediaCategory]) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value JSONB NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )

    cursor.execute("SELECT value FROM system_settings WHERE key = %s", ("database",))
    row = cursor.fetchone()
    if row and isinstance(row.get("value"), dict):
        settings = row["value"]
    elif row and isinstance(row.get("value"), str):
        try:
            settings = json.loads(row["value"])
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    directories = settings.get("media_scan_directories") or {}
    if not isinstance(directories, dict):
        directories = {}

    for category in categories:
        directories[category.key] = category.root_path

    settings["media_scan_directories"] = directories
    if "media_scan_root" not in settings and categories:
        settings["media_scan_root"] = categories[0].root_path

    cursor.execute(
        """
        INSERT INTO system_settings (key, value, updated_at)
        VALUES (%s, %s::jsonb, NOW())
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """,
        ("database", json.dumps(settings)),
    )


def _write_deletion_log(entries: Iterable[Dict[str, Any]]) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as stream:
            for entry in entries:
                stream.write(json.dumps(entry, ensure_ascii=False))
                stream.write("\n")
    except Exception as exc:
        logger.warning("Failed to write media deletion log: %s", exc)
