from fastapi import APIRouter

auth_router = APIRouter(
    prefix="",
    tags=["AUTHENTICATION"],
    redirect_slashes=False,
    responses={404: {"description": "Not found"}},
)


@auth_router.get("/login")
async def login():
    return "login"
