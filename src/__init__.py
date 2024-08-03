from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi_pagination import add_pagination
from slugify import slugify

from src.common.helpers.appdesc import load_app_description, load_permissions
from src.common.helpers.exceptions import setup_exception_handlers
from src.config import settings, shutdown_db, startup_db
from src.models import Role, User
from src.routers import auth_router, perm_router, role_router, user_router

BASE_URL = slugify(settings.APP_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_db(app=app, models=[User, Role])

    await load_app_description(mongodb_client=app.mongo_db_client)
    await load_permissions(mongodb_client=app.mongo_db_client)

    yield
    await shutdown_db(app=app)


app: FastAPI = FastAPI(
    lifespan=lifespan,
    title=f"{settings.APP_NAME.upper()} API Service",
    summary=f"{settings.APP_TITLE}",
    docs_url=f"/{BASE_URL}/docs",
    openapi_url=f"/{BASE_URL}/openapi.json",
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(perm_router)
add_pagination(app)

setup_exception_handlers(app)


@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse(url=f"/{BASE_URL}/docs")


@app.get(f"/{BASE_URL}/@ping", tags=["DEFAULT"], summary="Check if server is available")
async def ping():
    return {"message": "pong !"}
