from datetime import datetime
from typing import Any, Dict, Optional

from beanie import Document
from pydantic import Field, StrictBool

from src.config import settings
from src.schemas import CreateUser


class User(Document, CreateUser):
    is_active: StrictBool = True
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="User attributes")
    created_at: datetime = Field(default=datetime.now().timestamp(), description="Date user created")

    class Settings:
        name = settings.USER_MODEL_NAME
