from datetime import datetime, timedelta, timezone
from secrets import compare_digest

from fastapi import BackgroundTasks, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.common.helpers.exception import CustomHTTPException
from src.models import User
from src.schemas import (
    ChangePasswordWithOTPCode,
    PhonenumberModel,
    RequestChangePassword,
    VerifyOTP,
)
from src.services.shared import send_otp
from src.shared import otp_service
from src.shared.error_codes import AuthErrorCode, UserErrorCode
from src.shared.utils import password_hash
from src.services import roles


async def find_user_by_phonenumber(phonenumber: str):
    phone = f"+{phonenumber}" if not phonenumber.startswith("+") else phonenumber

    if (user := await User.find_one({"phonenumber": phone})) is None:
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with phone number {phone!r} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if not user.is_active:
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_ACCOUND_DESABLE,
            message_error=f"User account with phone number {phone!r} is disabled."
            f" Please request to activate the account.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user_dict = jsonable_encoder(
        {
            "fullname": user.fullname,
            "phonenumber": user.phonenumber,
            "avatar": user.attributes.get("avatar") if user.attributes.get("avatar") else None,
        }
    )
    return user_dict


async def request_password_reset_with_phonenumber(bg: BackgroundTasks, payload: PhonenumberModel):

    if payload.phonenumber and compare_digest(payload.phonenumber, " "):
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_PHONENUMBER_EMPTY,
            message_error="The phonenumber cannot be empty.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if (user := await User.find_one({"phonenumber": payload.phonenumber})) is None:
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with phone number '{payload.phonenumber}' not found",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    await send_otp(user, bg)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"We had sent a password reset code to the phone number: '{payload.phonenumber}'"},
    )


async def reset_password_completed_with_phonenumber(payload: ChangePasswordWithOTPCode) -> JSONResponse:
    if (user := await User.find_one({"phonenumber": payload.phonenumber})) is None:
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with phone number '{payload.phonenumber}' not found",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    otp_code_value = str(payload.code_otp)
    if not otp_service.generate_otp_instance(user.attributes["otp_secret"]).verify(otp=otp_code_value):
        raise CustomHTTPException(
            code_error=AuthErrorCode.AUTH_OTP_NOT_VALID,
            message_error=f"Code OTP '{otp_code_value}' invalid",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    password = password_hash(password=payload.confirm_password)
    await user.set({"password": password})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"message": "Your password has been successfully updated !"}),
    )


async def signup_with_phonenumber(bg: BackgroundTasks, payload: RequestChangePassword):
    STATUS_CODE_400 = status.HTTP_400_BAD_REQUEST

    await roles.get_one_role(role_id=payload.role)

    if payload.phonenumber and compare_digest(payload.phonenumber, " "):
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_PHONENUMBER_EMPTY,
            message_error="The phonenumber cannot be empty.",
            status_code=STATUS_CODE_400,
        )

    if payload.password and compare_digest(payload.password, " "):
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_PASSWORD_EMPTY,
            message_error="The password cannot be empty.",
            status_code=STATUS_CODE_400,
        )

    if user := await User.find_one({"phonenumber": payload.phonenumber}):
        if user.is_active:
            raise CustomHTTPException(
                code_error=UserErrorCode.USER_PHONENUMBER_TAKEN,
                message_error=f"This phone number '{payload.phonenumber}' is already taken.",
                status_code=STATUS_CODE_400,
            )
        else:
            raise CustomHTTPException(
                code_error=UserErrorCode.USER_ACCOUND_DESABLE,
                message_error=f"User account with phone number '{payload.phonenumber}' is disabled."
                f" Please request to activate the account.",
                status_code=STATUS_CODE_400,
            )

    user_data_dict = payload.model_copy(update={"password": password_hash(payload.password)})
    temp_user = User(**user_data_dict.model_dump(), attributes={})
    await temp_user.create()

    await send_otp(temp_user, bg)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"We had sent a connection code to the phone number: '{payload.phonenumber}'"},
    )


async def verify_otp(payload: VerifyOTP):
    if not (user := await User.find_one({"phonenumber": payload.phonenumber})):
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_PHONENUMBER_NOT_FOUND,
            message_error=f"User phonenumber '{payload.phonenumber}' not found",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if user.is_active:
        return JSONResponse(content={"message": "Account already activated"}, status_code=status.HTTP_200_OK)
    else:
        if otp_created_at := user.attributes.get("otp_created_at"):
            current_timestamp = datetime.now(timezone.utc).timestamp()
            time_elapsed = current_timestamp - otp_created_at
            if time_elapsed > timedelta(minutes=5).total_seconds():
                raise CustomHTTPException(
                    code_error=AuthErrorCode.AUTH_OTP_EXPIRED,
                    message_error="OTP has expired. Please request a new one.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        if not otp_service.generate_otp_instance(user.attributes["otp_secret"]).verify(int(payload.otp_code)):
            raise CustomHTTPException(
                code_error=AuthErrorCode.AUTH_OTP_NOT_VALID,
                message_error=f"Code OTP '{int(payload.otp_code)}' invalid",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        await user.set({"is_active": True})

        response_data = {"message": "Your count has been successfully verified !"}

        return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)


async def resend_otp(bg: BackgroundTasks, payload: PhonenumberModel):
    if (user := await User.find_one({"phonenumber": payload.phonenumber})) is None:
        raise CustomHTTPException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with phone number '{payload.phonenumber}' not found",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if user.is_active:
        return JSONResponse(content={"message": "Account already activated"}, status_code=status.HTTP_200_OK)
    else:
        await send_otp(user, bg)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"We have sent a new connection code to the phone number: {payload.phonenumber}"},
        )
