from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
import bcrypt
import hashlib
# from postgres_config import get_db_connection

from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from postgres_config import get_db_connection

def get_current_user_from_token():
    verify_jwt_in_request(optional=False)
    user_id = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, email, is_active, is_superuser FROM users WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not user:
        raise Exception("User not found")

    return {
        "id": user["id"],
        "email": user["email"],
        "is_active": user["is_active"],
        "is_superuser": user["is_superuser"],
    }

router = Blueprint('auth', __name__)

@router.route('/login/access-token', methods=['POST'])
def login():
    """Login endpoint"""
    try:
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()

        identifier = (data.get('username') or data.get('email') or '').strip().lower()
        password = (data.get('password') or '').strip()

        if not identifier or not password:
            return jsonify({"detail": "Username and password are required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, email, password_hash, is_active, is_superuser, full_name
                FROM users
                WHERE email = %s
                """,
                (identifier,)
            )
            user = cursor.fetchone()

            if not user:
                return jsonify({"detail": "Incorrect username or password"}), 401

            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user['password_hash'] != password_hash:
                return jsonify({"detail": "Incorrect username or password"}), 401

            if not user['is_active']:
                return jsonify({"detail": "Account is inactive"}), 401

            access_token = create_access_token(
                identity=str(user['id']),
                expires_delta=timedelta(days=8)
            )

            return jsonify({
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "full_name": user.get('full_name'),
                    "is_superuser": user['is_superuser']
                }
            })
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"detail": f"Login error: {str(e)}"}), 500

@router.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        payload = request.get_json() or {}

        email = (payload.get('email') or '').strip().lower()
        password = (payload.get('password') or '').strip()
        display_name = (payload.get('displayName') or payload.get('fullName') or '').strip() or None

        if not email or not password:
            return jsonify({"detail": "Email and password are required"}), 400

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"detail": "Email already registered"}), 409

            cursor.execute(
                """
                INSERT INTO users (email, password_hash, full_name, is_active, is_superuser)
                VALUES (%s, %s, %s, TRUE, FALSE)
                RETURNING id, email, full_name, is_superuser
                """,
                (email, password_hash, display_name)
            )
            new_user = cursor.fetchone()
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        access_token = create_access_token(identity=str(new_user['id']), expires_delta=timedelta(days=8))

        return jsonify({
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": new_user['id'],
                "email": new_user['email'],
                "full_name": new_user.get('full_name'),
                "is_superuser": new_user['is_superuser'],
            },
        }), 201

    except Exception as error:  # noqa: BLE001
        print(f"Register error: {error}")
        return jsonify({"detail": f"Register error: {str(error)}"}), 500

@router.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    '''Get current user info'''
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, email, full_name, is_active, is_superuser, created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"detail": "User not found"}), 404
        
        return jsonify({
            "id": user['id'],
            "email": user['email'],
            "full_name": user.get('full_name'),
            "is_active": user['is_active'],
            "is_superuser": user['is_superuser'],
            "created_at": user['created_at'].isoformat() if user['created_at'] else None,
            "updated_at": user['updated_at'].isoformat() if user.get('updated_at') else None
        })

    except Exception as e:
        print(f"Get current user error: {e}")
        return jsonify({"detail": f"User error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
