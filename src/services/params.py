from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import status
from slugify import slugify

from src.common.helpers.exceptions import CustomHTTException
from src.models import Params
from src.schemas import ParamsModel
from src.shared.error_codes import ParamErrorCode


async def create(params: ParamsModel) -> Params:
    return await Params(**params.model_dump()).create()


async def get_one(id: PydanticObjectId) -> Params:
    if (param := await Params.get(document_id=id)) is None:
        raise CustomHTTException(
            code_error=ParamErrorCode.DOCUMENT_NOT_FOUND,
            message_error=f"Parameter {id} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return param


async def update(id: PydanticObjectId, param: ParamsModel) -> Params:
    param = await get_one(id=id)

    slug_value = f"{param.type}-{param.name}"
    if await Params.find_one({"_id": {"$ne": id}, "slug": slugify(slug_value)}).exists():
        raise CustomHTTException(
            code_error=ParamErrorCode.PARAM_ALREADY_EXIST,
            message_error=f"Parameter with name '{param.name}' already exists.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    result = await param.set(
        {
            **param.model_dump(exclude_none=True, exclude_unset=True),
            "slug": slugify(slug_value),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    return result


async def delete(id: PydanticObjectId) -> None:
    await Params.find_one({"_id": PydanticObjectId(id)}).delete()
