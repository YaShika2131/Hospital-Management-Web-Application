from datetime import datetime
from .db import db

class Doctor(db.Model):
    """Doctor model"""
    __tablename__ = 'doctors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    experience_years = db.Column(db.Integer, nullable=False)
    qualifications = db.Column(db.Text)
    phone = db.Column(db.String(20))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    department = db.relationship('Department', backref='doctors')
    appointments = db.relationship('Appointment', backref='doctor', lazy='dynamic', cascade='all, delete-orphan')
    availability_slots = db.relationship('DoctorAvailability', backref='doctor', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        """Get doctor's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        """Convert doctor to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'specialization': self.specialization,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'experience_years': self.experience_years,
            'qualifications': self.qualifications,
            'phone': self.phone,
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<Doctor {self.full_name} ({self.specialization})>'

