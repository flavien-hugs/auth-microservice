from typing import Any, Mapping, Optional

import pymongo
from beanie import Indexed
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, StrictStr
from slugify import slugify
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.shared.error_codes import AuthErrorCode


class CreateUser(BaseModel):
    email: Indexed(EmailStr, pymongo.TEXT, unique=True)
    fullname: Optional[StrictStr] = Field(..., examples=["John Doe"])
    role: Optional[str] = Field(..., description="User role")
    password: str = Field(default=None, examples=["p@55word"])

    @classmethod
    @field_validator("email", mode="after")
    def lowercase_email(cls, value) -> str:
        if value:
            return value.lower()
        return value

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


class UpdateUser(BaseModel):
    fullname: Optional[StrictStr] = Field(default=None, examples=["John Doe"])
    role: Optional[str] = Field(default=None, description="User role")
    attributes: Optional[Mapping[str, Any]] = Field(default=None, examples=[{"key": "value"}])

    @field_validator("attributes", mode="before")
    def slugify_keys(cls, value):  # noqa: B902
        if value is None:
            return value
        return {slugify(k, separator="_"): v for k, v in value.items()}
