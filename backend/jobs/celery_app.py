"""Celery application configuration"""
from celery import Celery
from celery.schedules import crontab
from backend.config.config import Config

celery_app = Celery(
    'hospital_management',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=['backend.jobs.daily_reminders', 'backend.jobs.monthly_reports', 'backend.jobs.csv_export']
)

celery_app.conf.update(
    timezone='Asia/Kolkata',
    enable_utc=False,
    beat_schedule={
        'daily-reminder': {
            'task': 'backend.jobs.daily_reminders.send_daily_reminders',
            'schedule': crontab(hour=8, minute=0),  # Run at 08:00 AM IST every day
        },
        'monthly-report': {
            'task': 'backend.jobs.monthly_reports.send_monthly_reports',
            'schedule': 86400.0,  # Run daily, check if first day of month
        },
    },
)

