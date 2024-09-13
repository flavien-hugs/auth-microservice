from typing import Optional, Set

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, Depends, Query, Security, status
from fastapi_pagination.ext.beanie import paginate
from pymongo import ASCENDING, DESCENDING

from src.config import enable_endpoint
from src.middleware import AuthorizedHTTPBearer, CheckPermissionsHandler
from src.models import Role
from src.schemas import RoleModel
from src.services import roles
from src.shared.utils import SortEnum, customize_page

role_router = APIRouter(prefix="/roles", tags=["ROLES"], redirect_slashes=False)


@role_router.post(
    "",
    dependencies=[
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-create-role"})),
    ],
    response_model=Role,
    summary="Create role",
    status_code=status.HTTP_201_CREATED,
)
async def create_role(payload: RoleModel = Body(...)):
    return await roles.create_role(role=payload)


@role_router.get(
    "",
    response_model=customize_page(Role),
    dependencies=[
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-role"})),
    ],
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
        Security(AuthorizedHTTPBearer),
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
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-update-role"})),
    ],
    summary="Update role",
    status_code=status.HTTP_200_OK,
)
async def update_role(id: PydanticObjectId, payload: RoleModel = Body(...)):
    return await roles.update_role(role_id=PydanticObjectId(id), update_role=payload)


@role_router.delete(
    "/{id}",
    dependencies=[
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-delete-role"})),
    ],
    summary="Delete role",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_role(id: PydanticObjectId):
    return await roles.delete_role(role_id=PydanticObjectId(id))


if bool(enable_endpoint.SHOW_MEMBERS_IN_ROLE_ENDPOINT):

    @role_router.get(
        "/{id}/members",
        dependencies=[
            Security(AuthorizedHTTPBearer),
            Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-role"})),
        ],
        response_model=customize_page(dict),
        summary="Get role members",
        status_code=status.HTTP_200_OK,
    )
    async def get_role_members(
        id: PydanticObjectId,
        sorting: Optional[SortEnum] = Query(SortEnum.DESC, description="Order by creation date: 'asc' or 'desc"),
    ):
        return await roles.get_roles_members(role_id=PydanticObjectId(id), sorting=sorting)


@role_router.patch(
    "/{id}/assign-permissions",
    dependencies=[
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-assign-permission-role"})),
    ],
    response_model=Role,
    summary="Assign permissions to role",
    status_code=status.HTTP_200_OK,
)
async def manage_permission_to_role(id: PydanticObjectId, payload: Set[str] = Body(...)):
    return await roles.assign_permissions_to_role(role_id=PydanticObjectId(id), permission_codes=payload)
