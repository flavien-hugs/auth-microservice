from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, Query, Depends, Security, status
from fastapi_pagination import paginate
from pymongo import ASCENDING, DESCENDING

from src.dependences import AuthorizeHTTPBearer, CheckPermissionsHandler
from src.models import User, UserOut
from src.schemas import CreateUser, UpdateUser
from src.services import users, roles
from src.shared.utils import customize_page, SortEnum

user_router = APIRouter(prefix="/users", tags=["USERS"], redirect_slashes=False)


@user_router.post(
    "",
    response_model=User,
    response_model_exclude={"password", "is_primary"},
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
)
async def create_user(payload: CreateUser = Body(...)):
    return await users.create_user(payload)


@user_router.get(
    "",
    response_model=customize_page(User),
    dependencies=[
        Security(AuthorizeHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions=["can-display-user"])),
    ],
    response_model_exclude={"password"},
    summary="Get all users",
    status_code=status.HTTP_200_OK,
)
async def listing_users(
    query: Optional[str] = Query(None, description="Filter by user"),
    # is_primary: bool = Query(default=False, description="Filter grant super admin"),
    is_active: bool = Query(default=False, description="Filter account is active or disable"),
    sorting: Optional[SortEnum] = Query(SortEnum.DESC, description="Order by creation date: 'asc' or 'desc"),
):
    # search = {"is_primary": is_primary}
    search = {"is_primary": False, "is_active": is_active}
    if query:
        search["$text"] = {"$search": query}

    sorted = DESCENDING if sorting == SortEnum.DESC else ASCENDING
    users = await User.find(search).sort([("created_at", sorted)]).to_list()

    return paginate(
        [
            {
                **user.model_dump(exclude={"password", "is_primary"}),
                "extra": {"role_info": await roles.get_one_role(role_id=PydanticObjectId(user.role))},
            }
            for user in users
        ]
    )


@user_router.get(
    "/{id}",
    response_model=UserOut,
    dependencies=[
        Security(AuthorizeHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions=["can-display-user"])),
    ],
    response_model_exclude={"password", "is_primary"},
    summary="Get single user",
    status_code=status.HTTP_200_OK,
)
async def get_user(id: PydanticObjectId):
    return await users.get_one_user(user_id=PydanticObjectId(id))


@user_router.patch(
    "/{id}",
    response_model=User,
    dependencies=[
        Security(AuthorizeHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions=["can-display-user", "can-update-user"])),
    ],
    response_model_exclude={"password", "is_primary"},
    summary="Update user information",
    status_code=status.HTTP_200_OK,
)
async def update_user(id: PydanticObjectId, payload: UpdateUser = Body(...)):
    return await users.update_user(user_id=PydanticObjectId(id), update_user=payload)


@user_router.delete(
    "/{id}",
    dependencies=[
        Security(AuthorizeHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions=["can-display-user", "can-delete-user"])),
    ],
    summary="Delete one user",
    status_code=status.HTTP_200_OK,
)
async def delete_user(id: PydanticObjectId):
    return await users.delete_user(user_id=PydanticObjectId(id))
