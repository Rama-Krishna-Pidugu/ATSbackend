import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class EmailSender:
    def send_email(self, from_email: str, to_email: str, subject: str, body: str):
        print(f"Attempting to send email from {from_email} to {to_email}")
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            smtp_password = os.getenv('SMTP_PASSWORD')
            if not smtp_password:
                print("SMTP_PASSWORD not set")
                return False
            server.login(from_email, smtp_password)  # Use app password
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            server.quit()
            print("Email sent successfully")
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
