from .send_email import get_mail_service  # noqa: F401
from .utils import TokenBlacklistHandler

mail_service = get_mail_service()
blacklist_token = TokenBlacklistHandler()

__all__ = ["mail_service", "blacklist_token"]
