from datetime import datetime
from typing import Any, Mapping, Optional

from beanie import after_event, Document, Update
from pydantic import Field, StrictBool

from src.config import settings
from src.schemas import CreateUser


class User(CreateUser, Document):
    is_active: StrictBool = True
    attributes: Optional[Mapping[str, Any]] = Field(default=None, description="User attributes", examples=[{"key": "value"}])
    created_at: datetime = Field(default=datetime.now(), description="Create user date")
    updated_at: datetime = Field(default=datetime.now(), description="Updated user date")

    class Settings:
        name = settings.USER_MODEL_NAME

    @after_event(Update)
    def set_updated_at(self):
        self.updated_at = datetime.now()
