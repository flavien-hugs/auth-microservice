import logging
from datetime import datetime, timedelta, timezone
from typing import List, Sequence

from fastapi import Request, status
from fastapi.security import HTTPBearer
from fastapi_jwt import JwtAccessBearer
from jose import jwt, JWTError, ExpiredSignatureError
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from src.common.helpers.exceptions import CustomHTTException
from src.config import jwt_settings
from src.services.roles import get_one_role
from src.shared.error_codes import AuthErrorCode

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

_jwt_access_bearer = None
password_context = PasswordHash((Argon2Hasher(), BcryptHasher()))


class CustomAccessBearer:

    @classmethod
    def _conf_jwt_access_bearer(cls) -> JwtAccessBearer:
        access_expires_delta = timedelta(minutes=jwt_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires_delta = timedelta(minutes=jwt_settings.REFRESH_TOKEN_EXPIRE_MINUTES)

        cls._jwt_access_bearer = JwtAccessBearer(
            secret_key=jwt_settings.JWT_SECRET_KEY,
            algorithm=jwt_settings.JWT_ALGORITHM,
            access_expires_delta=access_expires_delta,
            refresh_expires_delta=refresh_expires_delta,
        )

        return cls._jwt_access_bearer

    @classmethod
    def access_token(cls, data: dict, user_id: str) -> str:
        access_bearer = cls._conf_jwt_access_bearer()
        expires_delta = timedelta(minutes=jwt_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return access_bearer.create_access_token(subject=data, expires_delta=expires_delta, unique_identifier=user_id)

    @classmethod
    def refresh_token(cls, data: dict, user_id: str) -> str:
        access_bearer = cls._conf_jwt_access_bearer()
        expires_delta = timedelta(minutes=jwt_settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        return access_bearer.create_refresh_token(subject=data, expires_delta=expires_delta, unique_identifier=user_id)

    @classmethod
    def decode_access_token(cls, token: str) -> dict:
        return jwt.decode(
            token=token,
            key=jwt_settings.JWT_SECRET_KEY,
            algorithms=[jwt_settings.JWT_ALGORITHM],
        )

    @classmethod
    async def verify_access_token(cls, token: str) -> bool:
        try:
            decode_token = cls.decode_access_token(token)
            current_timestamp = datetime.now(timezone.utc).timestamp()

            if decode_token["exp"] > current_timestamp:
                return True
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_EXPIRED_ACCESS_TOKEN,
                message_error="Token has expired !",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        except (ExpiredSignatureError, JWTError) as err:
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_INVALID_ACCESS_TOKEN,
                message_error=str(err),
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from err

    @classmethod
    async def check_permissions(cls, token: str, required_permissions: Sequence = ()) -> bool:
        docode_token = cls.decode_access_token(token)
        user_role_id = docode_token["subject"]["role"]

        role = await get_one_role(role_id=user_role_id)

        user_permissions = []
        for permissions in role.permissions:
            for perm in permissions["permissions"]:
                user_permissions.append(perm["code"])

        if not all(perm in user_permissions for perm in required_permissions):
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_INSUFFICIENT_PERMISSION,
                message_error="You do not have the necessary permissions to access this resource.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return True


class AuthTokenBearer(HTTPBearer):
    async def __call__(self, request: Request):
        if auth := await super().__call__(request=request):
            if not (auth.scheme.lower() == "bearer" and auth.scheme.startswith("Bearer")):
                raise CustomHTTException(
                    code_error=AuthErrorCode.AUTH_MISSING_SCHEME,
                    message_error="Missing or invalid authentication scheme.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            await CustomAccessBearer.verify_access_token(auth.credentials)
            return auth.credentials

        raise CustomHTTException(
            code_error=AuthErrorCode.AUTH_EXPIRED_ACCESS_TOKEN,
            message_error="The token has expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class CheckPermissionsHandler:
    """Handler for checking permissions based on the required permissions.

    This class provides a callable interface to check if a user has the required permissions
    based on the provided list of permissions.

    :param required_permissions: A list of strings representing the required permissions.
    :type required_permissions: list
    """

    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    async def __call__(self, request: Request):
        if not (authorization := request.headers.get("Authorization")):
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_MISSING_TOKEN,
                message_error="Missing token.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        token = authorization.split("Bearer ")[1]
        return await CustomAccessBearer.check_permissions(token, self.required_permissions)
