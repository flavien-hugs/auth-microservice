from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, Depends, Query, Security, status
from fastapi_pagination import paginate
from pymongo import ASCENDING, DESCENDING

from src.middleware import AuthorizedHTTPBearer, CheckPermissionsHandler
from src.models import User, UserOut
from src.schemas import CreateUser, UpdateUser
from src.services import roles, users
from src.shared.utils import SortEnum, customize_page

user_router = APIRouter(prefix="/users", tags=["USERS"], redirect_slashes=False)


@user_router.post(
    "",
    dependencies=[
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"can-create-user"})),
    ],
    response_model=User,
    response_model_exclude={"password", "is_primary"},
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
)
async def create_user(payload: CreateUser = Body(...)):
    """
    Create a new user in the system.

    This endpoint allows an authorized user with the `can create user` permission to create a new user.
    The new user's details are provided in the request body.

    Args:
    - payload (CreateUser): The data required to create a new user, including username, email, and other attributes.

    Returns:
    - User: The newly created user object.

    Example of use:

    ```bash

    curl -X POST "http://yourapi.com/users"
    -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    -H "Content-Type: application/json"
    -d '{
        "email": "newuser@example.com",
        "fullanme": "newuser",
        "role": "5eb7cf5a86d9755df3a6c593",
        "attributes": {"key": "value"},
        "password": "securepassword",
    }'

    ```
    """
    return await users.create_user(payload)


@user_router.get(
    "",
    response_model=customize_page(User),
    dependencies=[
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"can-display-user"})),
    ],
    summary="Get all users",
    status_code=status.HTTP_200_OK,
)
async def listing_users(
    query: Optional[str] = Query(None, description="Filter by user"),
    # is_primary: bool = Query(default=False, description="Filter grant super admin"),
    is_active: bool = Query(default=True, alias="active", description="Filter account is active or disable"),
    sorting: Optional[SortEnum] = Query(
        SortEnum.DESC, alias="sort", description="Order by creation date: 'asc' or 'desc"
    ),
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
                **user.model_dump(by_alias=True, exclude={"password", "is_primary"}),
                "extra": {"role_info": await roles.get_one_role(role_id=PydanticObjectId(user.role))},
            }
            for user in users
        ]
    )


@user_router.get(
    "/{id}",
    response_model=UserOut,
    dependencies=[
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"can-display-user"})),
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
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"can-display-user", "can-update-user"})),
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
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"can-display-user", "can-delete-user"})),
    ],
    summary="Delete one user",
    status_code=status.HTTP_200_OK,
)
async def delete_user(id: PydanticObjectId):
    return await users.delete_user(user_id=PydanticObjectId(id))
