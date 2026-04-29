from importlib import import_module

from flask import Flask

from app.api.v1 import api_v1
from app.cli import register_cli
from app.core.config import get_config
from app.core.errors import register_error_handlers
from app.extensions import bcrypt, cors, db, jwt, migrate


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    register_extensions(app)
    import_module("app.models")
    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)

    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(api_v1, url_prefix=app.config["API_V1_PREFIX"])
