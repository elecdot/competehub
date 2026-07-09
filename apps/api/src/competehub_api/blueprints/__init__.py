from __future__ import annotations

from flask import Flask

from competehub_api.blueprints.admin import admin_bp
from competehub_api.blueprints.health import health_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(admin_bp, url_prefix="/api/v1")
    app.register_blueprint(health_bp, url_prefix="/api/v1")
