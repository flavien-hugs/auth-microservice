import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import RedirectResponse
from fastapi_pagination import add_pagination
from httpx import AsyncClient
from slugify import slugify
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.common.helpers.appdesc import load_app_description, load_permissions
from src.common.helpers.error_codes import AppErrorCode
from src.common.helpers.exceptions import setup_exception_handlers
from src.config import settings, shutdown_db, startup_db
from src.models import Role, User
from src.routers import auth_router, perm_router, role_router, user_router
from src.services import roles, users

BASE_URL = slugify(settings.APP_NAME)


class State(TypedDict):
    client: AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    await startup_db(app=app, models=[User, Role])

    await load_app_description(mongodb_client=app.mongo_db_client)
    await load_permissions(mongodb_client=app.mongo_db_client)

    await roles.create_first_role()
    await users.create_first_user()

    yield
    await shutdown_db(app=app)


app: FastAPI = FastAPI(
    lifespan=lifespan,
    title=f"{settings.APP_NAME.upper()} API Service",
    summary=f"{settings.APP_TITLE}",
    docs_url=f"/{BASE_URL}/docs",
    openapi_url=f"/{BASE_URL}/openapi.json",
    root_path_in_servers=False,
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(perm_router)
add_pagination(app)

setup_exception_handlers(app)


@app.exception_handler(HTTPException)
def authentication_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(
                {
                    "code_error": AppErrorCode.AUTH_NOT_AUTHENTICATED,
                    "message_error": str(exc.detail),
                }
            ),
        )


@app.middleware("http")
async def add_version_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Version"] = os.environ.get("API_VERSION", "v.0.1")
    return response


@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse(url=f"/{BASE_URL}/docs")


@app.get(f"/{BASE_URL}/@ping", tags=["DEFAULT"], summary="Check if server is available")
async def ping():
    return {"message": "pong !"}
