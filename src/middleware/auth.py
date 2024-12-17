import logging
from datetime import datetime, timedelta, timezone

from fastapi import Request, status
from fastapi.security import HTTPBearer
from fastapi_cache.decorator import cache
from fastapi_jwt import JwtAccessBearer
from jose import ExpiredSignatureError, jwt, JWTError
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from slugify import slugify

from src.common.helpers.caching import custom_key_builder as cache_key_builder
from src.common.helpers.exceptions import CustomHTTException
from src.config import jwt_settings, settings
from src.services import users
from src.shared import blacklist_token
from src.shared.error_codes import AuthErrorCode, UserErrorCode

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

            check_if_active = decode_token.get("subject", {}).get("is_active", False)
            token_exp = decode_token.get("exp", 0)
            if check_if_active is True and token_exp > current_timestamp:
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
    @cache(
        expire=settings.EXPIRE_CACHE,
        key_builder=cache_key_builder(
            settings.APP_NAME + "check-permissions",
            use_query_params=True,
            use_path_params=False,
        ),
    )
    async def check_permissions(cls, token: str, required_permissions: set[str] = ()) -> bool:
        """
        Checks if the token has the required permissions.

        :param token: The access token.
        :type token: str
        :param required_permissions: A set of required permissions.
        :type required_permissions: set[str]
        :return: True if the user has the required permissions, otherwise raises a CustomHTTException.
        :rtype: bool
        :raises CustomHTTException: If the user doesn't have the required permissions.
        """

        docode_token = cls.decode_access_token(token)
        user_role_name = docode_token.get("subject", {}).get("role", {}).get("slug")
        if user_role_name == slugify(settings.DEFAULT_ADMIN_ROLE):
            return True

        user_role = docode_token.get("subject", {}).get("role", {}).get("_id")
        role = await users.get_one_role(role_id=user_role)
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

    def __init__(self, required_permissions: set[str]):
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


class CheckUserAccessHandler:
    """ "
    Handler for checking user access based on the provided key and roles.

    This class provides a callable interface to check if a user has access to a resource
    based on the provided key and roles. It verifies that the user has the required roles
    to access the resource and that the user is the owner of the resource.

    :param key: The key to check for the resource.
    :rtype key: str
    :return: True if the user has access to the resource, otherwise raises a CustomHTTException.
    :rtype: bool
    :raises CustomHTTException: If the user is not authorized to access the resource.
    """

    def __init__(self, key: str):
        self.key = key

    async def __call__(self, request: Request) -> str:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise CustomHTTException(
                code_error=AuthErrorCode.AUTH_INVALID_TOKEN,
                message_error="Invalid or missing token.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        token = authorization.split("Bearer ")[1]

        if not (value := request.path_params.get(self.key) or request.query_params.get(self.key)):
            raise CustomHTTException(
                code_error=UserErrorCode.USER_NOT_FOUND,
                message_error=f"Resource '{value}' not found.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user_info = CustomAccessBearer.decode_access_token(token=token)
        user_subject = user_info.get("subject", {})
        user_role_info = user_subject.get("role", {})

        if user_role_info.get("slug", "") == slugify(settings.DEFAULT_ADMIN_ROLE) or user_subject.get("_id") == str(
            value
        ):
            return value
        else:
            raise CustomHTTException(
                code_error=UserErrorCode.USER_UNAUTHORIZED_PERFORM_ACTION,
                message_error="You are not authorized to perform this action.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
