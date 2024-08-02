from enum import StrEnum


class AuthErrorCode(StrEnum):
    AUTH_NOT_AUTHENTICATED = "auth/no-authenticated"
    AUTH_PASSWORD_MISMATCH = "auth/password-mismatch"
