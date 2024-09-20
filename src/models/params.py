from typing import Optional

import pymongo
from beanie import before_event, Document, Indexed, Insert
from slugify import slugify
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.schemas import ParamsModel
from src.shared.error_codes import ParamErrorCode
from .mixins import DatetimeTimestamp


class Params(ParamsModel, DatetimeTimestamp, Document):
    slug: Optional[Indexed(str)] = None

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
            raise CustomHTTException(
                code_error=ParamErrorCode.PARAM_ALREADY_EXIST,
                message_error=f"This parameter '{self.name}' already exists.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        new_value = self.type + self.name
        self.slug = slugify(new_value)
