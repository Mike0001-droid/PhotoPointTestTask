import smtplib
from .base import BaseProvider
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailProvider(BaseProvider):
    async def send(self, to: str, subject: str, message: str, **kwargs):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.get('from_email', 'noreply@example.com')
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_username'], self.config['smtp_password'])
                server.send_message(msg)
            return True, None
        except Exception as e:
            return False, f"Email error: {e}"