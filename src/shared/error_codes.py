from enum import StrEnum


class AuthErrorCode(StrEnum):
    AUTH_NOT_AUTHENTICATED = "auth/no-authenticated"
    AUTH_PASSWORD_MISMATCH = "auth/password-mismatch"


class UserErrorCode(StrEnum):
    USER_NOT_FOUND = "users/user-not-found"
    USER_CREATE_FAILED = "users/create-user-failed"
    USER_UPDATE_INFO_FAILED = "users/update_user-failed"
    USER_EMAIL_ALREADY_EXIST = "users/email-alreary-exist"
