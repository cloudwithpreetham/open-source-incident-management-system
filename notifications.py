"""
SMTP Email Notification Module for Incident Management System.
Supports real SMTP dispatch as well as safe local logging for demonstration/dev mode.
"""
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("incident_notifications")
logging.basicConfig(level=logging.INFO)

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "devops-alerts@internal.company.com")
ENABLE_SMTP = os.getenv("ENABLE_SMTP", "false").lower() in ("true", "1", "yes")

def send_incident_notification(recipient: str, subject: str, incident_data: dict, action_type: str = "Created"):
    """
    Sends an incident alert email to the assignee or operations team.
    Falls back gracefully to logging if SMTP server is unreachable or disabled.
    """
    body_text = f"""
=====================================================
INCIDENT ALERT: {incident_data.get('severity', 'P3')} - {incident_data.get('title', 'Unknown')}
=====================================================
Action: {action_type}
Service: {incident_data.get('service', 'N/A')}
Status: {incident_data.get('status', 'Open')}
Assigned To: {incident_data.get('assigned_to') or 'Unassigned'}
Reporter: {incident_data.get('reporter_name', 'System')} ({incident_data.get('reporter_email', '')})

Description:
{incident_data.get('description', '')}

Resolution Notes:
{incident_data.get('resolution_notes') or 'None provided yet.'}
=====================================================
View Incident Portal: http://localhost:5000/incidents/{incident_data.get('id', '')}
    """

    if not ENABLE_SMTP:
        logger.info(f"[SIMULATED NOTIFICATION to {recipient}]: {subject}")
        logger.info(body_text.strip())
        return {"status": "simulated", "recipient": recipient, "subject": subject}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = recipient

        part = MIMEText(body_text, "plain")
        msg.attach(part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as server:
            if SMTP_USER and SMTP_PASS:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [recipient], msg.as_string())

        logger.info(f"Successfully sent incident alert email to {recipient}")
        return {"status": "sent", "recipient": recipient}
    except Exception as e:
        logger.warning(f"Could not deliver email via SMTP ({e}). Fallback to console alert log.")
        return {"status": "failed_fallback_logged", "error": str(e)}
