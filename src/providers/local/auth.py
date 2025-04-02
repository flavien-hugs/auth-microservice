from typing import Any, Type

from src.providers.base import AuthProvider

Class = Type[Any]


class LocalAuthProvider(AuthProvider):
    async def create_user(self, user_klass: Class, **kwargs) -> dict:
        raise NotImplementedError

    async def get_user(self, user_id: str) -> dict:
        raise NotImplementedError

    async def get_users(self, user_klass: Class, **kwargs) -> list:
        raise NotImplementedError

    async def update_user(self, user_id: str, **kwargs) -> dict:
        raise NotImplementedError

    def delete_user(self, user_id: str) -> None:
        raise NotImplementedError

    def authenticate_credentials(self, username: str, password: str) -> dict:
        raise NotImplementedError

    def authenticate_token(self, token: str) -> dict:
        raise NotImplementedError

    def issue_token(self, user_info: dict) -> str:
        raise NotImplementedError

    def refresh_token(self, token: str) -> dict:
        raise NotImplementedError

    def update_password(self, token: str, payload: dict) -> None:
        raise NotImplementedError

    def change_password(self, user_id: str, password: str) -> None:
        raise NotImplementedError

    def reset_password(self, user_id: str, token: str) -> None:
        raise NotImplementedError

    def request_password_reset(self, email: str) -> None:
        raise NotImplementedError

    def logout(self, token: str) -> None:
        raise NotImplementedError

    def disable_account(self, user_id: str) -> None:
        raise NotImplementedError

    def enable_account(self, user_id: str) -> None:
        raise NotImplementedError
