"""
Flask-compatible playlist endpoints extracted from working flask_simple.py,
updated to match the current frontend API expectations.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from postgres_config import get_db_connection


router = Blueprint('playlists', __name__)


def _playlist_to_dict(row, include_counts: bool = False):
    return {
        'id': row['id'],
        'name': row['name'],
        'description': row.get('description'),
        'is_public': row['is_public'],
        'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
        'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
        'owner_id': row.get('owner_id'),
        **({'items': row.get('items', []), 'item_count': row.get('item_count', 0)} if include_counts else {})
    }


@router.route('/', methods=['GET'])
@jwt_required()
def list_playlists():
    """Return all playlists owned by the current user."""
    try:
        user_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT p.id, p.name, p.description, p.is_public, p.created_at, p.updated_at,
                   p.owner_id, COUNT(pi.id) AS item_count
            FROM playlists p
            LEFT JOIN playlist_items pi ON p.id = pi.playlist_id
            WHERE p.owner_id = %s AND p.is_deleted = FALSE
            GROUP BY p.id
            ORDER BY p.created_at DESC
            """,
            (user_id,),
        )

        playlists = [_playlist_to_dict(row, include_counts=True) for row in cursor.fetchall()]
        return jsonify({'playlists': playlists})
    except Exception as error:  # noqa: BLE001
        print(f"Playlists list error: {error}")
        return jsonify({'detail': 'Failed to load playlists'}), 500


@router.route('/', methods=['POST'])
@jwt_required()
def create_playlist():
    """Create a new playlist for the current user."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        name = (data.get('name') or '').strip()
        description = (data.get('description') or '').strip() or None
        is_public = bool(data.get('is_public', False))

        if not name:
            return jsonify({'detail': 'Playlist name is required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO playlists (name, description, is_public, owner_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, description, is_public, created_at, updated_at, owner_id
            """,
            (name, description, is_public, user_id),
        )

        playlist = cursor.fetchone()
        conn.commit()
        return jsonify(_playlist_to_dict(playlist, include_counts=True)), 201
    except Exception as error:  # noqa: BLE001
        print(f"Create playlist error: {error}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'detail': 'Failed to create playlist'}), 500


@router.route('/<playlist_id>', methods=['GET'])
@jwt_required()
def get_playlist(playlist_id):
    """Get a single playlist with items."""
    try:
        user_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, description, is_public, created_at, updated_at, owner_id
            FROM playlists
            WHERE id = %s AND is_deleted = FALSE
            """,
            (playlist_id,),
        )

        playlist = cursor.fetchone()
        if not playlist:
            return jsonify({'detail': 'Playlist not found'}), 404

        if playlist['owner_id'] != int(user_id):
            return jsonify({'detail': 'Not authorized to view this playlist'}), 403

        cursor.execute(
            """
            SELECT pi.id, pi.position, pi.added_at,
                   m.id AS media_id, m.filename, m.title, m.duration_seconds,
                   m.category, m.file_size
            FROM playlist_items pi
            JOIN media_files m ON pi.media_id = m.id
            WHERE pi.playlist_id = %s AND m.is_deleted = FALSE
            ORDER BY pi.position
            """,
            (playlist_id,),
        )

        items = [
            {
                'item': {
                    'id': row['id'],
                    'playlist_id': playlist_id,
                    'mediaItemId': row['media_id'],
                    'position': row['position'],
                    'addedAt': row['added_at'].isoformat() if row['added_at'] else None,
                },
                'media': {
                    'id': row['media_id'],
                    'title': row.get('title'),
                    'filename': row.get('filename'),
                    'durationSeconds': row.get('duration_seconds'),
                    'category': row.get('category'),
                    'fileSize': row.get('file_size'),
                },
            }
            for row in cursor.fetchall()
        ]

        response = _playlist_to_dict(playlist, include_counts=True)
        response['items'] = items
        response['item_count'] = len(items)
        return jsonify(response)
    except Exception as error:  # noqa: BLE001
        print(f"Get playlist error: {error}")
        return jsonify({'detail': 'Failed to load playlist'}), 500


@router.route('/<playlist_id>', methods=['PUT'])
@jwt_required()
def update_playlist(playlist_id):
    """Update playlist metadata."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT owner_id FROM playlists WHERE id = %s AND is_deleted = FALSE",
            (playlist_id,),
        )
        playlist = cursor.fetchone()
        if not playlist:
            return jsonify({'detail': 'Playlist not found'}), 404
        if playlist['owner_id'] != int(user_id):
            return jsonify({'detail': 'Not authorized to modify this playlist'}), 403

        updates = []
        params = []
        if 'name' in data:
            new_name = (data.get('name') or '').strip()
            if not new_name:
                return jsonify({'detail': 'Playlist name cannot be empty'}), 400
            updates.append('name = %s')
            params.append(new_name)
        if 'description' in data:
            updates.append('description = %s')
            params.append((data.get('description') or '').strip() or None)
        if 'is_public' in data:
            updates.append('is_public = %s')
            params.append(bool(data.get('is_public')))

        if not updates:
            return jsonify({'detail': 'No changes provided'}), 400

        updates.append('updated_at = NOW()')
        params.append(playlist_id)

        cursor.execute(
            f"UPDATE playlists SET {', '.join(updates)} WHERE id = %s RETURNING id",
            params,
        )
        if not cursor.fetchone():
            return jsonify({'detail': 'Playlist update failed'}), 500
        conn.commit()

        cursor.execute(
            """
            SELECT id, name, description, is_public, created_at, updated_at, owner_id
            FROM playlists WHERE id = %s
            """,
            (playlist_id,),
        )
        updated = cursor.fetchone()
        return jsonify(_playlist_to_dict(updated, include_counts=True))
    except Exception as error:  # noqa: BLE001
        print(f"Update playlist error: {error}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'detail': 'Failed to update playlist'}), 500


@router.route('/<playlist_id>', methods=['DELETE'])
@jwt_required()
def delete_playlist(playlist_id):
    """Soft-delete a playlist."""
    try:
        user_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT owner_id FROM playlists WHERE id = %s AND is_deleted = FALSE",
            (playlist_id,),
        )
        playlist = cursor.fetchone()
        if not playlist:
            return jsonify({'detail': 'Playlist not found'}), 404
        if playlist['owner_id'] != int(user_id):
            return jsonify({'detail': 'Not authorized to delete this playlist'}), 403

        cursor.execute(
            "UPDATE playlists SET is_deleted = TRUE, updated_at = NOW() WHERE id = %s",
            (playlist_id,),
        )
        conn.commit()
        return jsonify({'message': 'Playlist deleted'})
    except Exception as error:  # noqa: BLE001
        print(f"Delete playlist error: {error}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'detail': 'Failed to delete playlist'}), 500


@router.route('/<playlist_id>/items', methods=['GET'])
@jwt_required()
def list_playlist_items(playlist_id):
    """Return playlist items (wrapper for backwards compatibility)."""
    return get_playlist(playlist_id)


@router.route('/<playlist_id>/items', methods=['POST'])
@jwt_required()
def add_playlist_item(playlist_id):
    """Add media to playlist."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        media_id = data.get('mediaItemId') or data.get('media_id')
        if not media_id:
            return jsonify({'detail': 'media_id is required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT owner_id FROM playlists WHERE id = %s AND is_deleted = FALSE",
            (playlist_id,),
        )
        playlist = cursor.fetchone()
        if not playlist:
            return jsonify({'detail': 'Playlist not found'}), 404
        if playlist['owner_id'] != int(user_id):
            return jsonify({'detail': 'Not authorized to modify this playlist'}), 403

        cursor.execute(
            "SELECT id FROM media_files WHERE id = %s AND is_deleted = FALSE",
            (media_id,),
        )
        if not cursor.fetchone():
            return jsonify({'detail': 'Media not found'}), 404

        cursor.execute(
            "SELECT id FROM playlist_items WHERE playlist_id = %s AND media_id = %s",
            (playlist_id, media_id),
        )
        if cursor.fetchone():
            return jsonify({'detail': 'Media already in playlist'}), 409

        cursor.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM playlist_items WHERE playlist_id = %s",
            (playlist_id,),
        )
        position = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO playlist_items (playlist_id, media_id, position)
            VALUES (%s, %s, %s)
            RETURNING id, added_at
            """,
            (playlist_id, media_id, position),
        )

        item = cursor.fetchone()
        conn.commit()
        return jsonify(
            {
                'item': {
                    'id': item['id'],
                    'playlist_id': playlist_id,
                    'mediaItemId': media_id,
                    'position': position,
                    'addedAt': item['added_at'].isoformat() if item['added_at'] else None,
                }
            }
        ), 201
    except Exception as error:  # noqa: BLE001
        print(f"Add playlist item error: {error}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'detail': 'Failed to add item to playlist'}), 500


@router.route('/<playlist_id>/items/<media_id>', methods=['DELETE'])
@jwt_required()
def remove_playlist_item(playlist_id, media_id):
    """Remove media from playlist."""
    try:
        user_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT owner_id FROM playlists WHERE id = %s AND is_deleted = FALSE",
            (playlist_id,),
        )
        playlist = cursor.fetchone()
        if not playlist:
            return jsonify({'detail': 'Playlist not found'}), 404
        if playlist['owner_id'] != int(user_id):
            return jsonify({'detail': 'Not authorized to modify this playlist'}), 403

        cursor.execute(
            "DELETE FROM playlist_items WHERE playlist_id = %s AND media_id = %s RETURNING id",
            (playlist_id, media_id),
        )
        deleted = cursor.fetchone()
        conn.commit()

        if not deleted:
            return jsonify({'detail': 'Item not found in playlist'}), 404
        return jsonify({'message': 'Item removed from playlist'})
    except Exception as error:  # noqa: BLE001
        print(f"Remove playlist item error: {error}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'detail': 'Failed to remove item from playlist'}), 500
