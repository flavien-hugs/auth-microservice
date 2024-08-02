from fastapi import status, Request
from fastapi.responses import JSONResponse

from src.common.helpers.exceptions import CustomHTTException
from src.dependences.auth import CustomAccessBearer
from src.models import User
from src.schemas import LoginUser
from src.shared.error_codes import AuthErrorCode, UserErrorCode
from src.shared.utils import verify_password


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

    user_data = user.model_dump(exclude={"password", "attributes", "created_at", "updated_at"})

    response_data = {
        "access_token": CustomAccessBearer.access_token(data=user_data, user_id=str(user.id)),
        "referesh_token": CustomAccessBearer.refresh_token(data=user_data, user_id=str(user.id)),
        "user": user_data,
    }

    return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)


async def logout(request: Request) -> JSONResponse:
    authorization = request.headers.get("Authorization").split()[1]
    decode_token = CustomAccessBearer.decode_access_token(authorization)

    data = decode_token["subject"]
    user_data = {
        "id": data["id"],
        "email": data["email"],
        "fullname": data["fullname"],
        "role": data["role"],
        "is_active": data["is_active"],
    }
    reqponse_data = {
        "access_token": CustomAccessBearer.access_token(data=user_data, user_id=decode_token["jti"]),
        "referesh_token": CustomAccessBearer.refresh_token(data=user_data, user_id=decode_token["jti"]),
    }

    return JSONResponse(status_code=status.HTTP_200_OK, content=reqponse_data)
