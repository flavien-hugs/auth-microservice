from urllib.parse import urljoin

from src.config import settings


API_VERIFY_ACCESS_TOKEN_ENDPOINT = urljoin(settings.API_AUTH_URL_BASE, settings.API_AUTH_CHECK_VALIDATE_ACCESS_TOKEN)
API_TRAILHUB_ENDPOINT = urljoin(settings.API_AUTH_URL_BASE, settings.API_TRAILHUB_ENDPOINT)
