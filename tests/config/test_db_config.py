from unittest import mock

import pytest

from src.config import settings, shutdown_db, startup_db


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
