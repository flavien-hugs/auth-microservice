from .send_email import email_sender_handler
from .send_sms import sms_sender_handler
from .utils import TokenBlacklistHandler

mail_service = email_sender_handler()
sms_service = sms_sender_handler()
blacklist_token = TokenBlacklistHandler()

__all__ = ["mail_service", "sms_service", "blacklist_token"]
