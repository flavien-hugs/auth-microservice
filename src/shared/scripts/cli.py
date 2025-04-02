from datetime import datetime, timezone

import pymongo
import typer
import yaml
from email_validator import EmailNotValidError, validate_email
from slugify import slugify

from src.config import settings
from .utils import BASE_URL, make_request

app = typer.Typer(pretty_exceptions_enable=False)


def check_validate_email(email: str):
    try:
        validate_email(email)
    except EmailNotValidError as exc:
        typer.echo(f"Invalid email address provided: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command(name="create-user", help="Create a first user for the application.")
def create_user():
    email = typer.prompt(text="Your Email (required)", type=str, err=True)
    check_validate_email(email)

    fullname = typer.prompt(text="Fullname (optional)", type=str, default="")
    phonenumber = typer.prompt(text="Phone number (optional)", type=str, default="")

    password = typer.prompt(
        text="Your password (required)",
        type=str,
        hide_input=True,
        confirmation_prompt=True,
    )

    payload = {
        "email": email,
        "fullname": fullname if fullname else None,
        "phonenumber": phonenumber if phonenumber else None,
        "password": password,
    }

    api_url = f"{BASE_URL}/users/add"
    response = make_request(method="post", url=api_url, json=payload)
    if response.is_success:
        typer.echo(f"User with '{email}' created successfully.")


@app.command(name="load-parms-data", help="Load params data")
def load_params_data(filepath: str):
    if not (mongodb_uri := settings.MONGODB_URI):
        raise ValueError("Missing MongoDB URI")

    if not (dbname := settings.MONGO_DB):
        raise ValueError("DB name not defined")

    if not (coll_name := settings.PARAM_MODEL_NAME):
        raise ValueError("Param collection not initialized")

    client = pymongo.MongoClient(mongodb_uri)

    try:
        db = client[dbname]
        coll = db[coll_name]

        with open(filepath) as fd:
            data = yaml.safe_load(fd)

        for value in data.get("params", []):
            name = value.get("name")
            items = value.get("data", [])

            for item in items:
                update_field = {
                    "type": name.upper(),
                    "name": item,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }

                slug_value = slug_value = slugify(f"{name}-{item}")

                coll.update_one(
                    {"slug": slug_value},
                    {"$set": update_field},
                    upsert=True,
                )
    finally:
        client.close()


@app.command(name="create-role-and-assign-permissions", help="Create a role and assign permissions")
def create_role_and_assign_permissions():
    """
    Command to create a role and optionally assign permissions to it.

    Prompts the user for a role name and optional permissions, then creates the role
    and assigns the specified permissions.

    Raises:
        typer.Exit: If the API request fails.
    """
    role_name = typer.prompt(text="Role name", type=str)
    permissions = typer.prompt(text="Permissions to assign (optional) (comma-separated)", type=str, default="")

    # Create role
    create_url = f"{BASE_URL}/roles/_create"
    ret = make_request(method="post", url=create_url, json={"name": role_name})

    if ret.is_success:
        role_data = ret.json()
        role_id = role_data.get("_id")
        typer.echo(f"Role '{role_name}' with ID {role_id} created successfully.")

        # Assign permissions
        if permissions:
            permissions_list = [perm.strip() for perm in permissions.split(",")]
            assign_url = f"{BASE_URL}/roles/{role_id}/_assign-permissions"
            response = make_request(method="patch", url=assign_url, json=permissions_list)
            if response.is_success:
                typer.echo(f"Permissions assigned to role '{role_name}' successfully.")
            else:
                typer.echo(f"Failed to assign permissions to role '{role_name}'.")
    else:
        typer.echo(f"Failed to create role '{role_name}'.")


if __name__ == "__main__":
    app()
