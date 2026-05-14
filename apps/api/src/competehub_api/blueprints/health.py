from __future__ import annotations

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    return jsonify(
        {
            "data": {
                "service": "competehub-api",
                "status": "ok",
            },
            "error": None,
        }
    )
