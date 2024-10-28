from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, Depends, File, Path, Query, Request, status, UploadFile
from fastapi_pagination.async_paginator import paginate
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pymongo import ASCENDING, DESCENDING

from src.config import settings
from src.middleware import AuthorizedHTTPBearer, CheckPermissionsHandler
from src.models import User, UserOut
from src.schemas import CreateUser, UpdateUser
from src.services import files, roles, users
from src.shared.utils import customize_page, get_fs, SortEnum

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
    response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Get all users",
    status_code=status.HTTP_200_OK,
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
    users = [
        user.model_dump(
            by_alias=True,
            mode="json",
            exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
        )
        for user in users_list
        if user.is_primary is False
    ]
    return await paginate(users)


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
    "/_i_{id}",
    response_model=UserOut,
    response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
    summary="Get single user (internal)",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_user(id: PydanticObjectId):
    user = await users.get_one_user(user_id=PydanticObjectId(id))
    role = await roles.get_one_role(role_id=user.role)
    result = user.model_copy(update={"extras": {"role_info": role.model_dump(by_alias=True, mode="json")}})
    return result


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


user_router.tags = ["USERS: PICTURES"]
user_router.prefix = "/pictures"


@user_router.put(
    "",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-update-user"})),
    ],
    summary="Upload user picture",
    status_code=status.HTTP_200_OK,
)
async def upload(
    request: Request,
    user_id: PydanticObjectId,
    file: UploadFile = File(...),
    description: Optional[str] = Body(None, description="Description of the file"),
    fs: AsyncIOMotorGridFSBucket = Depends(get_fs),
):
    result = await files.upload_file(request=request, user_id=user_id, description=description, file=file, fs=fs)
    return result


@user_router.get(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-read-user"})),
    ],
    summary="Download user picture",
    status_code=status.HTTP_200_OK,
)
@user_router.get(
    "/{id}/view",
    summary="Show user picture",
    status_code=status.HTTP_200_OK,
)
async def download(
    request: Request, id: str = Path(..., description="File ID"), fs: AsyncIOMotorGridFSBucket = Depends(get_fs)
):
    if request.url.path.endswith("/show"):
        return await files.get_file(id=id, fs=fs)
    else:
        return await files.download_file(id=id, fs=fs)


@user_router.delete(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-update-user"})),
    ],
    summary="Delete user picture",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_picture(
    user_id: PydanticObjectId,
    id: str = Path(..., description="File ID"),
    fs: AsyncIOMotorGridFSBucket = Depends(get_fs),
):
    return await files.delete_file(id=id, user_id=user_id, fs=fs)
