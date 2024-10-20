import re
from hmac import compare_digest
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, StrictBool
from pydantic.config import ConfigDict
from pydantic.json_schema import JsonSchemaMode
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.shared.error_codes import AuthErrorCode
from .users import PhonenumberModel, SignupBaseModel


class CheckEmailOrPhone:

    @model_validator(mode="before")
    @classmethod
    def check_email_or_phone(cls, values):
        if settings.REGISTER_WITH_EMAIL:
            if not values.get("email"):
                raise ValueError("The email address is required")
            values.pop("phonenumber", None)
        else:
            if not values.get("phonenumber"):
                raise ValueError("Phone number is required")
            values.pop("email", None)
        return values


class EmailModelMixin(BaseModel):
    email: Optional[EmailStr] = None


class RequestChangePassword(SignupBaseModel, EmailModelMixin, CheckEmailOrPhone):
    password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                (
                    {"email": "haf@example.com", "role": "5eb7cf5a86d9755df3a6c593"}
                    if settings.REGISTER_WITH_EMAIL
                    else {"password": "password", "phonenumber": "+2250151571396", "role": "5eb7cf5a86d9755df3a6c593"}
                )
            ]
        }
    )


class VerifyOTP(PhonenumberModel):
    otp_code: str


class LoginUser(BaseModel, CheckEmailOrPhone):
    email: Optional[str] = None
    phonenumber: Optional[str] = None
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                (
                    {"email": "haf@example.com", "password": "password"}
                    if settings.REGISTER_WITH_EMAIL
                    else {"phonenumber": "+2250151571396", "password": "password"}
                )
            ]
        }
    )

    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = "#/$defs/{model}",
        schema_generator: Any = None,
        mode: JsonSchemaMode = "validation",
    ) -> Dict:
        schema = super().model_json_schema(
            by_alias=by_alias, ref_template=ref_template, schema_generator=schema_generator, mode=mode
        )
        props = schema.get("properties", {})
        if settings.REGISTER_WITH_EMAIL:
            props.pop("phonenumber", None)
            schema["required"] = ["email", "password"]
        else:
            props.pop("email", None)
            schema["required"] = ["phonenumber", "password"]
        schema["properties"] = props
        return schema

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

    @model_validator(mode="before")
    @classmethod
    def check_email_or_phonenumber(cls, values):
        email, phonenumber = values.get("email"), values.get("phonenumber")
        if not email and not phonenumber:
            raise ValueError("Either email or phone number must be provided.")
        return values


class ManageAccount(BaseModel):
    is_active: StrictBool = True


class ChangePassword(BaseModel):
    current_password: str
    confirm_password: str

    @model_validator(mode="before")
    @classmethod
    def validate_new_password(cls, values: dict) -> dict:
        current_password = values.get("current_password")
        confirm_password = values.get("confirm_password")

        if (
            current_password is not None
            and confirm_password is not None
            and len(confirm_password) < settings.PASSWORD_MIN_LENGTH
            and compare_digest(current_password, confirm_password) is False
        ):
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_PASSWORD_MISMATCH,
                message_error="The two passwords did not match.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return values


class ChangePasswordWithOTPCode(ChangePassword):
    code_otp: str
    phonenumber: str

    @field_validator("phonenumber", mode="before")
    def phonenumber_validation(cls, value):  # noqa: B902
        if value and not re.match(r"^\+?1?\d{9,15}$", value):
            raise ValueError("Invalid phone number")
        return value
