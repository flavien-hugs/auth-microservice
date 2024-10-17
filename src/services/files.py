from datetime import datetime, UTC
from io import BytesIO
from pathlib import Path
from typing import Optional

from beanie import PydanticObjectId
from fastapi import Depends, File, Request, status, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from slugify import slugify

from src.common.helpers.exceptions import CustomHTTException
from src.config import settings
from src.schemas import Metadata
from src.shared.error_codes import UserErrorCode
from src.shared.utils import get_fs
from .users import get_one_user

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


async def upload_file(
    request: Request,
    user_id: PydanticObjectId,
    description: Optional[str],
    file: UploadFile = File(...),
    fs: AsyncIOMotorGridFSBucket = Depends(get_fs),
):
    user = await get_one_user(user_id=user_id)

    try:
        contents = await file.read()

        filepath = Path(file.filename)
        original_filename = filepath.stem
        file_suffixes = filepath.suffixes

        if not file_suffixes:
            raise CustomHTTException(
                code_error=UserErrorCode.UPLOAD_FILE_ERROR,
                message_error="File extension not allowed",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        file_extension = "".join(file_suffixes).lower()

        if file_extension not in ALLOWED_EXTENSIONS:
            raise CustomHTTException(
                code_error=UserErrorCode.UPLOAD_FILE_ERROR,
                message_error="File extension not allowed",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d%H%M")
        sanitized_filename = slugify(original_filename)
        unique_filename = f"{sanitized_filename}-{timestamp}{file_extension}"

        file_id = await fs.upload_from_stream(
            unique_filename, BytesIO(contents), metadata={"content_type": file.content_type}
        )

        metadata_doc = Metadata(
            file_id=str(file_id), filename=unique_filename, content_type=file.content_type, description=description
        )
        await user.set({"attributes": {**user.attributes, "picture": metadata_doc}})

        base_url = str(request.base_url) if request else f"http://127.0.0.1:{settings.APP_DEFAULT_PORT}"
        download_url = f"{base_url}pictures/{file_id}"

        response_data = jsonable_encoder(
            {"filename": str(unique_filename), "file_id": str(file_id), "download_url": download_url}
        )
    except Exception as e:
        raise CustomHTTException(
            code_error=UserErrorCode.UPLOAD_FILE_ERROR,
            message_error=f"Error while uploading file: {e}",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from e

    return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)


async def _get_stream_file(id: str, fs: AsyncIOMotorGridFSBucket = Depends(get_fs)):
    try:
        oid = PydanticObjectId(id)
    except Exception as e:
        raise CustomHTTException(
            code_error=UserErrorCode.UPLOAD_FILE_ERROR,
            message_error=f"Error while downloading file: {e}",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from e

    cursor = fs.find({"_id": oid})
    files = await cursor.to_list(length=1)

    if not files:
        raise CustomHTTException(
            code_error=UserErrorCode.UPLOAD_FILE_ERROR,
            message_error="File not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    file = files[0]

    if not file:
        raise CustomHTTException(
            code_error=UserErrorCode.UPLOAD_FILE_ERROR,
            message_error="File not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        stream = await fs.open_download_stream(file_id=oid)
    except Exception as e:
        raise CustomHTTException(
            code_error=UserErrorCode.UPLOAD_FILE_ERROR,
            message_error=f"Error while reading file: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e

    return stream


async def download_file(id: str, fs: AsyncIOMotorGridFSBucket = Depends(get_fs)):
    stream = await _get_stream_file(id=id, fs=fs)

    async def file_iterator():
        while True:
            chunk = await stream.readchunk()
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        content=file_iterator(),
        media_type=stream.metadata.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{stream.filename}"',
            "Content-Length": str(stream.length),
        },
    )


async def get_file(id: str, fs: AsyncIOMotorGridFSBucket = Depends(get_fs)):
    stream = await _get_stream_file(id=id, fs=fs)

    async def file_iterator():
        while True:
            chunk = await stream.readchunk()
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        content=file_iterator(),
        media_type=stream.metadata.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'inline; filename="{stream.filename}"',
            "Content-Length": str(stream.length),
        },
    )


async def delete_file(id: str, user_id: PydanticObjectId, fs: AsyncIOMotorGridFSBucket = Depends(get_fs)):
    try:
        oid = PydanticObjectId(id)
    except Exception as e:
        raise CustomHTTException(
            code_error=UserErrorCode.UPLOAD_FILE_ERROR,
            message_error=f"Error while deleting file: {e}",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from e

    cursor = fs.find({"_id": oid})
    files = await cursor.to_list(length=1)
    file = files[0]

    if not file:
        raise CustomHTTException(
            code_error=UserErrorCode.UPLOAD_FILE_ERROR,
            message_error="File not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    await fs.delete(file_id=oid)

    user = await get_one_user(user_id=user_id)
    await user.set({"attributes": {**user.attributes, "picture": None}})

    return JSONResponse(content={"message": "File deleted successfully"}, status_code=status.HTTP_200_OK)
