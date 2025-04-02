from abc import ABC, abstractmethod
from typing import Type, Any


Class = Type[Any]


class AuthProvider(ABC):
    @abstractmethod
    def create_user(self, user_klass: Class, **kwargs) -> dict:
        """
        Create a new user.
        """
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> dict:
        """
        Get user information
        """
        pass

    @abstractmethod
    async def get_users(self, user_klass: Class, **kwargs) -> list:
        """
        Get a list of all users in the system.
        """
        pass

    @abstractmethod
    async def update_user(self, user_id: str, **kwargs) -> dict:
        """
        Update the user with the given ID.
        """
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """
        Delete the user with the given ID.
        """
        pass

    @abstractmethod
    def authenticate_credentials(self, username: str, password: str) -> dict:
        """
        Validate the provided username and password and return the user info if valid.
        """
        pass

    @abstractmethod
    def authenticate_token(self, token: str) -> dict:
        """
        Validate the provided token and return the user info if valid.
        """
        pass

    @abstractmethod
    def issue_token(self, user_info: dict) -> str:
        """
        Issue a new token based on the provided user info.
        """
        pass

    @abstractmethod
    def refresh_token(self, token: str) -> dict:
        """
        Refresh the token with the provided refresh token.
        """
        pass

    @abstractmethod
    def update_password(self, token: str, payload: dict) -> None:
        """
        Update the password of the user with the given ID using the provided token.
        """
        pass

    @abstractmethod
    def change_password(self, user_id: str, password: str) -> None:
        """
        Change the password of the user with the given ID.
        """
        pass

    @abstractmethod
    def reset_password(self, user_id: str, token: str) -> None:
        """
        Reset the password of the user with the given ID.
        """
        pass

    @abstractmethod
    def request_password_reset(self, email: str) -> None:
        """
        Request a password reset for the user with the given email.
        """
        pass

    @abstractmethod
    def logout(self, token: str) -> None:
        """
        Logout the user associated with the given refresh token.
        """
        pass

    @abstractmethod
    def disable_account(self, user_id: str) -> None:
        """
        Disable the user with the given ID.
        """
        pass

    @abstractmethod
    def enable_account(self, user_id: str) -> None:
        """
        Enable the user with the given ID.
        """
        pass
