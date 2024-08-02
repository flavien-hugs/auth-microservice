from datetime import datetime
from typing import Any, Mapping, Optional

from beanie import Document
from pydantic import Field, StrictBool

from src.config import settings
from src.schemas import CreateUser


class User(CreateUser, Document):
    is_active: StrictBool = True
    attributes: Optional[Mapping[str, Any]] = Field(default=None, description="User attributes", examples=[{"key": "value"}])
    created_at: datetime = Field(default=datetime.now(), description="Date user created")

    class Settings:
        name = settings.USER_MODEL_NAME
