import logging
import os
from typing import Sequence

from beanie import PydanticObjectId
from slugify import slugify
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.models import Role, User
from src.schemas import CreateUser, UpdateUser
from src.shared.error_codes import UserErrorCode
from src.shared.utils import password_hash
from .roles import get_one_role

logger = logging.getLogger(__name__)


async def create_user(user: CreateUser) -> User:
    """
    Créer un nouvel utilisateur

    :param user: Les informations de l'utilisateur à créer
    :type user: CreateUser
    :return: Le nouvel utilisateur créé
    :rtype: User
    """
    await get_one_role(role_id=PydanticObjectId(user.role))
    if await User.find_one({"email": user.email, "is_active": True}).exists():
        raise CustomHTTException(
            code_error=UserErrorCode.USER_EMAIL_ALREADY_EXIST,
            message_error=f"User with email '{user.email.lower()}' already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user_data = user.model_copy(update={"password": password_hash(user.password)})
    new_user = await User(**user_data.model_dump()).create()
    return new_user


async def create_first_user():
    """
    Create first user
    :return:
    :rtype:
    """
    paylaod = {"email": os.getenv("DEFAULT_ADMIN_EMAIL"), "fullname": os.getenv("DEFAULT_ADMIN_FULLNAME")}

    default_role = os.getenv("DEFAULT_ADMIN_ROLE")
    if (role := await Role.find_one({"slug": slugify(default_role)})) is None:
        logger.info("Role not found !")
        return

    if await User.find_one({"email": paylaod["email"], "is_primary": True}).exists():
        logger.info("Admin user alreay exist !")
        return
    else:
        password = os.getenv("DEFAULT_ADMIN_PASSWORD")
        user = User(**paylaod, role=role.id, is_primary=True)
        user.password = password_hash(password)
        await user.create()
        logger.info("Create first user successfully !")


async def get_one_user(user_id: PydanticObjectId):
    """
    :param user_id:
    :type user_id:
    :return:
    :rtype:
    """
    if (user := await User.get(document_id=PydanticObjectId(user_id))) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with '{user_id}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    role = await get_one_role(role_id=PydanticObjectId(user.role))
    return user.model_copy(update={"extras": {"role_info": role.model_dump()}}, deep=True)


async def update_user(user_id: PydanticObjectId, update_user: UpdateUser):
    """

    :param user_id:
    :type user_id:
    :param update_user:
    :type update_user:
    :return:
    :rtype:
    """
    await get_one_role(role_id=PydanticObjectId(update_user.role))
    user = await get_one_user(user_id=user_id)
    result = await user.set({**update_user.model_dump(exclude_none=True, exclude_unset=True)})

    role = await get_one_role(role_id=PydanticObjectId(result.role))
    return user.model_copy(update={"extras": {"role_info": role.model_dump()}}, deep=True)


async def delete_user(user_id: PydanticObjectId) -> None:
    await User.get(document_id=PydanticObjectId(user_id)).delete()


async def delete_many_users(user_ids: Sequence[PydanticObjectId]) -> None:
    valid_oids = [PydanticObjectId(oid) for oid in user_ids]
    await User.find({"_id": {"$in": valid_oids}}).delete()
