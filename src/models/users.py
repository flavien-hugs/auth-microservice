from typing import Any, Dict, Optional

import pymongo
from beanie import Document

from src.config import settings
from src.schemas import CreateUser
from .mixins import DatetimeTimestamp


class User(CreateUser, DatetimeTimestamp, Document):
    is_active: Optional[bool] = False
    is_primary: Optional[bool] = False

    class Settings:
        name = settings.USER_MODEL_NAME
        use_state_management = True
        indexes = [pymongo.IndexModel(keys=[("fullname", pymongo.TEXT)])]


class UserOut(User):
    extras: Dict[str, Any] = {}
