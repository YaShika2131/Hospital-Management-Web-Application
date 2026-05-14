"""Patient routes"""
from flask import Blueprint, request, jsonify, make_response
from datetime import datetime, date, time, timedelta
from sqlalchemy import and_
from backend.models.db import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.department import Department
from backend.models.appointment import Appointment
from backend.models.treatment import Treatment
from backend.models.doctor_availability import DoctorAvailability
from backend.utils.decorators import patient_required

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/dashboard', methods=['GET'])
@patient_required
def dashboard(current_user):
    """Patient dashboard"""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    try:
        today = date.today()
        
        # Upcoming appointments
        upcoming_appointments = Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.appointment_date >= today,
            Appointment.status == 'Booked'
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
        
        # Get all departments
        departments = Department.query.all()
        
        return jsonify({
            'patient': patient.to_dict(),
            'upcoming_appointments': [apt.to_dict() for apt in upcoming_appointments],
            'departments': [dept.to_dict() for dept in departments]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@patient_bp.route('/profile', methods=['PUT'])
@patient_required
def update_profile(current_user):
    """Update patient profile"""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient profile not found'}), 404
    
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
        
        # Update user email if provided
        if 'email' in data and patient.user:
            if User.query.filter_by(email=data['email']).filter(User.id != patient.user_id).first():
                return jsonify({'error': 'Email already exists'}), 409
            patient.user.email = data['email']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'patient': patient.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

@patient_bp.route('/departments', methods=['GET'])
@patient_required
def list_departments(current_user):
    """List all departments"""
    departments = Department.query.all()
    return jsonify({'departments': [dept.to_dict() for dept in departments]}), 200

@patient_bp.route('/departments/<int:department_id>/doctors', methods=['GET'])
@patient_required
def list_doctors_by_department(current_user, department_id):
    """List doctors in a specific department"""
    department = Department.query.get_or_404(department_id)
    doctors = Doctor.query.filter_by(department_id=department_id).all()
    
    return jsonify({
        'department': department.to_dict(),
        'doctors': [doctor.to_dict() for doctor in doctors]
    }), 200

@patient_bp.route('/doctors', methods=['GET'])
@patient_required
def search_doctors(current_user):
    """Search doctors by name or specialization"""
    search = request.args.get('search', '')
    specialization = request.args.get('specialization', '')
    
    query = Doctor.query
    
    if search:
        query = query.filter(
            db.or_(
                Doctor.first_name.ilike(f'%{search}%'),
                Doctor.last_name.ilike(f'%{search}%'),
                Doctor.specialization.ilike(f'%{search}%')
            )
        )
    
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f'%{specialization}%'))
    
    doctors = query.all()
    return jsonify({'doctors': [doctor.to_dict() for doctor in doctors]}), 200

@patient_bp.route('/doctors/<int:doctor_id>', methods=['GET'])
@patient_required
def get_doctor_details(current_user, doctor_id):
    """Get doctor details and availability"""
    doctor = Doctor.query.get_or_404(doctor_id)
    
    # Get availability for next 7 days
    today = date.today()
    end_date = today + timedelta(days=7)
    
    availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.available_date >= today,
        DoctorAvailability.available_date <= end_date
    ).order_by(DoctorAvailability.available_date).all()
    
    return jsonify({
        'doctor': doctor.to_dict(),
        'availability': [av.to_dict() for av in availability]
    }), 200

@patient_bp.route('/doctors/<int:doctor_id>/availability', methods=['GET'])
@patient_required
def get_doctor_availability(current_user, doctor_id):
    """Get doctor availability for booking"""
    doctor = Doctor.query.get_or_404(doctor_id)
    
    today = date.today()
    end_date = today + timedelta(days=7)
    
    availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.available_date >= today,
        DoctorAvailability.available_date <= end_date
    ).order_by(DoctorAvailability.available_date).all()
    
    # Get existing appointments to show booked slots
    appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date >= today,
        Appointment.status == 'Booked'
    ).all()
    
    booked_slots = {}
    for apt in appointments:
        date_str = apt.appointment_date.isoformat()
        time_str = apt.appointment_time.strftime('%H:%M:%S')
        if date_str not in booked_slots:
            booked_slots[date_str] = []
        booked_slots[date_str].append(time_str)
    
    return jsonify({
        'availability': [av.to_dict() for av in availability],
        'booked_slots': booked_slots
    }), 200

@patient_bp.route('/appointments', methods=['POST'])
@patient_required
def book_appointment(current_user):
    """Book a new appointment"""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    doctor_id = data.get('doctor_id')
    appointment_date = data.get('appointment_date')
    appointment_time = data.get('appointment_time')
    
    if not all([doctor_id, appointment_date, appointment_time]):
        return jsonify({'error': 'Doctor ID, date, and time are required'}), 400
    
    try:
        doctor = Doctor.query.get_or_404(doctor_id)
        apt_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        apt_time = datetime.strptime(appointment_time, '%H:%M:%S').time()
        
        # Check if date is in future
        if apt_date < date.today():
            return jsonify({'error': 'Cannot book appointments in the past'}), 400
        
        # Check if doctor is available on this date and time
        availability = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            available_date=apt_date
        ).first()
        
        if not availability:
            return jsonify({'error': 'Doctor is not available on this date'}), 400
        
        # Check time slot availability (morning or evening)
        is_morning = availability.morning_start <= apt_time <= availability.morning_end
        is_evening = availability.evening_start <= apt_time <= availability.evening_end
        
        if not (is_morning or is_evening):
            return jsonify({'error': 'Selected time is not in available slots'}), 400
        
        if is_morning and not availability.is_available_morning:
            return jsonify({'error': 'Morning slot is not available'}), 400
        
        if is_evening and not availability.is_available_evening:
            return jsonify({'error': 'Evening slot is not available'}), 400
        
        # Check for existing appointment at same time (prevent double booking)
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=apt_date,
            appointment_time=apt_time,
            status='Booked'
        ).first()
        
        if existing:
            return jsonify({'error': 'This time slot is already booked'}), 409
        
        # Create appointment
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            appointment_date=apt_date,
            appointment_time=apt_time,
            status='Booked',
            visit_type=data.get('visit_type', 'In-person'),
            notes=data.get('notes')
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment booked successfully',
            'appointment': appointment.to_dict()
        }), 201
    
    except ValueError as e:
        return jsonify({'error': f'Invalid date or time format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to book appointment: {str(e)}'}), 500

@patient_bp.route('/appointments', methods=['GET'])
@patient_required
def list_appointments(current_user):
    """List all appointments for the patient"""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    status = request.args.get('status')
    include_past = request.args.get('include_past', 'false').lower() == 'true'
    
    query = Appointment.query.filter(Appointment.patient_id == patient.id)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    if not include_past:
        query = query.filter(Appointment.appointment_date >= date.today())
    
    appointments = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    
    # Include treatment details if available
    appointments_with_treatments = []
    for apt in appointments:
        apt_dict = apt.to_dict()
        if apt.treatment:
            apt_dict['treatment'] = apt.treatment.to_dict()
        appointments_with_treatments.append(apt_dict)
    
    return jsonify({'appointments': appointments_with_treatments}), 200

@patient_bp.route('/appointments/<int:appointment_id>/cancel', methods=['PUT'])
@patient_required
def cancel_appointment(current_user, appointment_id):
    """Cancel an appointment"""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.patient_id != patient.id:
        return jsonify({'error': 'Unauthorized access to this appointment'}), 403
    
    if appointment.status != 'Booked':
        return jsonify({'error': f'Cannot cancel appointment with status: {appointment.status}'}), 400
    
    try:
        appointment.status = 'Cancelled'
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment cancelled successfully',
            'appointment': appointment.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@patient_bp.route('/history', methods=['GET'])
@patient_required
def get_treatment_history(current_user):
    """Get complete treatment history"""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc()
    ).all()
    
    history = []
    for apt in appointments:
        apt_dict = apt.to_dict()
        if apt.treatment:
            apt_dict['treatment'] = apt.treatment.to_dict()
        history.append(apt_dict)
    
    return jsonify({
        'patient': patient.to_dict(),
        'history': history
    }), 200

@patient_bp.route('/history/export', methods=['GET'])
@patient_required
def export_treatment_history(current_user):
    """Export patient treatment history as a downloadable CSV file"""
    import csv
    import io

    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient profile not found'}), 404

    try:
        appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
            Appointment.appointment_date.desc()
        ).all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'User ID',
            'Username',
            'Patient Name',
            'Appointment Date',
            'Appointment Time',
            'Consulting Doctor',
            'Doctor Specialization',
            'Department',
            'Visit Type',
            'Status',
            'Diagnosis',
            'Prescription',
            'Tests Done',
            'Medicines',
            'Next Visit Suggested',
            'Notes'
        ])

        for appointment in appointments:
            treatment = appointment.treatment
            doctor_name = appointment.doctor.full_name if appointment.doctor else 'N/A'
            doctor_specialization = appointment.doctor.specialization if appointment.doctor else 'N/A'
            department_name = appointment.doctor.department.name if appointment.doctor and appointment.doctor.department else 'N/A'

            writer.writerow([
                patient.user_id,
                patient.user.username if patient.user else 'N/A',
                patient.full_name,
                appointment.appointment_date.isoformat() if appointment.appointment_date else 'N/A',
                appointment.appointment_time.strftime('%H:%M:%S') if appointment.appointment_time else 'N/A',
                doctor_name,
                doctor_specialization,
                department_name,
                appointment.visit_type or 'N/A',
                appointment.status,
                treatment.diagnosis if treatment and treatment.diagnosis else 'N/A',
                treatment.prescription if treatment and treatment.prescription else 'N/A',
                treatment.tests_done if treatment and treatment.tests_done else 'N/A',
                treatment.medicines if treatment and treatment.medicines else 'N/A',
                treatment.next_visit_suggested.isoformat() if treatment and treatment.next_visit_suggested else 'N/A',
                treatment.notes if treatment and treatment.notes else 'N/A'
            ])

        csv_content = output.getvalue()
        output.close()

        safe_name = ''.join(ch if ch.isalnum() else '_' for ch in patient.full_name).strip('_') or f'patient_{patient.id}'
        filename = f"medical_history_{safe_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    except Exception as e:
        return jsonify({'error': f'Failed to export CSV: {str(e)}'}), 500

