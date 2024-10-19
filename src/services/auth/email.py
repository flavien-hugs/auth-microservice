from datetime import timedelta
from urllib.parse import urljoin

from fastapi import BackgroundTasks, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import EmailStr

from src.common.helpers.exceptions import CustomHTTException
from src.config import email_settings, settings
from src.middleware.auth import CustomAccessBearer
from src.models import User
from src.schemas import (
    ChangePassword,
    UserBaseSchema,
)
from src.shared import mail_service
from src.shared.error_codes import UserErrorCode
from src.shared.utils import password_hash
from src.services.users import check_if_email_exist

template_loader = PackageLoader("src", "templates")
template_env = Environment(loader=template_loader, autoescape=select_autoescape(["html", "txt"]))


async def request_password_reset_with_email(bg: BackgroundTasks, email: EmailStr) -> JSONResponse:
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

    base_url = urljoin(settings.FRONTEND_URL, settings.FRONTEND_PATH_RESET_PASSWORD)
    reset_password_link = base_url + str(reset_token)

    template = template_env.get_template(name="reset_password.html")
    rendered_html = template.render(
        service_name=email_settings.SMTP_APP_NAME,
        reset_password_link=reset_password_link,
        link_validity=email_settings.RESET_PASSWORD_LIFESPAN_MINUTE,
    )

    mail_service.send_email_background(
        bg=bg,
        recipients=user.email.lower(),
        subject=f"{email_settings.SMTP_APP_NAME}: Reset your password",
        body=rendered_html,
    )

    response_data = {"message": f"We've just sent you an e-mail to '{email}' with a link to reset your password."}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(response_data),
    )


async def reset_password_completed_with_email(bg: BackgroundTasks, token: str, payload: ChangePassword) -> JSONResponse:
    await CustomAccessBearer.verify_access_token(token=token)
    decode_token = CustomAccessBearer.decode_access_token(token=token)

    check_user_email = decode_token.get("subject", {}).get("email")
    if (user := await User.find_one({"email": check_user_email})) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with email '{check_user_email}' not found",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    password = password_hash(password=payload.confirm_password)
    await user.set({"password": password})

    login_link = settings.FRONTEND_URL + settings.FRONTEND_PATH_LOGIN
    template = template_env.get_template(name="reset_password_completed_with_email.html")
    rendered_html = template.render(login_link=login_link, service_name=email_settings.SMTP_APP_NAME)

    mail_service.send_email_background(
        bg=bg,
        recipients=user.email.lower(),
        subject=f"{email_settings.SMTP_APP_NAME}: Password reset completed",
        body=rendered_html,
    )

    response_data = {"message": "Your password has been successfully updated !"}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(response_data),
    )


async def signup_with_email(bg: BackgroundTasks, email: EmailStr):
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
        bg=bg,
        recipients=email.lower(),
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


async def completed_register_with_email(token: str, payload: UserBaseSchema, bg: BackgroundTasks) -> User:
    await CustomAccessBearer.verify_access_token(token=token)
    decode_token = CustomAccessBearer.decode_access_token(token=token)

    addr_email = decode_token.get("subject", {}).get("email")

    user_data_dict = payload.model_copy(update={"password": password_hash(payload.password)})
    new_user = await User(**user_data_dict.model_dump(), email=addr_email).create()

    template = template_env.get_template(name="create_account_success.html")
    rendered_html = template.render(service_name=email_settings.SMTP_APP_NAME, login_link=settings.FRONTEND_PATH_LOGIN)

    mail_service.send_email_background(
        bg=bg, recipients=addr_email.lower(), subject=f"{email_settings.SMTP_APP_NAME}: You welcome", body=rendered_html
    )

    return new_user
