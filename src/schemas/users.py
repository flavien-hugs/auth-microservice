from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, StrictStr

from src.config import settings


class CreateUser(BaseModel):
    email: EmailStr
    password: str = Field(..., ge=settings.PASSWORD_LENGTH)
    fullname: Optional[StrictStr] = Field(description=None, ge=settings.FULLNAME_MIN_LENGTH)


class UpdateUser(BaseModel):
    fullname: Optional[StrictStr] = Field(description=None, ge=settings.FULLNAME_MIN_LENGTH)
    attributes: Optional[Dict[str, Any]] = Field(default=None)
