from functools import lru_cache
from typing import Optional
from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class AuthBaseConfig(BaseSettings):
    # APP CONFIG
    APP_NAME: Optional[str] = Field(default="Auth", alias="APP_NAME")
    APP_TITLE: Optional[str] = Field(default="UNSTA: User management and Auth", alias="APP_TITLE")
    APP_HOSTNAME: Optional[str] = Field(default="0.0.0.0", alias="APP_HOSTNAME")
    APP_RELOAD: Optional[bool] = Field(default=True, alias="APP_RELOAD")
    FULLNAME_MIN_LENGTH: Optional[PositiveInt] = Field(default=4, alias="FULLNAME_MIN_LENGTH")
    APP_ACCESS_LOG: Optional[bool] = Field(default=True, alias="APP_ACCESS_LOG")
    APP_DEFAULT_PORT: Optional[PositiveInt] = Field(default=9077, alias="APP_DEFAULT_PORT")
    PASSWORD_MIN_LENGTH: Optional[PositiveInt] = Field(default=3, alias="PASSWORD_MIN_LENGTH")
    DEFAULT_ADMIN_ROLE: Optional[str] = Field(default="Super administrateur", alias="DEFAULT_ADMIN_ROLE")
    ENABLE_OTP_CODE: Optional[bool] = Field(..., alias="ENABLE_OTP_CODE")
    OTP_CODE_DIGIT_LENGTH: Optional[PositiveInt] = Field(default=4, alias="OTP_CODE_DIGIT_LENGTH")
    REGISTER_WITH_EMAIL: Optional[bool] = Field(..., alias="REGISTER_WITH_EMAIL")
    LIST_ROLES_ENDPOINT_SECURITY_ENABLED: Optional[bool] = Field(..., alias="LIST_ROLES_ENDPOINT_SECURITY_ENABLED")
    REGISTER_USER_ENDPOINT_SECURITY_ENABLED: Optional[bool] = Field(
        ..., alias="REGISTER_USER_ENDPOINT_SECURITY_ENABLED"
    )
    LIST_PARAMETERS_ENDPOINT_SECURITY_ENABLED: Optional[bool] = Field(
        ..., alias="LIST_PARAMETERS_ENDPOINT_SECURITY_ENABLED"
    )
    USE_GRIDFS_STORAGE: Optional[bool] = Field(default=False, alias="USE_GRIDFS_STORAGE")
    LIST_PARAMETERS_ENDPOINT_SECURITY_ENABLED: Optional[bool] = Field(
        default=False, alias="LIST_PARAMETERS_ENDPOINT_SECURITY_ENABLED"
    )

    # USER MODEL NAME
    USER_MODEL_NAME: str = Field(..., alias="USER_MODEL_NAME")
    ROLE_MODEL_NAME: str = Field(..., alias="ROLE_MODEL_NAME")
    PARAM_MODEL_NAME: str = Field(..., alias="PARAM_MODEL_NAME")
    LOGIN_LOG_MODEL_NAME: str = Field(..., alias="LOGIN_LOG_MODEL_NAME")

    # FRONTEND URL CONFIG
    FRONTEND_URL: Optional[str] = Field(..., alias="FRONTEND_URL")
    FRONTEND_PATH_LOGIN: Optional[str] = Field(..., alias="FRONTEND_PATH_LOGIN")
    FRONTEND_PATH_RESET_PASSWORD: Optional[str] = Field(..., alias="FRONTEND_PATH_RESET_PASSWORD")
    FRONTEND_PATH_ACTIVATE_ACCOUNT: Optional[str] = Field(..., alias="FRONTEND_PATH_ACTIVATE_ACCOUNT")

    # DATABASE CONFIG
    MONGO_DB: str = Field(..., alias="MONGO_DB")
    MONGO_FS_BUCKET_NAME: str = Field(default="auth", alias="MONGO_FS_BUCKET_NAME")
    MONGODB_URI: str = Field(..., alias="MONGODB_URI")

    # REDIS CONFIG
    CACHE_DB_URL: str = Field(default="redis://redis:6379/0", alias="CACHE_DB_URL")
    EXPIRE_CACHE: Optional[PositiveInt] = Field(default=500, alias="EXPIRE_CACHE")

    # MIDDLEWARE CONFIG
    COMPRESS_MIN_SIZE: Optional[PositiveInt] = Field(default=1_000, alias="COMPRESS_MIN_SIZE")


@lru_cache
def get_settings() -> AuthBaseConfig:
    return AuthBaseConfig()
