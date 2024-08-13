import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pydantic import EmailStr, PositiveInt
from starlette.background import BackgroundTasks

from src.config import email_settings as env_email

logger = logging.getLogger(__name__)


class MailServiceHandler:
    """
    A class to handle the sending of emails using SMTP.

    Attributes:
    ----------
    email_address : EmailStr
        The email address to send from.
    email_password : str
        The password for the email account.
    smtp_server : str
        The SMTP server to connect to.
    smtp_port : PositiveInt
        The port to use for the SMTP server.

    Methods:
    -------
    async def send_email(receiver_email: EmailStr, subject: str, body: str):
        Sends an email to the specified receiver.

    def send_email_background(background_tasks: BackgroundTasks, receiver_email: EmailStr, subject: str, body: str):
        Schedules sending an email as a background task.

    Sends an email to the specified receiver.
    """

    def __init__(self, email_address: EmailStr, email_password: str, smtp_server: str, smtp_port: PositiveInt):
        self.email_address = email_address
        self.email_password = email_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    async def send_email(self, receiver_email: list[EmailStr], subject: str, body: str):
        message = MIMEMultipart()

        message["From"] = env_email.EMAIL_FROM_TO
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(_text=body, _subtype="html"))

        try:
            with smtplib.SMTP(host=self.smtp_server, port=self.smtp_port) as server:
                server.starttls()
                server.login(user=self.email_address, password=self.email_password)
                server.sendmail(from_addr=self.email_address, to_addrs=receiver_email, msg=message.as_string())
                server.quit()
            logger.debug("--> Email sent successfully.")
        except Exception as exc:
            logger.debug("--> Email sent failed." + str(exc))
            raise

    def send_email_background(
        self, background_tasks: BackgroundTasks, receiver_email: list[EmailStr], subject: str, body: str
    ):
        background_tasks.add_task(self.send_email, receiver_email, subject, body)
        logger.info("Email scheduled to be sent in the background.")


def email_sender_handler() -> MailServiceHandler:
    return MailServiceHandler(
        email_address=env_email.EMAIL_SENDER_ADDRESS,
        email_password=env_email.EMAIL_PASSWORD,
        smtp_server=env_email.SMTP_SERVER,
        smtp_port=env_email.SMTP_PORT,
    )
