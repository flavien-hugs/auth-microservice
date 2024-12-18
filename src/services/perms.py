import os

from src import settings
from src.common.config.mongo_client import config_mongodb_client


async def get_all_permissions():
    client = await config_mongodb_client(mongodb_uri=settings.MONGODB_URI)

    app_db_name, app_coll_name = os.getenv("APP_DESC_DB_COLLECTION").split(".")
    _, perm_coll_name = os.getenv("PERMS_DB_COLLECTION").split(".")

    db = client[app_db_name]
    app_coll = db[app_coll_name]

    lookups = [
        {
            "$lookup": {
                "from": perm_coll_name,
                "localField": "app",
                "foreignField": "app",
                "as": "permissions",
            }
        },
        {"$sort": {"app": 1}},
    ]

    items = await app_coll.aggregate(lookups).to_list(length=None)

    result = [
        {
            **doc,
            "_id": str(doc["_id"]),
            "permissions": [perm for perm in doc["permissions"][0]["permissions"]],
        }
        for doc in items
    ]

    return result
