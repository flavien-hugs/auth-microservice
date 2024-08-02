from .auth import AuthTokenBearer, CheckPermissionsHandler, CustomAccessBearer


AuthorizeHTTPBearer = AuthTokenBearer()

__all__ = ["AuthorizeHTTPBearer", "CheckPermissionsHandler", "CustomAccessBearer"]
