from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class SmsBaseConfig(BaseSettings):
    SMS_URL: str = Field(..., alias="SMS_URL")
    SMS_SENDER: str = Field(..., alias="SMS_SENDER")
    SMS_API_KEY: str = Field(..., alias="SMS_API_KEY")
    SMS_TYPE: Optional[int] = Field(default=1, alias="SMS_TYPE")
    SMS_CLIENT_ID: str = Field(..., alias="SMS_CLIENT_ID")


@lru_cache
def get_sms_config() -> SmsBaseConfig:
    return SmsBaseConfig()
