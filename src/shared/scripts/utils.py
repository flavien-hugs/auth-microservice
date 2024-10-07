from typing import Optional, Union

import httpx
import typer

from src.config import settings

BASE_URL = f"http://127.0.0.1:{settings.APP_DEFAULT_PORT}"


def make_request(
    method: str,
    url: str,
    access_token: Optional[str] = None,
    params: Optional[dict] = None,
    json: Optional[Union[str, dict, list]] = None,
    data: Optional[Union[str, dict, list]] = None,
) -> httpx.Response:
    """
    Make an HTTP request using the specified method.
    Returns:
        dict: The JSON response from the API.
    Raises:
        typer.Exit: If the API request fails.
    """
    headers = {"Authorization": f"Bearer {access_token}", "accept": "application/json"}
    with httpx.Client(timeout=30) as client:
        if method.lower() in ("get", "delete", "head"):
            response = getattr(client, method)(url, headers=headers, params=params)
        elif method.lower() in ("post", "put", "patch"):
            response = client.request(method, url, headers=headers, params=params, json=json, data=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        typer.echo(f"API error: {exc.response.text}", err=True)
        raise typer.Exit(code=1) from exc

    return response
