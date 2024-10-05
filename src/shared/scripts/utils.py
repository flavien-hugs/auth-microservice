from typing import Optional, Union

import httpx
import typer

from src.config import settings

BASE_URL = f"http://127.0.0.1:{settings.APP_DEFAULT_PORT}"


def make_request(
    method: str,
    url: str,
    access_token: Optional[str] = None,
    json: Optional[Union[str, dict, list]] = None,
    data: Optional[Union[str, dict, list]] = None,
):
    """
    Make an HTTP request using the specified method.

    Args:
        method (str): The HTTP method to use (e.g., 'get', 'post', 'patch').
        url (str): The URL to send the request to.
        access_token (str, optional): The access token for authorization. Defaults to None.
        json (dict, optional): The JSON payload to send with the request. Defaults to None.
        data (dict, optional): The form data to send with the request. Defaults to None.

    Returns:
        dict: The JSON response from the API.

    Raises:
        typer.Exit: If the API request fails.
    """
    headers = {"Authorization": f"Bearer {access_token}", "accept": "application/json"}
    with httpx.Client(timeout=30) as client:
        response = getattr(client, method)(url, headers=headers, json=json, data=data)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        typer.echo(f"API error: {exc.response.text}", err=True)
        raise typer.Exit(code=1) from exc

    return response
