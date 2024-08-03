import logging
import os
from typing import Sequence, Set

from beanie import PydanticObjectId
from slugify import slugify
from starlette import status

from src.common.helpers.exceptions import CustomHTTException
from src.models import Role
from src.schemas import RoleModel
from src.shared.error_codes import RoleErrorCode
from .perms import get_all_permissions

logger = logging.getLogger(__name__)


async def create_role(role: RoleModel) -> Role:
    """

    :param role:
    :type role:
    :return:
    :rtype:
    """
    new_role = await Role(**role.model_dump()).create()
    return new_role


async def create_first_role():
    paylaod = {"name": os.getenv("DEFAULT_ADMIN_ROLE"), "description": os.getenv("DEFAULT_ADMIN_ROLE_DESCRIPTION")}

    slug_value = os.getenv("DEFAULT_ADMIN_ROLE")
    if await Role.find_one({"slug": slug_value}).exists():
        logger.info("Role is exist")
        return
    else:
        all_permissions = await get_all_permissions()
        new_permissions = []

        for permission in all_permissions:
            service_info = {"name": permission["app"], "title": permission["title"]}
            service_permissions = []

            for perm in permission["permissions"]:
                service_permissions.append({"code": perm["code"], "description": perm["desc"]})

            if service_permissions:
                new_permissions.append({"service_info": service_info, "permissions": service_permissions})

        await Role(**paylaod, permissions=new_permissions).create()
        logger.info("Create role successfully !")


async def get_one_role(role_id: PydanticObjectId) -> Role:
    """

    :param role_id:
    :type role_id:
    :return:
    :rtype:
    """
    if (role := await Role.get(document_id=PydanticObjectId(role_id))) is None:
        raise CustomHTTException(
            code_error=RoleErrorCode.ROLE_NOT_FOUND,
            message_error=f"Role with '{role_id}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return role


async def update_role(role_id: PydanticObjectId, update_role: RoleModel) -> Role:
    role = await get_one_role(role_id=role_id)
    result = await role.set(
        {**update_role.model_dump(exclude_none=True, exclude_unset=True), "slug": slugify(update_role.name)}
    )
    return result


async def assign_permissions_to_role(role_id: PydanticObjectId, permission_codes: Set[str]) -> Role:
    """
    Ajouter une liste de permissions à un rôle.

    :param role_id: ID du rôle
    :type role_id: PydanticObjectId
    :param permission_codes: Liste de permissions à ajouter
    :type permission_codes: set
    :return: Le role mis à jour
    :rtype: dict
    """

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

    return await role.update({"$addToSet": {"permissions": {"$each": new_permissions}}})


async def delete_role(role_id: PydanticObjectId) -> None:
    """

    :param role_id:
    :type role_id:
    :return:
    :rtype:
    """
    await Role.get(document_id=PydanticObjectId(role_id)).delete()


async def delete_many_roles(role_ids: Sequence[PydanticObjectId]) -> None:
    """

    :param role_ids:
    :type role_ids:
    :return:
    :rtype:
    """
    valid_oids = [PydanticObjectId(oid) for oid in role_ids]
    await Role.find({"_id": {"$in": valid_oids}}).delete()
