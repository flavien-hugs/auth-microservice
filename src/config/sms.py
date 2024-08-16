from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class SmsBaseConfig(BaseSettings):
    SMS_ENDPOINT: str = Field(..., alias="SMS_ENDPOINT")
    SMS_USERNAME: str = Field(..., alias="SMS_USERNAME")
    SMS_SENDER: str = Field(..., alias="SMS_SENDER")
    SMS_TOKEN: str = Field(..., alias="SMS_TOKEN")


@lru_cache
def get_sms_config() -> SmsBaseConfig:
    return SmsBaseConfig()
