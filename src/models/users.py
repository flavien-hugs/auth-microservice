from typing import Any, Dict, Optional

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import StrictBool

from src.config import settings
from src.schemas import CreateUser
from .mixins import DatetimeTimestamp


class User(CreateUser, DatetimeTimestamp, Document):
    is_active: Optional[StrictBool] = False
    is_primary: Optional[StrictBool] = False

    class Settings:
        name = settings.USER_MODEL_NAME
        use_state_management = True
        indexes = [pymongo.IndexModel(keys=[("fullname", pymongo.TEXT)])]


class LoginLog(DatetimeTimestamp, Document):
    user_id: PydanticObjectId
    ip_address: str
    device: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    is_tablet: Optional[bool] = False
    is_mobile: Optional[bool] = False
    is_pc: Optional[bool] = False
    is_bot: Optional[bool] = False
    is_touch_capable: Optional[bool] = False
    is_email_client: Optional[bool] = False

    class Settings:
        name = settings.LOGIN_LOG_MODEL_NAME
        use_state_management = True


class UserOut(User):
    extras: Dict[str, Any] = {}
