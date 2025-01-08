import json
from unittest import mock
from datetime import datetime, UTC

import pytest
from starlette import status
from starlette.responses import JSONResponse

from src.common.depends.permission import CustomHTTPException
from src.config import settings
from src.schemas import LoginUser
from src.services import auth
from src.shared.error_codes import AuthErrorCode, UserErrorCode
from beanie import PydanticObjectId


@pytest.mark.asyncio
@mock.patch("src.services.auth.auth.get_mac_address")
@mock.patch("src.services.auth.auth.User.set", new_callable=mock.AsyncMock)
@mock.patch("src.services.auth.auth.User.find_one", new_callable=mock.AsyncMock)
@mock.patch("src.services.auth.auth.verify_password", return_value=True)
@mock.patch("src.services.auth.auth.get_one_role", new_callable=mock.AsyncMock)
@mock.patch("src.services.auth.auth.CustomAccessBearer.access_token", return_value="access_token")
@mock.patch("src.services.auth.auth.CustomAccessBearer.refresh_token", return_value="refresh_token")
async def test_login_success(
    mock_refresh_token,
    mock_access_token,
    mock_get_one_role,
    mock_verify_password,
    mock_find_one,
    mock_user_set,
    mock_get_mac_address,
    fixture_models,
    mock_task,
    mock_request,
):
    # setup device_id mock
    mock_get_mac_address.return_value = "test_device_id"

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
                attributes={
                    "device_id": None,
                    "address_ip": None,
                    "last_login": None
                }
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
                attributes={
                    "device_id": None,
                    "address_ip": None,
                    "last_login": None
                }
            )
            payload = LoginUser(phonenumber="+2250151571396", password="testpassword")

        # setup mocks
        mock_find_one.return_value = fake_user
        mock_get_one_role.return_value.model_dump = mock.Mock(
            return_value={"_id": "66e85363aa07cb1e95d3e3d0", "name": "admin"}
        )
        mock_user_set.return_value = fake_user

        # mock request headers for X-Forwarded-For
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1"}
        mock_request.client.host = "127.0.0.1"

        # execute login
        response = await auth.login(request=mock_request, payload=payload)

        # assertions
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_200_OK

        response_data = json.loads(response.body.decode())

        # token assertions
        assert response_data["access_token"] == "access_token"

        # user data assertions
        assert response_data["user"][identifier] == payload.email if register_with_email else payload.phonenumber
        assert response_data["user"]["role"]["name"] == "admin"


@pytest.mark.asyncio
async def test_login_device_already_logged_in(
        mock_request,
        fixture_models,
):
    settings.REGISTER_WITH_EMAIL = True

    # Setup user with existing device_id
    fake_user = fixture_models.users.User(
        id="66e85363aa07cb1e95d3e3d0",
        email="test@example.com",
        password="hashedpassword",
        role=PydanticObjectId("66e85363aa07cb1e95d3e3d0"),
        is_active=True,
        attributes={
            "device_id": "existing_device_id",
            "address_ip": "192.168.1.2",
            "last_login": datetime.now(tz=UTC)
        }
    )

    mock_role = {"_id": "66e85363aa07cb1e95d3e3d0", "name": "admin"}

    with mock.patch("src.services.auth.auth.get_mac_address", return_value="different_device_id"), \
            mock.patch("src.services.auth.auth.User.find_one", new_callable=mock.AsyncMock, return_value=fake_user), \
            mock.patch("src.services.auth.auth.verify_password", return_value=True), \
            mock.patch("src.services.auth.auth.get_one_role",
                       new_callable=mock.AsyncMock, return_value=mock.Mock(mock_role)):
        payload = LoginUser(email="test@example.com", password="testpassword")

        with pytest.raises(CustomHTTPException) as exc_info:
            await auth.login(request=mock_request, payload=payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.code_error == AuthErrorCode.AUTH_ALREADY_LOGGED_IN


@pytest.mark.asyncio
@mock.patch("src.services.auth.auth.User.find_one", new_callable=mock.AsyncMock)
async def test_login_inactive_user(mock_find_one, fixture_models, mock_request):
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

        with pytest.raises(CustomHTTPException) as excinfo:
            await auth.login(request=mock_request, payload=payload)

        assert excinfo.typename == "CustomHTTPException"
        assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
        assert excinfo.value.code_error == UserErrorCode.USER_NOT_FOUND
        assert excinfo.value.message_error == (
            "Your account is not active. Please contact the administrator to " "activate your account."
        )

        mock_request.assert_not_called()


@pytest.mark.asyncio
@mock.patch("src.services.auth.auth.User.find_one", new_callable=mock.AsyncMock)
@mock.patch("src.services.auth.auth.verify_password", return_value=False)
async def test_login_invalid_password(mock_verify_password, mock_find_one, mock_request, fixture_models):
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

    with pytest.raises(CustomHTTPException) as excinfo:
        await auth.login(mock_request, payload)

    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    assert excinfo.value.code_error == AuthErrorCode.AUTH_INVALID_PASSWORD
    assert excinfo.value.message_error == "Your password is invalid."

    mock_request.assert_not_called()


@pytest.mark.asyncio
@mock.patch("src.services.auth.auth.User.find_one", new_callable=mock.AsyncMock)
async def test_login_invalid_identifier_not_found(mock_find_one, mock_request, fixture_models):
    for register_with_email in [True, False]:
        settings.REGISTER_WITH_EMAIL = register_with_email

        if register_with_email:
            payload = LoginUser(email="test@example.com", password="testpassword")
        else:
            payload = LoginUser(phonenumber="+2250151571397", password="testpassword")

        mock_find_one.return_value = None

        with pytest.raises(CustomHTTPException) as excinfo:
            await auth.login(request=mock_request, payload=payload)

        expected_message = "User does not exist."
        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
        assert excinfo.value.code_error == UserErrorCode.USER_NOT_FOUND
        assert excinfo.value.message_error == expected_message

        mock_request.assert_not_called()
