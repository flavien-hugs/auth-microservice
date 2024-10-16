from datetime import datetime, timedelta, timezone
from secrets import compare_digest
from typing import Optional

from beanie import PydanticObjectId
from fastapi import BackgroundTasks, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import EmailStr

from src.common.helpers.exceptions import CustomHTTException
from src.config import email_settings, settings, sms_config
from src.middleware.auth import CustomAccessBearer
from src.models import User
from src.schemas import ChangePassword, LoginUser, PhonenumberModel, RequestChangePassword, UserBaseSchema, VerifyOTP
from src.shared import blacklist_token, mail_service, otp_service, sms_service
from src.shared.error_codes import AuthErrorCode, UserErrorCode
from src.shared.utils import password_hash, verify_password
from .roles import get_one_role
from .tracker import tracking
from .users import check_if_email_exist, get_one_user

template_loader = PackageLoader("src", "templates")
template_env = Environment(loader=template_loader, autoescape=select_autoescape(["html", "txt"]))


async def find_user_by_identifier(identifier: str, is_email: bool) -> Optional[User]:
    search_field = "email" if is_email else "phonenumber"
    return await User.find_one({search_field: identifier})


async def validate_user_status(user: User) -> None:
    if user is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error="User does not exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not user.is_active:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error="Your account is not active. Please contact the administrator to activate your account.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


async def login(task: BackgroundTasks, request: Request, payload: LoginUser) -> JSONResponse:
    is_email = settings.REGISTER_WITH_EMAIL
    identifier: Optional[str] = payload.email if is_email else payload.phonenumber

    if not identifier:
        field = "email" if is_email else "phone number"
        raise CustomHTTException(
            code_error=AuthErrorCode.AUTH_INVALID_CREDENTIALS,
            message_error=f"{field.capitalize()} is required for login.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = await find_user_by_identifier(identifier, is_email)
    await validate_user_status(user)

    if not verify_password(payload.password, user.password):
        raise CustomHTTException(
            code_error=AuthErrorCode.AUTH_INVALID_PASSWORD,
            message_error="Your password is invalid.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    role = await get_one_role(role_id=PydanticObjectId(user.role))
    user_data = user.model_dump(by_alias=True, mode="json", exclude={"password", "attributes", "is_primary"})

    response_data = {
        "access_token": CustomAccessBearer.access_token(data=jsonable_encoder(user_data), user_id=str(user.id)),
        "referesh_token": CustomAccessBearer.refresh_token(data=jsonable_encoder(user_data), user_id=str(user.id)),
        "user": user_data,
    }

    response_data["user"]["role"] = role.model_dump(
        by_alias=True, mode="json", exclude={"permissions", "created_at", "updated_at"}
    )

    await tracking.insert_log(task=task, request=request, user_id=user.id)

    return JSONResponse(content=jsonable_encoder(response_data), status_code=status.HTTP_200_OK)


async def logout(request: Request) -> JSONResponse:
    authorization = request.headers.get("Authorization")
    token = authorization.split()[1]
    await blacklist_token.add_blacklist_token(token)
    return JSONResponse(content={"message": "Logout successfully !"}, status_code=status.HTTP_200_OK)


async def change_password(user_id: PydanticObjectId, change_password: ChangePassword):
    user = await get_one_user(user_id=user_id)

    password = password_hash(password=change_password.confirm_password)
    await user.set({"password": password_hash(password=password)})

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"message": "Your password has been successfully updated !"}),
    )


async def check_access(token: str, permission: set[str]):
    access = await CustomAccessBearer.check_permissions(token=token, required_permissions=permission)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"access": access}))


async def validate_access_token(token: str):
    """
    Validates the access token by checking its validity and user info from cache or by decoding it.

    :param token: The access token to validate.
    :type token: str
    :return: JSONResponse containing the token validity and user information.
    :rtype: JSONResponse
    """

    decode_token = CustomAccessBearer.decode_access_token(token=token)
    current_timestamp = datetime.now(timezone.utc).timestamp()
    is_token_active = decode_token.get("exp", 0) > current_timestamp
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"active": bool(is_token_active), "user_info": decode_token.get("subject", {})}),
    )


async def request_password_reset(background: BackgroundTasks, email: EmailStr) -> JSONResponse:
    if (user := await User.find_one({"email": email})) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with email '{email}' not found",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    reset_token = CustomAccessBearer.access_token(
        data={"email": email},
        user_id=str(user.id),
        expires_delta=timedelta(minutes=email_settings.RESET_PASSWORD_LIFESPAN_MINUTE),
    )
    reset_password_link = settings.FRONTEND_URL + settings.FRONTEND_PATH_RESET_PASSWORD + str(reset_token)

    template = template_env.get_template(name="reset_password.html")
    rendered_html = template.render(
        service_name=email_settings.SMTP_APP_NAME,
        reset_password_link=reset_password_link,
        link_validity=email_settings.RESET_PASSWORD_LIFESPAN_MINUTE,
    )

    mail_service.send_email_background(
        background_task=background,
        receiver_email=user.email.lower(),
        subject=f"{email_settings.SMTP_APP_NAME}: Reset your password",
        body=rendered_html,
    )

    response_data = {"message": f"We've just sent you an e-mail to '{email}' with a link to reset your password."}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(response_data),
    )


async def reset_password_completed(
    background: BackgroundTasks, reset_passwoord_token: str, new_password: ChangePassword
) -> JSONResponse:
    await CustomAccessBearer.verify_access_token(token=reset_passwoord_token)
    decode_token = CustomAccessBearer.decode_access_token(token=reset_passwoord_token)

    check_user_email = decode_token.get("subject", {}).get("email")
    if (user := await User.find_one({"email": check_user_email})) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with email '{check_user_email}' not found",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    password = password_hash(password=new_password.confirm_password)
    await user.set({"password": password_hash(password=password)})

    login_link = settings.FRONTEND_URL + settings.FRONTEND_PATH_LOGIN
    template = template_env.get_template(name="reset_password_completed.html")
    rendered_html = template.render(login_link=login_link, service_name=email_settings.SMTP_APP_NAME)

    mail_service.send_email_background(
        background_task=background,
        receiver_email=user.email.lower(),
        subject=f"{email_settings.SMTP_APP_NAME}: Password reset completed",
        body=rendered_html,
    )

    response_data = {"message": "Your password has been successfully updated !"}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(response_data),
    )


async def signup_with_email(background: BackgroundTasks, email: EmailStr):
    await check_if_email_exist(email=email.lower())

    activate_token = CustomAccessBearer.access_token(
        data={"email": email},
        user_id=str(email),
        expires_delta=timedelta(minutes=email_settings.ACTIVATE_LINK_IFESPAN_MINUTE),
    )
    activate_link = settings.FRONTEND_URL + settings.FRONTEND_PATH_ACTIVATE_ACCOUNT + str(activate_token)

    template = template_env.get_template(name="confirm_account.html")
    rendered_html = template.render(
        link_validity=email_settings.ACTIVATE_LINK_IFESPAN_MINUTE,
        service_name=email_settings.SMTP_APP_NAME,
        activate_link=activate_link,
    )

    mail_service.send_email_background(
        background_task=background,
        receiver_email=email.lower(),
        subject=f"{email_settings.SMTP_APP_NAME}: Please confirm your e-mail address to activate your account",
        body=rendered_html,
    )

    response_data = {
        "message": f"A link confirming your account has been sent to the email address you provided: '{email}'."
    }

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(response_data),
    )


async def complete_registration_with_email(
    token: str,
    user_data: UserBaseSchema,
    background: BackgroundTasks,
) -> User:
    await CustomAccessBearer.verify_access_token(token=token)
    decode_token = CustomAccessBearer.decode_access_token(token=token)

    addr_email = decode_token.get("subject", {}).get("email")

    user_data_dict = user_data.model_copy(update={"password": password_hash(user_data.password)})
    new_user = await User(**user_data_dict.model_dump(), email=addr_email).create()

    template = template_env.get_template(name="create_account_success.html")
    rendered_html = template.render(service_name=email_settings.SMTP_APP_NAME, login_link=settings.FRONTEND_PATH_LOGIN)

    mail_service.send_email_background(
        background_task=background,
        receiver_email=addr_email.lower(),
        subject=f"{email_settings.SMTP_APP_NAME}: You welcome",
        body=rendered_html,
    )

    return new_user


async def check_user_attribute(key: str, value: str, in_attributes: Optional[bool] = False) -> JSONResponse:
    query = {f"attributes.{key}": value} if in_attributes else {key: value}
    can = await User.find_one(query).exists()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"exists": can})


async def send_otp(user: User, background: BackgroundTasks):
    otp_secret = otp_service.generate_key()
    otp_code = otp_service.generate_otp_instance(otp_secret).now()
    recipient = user.phonenumber.replace("+", "")

    new_attributes = user.attributes.copy() if user.attributes else {}
    new_attributes["otp_secret"] = otp_secret
    new_attributes["otp_created_at"] = datetime.now(timezone.utc).timestamp()

    template = template_env.get_template(name="sms_send_otp.txt")
    message = template.render(otp_code=otp_code, service_name=sms_config.SMS_SENDER)
    await sms_service.send_sms(background, recipient, message)
    await user.set({"attributes": new_attributes})


async def signup_with_phonenumber(background: BackgroundTasks, payload: RequestChangePassword):

    if payload.password and compare_digest(payload.password, " "):
        raise CustomHTTException(
            code_error=UserErrorCode.USER_PASSWORD_EMPTY,
            message_error="The password cannot be empty.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if await User.find_one({"phonenumber": payload.phonenumber}).exists():
        raise CustomHTTException(
            code_error=UserErrorCode.USER_PHONENUMBER_TAKEN,
            message_error=f"This phone number '{payload.phonenumber}' is already taken.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user_data_dict = payload.model_copy(update={"password": password_hash(payload.password)})
    temp_user = User(**user_data_dict.model_dump(), attributes={})
    await temp_user.create()

    try:
        await send_otp(temp_user, background)
    except HTTPException as exc:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_CREATE_FAILED,
            message_error="Failed to send SMS OTP. Please try again.",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"We had sent a connection code to the phone number: '{payload.phonenumber}'"},
    )


async def verify_otp(payload: VerifyOTP):
    if not (user := await User.find_one({"phonenumber": payload.phonenumber})):
        raise CustomHTTException(
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
                raise CustomHTTException(
                    code_error=AuthErrorCode.AUTH_OTP_EXPIRED,
                    message_error="OTP has expired. Please request a new one.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        if not otp_service.generate_otp_instance(user.attributes["otp_secret"]).verify(int(payload.otp_code)):
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_OTP_NOT_VALID,
                message_error=f"Code OTP '{int(payload.otp_code)}' invalid",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        await user.set({"is_active": True})

        response_data = {"message": "Your count has been successfully verified !"}

        return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)


async def resend_otp(background: BackgroundTasks, payload: PhonenumberModel):
    if (user := await User.find_one({"phonenumber": payload.phonenumber})) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with phone number '{payload.phonenumber}' not found",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if user.is_active:
        return JSONResponse(content={"message": "Account already activated"}, status_code=status.HTTP_200_OK)
    else:
        await send_otp(user, background)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"We have sent a new connection code to the phone number: {payload.phonenumber}"},
        )
