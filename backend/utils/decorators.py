"""Authentication decorators for role-based access control"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.user import User
from backend.models.db import db

def role_required(*allowed_roles):
    """Decorator to check if user has required role"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            current_user_id = get_jwt_identity()
            try:
                current_user_id = int(current_user_id)
            except (TypeError, ValueError):
                return jsonify({'error': 'Invalid token identity'}), 401
            user = User.query.get(current_user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if user.is_blacklisted or not user.is_active:
                return jsonify({'error': 'User account is disabled'}), 403
            
            if user.role not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            # Add current_user to kwargs for use in route handlers
            kwargs['current_user'] = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator specifically for admin routes"""
    return role_required('admin')(f)

def doctor_required(f):
    """Decorator specifically for doctor routes"""
    return role_required('doctor')(f)

def patient_required(f):
    """Decorator specifically for patient routes"""
    return role_required('patient')(f)

