"""
Flask-compatible admin maintenance endpoints for AdminMaintenance.vue
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from psycopg2 import sql
from postgres_config import get_db_connection
from app.services.media_maintenance import (
    MediaMaintenanceError,
    run_media_maintenance_scan,
)
import json
import os
import time
from datetime import datetime

router = Blueprint('admin', __name__)

# Simple job tracking (in production, use Redis or database)
job_counter = 1
jobs_db = {}


DEFAULT_BACKUP_DIR = os.getenv('WATCH1_BACKUP_DIR', '/app/data/backups')


def ensure_settings_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value JSONB NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )


def get_database_settings(cursor):
    ensure_settings_table(cursor)
    cursor.execute('SELECT value FROM system_settings WHERE key = %s', ('database',))
    row = cursor.fetchone()
    if row and isinstance(row.get('value'), dict):
        return row['value']
    if row and isinstance(row.get('value'), str):
        try:
            return json.loads(row['value'])
        except json.JSONDecodeError:
            return {}


def table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        ) AS exists
        """,
        (table_name,),
    )
    row = cursor.fetchone()
    return bool(row and row.get('exists'))


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
        ) AS exists
        """,
        (table_name, column_name),
    )
    row = cursor.fetchone()
    return bool(row and row.get('exists'))


def get_table_count(cursor, table_name: str) -> int:
    if not table_exists(cursor, table_name):
        return 0

    cursor.execute(
        sql.SQL("SELECT COUNT(*) AS count FROM {}" ).format(sql.Identifier(table_name))
    )
    row = cursor.fetchone()
    return int(row['count']) if row and row.get('count') is not None else 0


def get_sum(cursor, table_name: str, column_name: str) -> int:
    if not table_exists(cursor, table_name) or not column_exists(cursor, table_name, column_name):
        return 0

    cursor.execute(
        sql.SQL("SELECT COALESCE(SUM({}), 0) AS total FROM {}" ).format(
            sql.Identifier(column_name),
            sql.Identifier(table_name),
        )
    )
    row = cursor.fetchone()
    return int(row['total']) if row and row.get('total') is not None else 0

def create_job(job_name, status='queued'):
    """Create a new maintenance job"""
    global job_counter
    job_id = job_counter
    job_counter += 1
    
    job = {
        'id': job_id,
        'job_name': job_name,
        'status': status,
        'details': None,
        'started_at': datetime.utcnow().isoformat() + 'Z',
        'finished_at': None,
        'duration_seconds': None,
        'result': None,
        'running': status == 'running'
    }
    
    jobs_db[job_id] = job
    return job

def complete_job(job_id, status='success', result=None):
    """Complete a maintenance job"""
    if job_id in jobs_db:
        job = jobs_db[job_id]
        job['status'] = status
        job['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        job['running'] = False
        job['result'] = result
        
        # Calculate duration
        started = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
        finished = datetime.fromisoformat(job['finished_at'].replace('Z', '+00:00'))
        job['duration_seconds'] = (finished - started).total_seconds()

@router.route('/database/info', methods=['GET'])
@jwt_required()
def get_database_info():
    """Get database information for AdminMaintenance.vue"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        # Table counts aligned with Drizzle schema
        users_count = get_table_count(cursor, 'users')
        media_items_count = get_table_count(cursor, 'media_items')
        playlists_count = get_table_count(cursor, 'playlists')
        playlist_items_count = get_table_count(cursor, 'playlist_items')

        # Best-effort media size — only computed if a numeric column exists
        total_size = 0
        for candidate_column in ('file_size', 'size_bytes', 'size'):    # legacy support if present
            total_size = get_sum(cursor, 'media_items', candidate_column)
            if total_size:
                break
        
        # Database version
        cursor.execute("SELECT version() as version")
        db_version = cursor.fetchone()['version']
        
        return jsonify({
            "environment": os.getenv('FLASK_ENV', 'production'),
            "database_type": "PostgreSQL",
            "database_version": db_version,
            "total_size": total_size,
            "tables": {
                "users": users_count,
                "media_items": media_items_count,
                "playlists": playlists_count,
                "playlist_items": playlist_items_count
            }
        })
        
    except Exception as e:
        print(f"Database info error: {e}")
        return jsonify({"detail": f"Database info error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@router.route('/database/backups', methods=['GET'])
@jwt_required()
def list_backups():
    """List available database backups"""
    try:
        user_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403

        db_settings = get_database_settings(cursor)
        backup_directory = (db_settings.get('backup_directory') or '').strip()
        if not backup_directory:
            backup_directory = DEFAULT_BACKUP_DIR

        items = []
        if os.path.isdir(backup_directory):
            try:
                for entry in sorted(os.scandir(backup_directory), key=lambda e: e.name):
                    if entry.is_file():
                        stats = entry.stat()
                        items.append({
                            'file': entry.name,
                            'path': entry.path,
                            'size': stats.st_size,
                            'createdAt': datetime.fromtimestamp(stats.st_mtime).isoformat()
                        })
            except PermissionError:
                return jsonify({
                    "detail": "Permission denied when accessing backup directory",
                    "directory": backup_directory,
                    "items": []
                }), 500

        return jsonify({
            "directory": backup_directory,
            "items": items
        })

    except Exception as e:
        print(f"List backups error: {e}")
        return jsonify({"detail": f"List backups error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@router.route('/database/clean', methods=['POST'])
@jwt_required()
def clean_orphans():
    """Clean orphan records"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        
        apply = data.get('apply', False)
        if isinstance(apply, str):
            apply = apply.lower() in ('true', '1', 'yes')
        
        delete_rows = data.get('delete', False)
        if isinstance(delete_rows, str):
            delete_rows = delete_rows.lower() in ('true', '1', 'yes')
        
        # Create job
        job_name = f"clean-orphans-{'delete' if delete_rows else 'mark'}" if apply else "clean-orphans-dry-run"
        job = create_job(job_name, 'running')
        
        # Simulate orphan cleaning
        time.sleep(1)  # Simulate work
        
        # Mock result
        result = {
            "orphan_media_files": 0,
            "orphan_playlist_items": 0,
            "action_taken": "deleted" if delete_rows else "marked_deleted" if apply else "dry_run"
        }
        
        complete_job(job['id'], 'success', result)
        
        return jsonify({
            "job_id": job['id'],
            "status": "completed",
            "submitted_at": job['started_at']
        })
        
    except Exception as e:
        print(f"Clean orphans error: {e}")
        return jsonify({"detail": f"Clean orphans error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@router.route('/database/prune', methods=['POST'])
@jwt_required()
def prune_test_media():
    """Prune test media"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        data = request.get_json() or {}
        apply = data.get('apply', False)
        delete_rows = data.get('delete', False)
        patterns = data.get('patterns', ['test', 'sample', 'demo'])
        
        # Create job
        job_name = f"prune-test-media-{'delete' if delete_rows else 'mark'}" if apply else "prune-test-media-dry-run"
        job = create_job(job_name, 'running')
        
        # Simulate test media pruning
        time.sleep(1)  # Simulate work
        
        # Mock result
        result = {
            "test_media_found": 2,
            "patterns_used": patterns,
            "action_taken": "deleted" if delete_rows else "marked_deleted" if apply else "dry_run"
        }
        
        complete_job(job['id'], 'success', result)
        
        return jsonify({
            "job_id": job['id'],
            "status": "completed",
            "submitted_at": job['started_at']
        })
        
    except Exception as e:
        print(f"Prune test media error: {e}")
        return jsonify({"detail": f"Prune test media error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@router.route('/database/verify-posters', methods=['POST'])
@jwt_required()
def verify_posters():
    """Verify poster data"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        data = request.get_json() or {}
        rebuild = data.get('rebuild', False)
        
        # Create job
        job_name = "verify-posters-rebuild" if rebuild else "verify-posters"
        job = create_job(job_name, 'running')
        
        # Simulate poster verification
        time.sleep(2)  # Simulate work
        
        # Mock result
        result = {
            "total_media": 5,
            "missing_posters": 3,
            "action_taken": "rebuilt" if rebuild else "verified"
        }
        
        complete_job(job['id'], 'success', result)
        
    except Exception as e:
        print(f"Verify posters error: {e}")
        return jsonify({"detail": f"Verify posters error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@router.route('/media/maintenance-scan', methods=['POST'])
@jwt_required()
def maintenance_scan():
    """Run the unified media maintenance scanner."""
    conn = None
    cursor = None
    try:
        user_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403

        payload = request.get_json(silent=True) or {}
        category_keys = payload.get('categories')
        dry_run = bool(payload.get('dry_run', False))
        limit = payload.get('limit')

        if category_keys is not None and not isinstance(category_keys, (list, tuple)):
            return jsonify({"detail": "'categories' must be a list when provided"}), 400

        if limit is not None:
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                return jsonify({"detail": "'limit' must be an integer"}), 400

        try:
            summary = run_media_maintenance_scan(
                categories=category_keys,
                dry_run=dry_run,
                limit=limit,
            )
        except MediaMaintenanceError as exc:
            return jsonify({"detail": str(exc)}), 400

        return jsonify({
            "status": "completed",
            "dry_run": dry_run,
            "summary": summary,
        })

    except Exception as e:
        print(f"Maintenance scan error: {e}")
        return jsonify({"detail": f"Maintenance scan error: {str(e)}"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

@router.route('/database/backup', methods=['POST'])
@jwt_required()
def create_backup():
    """Create database backup"""
    try:
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        data = request.get_json() or {}
        format_type = data.get('format', 'plain')
        output = data.get('output')
        
        # Create job
        job_name = f"backup-{format_type}"
        job = create_job(job_name, 'running')
        
        # Simulate backup creation
        time.sleep(3)  # Simulate work
        
        # Mock result
        backup_file = f"/app/data/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        result = {
            "backup_file": backup_file,
            "format": format_type,
            "size_bytes": 1024000,
            "tables_backed_up": 4
        }
        
        complete_job(job['id'], 'success', result)
        
        return jsonify({
            "job_id": job['id'],
            "status": "completed",
            "submitted_at": job['started_at']
        })
        
    except Exception as e:
        print(f"Create backup error: {e}")
        return jsonify({"detail": f"Create backup error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@router.route('/database/jobs', methods=['GET'])
@jwt_required()
def get_job_history():
    """Get maintenance job history"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        limit = int(request.args.get('limit', 20))
        
        # Get recent jobs (sorted by ID descending)
        recent_jobs = sorted(jobs_db.values(), key=lambda x: x['id'], reverse=True)[:limit]
        
        return jsonify({
            "jobs": recent_jobs
        })
        
    except Exception as e:
        print(f"Get job history error: {e}")
        return jsonify({"detail": f"Get job history error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@router.route('/database/jobs/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job_status(job_id):
    """Get job status"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        if job_id not in jobs_db:
            return jsonify({"detail": "Job not found"}), 404
        
        job = jobs_db[job_id]
        return jsonify(job)
        
    except Exception as e:
        print(f"Get job status error: {e}")
        return jsonify({"detail": f"Get job status error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@router.route('/database/jobs/<int:job_id>', methods=['DELETE'])
@jwt_required()
def cancel_job(job_id):
    """Cancel a job"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        if job_id not in jobs_db:
            return jsonify({"detail": "Job not found"}), 404
        
        job = jobs_db[job_id]
        if not job['running']:
            return jsonify({"detail": "Job is not running"}), 400
        
        # Cancel the job
        complete_job(job_id, 'cancelled', {"message": "Job cancelled by user"})
        
        return jsonify({
            "job_id": job_id,
            "status": "cancelled"
        })
        
    except Exception as e:
        print(f"Cancel job error: {e}")
        return jsonify({"detail": f"Cancel job error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@router.route('/worker/health', methods=['GET'])
@jwt_required()
def get_worker_health():
    """Get worker health status"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is superuser
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_superuser FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user or not user['is_superuser']:
            return jsonify({"detail": "Not enough permissions"}), 403
        
        # Mock worker health data
        running_jobs = [job['id'] for job in jobs_db.values() if job['running']]
        pending_jobs = []  # No pending jobs in this simple implementation
        
        return jsonify({
            "max_workers": 4,
            "running": len(running_jobs),
            "pending_jobs": pending_jobs,
            "completed_result_cache": len(jobs_db) - len(running_jobs)
        })
        
    except Exception as e:
        print(f"Get worker health error: {e}")
        return jsonify({"detail": f"Get worker health error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
