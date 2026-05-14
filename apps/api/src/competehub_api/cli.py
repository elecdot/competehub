from __future__ import annotations

from competehub_api.app import create_app


def main() -> None:
    app = create_app()
    print(f"CompeteHub API ready: {app.name}")
