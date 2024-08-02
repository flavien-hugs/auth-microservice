from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class AuthBaseConfig(BaseSettings):
    # APP CONFIG
    APP_NAME: str = Field(default="Auth", alias="APP_NAME")
    APP_TITLE: str = Field(default="Authentication and user management system", alias="APP_TITLE")
    APP_HOSTNAME: str = Field(default="0.0.0.0", alias="APP_HOSTNAME")
    APP_RELOAD: bool = Field(default=True, alias="APP_RELOAD")
    APP_ACCESS_LOG: bool = Field(default=True, alias="APP_ACCESS_LOG")
    APP_DEFAULT_PORT: int = Field(default=9077, alias="APP_DEFAULT_PORT")
    DEFAULT_PAGIGNIATE_PAGE_SIZE: int = Field(default=10, alias="DEFAULT_PAGIGNIATE_PAGE_SIZE")

    # USER MODEL NAME
    USER_MODEL_NAME: str = Field(..., alias="USER_MODEL_NAME")

    # DATABASE CONFIG
    MONGO_DB: str = Field(..., alias="MONGO_DB")
    MONGODB_URI: str = Field(..., alias="MONGODB_URI")


@lru_cache
def get_settings() -> AuthBaseConfig:
    return AuthBaseConfig()
