from typing import Set

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Query, Request, Security, status

from src.middleware import AuthorizedHTTPBearer
from src.schemas import ChangePassword, LoginUser, RequestChangePassword
from src.services import auth

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
    return await auth.check_validate_access_token(token=token)


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
