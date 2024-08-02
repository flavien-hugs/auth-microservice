from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class JwtTokenSettings(BaseSettings):
    JWT_SECRET_KEY: str = Field(..., alias="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(..., alias="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(..., alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(..., alias="REFRESH_TOKEN_EXPIRE_MINUTES")


@lru_cache
def get_token_settings() -> JwtTokenSettings:
    return JwtTokenSettings()
