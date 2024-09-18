import json
from unittest import mock

import pytest
from starlette import status
from starlette.responses import JSONResponse

from src.common.helpers.permissions import CustomHTTException
from src.config import settings
from src.schemas import LoginUser
from src.services import auth
from src.shared.error_codes import AuthErrorCode, UserErrorCode
from beanie import PydanticObjectId


@pytest.mark.asyncio
@mock.patch("src.services.auth.User.find_one", new_callable=mock.AsyncMock)
@mock.patch("src.services.auth.verify_password", return_value=True)
@mock.patch("src.services.auth.get_one_role", new_callable=mock.AsyncMock)
@mock.patch("src.services.auth.CustomAccessBearer.access_token", return_value="access_token")
@mock.patch("src.services.auth.CustomAccessBearer.refresh_token", return_value="refresh_token")
async def test_login_success(
    mock_refresh_token, mock_access_token, mock_get_one_role, mock_verify_password, mock_find_one, fixture_models
):
    for register_with_email in [True, False]:
        settings.REGISTER_WITH_EMAIL = register_with_email

        if register_with_email:
            identifier = "email"
            fake_user = fixture_models.users.User(
                id="66e85363aa07cb1e95d3e3d0",
                email="test@example.com",
                password="hashedpassword",
                role=PydanticObjectId("66e85363aa07cb1e95d3e3d0"),
                is_active=True,
            )
            payload = LoginUser(email="test@example.com", password="testpassword")
        else:
            identifier = "phonenumber"
            fake_user = fixture_models.users.User(
                id="66e85363aa07cb1e95d3e3d0",
                email="test@example.com",
                phonenumber="+2250151571396",
                password="hashedpassword",
                role=PydanticObjectId("66e85363aa07cb1e95d3e3d0"),
                is_active=True,
            )
            payload = LoginUser(phonenumber="+2250151571396", password="testpassword")

        mock_find_one.return_value = fake_user
        mock_get_one_role.return_value.model_dump = mock.Mock(
            return_value={"_id": "66e85363aa07cb1e95d3e3d0", "name": "admin"}
        )

        response = await auth.login(payload)
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_200_OK

        response_data = json.loads(response.body.decode())
        assert response_data["access_token"] == "access_token"
        assert response_data["referesh_token"] == "refresh_token"
        assert response_data["user"][identifier] == payload.email if register_with_email else payload.phonenumber
        assert response_data["user"]["role"]["name"] == "admin"


@pytest.mark.asyncio
@mock.patch("src.services.auth.User.find_one", new_callable=mock.AsyncMock)
async def test_login_inactive_user(mock_find_one, fixture_models):
    for register_with_email in [True, False]:
        settings.REGISTER_WITH_EMAIL = register_with_email

        if register_with_email:
            payload = LoginUser(email="test@example.com", password="testpassword")
            fake_user = fixture_models.users.User(
                id="66e85363aa07cb1e95d3e3d0",
                email="test@example.com",
                password="hashedpassword",
                role=PydanticObjectId("66e85363aa07cb1e95d3e3d0"),
                is_active=False,
            )
        else:
            payload = LoginUser(phonenumber="+2250151571396", password="testpassword")
            fake_user = fixture_models.users.User(
                id="66e85363aa07cb1e95d3e3d0",
                email="test@example.com",
                phonenumber="+2250151571396",
                password="hashedpassword",
                role=PydanticObjectId("66e85363aa07cb1e95d3e3d0"),
                is_active=False,
            )

        mock_find_one.return_value = fake_user

        with pytest.raises(CustomHTTException) as excinfo:
            await auth.login(payload)

        assert excinfo.typename == "CustomHTTException"
        assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
        assert excinfo.value.code_error == UserErrorCode.USER_NOT_FOUND
        assert excinfo.value.message_error == (
            "Your account is not active. Please contact the administrator to " "activate your account."
        )


@pytest.mark.asyncio
@mock.patch("src.services.auth.User.find_one", new_callable=mock.AsyncMock)
@mock.patch("src.services.auth.verify_password", return_value=False)
async def test_login_invalid_password(mock_verify_password, mock_find_one, fixture_models):
    settings.REGISTER_WITH_EMAIL = True

    fake_user = fixture_models.users.User(
        id="66e85363aa07cb1e95d3e3d0",
        email="test@example.com",
        password="hashedpassword",
        role=PydanticObjectId("66e85363aa07cb1e95d3e3d0"),
        is_active=True,
    )

    mock_find_one.return_value = fake_user
    payload = LoginUser(email="test@example.com", password="wrongpassword")

    with pytest.raises(CustomHTTException) as excinfo:
        await auth.login(payload)

    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    assert excinfo.value.code_error == AuthErrorCode.AUTH_INVALID_PASSWORD
    assert excinfo.value.message_error == "Your password is invalid."


@pytest.mark.asyncio
@mock.patch("src.services.auth.User.find_one", new_callable=mock.AsyncMock)
async def test_login_invalid_identifier_not_found(mock_find_one, fixture_models):
    for register_with_email in [True, False]:
        settings.REGISTER_WITH_EMAIL = register_with_email

        if register_with_email:
            payload = LoginUser(email="test@example.com", password="testpassword")
        else:
            payload = LoginUser(phonenumber="+2250151571397", password="testpassword")

        mock_find_one.return_value = None

        with pytest.raises(CustomHTTException) as excinfo:
            await auth.login(payload)

        expected_message = "User does not exist."
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
        assert excinfo.value.code_error == UserErrorCode.USER_NOT_FOUND
        assert excinfo.value.message_error == expected_message
