from .database import shutdown_db, startup_db  # noqa: F401
from .email import get_email_settings  # noqa: F401
from .settings import get_settings  # noqa: F401
from .swaggers import enable_endpoint  # noqa: F401
from .token import get_token_settings  # noqa: F401

settings = get_settings()
jwt_settings = get_token_settings()
email_settings = get_email_settings()
enable_endpoint = enable_endpoint()

__all__ = ["settings", "startup_db", "shutdown_db", "email_settings", "jwt_settings", "enable_endpoint"]
