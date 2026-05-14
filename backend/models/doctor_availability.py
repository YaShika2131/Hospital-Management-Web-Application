from datetime import datetime, date, time
from .db import db

class DoctorAvailability(db.Model):
    """Doctor availability slots for next 7 days"""
    __tablename__ = 'doctor_availability'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False, index=True)
    available_date = db.Column(db.Date, nullable=False, index=True)
    morning_start = db.Column(db.Time)  # e.g., 08:00
    morning_end = db.Column(db.Time)    # e.g., 12:00
    evening_start = db.Column(db.Time)  # e.g., 16:00
    evening_end = db.Column(db.Time)    # e.g., 21:00
    is_available_morning = db.Column(db.Boolean, default=True)
    is_available_evening = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique constraint - one availability record per doctor per date
    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'available_date', name='unique_doctor_date'),
    )
    
    def to_dict(self):
        """Convert availability to dictionary"""
        return {
            'id': self.id,
            'doctor_id': self.doctor_id,
            'available_date': self.available_date.isoformat() if self.available_date else None,
            'morning_start': self.morning_start.strftime('%H:%M:%S') if self.morning_start else None,
            'morning_end': self.morning_end.strftime('%H:%M:%S') if self.morning_end else None,
            'evening_start': self.evening_start.strftime('%H:%M:%S') if self.evening_start else None,
            'evening_end': self.evening_end.strftime('%H:%M:%S') if self.evening_end else None,
            'is_available_morning': self.is_available_morning,
            'is_available_evening': self.is_available_evening,
        }
    
    def __repr__(self):
        return f'<DoctorAvailability {self.doctor_id} on {self.available_date}>'

