from hmac import compare_digest

from pydantic import BaseModel, EmailStr, Field, model_validator, StrictBool
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.shared.error_codes import AuthErrorCode


class RequestChangePassword(BaseModel):
    email: EmailStr


class LoginUser(RequestChangePassword):
    password: str = Field(..., pattern=settings.PASSWORD_REGEX)


class ManageAccount(BaseModel):
    is_active: StrictBool = True


class ChangePassword(BaseModel):
    current_password: str = Field(..., pattern=settings.PASSWORD_REGEX)
    confirm_password: str = Field(..., pattern=settings.PASSWORD_REGEX)

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
