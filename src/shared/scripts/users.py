import typer
from email_validator import EmailNotValidError, validate_email

from .utils import BASE_URL, make_request

app = typer.Typer(pretty_exceptions_enable=False)


def check_validate_email(email: str):
    try:
        validate_email(email)
    except EmailNotValidError as exc:
        typer.echo(f"Invalid email address provided: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command(help="Create a first user for the application.")
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


if __name__ == "__main__":
    app()
