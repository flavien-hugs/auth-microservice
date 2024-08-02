from typing import Sequence

from beanie import PydanticObjectId
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.models import User
from src.schemas import CreateUser, UpdateUser
from src.shared.error_codes import UserErrorCode
from src.shared.utils import password_hash


async def create_user(user: CreateUser) -> User:
    new_user = User(**user.model_dump())
    new_user.password = password_hash(user.password)
    return await new_user.create()


async def get_one_user(user_id: PydanticObjectId) -> User:
    if (result := await User.get(document_id=PydanticObjectId(user_id))) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with '{user_id}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return result


async def update_user(user_id: PydanticObjectId, update_user: UpdateUser) -> User:
    if (user := await User.get(document_id=PydanticObjectId(user_id))) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with '{user_id}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    result = await user.set({**update_user.model_dump(exclude_none=True, exclude_unset=True)})
    return result


async def delete_user(user_id: PydanticObjectId) -> None:
    await User.get(document_id=PydanticObjectId(user_id)).delete()


async def delete_many_users(user_ids: Sequence[PydanticObjectId]) -> None:
    valid_oids = [PydanticObjectId(oid) for oid in user_ids]
    await User.find({"_id": {"$in": valid_oids}}).delete()
