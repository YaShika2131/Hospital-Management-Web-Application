"""Doctor routes"""
from flask import Blueprint, request, jsonify
from datetime import datetime, date, time, timedelta
from backend.models.db import db
from backend.models.doctor import Doctor
from backend.models.appointment import Appointment
from backend.models.treatment import Treatment
from backend.models.patient import Patient
from backend.models.doctor_availability import DoctorAvailability
from backend.utils.decorators import doctor_required

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/dashboard', methods=['GET'])
@doctor_required
def dashboard(current_user):
    """Doctor dashboard with upcoming appointments"""
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        return jsonify({'error': 'Doctor profile not found'}), 404
    
    try:
        today = date.today()
        end_date = today + timedelta(days=7)
        
        # Upcoming appointments for next 7 days
        upcoming_appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date >= today,
            Appointment.appointment_date <= end_date,
            Appointment.status == 'Booked'
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
        
        # Get unique patients assigned to this doctor
        patient_ids = db.session.query(Appointment.patient_id).filter(
            Appointment.doctor_id == doctor.id
        ).distinct().all()
        patient_ids = [pid[0] for pid in patient_ids]
        assigned_patients = Patient.query.filter(Patient.id.in_(patient_ids)).all()
        
        return jsonify({
            'doctor': doctor.to_dict(),
            'upcoming_appointments': [apt.to_dict() for apt in upcoming_appointments],
            'assigned_patients': [patient.to_dict() for patient in assigned_patients]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@doctor_bp.route('/appointments', methods=['GET'])
@doctor_required
def list_appointments(current_user):
    """List all appointments for the doctor"""
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        return jsonify({'error': 'Doctor profile not found'}), 404
    
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Appointment.query.filter(Appointment.doctor_id == doctor.id)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    if date_from:
        query = query.filter(Appointment.appointment_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Appointment.appointment_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    appointments = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    
    return jsonify({'appointments': [apt.to_dict() for apt in appointments]}), 200

@doctor_bp.route('/appointments/<int:appointment_id>/complete', methods=['PUT'])
@doctor_required
def mark_appointment_complete(current_user, appointment_id):
    """Mark appointment as completed"""
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        return jsonify({'error': 'Doctor profile not found'}), 404
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != doctor.id:
        return jsonify({'error': 'Unauthorized access to this appointment'}), 403
    
    try:
        appointment.status = 'Completed'
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment marked as completed',
            'appointment': appointment.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@doctor_bp.route('/appointments/<int:appointment_id>/cancel', methods=['PUT'])
@doctor_required
def cancel_appointment(current_user, appointment_id):
    """Cancel an appointment"""
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        return jsonify({'error': 'Doctor profile not found'}), 404
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != doctor.id:
        return jsonify({'error': 'Unauthorized access to this appointment'}), 403
    
    try:
        appointment.status = 'Cancelled'
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment cancelled',
            'appointment': appointment.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@doctor_bp.route('/appointments/<int:appointment_id>/treatment', methods=['POST', 'PUT'])
@doctor_required
def update_treatment(current_user, appointment_id):
    """Create or update treatment history for an appointment"""
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        return jsonify({'error': 'Doctor profile not found'}), 404
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != doctor.id:
        return jsonify({'error': 'Unauthorized access to this appointment'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    if 'diagnosis' not in data:
        return jsonify({'error': 'Diagnosis is required'}), 400
    
    try:
        # Check if treatment already exists
        treatment = Treatment.query.filter_by(appointment_id=appointment_id).first()
        
        if treatment and request.method == 'POST':
            return jsonify({'error': 'Treatment already exists. Use PUT to update.'}), 409
        
        if not treatment:
            treatment = Treatment(appointment_id=appointment_id)
        
        # Update treatment fields
        treatment.diagnosis = data.get('diagnosis', treatment.diagnosis)
        treatment.prescription = data.get('prescription', treatment.prescription)
        treatment.tests_done = data.get('tests_done', treatment.tests_done)
        treatment.medicines = data.get('medicines', treatment.medicines)
        treatment.notes = data.get('notes', treatment.notes)
        
        if 'next_visit_suggested' in data:
            treatment.next_visit_suggested = datetime.strptime(data['next_visit_suggested'], '%Y-%m-%d').date()
        
        if not treatment.id:
            db.session.add(treatment)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Treatment updated successfully',
            'treatment': treatment.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update treatment: {str(e)}'}), 500

@doctor_bp.route('/patients/<int:patient_id>/history', methods=['GET'])
@doctor_required
def get_patient_history(current_user, patient_id):
    """Get full treatment history of a patient"""
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        return jsonify({'error': 'Doctor profile not found'}), 404
    
    # Verify patient has appointments with this doctor
    patient_appointments = Appointment.query.filter_by(
        patient_id=patient_id,
        doctor_id=doctor.id
    ).all()
    
    if not patient_appointments:
        return jsonify({'error': 'No appointments found for this patient with you'}), 404
    
    # Get all appointments with treatments
    appointments_with_treatments = []
    for apt in patient_appointments:
        apt_dict = apt.to_dict()
        if apt.treatment:
            apt_dict['treatment'] = apt.treatment.to_dict()
        appointments_with_treatments.append(apt_dict)
    
    patient = Patient.query.get(patient_id)
    
    return jsonify({
        'patient': patient.to_dict() if patient else None,
        'appointments': appointments_with_treatments
    }), 200

@doctor_bp.route('/availability', methods=['GET'])
@doctor_required
def get_availability(current_user):
    """Get doctor availability for next 7 days"""
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        return jsonify({'error': 'Doctor profile not found'}), 404
    
    today = date.today()
    end_date = today + timedelta(days=7)
    
    availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.available_date >= today,
        DoctorAvailability.available_date <= end_date
    ).order_by(DoctorAvailability.available_date).all()
    
    return jsonify({
        'availability': [av.to_dict() for av in availability]
    }), 200

@doctor_bp.route('/availability', methods=['POST'])
@doctor_required
def set_availability(current_user):
    """Set doctor availability for next 7 days"""
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        return jsonify({'error': 'Doctor profile not found'}), 404
    
    data = request.get_json()
    availability_data = data.get('availability', [])
    
    if not availability_data:
        return jsonify({'error': 'Availability data is required'}), 400
    
    try:
        today = date.today()
        
        for av_data in availability_data:
            available_date = datetime.strptime(av_data['date'], '%Y-%m-%d').date()
            
            # Only allow setting availability for next 7 days
            if available_date < today or available_date > today + timedelta(days=7):
                continue
            
            # Get or create availability record
            availability = DoctorAvailability.query.filter_by(
                doctor_id=doctor.id,
                available_date=available_date
            ).first()
            
            if not availability:
                availability = DoctorAvailability(
                    doctor_id=doctor.id,
                    available_date=available_date
                )
            
            # Update time slots
            if 'morning_start' in av_data and 'morning_end' in av_data:
                availability.morning_start = time.fromisoformat(av_data['morning_start'])
                availability.morning_end = time.fromisoformat(av_data['morning_end'])
                availability.is_available_morning = av_data.get('is_available_morning', True)
            
            if 'evening_start' in av_data and 'evening_end' in av_data:
                availability.evening_start = time.fromisoformat(av_data['evening_start'])
                availability.evening_end = time.fromisoformat(av_data['evening_end'])
                availability.is_available_evening = av_data.get('is_available_evening', True)
            
            if not availability.id:
                db.session.add(availability)
        
        db.session.commit()
        
        return jsonify({'message': 'Availability updated successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update availability: {str(e)}'}), 500

