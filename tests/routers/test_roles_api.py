import pytest
from slugify import slugify
from starlette import status


@pytest.mark.asyncio
async def test_create_roles_unauthorized(http_client_api, mock_authorized_http_bearer, fake_role_data):
    response = await http_client_api.post(
        "/roles", json=fake_role_data, headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text
    assert response.json() == {"code_error": "auth/invalid-access-token", "message_error": "Not enough segments"}


@pytest.mark.asyncio
async def test_create_roles_already_exists(
    http_client_api, mock_authorized_http_bearer, mock_check_permissions_handler, fake_role_collection, fake_role_data
):
    fake_role_data.update({"name": fake_role_collection.name})
    response = await http_client_api.post(
        "/roles", json=fake_role_data, headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert fake_role_data["name"] == fake_role_collection.name
    assert response.json() == {
        "code_error": "roles/role-already-exist",
        "message_error": f"This role '{fake_role_data['name']}' already exists.",
    }

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_create_roles_success(
    http_client_api, mock_authorized_http_bearer, mock_check_permissions_handler, fake_role_data
):
    response = await http_client_api.post(
        "/roles", json=fake_role_data, headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == status.HTTP_201_CREATED, response.text
    assert fake_role_data["name"] == response.json()["name"]

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


@pytest.mark.asyncio
async def test_listing_roles_success(http_client_api, mock_authorized_http_bearer, mock_check_permissions_handler):
    response = await http_client_api.get("/roles", headers={"Authorization": "Bearer valid_token"})

    assert response.status_code == status.HTTP_200_OK, response.text
    assert "items" in response.json()
    assert response.json()["total"] == 0

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_read_role_success(
    http_client_api,
    fake_role_collection,
    mock_authorized_http_bearer,
    mock_check_permissions_handler,
):
    role_id = fake_role_collection.id
    response = await http_client_api.get(f"/roles/{role_id}", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["_id"] == str(role_id)
    assert response.json()["slug"] == fake_role_collection.slug

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_read_role_not_found(
    http_client_api,
    mock_authorized_http_bearer,
    mock_check_permissions_handler,
):
    response = await http_client_api.get(
        "/roles/66e85363aa07cb1e95d3e3d0", headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json() == {
        "code_error": "roles/role-not-found",
        "message_error": "Role with '66e85363aa07cb1e95d3e3d0' not found.",
    }

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_update_role_success(
    http_client_api,
    fake_role_collection,
    fake_role_data,
    mock_authorized_http_bearer,
    mock_check_permissions_handler,
):
    role_id = fake_role_collection.id
    fake_role_data.update({"name": "Developpeur"})

    response = await http_client_api.put(
        f"/roles/{role_id}", json=fake_role_data, headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["_id"] == str(role_id)
    assert response.json()["slug"] == slugify(fake_role_data["name"])

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_update_role_not_found(
    http_client_api,
    fake_role_collection,
    fake_role_data,
    mock_authorized_http_bearer,
    mock_check_permissions_handler,
):
    fake_role_data.update({"name": "Manager"})
    response = await http_client_api.put(
        "/roles/66e85363aa07cb1e95d3e3d0", json=fake_role_data, headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json() == {
        "code_error": "roles/role-not-found",
        "message_error": "Role with '66e85363aa07cb1e95d3e3d0' not found.",
    }

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_update_user_bad_request(
    http_client_api,
    fake_role_collection,
    mock_authorized_http_bearer,
    mock_check_permissions_handler,
):
    role_id = fake_role_collection.id

    response = await http_client_api.put(f"/roles/{role_id}", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
    assert response.json() == {
        "code_error": "validation/request-validation-error",
        "message_error": "[{'field': 'body', 'message': 'Field required'}]",
    }

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_get_role_members_succes(
    http_client_api,
    fake_role_collection,
    fake_user_collection,
    mock_authorized_http_bearer,
    mock_check_permissions_handler,
):
    role = fake_role_collection.name

    response = await http_client_api.get(f"/roles/{role}/members", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["role"] == str(fake_user_collection.role)

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_delete_role_not_found(
    http_client_api,
    mock_authorized_http_bearer,
    mock_check_permissions_handler,
):
    response = await http_client_api.delete(
        "/roles/66e85363aa07cb1e95d3e3d0", headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()


async def test_delete_role_success(
    http_client_api,
    fake_role_collection,
    mock_authorized_http_bearer,
    mock_check_permissions_handler,
):
    role_id = fake_role_collection.id

    response = await http_client_api.delete(f"/roles/{role_id}", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text

    mock_authorized_http_bearer.assert_called_once()
    mock_authorized_http_bearer.assert_called_once_with("valid_token")
    mock_check_permissions_handler.assert_called_once()
