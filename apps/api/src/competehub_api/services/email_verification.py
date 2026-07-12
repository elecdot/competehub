from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.parse import parse_qs, unquote, urlparse


@dataclass(frozen=True)
class SmtpEmailVerificationSender:
    host: str
    port: int
    from_address: str
    username: str | None
    password: str | None
    use_ssl: bool
    starttls: bool
    timeout: float = 10.0

    @classmethod
    def from_dsn(cls, dsn: str) -> SmtpEmailVerificationSender:
        parsed = urlparse(dsn)
        query = parse_qs(parsed.query)
        from_values = query.get("from", [])
        if parsed.scheme not in {"smtp", "smtps"} or not parsed.hostname or len(from_values) != 1:
            raise ValueError(
                "EMAIL_VERIFICATION_SENDER_DSN must be an smtp/smtps URL with one from query value"
            )

        username = unquote(parsed.username) if parsed.username else None
        password = unquote(parsed.password) if parsed.password else None
        if bool(username) != bool(password):
            raise ValueError(
                "EMAIL_VERIFICATION_SENDER_DSN must provide both SMTP username and password"
            )

        use_ssl = parsed.scheme == "smtps"
        starttls = _query_bool(query, "starttls", default=not use_ssl)
        if use_ssl and starttls:
            raise ValueError(
                "EMAIL_VERIFICATION_SENDER_DSN cannot enable starttls with the smtps scheme"
            )

        return cls(
            host=parsed.hostname,
            port=parsed.port or (465 if use_ssl else 587),
            from_address=from_values[0],
            username=username,
            password=password,
            use_ssl=use_ssl,
            starttls=starttls,
        )

    def send_verification_code(self, *, to: str, code: str) -> None:
        message = EmailMessage()
        message["Subject"] = "CompeteHub 邮箱验证码"
        message["From"] = self.from_address
        message["To"] = to
        message.set_content(f"你的 CompeteHub 邮箱验证码是：{code}\n\n验证码将在 15 分钟后失效。")

        client_type = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP
        with client_type(self.host, self.port, timeout=self.timeout) as client:
            if self.starttls:
                client.starttls()
            if self.username and self.password:
                client.login(self.username, self.password)
            client.send_message(message)


def configure_email_verification_sender(config: dict) -> None:
    if config.get("EMAIL_VERIFICATION_SENDER") is None:
        dsn = config.get("EMAIL_VERIFICATION_SENDER_DSN")
        if dsn:
            config["EMAIL_VERIFICATION_SENDER"] = SmtpEmailVerificationSender.from_dsn(dsn)
    if (
        config.get("PUBLIC_EMAIL_REGISTRATION_ENABLED")
        and config.get("EMAIL_VERIFICATION_SENDER") is None
    ):
        raise RuntimeError(
            "PUBLIC_EMAIL_REGISTRATION_ENABLED requires EMAIL_VERIFICATION_SENDER_DSN"
        )


def _query_bool(query: dict[str, list[str]], name: str, *, default: bool) -> bool:
    values = query.get(name)
    if values is None:
        return default
    if len(values) != 1 or values[0].casefold() not in {"true", "false"}:
        raise ValueError(f"EMAIL_VERIFICATION_SENDER_DSN {name} must be true or false")
    return values[0].casefold() == "true"
