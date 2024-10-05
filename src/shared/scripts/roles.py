import typer

from .utils import BASE_URL, make_request

app = typer.Typer(pretty_exceptions_enable=False)


@app.command(help="Create a role and assign permissions")
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
