from datetime import datetime, timezone
from secrets import compare_digest
from unittest import mock

import pytest
from fastapi import Request, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError

from src.middleware.auth import AuthorizedHTTPBearer, CheckPermissionsHandler, CustomAccessBearer, CustomHTTException
from src.shared.error_codes import AuthErrorCode


class TestCustomAccessBearer:

    def setup_method(self):
        self.custom_access_token = CustomAccessBearer()

    @pytest.mark.asyncio
    def test_create_access_token(self, fake_jwt_access_bearer, fake_user_collection, mock_jwt_settings):
        with mock.patch("src.middleware.auth.JwtAccessBearer", fake_jwt_access_bearer):
            fake_jwt_access_bearer.create_access_token.return_value = "fake_access_token"
            token = self.custom_access_token.access_token(data=fake_user_collection, user_id=fake_user_collection.id)
            assert compare_digest(token, "fake_access_token")

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, fake_jwt_access_bearer, fake_user_collection, mock_jwt_settings):
        with mock.patch("src.middleware.auth.JwtAccessBearer", fake_jwt_access_bearer):
            fake_jwt_access_bearer.create_refresh_token.return_value = "fake_refresh_token"
            token = self.custom_access_token.refresh_token(data=fake_user_collection, user_id=fake_user_collection.id)
            assert compare_digest(token, "fake_refresh_token")

    @mock.patch("src.middleware.auth.jwt.decode")
    def test_decode_access_token(self, mock_jwt_decode, mock_jwt_settings):
        mock_jwt_decode.return_value = {"sub": "user_id_123", "exp": datetime.now(timezone.utc).timestamp() + 600}
        decoded_token = self.custom_access_token.decode_access_token("fake_access_token")
        assert decoded_token["sub"] == "user_id_123"

    @pytest.mark.asyncio
    @mock.patch("src.middleware.auth.CustomAccessBearer.decode_access_token")
    async def test_verify_access_token_success(self, mock_decode_access_token, mock_jwt_settings):
        mock_decode_access_token.return_value = {
            "subject": {"is_active": True},
            "exp": datetime.now(timezone.utc).timestamp() + 600,
        }
        result = await self.custom_access_token.verify_access_token("fake_access_token")
        assert result is True

    @pytest.mark.asyncio
    @mock.patch("src.middleware.auth.CustomAccessBearer.decode_access_token")
    async def test_verify_access_token_expired(self, mock_decode_access_token, mock_jwt_settings):
        mock_decode_access_token.return_value = {
            "subject": {"is_active": False},
            "exp": datetime.now(timezone.utc).timestamp() - 600,
        }
        with pytest.raises(CustomHTTException) as exc_info:
            await self.custom_access_token.verify_access_token("fake_access_token")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.code_error == AuthErrorCode.AUTH_EXPIRED_ACCESS_TOKEN

    @pytest.mark.asyncio
    @mock.patch("src.middleware.auth.CustomAccessBearer.decode_access_token")
    @mock.patch("src.middleware.auth.blacklist_token")
    async def test_verify_access_token_decode_and_cache_success(self, mock_blacklist, mock_decode_access_token):
        # Jeton non trouvé dans le cache, mais décodé et valide
        current_timestamp = datetime.now(timezone.utc).timestamp()
        mock_blacklist.is_token_blacklisted = mock.AsyncMock(return_value=False)
        mock_decode_access_token.return_value = {"subject": {"is_active": True}, "exp": current_timestamp + 600}

        result = await CustomAccessBearer.verify_access_token("valid_token")

        # Vérification des appels
        mock_blacklist.is_token_blacklisted.assert_awaited_once_with("valid_token")
        assert result is True

    @pytest.mark.asyncio
    @mock.patch("src.middleware.auth.CustomAccessBearer.decode_access_token")
    @mock.patch("src.middleware.auth.blacklist_token")
    async def test_verify_access_token_expired_to_blacklist(self, mock_blacklist, mock_decode_access_token):
        # Jeton non trouvé dans le cache, décodé mais expiré
        current_timestamp = datetime.now(timezone.utc).timestamp()
        mock_blacklist.is_token_blacklisted = mock.AsyncMock(return_value=False)
        mock_decode_access_token.return_value = {"subject": {"is_active": True}, "exp": current_timestamp - 100}

        with pytest.raises(CustomHTTException) as exc:
            await CustomAccessBearer.verify_access_token("expired_token")

        # Vérification des appels
        mock_blacklist.is_token_blacklisted.assert_awaited_once_with("expired_token")
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.value.message_error == "Token has expired !"

    @pytest.mark.asyncio
    @mock.patch("src.middleware.auth.CustomAccessBearer.decode_access_token")
    @mock.patch("src.middleware.auth.blacklist_token")
    async def test_verify_access_token_invalid(self, mock_blacklist, mock_decode_access_token):
        # Jeton invalide et exception lors du décodage
        mock_blacklist.is_token_blacklisted = mock.AsyncMock(return_value=False)
        mock_decode_access_token.side_effect = JWTError("Invalid token")

        with pytest.raises(CustomHTTException) as exc:
            await CustomAccessBearer.verify_access_token("invalid_token")

        # Vérification des appels
        mock_blacklist.is_token_blacklisted.assert_awaited_once_with("invalid_token")
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.value.message_error == "Invalid token"

    @pytest.mark.asyncio
    @mock.patch("src.middleware.auth.CustomAccessBearer.decode_access_token")
    async def test_verify_access_with_token(self, mock_decode_access_token, mock_jwt_settings):
        mock_decode_access_token.side_effect = JWTError("Token is invalid")
        with pytest.raises(CustomHTTException) as exc_info:
            await self.custom_access_token.verify_access_token("fake_access_token")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.code_error == AuthErrorCode.AUTH_INVALID_ACCESS_TOKEN


class TestAuthorizeHTTPBearer:

    def setup_method(self):
        self.auth_bearer = AuthorizedHTTPBearer()
        self.request = mock.Mock(spec=Request)

    @pytest.mark.asyncio
    @mock.patch("src.middleware.CustomAccessBearer.verify_access_token")
    async def test_verify_access_token(self, mock_verify_token):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        with mock.patch("fastapi.security.HTTPBearer.__call__", return_value=credentials):
            result = await self.auth_bearer(self.request)

        mock_verify_token.assert_called_once_with("valid_token")
        assert result == "valid_token"

    @pytest.mark.asyncio
    async def test_missing_scheme(self):
        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="valid_token")

        with mock.patch("fastapi.security.HTTPBearer.__call__", return_value=credentials):
            with pytest.raises(CustomHTTException) as excinfo:
                await self.auth_bearer(self.request)

            assert excinfo.value.code_error == AuthErrorCode.AUTH_MISSING_SCHEME
            assert excinfo.value.message_error == "Missing or invalid authentication scheme."
            assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_token_expired(self):
        with mock.patch("fastapi.security.HTTPBearer.__call__", return_value=None):
            with pytest.raises(CustomHTTException) as excinfo:
                await self.auth_bearer(self.request)

            assert excinfo.value.code_error == AuthErrorCode.AUTH_EXPIRED_ACCESS_TOKEN
            assert excinfo.value.message_error == "The token has expired."
            assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestCheckPermissionsHandler:
    def setup_method(self):
        self.required_permissions = {f"perm-name-{i}" for i in range(1, 4)}
        self.ckeck_permissions_handler = CheckPermissionsHandler(required_permissions=self.required_permissions)
        self.request = mock.Mock(spec=Request)

    @pytest.mark.asyncio
    @mock.patch("src.middleware.CustomAccessBearer.check_permissions")
    async def test_valid_permissions(self, mock_check_permissions):
        mock_check_permissions.return_value = True
        self.request.headers = {"Authorization": "Bearer mocker_access_token"}

        result = await self.ckeck_permissions_handler(self.request)

        mock_check_permissions.assert_called_once_with("mocker_access_token", self.required_permissions)
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        self.request.headers = {}

        with pytest.raises(CustomHTTException) as excinfo:
            await self.ckeck_permissions_handler(self.request)

        assert excinfo.value.code_error == AuthErrorCode.AUTH_MISSING_TOKEN
        assert excinfo.value.message_error == "Missing token."
        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @mock.patch("src.middleware.CustomAccessBearer.check_permissions")
    async def test_insufficient_permissions(self, mock_check_permissions):
        mock_check_permissions.side_effect = CustomHTTException(
            code_error=AuthErrorCode.AUTH_INSUFFICIENT_PERMISSION,
            message_error="You do not have the necessary permissions to access this resource.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
        self.request.headers = {"Authorization": "Bearer valid_token"}

        with pytest.raises(CustomHTTException) as excinfo:
            await self.ckeck_permissions_handler(self.request)

        mock_check_permissions.assert_called_once_with("valid_token", self.required_permissions)
        assert excinfo.value.code_error == AuthErrorCode.AUTH_INSUFFICIENT_PERMISSION
        assert excinfo.value.message_error == "You do not have the necessary permissions to access this resource."
        assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
