from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", Any, BaseModel)


class ResponseModelData(BaseModel, Generic[T]):
    message: str
    data: T
