"""
Email service for sending notifications and account credentials.
"""
import os
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from typing import Optional


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        
    async def send_staff_credentials_email(self, to_email: str, password: str, staff_name: Optional[str] = None):
        """
        Send staffs account credentials via email.
        
        Args:
            to_email: Staff member's email address
            password: Auto-generated password
            staff_name: Optional staffs member name
        """
        subject = "Your Staff Account Credentials"
        
        # Email template
        email_template = Template("""
        <html>
        <body>
            <h2>Welcome to Our Store Management System!</h2>
            
            {% if staff_name %}
            <p>Hello {{ staff_name }},</p>
            {% else %}
            <p>Hello,</p>
            {% endif %}
            
            <p>Your staffs account has been created successfully. Here are your login credentials:</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Email:</strong> {{ email }}</p>
                <p><strong>Password:</strong> {{ password }}</p>
            </div>
            
            <p><strong>Important:</strong> Please change your password after your first login for security purposes.</p>
            
            <p>You can now access the store management system using these credentials.</p>
            
            <p>If you have any questions, please contact your store administrator.</p>
            
            <p>Best regards,<br>Store Management Team</p>
        </body>
        </html>
        """)
        
        html_content = email_template.render(
            email=to_email,
            password=password,
            staff_name=staff_name
        )
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = to_email
        
        # Add HTML part
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Send email
        try:
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_username,
                password=self.smtp_password,
            )
            return True
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            raise Exception(f"Failed to send credentials email: {str(e)}")


# Global email service instance
email_service = EmailService()
