from enum import StrEnum

from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseParamsFields
from fastapi_pagination.utils import disable_installed_extensions_check
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from src.config import settings

disable_installed_extensions_check()

password_context = PasswordHash((Argon2Hasher(), BcryptHasher()))


class SortEnum(StrEnum):
    ASC = "asc"
    DESC = "desc"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(password=plain_password, hash=hashed_password)


def password_hash(password: str) -> str:
    return password_context.hash(password=password)


def customize_page(model):
    return CustomizedPage[Page, UseParamsFields(size=settings.DEFAULT_PAGIGNIATE_PAGE_SIZE)]
