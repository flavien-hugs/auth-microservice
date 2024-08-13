from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class IncludeInSwagger(BaseSettings):
    SHOW_CREATE_NEW_ACCOUNT: bool = Field(..., alias="SHOW_CREATE_NEW_ACCOUNT")
    SHOW_REQUEST_CREATE_ACCOUNT: bool = Field(..., alias="SHOW_REQUEST_CREATE_ACCOUNT")


@lru_cache()
def include_in_swagger() -> IncludeInSwagger:
    return IncludeInSwagger()
