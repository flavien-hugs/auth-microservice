from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, Depends, Query, status
from fastapi_pagination.ext.beanie import paginate
from pymongo import ASCENDING, DESCENDING

from src.common.helpers.pagination import customize_page
from src.config import settings
from src.middleware import AuthorizedHTTPBearer, CheckPermissionsHandler
from src.models import Params
from src.schemas import FilterParams, ParamsModel
from src.services import params
from src.shared.utils import SortEnum

param_router = APIRouter(prefix="/parameters", tags=["PARAMETERS"])


@param_router.post(
    "",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-create-parameters"})),
    ],
    response_model=Params,
    summary="Add new parameter",
    status_code=status.HTTP_201_CREATED,
)
async def create(payload: ParamsModel = Body(...)):
    return await params.create(payload)


@param_router.get(
    "",
    dependencies=(
        [
            Depends(AuthorizedHTTPBearer),
            Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-parameters"})),
        ]
        if settings.LIST_PARAMETERS_ENDPOINT_SECURITY_ENABLED
        else []
    ),
    summary="Get all parameters",
    response_model=customize_page(Params),
    status_code=status.HTTP_200_OK,
)
async def all(
    filter: FilterParams = Depends(FilterParams),
    sort: Optional[SortEnum] = Query(default=SortEnum.DESC, alias="sort", description="Sort by 'asc' or 'desc"),
):
    search = {}

    if filter.type:
        search["type"] = filter.type.upper()

    if filter.name:
        search["name"] = {"$regex": filter.name, "$options": "i"}

    sorted = DESCENDING if sort == SortEnum.DESC else ASCENDING
    params = Params.find(search, sort=[("created_at", sorted)])
    return await paginate(params)


@param_router.get(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-display-parameters"})),
    ],
    response_model=Params,
    summary="Get one params",
    status_code=status.HTTP_200_OK,
)
async def read(id: PydanticObjectId):
    return await params.get_one(id=PydanticObjectId(id))


@param_router.patch(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-edit-parameters"})),
    ],
    response_model=Params,
    summary="Update param",
    status_code=status.HTTP_202_ACCEPTED,
)
async def update(id: PydanticObjectId, payload: ParamsModel = Body(...)):
    return await params.update(id=PydanticObjectId(id), param=payload)


@param_router.delete(
    "/{id}",
    dependencies=[
        Depends(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"auth:can-delete-parameters"})),
    ],
    summary="Remove param",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete(id: PydanticObjectId):
    return await params.delete(id=PydanticObjectId(id))
