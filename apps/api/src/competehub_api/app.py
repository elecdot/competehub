from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask
from flask.sessions import SecureCookieSessionInterface
from itsdangerous import SignatureExpired, TimestampSigner

from competehub_api.blueprints import register_blueprints
from competehub_api.cli import register_cli_commands
from competehub_api.config import config_from_env
from competehub_api.e2e_seed import register_e2e_commands
from competehub_api.errors import register_error_handlers
from competehub_api.extensions import init_extensions
from competehub_api.services.email_verification import configure_email_verification_sender


class _E2ETimestampSigner(TimestampSigner):
    """Keep browser tests stable across a one-second host clock correction."""

    def unsign(
        self,
        signed_value: str | bytes,
        max_age: int | None = None,
        return_timestamp: bool = False,
    ):
        try:
            return super().unsign(signed_value, max_age, return_timestamp)
        except SignatureExpired as error:
            if error.date_signed is None:
                raise
            future_skew = int(error.date_signed.timestamp()) - self.get_timestamp()
            if not 0 < future_skew <= 1:
                raise
            return super().unsign(signed_value, None, return_timestamp)


class _E2ESessionInterface(SecureCookieSessionInterface):
    def get_signing_serializer(self, app: Flask):
        serializer = super().get_signing_serializer(app)
        if serializer is not None:
            serializer.signer = _E2ETimestampSigner
        return serializer


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_from_env())

    if test_config:
        app.config.update(test_config)

    if app.config.get("E2E_TESTING"):
        app.session_interface = _E2ESessionInterface()

    configure_email_verification_sender(app.config)
    init_extensions(app)
    # Import models after extension setup so Flask-Migrate can discover metadata.
    import competehub_api.models  # noqa: F401

    register_blueprints(app)
    register_cli_commands(app)
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
            "AUTH_RATE_LIMIT_ENABLED": False,
            "OUTBOUND_RATE_LIMIT_ENABLED": False,
        }
    )
