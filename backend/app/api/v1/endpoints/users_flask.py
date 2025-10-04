"""
Flask-compatible user management endpoints.
"""

from contextlib import closing
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from postgres_config import get_db_connection

router = Blueprint("users", __name__)


def _row_to_user(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "username": row.get("username"),
        "email": row.get("email"),
        "full_name": row.get("full_name"),
        "is_active": row.get("is_active"),
        "is_superuser": row.get("is_superuser"),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


@router.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Return the authenticated user's profile."""
    user_id = get_jwt_identity()

    with closing(get_db_connection()) as conn, closing(conn.cursor()) as cursor:
        cursor.execute(
            """
            SELECT id, username, email, full_name, is_active, is_superuser, created_at, updated_at
            FROM users
            WHERE id = %s AND is_deleted = FALSE
            """,
            (user_id,),
        )
        user = _row_to_user(cursor.fetchone())

    if not user:
        return jsonify({"detail": "User not found"}), 404

    return jsonify(user)


@router.route("/me", methods=["PUT"])
@jwt_required()
def update_current_user():
    """Update fields on the authenticated user's profile."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    allowed_fields = {
        "username": lambda value: (value or "").strip() or None,
        "email": lambda value: (value or "").strip() or None,
        "full_name": lambda value: (value or "").strip() or None,
        "is_active": bool,
    }

    updates = []
    params = []
    for field, sanitizer in allowed_fields.items():
        if field in data:
            sanitized = sanitizer(data.get(field))
            if field in {"username", "email"} and sanitized is None:
                return jsonify({"detail": f"{field} cannot be empty"}), 400
            updates.append(f"{field} = %s")
            params.append(sanitized)

    if not updates:
        return jsonify({"detail": "No changes provided"}), 400

    updates.append("updated_at = NOW()")

    try:
        with closing(get_db_connection()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE id = %s AND is_deleted = FALSE",
                (user_id,),
            )
            if not cursor.fetchone():
                return jsonify({"detail": "User not found"}), 404

            params.append(user_id)
            cursor.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING id",
                params,
            )
            if not cursor.fetchone():
                conn.rollback()
                return jsonify({"detail": "Failed to update user"}), 500
            conn.commit()

            cursor.execute(
                """
                SELECT id, username, email, full_name, is_active, is_superuser, created_at, updated_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            updated_user = _row_to_user(cursor.fetchone())
    except Exception as error:  # noqa: BLE001
        print(f"Update user error: {error}")
        return jsonify({"detail": "Failed to update user"}), 500

    return jsonify(updated_user)


@router.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id: int):
    """Fetch a user by ID."""
    with closing(get_db_connection()) as conn, closing(conn.cursor()) as cursor:
        cursor.execute(
            """
            SELECT id, username, email, full_name, is_active, is_superuser, created_at, updated_at
            FROM users
            WHERE id = %s AND is_deleted = FALSE
            """,
            (user_id,),
        )
        user = _row_to_user(cursor.fetchone())

    if not user:
        return jsonify({"detail": "User not found"}), 404

    return jsonify(user)
