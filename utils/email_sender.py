import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# For simplicity, we hardcode them here but they can be moved to .env
GMAIL_USER = os.getenv("GMAIL_USER", "ttuba8525@gmail.com")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "ieqkroknzzlhontz")

def send_email(recipient_email, subject, html_body):
    """Generic function to send an email using Gmail's SMTP server."""
    if not recipient_email or not GMAIL_USER or not GMAIL_PASSWORD:
        print("[Email] Could not send email due to missing credentials or recipient.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Agentic Memory AI <{GMAIL_USER}>"
        msg["To"] = recipient_email

        part = MIMEText(html_body, "html")
        msg.attach(part)

        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, recipient_email, msg.as_string())
        server.quit()
        print(f"[Email] Successfully sent '{subject}' to {recipient_email}")
        return True
    except Exception as e:
        print(f"[Email] Failed to send email to {recipient_email}. Error: {e}")
        return False

def send_verification_email(recipient_email, verification_url):
    """Send an account verification email."""
    subject = "Verify your Agentic Memory AI Account"
    body = f"""
    <html>
      <body>
        <h2>Welcome to Agentic Memory AI!</h2>
        <p>Before you can log in, please verify your email address by clicking the link below:</p>
        <p><a href="{verification_url}" style="padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
        <p>Or paste this link into your browser: <br>{verification_url}</p>
        <p>If you didn't create an account, you can safely ignore this email.</p>
      </body>
    </html>
    """
    return send_email(recipient_email, subject, body)

def send_reminder_email(recipient_email, reminder_text):
    """Send a scheduled reminder email."""
    subject = "Reminder from Agentic Memory AI"
    body = f"""
    <html>
      <body>
        <h2>You have a reminder!</h2>
        <p style="font-size: 16px; padding: 15px; background-color: #f4f4f4; border-left: 4px solid #2196F3;">
          {reminder_text}
        </p>
      </body>
    </html>
    """
    return send_email(recipient_email, subject, body)

