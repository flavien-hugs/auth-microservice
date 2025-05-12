import asyncio
from typing import Optional, Set

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request, status
from fastapi_pagination.ext.beanie import paginate
from pymongo import ASCENDING, DESCENDING
from slugify import slugify

from src.common.helpers.caching import delete_custom_key
from src.common.helpers.error_codes import AppErrorCode
from src.common.helpers.exception import CustomHTTPException
from src.common.helpers.pagination import customize_page
from src.common.services.trailhub_client import send_event
from src.config import enable_endpoint, settings
from src.middleware import AuthorizedHTTPBearer, CheckPermissionsHandler
from src.models import Role
from src.schemas import RoleModel
from src.services import roles
from src.shared import API_TRAILHUB_ENDPOINT, API_VERIFY_ACCESS_TOKEN_ENDPOINT, SortEnum

service_appname_slug = slugify(settings.APP_NAME)

role_router = APIRouter(prefix="/roles", tags=["ROLES"], redirect_slashes=False)


@role_router.post(
    "/_create",
    response_model=Role,
    summary="Create role (internal)",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@role_router.post(
    "",
    dependencies=(
        [
            Depends(AuthorizedHTTPBearer),
            Depends(CheckPermissionsHandler(required_permissions={"auth:can-create-role"})),
        ]
    ),
    response_model=Role,
    summary="Create role",
    status_code=status.HTTP_201_CREATED,
)
async def create_role(request: Request, bg: BackgroundTasks, payload: RoleModel = Body(...)):
    try:
        result = await roles.create_role(role=payload)
    except HTTPException as exc:
        raise CustomHTTPException(
            code_error=AppErrorCode.REQUEST_VALIDATION_ERROR,
            message_error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc
    except Exception as exc:
        raise CustomHTTPException(
            code_error=AppErrorCode.HTTP_ERROR,
            message_error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc

    if settings.USE_TRACK_ACTIVITY_LOGS:
        await send_event(
            request=request,
            bg=bg,
            oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
            trailhub_url=API_TRAILHUB_ENDPOINT,
            source=settings.APP_NAME.lower(),
            message=f" has created a new role with the name '{payload.name}'",
            user_id=None,
        )
    return result


@role_router.get(
    "",
    response_model=customize_page(Role),
    dependencies=(
        [
            Depends(AuthorizedHTTPBearer),
            Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-role"})),
        ]
        if settings.LIST_ROLES_ENDPOINT_SECURITY_ENABLED
        else []
    ),
    summary="Get all roles",
    status_code=status.HTTP_200_OK,
)
async def listing_roles(
    query: Optional[str] = Query(None, description="Filter by role"),
    sorting: Optional[SortEnum] = Query(SortEnum.DESC, description="Order by creation date: 'asc' or 'desc"),
):
    search = {}
    if query:
        search["$text"] = {"$search": query}

    sorted = DESCENDING if sorting == SortEnum.DESC else ASCENDING
    roles = Role.find(search, sort=[("created_at", sorted)])
    return await paginate(roles)


@role_router.get(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-role"})),
    ],
    summary="Get one roles",
    status_code=status.HTTP_200_OK,
)
async def ger_role(id: PydanticObjectId):
    return await roles.get_one_role(role_id=PydanticObjectId(id))


@role_router.put(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-update-role"})),
    ],
    summary="Update role",
    status_code=status.HTTP_200_OK,
)
async def update_role(request: Request, bg: BackgroundTasks, id: PydanticObjectId, payload: RoleModel = Body(...)):
    result = await roles.update_role(role_id=PydanticObjectId(id), update_role=payload)
    if settings.USE_TRACK_ACTIVITY_LOGS:
        await send_event(
            request=request,
            bg=bg,
            oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
            trailhub_url=API_TRAILHUB_ENDPOINT,
            source=settings.APP_NAME.lower(),
            message=f" has created a new role with the name '{id}:{payload.name}'",
            user_id=None,
        )
    return result


@role_router.delete(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-delete-role"})),
    ],
    summary="Delete role",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_role(request: Request, bg: BackgroundTasks, id: PydanticObjectId):
    result = await roles.delete_role(role_id=PydanticObjectId(id))
    if settings.USE_TRACK_ACTIVITY_LOGS:
        await send_event(
            request=request,
            bg=bg,
            oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
            trailhub_url=API_TRAILHUB_ENDPOINT,
            source=settings.APP_NAME.lower(),
            message=f" has deleted the role with the name '{id}'",
            user_id=None,
        )
    return result


if bool(enable_endpoint.SHOW_MEMBERS_IN_ROLE_ENDPOINT):

    @role_router.get(
        "/{name}/members",
        dependencies=[
            Depends(AuthorizedHTTPBearer),
            Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-role"})),
        ],
        response_model=customize_page(dict),
        summary="Get role members",
        status_code=status.HTTP_200_OK,
    )
    async def get_role_members(
        name: str,
        sorting: Optional[SortEnum] = Query(SortEnum.DESC, description="Order by creation date: 'asc' or 'desc"),
    ):
        return await roles.get_users_for_role(name=name, sorting=sorting)


@role_router.patch(
    "/{id}/_assign-permissions",
    response_model=Role,
    summary="Assign permissions to role (internal)",
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
@role_router.patch(
    "/{id}/assign-permissions",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-assign-permission-role"})),
    ],
    response_model=Role,
    summary="Assign permissions to role",
    status_code=status.HTTP_200_OK,
)
async def manage_permission_to_role(request: Request, bg: BackgroundTasks, id: PydanticObjectId, payload: Set[str] = Body(...)):
    result = await roles.assign_permissions_to_role(role_id=PydanticObjectId(id), permission_codes=payload)

    await asyncio.gather(
        delete_custom_key(custom_key_prefix=settings.APP_NAME + "access"),
        delete_custom_key(custom_key_prefix=settings.APP_NAME + "validate"),
    )

    if settings.USE_TRACK_ACTIVITY_LOGS:
        await send_event(
            request=request,
            bg=bg,
            oauth_url=API_VERIFY_ACCESS_TOKEN_ENDPOINT,
            trailhub_url=API_TRAILHUB_ENDPOINT,
            source=settings.APP_NAME.lower(),
            message=f" has assigned permissions to the role with the ID '{id}'",
            user_id=None,
        )
    return result
