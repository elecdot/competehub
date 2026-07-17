from __future__ import annotations

from flask import Flask

from competehub_api.blueprints.admin import admin_bp
from competehub_api.blueprints.auth import auth_bp
from competehub_api.blueprints.competitions import competitions_bp
from competehub_api.blueprints.health import health_bp
from competehub_api.blueprints.me import me_bp
from competehub_api.blueprints.recommendation_rule_sets import recommendation_rule_sets_bp
from competehub_api.blueprints.recommendations import recommendations_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(admin_bp, url_prefix="/api/v1")
    app.register_blueprint(competitions_bp, url_prefix="/api/v1")
    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(me_bp, url_prefix="/api/v1")
    app.register_blueprint(recommendation_rule_sets_bp, url_prefix="/api/v1")
    app.register_blueprint(recommendations_bp, url_prefix="/api/v1")
