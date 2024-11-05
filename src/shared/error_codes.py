from enum import StrEnum


class AuthErrorCode(StrEnum):
    AUTH_MISSING_TOKEN = "auth/missing-token"
    AUTH_MISSING_SCHEME = "auth/missing-scheme"
    AUTH_INVALID_PASSWORD = "auth/invalid-password"
    AUTH_NOT_AUTHENTICATED = "auth/no-authenticated"
    AUTH_PASSWORD_MISMATCH = "auth/password-mismatch"
    AUTH_INVALID_CREDENTIALS = "auth/invalid-credentials"
    AUTH_UNAUTHORIZED_ACCESS = "auth/unauthorized-access"
    AUTH_EXPIRED_ACCESS_TOKEN = "auth/expired-access-token"
    AUTH_INVALID_ACCESS_TOKEN = "auth/invalid-access-token"
    AUTH_INSUFFICIENT_PERMISSION = "auth/insufficient-permission"
    AUTH_OTP_NOT_VALID = "auth/otp-not-valid"
    AUTH_OTP_EXPIRED = "auth/otp-code-expired"


class UserErrorCode(StrEnum):
    USER_NOT_FOUND = "users/user-not-found"
    USER_PASSWORD_EMPTY = "users/password-empty"
    USER_PHONENUMBER_EMPTY = "users/phonenumber-empty"
    USER_ACCOUND_DESABLE = "users/account-disabled"
    USER_CREATE_FAILED = "users/create-user-failed"
    USER_UPDATE_INFO_FAILED = "users/update-user-failed"
    USER_EMAIL_ALREADY_EXIST = "users/email-already-exist"
    FIRST_USER_ALREADY_EXIST = "users/first-user-alreary-exist"
    USER_PHONENUMBER_NOT_FOUND = "users/phone-number-not-found"
    USER_PHONENUMBER_TAKEN = "users/phonenumber-already-taken"
    UPLOAD_FILE_ERROR = "users/upload-file-error"
    USER_DELETE_PRIMARY = "users/can-not-delete-user"
    INVALID_ATTRIBUTES = "users/invalid-attributes"


class RoleErrorCode(StrEnum):
    ROLE_NOT_FOUND = "roles/role-not-found"
    ROLE_CREATE_FAILED = "roles/create-role-failed"
    ROLE_UPDATE_INFO_FAILED = "roles/update-role-failed"
    ROLE_ALREADY_EXIST = "roles/role-already-exist"


class ParamErrorCode(StrEnum):
    PARAM_NOT_FOUND = "parameters/parameter-not-found"
    PARAM_ALREADY_EXIST = "parameters/parameter-already-exist"
    PARAM_CREATE_FAILED = "parameters/create-parameter-failed"
    PARAM_UPDATE_INFO_FAILED = "parameters/update-parameter-failed"
