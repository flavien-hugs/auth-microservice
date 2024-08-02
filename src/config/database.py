from typing import List, Type

from beanie import Document, init_beanie
from fastapi import FastAPI

from src.common.helpers.mongodb import mongodb_client
from .settings import get_settings


async def startup_db(app: FastAPI, models: List[Type[Document]]):
    settings = get_settings()
    client = await mongodb_client(settings.MONGODB_URI)
    app.mongo_db_client = client

    await init_beanie(
        database=client[settings.MONGO_DB],
        document_models=models,
    )


async def shutdown_db(app: FastAPI):
    app.mongo_db_client.close()
