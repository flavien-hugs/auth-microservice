from typing import Any, Mapping, Optional

from beanie import Document
from pydantic import Field, StrictBool

from src.config import settings
from src.schemas import CreateUser
from .mixins import DatetimeTimestamp


class User(CreateUser, DatetimeTimestamp, Document):
    is_active: StrictBool = True
    attributes: Optional[Mapping[str, Any]] = Field(default=None, description="User attributes", examples=[{"key": "value"}])

    class Settings:
        name = settings.USER_MODEL_NAME
