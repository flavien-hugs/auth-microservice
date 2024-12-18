import os

import pytest
from starlette import status

from src.common.helpers.error_codes import AppErrorCode
from src.shared.error_codes import AuthErrorCode, UserErrorCode


@pytest.mark.asyncio
async def test_ping_api(http_client_api):
    response = await http_client_api.get("/@ping")
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"message": "pong !"}


@pytest.mark.asyncio
async def test_create_users_unauthorized(http_client_api, fake_user_data):
    response = await http_client_api.post("/users", json=fake_user_data)

    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    assert response.json() == {"code_error": "auth/no-authenticated", "message_error": "Not authenticated"}


@pytest.mark.asyncio
async def test_create_users_forbidden(http_client_api, mock_check_permissions_handler, fake_user_data):
    response = await http_client_api.post(
        "/users", json=fake_user_data, headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text
    assert response.json() == {"code_error": "auth/invalid-access-token", "message_error": "Not enough segments"}
    mock_check_permissions_handler.assert_not_called()


@pytest.mark.asyncio
async def test_create_users_no_authenticated(
    http_client_api, mock_verify_access_token, mock_check_permissions_handler, fake_user_data
):
    response = await http_client_api.post("/users", json=fake_user_data)

    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    assert response.json() == {"code_error": "auth/no-authenticated", "message_error": "Not authenticated"}

    mock_verify_access_token.assert_not_called()
    mock_check_permissions_handler.assert_not_called()


@pytest.mark.asyncio
async def test_add_users_failed(http_client_api, fake_user_data):
    response = await http_client_api.post(
        "/users/add", json=fake_user_data, headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json() == {
        "code_error": "roles/role-not-found",
        "message_error": f"Role with name '{os.getenv('DEFAULT_ADMIN_ROLE')}' not found.",
    }


@pytest.mark.asyncio
async def test_create_users_already_exists(
    http_client_api, mock_verify_access_token, mock_check_permissions_handler, fake_user_collection, fake_user_data
):

    fake_user_data.update({"email": fake_user_collection.email})
    response = await http_client_api.post(
        "/users", json=fake_user_data, headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert fake_user_data["email"] == fake_user_collection.email
    assert response.json() == {
        "code_error": "users/email-already-exist",
        "message_error": f"User with email '{fake_user_data['email']}' already exists",
    }

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_create_users_success(
    http_client_api, mock_verify_access_token, mock_check_permissions_handler, fake_user_data
):
    response = await http_client_api.post(
        "/users", json=fake_user_data, headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == status.HTTP_201_CREATED, response.text
    assert fake_user_data["email"] == response.json()["email"]

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_listing_users_success(http_client_api, mock_verify_access_token, mock_check_permissions_handler):
    response = await http_client_api.get("/users", headers={"Authorization": "Bearer valid_token"})

    assert response.status_code == status.HTTP_200_OK, response.text
    assert "items" in response.json()

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_listing_users_with_query_success(
    http_client_api,
    fake_user_collection,
    mock_verify_access_token,
    mock_check_permissions_handler,
):
    search_email = fake_user_collection.email
    response = await http_client_api.get(
        "/users", params={"query": search_email}, headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["items"][0]["email"] == search_email
    assert response.json()["total"] >= 1, "Le total doit-être supérieur ou égal à 1"

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_read_user_success(
    http_client_api,
    fake_user_collection,
    mock_verify_access_token,
    mock_check_permissions_handler,
):
    id_user = fake_user_collection.id
    response = await http_client_api.get(f"/users/{id_user}", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["_id"] == str(id_user)
    assert response.json()["email"] == fake_user_collection.email

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_read_user_not_found(
    http_client_api,
    mock_verify_access_token,
    mock_check_permissions_handler,
):
    response = await http_client_api.get(
        "/users/66e85363aa07cb1e95d3e3d0", headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json() == {
        "code_error": "users/user-not-found",
        "message_error": "User with '66e85363aa07cb1e95d3e3d0' not found.",
    }

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_success(
    http_client_api,
    fake_user_collection,
    fake_user_data,
    mock_verify_access_token,
    mock_check_permissions_handler,
    fake_data,
):
    user_id = fake_user_collection.id
    fake_user_data.update(
        {
            "fullname": fake_data.name(),
            "attributes": {"city": fake_data.city()},
        }
    )

    response = await http_client_api.patch(
        f"/users/{user_id}", json=fake_user_data, headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["_id"] == str(user_id)
    assert response.json()["fullname"] == fake_user_data["fullname"]

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_not_found(
    http_client_api,
    fake_user_collection,
    fake_user_data,
    mock_verify_access_token,
    mock_check_permissions_handler,
):
    fake_user_data.update({"fullname": "Adele"})
    response = await http_client_api.patch(
        "/users/66e85363aa07cb1e95d3e3d0", json=fake_user_data, headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json() == {
        "code_error": "users/user-not-found",
        "message_error": "User with '66e85363aa07cb1e95d3e3d0' not found.",
    }

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_bad_request(
    http_client_api,
    fake_user_collection,
    mock_verify_access_token,
    mock_check_permissions_handler,
):
    user_id = fake_user_collection.id

    response = await http_client_api.patch(f"/users/{user_id}", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
    assert response.json()["code_error"] == AppErrorCode.UNPROCESSABLE_ENTITY
    assert response.json()["message_error"] == "[{'field': 'body', 'message': 'Field required'}]"

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_success(
    http_client_api,
    fake_user_collection,
    mock_verify_access_token,
    mock_check_permissions_handler,
    mock_check_check_user_access_handler,
):
    user_id = fake_user_collection.id

    response = await http_client_api.delete(f"/users/{user_id}", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()

    mock_check_check_user_access_handler.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_not_found(
    http_client_api,
    mock_verify_access_token,
    mock_check_permissions_handler,
    mock_check_check_user_access_handler,
):
    response = await http_client_api.delete(
        "/users/66e85363aa07cb1e95d3e3d0", headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json() == {
        "code_error": UserErrorCode.USER_NOT_FOUND,
        "message_error": "User with '66e85363aa07cb1e95d3e3d0' not found.",
    }

    mock_verify_access_token.assert_called_once()
    mock_verify_access_token.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()

    mock_check_check_user_access_handler.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_unauthorized(
    http_client_api,
    fake_user_collection,
    mock_verify_access_token,
    mock_check_permissions_handler,
    mock_check_check_user_access_handler,
):
    user_id = fake_user_collection.id

    response = await http_client_api.delete(f"/users/{user_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    assert response.json() == {"code_error": AuthErrorCode.AUTH_NOT_AUTHENTICATED, "message_error": "Not authenticated"}

    mock_verify_access_token.assert_not_called()
    mock_check_permissions_handler.assert_not_called()
    mock_check_check_user_access_handler.assert_not_called()


@pytest.mark.asyncio
async def test_activate_user_account_acction_uses_cases(
    http_client_api,
    fake_user_collection,
    mock_verify_access_token,
    mock_check_permissions_handler,
    mock_check_check_user_access_handler,
    mock_redis_client,
):
    user_id = fake_user_collection.id

    # Test activate user account
    response = await http_client_api.put(
        f"/users/{user_id}/activate", params={"action": "activate"}, headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"message": "User account activated successfully."}

    # Verify if the redis client is called
    mock_redis_client.keys.assert_called()
    mock_redis_client.delete.assert_called()

    # Test deactivate user account
    response = await http_client_api.put(
        f"/users/{user_id}/activate", params={"action": "deactivate"}, headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"message": "User account deactivated successfully."}

    mock_verify_access_token.assert_called()
    mock_verify_access_token.assert_called_with("valid_token")
    mock_check_permissions_handler.assert_called()

    mock_check_check_user_access_handler.assert_called()
