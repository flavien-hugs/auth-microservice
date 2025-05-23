import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from fastapi_pagination import add_pagination
from httpx import AsyncClient
from slugify import slugify
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.common.config import shutdown_db_client, startup_db_client
from src.common.config.setup_permission import load_app_description, load_app_permissions
from src.common.helpers.caching import init_redis_cache
from src.common.helpers.error_codes import AppErrorCode
from src.common.helpers.exception import setup_exception_handlers
from src.config import settings
from src.models import Params, Role, User
from src.routers import auth_router, param_router, perm_router, role_router, user_router
from src.services import roles, users
from src.shared import blacklist_token

__version__ = "0.1.0"

BASE_URL = slugify(settings.APP_NAME)


class State(TypedDict):
    client: AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    await startup_db_client(
        app=app, mongodb_uri=settings.MONGODB_URI, database_name=settings.MONGO_DB, document_models=[User, Role, Params]
    )

    await load_app_description(mongodb_client=app.mongo_db_client)
    await load_app_permissions(mongodb_client=app.mongo_db_client)

    await roles.create_admin_role()
    await users.create_admin_user()

    blacklist_token.init_blacklist_token_file()

    await init_redis_cache(app_name=BASE_URL, cache_db_url=settings.CACHE_DB_URL)

    yield
    await shutdown_db_client(app=app)


app: FastAPI = FastAPI(
    lifespan=lifespan,
    version=__version__,
    title=f"{settings.APP_TITLE} API Service",
    docs_url="/auth/docs",
    openapi_url="/auth/openapi.json",
    redirect_slashes=False,
    root_path_in_servers=False,
)


@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse(url="/auth/docs")


@app.get("/@ping", tags=["DEFAULT"], summary="Check if server is available")
async def ping():
    return {"message": "pong !"}


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(param_router)
app.include_router(perm_router)
add_pagination(app)
setup_exception_handlers(app)

# Compress responses larger than 1000 bytes
app.add_middleware(GZipMiddleware, minimum_size=int(settings.COMPRESS_MIN_SIZE))


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
