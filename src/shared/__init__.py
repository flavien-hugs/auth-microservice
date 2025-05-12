from .error_codes import *  # noqa: F401, F403
from .exceptions import *  # noqa: F401, F403
from .send_email import email_sender_handler
from .send_sms import sms_sender_handler
from .url_patterns import API_TRAILHUB_ENDPOINT, API_VERIFY_ACCESS_TOKEN_ENDPOINT
from .utils import *  # noqa: F401, F403

mail_service = email_sender_handler()
sms_service = sms_sender_handler()

__all__ = [
    "mail_service",
    "sms_service",
    "API_TRAILHUB_ENDPOINT",
    "API_VERIFY_ACCESS_TOKEN_ENDPOINT",
]
