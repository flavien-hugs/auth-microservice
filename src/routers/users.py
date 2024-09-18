from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, Depends, Query, Request, status
from fastapi_pagination import paginate
from pymongo import ASCENDING, DESCENDING

from src.middleware import AuthorizedHTTPBearer, CheckPermissionsHandler
from src.models import User, UserOut
from src.schemas import CreateUser, UpdateUser
from src.services import roles, users
from src.shared.utils import customize_page, SortEnum

user_router = APIRouter(prefix="/users", tags=["USERS"], redirect_slashes=False)


@user_router.post(
    "",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-create-user"})),
    ],
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
async def create_user(request: Request, payload: CreateUser = Body(...)):
    if request.url.path.endswith("/add"):
        return await users.create_first_user(payload)
    else:
        return await users.create_user(payload)


@user_router.get(
    "",
    response_model=customize_page(User),
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-user"})),
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
    users = await User.find(search, sort=[("created_at", sorted)]).to_list()

    return paginate(
        [
            {
                **user.model_dump(
                    by_alias=True,
                    exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
                ),
                "extra": {"role_info": await roles.get_one_role(role_id=PydanticObjectId(user.role))},
            }
            for user in users
        ]
    )


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
async def get_user(id: PydanticObjectId):
    return await users.get_one_user(user_id=PydanticObjectId(id))


@user_router.patch(
    "/{id}",
    response_model=User,
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-update-user"})),
    ],
    response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Update user information",
    status_code=status.HTTP_200_OK,
)
async def update_user(id: PydanticObjectId, payload: UpdateUser = Body(...)):
    return await users.update_user(user_id=PydanticObjectId(id), update_user=payload)


@user_router.delete(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-delete-user"})),
    ],
    summary="Delete one user",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(id: PydanticObjectId):
    return await users.delete_user(user_id=PydanticObjectId(id))
