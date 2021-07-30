import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv


class Mail:
    def __init__(self):
        load_dotenv()
        self.email = os.getenv("MY_EMAIL")
        self.password = os.getenv("MY_PASSWORD")

    def send_mail(self, msg_data):
        msg = MIMEMultipart()

        msg['From'] = self.email
        msg['To'] = self.email
        msg['Subject'] = "New Contact Added."

        # MIME formatted message
        body = f"""
            <html>
                <body>
                    <h3>Name: {msg_data['name']}</h3>
                    <h3>Email: {msg_data['email']}</h3>
                    <h3>Phone: {msg_data['phone']}</h3>
                    <h3>Message: {msg_data['message']}</h3>
                </body>
            </html>
        """

        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP_SSL("smtp.gmail.com") as connection:
            try:
                print("trying to send email...")
                connection.login(user=self.email, password=self.password)
                connection.sendmail(
                    from_addr=self.email,
                    to_addrs=self.email,
                    msg=msg.as_string(),
                )

                print("Email sent")
            except smtplib.SMTPException as e:
                print("Error sending email:", str(e))

