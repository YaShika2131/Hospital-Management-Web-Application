"""Daily reminder job - Send reminders to patients about upcoming appointments"""
from datetime import date, datetime
import smtplib
from email.mime.text import MIMEText
import requests
import os
from backend.jobs.celery_app import celery_app
from backend.models.db import db
from backend.models.appointment import Appointment
from backend.models.patient import Patient
from backend.config.config import Config

@celery_app.task(name='backend.jobs.daily_reminders.send_daily_reminders')
def send_daily_reminders():
    """Send daily reminders to patients with appointments today"""
    from backend.app import create_app
    
    app = create_app()
    with app.app_context():
        today = date.today()
        
        # Get all appointments scheduled for today
        appointments = Appointment.query.filter(
            Appointment.appointment_date == today,
            Appointment.status == 'Booked'
        ).all()
        
        reminders_sent = 0
        skipped_missing_email = 0
        failed_sends = 0
        failure_reasons = []
        
        for appointment in appointments:
            try:
                patient = Patient.query.get(appointment.patient_id)
                if not patient:
                    continue
                
                # Prepare reminder message
                time_str = appointment.appointment_time.strftime('%I:%M %p') if appointment.appointment_time else 'TBD'
                doctor_name = appointment.doctor.full_name if appointment.doctor else 'Doctor'
                
                message = (
                    f"Reminder: You have an appointment with {doctor_name} "
                    f"today at {time_str}. Please arrive on time."
                )

                # Primary delivery: email reminder.
                if patient.user and patient.user.email:
                    sent = send_email_notification(
                        patient.user.email,
                        "Appointment Reminder - Hospital Management System",
                        message
                    )
                    if sent:
                        reminders_sent += 1
                else:
                    print(f"Skipping appointment {appointment.id}: patient email not available")
                    skipped_missing_email += 1
                
            except Exception as e:
                print(f"Error sending reminder for appointment {appointment.id}: {str(e)}")
                failed_sends += 1
                failure_reasons.append(f"appointment {appointment.id}: {str(e)}")
                continue
        
        mail_configured = bool(Config.MAIL_SERVER and Config.MAIL_USERNAME and Config.MAIL_PASSWORD)

        return {
            'status': 'success',
            'appointments_found': len(appointments),
            'reminders_sent': reminders_sent,
            'skipped_missing_email': skipped_missing_email,
            'failed_sends': failed_sends,
            'mail_configured': mail_configured,
            'failure_reasons': failure_reasons[:5],
            'date': today.isoformat()
        }

def send_google_chat_notification(email, message):
    """Send notification via Google Chat Webhook"""
    if not Config.GOOGLE_CHAT_WEBHOOK_URL:
        return
    
    try:
        payload = {
            'text': f"Patient Reminder - {email}\n{message}"
        }
        response = requests.post(Config.GOOGLE_CHAT_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Google Chat notification: {str(e)}")

def send_email_notification(email, subject, message):
    """Send notification via SMTP email. Returns True when sent."""
    if not Config.MAIL_SERVER or not Config.MAIL_USERNAME:
        print(f"Email not configured. Would send reminder to {email}")
        return False

    try:
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = Config.MAIL_USERNAME
        msg['To'] = email

        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        if Config.MAIL_USE_TLS:
            server.starttls()
        if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"Reminder email sent to {email}")
        return True
    except Exception as e:
        print(f"Failed to send reminder email to {email}: {str(e)}")
        return False

