"""Monthly activity report job - Send monthly reports to doctors (HTML + PDF)"""
from datetime import date, datetime, timedelta
from calendar import monthrange
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from backend.jobs.celery_app import celery_app
from backend.models.db import db
from backend.models.doctor import Doctor
from backend.models.appointment import Appointment
from backend.models.treatment import Treatment
from backend.config.config import Config

@celery_app.task(name='backend.jobs.monthly_reports.send_monthly_reports')
def send_monthly_reports():
    """Send monthly activity reports to doctors on the first day of each month (HTML + PDF)"""
    from backend.app import create_app
    
    app = create_app()
    with app.app_context():
        today = date.today()
        
        # Only run on the first day of the month
        if today.day != 1:
            return {'status': 'skipped', 'reason': 'Not the first day of month'}
        
        # Get previous month
        if today.month == 1:
            prev_month = 12
            prev_year = today.year - 1
        else:
            prev_month = today.month - 1
            prev_year = today.year
        
        # Get date range for previous month
        first_day = date(prev_year, prev_month, 1)
        last_day = date(prev_year, prev_month, monthrange(prev_year, prev_month)[1])
        
        doctors = Doctor.query.all()
        reports_sent = 0
        
        for doctor in doctors:
            try:
                # Get appointments for previous month
                appointments = Appointment.query.filter(
                    Appointment.doctor_id == doctor.id,
                    Appointment.appointment_date >= first_day,
                    Appointment.appointment_date <= last_day
                ).all()
                
                # Generate HTML report
                report_html = generate_monthly_report_html(doctor, appointments, prev_month, prev_year)
                
                # Generate PDF report
                pdf_buffer = generate_monthly_report_pdf(doctor, appointments, prev_month, prev_year)
                
                # Send email with both HTML body and PDF attachment
                if doctor.user and doctor.user.email:
                    send_email_report(doctor.user.email, report_html, pdf_buffer, prev_month, prev_year)
                    reports_sent += 1
                
            except Exception as e:
                print(f"Error generating report for doctor {doctor.id}: {str(e)}")
                continue
        
        return {
            'status': 'success',
            'reports_sent': reports_sent,
            'month': prev_month,
            'year': prev_year
        }

def generate_monthly_report_html(doctor, appointments, month, year):
    """Generate HTML report for doctor's monthly activity"""
    month_name = datetime(year, month, 1).strftime('%B')
    
    completed_count = sum(1 for apt in appointments if apt.status == 'Completed')
    total_count = len(appointments)
    
    # Get treatments
    treatment_data = []
    for apt in appointments:
        if apt.treatment:
            treatment_data.append({
                'date': apt.appointment_date.isoformat(),
                'patient': apt.patient.full_name if apt.patient else 'N/A',
                'diagnosis': apt.treatment.diagnosis[:100] if apt.treatment.diagnosis else 'N/A',
                'prescription': apt.treatment.prescription[:100] if apt.treatment.prescription else 'N/A',
            })
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monthly Activity Report - {month_name} {year}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #2c3e50; }}
            .stats {{ background-color: #ecf0f1; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #3498db; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Monthly Activity Report - {month_name} {year}</h1>
        <h2>Dr. {doctor.full_name}</h2>
        <div class="stats">
            <h3>Statistics</h3>
            <p><strong>Total Appointments:</strong> {total_count}</p>
            <p><strong>Completed Appointments:</strong> {completed_count}</p>
            <p><strong>Specialization:</strong> {doctor.specialization}</p>
        </div>
        
        <h3>Treatment Details</h3>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Patient</th>
                    <th>Diagnosis</th>
                    <th>Prescription</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for treatment in treatment_data:
        html += f"""
                <tr>
                    <td>{treatment['date']}</td>
                    <td>{treatment['patient']}</td>
                    <td>{treatment['diagnosis']}</td>
                    <td>{treatment['prescription']}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    return html

def generate_monthly_report_pdf(doctor, appointments, month, year):
    """Generate PDF report for doctor's monthly activity using ReportLab"""
    month_name = datetime(year, month, 1).strftime('%B')
    
    completed_count = sum(1 for apt in appointments if apt.status == 'Completed')
    total_count = len(appointments)
    
    # Build treatment data
    treatment_data = []
    for apt in appointments:
        if apt.treatment:
            treatment_data.append([
                apt.appointment_date.strftime('%Y-%m-%d'),
                apt.patient.full_name if apt.patient else 'N/A',
                (apt.treatment.diagnosis[:80] + '...') if apt.treatment.diagnosis and len(apt.treatment.diagnosis) > 80 else (apt.treatment.diagnosis or 'N/A'),
                (apt.treatment.prescription[:80] + '...') if apt.treatment.prescription and len(apt.treatment.prescription) > 80 else (apt.treatment.prescription or 'N/A'),
            ])
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15
    )
    
    story = []
    
    # Title
    story.append(Paragraph(f'Monthly Activity Report - {month_name} {year}', title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Doctor name
    story.append(Paragraph(f'<b>Dr. {doctor.full_name}</b>', styles['Normal']))
    story.append(Paragraph(f'Specialization: {doctor.specialization}', styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Statistics
    story.append(Paragraph('Statistics', heading_style))
    stats_data = [
        ['Total Appointments', str(total_count)],
        ['Completed Appointments', str(completed_count)],
        ['Cancelled', str(sum(1 for apt in appointments if apt.status == 'Cancelled'))],
    ]
    stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Treatment Details
    story.append(Paragraph('Treatment Details', heading_style))
    if treatment_data:
        header_row = [['Date', 'Patient', 'Diagnosis', 'Prescription']]
        table_data = header_row + treatment_data
        t = Table(table_data, colWidths=[1*inch, 1.5*inch, 2.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)
    else:
        story.append(Paragraph('No treatment records for this period.', styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def send_email_report(email, html_content, pdf_content, month, year):
    """Send HTML report and PDF attachment via email"""
    if not Config.MAIL_SERVER or not Config.MAIL_USERNAME:
        print(f"Email not configured. Would send report to {email}")
        return
    
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f'Monthly Activity Report - {datetime(year, month, 1).strftime("%B %Y")}'
        msg['From'] = Config.MAIL_USERNAME
        msg['To'] = email
        
        # HTML body
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # PDF attachment
        pdf_attachment = MIMEBase('application', 'pdf')
        pdf_attachment.set_payload(pdf_content)
        encoders.encode_base64(pdf_attachment)
        pdf_filename = f"Monthly_Report_{datetime(year, month, 1).strftime('%B_%Y')}.pdf"
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
        msg.attach(pdf_attachment)
        
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Report (HTML + PDF) sent to {email}")
        
    except Exception as e:
        print(f"Failed to send email report to {email}: {str(e)}")

