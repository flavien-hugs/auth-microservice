from .send_email import get_mail_service  # noqa: F401

mail_service = get_mail_service()

__all__ = [mail_service]
