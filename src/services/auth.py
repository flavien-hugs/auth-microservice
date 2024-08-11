from datetime import datetime, timedelta, timezone

from beanie import PydanticObjectId
from fastapi import BackgroundTasks, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import EmailStr

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.middleware.auth import CustomAccessBearer
from src.models import User
from src.schemas import ChangePassword, LoginUser
from src.shared import mail_service, blacklist_token
from src.shared.error_codes import AuthErrorCode, UserErrorCode
from src.shared.utils import password_hash, verify_password
from .roles import get_one_role
from .users import get_one_user

template_loader = PackageLoader("src", "templates")
template_env = Environment(loader=template_loader, autoescape=select_autoescape(["html", "xml"]))


async def login(payload: LoginUser) -> JSONResponse:
    if (user := await User.find_one({"email": payload.email.lower()})) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"This e-mail address '{payload.email}' is invalid or does not exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not user.is_active:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error="Your account is not active. Please contact the administrator to activate your account.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if not verify_password(payload.password, user.password):
        raise CustomHTTException(
            code_error=AuthErrorCode.AUTH_INVALID_PASSWORD,
            message_error="Your password is invalid.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    role = await get_one_role(role_id=PydanticObjectId(user.role))
    user_data = user.model_dump(exclude={"password", "attributes", "is_primary"})

    response_data = {
        "access_token": CustomAccessBearer.access_token(data=jsonable_encoder(user_data), user_id=str(user.id)),
        "referesh_token": CustomAccessBearer.refresh_token(data=jsonable_encoder(user_data), user_id=str(user.id)),
        "user": user_data,
    }
    response_data["user"]["role"] = role.model_dump()
    return JSONResponse(content=jsonable_encoder(response_data), status_code=status.HTTP_200_OK)


async def logout(request: Request) -> JSONResponse:

    authorization = request.headers.get("Authorization").split()[1]
    await blacklist_token.add_blacklist_token(authorization)

    decode_token = CustomAccessBearer.decode_access_token(authorization)

    data = decode_token["subject"]
    user_data = {
        "id": data["id"],
        "email": data["email"],
        "fullname": data["fullname"],
        "role": data["role"],
        "is_active": data["is_active"],
    }
    response_data = {
        "access_token": CustomAccessBearer.access_token(data=user_data, user_id=decode_token["jti"]),
        "referesh_token": CustomAccessBearer.refresh_token(data=user_data, user_id=decode_token["jti"]),
    }

    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_data))


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
        data={"email": email}, user_id=str(user.id), expires_delta=timedelta(minutes=5)
    )
    reset_password_link = settings.FRONTEND_URL + settings.FRONTEND_PATH_RESET_PASSWORD + str(reset_token)

    template = template_env.get_template(name="reset_password.html")
    rendered_html = template.render(reset_password_link=reset_password_link)

    mail_service.send_email_background(
        background_tasks=background,
        receiver_email=user.email.lower(),
        subject="Yimba: Réinitialisation de mot de passe",
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
    rendered_html = template.render(login_link=login_link)

    mail_service.send_email_background(
        background_tasks=background,
        receiver_email=user.email.lower(),
        subject="Yimba: Réinitialisation de mot de passe confirmé",
        body=rendered_html,
    )

    response_data = {"message": "Your password has been successfully updated !"}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(response_data),
    )
