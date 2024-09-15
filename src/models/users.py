from typing import Any, Dict, Optional

import pymongo
from beanie import Document
from pydantic import field_validator, StrictBool, ValidationError
from slugify import slugify

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

    @field_validator("attributes", mode="before")
    def validate_and_slugify_attributes(cls, value: Dict[str, Any]) -> Dict[str, Any]:  # noqa: B902
        if not isinstance(value, dict):
            raise ValidationError("The attributes must be a dictionary")

        existing_fields = set(cls.model_fields.keys())

        validated_attributes = {}

        for k, v in value.items():
            slugified_key = slugify(k, separator="_")
            if slugified_key in existing_fields:
                raise ValidationError(
                    f"The '{k}' key (slugified as '{slugified_key}') is already an existing User field."
                )

            if slugified_key in validated_attributes:
                raise ValidationError(
                    f"Key '{k}' (slugified as '{slugified_key}') conflicts with another attribute key"
                )

            validated_attributes[slugified_key] = v

        return validated_attributes


class UserOut(User):
    extras: Dict[str, Any] = {}
