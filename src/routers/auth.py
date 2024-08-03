from fastapi import APIRouter, Body, Request, Security, status

from src.dependences import AuthorizeHTTPBearer
from src.schemas import LoginUser
from src.services import auth

auth_router = APIRouter(prefix="", tags=["AUTH"], redirect_slashes=False)


@auth_router.post("/login", summary="Login User", status_code=status.HTTP_200_OK)
async def login(payload: LoginUser = Body(...)):
    return await auth.login(payload)


@auth_router.get(
    "/logout", dependencies=[Security(AuthorizeHTTPBearer)], summary="Logout User", status_code=status.HTTP_200_OK
)
async def logout(request: Request):
    return await auth.logout(request)
