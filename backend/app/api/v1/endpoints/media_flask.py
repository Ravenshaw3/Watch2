"""
Flask-compatible media endpoints extracted from working flask_simple.py
"""

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from postgres_config import get_db_connection
from app.services.media_maintenance import STATUS_AVAILABLE
from app.services.media_ingestion import (
    save_uploaded_file,
    delete_media_file_record,
    generate_file_metadata,
)
from .settings_flask import ensure_settings_table
from config_loader import load_media_config
import os
import json
import hashlib
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import io
import mimetypes
from base64 import b64decode
sys.path.append('/app')
from app.core.enhanced_scanner import EnhancedMediaScanner
from pathlib import Path

_DEFAULT_POSTER_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)

router = Blueprint('media', __name__)


def _ensure_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return metadata if isinstance(metadata, dict) else {}


def _metadata_value(metadata: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in metadata and metadata[key] not in (None, ""):
            return metadata[key]
    return default


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _isoformat(value: Any) -> Optional[str]:
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def _map_media_item_row(row: Dict[str, Any]) -> Dict[str, Any]:
    metadata = _ensure_metadata(row.get('metadata'))

    file_size = _to_int(
        _metadata_value(metadata, 'fileSize', 'sizeBytes', 'size'),
        default=0,
    )
    file_path = row.get('source_path') or _metadata_value(
        metadata,
        'sourcePath',
        'filePath',
        'path',
        default='',
    )
    duration_seconds = _to_float(
        row.get('duration_seconds')
        or metadata.get('duration')
        or metadata.get('durationSeconds'),
        default=None,
    )

    filename = _metadata_value(metadata, 'filename', 'fileName', 'name', default=row.get('title') or '')
    original_filename = _metadata_value(metadata, 'originalFilename', 'original_name', default=None)

    created_at = _isoformat(row.get('created_at'))
    updated_at = _isoformat(row.get('updated_at'))

    media_type = row.get('media_type')

    mapped = {
        'id': str(row.get('id')) if row.get('id') is not None else None,
        'title': row.get('title'),
        'description': row.get('description'),
        'media_type': media_type,
        'mediaType': media_type,
        'status': row.get('status'),
        'filename': filename,
        'original_filename': original_filename,
        'file_path': file_path,
        'source_path': file_path,
        'sourcePath': file_path,
        'file_size': file_size,
        'fileSize': file_size,
        'mime_type': _metadata_value(metadata, 'mimeType', 'contentType'),
        'category': media_type,
        'duration_seconds': duration_seconds,
        'durationSeconds': duration_seconds,
        'duration': duration_seconds,
        'thumbnail_path': _metadata_value(metadata, 'thumbnailPath', 'thumbnail_path'),
        'poster_path': _metadata_value(metadata, 'posterPath', 'poster_path'),
        'artwork': _metadata_value(metadata, 'artwork'),
        'uploaded_by': _metadata_value(metadata, 'uploadedBy', 'uploader'),
        'last_accessed': _metadata_value(metadata, 'lastAccessed'),
        'metadata': metadata,
        'created_at': created_at,
        'createdAt': created_at,
        'updated_at': updated_at,
        'updatedAt': updated_at,
    }

    return mapped

@router.route('', methods=['OPTIONS'], strict_slashes=False)
@router.route('/', methods=['OPTIONS'], strict_slashes=False)
def media_options():
    """Handle CORS preflight without authentication."""
    return ('', 204)


@router.route('', methods=['GET'], strict_slashes=False)
@router.route('/', methods=['GET'], strict_slashes=False)
@jwt_required()
def get_media():
    """Get media files with pagination from the `media_items` table."""
    conn = None
    cursor = None
    try:
        page = max(int(request.args.get('page', 1) or 1), 1)
        raw_limit = request.args.get('limit') or request.args.get('page_size') or 24
        limit = max(int(raw_limit), 1)

        status_filter = request.args.get('status')
        media_type_filter = request.args.get('media_type') or request.args.get('category')
        search_term = request.args.get('search')

        sort_by_param = (request.args.get('sort_by') or 'created_at').lower()
        sort_order_param = (request.args.get('sort_order') or 'desc').lower()
        sort_direction = 'DESC' if sort_order_param == 'desc' else 'ASC'
        if sort_direction not in ('ASC', 'DESC'):
            sort_direction = 'ASC'

        if sort_by_param == 'title':
            sort_column = 'title'
        elif sort_by_param == 'duration':
            sort_column = 'duration_seconds'
        elif sort_by_param == 'status':
            sort_column = 'status'
        elif sort_by_param == 'filename':
            sort_column = "COALESCE(metadata->>'filename', title)"
        elif sort_by_param == 'file_size':
            sort_column = "COALESCE(NULLIF(metadata->>'fileSize', ''), '0')::numeric"
        else:
            sort_column = 'created_at'

        filters = []
        params = []

        if status_filter:
            filters.append('status = %s')
            params.append(status_filter)

        if media_type_filter:
            filters.append('media_type = %s')
            params.append(media_type_filter)

        if search_term:
            like_term = f"%{search_term}%"
            filters.append(
                "(title ILIKE %s OR description ILIKE %s OR "
                "metadata->>'filename' ILIKE %s OR metadata->>'originalFilename' ILIKE %s)"
            )
            params.extend([like_term, like_term, like_term, like_term])

        where_clause = ' AND '.join(filters) if filters else 'TRUE'

        conn = get_db_connection()
        cursor = conn.cursor()

        count_query = f"SELECT COUNT(*) as count FROM media_items WHERE {where_clause}"
        cursor.execute(count_query, params)
        total_row = cursor.fetchone() or {'count': 0}
        total_count = _to_int(total_row.get('count'), default=0)

        offset = (page - 1) * limit
        query = f"""
            SELECT id, title, description, media_type, source_path, status,
                   metadata, duration_seconds, created_at, updated_at
            FROM media_items
            WHERE {where_clause}
            ORDER BY {sort_column} {sort_direction}
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [limit, offset])
        rows = cursor.fetchall() or []
        media_items = [_map_media_item_row(row) for row in rows]

        cursor.execute(
            """
            SELECT COALESCE(media_type, 'unknown') AS category, COUNT(*) AS count
            FROM media_items
            GROUP BY media_type
            ORDER BY category
            """
        )
        category_rows = cursor.fetchall() or []
        categories = {row['category']: _to_int(row['count'], default=0) for row in category_rows}

        return jsonify({
            'items': media_items,
            'total': total_count,
            'page': page,
            'page_size': limit,
            'categories': categories
        })

    except Exception as e:
        print(f"Media error: {e}")
        return jsonify({"detail": f"Media error: {str(e)}"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@router.route('/upload', methods=['POST'])
@jwt_required()
def upload_media():
    """Upload a media file and create a record in `media_items`."""
    if 'file' not in request.files:
        return jsonify({"detail": "No file part in request"}), 400

    uploaded_file = request.files['file']
    if not uploaded_file or uploaded_file.filename == '':
        return jsonify({"detail": "Empty filename"}), 400

    form = request.form or {}
    category_key = form.get('category')
    title = form.get('title')
    description = form.get('description')

    try:
        config = load_media_config()
    except Exception as exc:
        print(f"Config load error: {exc}")
        return jsonify({"detail": "Failed to load media configuration"}), 500

    categories = {cat.key: cat for cat in config.categories}
    category = None
    if category_key:
        category = categories.get(category_key)
        if category is None:
            return jsonify({"detail": f"Unknown category '{category_key}'"}), 400
    else:
        category = config.default_category or (config.categories[0] if config.categories else None)

    if category is None:
        return jsonify({"detail": "No media categories configured"}), 500

    saved_path = None
    conn = None
    cursor = None
    try:
        saved_path = save_uploaded_file(
            uploaded_file,
            destination_dir=category.root_path,
            preferred_name=uploaded_file.filename,
        )

        metadata = generate_file_metadata(
            saved_path,
            category=category,
            title=title,
            description=description,
            uploader=request.form.get('uploaded_by') or request.form.get('uploader') or request.form.get('user'),
            mime_type=uploaded_file.mimetype,
            original_filename=uploaded_file.filename,
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO media_items (title, description, media_type, source_path, status, metadata, duration_seconds)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING id, title, description, media_type, source_path, status,
                      metadata, duration_seconds, created_at, updated_at
            """,
            (
                metadata.get('title'),
                description or metadata.get('description'),
                metadata.get('mediaType'),
                metadata.get('sourcePath'),
                STATUS_AVAILABLE,
                json.dumps(metadata),
                metadata.get('durationSeconds'),
            ),
        )
        inserted_row = cursor.fetchone()
        conn.commit()

        response_payload = _map_media_item_row(inserted_row)
        return jsonify({
            "status": "uploaded",
            "item": response_payload,
        }), 201

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        if saved_path and Path(saved_path).exists():
            try:
                os.remove(saved_path)
            except OSError:
                pass
        print(f"Upload media error: {exc}")
        return jsonify({"detail": f"Upload media error: {str(exc)}"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@router.route('/<media_id>', methods=['GET'])
@jwt_required()
def get_media_detail(media_id):
    """Return a single media item."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, description, media_type, source_path, status,
                   metadata, duration_seconds, created_at, updated_at
            FROM media_items
            WHERE id = %s
            """,
            (media_id,),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"detail": "Media not found"}), 404
        return jsonify(_map_media_item_row(row))
    except Exception as exc:
        print(f"Media detail error: {exc}")
        return jsonify({"detail": f"Media detail error: {str(exc)}"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@router.route('/<media_id>', methods=['DELETE'])
@jwt_required()
def delete_media(media_id):
    """Delete a media item and optionally remove the backing file."""
    conn = None
    cursor = None
    try:
        toggle_only = request.args.get('soft', 'false').lower() in ('true', '1', 'yes')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_path, metadata FROM media_items WHERE id = %s",
            (media_id,),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"detail": "Media not found"}), 404

        metadata = _ensure_metadata(row.get('metadata'))
        file_path = row.get('source_path') or metadata.get('sourcePath')

        if toggle_only:
            cursor.execute(
                "UPDATE media_items SET status = %s, updated_at = NOW() WHERE id = %s",
                ('deleted', media_id),
            )
            conn.commit()
            return jsonify({"status": "deleted", "mode": "soft"})

        delete_media_file_record(cursor, media_id)
        conn.commit()

        if file_path:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
            except PermissionError as exc:
                print(f"Unable to delete media file {file_path}: {exc}")

        return jsonify({"status": "deleted", "mode": "hard"})

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        print(f"Delete media error: {exc}")
        return jsonify({"detail": f"Delete media error: {str(exc)}"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

def _format_bytes(size: int) -> str:
    if size <= 0:
        return "0 Bytes"
    units = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB']
    idx = 0
    value = float(size)
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.2f} {units[idx]}"


SUPPORTED_SCAN_EXTENSIONS = sorted({
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
    '.mpg', '.mpeg', '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'
})


@router.route('/scan-info', methods=['GET'])
@jwt_required()
def get_scan_info():
    """Get media scan information in a frontend-friendly structure"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            ensure_settings_table(cursor)

            # Load persisted scan directory if available
            cursor.execute('SELECT value FROM system_settings WHERE key = %s', ('database',))
            db_row = cursor.fetchone() or {}
            database_settings = db_row.get('value') if isinstance(db_row.get('value'), dict) else {}
            scan_directory = (database_settings.get('media_scan_root') or '/app/media').strip()

            cursor.execute(
                "SELECT media_type, metadata, duration_seconds FROM media_items"
            )
            rows = cursor.fetchall() or []

            total_files = len(rows)
            total_size_bytes = 0
            categories: Dict[str, Dict[str, Any]] = {}

            for row in rows:
                metadata = _ensure_metadata(row.get('metadata'))
                total_size_bytes += _to_int(
                    _metadata_value(metadata, 'fileSize', 'sizeBytes', 'size'),
                    default=0,
                )

                category_key = row.get('media_type') or 'uncategorized'
                if not category_key:
                    category_key = 'uncategorized'
                if category_key not in categories:
                    categories[category_key] = {
                        'count': 0,
                        'display_name': category_key.replace('_', ' ').title(),
                    }
                categories[category_key]['count'] += 1

            scan_directory_exists = bool(scan_directory and os.path.isdir(scan_directory))

            return jsonify({
                'directory_info': {
                    'scan_directory': scan_directory,
                    'scan_directory_exists': scan_directory_exists,
                    'supported_extensions': SUPPORTED_SCAN_EXTENSIONS,
                },
                'library_stats': {
                    'total_media_files': total_files,
                    'total_size_bytes': total_size_bytes,
                    'total_size_formatted': _format_bytes(total_size_bytes),
                    'categories': categories,
                },
                'scan_status': 'idle',
                'last_scan': None,
            })
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Scan info error: {e}")
        return jsonify({"detail": f"Scan info error: {str(e)}"}), 500

@router.route('/<media_id>/stream', methods=['GET', 'HEAD', 'OPTIONS'])
@jwt_required(optional=True)  # Allow token in query parameter
def stream_media(media_id):
    """Stream media file with range request support"""
    conn = None
    cursor = None
    try:
        token = request.args.get('token')
        if token:
            from flask_jwt_extended import decode_token
            try:
                decode_token(token)
            except Exception:
                return jsonify({"detail": "Invalid token"}), 401

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT source_path, metadata FROM media_items WHERE id = %s",
            (media_id,),
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({"detail": "Media not found"}), 404

        metadata = _ensure_metadata(row.get('metadata'))
        source_path = row.get('source_path') or _metadata_value(
            metadata,
            'sourcePath',
            'filePath',
            'path',
            default=None,
        )

        if not source_path:
            return jsonify({"detail": "Media source path unavailable"}), 404

        file_path = Path(source_path)
        if not file_path.exists():
            return jsonify({"detail": "Media file not found on disk"}), 404

        download_name = _metadata_value(
            metadata,
            'filename',
            'fileName',
            'name',
            default=file_path.name,
        )

        range_header = request.headers.get('Range')
        file_size = file_path.stat().st_size

        if range_header:
            byte_start = 0
            byte_end = file_size - 1

            if range_header.startswith('bytes='):
                parts = range_header[6:].split('-')
                if parts[0]:
                    byte_start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    byte_end = int(parts[1])

            byte_start = max(0, byte_start)
            byte_end = min(file_size - 1, byte_end)
            if byte_start > byte_end:
                byte_start, byte_end = 0, file_size - 1

            content_length = byte_end - byte_start + 1

            with open(file_path, 'rb') as f:
                f.seek(byte_start)
                data = f.read(content_length)

            response = send_file(
                io.BytesIO(data),
                mimetype=mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream',
                as_attachment=False,
                download_name=download_name,
            )
            response.status_code = 206
            response.headers['Content-Range'] = f'bytes {byte_start}-{byte_end}/{file_size}'
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Length'] = str(content_length)

            if request.method == 'HEAD':
                response.response = []
                response.direct_passthrough = False

            return response

        response = send_file(
            file_path,
            mimetype=mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream',
            as_attachment=False,
            download_name=download_name,
        )
        if request.method == 'HEAD':
            response.response = []
            response.direct_passthrough = False
        return response

    except Exception as e:
        print(f"Stream error: {e}")
        return jsonify({"detail": f"Media error: {str(e)}"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@router.route('/<media_id>/poster', methods=['GET', 'HEAD'])
@jwt_required(optional=True)
def get_media_poster(media_id):
    """Serve poster or thumbnail image for a media item from metadata."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT metadata FROM media_items WHERE id = %s",
            (media_id,),
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({"detail": "Media not found"}), 404

        metadata = _ensure_metadata(row.get('metadata'))
        poster_path = _metadata_value(
            metadata,
            'posterPath',
            'poster_path',
            'thumbnailPath',
            'thumbnail_path',
            default=None,
        )
        poster_data = _metadata_value(
            metadata,
            'posterData',
            'posterBase64',
            'thumbnailData',
            default=None,
        )

        if poster_path:
            file_path = Path(poster_path)
            if not file_path.is_absolute():
                file_path = Path(poster_path).resolve()

            if file_path.exists() and file_path.is_file():
                mimetype = mimetypes.guess_type(str(file_path))[0] or 'image/jpeg'
                response = send_file(file_path, mimetype=mimetype, as_attachment=False)
                if request.method == 'HEAD':
                    response.response = []
                    response.direct_passthrough = False
                return response

        if poster_data:
            try:
                if isinstance(poster_data, str):
                    encoded = poster_data
                    mimetype = 'image/jpeg'
                    if poster_data.startswith('data:') and ';base64,' in poster_data:
                        mimetype = poster_data.split(';base64,', 1)[0].replace('data:', '')
                        encoded = poster_data.split(';base64,', 1)[1]
                    binary = b64decode(encoded)
                else:
                    binary = poster_data
                    mimetype = 'image/jpeg'

                response = send_file(
                    io.BytesIO(binary),
                    mimetype=mimetype,
                    as_attachment=False,
                    download_name=f"{media_id}.jpg",
                )
                if request.method == 'HEAD':
                    response.response = []
                    response.direct_passthrough = False
                return response
            except Exception as decode_error:
                print(f"Poster decode error for {media_id}: {decode_error}")

        response = send_file(
            io.BytesIO(_DEFAULT_POSTER_BYTES),
            mimetype='image/png',
            as_attachment=False,
            download_name=f"{media_id}-placeholder.png",
        )
        if request.method == 'HEAD':
            response.response = []
            response.direct_passthrough = False
        return response

    except Exception as e:
        print(f"Poster error: {e}")
        return jsonify({"detail": f"Poster error: {str(e)}"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@router.route('/categories', methods=['GET'])
@jwt_required()
def get_media_categories():
    """Get media categories with counts from `media_items`."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT COALESCE(media_type, 'unknown') AS category, COUNT(*) AS count
            FROM media_items
            GROUP BY media_type
            ORDER BY category
            """
        )

        categories: Dict[str, int] = {}
        for row in cursor.fetchall() or []:
            categories[row['category']] = _to_int(row['count'], default=0)

        return jsonify(categories)

    except Exception as e:
        print(f"Categories error: {e}")
        return jsonify({"detail": f"Categories error: {str(e)}"}), 500

@router.route('/scan-unraid', methods=['POST'])
@jwt_required()
def scan_unraid_media():
    """Scan Unraid media using direct T: drive access (bypasses Docker mount issues)"""
    try:
        # Check admin permissions
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT is_superuser FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        # Get request parameters
        data = request.get_json() or {}
        scan_method = data.get('scan_method', 'direct_t_drive')
        
        print(f"Starting Unraid scan with method: {scan_method}")
        
        # Import and run the unified Unraid scanner
        import subprocess
        import os
        
        # Run the unified scanner as a subprocess
        scanner_path = '/app/tools/unified-unraid-scanner.py'
        
        # Set environment variables for the scanner
        env = os.environ.copy()
        env['ENV_TYPE'] = 'local'
        env['UNRAID_ACCESS_METHOD'] = 'direct_scanner'
        env['T_DRIVE_PATH'] = 'T:\\'
        
        # Run the scanner with a timeout
        try:
            result = subprocess.run([
                'python', '/app/tools/unified-unraid-scanner.py'
            ], capture_output=True, text=True, timeout=300, env=env, cwd='/app')
            
            if result.returncode == 0:
                # Parse the output to extract scan results
                output_lines = result.stdout.strip().split('\n')
                
                # Look for the results summary
                total_files = 0
                categories_found = {}
                
                for line in output_lines:
                    if 'TOTAL FILES FOUND:' in line:
                        try:
                            total_files = int(line.split(':')[1].strip())
                        except:
                            pass
                    elif '|' in line and 'files |' in line:
                        # Parse category results like "movies | collection | 732 files | [MOUNT]"
                        parts = line.split('|')
                        if len(parts) >= 3:
                            category = parts[0].strip()
                            files_part = parts[2].strip()
                            if 'files' in files_part:
                                try:
                                    file_count = int(files_part.split()[0])
                                    categories_found[category] = file_count
                                except:
                                    pass
                
                return jsonify({
                    "message": "Unraid media scan completed successfully via direct T: drive access",
                    "scan_method": scan_method,
                    "total_files_found": total_files,
                    "files_added": 0,  # Scanner doesn't update DB directly
                    "files_updated": 0,
                    "directories_scanned": len(categories_found),
                    "scan_results": categories_found,
                    "scan_status": "completed",
                    "scanner_output": output_lines[-5:] if len(output_lines) > 5 else output_lines,
                    "note": "Files scanned from T: drive. Results show available media but are not imported to database."
                })
            else:
                return jsonify({
                    "detail": f"Unraid scanner failed with return code {result.returncode}",
                    "error_output": result.stderr[:500] if result.stderr else "No error output",
                    "scan_method": scan_method
                }), 500
                
        except subprocess.TimeoutExpired:
            return jsonify({
                "detail": "Unraid scan timed out (5 minutes)",
                "scan_method": scan_method
            }), 408
        except FileNotFoundError:
            return jsonify({
                "detail": "Unraid scanner script not found",
                "scan_method": scan_method,
                "note": "Direct T: drive scanner is not available in this container"
            }), 404
            
    except Exception as e:
        print(f"Unraid scan error: {e}")
        return jsonify({"detail": f"Unraid scan error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
