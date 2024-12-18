from typing import Any, Dict, Optional

import pymongo
from beanie import Document
from pydantic import Field

from src.config import settings
from src.schemas import CreateUser
from .mixins import DatetimeTimestamp


class User(CreateUser, DatetimeTimestamp, Document):
    is_active: Optional[bool] = Field(False, description="User is active")
    is_primary: Optional[bool] = Field(False, description="User is primary")

    class Settings:
        name = settings.USER_MODEL_NAME
        use_state_management = True
        indexes = [pymongo.IndexModel(keys=[("fullname", pymongo.TEXT)])]


class UserOut(User):
    extras: Dict[str, Any] = {}
