from flask import Blueprint

from app.core.response import success

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    return success({"status": "ok", "service": "competehub-api"})

