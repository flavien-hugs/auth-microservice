from .send_email import email_sender_handler
from .send_sms import sms_sender_handler
from .utils import TokenBlacklistHandler, GenerateOPTKey
from .url_patterns import API_TRAILHUB_ENDPOINT, API_VERIFY_ACCESS_TOKEN_ENDPOINT

mail_service = email_sender_handler()
sms_service = sms_sender_handler()
blacklist_token = TokenBlacklistHandler()
otp_service = GenerateOPTKey()

__all__ = [
    "mail_service",
    "otp_service",
    "sms_service",
    "blacklist_token",
    "API_TRAILHUB_ENDPOINT",
    "API_VERIFY_ACCESS_TOKEN_ENDPOINT",
]
