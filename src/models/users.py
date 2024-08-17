from typing import Any, Dict

from beanie import Document
from pydantic import StrictBool, field_validator
from slugify import slugify

from src.config import settings
from src.schemas import CreateUser

from .mixins import DatetimeTimestamp


class User(CreateUser, DatetimeTimestamp, Document):
    is_active: StrictBool = True
    is_primary: StrictBool = False

    class Settings:
        name = settings.USER_MODEL_NAME

    @field_validator("attributes", mode="before")
    def slugify_attributes_keys(cls, value):  # noqa: B902
        if isinstance(value, dict):
            return {slugify(k, separator="_"): v for k, v in value.items()}
        return value


class UserOut(User):
    extras: Dict[str, Any] = {}
