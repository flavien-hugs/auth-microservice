import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Set

from fastapi import Request, status
from fastapi.security import HTTPBearer
from fastapi_cache.decorator import cache
from fastapi_jwt import JwtAccessBearer
from jose import ExpiredSignatureError, jwt, JWTError
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from slugify import slugify

from src.common.helpers.exceptions import CustomHTTException
from src.config import jwt_settings, settings
from src.services.roles import get_one_role
from src.shared import blacklist_token
from src.shared.error_codes import AuthErrorCode
from src.shared.utils import custom_key_builder

logging.basicConfig(format="%(message)s", level=logging.INFO)

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
    def access_token(
        cls,
        data: dict,
        user_id: str = None,
        expires_delta: timedelta = timedelta(minutes=jwt_settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    ) -> str:
        access_bearer = cls._conf_jwt_access_bearer()
        return access_bearer.create_access_token(subject=data, expires_delta=expires_delta, unique_identifier=user_id)

    @classmethod
    def refresh_token(
        cls,
        data: dict,
        user_id: str,
        expires_delta: timedelta = timedelta(minutes=jwt_settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    ) -> str:
        access_bearer = cls._conf_jwt_access_bearer()
        return access_bearer.create_refresh_token(subject=data, expires_delta=expires_delta, unique_identifier=user_id)

    @classmethod
    def decode_access_token(cls, token: str) -> dict:
        try:
            result = jwt.decode(
                token=token,
                key=jwt_settings.JWT_SECRET_KEY,
                algorithms=[jwt_settings.JWT_ALGORITHM],
            )
        except (jwt.ExpiredSignatureError, JWTError) as err:
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_INVALID_ACCESS_TOKEN,
                message_error=str(err),
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from err

        return result

    @classmethod
    @cache(expire=settings.EXPIRE_CACHE, key_builder=custom_key_builder)  # noqa
    async def verify_access_token(cls, token: str) -> bool:
        """
        Verifies the validity of an access token by checking the cache and token properties.

        :param token: The access token to verify.
        :type token: str
        :return: True if the token is valid, otherwise raises a CustomHTTException.
        :rtype: bool
        :raises CustomHTTException: If the token is expired or invalid, raises a CustomHTTException.
        """

        try:
            if await blacklist_token.is_token_blacklisted(token):
                raise CustomHTTException(
                    code_error=AuthErrorCode.AUTH_EXPIRED_ACCESS_TOKEN,
                    message_error="Token has expired !",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            decode_token = cls.decode_access_token(token)
            current_timestamp = datetime.now(timezone.utc).timestamp()

            if decode_token["subject"]["is_active"] is True and decode_token["exp"] > current_timestamp:
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
    async def check_permissions(cls, token: str, required_permissions: Set[str] = ()) -> bool:
        """
        Checks if the token has the required permissions.

        :param token: The access token.
        :type token: str
        :param required_permissions: A set of required permissions.
        :type required_permissions: Set[str]
        :return: True if the user has the required permissions, otherwise raises a CustomHTTException.
        :rtype: bool
        :raises CustomHTTException: If the user doesn't have the required permissions.
        """

        docode_token = cls.decode_access_token(token)
        user_role_id = docode_token["subject"]["role"]

        role = await get_one_role(role_id=user_role_id)

        default_role = os.getenv("DEFAULT_ADMIN_ROLE")
        if role.slug == slugify(default_role):
            return True

        user_permissions = {perm["code"] for permissions in role.permissions for perm in permissions["permissions"]}

        if required_permissions & user_permissions:
            return True
        else:
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_INSUFFICIENT_PERMISSION,
                message_error="You do not have the necessary permissions to access this resource.",
                status_code=status.HTTP_403_FORBIDDEN,
            )


class AuthorizedHTTPBearer(HTTPBearer):
    """
    A custom HTTPBearer class that validates the Bearer authentication scheme
    and verifies the access token.

    This class extends the functionality of HTTPBearer to include additional validation checks
    for the bearer token scheme and validity. It verifies that the token is in the correct format
    and that it is valid for accessing the requested resource.

    :param HTTPBearer: A class for handling bearer token authentication.
    :type HTTPBearer: HTTPBearer
    """

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
    :type required_permissions: set
    """

    def __init__(self, required_permissions: Set[str]):
        self._required_permissions = required_permissions

    async def __call__(self, request: Request):
        if not (authorization := request.headers.get("Authorization")):
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_MISSING_TOKEN,
                message_error="Missing token.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        token = authorization.split("Bearer ")[1]
        return await CustomAccessBearer.check_permissions(token, self._required_permissions)
