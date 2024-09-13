from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class EnableEndpointSettings(BaseSettings):
    SHOW_MEMBERS_IN_ROLE_ENDPOINT: bool = Field(default=0, alias="SHOW_MEMBERS_IN_ROLE_ENDPOINT")
    SHOW_CREATE_NEW_ACCOUNT_ENDPOINT: bool = Field(default=0, alias="SHOW_CREATE_NEW_ACCOUNT_ENDPOINT")
    SHOW_REQUEST_CREATE_ACCOUNT_ENDPOINT: bool = Field(default=0, alias="SHOW_REQUEST_CREATE_ACCOUNT_ENDPOINT")
    SHOW_CHECK_USER_ATTRIBUTE_ENDPOINT: bool = Field(default=1, alias="SHOW_CHECK_USER_ATTRIBUTE_ENDPOINT")


@lru_cache()
def enable_endpoint() -> EnableEndpointSettings:
    return EnableEndpointSettings()
