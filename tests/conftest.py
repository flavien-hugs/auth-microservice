from unittest import mock

import faker
import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import AsyncClient
from mongomock_motor import AsyncMongoMockClient

from src.config import settings, jwt_settings


@pytest.fixture
def fake_data():
    return faker.Faker()


@pytest.fixture()
def fixture_models():
    from src import models

    return models


@pytest.fixture
async def mock_app_instance():
    from src import app as mock_app

    yield mock_app


@pytest.fixture(autouse=True)
async def mock_mongodb_client(mock_app_instance, fixture_models):
    client = AsyncMongoMockClient()
    mock_app_instance.mongo_db_client = client[settings.MONGO_DB]
    await init_beanie(
        database=mock_app_instance.mongo_db_client,
        document_models=[fixture_models.User, fixture_models.Role],
    )
    yield client


@pytest.fixture(autouse=True)
async def clean_db(fixture_models, mock_mongodb_client):
    for model in [fixture_models.User, fixture_models.Role]:
        await model.delete_all()


@pytest.fixture()
def mock_authorize_bearer():
    with mock.patch("src.routers.users.AuthorizeHTTPBearer.__call__", return_value=True):
        yield


@pytest.fixture()
def mock_chek_permissions_handler():
    with mock.patch("src.routers.users.CheckPermissionsHandler.__call__", return_value=True):
        yield


@pytest.fixture(autouse=True)
async def http_client_api(mock_app_instance, clean_db):
    async with AsyncClient(
        app=mock_app_instance,
        base_url="http://auth.localhost.com",
        follow_redirects=True,
    ) as client:
        yield client


@pytest.fixture()
def fake_jwt_access_bearer():
    class FakeJwtAccessBearer:
        def __init__(self, secret_key, algorithm, access_expires_delta, refresh_expires_delta):
            self.secret_key = secret_key
            self.algorithm = algorithm
            self.access_expires_delta = access_expires_delta
            self.refresh_expires_delta = refresh_expires_delta

        @staticmethod
        def create_access_token(subject, expires_delta, unique_identifier):
            return "fake_access_token"

        @staticmethod
        def create_refresh_token(subject, expires_delta, unique_identifier):
            return "fake_refresh_token"

    return FakeJwtAccessBearer


@pytest.fixture
def mock_jwt_settings(monkeypatch):
    class MockJwtSettings:
        JWT_SECRET_KEY = jwt_settings.JWT_SECRET_KEY
        JWT_ALGORITHM = jwt_settings.JWT_ALGORITHM
        ACCESS_TOKEN_EXPIRE_MINUTES = jwt_settings.ACCESS_TOKEN_EXPIRE_MINUTES
        REFRESH_TOKEN_EXPIRE_MINUTES = jwt_settings.REFRESH_TOKEN_EXPIRE_MINUTES

    monkeypatch.setattr("src.config.jwt_settings", MockJwtSettings())


@pytest.fixture()
def fake_role_data(fake_data):
    return {
        "name": fake_data.unique.name(),
        "description": fake_data.text(),
        "permissions": [
            {
                "service_info": {"name": fake_data.name().lower(), "title": fake_data.name()},
                "permissions": [{"code": f"perm-{i}"} for i in range(1, 2)],
            }
        ],
    }


@pytest_asyncio.fixture()
async def fake_role_collection(fixture_models, fake_role_data):
    result = await fixture_models.Role(**fake_role_data).create()
    return result


@pytest.fixture()
def fake_user_data(fake_role_collection, fake_data):
    return {
        "email": fake_data.unique.email().lower(),
        "fullname": fake_data.name(),
        "role": str(fake_role_collection.id),
        "attributes": {"city": fake_data.city()},
        "password": fake_data.password(),
    }


@pytest_asyncio.fixture()
async def fake_user_collection(fixture_models, fake_user_data):
    result = await fixture_models.User(**fake_user_data).create()
    return result
