from typing import Dict, List, Optional

import pymongo
from beanie import before_event, Document, Indexed, Insert
from pydantic import Field
from slugify import slugify

from src.config import settings
from src.schemas import RoleModel
from src.shared import DuplicateKeyException
from .mixins import DatetimeTimestamp


class Role(RoleModel, DatetimeTimestamp, Document):
    permissions: List[Dict] = Field(default_factory=list, description="Role permissions")
    slug: Optional[Indexed(str)] = Field(None, description="Role slug")

    class Settings:
        name = settings.ROLE_MODEL_NAME
        use_state_management = True
        indexes = [
            pymongo.IndexModel(
                keys=[
                    ("name", pymongo.TEXT),
                    ("description", pymongo.TEXT),
                    ("slug", pymongo.TEXT),
                ]
            )
        ]

    @before_event(Insert)
    async def generate_unique_slug(self, **kwargs):
        new_slug_value = slugify(self.name)
        if await Role.find({"slug": new_slug_value}).exists() is True:
            raise DuplicateKeyException(f"This role '{self.name}' already exists.")
        self.slug = new_slug_value
