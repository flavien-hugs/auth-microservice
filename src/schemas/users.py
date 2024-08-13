from typing import Any, Dict, Optional

import pymongo
from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator, StrictStr
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.shared.error_codes import AuthErrorCode


class UserBaseSchema(BaseModel):
    fullname: Optional[StrictStr] = Field(..., examples=["John Doe"])
    role: Optional[PydanticObjectId] = Field(..., description="User role")
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, examples=[{"key": "value"}])
    password: str = Field(default=None, examples=["p@55word"])

    @field_validator("password", mode="before")
    def validate_password_length(cls, value):  # noqa: B902
        if len(value) > settings.PASSWORD_MIN_LENGTH:
            return value
        raise CustomHTTException(
            code_error=AuthErrorCode.AUTH_PASSWORD_MISMATCH,
            message_error="The password must be 6 characters or more.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class CreateUser(UserBaseSchema):
    email: Indexed(EmailStr, pymongo.TEXT)

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
