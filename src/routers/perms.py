from fastapi import APIRouter, Depends, Security, status

from src.middlewares import AuthorizedHTTPBearer, CheckPermissionsHandler

perm_router = APIRouter(prefix="/permissions", tags=["PERMISSIONS"], redirect_slashes=False)


@perm_router.get(
    "",
    dependencies=[
        Security(AuthorizedHTTPBearer),
        Depends(CheckPermissionsHandler(required_permissions={"can-display-permission"})),
    ],
    summary="Get all permissions",
    status_code=status.HTTP_200_OK,
)
async def ger_permssions():
    from src.services.perms import get_all_permissions

    return await get_all_permissions()
