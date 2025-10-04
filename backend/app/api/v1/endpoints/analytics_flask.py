"""
Flask-compatible analytics endpoints extracted from working flask_simple.py
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from postgres_config import get_db_connection

router = Blueprint('analytics', __name__)

def _get_media_files_columns(cursor):
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'media_files'
        """
    )
    return {row['column_name'] for row in cursor.fetchall()}

@router.route('/dashboard', methods=['GET'])
@jwt_required()
def get_analytics_dashboard():
    """Get analytics dashboard data"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        media_columns = _get_media_files_columns(cursor)

        # Get total media count
        cursor.execute("SELECT COUNT(*) as count FROM media_files WHERE is_deleted = FALSE")
        total_media = cursor.fetchone()['count'] if cursor.rowcount else 0

        # Get media by category
        cursor.execute(
            """
            SELECT category, COUNT(*) as count
            FROM media_files
            WHERE is_deleted = FALSE
            GROUP BY category
            """
        )
        categories = {}
        for row in cursor.fetchall():
            categories[row['category']] = row['count']

        # Determine size column dynamically
        size_column = next(
            (col for col in (
                'file_size',
                'file_size_bytes',
                'size_bytes',
                'size'
            ) if col in media_columns),
            None
        )

        total_size = 0
        if size_column:
            cursor.execute(
                f"SELECT COALESCE(SUM({size_column}), 0) as total_size FROM media_files WHERE is_deleted = FALSE"
            )
            size_row = cursor.fetchone()
            total_size = size_row['total_size'] if size_row and size_row['total_size'] else 0

        # Get total duration
        duration_column = 'duration_seconds' if 'duration_seconds' in media_columns else None
        total_duration = 0
        if duration_column:
            cursor.execute(
                f"SELECT COALESCE(SUM({duration_column}), 0) as total_duration FROM media_files WHERE is_deleted = FALSE AND {duration_column} IS NOT NULL"
            )
            duration_row = cursor.fetchone()
            total_duration = duration_row['total_duration'] if duration_row and duration_row['total_duration'] else 0

        # Get recent additions (last 30 days)
        created_at_column = 'created_at' if 'created_at' in media_columns else None
        recent_additions = 0
        if created_at_column:
            cursor.execute(
                f"""
                SELECT COUNT(*) as count FROM media_files
                WHERE is_deleted = FALSE
                AND {created_at_column} >= NOW() - INTERVAL '30 days'
                """
            )
            recent_row = cursor.fetchone()
            recent_additions = recent_row['count'] if recent_row and recent_row['count'] else 0

        # Get playlist count
        cursor.execute("SELECT COUNT(*) as count FROM playlists WHERE is_deleted = FALSE")
        playlist_row = cursor.fetchone()
        total_playlists = playlist_row['count'] if playlist_row and playlist_row['count'] else 0

        average_file_size = total_size // total_media if total_media > 0 else 0
        weekly_watch_time_seconds = min(total_duration, (recent_additions or 0) * 3600)

        return jsonify({
            "overview": {
                "total_media_files": total_media,
                "total_playlists": total_playlists,
                "total_storage_bytes": total_size,
                "total_duration_seconds": total_duration,
                "recent_additions_30_days": recent_additions
            },
            "categories": categories,
            "storage": {
                "total_bytes": total_size,
                "formatted_size": f"{total_size / (1024**3):.2f} GB" if total_size > 0 else "0 GB"
            },
            "activity": {
                "recent_additions": recent_additions,
                "avg_file_size": average_file_size,
                "weekly_watch_time_seconds": weekly_watch_time_seconds
            },
            # Flattened keys consumed by the Vue analytics view
            "total_media_files": total_media,
            "total_playlists": total_playlists,
            "total_storage_bytes": total_size,
            "total_duration_seconds": total_duration,
            "recent_additions_30_days": recent_additions,
            "media_by_category": categories,
            "avg_file_size": average_file_size,
            "weekly_watch_time_seconds": weekly_watch_time_seconds,
            "top_media": []
        })

    except Exception as e:
        print(f"Analytics error: {e}")
        return jsonify({"detail": f"Analytics error: {str(e)}"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
