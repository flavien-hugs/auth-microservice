import re
from typing import Any, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator, StrictStr
from slugify import slugify
from starlette import status

from src.common.helpers.exception import CustomHTTPException
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
    role: PydanticObjectId = Field(..., description="User role")
    password: Optional[str] = Field(default=None, examples=["password"])


class UserBaseSchema(SignupBaseModel):
    fullname: Optional[StrictStr] = Field(default=None, examples=["John Doe"])
    attributes: Optional[dict[str, Any]] = Field(default_factory=dict, examples=[{"key": "value"}])


class CreateUser(UserBaseSchema):
    email: Optional[EmailStr] = Field(default=None, examples=["user@exemple.com"])

    @classmethod
    @field_validator("email", mode="before")
    def lowercase_email(cls, value) -> str:
        if value:
            return value.lower()
        return value

    @classmethod
    @field_validator("attributes", mode="before")
    def check_unique_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:  # noqa: B902
        if not isinstance(value, dict):
            raise CustomHTTPException(
                code_error=UserErrorCode.INVALID_ATTRIBUTES,
                message_error="Attributes must be a dictionary.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        seen_keys = set()

        for k, _ in value.items():
            slugified_key = slugify(k, separator="_")
            if slugified_key in seen_keys:
                raise CustomHTTPException(
                    code_error=UserErrorCode.INVALID_ATTRIBUTES,
                    message_error=f"Duplicate key '{k}' ('{slugified_key}') in attributes.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            seen_keys.add(slugified_key)

        return value


class UpdateUser(BaseModel):
    role: Optional[PydanticObjectId] = Field(default=None, description="User role")
    fullname: Optional[StrictStr] = Field(default=None, examples=["John Doe"])
    attributes: Optional[dict[str, Any]] = Field(default_factory=dict, examples=[{"key": "value"}])

    @classmethod
    @field_validator("attributes", mode="before")
    def check_if_attributes_is_dict(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise CustomHTTPException(
                code_error=UserErrorCode.INVALID_ATTRIBUTES,
                message_error="Attributes must be a dictionary.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return value

    @classmethod
    @field_validator("attributes", mode="before")
    def validate_attributes(cls, attrs: dict[str, Any]) -> dict[str, Any]:
        validated_attributes = {}
        for k, value in attrs.items():
            slugified_key = slugify(k, separator="_")
            validated_attributes[slugified_key] = value

        return validated_attributes
