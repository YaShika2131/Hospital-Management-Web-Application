from datetime import datetime, date
from .db import db

class Appointment(db.Model):
    """Appointment model"""
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Booked', nullable=False, index=True)  # Booked, Completed, Cancelled
    visit_type = db.Column(db.String(50), default='In-person')  # In-person, Online
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    treatment = db.relationship('Treatment', backref='appointment', uselist=False, cascade='all, delete-orphan')
    
    # Unique constraint to prevent double booking
    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'appointment_date', 'appointment_time', name='unique_doctor_time_slot'),
    )
    
    def to_dict(self):
        """Convert appointment to dictionary"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'doctor_id': self.doctor_id,
            'doctor_name': self.doctor.full_name if self.doctor else None,
            'doctor_specialization': self.doctor.specialization if self.doctor else None,
            'department_name': self.doctor.department.name if self.doctor and self.doctor.department else None,
            'appointment_date': self.appointment_date.isoformat() if self.appointment_date else None,
            'appointment_time': self.appointment_time.strftime('%H:%M:%S') if self.appointment_time else None,
            'appointment_datetime': f"{self.appointment_date} {self.appointment_time}" if self.appointment_date and self.appointment_time else None,
            'status': self.status,
            'visit_type': self.visit_type,
            'notes': self.notes,
            'has_treatment': self.treatment is not None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<Appointment {self.id} - {self.patient_id} with {self.doctor_id} on {self.appointment_date}>'

