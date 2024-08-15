from typing import Set

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Query, Request, Security
from starlette import status

from src.middleware import AuthorizedHTTPBearer
from src.models import User
from src.schemas import ChangePassword, LoginUser, RequestChangePassword, UserBaseSchema
from src.services import auth
from src.config import enable_endpoint


auth_router = APIRouter(prefix="", tags=["AUTH"], redirect_slashes=False)


@auth_router.post("/login", summary="Login User", status_code=status.HTTP_200_OK)
async def login(payload: LoginUser = Body(...)):
    return await auth.login(payload)


@auth_router.get(
    "/logout", dependencies=[Security(AuthorizedHTTPBearer)], summary="Logout User", status_code=status.HTTP_200_OK
)
async def logout(request: Request):
    return await auth.logout(request)


@auth_router.get(
    "/check-access",
    summary="Check user access",
    status_code=status.HTTP_200_OK,
)
async def check_access(
    token: str = Security(AuthorizedHTTPBearer),
    permission: Set[str] = Query(..., title="Permission to check"),
):
    return await auth.check_access(token=token, permission=permission)


@auth_router.get(
    "/check-validate-access-token",
    summary="Check validate access token",
    status_code=status.HTTP_200_OK,
)
async def check_validate_access_token(token: str):
    return await auth.validate_access_token(token=token)


@auth_router.put("/change-password/{id}", summary="Set up a password for the user.", status_code=status.HTTP_200_OK)
async def change_password(id: str, payload: ChangePassword = Body(...)):
    return await auth.change_password(user_id=PydanticObjectId(id), change_password=payload)


@auth_router.post("/request-password-reset", summary="Request a password reset.", status_code=status.HTTP_200_OK)
async def request_password_reset(background: BackgroundTasks, payload: RequestChangePassword = Body(...)):
    return await auth.request_password_reset(background=background, email=payload.email)


@auth_router.post("/reset-password-completed", summary="Request a password reset.", status_code=status.HTTP_200_OK)
async def reset_password_completed(
    background: BackgroundTasks,
    token: str = Query(..., alias="token", description="Reset password token"),
    payload: ChangePassword = Body(...),
):
    return await auth.reset_password_completed(background=background, reset_passwoord_token=token, new_password=payload)


if bool(enable_endpoint.SHOW_REQUEST_CREATE_ACCOUNT_ENDPOINT):

    @auth_router.post(
        "/request-create-account",
        status_code=status.HTTP_201_CREATED,
        summary="Request create account",
        description="Request create account and receive e-mail to active account.",
    )
    async def request_create_account(background: BackgroundTasks, payload: RequestChangePassword = Body(...)):
        return await auth.request_create_account_with_send_email(background=background, email=payload.email)


if bool(enable_endpoint.SHOW_CREATE_NEW_ACCOUNT_ENDPOINT):

    @auth_router.post(
        "/create-new-account",
        response_model=User,
        response_model_exclude={"password"},
        status_code=status.HTTP_200_OK,
        summary="Create new account",
        description="Create new account and receive e-mail to active account.",
    )
    async def create_new_account(token: str, background: BackgroundTasks, payload: UserBaseSchema = Body(...)):
        return await auth.create_new_account_with_send_email(token=token, user_data=payload, background=background)
