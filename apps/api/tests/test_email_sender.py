from __future__ import annotations

from email.message import EmailMessage

import pytest

from competehub_api import create_app
from competehub_api.services.email_verification import SmtpEmailVerificationSender


class FakeSmtpClient:
    def __init__(self, host: str, port: int, *, timeout: float) -> None:
        self.connection = (host, port, timeout)
        self.started_tls = False
        self.credentials: tuple[str, str] | None = None
        self.message: EmailMessage | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.credentials = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


def test_app_builds_real_sender_from_smtp_dsn(monkeypatch) -> None:
    created_clients: list[FakeSmtpClient] = []

    def create_client(host: str, port: int, *, timeout: float) -> FakeSmtpClient:
        client = FakeSmtpClient(host, port, timeout=timeout)
        created_clients.append(client)
        return client

    monkeypatch.setattr("smtplib.SMTP", create_client)
    app = create_app(
        {
            "TESTING": True,
            "EMAIL_VERIFICATION_SENDER_DSN": (
                "smtp://mailer:secret@smtp.example.edu:587"
                "?from=CompeteHub%20%3Cnoreply%40example.edu%3E&starttls=true"
            ),
            "PUBLIC_EMAIL_REGISTRATION_ENABLED": True,
        }
    )

    sender = app.config["EMAIL_VERIFICATION_SENDER"]
    assert isinstance(sender, SmtpEmailVerificationSender)

    sender.send_verification_code(to="student@example.edu", code="123456")

    client = created_clients[0]
    assert client.connection == ("smtp.example.edu", 587, 10.0)
    assert client.started_tls is True
    assert client.credentials == ("mailer", "secret")
    assert client.message is not None
    assert client.message["From"] == "CompeteHub <noreply@example.edu>"
    assert client.message["To"] == "student@example.edu"
    assert "123456" in client.message.get_content()


def test_app_rejects_invalid_sender_dsn() -> None:
    with pytest.raises(ValueError, match="EMAIL_VERIFICATION_SENDER_DSN"):
        create_app(
            {
                "TESTING": True,
                "EMAIL_VERIFICATION_SENDER_DSN": "smtp://smtp.example.edu:587",
            }
        )


def test_app_rejects_enabled_registration_without_sender() -> None:
    with pytest.raises(RuntimeError, match="PUBLIC_EMAIL_REGISTRATION_ENABLED"):
        create_app(
            {
                "TESTING": True,
                "EMAIL_VERIFICATION_SENDER": None,
                "EMAIL_VERIFICATION_SENDER_DSN": None,
                "PUBLIC_EMAIL_REGISTRATION_ENABLED": True,
            }
        )
