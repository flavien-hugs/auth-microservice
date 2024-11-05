from typing import Any, Dict, Optional

import pymongo
from starlette import status
from beanie import Document, PydanticObjectId
from pydantic import field_validator, StrictBool
from slugify import slugify

from src.config import settings
from src.schemas import CreateUser
from .mixins import DatetimeTimestamp
from src.common.helpers.exceptions import CustomHTTException
from src.shared.error_codes import UserErrorCode


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
            raise CustomHTTException(
                code_error=UserErrorCode.INVALID_ATTRIBUTES,
                message_error="Attributes must be a dictionary.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        existing_fields = set(cls.model_fields.keys())

        validated_attributes = {}

        for k, v in value.items():
            slugified_key = slugify(k, separator="_")
            if slugified_key in existing_fields:
                raise CustomHTTException(
                    code_error=UserErrorCode.INVALID_ATTRIBUTES,
                    message_error=f"The '{k}' key ('{slugified_key}') is already an existing User field.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            if slugified_key in validated_attributes:
                raise CustomHTTException(
                    code_error=UserErrorCode.INVALID_ATTRIBUTES,
                    message_error=f"Key '{k}' ('{slugified_key}') conflicts with another attribute key",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            validated_attributes[slugified_key] = v

        return validated_attributes


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
