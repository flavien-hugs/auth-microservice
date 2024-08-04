import faker
import pytest
from starlette import status

from src.shared.error_codes import UserErrorCode, RoleErrorCode, AuthErrorCode
from src.common.helpers.error_codes import AppErrorCode
# fake = faker.Faker()


@pytest.mark.asyncio
async def test_create_users_success(http_client_api, fake_user_data):
    response = await http_client_api.post("/users", json=fake_user_data)

    response_json = response.json()
    assert response.status_code == status.HTTP_201_CREATED, response.text
    assert "_id" in response_json.keys()
    assert response_json["email"] == fake_user_data["email"]


@pytest.mark.asyncio
async def test_create_user_already_exists(http_client_api, fake_user_collection, fake_user_data):
    fake_user_data.update({"email": fake_user_collection.email})

    response = await http_client_api.post("/users", json=fake_user_data)

    response_json = response.json()
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response_json["code_error"] == UserErrorCode.USER_EMAIL_ALREADY_EXIST
    assert response_json["message_error"] == f"User with email '{fake_user_data['email'].lower()}' already exists"


@pytest.mark.asyncio
async def test_create_user_with_email_empty(http_client_api, fake_user_data):
    fake_user_data.update({"email": None})

    response = await http_client_api.post("/users", json=fake_user_data)

    response_json = response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
    assert response_json["code_error"] == AppErrorCode.REQUEST_VALIDATION_ERROR
    assert response_json["message_error"] == "[{'field': 'email', 'message': 'Input should be a valid string'}]"


@pytest.mark.asyncio
async def test_create_user_with_role_empty(http_client_api, fake_user_data):
    fake_user_data.update({"role": None})
    response = await http_client_api.post("/users", json=fake_user_data)
    response_json = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response_json["code_error"] == RoleErrorCode.ROLE_NOT_FOUND


@pytest.mark.asyncio
async def test_create_user_with_password_empty(http_client_api, fake_user_data):
    fake_user_data.update({"password": ""})

    response = await http_client_api.post("/users", json=fake_user_data)

    response_json = response.json()
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response_json["code_error"] == AuthErrorCode.AUTH_PASSWORD_MISMATCH
    assert response_json["message_error"] == "The password must be 6 characters or more."
