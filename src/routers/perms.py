from fastapi import APIRouter, status


perm_router = APIRouter(prefix="/permissions", tags=["PERMISSIONS"], redirect_slashes=False)


@perm_router.get("", summary="Get all permissions", status_code=status.HTTP_200_OK)
async def ger_permssions():
    from src.services.perms import get_all_permissions

    return await get_all_permissions()
