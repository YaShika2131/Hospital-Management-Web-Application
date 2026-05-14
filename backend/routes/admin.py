"""Admin routes"""
from flask import Blueprint, request, jsonify
from datetime import datetime, date, timedelta
from backend.models.db import db
from backend.models.user import User
from backend.models.doctor import Doctor
from backend.models.patient import Patient
from backend.models.department import Department
from backend.models.appointment import Appointment
from backend.utils.decorators import admin_required
from backend.utils.cache import cache_result, invalidate_cache

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard(current_user):
    """Admin dashboard with statistics and chart data"""
    try:
        # Count statistics
        doctors_count = Doctor.query.count()
        patients_count = Patient.query.count()
        
        today = date.today()
        upcoming_appointments = Appointment.query.filter(
            Appointment.appointment_date >= today,
            Appointment.status == 'Booked'
        ).count()
        
        total_appointments = Appointment.query.count()
        
        # Get recent appointments
        recent_appointments = Appointment.query.filter(
            Appointment.appointment_date >= today
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(10).all()
        
        # Chart data: appointment status breakdown (for pie/doughnut chart)
        from sqlalchemy import func
        status_counts = db.session.query(Appointment.status, func.count(Appointment.id)).group_by(Appointment.status).all()
        appointment_status_breakdown = {status: count for status, count in status_counts}
        
        # Chart data: appointments per department (for bar chart)
        dept_counts = db.session.query(
            Department.name,
            func.count(Appointment.id)
        ).join(Doctor, Doctor.department_id == Department.id).join(
            Appointment, Appointment.doctor_id == Doctor.id
        ).group_by(Department.name).all()
        appointments_by_department = [{'department': name, 'count': count} for name, count in dept_counts]
        
        return jsonify({
            'statistics': {
                'doctors_count': doctors_count,
                'patients_count': patients_count,
                'upcoming_appointments': upcoming_appointments,
                'total_appointments': total_appointments
            },
            'recent_appointments': [apt.to_dict() for apt in recent_appointments],
            'chart_data': {
                'appointment_status_breakdown': appointment_status_breakdown,
                'appointments_by_department': appointments_by_department
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/doctors', methods=['GET'])
@admin_required
@cache_result(expiry=300)
def list_doctors(current_user):
    """List all doctors with optional search"""
    search = request.args.get('search', '')
    department_id = request.args.get('department_id', type=int)
    
    query = Doctor.query
    
    if search:
        query = query.filter(
            db.or_(
                Doctor.first_name.ilike(f'%{search}%'),
                Doctor.last_name.ilike(f'%{search}%'),
                Doctor.specialization.ilike(f'%{search}%')
            )
        )
    
    if department_id:
        query = query.filter(Doctor.department_id == department_id)
    
    doctors = query.all()
    return jsonify({'doctors': [doctor.to_dict() for doctor in doctors]}), 200

@admin_bp.route('/doctors', methods=['POST'])
@admin_required
def create_doctor(current_user):
    """Create a new doctor"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'specialization', 'department_id', 'experience_years']
    if not all(data.get(field) for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if username or email already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    # Check if department exists
    department = Department.query.get(data['department_id'])
    if not department:
        return jsonify({'error': 'Department not found'}), 404
    
    try:
        # Create user
        user = User(
            username=data['username'],
            email=data['email'],
            role='doctor',
            is_active=True,
            is_blacklisted=False
        )
        user.set_password(data['password'])
        
        # Create doctor profile
        doctor = Doctor(
            first_name=data['first_name'],
            last_name=data['last_name'],
            specialization=data['specialization'],
            department_id=data['department_id'],
            experience_years=data['experience_years'],
            qualifications=data.get('qualifications'),
            phone=data.get('phone'),
            bio=data.get('bio'),
        )
        
        db.session.add(user)
        db.session.flush()
        
        doctor.user_id = user.id
        db.session.add(doctor)
        db.session.commit()
        
        # Invalidate cache
        invalidate_cache('list_doctors:*')
        
        return jsonify({
            'message': 'Doctor created successfully',
            'doctor': doctor.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create doctor: {str(e)}'}), 500

@admin_bp.route('/doctors/<int:doctor_id>', methods=['GET'])
@admin_required
def get_doctor(current_user, doctor_id):
    """Get doctor details"""
    doctor = Doctor.query.get_or_404(doctor_id)
    return jsonify({'doctor': doctor.to_dict()}), 200

@admin_bp.route('/doctors/<int:doctor_id>', methods=['PUT'])
@admin_required
def update_doctor(current_user, doctor_id):
    """Update doctor details"""
    doctor = Doctor.query.get_or_404(doctor_id)
    data = request.get_json()
    
    try:
        # Update doctor fields
        if 'first_name' in data:
            doctor.first_name = data['first_name']
        if 'last_name' in data:
            doctor.last_name = data['last_name']
        if 'specialization' in data:
            doctor.specialization = data['specialization']
        if 'department_id' in data:
            department = Department.query.get(data['department_id'])
            if department:
                doctor.department_id = data['department_id']
        if 'experience_years' in data:
            doctor.experience_years = data['experience_years']
        if 'qualifications' in data:
            doctor.qualifications = data['qualifications']
        if 'phone' in data:
            doctor.phone = data['phone']
        if 'bio' in data:
            doctor.bio = data['bio']
        
        # Update user email if provided
        if 'email' in data and doctor.user:
            if User.query.filter_by(email=data['email']).filter(User.id != doctor.user_id).first():
                return jsonify({'error': 'Email already exists'}), 409
            doctor.user.email = data['email']
        
        db.session.commit()
        
        # Invalidate cache
        invalidate_cache('list_doctors:*')
        
        return jsonify({
            'message': 'Doctor updated successfully',
            'doctor': doctor.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update doctor: {str(e)}'}), 500

@admin_bp.route('/doctors/<int:doctor_id>', methods=['DELETE'])
@admin_required
def delete_doctor(current_user, doctor_id):
    """Delete/blacklist a doctor"""
    doctor = Doctor.query.get_or_404(doctor_id)
    
    try:
        # Blacklist instead of hard delete (soft delete)
        if doctor.user:
            doctor.user.is_blacklisted = True
            doctor.user.is_active = False
        db.session.commit()
        
        # Invalidate cache
        invalidate_cache('list_doctors:*')
        
        return jsonify({'message': 'Doctor blacklisted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to blacklist doctor: {str(e)}'}), 500

@admin_bp.route('/patients', methods=['GET'])
@admin_required
def list_patients(current_user):
    """List all patients with optional search"""
    search = request.args.get('search', '')
    patient_id = request.args.get('id', type=int)
    
    query = Patient.query
    
    if patient_id:
        query = query.filter(Patient.id == patient_id)
    elif search:
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(f'%{search}%'),
                Patient.last_name.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%')
            )
        )
    
    patients = query.all()
    return jsonify({'patients': [patient.to_dict() for patient in patients]}), 200

@admin_bp.route('/patients/<int:patient_id>', methods=['PUT'])
@admin_required
def update_patient(current_user, patient_id):
    """Update patient details"""
    patient = Patient.query.get_or_404(patient_id)
    data = request.get_json()
    
    try:
        # Update patient fields
        if 'first_name' in data:
            patient.first_name = data['first_name']
        if 'last_name' in data:
            patient.last_name = data['last_name']
        if 'phone' in data:
            patient.phone = data['phone']
        if 'date_of_birth' in data:
            dob = data['date_of_birth']
            patient.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
        if 'gender' in data:
            patient.gender = data['gender']
        if 'address' in data:
            patient.address = data['address']
        if 'emergency_contact' in data:
            patient.emergency_contact = data['emergency_contact']
        if 'emergency_phone' in data:
            patient.emergency_phone = data['emergency_phone']
        if 'blood_group' in data:
            patient.blood_group = data['blood_group']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Patient updated successfully',
            'patient': patient.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update patient: {str(e)}'}), 500

@admin_bp.route('/patients/<int:patient_id>', methods=['DELETE'])
@admin_required
def delete_patient(current_user, patient_id):
    """Blacklist a patient"""
    patient = Patient.query.get_or_404(patient_id)
    
    try:
        if patient.user:
            patient.user.is_blacklisted = True
            patient.user.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Patient blacklisted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to blacklist patient: {str(e)}'}), 500

@admin_bp.route('/appointments', methods=['GET'])
@admin_required
def list_appointments(current_user):
    """List all appointments with optional filters"""
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Appointment.query
    
    if status:
        query = query.filter(Appointment.status == status)
    
    if date_from:
        query = query.filter(Appointment.appointment_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Appointment.appointment_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    appointments = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    
    return jsonify({'appointments': [apt.to_dict() for apt in appointments]}), 200

@admin_bp.route('/departments', methods=['GET'])
@admin_required
@cache_result(expiry=600)
def list_departments(current_user):
    """List all departments"""
    departments = Department.query.all()
    return jsonify({'departments': [dept.to_dict() for dept in departments]}), 200

@admin_bp.route('/reminders/trigger', methods=['POST'])
@admin_required
def trigger_daily_reminders(current_user):
    """Manually trigger daily reminders task for testing"""
    try:
        from backend.jobs.daily_reminders import send_daily_reminders
        task = send_daily_reminders.delay()
        return jsonify({
            'message': 'Daily reminders task queued successfully',
            'task_id': task.id
        }), 202
    except Exception as e:
        return jsonify({'error': f'Failed to trigger reminders: {str(e)}'}), 500

