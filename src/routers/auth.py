from fastapi import APIRouter

auth_router = APIRouter(prefix="", tags=["AUTHENTICATION"], redirect_slashes=False)


@auth_router.get("/login")
async def login():
    return "login"
