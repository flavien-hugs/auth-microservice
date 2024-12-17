from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId
from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from src.common.helpers.caching import delete_custom_key
from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.middleware import CustomAccessBearer
from src.models import User
from src.schemas import ChangePassword, LoginUser
from src.services.roles import get_one_role
from src.services.users import get_one_user
from src.shared import blacklist_token
from src.shared.error_codes import AuthErrorCode, UserErrorCode
from src.shared.utils import password_hash, verify_password


async def _find_user_by_identifier(identifier: str, is_email: bool) -> Optional[User]:
    search_field = "email" if is_email else "phonenumber"
    return await User.find_one({search_field: identifier})


async def _validate_user_status(user: User) -> None:
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


async def login(request: Request, payload: LoginUser) -> JSONResponse:
    is_email = settings.REGISTER_WITH_EMAIL
    identifier: Optional[str] = payload.email if is_email else payload.phonenumber

    if not identifier:
        field = "email" if is_email else "phonenumber"
        raise CustomHTTException(
            code_error=AuthErrorCode.AUTH_INVALID_CREDENTIALS,
            message_error=f"{field.capitalize()} is required for login.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = await _find_user_by_identifier(identifier, is_email)
    await _validate_user_status(user)

    if not verify_password(payload.password, user.password):
        raise CustomHTTException(
            code_error=AuthErrorCode.AUTH_INVALID_PASSWORD,
            message_error="Your password is invalid.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    role = await get_one_role(role_id=PydanticObjectId(user.role))
    user_data = user.model_dump(by_alias=True, mode="json", exclude={"password", "attributes", "is_primary"})
    user_data.update(
        {"role": role.model_dump(by_alias=True, mode="json", exclude={"permissions", "created_at", "updated_at"})}
    )

    response_data = {
        "access_token": CustomAccessBearer.access_token(data=jsonable_encoder(user_data), user_id=str(user.id)),
        "referesh_token": CustomAccessBearer.refresh_token(data=jsonable_encoder(user_data), user_id=str(user.id)),
        "user": user_data,
    }

    return JSONResponse(content=jsonable_encoder(response_data), status_code=status.HTTP_200_OK)


async def logout(request: Request) -> JSONResponse:
    authorization = request.headers.get("Authorization")
    token = authorization.split()[1]
    await blacklist_token.add_blacklist_token(token)

    await delete_custom_key(settings.APP_NAME + "access")
    await delete_custom_key(settings.APP_NAME + "validate")

    return JSONResponse(content={"message": "Logout successfully !"}, status_code=status.HTTP_200_OK)


async def change_password(user_id: PydanticObjectId, payload: ChangePassword) -> JSONResponse:
    user = await get_one_user(user_id=user_id)

    password = password_hash(password=payload.confirm_password)
    await user.set({"password": password})

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"message": "Your password has been successfully updated !"}),
    )


async def check_access(token: str, permission: set[str]) -> JSONResponse:
    access = await CustomAccessBearer.check_permissions(token=token, required_permissions=permission)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"access": access}))


async def validate_access_token(token: str) -> JSONResponse:
    decode_token = CustomAccessBearer.decode_access_token(token=token)
    current_timestamp = datetime.now(timezone.utc).timestamp()
    is_token_active = decode_token.get("exp", 0) > current_timestamp
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"active": bool(is_token_active), "user_info": decode_token.get("subject", {})}),
    )


async def check_user_attribute(key: str, value: str, in_attributes: Optional[bool] = False) -> JSONResponse:
    query = {f"attributes.{key}": value} if in_attributes else {key: value}
    can = await User.find_one(query).exists()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"exists": can})
