// Hospital Management System - Vue.js Application

const API_BASE = '/api';

const { createApp } = Vue;

const app = createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            // Auth state
            isLoggedIn: false,
            user: null,
            profile: null,
            token: null,
            
            // UI state
            currentView: 'login',
            authTab: 'login',
            loading: false,
            error: null,
            modalError: null,
            
            // Toast
            showToast: false,
            toastMessage: '',
            toastType: 'success',
            
            // Forms
            loginForm: { username: '', password: '' },
            registerForm: {
                role: 'patient',
                username: '', email: '', password: '', first_name: '', last_name: '',
                phone: '', date_of_birth: '', gender: '', blood_group: '',
                department_id: '', specialization: '', experience_years: 0, qualifications: '', bio: ''
            },
            registrationDepartments: [],
            
            // Admin data
            stats: {},
            chartData: {},
            recentAppointments: [],
            doctors: [],
            patients: [],
            allAppointments: [],
            departments: [],
            searchQuery: '',
            filterDepartment: '',
            patientSearch: '',
            patientIdSearch: '',
            appointmentFilter: { status: '', date_from: '', date_to: '' },
            
            // Doctor forms
            doctorForm: {
                first_name: '', last_name: '', username: '', password: '', email: '',
                specialization: '', department_id: '', experience_years: '', phone: '',
                qualifications: '', bio: ''
            },
            editingDoctor: null,
            
            // Patient forms
            patientForm: {
                first_name: '', last_name: '', phone: '', date_of_birth: '', gender: '', blood_group: ''
            },
            editingPatient: null,
            
            // Doctor dashboard data
            doctorUpcomingAppointments: [],
            assignedPatients: [],
            doctorAppointments: [],
            doctorAppointmentFilter: { status: '', date_from: '', date_to: '' },
            availabilitySlots: [],
            selectedPatientHistory: null,
            
            // Treatment
            selectedAppointment: null,
            treatmentForm: {
                diagnosis: '', prescription: '', medicines: '', tests_done: '',
                next_visit_suggested: '', notes: ''
            },
            
            // Patient dashboard data
            patientUpcomingAppointments: [],
            patientAppointments: [],
            patientAppointmentFilter: { status: '', include_past: false },
            medicalHistory: [],
            availableDoctors: [],
            doctorSearchQuery: '',
            selectedDepartmentId: '',
            
            // Booking
            selectedDoctor: null,
            doctorAvailability: [],
            bookedSlots: {},
            availableTimeSlots: [],
            bookingForm: {
                appointment_date: '', appointment_time: '', visit_type: 'In-person', notes: ''
            },
            
            // Profile
            profileForm: {
                first_name: '', last_name: '', email: '', phone: '', date_of_birth: '',
                gender: '', blood_group: '', address: '', emergency_contact: '', emergency_phone: ''
            },
            
            // Viewing treatment
            viewingTreatment: null,
            
            // Export
            exportLoading: false,
            exportTaskId: null,
            reminderTriggerLoading: false,
            
            // Constants
            bloodGroups: ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
            
            // Chart.js instances (for cleanup)
            chartInstances: {}
        };
    },
    
    computed: {
        todayAppointments() {
            const today = new Date().toISOString().split('T')[0];
            return this.doctorUpcomingAppointments.filter(apt => apt.appointment_date === today);
        }
    },
    
    mounted() {
        this.checkAuth();
    },
    
    methods: {
        // API helper
        async api(method, endpoint, data = null) {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            if (this.token) {
                options.headers['Authorization'] = `Bearer ${this.token}`;
            }
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            let response;
            try {
                response = await fetch(`${API_BASE}${endpoint}`, options);
            } catch (e) {
                throw new Error('API request failed. Check server/network.');
            }

            let result = {};
            try {
                result = await response.json();
            } catch (e) {
                result = {};
            }
            
            if (!response.ok) {
                throw new Error(result.error || 'API request failed');
            }
            
            return result;
        },
        
        // Auth methods
        async checkAuth() {
            const token = localStorage.getItem('token');
            if (token) {
                this.token = token;
                try {
                    const data = await this.api('GET', '/auth/me');
                    this.user = data.user;
                    this.profile = data.profile;
                    this.isLoggedIn = true;
                    this.navigateTo('dashboard');
                } catch (e) {
                    localStorage.removeItem('token');
                    this.token = null;
                }
            }
        },
        
        async login() {
            this.loading = true;
            this.error = null;
            try {
                const data = await this.api('POST', '/auth/login', this.loginForm);
                this.token = data.access_token;
                localStorage.setItem('token', this.token);
                this.user = data.user;
                this.profile = data.profile;
                this.isLoggedIn = true;
                this.loginForm = { username: '', password: '' };
                this.navigateTo('dashboard');
                this.showNotification('Login successful!', 'success');
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        async loadRegistrationDepartments() {
            try {
                const data = await this.api('GET', '/auth/departments');
                this.registrationDepartments = data.departments || [];
            } catch (e) {
                console.error('Failed to load departments:', e);
            }
        },
        
        async register() {
            this.loading = true;
            this.error = null;
            try {
                const payload = { ...this.registerForm };
                if (payload.role === 'patient') {
                    delete payload.department_id;
                    delete payload.specialization;
                    delete payload.experience_years;
                    delete payload.qualifications;
                    delete payload.bio;
                } else {
                    delete payload.date_of_birth;
                    delete payload.gender;
                    delete payload.blood_group;
                }
                const data = await this.api('POST', '/auth/register', payload);
                this.token = data.access_token;
                localStorage.setItem('token', this.token);
                this.user = data.user;
                this.profile = data.profile;
                this.isLoggedIn = true;
                this.registerForm = {
                    role: 'patient',
                    username: '', email: '', password: '', first_name: '', last_name: '',
                    phone: '', date_of_birth: '', gender: '', blood_group: '',
                    department_id: '', specialization: '', experience_years: 0, qualifications: '', bio: ''
                };
                this.navigateTo('dashboard');
                this.showNotification('Registration successful!', 'success');
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        logout() {
            localStorage.removeItem('token');
            this.token = null;
            this.user = null;
            this.profile = null;
            this.isLoggedIn = false;
            this.currentView = 'login';
            this.showNotification('Logged out successfully', 'success');
        },
        
        // Navigation
        navigateTo(view) {
            this.currentView = view;
            this.error = null;
            this.modalError = null;
            
            if (view === 'dashboard') {
                this.loadDashboard();
            } else if (view === 'doctors' && this.user?.role === 'admin') {
                this.loadDoctors();
                this.loadDepartments();
            } else if (view === 'patients' && this.user?.role === 'admin') {
                this.loadPatients();
            } else if (view === 'appointments' && this.user?.role === 'admin') {
                this.loadAllAppointments();
            } else if (view === 'my-appointments' && this.user?.role === 'doctor') {
                this.loadDoctorAppointments();
            } else if (view === 'availability' && this.user?.role === 'doctor') {
                this.initializeAvailabilitySlots();
                this.loadDoctorAvailability();
            } else if (view === 'my-patients' && this.user?.role === 'doctor') {
                this.loadAssignedPatients();
            } else if (view === 'find-doctors' && this.user?.role === 'patient') {
                this.loadAvailableDoctors();
                this.loadPatientDepartments();
            } else if (view === 'my-appointments' && this.user?.role === 'patient') {
                this.loadPatientAppointments();
            } else if (view === 'history' && this.user?.role === 'patient') {
                this.loadMedicalHistory();
            } else if (view === 'profile') {
                this.loadProfile();
            }
        },
        
        // Load Dashboard based on role
        async loadDashboard() {
            if (this.user?.role === 'admin') {
                await this.loadAdminDashboard();
            } else if (this.user?.role === 'doctor') {
                await this.loadDoctorDashboard();
            } else if (this.user?.role === 'patient') {
                await this.loadPatientDashboard();
            }
        },

        async triggerDailyReminders() {
            this.reminderTriggerLoading = true;
            try {
                const data = await this.api('POST', '/admin/reminders/trigger');
                const taskId = data.task_id || 'N/A';
                this.showNotification(`Daily reminders queued. Task ID: ${taskId}`, 'success');
                if (taskId !== 'N/A') {
                    this.pollReminderTaskStatus(taskId);
                }
            } catch (e) {
                this.showNotification(e.message, 'error');
            } finally {
                this.reminderTriggerLoading = false;
            }
        },

        async pollReminderTaskStatus(taskId, attempt = 0) {
            const maxAttempts = 10;
            try {
                const status = await this.api('GET', `/tasks/${taskId}`);
                if (status.state === 'SUCCESS') {
                    const result = status.result || {};
                    const found = result.appointments_found ?? 0;
                    const sent = result.reminders_sent ?? 0;
                    const failed = result.failed_sends ?? 0;
                    if (!result.mail_configured) {
                        this.showNotification(
                            `Reminder task completed, but mail is not configured on worker. Found: ${found}, Sent: ${sent}, Failed: ${failed}.`,
                            'error'
                        );
                        return;
                    }
                    this.showNotification(
                        `Reminder task done. Found: ${found}, Sent: ${sent}, Failed: ${failed}.`,
                        failed > 0 ? 'error' : 'success'
                    );
                    return;
                }

                if (status.state === 'FAILURE') {
                    this.showNotification(`Reminder task failed: ${status.error || 'Unknown error'}`, 'error');
                    return;
                }

                if (attempt < maxAttempts) {
                    setTimeout(() => this.pollReminderTaskStatus(taskId, attempt + 1), 2000);
                } else {
                    this.showNotification('Reminder task is still running. Check worker logs for details.', 'error');
                }
            } catch (e) {
                this.showNotification(`Failed to check task status: ${e.message}`, 'error');
            }
        },
        
        // Admin methods
        async loadAdminDashboard() {
            try {
                const data = await this.api('GET', '/admin/dashboard');
                this.stats = data.statistics;
                this.recentAppointments = data.recent_appointments;
                this.chartData = data.chart_data || {};
                this.$nextTick(() => this.initAdminCharts());
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async loadDoctors() {
            try {
                let url = '/admin/doctors';
                const params = [];
                if (this.searchQuery) params.push(`search=${encodeURIComponent(this.searchQuery)}`);
                if (this.filterDepartment) params.push(`department_id=${this.filterDepartment}`);
                if (params.length) url += '?' + params.join('&');
                
                const data = await this.api('GET', url);
                this.doctors = data.doctors;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        searchDoctors() {
            this.loadDoctors();
        },
        
        async loadDepartments() {
            try {
                const data = await this.api('GET', '/admin/departments');
                this.departments = data.departments || [];
            } catch (e) {
                console.error('Failed to load departments:', e);
                this.departments = [];
            }
        },

        async loadPatientDepartments() {
            try {
                const data = await this.api('GET', '/patient/departments');
                this.departments = data.departments;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        showDoctorModal(doctor = null) {
            this.editingDoctor = doctor;
            this.modalError = null;
            
            if (doctor) {
                this.doctorForm = {
                    first_name: doctor.first_name,
                    last_name: doctor.last_name,
                    email: '',
                    specialization: doctor.specialization,
                    department_id: doctor.department_id,
                    experience_years: doctor.experience_years,
                    phone: doctor.phone || '',
                    qualifications: doctor.qualifications || '',
                    bio: doctor.bio || ''
                };
            } else {
                this.doctorForm = {
                    first_name: '', last_name: '', username: '', password: '', email: '',
                    specialization: '', department_id: '', experience_years: '', phone: '',
                    qualifications: '', bio: ''
                };
            }
            
            const modal = new bootstrap.Modal(document.getElementById('doctorModal'));
            modal.show();
        },
        
        async saveDoctor() {
            this.loading = true;
            this.modalError = null;
            try {
                if (this.editingDoctor) {
                    await this.api('PUT', `/admin/doctors/${this.editingDoctor.id}`, this.doctorForm);
                    this.showNotification('Doctor updated successfully', 'success');
                } else {
                    await this.api('POST', '/admin/doctors', this.doctorForm);
                    this.showNotification('Doctor created successfully', 'success');
                }
                bootstrap.Modal.getInstance(document.getElementById('doctorModal')).hide();
                this.loadDoctors();
                this.loadAdminDashboard();
            } catch (e) {
                this.modalError = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        confirmDeleteDoctor(doctor) {
            if (confirm(`Are you sure you want to blacklist Dr. ${doctor.full_name}?`)) {
                this.deleteDoctor(doctor);
            }
        },
        
        async deleteDoctor(doctor) {
            try {
                await this.api('DELETE', `/admin/doctors/${doctor.id}`);
                this.showNotification('Doctor blacklisted successfully', 'success');
                this.loadDoctors();
                this.loadAdminDashboard();
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async loadPatients() {
            try {
                let url = '/admin/patients';
                const params = [];
                if (this.patientSearch) params.push(`search=${encodeURIComponent(this.patientSearch)}`);
                if (this.patientIdSearch) params.push(`id=${this.patientIdSearch}`);
                if (params.length) url += '?' + params.join('&');
                
                const data = await this.api('GET', url);
                this.patients = data.patients;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        searchPatients() {
            this.loadPatients();
        },
        
        showPatientModal(patient) {
            this.editingPatient = patient;
            this.modalError = null;
            this.patientForm = {
                first_name: patient.first_name,
                last_name: patient.last_name,
                phone: patient.phone || '',
                date_of_birth: patient.date_of_birth || '',
                gender: patient.gender || '',
                blood_group: patient.blood_group || ''
            };
            
            const modal = new bootstrap.Modal(document.getElementById('patientModal'));
            modal.show();
        },
        
        async savePatient() {
            this.loading = true;
            this.modalError = null;
            try {
                await this.api('PUT', `/admin/patients/${this.editingPatient.id}`, this.patientForm);
                this.showNotification('Patient updated successfully', 'success');
                bootstrap.Modal.getInstance(document.getElementById('patientModal')).hide();
                this.loadPatients();
            } catch (e) {
                this.modalError = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        confirmDeletePatient(patient) {
            if (confirm(`Are you sure you want to blacklist ${patient.full_name}?`)) {
                this.deletePatient(patient);
            }
        },
        
        async deletePatient(patient) {
            try {
                await this.api('DELETE', `/admin/patients/${patient.id}`);
                this.showNotification('Patient blacklisted successfully', 'success');
                this.loadPatients();
                this.loadAdminDashboard();
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async loadAllAppointments() {
            try {
                let url = '/admin/appointments';
                const params = [];
                if (this.appointmentFilter.status) params.push(`status=${this.appointmentFilter.status}`);
                if (this.appointmentFilter.date_from) params.push(`date_from=${this.appointmentFilter.date_from}`);
                if (this.appointmentFilter.date_to) params.push(`date_to=${this.appointmentFilter.date_to}`);
                if (params.length) url += '?' + params.join('&');
                
                const data = await this.api('GET', url);
                this.allAppointments = data.appointments;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        clearAppointmentFilters() {
            this.appointmentFilter = { status: '', date_from: '', date_to: '' };
            this.loadAllAppointments();
        },
        
        // Doctor methods
        async loadDoctorDashboard() {
            try {
                const data = await this.api('GET', '/doctor/dashboard');
                this.profile = data.doctor;
                this.doctorUpcomingAppointments = data.upcoming_appointments;
                this.assignedPatients = data.assigned_patients;
                this.$nextTick(() => this.initDoctorCharts());
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async loadDoctorAppointments() {
            try {
                let url = '/doctor/appointments';
                const params = [];
                if (this.doctorAppointmentFilter.status) params.push(`status=${this.doctorAppointmentFilter.status}`);
                if (this.doctorAppointmentFilter.date_from) params.push(`date_from=${this.doctorAppointmentFilter.date_from}`);
                if (this.doctorAppointmentFilter.date_to) params.push(`date_to=${this.doctorAppointmentFilter.date_to}`);
                if (params.length) url += '?' + params.join('&');
                
                const data = await this.api('GET', url);
                this.doctorAppointments = data.appointments;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async markAppointmentComplete(appointment) {
            try {
                await this.api('PUT', `/doctor/appointments/${appointment.id}/complete`);
                this.showNotification('Appointment marked as completed', 'success');
                if (this.currentView === 'dashboard') {
                    this.loadDoctorDashboard();
                } else {
                    this.loadDoctorAppointments();
                }
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async cancelDoctorAppointment(appointment) {
            if (!confirm('Are you sure you want to cancel this appointment?')) return;
            
            try {
                await this.api('PUT', `/doctor/appointments/${appointment.id}/cancel`);
                this.showNotification('Appointment cancelled', 'success');
                this.loadDoctorAppointments();
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        showTreatmentModal(appointment) {
            this.selectedAppointment = appointment;
            this.modalError = null;
            
            if (appointment.has_treatment) {
                this.loadTreatmentData(appointment.id);
            } else {
                this.treatmentForm = {
                    diagnosis: '', prescription: '', medicines: '', tests_done: '',
                    next_visit_suggested: '', notes: ''
                };
            }
            
            const modal = new bootstrap.Modal(document.getElementById('treatmentModal'));
            modal.show();
        },
        
        async loadTreatmentData(appointmentId) {
            try {
                const data = await this.api('GET', `/doctor/patients/${this.selectedAppointment.patient_id}/history`);
                const apt = data.appointments.find(a => a.id === appointmentId);
                if (apt && apt.treatment) {
                    this.treatmentForm = {
                        diagnosis: apt.treatment.diagnosis || '',
                        prescription: apt.treatment.prescription || '',
                        medicines: apt.treatment.medicines || '',
                        tests_done: apt.treatment.tests_done || '',
                        next_visit_suggested: apt.treatment.next_visit_suggested || '',
                        notes: apt.treatment.notes || ''
                    };
                }
            } catch (e) {
                console.error('Failed to load treatment:', e);
            }
        },
        
        async saveTreatment() {
            this.loading = true;
            this.modalError = null;
            try {
                const method = this.selectedAppointment.has_treatment ? 'PUT' : 'POST';
                await this.api(method, `/doctor/appointments/${this.selectedAppointment.id}/treatment`, this.treatmentForm);
                this.showNotification('Treatment saved successfully', 'success');
                bootstrap.Modal.getInstance(document.getElementById('treatmentModal')).hide();
                if (this.currentView === 'dashboard') {
                    this.loadDoctorDashboard();
                } else {
                    this.loadDoctorAppointments();
                }
            } catch (e) {
                this.modalError = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        initializeAvailabilitySlots() {
            const slots = [];
            const today = new Date();
            
            for (let i = 0; i < 7; i++) {
                const date = new Date(today);
                date.setDate(today.getDate() + i);
                slots.push({
                    date: date.toISOString().split('T')[0],
                    is_available_morning: true,
                    morning_start: '09:00',
                    morning_end: '12:00',
                    is_available_evening: true,
                    evening_start: '14:00',
                    evening_end: '18:00'
                });
            }
            
            this.availabilitySlots = slots;
        },
        
        async loadDoctorAvailability() {
            try {
                const data = await this.api('GET', '/doctor/availability');
                
                data.availability.forEach(av => {
                    const slot = this.availabilitySlots.find(s => s.date === av.available_date);
                    if (slot) {
                        slot.is_available_morning = av.is_available_morning;
                        slot.morning_start = av.morning_start ? av.morning_start.substring(0, 5) : '09:00';
                        slot.morning_end = av.morning_end ? av.morning_end.substring(0, 5) : '12:00';
                        slot.is_available_evening = av.is_available_evening;
                        slot.evening_start = av.evening_start ? av.evening_start.substring(0, 5) : '14:00';
                        slot.evening_end = av.evening_end ? av.evening_end.substring(0, 5) : '18:00';
                    }
                });
            } catch (e) {
                console.error('Failed to load availability:', e);
            }
        },
        
        async saveAvailability() {
            this.loading = true;
            try {
                const availability = this.availabilitySlots.map(slot => ({
                    date: slot.date,
                    is_available_morning: slot.is_available_morning,
                    morning_start: slot.morning_start + ':00',
                    morning_end: slot.morning_end + ':00',
                    is_available_evening: slot.is_available_evening,
                    evening_start: slot.evening_start + ':00',
                    evening_end: slot.evening_end + ':00'
                }));
                
                await this.api('POST', '/doctor/availability', { availability });
                this.showNotification('Availability saved successfully', 'success');
            } catch (e) {
                this.showNotification(e.message, 'error');
            } finally {
                this.loading = false;
            }
        },
        
        async loadAssignedPatients() {
            try {
                const data = await this.api('GET', '/doctor/dashboard');
                this.assignedPatients = data.assigned_patients;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async viewPatientHistory(patientId) {
            try {
                const data = await this.api('GET', `/doctor/patients/${patientId}/history`);
                this.selectedPatientHistory = data;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        // Patient methods
        async loadPatientDashboard() {
            try {
                const data = await this.api('GET', '/patient/dashboard');
                this.profile = data.patient;
                this.patientUpcomingAppointments = data.upcoming_appointments;
                this.departments = data.departments;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async viewDepartmentDoctors(dept) {
            this.selectedDepartmentId = dept.id;
            this.navigateTo('find-doctors');
        },
        
        async loadAvailableDoctors() {
            try {
                let url = '/patient/doctors';
                const params = [];
                if (this.doctorSearchQuery) params.push(`search=${encodeURIComponent(this.doctorSearchQuery)}`);
                if (params.length) url += '?' + params.join('&');
                
                const data = await this.api('GET', url);
                this.availableDoctors = data.doctors;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        searchAvailableDoctors() {
            this.loadAvailableDoctors();
        },
        
        async loadDepartmentDoctors() {
            try {
                if (this.selectedDepartmentId) {
                    const data = await this.api('GET', `/patient/departments/${this.selectedDepartmentId}/doctors`);
                    this.availableDoctors = data.doctors;
                } else {
                    this.loadAvailableDoctors();
                }
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async showBookingModal(doctor) {
            this.selectedDoctor = doctor;
            this.modalError = null;
            this.bookingForm = {
                appointment_date: '', appointment_time: '', visit_type: 'In-person', notes: ''
            };
            this.availableTimeSlots = [];
            
            try {
                const data = await this.api('GET', `/patient/doctors/${doctor.id}/availability`);
                this.doctorAvailability = data.availability;
                this.bookedSlots = data.booked_slots;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
            
            const modal = new bootstrap.Modal(document.getElementById('bookingModal'));
            modal.show();
        },
        
        loadTimeSlots() {
            const selectedDate = this.bookingForm.appointment_date;
            const availability = this.doctorAvailability.find(a => a.available_date === selectedDate);
            
            if (!availability) {
                this.availableTimeSlots = [];
                return;
            }
            
            const slots = [];
            
            if (availability.is_available_morning && availability.morning_start && availability.morning_end) {
                const start = this.parseTime(availability.morning_start);
                const end = this.parseTime(availability.morning_end);
                for (let hour = start; hour < end; hour++) {
                    slots.push(`${hour.toString().padStart(2, '0')}:00:00`);
                    slots.push(`${hour.toString().padStart(2, '0')}:30:00`);
                }
            }
            
            if (availability.is_available_evening && availability.evening_start && availability.evening_end) {
                const start = this.parseTime(availability.evening_start);
                const end = this.parseTime(availability.evening_end);
                for (let hour = start; hour < end; hour++) {
                    slots.push(`${hour.toString().padStart(2, '0')}:00:00`);
                    slots.push(`${hour.toString().padStart(2, '0')}:30:00`);
                }
            }
            
            this.availableTimeSlots = slots;
        },
        
        parseTime(timeStr) {
            return parseInt(timeStr.split(':')[0]);
        },
        
        isSlotBooked(time) {
            const selectedDate = this.bookingForm.appointment_date;
            return this.bookedSlots[selectedDate]?.includes(time);
        },
        
        async bookAppointment() {
            this.loading = true;
            this.modalError = null;
            try {
                await this.api('POST', '/patient/appointments', {
                    doctor_id: this.selectedDoctor.id,
                    appointment_date: this.bookingForm.appointment_date,
                    appointment_time: this.bookingForm.appointment_time,
                    visit_type: this.bookingForm.visit_type,
                    notes: this.bookingForm.notes
                });
                this.showNotification('Appointment booked successfully!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('bookingModal')).hide();
                this.loadPatientDashboard();
            } catch (e) {
                this.modalError = e.message;
            } finally {
                this.loading = false;
            }
        },
        
        async loadPatientAppointments() {
            try {
                let url = '/patient/appointments';
                const params = [];
                if (this.patientAppointmentFilter.status) params.push(`status=${this.patientAppointmentFilter.status}`);
                if (this.patientAppointmentFilter.include_past) params.push('include_past=true');
                if (params.length) url += '?' + params.join('&');
                
                const data = await this.api('GET', url);
                this.patientAppointments = data.appointments;
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async cancelPatientAppointment(appointment) {
            if (!confirm('Are you sure you want to cancel this appointment?')) return;
            
            try {
                await this.api('PUT', `/patient/appointments/${appointment.id}/cancel`);
                this.showNotification('Appointment cancelled', 'success');
                if (this.currentView === 'dashboard') {
                    this.loadPatientDashboard();
                } else {
                    this.loadPatientAppointments();
                }
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        viewTreatmentDetails(appointment) {
            this.viewingTreatment = appointment.treatment;
            const modal = new bootstrap.Modal(document.getElementById('treatmentViewModal'));
            modal.show();
        },
        
        async loadMedicalHistory() {
            try {
                const data = await this.api('GET', '/patient/history');
                this.medicalHistory = data.history;
                this.$nextTick(() => this.initPatientHistoryChart());
            } catch (e) {
                this.showNotification(e.message, 'error');
            }
        },
        
        async exportHistory() {
            this.exportLoading = true;
            this.exportTaskId = null;
            try {
                const response = await fetch(`${API_BASE}/patient/history/export`, {
                    method: 'GET',
                    headers: this.token ? { 'Authorization': `Bearer ${this.token}` } : {}
                });

                if (!response.ok) {
                    let errorMessage = 'Failed to export CSV';
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } catch (e) {
                        // Non-JSON error body; keep default message.
                    }
                    throw new Error(errorMessage);
                }

                const blob = await response.blob();
                const disposition = response.headers.get('Content-Disposition') || '';
                const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
                const filename = filenameMatch ? filenameMatch[1] : 'medical_history.csv';

                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);

                this.showNotification('CSV downloaded successfully.', 'success');
            } catch (e) {
                this.showNotification(e.message, 'error');
            } finally {
                this.exportLoading = false;
            }
        },
        
        // Profile
        loadProfile() {
            if (this.profile && this.user?.role === 'patient') {
                this.profileForm = {
                    first_name: this.profile.first_name || '',
                    last_name: this.profile.last_name || '',
                    email: this.user.email || '',
                    phone: this.profile.phone || '',
                    date_of_birth: this.profile.date_of_birth || '',
                    gender: this.profile.gender || '',
                    blood_group: this.profile.blood_group || '',
                    address: this.profile.address || '',
                    emergency_contact: this.profile.emergency_contact || '',
                    emergency_phone: this.profile.emergency_phone || ''
                };
            }
        },
        
        async updateProfile() {
            this.loading = true;
            try {
                const data = await this.api('PUT', '/patient/profile', this.profileForm);
                this.profile = data.patient;
                this.showNotification('Profile updated successfully', 'success');
            } catch (e) {
                this.showNotification(e.message, 'error');
            } finally {
                this.loading = false;
            }
        },
        
        // Chart.js initialization
        destroyChart(name) {
            if (this.chartInstances[name]) {
                this.chartInstances[name].destroy();
                this.chartInstances[name] = null;
            }
        },
        
        initAdminCharts() {
            if (typeof Chart === 'undefined') return;
            
            this.destroyChart('adminStatus');
            this.destroyChart('adminDepartment');
            
            const statusData = this.chartData.appointment_status_breakdown || {};
            const labels = Object.keys(statusData);
            const values = Object.values(statusData);
            const colors = ['#0d6efd', '#198754', '#dc3545', '#ffc107'];
            
            if (labels.length > 0) {
                const ctx = document.getElementById('adminStatusChart');
                if (ctx) {
                    this.chartInstances['adminStatus'] = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: labels,
                            datasets: [{
                                data: values,
                                backgroundColor: colors.slice(0, labels.length),
                                borderWidth: 2
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { position: 'bottom' } }
                        }
                    });
                }
            }
            
            const deptData = this.chartData.appointments_by_department || [];
            if (deptData.length > 0) {
                const ctx = document.getElementById('adminDepartmentChart');
                if (ctx) {
                    this.chartInstances['adminDepartment'] = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: deptData.map(d => d.department),
                            datasets: [{
                                label: 'Appointments',
                                data: deptData.map(d => d.count),
                                backgroundColor: 'rgba(13, 110, 253, 0.7)',
                                borderColor: '#0d6efd',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: { beginAtZero: true }
                            },
                            plugins: { legend: { display: false } }
                        }
                    });
                }
            }
        },
        
        initDoctorCharts() {
            if (typeof Chart === 'undefined') return;
            
            this.destroyChart('doctorAppointments');
            
            const aptsByDate = {};
            this.doctorUpcomingAppointments.forEach(apt => {
                const d = apt.appointment_date;
                aptsByDate[d] = (aptsByDate[d] || 0) + 1;
            });
            
            const today = new Date();
            const labels = [];
            const data = [];
            for (let i = 0; i < 7; i++) {
                const d = new Date(today);
                d.setDate(today.getDate() + i);
                const dateStr = d.toISOString().split('T')[0];
                labels.push(this.formatDate(dateStr));
                data.push(aptsByDate[dateStr] || 0);
            }
            
            const ctx = document.getElementById('doctorAppointmentsChart');
            if (ctx) {
                this.chartInstances['doctorAppointments'] = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Appointments',
                            data: data,
                            backgroundColor: 'rgba(13, 110, 253, 0.7)',
                            borderColor: '#0d6efd',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                });
            }
        },
        
        initPatientHistoryChart() {
            if (typeof Chart === 'undefined') return;
            
            this.destroyChart('patientHistory');
            
            const statusCounts = {};
            this.medicalHistory.forEach(record => {
                const s = record.status || 'Unknown';
                statusCounts[s] = (statusCounts[s] || 0) + 1;
            });
            
            const labels = Object.keys(statusCounts);
            const values = Object.values(statusCounts);
            const colors = { 'Booked': '#0d6efd', 'Completed': '#198754', 'Cancelled': '#dc3545' };
            const bgColors = labels.map(l => colors[l] || '#6c757d');
            
            if (labels.length > 0) {
                const ctx = document.getElementById('patientHistoryChart');
                if (ctx) {
                    this.chartInstances['patientHistory'] = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: labels,
                            datasets: [{
                                data: values,
                                backgroundColor: bgColors,
                                borderWidth: 2
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { position: 'bottom' } }
                        }
                    });
                }
            }
        },
        
        // Utility methods
        formatDate(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        },
        
        formatTime(timeStr) {
            if (!timeStr) return '-';
            const [hours, minutes] = timeStr.split(':');
            const hour = parseInt(hours);
            const ampm = hour >= 12 ? 'PM' : 'AM';
            const hour12 = hour % 12 || 12;
            return `${hour12}:${minutes} ${ampm}`;
        },
        
        getDayName(dateStr) {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { weekday: 'long' });
        },
        
        getStatusBadge(status) {
            const badges = {
                'Booked': 'bg-primary',
                'Completed': 'bg-success',
                'Cancelled': 'bg-danger'
            };
            return badges[status] || 'bg-secondary';
        },
        
        showNotification(message, type = 'success') {
            this.toastMessage = message;
            this.toastType = type;
            this.showToast = true;
            setTimeout(() => {
                this.showToast = false;
            }, 3000);
        }
    }
});

app.mount('#app');
