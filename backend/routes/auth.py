"""Authentication routes"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from backend.models.db import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.department import Department

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/departments', methods=['GET'])
def list_departments_public():
    """Public endpoint - list departments for registration form"""
    departments = Department.query.all()
    return jsonify({'departments': [d.to_dict() for d in departments]}), 200

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login endpoint for all user types"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if user.is_blacklisted or not user.is_active:
        return jsonify({'error': 'Account is disabled'}), 403
    
    # Create JWT token
    access_token = create_access_token(identity=str(user.id))
    
    response_data = {
        'message': 'Login successful',
        'access_token': access_token,
        'user': user.to_dict()
    }
    
    # Add role-specific profile data
    if user.role == 'patient' and user.patient_profile:
        response_data['profile'] = user.patient_profile.to_dict()
    elif user.role == 'doctor' and user.doctor_profile:
        response_data['profile'] = user.doctor_profile.to_dict()
    
    return jsonify(response_data), 200

def _parse_date(date_str):
    """Parse date string to Python date object"""
    if not date_str:
        return None
    if hasattr(date_str, 'isoformat'):
        return date_str
    try:
        return datetime.strptime(str(date_str)[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register endpoint for patients and doctors (Admin is pre-existing, login only)"""
    data = request.get_json()
    role = data.get('role', 'patient')
    
    if role not in ('patient', 'doctor'):
        return jsonify({'error': 'Invalid role. Must be patient or doctor.'}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    
    if not all([username, email, password, first_name, last_name]):
        return jsonify({'error': 'Username, email, password, first name and last name are required'}), 400
    
    if role == 'doctor':
        if not all([data.get('department_id'), data.get('specialization')]):
            return jsonify({'error': 'Department and specialization are required for doctor registration'}), 400
        try:
            experience_years = int(data.get('experience_years', 0))
        except (TypeError, ValueError):
            experience_years = 0
        if experience_years < 0:
            return jsonify({'error': 'Experience years must be 0 or more'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    user = User(username=username, email=email, role=role, is_active=True, is_blacklisted=False)
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.flush()
        
        if role == 'patient':
            patient = Patient(
                first_name=first_name, last_name=last_name, phone=data.get('phone'),
                date_of_birth=_parse_date(data.get('date_of_birth')), gender=data.get('gender'),
                address=data.get('address'), emergency_contact=data.get('emergency_contact'),
                emergency_phone=data.get('emergency_phone'), blood_group=data.get('blood_group'),
            )
            patient.user_id = user.id
            db.session.add(patient)
            db.session.commit()
            return jsonify({
                'message': 'Registration successful',
                'access_token': create_access_token(identity=str(user.id)),
                'user': user.to_dict(), 'profile': patient.to_dict()
            }), 201
        else:
            department_id = int(data['department_id'])
            if not Department.query.get(department_id):
                db.session.rollback()
                return jsonify({'error': 'Invalid department'}), 400
            doctor = Doctor(
                first_name=first_name, last_name=last_name, specialization=data['specialization'],
                department_id=department_id, experience_years=int(data.get('experience_years', 0)),
                qualifications=data.get('qualifications'), phone=data.get('phone'), bio=data.get('bio'),
            )
            doctor.user_id = user.id
            db.session.add(doctor)
            db.session.commit()
            return jsonify({
                'message': 'Registration successful',
                'access_token': create_access_token(identity=str(user.id)),
                'user': user.to_dict(), 'profile': doctor.to_dict()
            }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user"""
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid token identity'}), 401
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    response_data = {'user': user.to_dict()}
    
    # Add role-specific profile data
    if user.role == 'patient' and user.patient_profile:
        response_data['profile'] = user.patient_profile.to_dict()
    elif user.role == 'doctor' and user.doctor_profile:
        response_data['profile'] = user.doctor_profile.to_dict()
    
    return jsonify(response_data), 200

