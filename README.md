# [AUTH-MICROSERVICE](https://github.com/flavien-hugs/auth-microservice.git)

This microservice provides endpoints for user authentication and management.

### Requirements

* [Python3](https://python.org)
* [Poetry](https://python-poetry.org)
* [Docker](https://docker.com)
* [FastAPI](https://fastapi.tiangolo.com)
* [Beanie-odm](https://beanie-odm.dev)
* [Mongodb](https://www.mongodb.com)
* [fastapi-pagination](https://uriyyo-fastapi-pagination.netlify.app)
* [python-slugify](https://github.com/un33k/python-slugify)

### Usage

* Clone repository
```shell
git clone https://github.com/flavien-hugs/auth-microservice.git
cd auth-microservice
```

* Add `common` submodule
```shell
git submodule add https://github.com/flavien-hugs/backend-common-code.git src/common
```

* Update local `common` submodule
```shell
git submodule update --remote --merge
```

### Configuration:

Create a `.env` file in the project root and add the following configurations:

<blockquote>

#### Config de l'application

**APP_NAME** :  Application name.
> Exemple: `APP_NAME="Auth and User Manager"`

**APP_TITLE** :  Application title.
> Exemple: `APP_TITLE="My Application"`

**APP_HOSTNAME** : The IP address or host name on which the application is listening.
> Exemple: `APP_HOSTNAME="0.0.0.0"`

**APP_DEFAULT_PORT** : The default port on which the application listens.
> Exemple: `APP_DEFAULT_PORT=8000`
</blockquote>

<blockquote>

#### MONGO DB Configuration

**MONGO_DB**: Name of the MongoDB database used by the application.
> Exemple: `MONGO_DB="devices"`

**MONGODB_URI**: MongoDB connection URI, specifying connection protocol, host, port, and target database.
> Exemple: `MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@{MONGODB_INSTANCE_DOCKER}:${MONGO_PORT}`

**MONGO_HOST**: The IP address or host name where MongoDB is hosted.
 "Localhost" means that MongoDB runs on the same machine as the application.
> Exemple: `MONGO_HOST="O.O.O.O"`

**MONGO_PORT**: The port on which MongoDB listens.
> Exemple: `MONGO_PORT=27017`

**MONGO_USER**: User name to connect to MongoDB.
> Exemple: `MONGO_USER="ChangeMe"`

**MONGO_PASSWORD**: User name to connect to MongoDB.
> Exemple: `MONGO_PASSWORD="pA55word"`
</blockquote>

* Run the following command to start the project with docker.

```shell
docker compose --env-file=.env up
```

- Then go to `http://0.0.0.0:9001/${APP_NAME}/docs#/` to see the documentation (swagger).
