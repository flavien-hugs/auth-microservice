from functools import lru_cache

from pydantic import EmailStr, Field, PositiveInt
from pydantic_settings import BaseSettings


class EmailSettings(BaseSettings):
    SMTP_SERVER: str = Field(..., alias="SMTP_SERVER")
    SMTP_APP_NAME: str = Field(..., alias="SMTP_APP_NAME")
    SMTP_PORT: PositiveInt = Field(..., alias="SMTP_PORT")
    EMAIL_FROM_TO: str = Field(..., alias="EMAIL_FROM_TO")
    EMAIL_PASSWORD: str = Field(..., alias="EMAIL_PASSWORD")
    EMAIL_SENDER_ADDRESS: EmailStr = Field(..., alias="EMAIL_SENDER_ADDRESS")
    ACTIVATE_LINK_IFESPAN_MINUTE: PositiveInt = Field(default=5, alias="ACTIVATE_LINK_IFESPAN_MINUTE")
    RESET_PASSWORD_LIFESPAN_MINUTE: PositiveInt = Field(default=5, alias="RESET_PASSWORD_LIFESPAN_MINUTE")


@lru_cache
def get_email_settings() -> EmailSettings:
    return EmailSettings()
