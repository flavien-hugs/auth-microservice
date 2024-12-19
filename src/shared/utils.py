import logging
import os
from enum import StrEnum
from pathlib import Path
from secrets import compare_digest
from typing import Any, Callable, Optional, TypeVar

import pyotp
from fastapi import Request, Response
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from slugify import slugify

password_context = PasswordHash((Argon2Hasher(), BcryptHasher()))

logging.basicConfig(format="%(message)s", level=logging.INFO)
_log = logging.getLogger(__name__)


T = TypeVar("T")


class SortEnum(StrEnum):
    ASC: str = "asc"
    DESC: str = "desc"


class AccountAction(StrEnum):
    ACTIVATE: str = "activate"
    DEACTIVATE: str = "deactivate"


def custom_key_builder(service_name: str, *args, **kwargs):
    def _key_builder(
        func: Callable[..., Any],
        namespace: str,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
        *args,
        **kwargs,
    ) -> str:
        token_value = ""
        query_params_str = ""
        url_path = ""

        if request is not None:
            # Récupérer le token d'autorisation depuis les en-têtes de la requête
            if (token := request.headers.get("Authorization")) is not None:
                token_value = token.split()[1] if len(token.split()) > 1 else token
            else:
                # Récupérer le premier paramètre de requête si le token n'est pas dans les en-têtes
                token_value = next(iter(request.query_params.values()), "")

            # Convertir les paramètres de requête en chaîne de caractères triée
            query_params_str = repr(sorted(request.query_params.items()))
            # Récupérer le chemin de l'URL de la requête
            url_path = request.url.path

        slugify_service_name = slugify(service_name)

        return ":".join([slugify_service_name, token_value, query_params_str, url_path])

    return _key_builder


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(password=plain_password, hash=hashed_password)


def password_hash(password: str) -> str:
    return password_context.hash(password=password)


class GenerateOPTKey:

    @classmethod
    def generate_key(cls) -> str:
        return pyotp.random_base32()

    @classmethod
    def generate_otp_instance(cls, key: str) -> pyotp.TOTP:
        return pyotp.TOTP(key, digits=4, interval=3000)

    @classmethod
    def verify_opt_code(cls, secret_otp: str, verify_otp: str) -> bool:
        return cls.generate_otp_instance(secret_otp).verify(verify_otp)


class TokenBlacklistHandler:
    def __init__(self):
        self._token_file = Path(os.getenv("BLACKLIST_TOKEN_FILE", ".token.txt"))
        if not self._token_file:
            raise ValueError("Blacklist file does not exist!")
        self.init_blacklist_token_file()

    def init_blacklist_token_file(self) -> bool:
        try:
            self._token_file.touch(exist_ok=True)
        except IOError as e:
            raise IOError(f"Error when initializing the token blacklist file: {e}") from e
        return True

    async def add_blacklist_token(self, token: str) -> bool:
        try:
            with self._token_file.open(mode="a", encoding="utf-8") as file:
                file.write(f"{token},")
                _log.info("--> Adding token to blacklist file!")
        except IOError as e:
            raise IOError(f"Error when adding token to blacklist: {e}") from e
        return True

    async def is_token_blacklisted(self, token: str) -> bool:
        try:
            with self._token_file.open(encoding="utf-8") as file:
                content = file.read()
                tokens = content.rstrip(",").split(",")
        except IOError as e:
            raise IOError(f"Error verifying token in blacklist: {e}") from e

        return any(compare_digest(value, token) for value in tokens)
