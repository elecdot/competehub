from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask

from competehub_api.blueprints import register_blueprints
from competehub_api.config import config_from_env
from competehub_api.e2e_seed import register_e2e_commands
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
    register_e2e_commands(app)
    register_error_handlers(app)

    return app


def create_e2e_app() -> Flask:
    """Create an app that can only use the workspace-local browser-test database."""
    repo_root = Path(__file__).resolve().parents[4]
    database_path = repo_root / ".cache" / "tmp" / "competehub-e2e.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    return create_app(
        {
            "TESTING": True,
            "E2E_TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )
