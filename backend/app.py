"""Main Flask application"""
import os
import sys
from datetime import date, datetime, time, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.config.config import Config
from backend.models.db import db
from backend.models.department import Department
from backend.models.user import User
from backend.models.doctor import Doctor
from backend.models.patient import Patient
from backend.models.appointment import Appointment
from backend.models.treatment import Treatment
from backend.models.doctor_availability import DoctorAvailability

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app)
    
    # Register blueprints
    from backend.routes.auth import auth_bp
    from backend.routes.admin import admin_bp
    from backend.routes.doctor import doctor_bp
    from backend.routes.patient import patient_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    
    # Frontend route - serve the Vue.js SPA
    @app.route('/')
    def index():
        """Serve the main frontend application"""
        return render_template('index.html')
    
    # Task status endpoint for checking Celery job status
    @app.route('/api/tasks/<task_id>', methods=['GET'])
    def get_task_status(task_id):
        """Get the status of a Celery task"""
        from backend.jobs.celery_app import celery_app
        task = celery_app.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            response = {'state': task.state, 'status': 'Task is waiting...'}
        elif task.state == 'STARTED':
            response = {'state': task.state, 'status': 'Task is in progress...'}
        elif task.state == 'SUCCESS':
            response = {'state': task.state, 'status': 'Task completed!', 'result': task.result}
        elif task.state == 'FAILURE':
            response = {'state': task.state, 'status': 'Task failed', 'error': str(task.info)}
        else:
            response = {'state': task.state, 'status': str(task.info)}
        
        return jsonify(response)
    
    # Create tables and initialize admin user
    with app.app_context():
        db.create_all()
        create_default_departments()
        create_admin_user()
        create_default_doctor_availability()
    
    return app

def create_default_doctor_availability():
    """
    Seed default availability slots for all doctors that don't have availability
    for the next 7 days. This allows patients to see selectable dates immediately.
    """
    today = date.today()
    end_date = today + timedelta(days=7)

    # Import here to avoid circular imports in some environments
    from backend.models.doctor import Doctor

    default_data = {
        'morning_start': time.fromisoformat('09:00'),
        'morning_end': time.fromisoformat('12:00'),
        'evening_start': time.fromisoformat('14:00'),
        'evening_end': time.fromisoformat('18:00'),
        'is_available_morning': True,
        'is_available_evening': True,
    }

    doctors = Doctor.query.all()
    for doctor in doctors:
        for i in range((end_date - today).days + 1):
            available_date = today + timedelta(days=i)
            exists = DoctorAvailability.query.filter_by(
                doctor_id=doctor.id,
                available_date=available_date
            ).first()
            if exists:
                continue

            slot = DoctorAvailability(
                doctor_id=doctor.id,
                available_date=available_date,
                morning_start=default_data['morning_start'],
                morning_end=default_data['morning_end'],
                evening_start=default_data['evening_start'],
                evening_end=default_data['evening_end'],
                is_available_morning=default_data['is_available_morning'],
                is_available_evening=default_data['is_available_evening'],
            )
            db.session.add(slot)

    db.session.commit()

def create_default_departments():
    """Create default departments if they don't exist"""
    departments = [
        {'name': 'Cardiology', 'description': 'Heart and cardiovascular diseases'},
        {'name': 'Oncology', 'description': 'Cancer treatment and care'},
        {'name': 'General', 'description': 'General medicine and primary care'},
        {'name': 'Orthopedics', 'description': 'Bone and joint care'},
        {'name': 'Pediatrics', 'description': 'Children healthcare'},
        {'name': 'Neurology', 'description': 'Brain and nervous system'},
    ]
    
    for dept_data in departments:
        existing = Department.query.filter_by(name=dept_data['name']).first()
        if not existing:
            dept = Department(**dept_data)
            db.session.add(dept)
    
    db.session.commit()

def create_admin_user():
    """Create default admin user if it doesn't exist"""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@hospital.com',
            role='admin',
            is_active=True,
            is_blacklisted=False
        )
        admin.set_password('admin123')  # Default password - should be changed in production
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: username='admin', password='admin123'")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)

