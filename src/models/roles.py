from typing import Dict, List, Optional

import pymongo
from beanie import Document, Indexed, Insert, before_event
from slugify import slugify
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.schemas import RoleModel
from src.shared.error_codes import RoleErrorCode

from .mixins import DatetimeTimestamp


class Role(RoleModel, DatetimeTimestamp, Document):
    permissions: List[Dict] = []
    slug: Optional[Indexed(str)] = None

    class Settings:
        name = settings.ROLE_MODEL_NAME
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
            raise CustomHTTException(
                code_error=RoleErrorCode.ROLE_ALREADY_EXIST,
                message_error=f"This role '{self.name}' already exists.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        self.slug = new_slug_value
