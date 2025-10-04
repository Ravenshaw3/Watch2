# Media Maintenance & Ingestion Overview

## Scanner Workflow
- **Service**: `app/services/media_maintenance.py`
- **Entry**: `POST /api/v1/admin/media/maintenance-scan`
- **Flow**:
  1. Load categories from `config/watch_media_dirs.yml` via `config_loader.load_media_config()`. (The legacy copy under `backend/` has been removed.)
  2. Walk category roots with `EnhancedMediaScanner`.
  3. Upsert into `media_items` (insert/update) and mark missing items (`status='missing'`).
  4. Persist per-category roots to `system_settings.media_scan_directories`.
  5. Log missing files to `logs/media_deletions.log` when not in dry-run mode.

### Request Options
- `categories`: Optional list of category keys to limit the scan.
- `dry_run`: Boolean flag to skip commits/logging (defaults to `false`).
- `limit`: Optional integer to cap processed files per category.

### Summary Payload
```json
{
  "scanned_at": "UTC timestamp",
  "dry_run": false,
  "config_version": 2,
  "selected_categories": ["movies", "tv_series"],
  "categories": {
    "movies": {
      "files_found": 120,
      "files_scanned": 120,
      "added": 5,
      "updated": 12,
      "missing": 2,
      "missing_paths": ["/app/media/Movies/Old.MOV"],
      "errors": [],
      "limited": false,
      "dry_run": false,
      "root_exists": true,
      "notes": []
    }
  },
  "totals": {
    "added": 5,
    "updated": 12,
    "unchanged": 103,
    "missing": 2,
    "files_scanned": 120,
    "files_found": 120,
    "categories": 2,
    "logged_missing": 2
  }
}
```

## Upload Ingestion
- **Service**: `app/services/media_ingestion.py`
- **Endpoint**: `POST /api/v1/media/upload`
- Saves incoming multipart upload into the category root, generates metadata aligned with the maintenance scanner, and inserts a `media_items` row with `status='available'`.
- Uses `MediaCategory` defaults when no category is supplied.
- Rolls back DB insert and deletes the file if any error occurs.

### Form Fields
- `file` *(required)*: Media file.
- `category`: Optional category key from config.
- `title`, `description`: Optional metadata overrides.
- `uploaded_by` / `uploader` / `user`: Optional uploader identifier.

## Media API Summary
- `GET /api/v1/media`: Paginated list from `media_items` with filters & sorting.
- `POST /api/v1/media/upload`: Upload + ingest.
- `GET /api/v1/media/<media_id>`: Detail.
- `DELETE /api/v1/media/<media_id>`: Soft delete via `?soft=true` or hard delete (default) with optional file removal.
- `GET /api/v1/media/<media_id>/stream`: File streaming with range support.
- `GET /api/v1/media/<media_id>/poster`: Poster/thumbnail resolution with fallbacks.
- `GET /api/v1/media/categories`: Category counts.
- `GET /api/v1/media/scan-info`: Aggregated library stats.

- Scanner logs missing files to `logs/media_deletions.log` (JSON lines).
- Uploads respect category `root_path` defined in `config/watch_media_dirs.yml`.
- Ensure directories exist and have appropriate permissions before running scans/uploads.

## Cleanup
- **Legacy FastAPI modules (`app/api/v1/endpoints/media.py`, `playlists.py`, `subtitles.py`, `viewing_history.py`) and legacy models/schemas have been removed. Frontend and integrations should target the Flask routes above.**
- **Admin UI proxy**: The Windsurf Admin router forwards maintenance-scan requests to Flask via `/admin/media/maintenance-scan`. Set `FLASK_API_BASE_URL` (see `windsurf-project/.env.example`) so the proxy can reach the Flask backend. Future UI actions (e.g., ingest uploads) should reuse this proxy pattern.
  - Uploads now proxy through `/admin/media/upload`, preserving multipart uploads and auth headers before delegating to `POST /api/v1/media/upload`.
