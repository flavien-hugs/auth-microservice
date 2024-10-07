from typing import Optional, Set

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, Request, status
from fastapi_cache.decorator import cache

from src.config import enable_endpoint, settings
from src.middleware import AuthorizedHTTPBearer
from src.models import User
from src.schemas import (
    ChangePassword,
    EmailModelMixin,
    LoginUser,
    PhonenumberModel,
    RequestChangePassword,
    SendEmailMessage,
    SendSmsMessage,
    UserBaseSchema,
    VerifyOTP,
)
from src.services import auth
from src.shared import mail_service, sms_service
from src.shared.utils import custom_key_builder

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
async def login(task: BackgroundTasks, request: Request, payload: LoginUser = Body(...)):
    return await auth.login(task=task, request=request, payload=payload)


if not bool(settings.REGISTER_WITH_EMAIL):

    @auth_router.post(
        "/verify-otp",
        response_model_exclude={"password", "is_primary", "attributes.otp_secret", "attributes.otp_created_at"},
        summary="Verify OTP Code",
        status_code=status.HTTP_200_OK,
    )
    async def verif_otp_code(payload: VerifyOTP = Body(...)):
        return await auth.verify_otp(payload)

    @auth_router.post("/resend-otp", summary="Resend OTP Code", status_code=status.HTTP_200_OK)
    async def resend_otp_code(bg: BackgroundTasks, payload: PhonenumberModel = Body(...)):
        return await auth.resend_otp(bg, payload)


@auth_router.get(
    "/logout", dependencies=[Depends(AuthorizedHTTPBearer)], summary="Logout User", status_code=status.HTTP_200_OK
)
async def logout(request: Request):
    return await auth.logout(request)


@auth_router.get(
    "/check-access",
    summary="Check user access",
    status_code=status.HTTP_200_OK,
)
@cache(expire=settings.EXPIRE_CACHE, key_builder=custom_key_builder)  # noqa
async def check_access(
    token: str = Depends(AuthorizedHTTPBearer),
    permission: Set[str] = Query(..., title="Permission to check"),
):
    return await auth.check_access(token=token, permission=permission)


@auth_router.get(
    "/check-validate-access-token",
    summary="Check validate access token",
    status_code=status.HTTP_200_OK,
)
@cache(expire=settings.EXPIRE_CACHE, key_builder=custom_key_builder)  # noqa
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


auth_router.tags = ["SEND MESSAGE"]
auth_router.prefix = "/send"


@auth_router.post("-sms", summary="Send a message", status_code=status.HTTP_200_OK, include_in_schema=False)
async def send_sms(background: BackgroundTasks, payload: SendSmsMessage = Body(...)):
    phone = payload.phone_number.replace("+", "")
    await sms_service.send_sms(background, recipient=phone, message=payload.message)
    return {"message": "SMS sent successfully."}


@auth_router.post("-email", summary="Send a e-mail", status_code=status.HTTP_200_OK, include_in_schema=False)
async def send_email(background: BackgroundTasks, payload: SendEmailMessage = Body(...)):
    mail_service.send_email_background(
        background, receiver_email=payload.recipients, subject=payload.subject, body=payload.message
    )
    return {"message": "E-mail sent successfully."}
