"""
email_handler.py
© 2026 Fayaz Ahmed Shaik. All rights reserved.
─────────────────────────────────────────────
Handles sending transactional emails using Brevo (formerly Sendinblue) SMTP.
Uses Python's built-in smtplib — no extra packages needed.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# ── Brevo SMTP Configuration ─────────────────────────────────────────────────
BREVO_SMTP_SERVER = "smtp-relay.brevo.com"
BREVO_SMTP_PORT = 587
BREVO_SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN", "")     # Your Brevo account email
BREVO_SMTP_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD", "") # Your Brevo SMTP key
SENDER_EMAIL = os.getenv("SENDER_EMAIL", BREVO_SMTP_LOGIN) # "From" address
SENDER_NAME = "Fury AI"


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Sends an email via Brevo SMTP relay.
    Returns True on success, False on failure.
    """
    if not BREVO_SMTP_LOGIN or not BREVO_SMTP_PASSWORD:
        logger.error("BREVO_SMTP_LOGIN or BREVO_SMTP_PASSWORD is not set. Email sending failed.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(BREVO_SMTP_SERVER, BREVO_SMTP_PORT) as server:
            server.starttls()
            server.login(BREVO_SMTP_LOGIN, BREVO_SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_otp_email(receiver_email: str, otp: str) -> bool:
    """
    Sends a 6-digit OTP to the user's email for verification.
    """
    subject = f"{otp} is your Fury AI verification code"
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #4285f4;">Verify Your Email</h2>
        <p>To complete your registration, please use the following one-time password (OTP):</p>
        <div style="background: #f4f4f4; padding: 15px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; border-radius: 5px; color: #333;">
            {otp}
        </div>
        <p style="margin-top: 20px; color: #666;">This code will expire in 10 minutes. If you didn't request this, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #999;">© 2026 Fayaz Ahmed Shaik. All rights reserved.</p>
    </div>
    """
    return _send_email(receiver_email, subject, html)


def send_welcome_email(receiver_email: str) -> bool:
    """
    Sends a welcome email after successful registration.
    """
    subject = "Welcome to Fury AI!"
    html = """
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #4285f4; text-align: center;">You're All Set!</h2>
        <p>Hello,</p>
        <p>Your account has been successfully verified. Welcome to <strong>Fury AI</strong> — your personal AI voice assistant.</p>
        <p>You can now start chatting, exploring history, and using our voice processing features.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="#" style="background: #4285f4; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Get Started</a>
        </div>
        <p style="color: #666;">If you have any questions, feel free to reply to this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #999;">© 2026 Fayaz Ahmed Shaik. All rights reserved.</p>
    </div>
    """
    return _send_email(receiver_email, subject, html)
