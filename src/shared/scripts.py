import httpx
import typer
from email_validator import EmailNotValidError, validate_email

from src.config import settings

create_first_user = typer.Typer(pretty_exceptions_enable=False)


def check_validate_email(email: str):
    try:
        validate_email(email)
    except EmailNotValidError as exc:
        typer.echo(f"Invalid email address provided: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@create_first_user.command(help="Create a first user to application.")
def create_first_user():
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

    api_url = f"http://0.0.0.0:{settings.APP_DEFAULT_PORT}/users/add"

    with httpx.Client(timeout=30) as client:
        response = client.post(api_url, json=payload)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        typer.echo(f"API error: {exc.response.text}", err=True)

    if response.is_success:
        typer.echo(f"User with '{email}' created successfully.")


if __name__ == "__main__":
    create_first_user()
