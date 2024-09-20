import pymongo
import typer
import yaml
from slugify import slugify
from datetime import datetime, timezone
from src.config import settings

app = typer.Typer(pretty_exceptions_enable=False)


@app.command(help="Load params data")
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


if __name__ == "__main__":
    app()
