from typing import Any

from flask import jsonify


def success(data: Any = None, message: str = "success", code: int = 0, status: int = 200):
    return jsonify({"code": code, "message": message, "data": data}), status


def fail(message: str, code: int = 40000, status: int = 400, data: Any = None):
    return jsonify({"code": code, "message": message, "data": data}), status

