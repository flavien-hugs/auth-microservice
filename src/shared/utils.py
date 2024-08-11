import os
import logging
from enum import StrEnum
from secrets import compare_digest

import pyotp
from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseParamsFields
from fastapi_pagination.utils import disable_installed_extensions_check
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from src.config import settings

disable_installed_extensions_check()

password_context = PasswordHash((Argon2Hasher(), BcryptHasher()))

logging.basicConfig(format="%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class SortEnum(StrEnum):
    ASC = "asc"
    DESC = "desc"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(password=plain_password, hash=hashed_password)


def password_hash(password: str) -> str:
    return password_context.hash(password=password)


def customize_page(model):
    return CustomizedPage[Page, UseParamsFields(size=settings.DEFAULT_PAGIGNIATE_PAGE_SIZE)]


class GenerateOPTKey:

    @classmethod
    def generate_key(cls) -> str:
        return pyotp.random_base32()

    @classmethod
    def generate_otp_instance(cls, key: str) -> pyotp.TOTP:
        return pyotp.TOTP(key, interval=3000)

    @classmethod
    def verify_opt_code(cls, secret_otp: str, verify_otp: str) -> bool:
        return cls.generate_otp_instance(secret_otp).verify(verify_otp)


class TokenBlacklistHandler:

    def __init__(self):
        self._token_file = os.getenv("BLACKLIST_TOKEN_FILE")
        if not self._token_file:
            raise ValueError("Blacklist file does not exist !")
        self.init_blacklist_token_file()

    def init_blacklist_token_file(self) -> bool:
        try:
            open(file=self._token_file, mode="a").close()
            logger.info("Initialising the token blacklist file !")
        except IOError as e:
            raise IOError(f"Error when initialising the token blacklist file: {e}") from e
        return True

    async def add_blacklist_token(self, token: str) -> bool:
        try:
            with open(file=self._token_file, mode="a", encoding='utf_8') as file:
                file.write(f"{token},")
                logger.info("Adding token to blacklist file !")
        except IOError as e:
            raise IOError(f"Error when adding token to blacklist: {e}") from e
        return True

    async def is_token_blacklisted(self, token: str) -> bool:
        try:
            with open(file=self._token_file, mode="r") as file:
                content = file.read()
                tokens = content.rstrip(",").split(",")
                logger.info("The token already exists in the blacklist !")
        except IOError as e:
            raise IOError(f"Error verifying token in black list: {e}") from e

        return any(compare_digest(value, token) for value in tokens)
