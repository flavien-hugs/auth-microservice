import re
from datetime import datetime, UTC
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator, StrictStr
from slugify import slugify
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.shared.error_codes import UserErrorCode


class PhonenumberModel(BaseModel):
    phonenumber: Optional[str] = Field(default=None, examples=["+2250151571396"])

    @classmethod
    @field_validator("phonenumber", mode="before")
    def phonenumber_validation(cls, value):  # noqa: B902
        if value and not re.match(r"^\+?1?\d{9,15}$", value):
            raise ValueError("Invalid phone number")
        return value


class SignupBaseModel(PhonenumberModel):
    role: PydanticObjectId
    password: Optional[str] = None


class UserBaseSchema(SignupBaseModel):
    fullname: Optional[StrictStr] = Field(default=None, examples=["John Doe"])
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, examples=[{"key": "value"}])


class CreateUser(UserBaseSchema):
    email: Optional[EmailStr] = None

    @classmethod
    @field_validator("email", mode="before")
    def lowercase_email(cls, value) -> str:
        if value:
            return value.lower()
        return value

    @classmethod
    @field_validator("attributes", mode="before")
    def check_unique_attributes(cls, value: Dict[str, Any]) -> Dict[str, Any]:  # noqa: B902
        if not isinstance(value, dict):
            raise CustomHTTException(
                code_error=UserErrorCode.INVALID_ATTRIBUTES,
                message_error="Attributes must be a dictionary.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        seen_keys = set()

        for k, _ in value.items():
            slugified_key = slugify(k, separator="_")
            if slugified_key in seen_keys:
                raise CustomHTTException(
                    code_error=UserErrorCode.INVALID_ATTRIBUTES,
                    message_error=f"Duplicate key '{k}' ('{slugified_key}') in attributes.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            seen_keys.add(slugified_key)

        return value


class UpdateUser(BaseModel):
    role: Optional[PydanticObjectId] = Field(default=None, description="User role")
    fullname: Optional[StrictStr] = Field(default=None, examples=["John Doe"])
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, examples=[{"key": "value"}])

    @classmethod
    @field_validator("attributes", mode="before")
    def check_if_attributes_is_dict(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise CustomHTTException(
                code_error=UserErrorCode.INVALID_ATTRIBUTES,
                message_error="Attributes must be a dictionary.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return value

    @classmethod
    @field_validator("attributes", mode="before")
    def validate_attributes(cls, attrs: Dict[str, Any]) -> Dict[str, Any]:
        validated_attributes = {}
        for k, value in attrs.items():
            slugified_key = slugify(k, separator="_")
            validated_attributes[slugified_key] = value

        return validated_attributes


class Metadata(BaseModel):
    file_id: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    description: Optional[str] = None
    upload_date: Optional[datetime] = datetime.now(tz=UTC)
