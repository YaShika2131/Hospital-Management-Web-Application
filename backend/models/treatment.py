from datetime import datetime
from .db import db

class Treatment(db.Model):
    """Treatment model - stores diagnosis, prescription, and treatment details"""
    __tablename__ = 'treatments'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), unique=True, nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text)
    tests_done = db.Column(db.Text)  # Store as comma-separated or JSON
    medicines = db.Column(db.Text)  # Store as JSON or formatted string
    notes = db.Column(db.Text)
    next_visit_suggested = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert treatment to dictionary"""
        return {
            'id': self.id,
            'appointment_id': self.appointment_id,
            'diagnosis': self.diagnosis,
            'prescription': self.prescription,
            'tests_done': self.tests_done,
            'medicines': self.medicines,
            'notes': self.notes,
            'next_visit_suggested': self.next_visit_suggested.isoformat() if self.next_visit_suggested else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<Treatment {self.id} for Appointment {self.appointment_id}>'

