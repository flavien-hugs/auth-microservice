from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class EnableEndpointSettings(BaseSettings):
    SHOW_MEMBERS_IN_ROLE_ENDPOINT: Optional[bool] = Field(default=1, alias="SHOW_MEMBERS_IN_ROLE_ENDPOINT")
    SHOW_CHECK_USER_ATTRIBUTE_ENDPOINT: Optional[bool] = Field(default=1, alias="SHOW_CHECK_USER_ATTRIBUTE_ENDPOINT")
    SHOW_FIND_USER_BY_PHONENUMBER_ENDPOINT: Optional[bool] = Field(
        default=1, alias="SHOW_FIND_USER_BY_PHONENUMBER_ENDPOINT"
    )


@lru_cache
def enable_endpoint() -> EnableEndpointSettings:
    return EnableEndpointSettings()
