"""CSV export job - Export patient treatment history as CSV"""
import csv
import io
from datetime import datetime
from backend.jobs.celery_app import celery_app
from backend.models.db import db
from backend.models.patient import Patient
from backend.models.appointment import Appointment
from backend.models.treatment import Treatment
from backend.config.config import Config
import requests

@celery_app.task(name='backend.jobs.csv_export.export_patient_treatment_history')
def export_patient_treatment_history(patient_id):
    """Export patient treatment history as CSV"""
    from backend.app import create_app
    
    app = create_app()
    with app.app_context():
        try:
            patient = Patient.query.get_or_404(patient_id)
            
            # Get all appointments with treatments
            appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(
                Appointment.appointment_date.desc()
            ).all()
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
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
            
            # Write data rows
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
            
            # Store CSV in Redis or file system (for now, return success)
            # In production, you might want to save to file and send link via email/notification
            
            return {
                'status': 'success',
                'patient_id': patient_id,
                'patient_name': patient.full_name,
                'csv_content': csv_content,
                'records_count': len(appointments),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'patient_id': patient_id
            }

