from .database import shutdown_db, startup_db
from .settings import get_settings

settings = get_settings()

__all__ = ["settings", "startup_db", "shutdown_db"]
