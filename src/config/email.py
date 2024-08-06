from functools import lru_cache

from pydantic import EmailStr, Field, PositiveInt
from pydantic_settings import BaseSettings


class EmailSettings(BaseSettings):
    SMTP_PORT: PositiveInt = Field(..., alias="SMTP_PORT")
    SMTP_SERVER: str = Field(..., alias="SMTP_SERVER")
    EMAIL_PASSWORD: str = Field(..., alias="EMAIL_PASSWORD")
    EMAIL_SENDER_ADDRESS: EmailStr = Field(..., alias="EMAIL_SENDER_ADDRESS")
    EMAIL_FROM_TO: str = Field(..., alias="EMAIL_FROM_TO")


@lru_cache
def get_email_settings() -> EmailSettings:
    return EmailSettings()
