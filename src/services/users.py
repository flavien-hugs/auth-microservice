import logging
import os
from datetime import datetime, UTC
from typing import Sequence

from beanie import PydanticObjectId
from fastapi import status
from fastapi.responses import JSONResponse
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import EmailStr
from slugify import slugify

from src.common.helpers.caching import delete_custom_key
from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.models import Role, User
from src.schemas import CreateUser, UpdatePassword, UpdateUser
from src.shared.error_codes import RoleErrorCode, UserErrorCode
from src.shared.utils import AccountAction, password_hash
from .roles import get_one_role

logging.basicConfig(format="%(message)s", level=logging.INFO)
_log = logging.getLogger(__name__)

template_loader = PackageLoader("src", "templates")
template_env = Environment(loader=template_loader, autoescape=select_autoescape(["html", "txt"]))


async def check_if_email_exist(email: EmailStr) -> bool:
    if await User.find_one({"email": email, "is_active": True}).exists():
        raise CustomHTTException(
            code_error=UserErrorCode.USER_EMAIL_ALREADY_EXIST,
            message_error=f"User with email '{email}' already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    elif await User.find_one({"email": email, "is_active": False}).exists():
        raise CustomHTTException(
            code_error=UserErrorCode.USER_ACCOUND_DESABLE,
            message_error=f"User account with email '{email}' is disabled." f" Please request to activate the account.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    else:
        return True


async def create_user(user_data: CreateUser) -> User:
    await get_one_role(role_id=user_data.role)
    await check_if_email_exist(email=user_data.email.lower())
    user_dict = user_data.model_copy(update={"password": password_hash(user_data.password)})
    new_user = await User(**user_dict.model_dump(), is_active=True).create()
    return new_user


async def create_first_user(user_data: CreateUser) -> User:
    default_role = os.getenv("DEFAULT_ADMIN_ROLE")
    if (role := await Role.find_one({"slug": slugify(default_role)})) is None:
        raise CustomHTTException(
            code_error=RoleErrorCode.ROLE_NOT_FOUND,
            message_error=f"Role with name '{default_role}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    await check_if_email_exist(email=user_data.email.lower())
    user_dict = user_data.model_copy(update={"role": role.id, "password": password_hash(user_data.password)})
    new_user = await User(is_active=True, **user_dict.model_dump()).create()
    return new_user


async def create_admin_user():
    paylaod = {
        "email": os.getenv("DEFAULT_ADMIN_EMAIL"),
        "phonenumber": os.getenv("DEFAULT_ADMIN_PHONE"),
        "fullname": os.getenv("DEFAULT_ADMIN_FULLNAME"),
    }

    default_role = os.getenv("DEFAULT_ADMIN_ROLE")
    if (role := await Role.find_one({"slug": slugify(default_role)})) is None:
        _log.info("--> Role not found !")
        return

    if await User.find_one({"email": paylaod["email"], "is_primary": True}).exists():
        _log.info("--> Admin user alreay exist !")
        return
    else:
        password = os.getenv("DEFAULT_ADMIN_PASSWORD")
        user = User(is_active=True, role=role.id, is_primary=True, **paylaod)
        user.password = password_hash(password)
        await user.create()
        _log.info("--> Create first user successfully !")


async def get_one_user(user_id: PydanticObjectId):
    if (user := await User.get(document_id=PydanticObjectId(user_id))) is None:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_NOT_FOUND,
            message_error=f"User with '{user_id}' not found.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    role = await get_one_role(role_id=user.role)
    result = user.model_copy(update={"extras": {"role_info": role.model_dump(by_alias=True, mode="json")}})
    return result


async def update_user(user_id: PydanticObjectId, update_user: UpdateUser):
    if update_user.role:
        await get_one_role(role_id=PydanticObjectId(update_user.role))

    user = await get_one_user(user_id=user_id)
    update_data = update_user.model_dump(exclude_unset=True)

    if "attributes" in update_data:
        """
        existing_attribute_keys = set(user.attributes.keys())
        _log.info(f"Existing keys --> {existing_attribute_keys}")

        new_keys = set(update_data.get("attributes", {}).keys()) - existing_attribute_keys
        _log.info(f"New keys --> {new_keys}")

        if new_keys:
            raise CustomHTTException(
                code_error=UserErrorCode.INVALID_ATTRIBUTES,
                message_error=f"Unauthorized addition of new keys: {', '.join(new_keys)}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        """
        update_data["attributes"] = {**user.attributes, **update_data["attributes"]}

    updated_user_doc = await user.set({"updated_at": datetime.now(tz=UTC), **update_data})

    role = await get_one_role(role_id=PydanticObjectId(updated_user_doc.role))
    return user.model_copy(update={"extras": {"role_info": role.model_dump(by_alias=True)}})


async def update_user_password(user_id: PydanticObjectId, payload: UpdatePassword):
    user = await get_one_user(user_id=user_id)
    updated_user_doc = await user.set(
        {"updated_at": datetime.now(tz=UTC), "password": password_hash(payload.confirm_password)}
    )
    role = await get_one_role(role_id=PydanticObjectId(updated_user_doc.role))
    return user.model_copy(update={"extras": {"role_info": role.model_dump(by_alias=True)}})


async def delete_user_account(user_id: PydanticObjectId) -> None:
    user = await get_one_user(user_id=user_id)
    if user.is_primary:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_DELETE_PRIMARY,
            message_error="Primary user cannot be deleted.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    await user.set({"is_active": False})


async def activate_user_account(user_id: PydanticObjectId, action: AccountAction) -> JSONResponse:
    user = await get_one_user(user_id=user_id)

    is_active = True if action == AccountAction.ACTIVATE else False
    await user.set({"is_active": is_active})

    await delete_custom_key(custom_key_prefix=settings.APP_NAME + "access")
    await delete_custom_key(custom_key_prefix=settings.APP_NAME + "validate")

    message = "activated" if is_active else "deactivated"
    return JSONResponse(
        content={"message": f"User account {message} successfully."},
        status_code=status.HTTP_200_OK,
    )


async def delete_many_users(user_ids: Sequence[PydanticObjectId]) -> None:
    valid_oids = [PydanticObjectId(oid) for oid in user_ids]
    await User.find({"_id": {"$in": valid_oids}}).delete()
