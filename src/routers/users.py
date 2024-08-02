from fastapi import APIRouter

user_router = APIRouter(
    prefix="/users",
    tags=["USERS"],
    redirect_slashes=False,
    responses={404: {"description": "Not found"}},
)


@user_router.get("")
async def create_user():
    return "create an account"
