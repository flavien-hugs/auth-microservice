import typer
import httpx
from src.config import settings

app = typer.Typer(pretty_exceptions_enable=False)

BASE_URL = f"http://0.0.0.0:{settings.APP_DEFAULT_PORT}"


def make_request(method: str, url: str, access_token: str, json=None, data=None):
    headers = {"Authorization": f"Bearer {access_token}", "accept": "application/json"}
    with httpx.Client(timeout=30) as client:
        response = getattr(client, method)(url, headers=headers, json=json, data=data)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        typer.echo(f"API error: {exc.response.text}", err=True)
        raise typer.Exit(code=1) from exc

    return response.json()


@app.command(help="Create a role and assign permissions")
def create_role_and_assign_permissions():
    role_name = typer.prompt(text="Role name", type=str)
    access_token = typer.prompt(text="Access token", hide_input=True, type=str)
    permissions = typer.prompt(text="Permissions to assign (optional) (comma-separated)", type=str, default="")

    # Create role
    create_url = f"{BASE_URL}/roles"
    role_data = make_request("post", create_url, access_token, json={"name": role_name})
    role_id = role_data["_id"]
    typer.echo(f"Role '{role_name}' with ID {role_id} created successfully.")

    # Assign permissions
    if permissions:
        permissions_list = [perm.strip() for perm in permissions.split(",")]
        assign_url = f"{BASE_URL}/roles/{role_id}/assign-permissions"
        make_request("patch", assign_url, access_token, json=permissions_list)
        typer.echo(f"Permissions assigned to role '{role_name}' successfully.")


if __name__ == "__main__":
    app()
