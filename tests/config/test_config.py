import os
from unittest import mock

import pytest
from slugify import slugify

from src.config import settings, shutdown_db, startup_db


@pytest.mark.asyncio
async def test_app_startup(mock_app_instance, fixture_models):
    assert mock_app_instance.mongo_db_client is not None

    admin_role = await fixture_models.Role.find_one({"slug": slugify(os.getenv("DEFAULT_ADMIN_ROLE"))})
    assert admin_role is None, "Le rôle admin n'a pas été créé"

    admin_user = await fixture_models.User.find_one({"email": os.getenv("DEFAULT_ADMIN_EMAIL")})
    assert admin_user is None, "L'utilisateur admin n'a pas été créé"

    from src.shared import blacklist_token

    assert blacklist_token.init_blacklist_token_file(), "Le fichier de blacklist de tokens n'a pas été initialisé"

    from src.common.helpers.appdesc import load_app_description, load_permissions

    assert (
        load_app_description(mock_app_instance.mongo_db_client) is not None
    ), "La description de l'application n'a pas été chargée"
    assert load_permissions(mock_app_instance.mongo_db_client) is not None, "Les permissions n'ont pas été chargées"


@pytest.mark.asyncio
@mock.patch("src.config.settings")
@mock.patch("src.config.database.init_beanie", return_value=None)
async def test_startup_db(mock_settings, mock_init_beanie, mock_mongodb_client, mock_app_instance, fixture_models):
    mock_settings.return_value = mock.Mock(MONGODB_URI=settings.MONGODB_URI, DB_NAME=settings.MONGODB_URI)

    await startup_db(app=mock_app_instance, models=[fixture_models.User, fixture_models.Role])

    mock_settings.assert_called_once()
    assert mock_app_instance.mongo_db_client is not None
    assert mock_mongodb_client.is_mongos is True


@pytest.mark.asyncio
async def test_shutdown_db(mock_app_instance):
    mock_app_instance.mongo_db_client = mock.AsyncMock()
    await shutdown_db(app=mock_app_instance)
    mock_app_instance.mongo_db_client.close.assert_called_once()
