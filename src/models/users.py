from datetime import datetime

from beanie import Document
from pydantic import Field, StrictBool

from src.config import settings
from src.schemas import CreateUser


class User(Document, CreateUser):
    is_active: StrictBool = True
    created_at: datetime = Field(default=datetime.now().timestamp(), description="Date user created")

    class Settings:
        name = settings.USER_MODEL_NAME
