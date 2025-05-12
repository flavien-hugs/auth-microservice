from typing import Optional

import pymongo
from beanie import before_event, Document, Indexed, Insert
from pydantic import Field
from slugify import slugify

from src.config import settings
from src.schemas import ParamsModel
from src.shared import DuplicateKeyException
from .mixins import DatetimeTimestamp


class Params(ParamsModel, DatetimeTimestamp, Document):
    slug: Optional[Indexed(str)] = Field(..., description="Slug of the parameter")

    class Settings:
        name = settings.PARAM_MODEL_NAME
        use_state_management = True
        indexes = [
            pymongo.IndexModel(
                keys=[
                    ("name", pymongo.ASCENDING),
                    ("type", pymongo.ASCENDING),
                    ("slug", pymongo.ASCENDING),
                ],
                unique=True,
                background=True,
            )
        ]

    @before_event(Insert)
    async def generate_unique_slug(self, **kwargs):
        new_slug_value = slugify(self.name)
        if await Params.find({"slug": new_slug_value, "type": self.type}).exists() is True:
            raise DuplicateKeyException(f"This parameter '{self.name}' already exists.")
        new_value = self.type + self.name
        self.slug = slugify(new_value)
