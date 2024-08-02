from hmac import compare_digest

from pydantic import BaseModel, EmailStr, model_validator, StrictBool
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.shared.error_codes import AuthErrorCode


class RequestChangePassword(BaseModel):
    email: EmailStr


class LoginUser(RequestChangePassword):
    password: str

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
            and compare_digest(current_password, confirm_password) is False
        ):
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_PASSWORD_MISMATCH,
                message_error="The two passwords did not match.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return values
