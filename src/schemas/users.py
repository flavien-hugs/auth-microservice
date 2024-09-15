import re
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, EmailStr, Field, StrictStr, field_validator, model_validator
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.shared.error_codes import AuthErrorCode


class PhonenumberModel(BaseModel):
    phonenumber: Optional[str] = Field(default=None, examples=["+2250151571396"])

    @field_validator("phonenumber", mode="before")
    def phonenumber_validation(cls, value):  # noqa: B902
        if value and not re.match(r"^\+?1?\d{9,15}$", value):
            raise ValueError("Invalid phone number")
        return value


class SignupBaseModel(PhonenumberModel):
    password: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_password(cls, values: dict):
        password = values.get("password")
        if len(password) > settings.PASSWORD_MIN_LENGTH:
            return values
        raise CustomHTTException(
            code_error=AuthErrorCode.AUTH_PASSWORD_MISMATCH,
            message_error="The password must be 6 characters or more.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class UserBaseSchema(SignupBaseModel):
    fullname: Optional[StrictStr] = Field(default=None, examples=["John Doe"])
    role: Optional[PydanticObjectId] = Field(default=None, description="User role")
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, examples=[{"key": "value"}])


class CreateUser(UserBaseSchema):
    email: Optional[EmailStr] = None

    @classmethod
    @field_validator("email", mode="after")
    def lowercase_email(cls, value) -> str:
        if value:
            return value.lower()
        return value


class UpdateUser(BaseModel):
    role: Optional[PydanticObjectId] = Field(default=None, description="User role")
    fullname: Optional[StrictStr] = Field(default=None, examples=["John Doe"])
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, examples=[{"key": "value"}])
