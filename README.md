# Hospital Management System (HMS)

A comprehensive web application for managing hospitals, patients, doctors, appointments, and treatments. 

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: Vue.js (CDN)
- **Templates**: Jinja2 (entry point only)
- **Styling**: Bootstrap 5
- **Database**: SQLite (created programmatically)
- **Caching**: Redis
- **Background Jobs**: Celery + Redis

## Project Structure

```
hospital-management-system/
├── backend/
│   ├── config/          # Configuration files
│   │   └── config.py
│   ├── jobs/            # Celery background tasks
│   │   ├── celery_app.py
│   │   ├── csv_export.py
│   │   ├── daily_reminders.py
│   │   └── monthly_reports.py
│   ├── models/          # Database models
│   │   ├── appointment.py
│   │   ├── department.py
│   │   ├── doctor.py
│   │   ├── doctor_availability.py
│   │   ├── patient.py
│   │   ├── treatment.py
│   │   └── user.py
│   ├── routes/          # API routes
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── doctor.py
│   │   └── patient.py
│   ├── static/          # Static files
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js   # Vue.js application
│   ├── templates/       # Jinja2 templates
│   │   └── index.html   # Entry point
│   ├── utils/           # Utility functions
│   │   ├── cache.py
│   │   └── decorators.py
│   └── app.py           # Flask application
├── requirements.txt
├── run.sh
└── README.md
```

## Roles & Features

### Admin (Hospital Staff)
- Pre-existing superuser (created programmatically)
- Dashboard with statistics (doctors, patients, appointments count)
- Add/update/delete doctor profiles
- View and manage all appointments
- Search for patients or doctors by name/specialization/ID
- Blacklist doctors and patients

### Doctor
- Dashboard with upcoming appointments
- View assigned appointments (day/week)
- Mark appointments as completed or cancelled
- Provide availability for next 7 days
- Update patient treatment history (diagnosis, prescription, medicines)
- View patient treatment history

### Patient
- Register and login
- Dashboard with departments and upcoming appointments
- Search doctors by specialization and availability
- Book, reschedule, or cancel appointments
- View appointment history and treatment details
- Export treatment history as CSV (async job)
- Edit profile information

## Prerequisites

- Python 3.8 or higher
- Redis server
- pip (Python package manager)

## Setup Instructions

### 1. Clone or Navigate to Project Directory

```bash
cd hospital-management-system
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and Start Redis

**On macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**On Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**On Windows:**
Download and install Redis from: https://redis.io/download

### 5. Configure Environment Variables (Optional)

Copy `.env.example` to `.env` and update with your configuration:

```bash
cp .env.example .env
```

Edit `.env` file with your settings (optional for development - defaults are provided).

### 6. Run the Application

**Option 1: Using the run script**
```bash
./run.sh
```

**Option 2: Manual start**
```bash
python backend/app.py
```

The application will be available at **http://localhost:5000**

### 7. Start Celery Worker (for background jobs)

In a separate terminal:

```bash
celery -A backend.jobs.celery_app worker --loglevel=info
```

### 8. Start Celery Beat (for scheduled tasks)

In another separate terminal:

```bash
celery -A backend.jobs.celery_app beat --loglevel=info
```

## Default Login Credentials

- **Admin**: username: `admin`, password: `admin123`

**Note**: Change the default admin password in production!

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login (all users)
- `POST /api/auth/register` - Register (patients only)
- `GET /api/auth/me` - Get current user

### Admin Routes
- `GET /api/admin/dashboard` - Admin dashboard statistics
- `GET /api/admin/doctors` - List all doctors (with search)
- `POST /api/admin/doctors` - Create doctor
- `GET /api/admin/doctors/<id>` - Get doctor details
- `PUT /api/admin/doctors/<id>` - Update doctor
- `DELETE /api/admin/doctors/<id>` - Blacklist doctor
- `GET /api/admin/patients` - List all patients (with search)
- `PUT /api/admin/patients/<id>` - Update patient
- `DELETE /api/admin/patients/<id>` - Blacklist patient
- `GET /api/admin/appointments` - List all appointments (with filters)
- `GET /api/admin/departments` - List departments

### Doctor Routes
- `GET /api/doctor/dashboard` - Doctor dashboard
- `GET /api/doctor/appointments` - List doctor's appointments
- `PUT /api/doctor/appointments/<id>/complete` - Mark appointment complete
- `PUT /api/doctor/appointments/<id>/cancel` - Cancel appointment
- `POST /api/doctor/appointments/<id>/treatment` - Create treatment record
- `PUT /api/doctor/appointments/<id>/treatment` - Update treatment
- `GET /api/doctor/patients/<id>/history` - Get patient history
- `GET /api/doctor/availability` - Get availability
- `POST /api/doctor/availability` - Set availability

### Patient Routes
- `GET /api/patient/dashboard` - Patient dashboard
- `PUT /api/patient/profile` - Update profile
- `GET /api/patient/departments` - List departments
- `GET /api/patient/departments/<id>/doctors` - List doctors by department
- `GET /api/patient/doctors` - Search doctors
- `GET /api/patient/doctors/<id>` - Get doctor details
- `GET /api/patient/doctors/<id>/availability` - Get doctor availability
- `POST /api/patient/appointments` - Book appointment
- `GET /api/patient/appointments` - List appointments
- `PUT /api/patient/appointments/<id>/cancel` - Cancel appointment
- `GET /api/patient/history` - Get treatment history
- `POST /api/patient/history/export` - Export CSV (async job)

### Task Status
- `GET /api/tasks/<task_id>` - Get Celery task status

## Background Jobs

### 1. Daily Reminders (Scheduled)
- Sends daily reminders to patients with appointments scheduled for today
- Configured via Google Chat Webhooks or email
- Runs every hour (adjustable in `celery_app.py`)

### 2. Monthly Activity Report (Scheduled)
- Sends monthly activity reports to doctors via email
- Includes appointment statistics and treatment details
- HTML formatted report
- Runs on the first day of each month

### 3. CSV Export (User Triggered)
- Exports patient treatment history as CSV
- Triggered by patient request (async job)
- Returns task ID for status checking
- Includes: user_id, username, consulting doctor, appointment date, diagnosis, treatment, next visit suggested

## Caching

Redis caching is implemented for:
- Department listings (600 seconds expiry)
- Doctor listings (300 seconds expiry)
- Cache invalidation on data updates

## Core Functionalities

- **Prevent Double Booking**: Unique constraint on doctor + date + time
- **Dynamic Status Updates**: Booked → Completed → Cancelled
- **Search**: Admin/Patient can search doctors by name/specialization
- **Patient Search**: Admin can search by name, ID, or contact
- **Treatment History**: Store all completed appointment records
- **Role-based Access Control**: JWT token authentication

## Database Models

### User
- id, username, email, password_hash, role, is_active, is_blacklisted

### Doctor
- id, user_id, first_name, last_name, specialization, department_id, experience_years, qualifications, phone, bio

### Patient
- id, user_id, first_name, last_name, date_of_birth, gender, phone, address, blood_group, emergency_contact

### Department
- id, name, description

### Appointment
- id, patient_id, doctor_id, appointment_date, appointment_time, status, visit_type, notes

### Treatment
- id, appointment_id, diagnosis, prescription, tests_done, medicines, notes, next_visit_suggested

### DoctorAvailability
- id, doctor_id, available_date, morning_start, morning_end, evening_start, evening_end, is_available_morning, is_available_evening

