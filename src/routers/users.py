from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, Request, status
from fastapi_pagination.async_paginator import paginate
from pymongo import ASCENDING, DESCENDING

from src.common.helpers.pagination import customize_page
from src.common.services.trailhub_client import send_event
from src.config import settings
from src.middleware import AuthorizedHTTPBearer, CheckPermissionsHandler, CheckUserAccessHandler
from src.models import User, UserOut
from src.schemas import CreateUser, UpdatePassword, UpdateUser
from src.services import roles, users
from src.shared import API_TRAILHUB_ENDPOINT, API_VERIFY_ACCESS_TOKEN_ENDPOINT
from src.shared.utils import AccountAction, SortEnum

user_router = APIRouter(prefix="/users", tags=["USERS"], redirect_slashes=False)


@user_router.post(
    "",
    dependencies=(
        [
            Depends(AuthorizedHTTPBearer),
            Depends(CheckPermissionsHandler(required_permissions={"auth:can-create-user"})),
        ]
        if settings.REGISTER_USER_ENDPOINT_SECURITY_ENABLED
        else []
    ),
    response_model=User,
    response_model_exclude={"password", "is_primary"},
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
)
@user_router.post(
    "/add",
    response_model=User,
    response_model_exclude={"password", "is_primary"},
    status_code=status.HTTP_201_CREATED,
    summary="Add new user",
    include_in_schema=False,
)
async def create_user(request: Request, bg: BackgroundTasks, payload: CreateUser = Body(...)):
    if request.url.path.endswith("/add"):
        result = await users.create_first_user(payload)
        if settings.USE_TRACK_ACTIVITY_LOGS:
            await send_event(
                request=request,
                bg=bg,
                oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
                trailhub_url=API_TRAILHUB_ENDPOINT,
                source=settings.APP_NAME.lower(),
                message=f" has created a new user with the email '{payload.email}'",
                user_id=None,
            )
        return result
    else:
        result = await users.create_user(payload)
        if settings.USE_TRACK_ACTIVITY_LOGS:
            await send_event(
                request=request,
                bg=bg,
                oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
                trailhub_url=API_TRAILHUB_ENDPOINT,
                source=settings.APP_NAME.lower(),
                message=f" has created a new user with the email '{payload.email}'",
                user_id=None,
            )
        return result


@user_router.get(
    "",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-user"})),
    ],
    response_model=customize_page(UserOut),
    response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Get all users",
    status_code=status.HTTP_200_OK,
)
@user_router.get(
    "/_read",
    response_model=customize_page(UserOut),
    response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Get all users (internal)",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def listing_users(
    query: Optional[str] = Query(None, description="Filter by user"),
    # is_primary: bool = Query(default=False, description="Filter grant super admin"),
    is_active: Optional[bool] = Query(default=None, alias="active", description="Filter account is active or disable"),
    sorting: Optional[SortEnum] = Query(
        SortEnum.DESC, alias="sort", description="Order by creation date: 'asc' or 'desc"
    ),
):
    # search = {"is_primary": is_primary}
    search = {}
    if is_active:
        search.update({"is_active": is_active, "is_primary": False})
    if query:
        search["$or"] = [
            {"email": {"$regex": query, "$options": "i"}},
            {"fullname": {"$regex": query, "$options": "i"}},
            {
                "$expr": {
                    "$gt": [
                        {
                            "$indexOfArray": [
                                {
                                    "$map": {
                                        "input": {"$objectToArray": "$attributes"},
                                        "as": "attr",
                                        "in": {"$toLower": "$$attr.v"},
                                    }
                                },
                                {"$toLower": query},
                            ]
                        },
                        -1,
                    ]
                }
            },
        ]

    sorted = DESCENDING if sorting == SortEnum.DESC else ASCENDING
    users_list = await User.find(search, sort=[("created_at", sorted)]).to_list()
    users_output = []
    for user in users_list:
        if user.is_primary is False:
            role_data = await roles.get_one_role(role_id=user.role)
            users_output.append(
                UserOut(
                    **user.model_dump(
                        by_alias=True,
                        mode="json",
                        exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
                    ),
                    extras={"role_info": {"name": role_data.name, "slug": role_data.slug} if role_data else None},
                )
            )
    return await paginate(users_output)


@user_router.get(
    "/{id}",
    response_model=UserOut,
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-user"})),
    ],
    response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Get single user",
    status_code=status.HTTP_200_OK,
)
@user_router.get(
    "/{id}/_read",
    response_model=UserOut,
    response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Get single user (internal)",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_user(id: PydanticObjectId):
    user_data = await users.get_one_user(user_id=PydanticObjectId(id))
    role_data = await roles.get_one_role(role_id=user_data.role)
    result = UserOut(
        **user_data.model_dump(
            by_alias=True,
            mode="json",
            exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
        ),
        extras={"role_info": {"name": role_data.name, "slug": role_data.slug} if role_data else None},
    )
    return result


@user_router.get(
    "/{id}/attributes",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-user"})),
    ],
    response_model_exclude={"is_admin", "password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Get single user attributes only",
    status_code=status.HTTP_200_OK,
)
async def get_user_attributes(id: PydanticObjectId):
    user_data = await users.get_one_user(user_id=PydanticObjectId(id))
    return user_data.attributes


@user_router.patch(
    "/{id}",
    response_model=User,
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckUserAccessHandler(key="id")),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-update-user"})),
    ],
    response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Update user information",
    status_code=status.HTTP_200_OK,
)
async def update_user(request: Request, bg: BackgroundTasks, id: PydanticObjectId, payload: UpdateUser = Body(...)):
    # TODO: Ajouter une vérification pour voir si l'utilisateur met à jour son propre compte.
    result = await users.update_user(user_id=PydanticObjectId(id), update_user=payload)
    if settings.USE_TRACK_ACTIVITY_LOGS:
        await send_event(
            request=request,
            bg=bg,
            oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
            trailhub_url=API_TRAILHUB_ENDPOINT,
            source=settings.APP_NAME.lower(),
            message=f" has updated the user information '{id}:{payload.fullname}'",
            user_id=str(id),
        )
    return result


@user_router.put(
    "/{id}/update-password",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckUserAccessHandler(key="id")),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-update-user"})),
    ],
)
async def update_user_password(
    request: Request, bg: BackgroundTasks, id: PydanticObjectId, payload: UpdatePassword = Body(...)
):
    # TODO: Ajouter une vérification pour voir si l'utilisateur met à jour son propre compte.
    result = await users.update_user_password(user_id=PydanticObjectId(id), payload=payload)
    if settings.USE_TRACK_ACTIVITY_LOGS:
        await send_event(
            request=request,
            bg=bg,
            oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
            trailhub_url=API_TRAILHUB_ENDPOINT,
            source=settings.APP_NAME.lower(),
            message=f" has updated the password of the user with the email '{id}'",
            user_id=str(id),
        )
    return result


@user_router.put(
    "/{id}/activate",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckUserAccessHandler(key="id")),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-update-user"})),
    ],
    summary="Activate or deactivate user account",
    status_code=status.HTTP_202_ACCEPTED,
)
async def activate_user_account(request: Request, bg: BackgroundTasks, id: PydanticObjectId, action: AccountAction):
    # TODO: Ajouter une vérification pour voir si l'utilisateur met à jour son propre compte.

    result = await users.activate_user_account(user_id=PydanticObjectId(id), action=action)
    if settings.USE_TRACK_ACTIVITY_LOGS:
        await send_event(
            request=request,
            bg=bg,
            oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
            trailhub_url=API_TRAILHUB_ENDPOINT,
            source=settings.APP_NAME.lower(),
            message=f" has {'activate' if action == AccountAction.ACTIVATE else 'deactivate'} the account user '{id}'",
            user_id=str(id),
        )
    return result


@user_router.delete(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckUserAccessHandler(key="id")),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-delete-user"})),
    ],
    summary="Delete one user",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(request: Request, bg: BackgroundTasks, id: PydanticObjectId):
    result = await users.delete_user_account(user_id=PydanticObjectId(id))
    if settings.USE_TRACK_ACTIVITY_LOGS:
        await send_event(
            request=request,
            bg=bg,
            oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
            trailhub_url=API_TRAILHUB_ENDPOINT,
            source=settings.APP_NAME.lower(),
            message=f" has deleted the user with the email '{id}'",
            user_id=str(id),
        )
    return result
