#!/usr/bin/env python3
"""
Create a simple authentication endpoint for Watch1
Based on the working system from memories
"""

auth_endpoint_code = '''
"""
Simple Flask authentication endpoint
Based on working Watch1 v3.0.3 system
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
import bcrypt
import logging
from postgres_config import get_db_connection

logger = logging.getLogger(__name__)

router = Blueprint('auth', __name__)

@router.route('/api/v1/auth/login/access-token', methods=['POST'])
def login():
    """Login endpoint that works with both JSON and form data"""
    try:
        # Get credentials from JSON or form data
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        if not username or not password:
            return jsonify({"detail": "Username and password required"}), 400
        
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({"detail": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        
        # Find user by email
        cursor.execute("SELECT id, email, full_name, hashed_password FROM users WHERE email = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"detail": "Invalid credentials"}), 401
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            # Create JWT token
            access_token = create_access_token(
                identity=str(user[0]),
                expires_delta=timedelta(hours=24)
            )
            
            return jsonify({
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user[0],
                    "email": user[1],
                    "full_name": user[2]
                }
            })
        else:
            return jsonify({"detail": "Invalid credentials"}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"detail": "Login failed"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@router.route('/api/v1/users/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user profile"""
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, email, full_name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user:
            return jsonify({
                "id": user[0],
                "email": user[1],
                "full_name": user[2]
            })
        else:
            return jsonify({"detail": "User not found"}), 404
            
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({"detail": "Failed to get user"}), 500
    finally:
        if 'conn' in locals():
            conn.close()
'''

# Write the auth endpoint
with open('/tmp/simple_auth.py', 'w') as f:
    f.write(auth_endpoint_code)

print("✅ Simple authentication endpoint created")
print("Copy this to your Unraid server:")
print("scp /tmp/simple_auth.py root@192.168.254.14:/mnt/user/appdata/watch1/backend/app/api/v1/endpoints/auth.py")
