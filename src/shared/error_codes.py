from enum import StrEnum


class AuthErrorCode(StrEnum):
    AUTH_MISSING_TOKEN = "auth/missing-token"
    AUTH_MISSING_SCHEME = "auth/missing-scheme"
    AUTH_INVALID_PASSWORD = "auth/invalid-password"
    AUTH_NOT_AUTHENTICATED = "auth/no-authenticated"
    AUTH_PASSWORD_MISMATCH = "auth/password-mismatch"
    AUTH_UNAUTHORIZED_ACCESS = "auth/unauthorized-access"
    AUTH_EXPIRED_ACCESS_TOKEN = "auth/expired-access-token"
    AUTH_INVALID_ACCESS_TOKEN = "auth/invalid-access-token"
    AUTH_INSUFFICIENT_PERMISSION = "auth/insufficient-permission"


class UserErrorCode(StrEnum):
    USER_NOT_FOUND = "users/user-not-found"
    USER_ACCOUND_DESABLE = "users/account-disabled"
    USER_CREATE_FAILED = "users/create-user-failed"
    USER_UPDATE_INFO_FAILED = "users/update_user-failed"
    USER_EMAIL_ALREADY_EXIST = "users/email-alreary-exist"
