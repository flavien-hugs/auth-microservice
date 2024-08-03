from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, Query, Security, status
from fastapi_pagination import paginate
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from src.common.helpers.exceptions import CustomHTTException
from src.dependences import AuthorizeHTTPBearer
from src.models import User
from src.schemas import CreateUser, UpdateUser
from src.services import users
from src.shared.error_codes import UserErrorCode
from src.shared.utils import customize_page, SortEnum

user_router = APIRouter(prefix="/users", tags=["USERS"], redirect_slashes=False)


@user_router.post(
    "",
    response_model=User,
    response_model_exclude={"password"},
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
)
async def create_user(payload: CreateUser = Body(...)):
    try:
        result = await users.create_user(payload)
    except DuplicateKeyError as err:
        raise CustomHTTException(
            code_error=UserErrorCode.USER_EMAIL_ALREADY_EXIST, message_error=str(err), status_code=status.HTTP_400_BAD_REQUEST
        ) from err
    return result


@user_router.get(
    "",
    response_model=customize_page(User),
    dependencies=[Security(AuthorizeHTTPBearer)],
    response_model_exclude={"password"},
    summary="Get all users",
    status_code=status.HTTP_200_OK,
)
async def listing_users(
    query: Optional[str] = Query(None, description="Filter by user"),
    sorting: Optional[SortEnum] = Query(SortEnum.DESC, description="Order by creation date: 'asc' or 'desc"),
):
    search = {}
    if query:
        search["$text"] = {"$search": query}

    sorted = DESCENDING if sorting == SortEnum.DESC else ASCENDING
    users = await User.find(search).sort([("created_at", sorted)]).to_list()
    return paginate(users)


@user_router.get(
    "/{id}",
    response_model=User,
    dependencies=[Security(AuthorizeHTTPBearer)],
    response_model_exclude={"password"},
    summary="Get single user",
    status_code=status.HTTP_200_OK,
)
async def get_user(id: PydanticObjectId):
    return await users.get_one_user(user_id=PydanticObjectId(id))


@user_router.patch(
    "/{id}",
    response_model=User,
    dependencies=[Security(AuthorizeHTTPBearer)],
    response_model_exclude={"password"},
    summary="Update user information",
    status_code=status.HTTP_200_OK,
)
async def update_user(id: PydanticObjectId, payload: UpdateUser = Body(...)):
    return await users.update_user(user_id=PydanticObjectId(id), update_user=payload)


@user_router.delete(
    "/{id}",
    dependencies=[Security(AuthorizeHTTPBearer)],
    summary="Delete one user",
    status_code=status.HTTP_200_OK,
)
async def delete_user(id: PydanticObjectId):
    return await users.delete_user(user_id=PydanticObjectId(id))
