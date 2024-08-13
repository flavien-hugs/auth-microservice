from .send_email import email_sender_handler  # noqa: F401
from .utils import TokenBlacklistHandler

mail_service = email_sender_handler()
blacklist_token = TokenBlacklistHandler()

__all__ = ["mail_service", "blacklist_token"]
