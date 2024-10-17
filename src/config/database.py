import logging
from typing import List, Type

from beanie import Document, init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from src.common.helpers.mongodb import mongodb_client

from .settings import get_settings

logging.basicConfig(format="%(message)s", level=logging.INFO)
_log = logging.getLogger(__name__)


async def startup_db(app: FastAPI, models: List[Type[Document]]) -> None:
    settings = get_settings()
    client = await mongodb_client(settings.MONGODB_URI)
    app.mongo_db_client = client

    db = client[settings.MONGO_DB]

    await init_beanie(database=db, document_models=models, multiprocessing_mode=True)
    app.state.fs = AsyncIOMotorGridFSBucket(database=db, bucket_name=settings.MONGO_FS_BUCKET_NAME)
    _log.info("--> Database init successfully !")


async def shutdown_db(app: FastAPI):
    app.mongo_db_client.close()
    _log.info("--> Database closed successfully !")
