import pytest
from starlette import status


# fake = faker.Faker()


@pytest.mark.asyncio
async def test_ping_api(http_client_api):
    response = await http_client_api.get("/@ping")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"message": "pong !"}


@pytest.mark.asyncio
async def test_create_users_success(http_client_api, fake_user_data):
    response = await http_client_api.post("/users", json=fake_user_data)

    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    assert response.json() == {"code_error": "auth/no-authenticated", "message_error": "Not authenticated"}
