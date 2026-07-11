from __future__ import annotations

from typing import Any

from flask import Flask

from competehub_api.blueprints import register_blueprints
from competehub_api.cli import register_cli_commands
from competehub_api.config import config_from_env
from competehub_api.errors import register_error_handlers
from competehub_api.extensions import init_extensions


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_from_env())

    if test_config:
        app.config.update(test_config)

    init_extensions(app)
    # Import models after extension setup so Flask-Migrate can discover metadata.
    import competehub_api.models  # noqa: F401

    register_blueprints(app)
    register_cli_commands(app)
    register_error_handlers(app)

    return app
