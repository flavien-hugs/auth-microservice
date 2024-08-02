from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from slugify import slugify

from src.config import settings
from src.routers import auth_router, user_router

BASE_URL = slugify(settings.APP_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pass


app: FastAPI = FastAPI(
    title=f"{settings.APP_NAME.upper()} API Service",
    summary=f"{settings.APP_TITLE}",
    docs_url=f"/{BASE_URL}/docs",
    openapi_url=f"/{BASE_URL}/openapi.json",
)

app.include_router(auth_router)
app.include_router(user_router)


@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse(url=f"/{BASE_URL}/docs")


@app.get(f"/{BASE_URL}/@ping", tags=["DEFAULT"], summary="Check if server is available")
async def ping():
    return {"message": "pong !"}
