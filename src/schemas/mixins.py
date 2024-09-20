from typing import Optional

from fastapi import Query
from pydantic import BaseModel


class FilterParams(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None


def get_filter_params(type: Optional[str] = Query(None), name: Optional[str] = Query(None)) -> FilterParams:
    return FilterParams(type=type, name=name)
