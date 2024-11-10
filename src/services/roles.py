import logging
import os
from datetime import datetime, UTC
from typing import Dict, List, Optional, Sequence, Set

from beanie import PydanticObjectId
from fastapi_pagination import paginate
from pymongo import ASCENDING, DESCENDING
from slugify import slugify
from starlette import status

from src.common.helpers.caching import delete_custom_key
from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.models import Role, User
from src.schemas import RoleModel
from src.shared.error_codes import RoleErrorCode
from src.shared.utils import SortEnum
from .perms import get_all_permissions

logging.basicConfig(format="%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

service_appname_slug = slugify(settings.APP_NAME)


async def get_formatted_permissions() -> List[Dict]:
    all_permissions = await get_all_permissions()
    formatted_permissions = []

    for permission in all_permissions:
        service_info = {"name": permission["app"], "title": permission["title"]}
        service_permissions = [
            {"code": perm["code"], "description": perm["desc"]} for perm in permission["permissions"]
        ]

        if service_permissions:
            formatted_permissions.append({"service_info": service_info, "permissions": service_permissions})

    return formatted_permissions


async def create_role(role: RoleModel) -> Role:
    new_role = await Role(**role.model_dump()).create()
    return new_role


async def insert_default_role(name: str, permissions: List[Dict], description: str = None) -> None:
    slug_value = slugify(name)
    if await Role.find_one({"slug": slug_value}).exists():
        logger.info(f"--> Role '{name}' already exists!")
        return

    role_data = {"name": name, "permissions": permissions}
    if description:
        role_data["description"] = description

    await Role(**role_data).create()
    logger.info(f"--> Role '{name}' created successfully!")


async def create_admin_role():
    admin_role_name = os.getenv("DEFAULT_ADMIN_ROLE")
    admin_role_description = os.getenv("DEFAULT_ADMIN_ROLE_DESCRIPTION")
    permissions = await get_formatted_permissions()

    await insert_default_role(admin_role_name, permissions, admin_role_description)


async def get_one_role(role_id: PydanticObjectId) -> Role:
    if (role := await Role.get(document_id=PydanticObjectId(role_id))) is None:
        raise CustomHTTException(
            code_error=RoleErrorCode.ROLE_NOT_FOUND,
            message_error=f"Role with '{role_id}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return role


async def update_role(role_id: PydanticObjectId, update_role: RoleModel) -> Role:
    role = await get_one_role(role_id=role_id)

    if await Role.find_one({"_id": {"$ne": role_id}, "slug": slugify(update_role.name)}).exists():
        raise CustomHTTException(
            code_error=RoleErrorCode.ROLE_ALREADY_EXIST,
            message_error=f"Role with name '{update_role.name}' already exists.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    result = await role.set(
        {
            **update_role.model_dump(exclude_none=True, exclude_unset=True),
            "slug": slugify(update_role.name),
            "updated_at": datetime.now(tz=UTC),
        }
    )
    return result


async def get_users_for_role(name: str, sorting: Optional[SortEnum] = SortEnum.DESC):
    if (role := await Role.find_one({"slug": slugify(name)})) is None:
        raise CustomHTTException(
            code_error=RoleErrorCode.ROLE_NOT_FOUND,
            message_error=f"Role with '{name}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    sorted = DESCENDING if sorting == SortEnum.DESC else ASCENDING
    users = await User.find({"role": PydanticObjectId(role.id)}, sort=[("created_at", sorted)]).to_list()
    users_list = [{**user.model_dump(by_alias=True, mode="json", exclude={"password", "is_primary"})} for user in users]
    result = paginate(users_list)
    return result


async def assign_permissions_to_role(role_id: PydanticObjectId, permission_codes: Set[str]) -> Role:
    role = await get_one_role(role_id=role_id)
    old_permissions = role.permissions.copy()

    await role.update({"$pull": {"permissions": {"$in": role.permissions}}})

    all_permissions = await get_all_permissions()

    new_permissions = []
    for permission in all_permissions:
        service_info = {"name": permission["app"], "title": permission["title"]}
        service_permissions = []

        for perm in permission["permissions"]:
            if perm["code"] in permission_codes:
                service_permissions.append({"code": perm["code"], "description": perm["desc"]})

        if service_permissions:
            new_permissions.append({"service_info": service_info, "permissions": service_permissions})
    if not new_permissions:
        return await role.update({"$set": {"permissions": old_permissions}})

    await delete_custom_key(custom_key_prefix=settings.APP_NAME + "check-permissions")
    await delete_custom_key(custom_key_prefix=settings.APP_NAME + "access")

    return await role.update({"$addToSet": {"permissions": {"$each": new_permissions}}})


async def delete_role(role_id: PydanticObjectId) -> None:
    await Role.find_one({"_id": PydanticObjectId(role_id)}).delete()


async def delete_many_roles(role_ids: Sequence[PydanticObjectId]) -> None:
    valid_oids = [PydanticObjectId(oid) for oid in role_ids]
    await Role.find({"_id": {"$in": valid_oids}}).delete()
