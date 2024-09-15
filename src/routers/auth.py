from typing import Optional, Set

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Query, Request, Security, status

from src.config import enable_endpoint, settings
from src.middleware import AuthorizedHTTPBearer
from src.models import User
from src.schemas import (
    ChangePassword,
    EmailModelMixin,
    LoginUser,
    PhonenumberModel,
    RequestChangePassword,
    UserBaseSchema,
    VerifyOTP,
)
from src.services import auth

auth_router = APIRouter(prefix="", tags=["AUTH"], redirect_slashes=False)


@auth_router.post("/signup", summary="Signup", status_code=status.HTTP_201_CREATED)
async def register(background: BackgroundTasks, payload: RequestChangePassword = Body(...)):
    if settings.REGISTER_WITH_EMAIL:
        return await auth.signup_with_email(background=background, email=payload.email)
    else:
        return await auth.signup_with_phonenumber(background, payload)


if bool(settings.REGISTER_WITH_EMAIL):

    @auth_router.post(
        "/complete-registration",
        response_model=User,
        response_model_exclude={"password"},
        status_code=status.HTTP_200_OK,
        summary="Complete registration if you are registered with an e-mail address.",
        description="Complete registration if you are registered with an e-mail address.",
    )
    async def complete_registration(token: str, background: BackgroundTasks, payload: UserBaseSchema = Body(...)):
        return await auth.complete_registration_with_email(token=token, user_data=payload, background=background)


@auth_router.post("/login", summary="Login", status_code=status.HTTP_200_OK)
async def login(payload: LoginUser = Body(...)):
    return await auth.login(payload)


if not bool(settings.REGISTER_WITH_EMAIL):

    @auth_router.post("/verify-otp", summary="Verify OTP Code", status_code=status.HTTP_200_OK)
    async def verif_otp_code(payload: VerifyOTP = Body(...)):
        return await auth.verify_otp(payload)

    @auth_router.post("/resend-otp", summary="Resend OTP Code", status_code=status.HTTP_200_OK)
    async def resend_otp_code(bg: BackgroundTasks, payload: PhonenumberModel = Body(...)):
        return await auth.resend_otp(bg, payload)


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
async def request_password_reset(background: BackgroundTasks, payload: EmailModelMixin = Body(...)):
    return await auth.request_password_reset(background=background, email=payload.email)


@auth_router.post("/reset-password-completed", summary="Request a password reset.", status_code=status.HTTP_200_OK)
async def reset_password_completed(
    background: BackgroundTasks,
    token: str = Query(..., alias="token", description="Reset password token"),
    payload: ChangePassword = Body(...),
):
    return await auth.reset_password_completed(background=background, reset_passwoord_token=token, new_password=payload)


if bool(enable_endpoint.SHOW_CHECK_USER_ATTRIBUTE_ENDPOINT):

    @auth_router.get("/check-attribute", summary="Check if user attributes exists", status_code=status.HTTP_200_OK)
    async def check_user_attributes(
        key: str = Query(...), value: str = Query(...), in_attributes: Optional[bool] = Query(default=False)
    ):
        return await auth.check_user_attribute(key=key, value=value, in_attributes=in_attributes)
