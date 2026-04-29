from flask import Blueprint

from app.api.v1.admin import admin_bp
from app.api.v1.auth import auth_bp
from app.api.v1.competitions import competitions_bp
from app.api.v1.forum import forum_bp
from app.api.v1.health import health_bp
from app.api.v1.recommendations import recommendations_bp
from app.api.v1.reminders import reminders_bp
from app.api.v1.users import users_bp

api_v1 = Blueprint("api_v1", __name__)

api_v1.register_blueprint(health_bp)
api_v1.register_blueprint(auth_bp, url_prefix="/auth")
api_v1.register_blueprint(users_bp, url_prefix="/users")
api_v1.register_blueprint(competitions_bp, url_prefix="/competitions")
api_v1.register_blueprint(recommendations_bp, url_prefix="/recommendations")
api_v1.register_blueprint(reminders_bp, url_prefix="/reminders")
api_v1.register_blueprint(forum_bp, url_prefix="/forum")
api_v1.register_blueprint(admin_bp, url_prefix="/admin")

