import typer
import uvicorn

from src.config import settings

app = typer.Typer(pretty_exceptions_show_locals=False)


@app.command()
def run():
    uvicorn.run(
        "src:app",
        host=f"{settings.APP_HOSTNAME}",
        port=settings.APP_DEFAULT_PORT,
        reload=settings.APP_RELOAD,
        access_log=settings.APP_ACCESS_LOG,
        loop="uvloop",
    )


if __name__ == "__main__":
    app()
