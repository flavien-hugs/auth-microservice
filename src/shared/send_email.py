import logging
import smtplib
from email.mime.text import MIMEText

from pydantic import EmailStr, PositiveInt

logger = logging.getLogger(__name__)


class EmailSenderHandler:
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
    email_sender = EmailSender(
        email_address=email_env.EMAIL_SENDER_ADDRESS,
        email_password=email_env.EMAIL_PASSWORD,
        smtp_server=email_env.SMTP_SERVER,
        smtp_port=email_env.SMTP_PORT,
    )

    await email_sender.send_email(
        receiver_email="receiver@example.com",
        subject="Sujet de l'email",
        body="<h1>Contenu de l'email</h1>",
        from_to=no-reply@example.com
    )

    Sends an email to the specified receiver.
    """

    def __init__(self, email_address: EmailStr, email_password: str, smtp_server: str, smtp_port: PositiveInt):
        self.email_address = email_address
        self.email_password = email_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    async def send_email(self, receiver_email: EmailStr, subject: str, body: str, from_to: str):
        message = MIMEText(_text=body, _subtype="html")
        message["Subject"] = subject
        message["From"] = from_to
        message["To"] = receiver_email

        try:
            with smtplib.SMTP(host=self.smtp_server, port=self.smtp_port) as server:
                server.starttls()
                server.login(user=self.email_address, password=self.email_password)
                server.sendmail(from_addr=self.email_address, to_addrs=[receiver_email], msg=message.as_string())
            logger.debug("Email sent successfully.")
        except Exception as exc:
            logger.debug("Email sent failed." + str(exc))
            raise
