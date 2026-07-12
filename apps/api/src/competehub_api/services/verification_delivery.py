from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from flask import current_app
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from competehub_api.extensions import db
from competehub_api.models import IdentityVerificationChallenge, VerificationDeliveryOutbox


def derive_verification_code(delivery_nonce: str) -> str:
    secret_key = str(current_app.config["SECRET_KEY"]).encode()
    digest = hmac.new(secret_key, delivery_nonce.encode(), hashlib.sha256).digest()
    return f"{int.from_bytes(digest, byteorder='big') % 1_000_000:06d}"


def dispatch_verification_deliveries(*, limit: int | None = None) -> dict[str, int]:
    sender = current_app.config.get("EMAIL_VERIFICATION_SENDER")
    if sender is None:
        return {"delivered": 0, "discarded": 0, "failed": 0}

    now = datetime.now(UTC)
    batch_size = limit or current_app.config.get("VERIFICATION_DELIVERY_BATCH_SIZE", 100)
    deliveries = db.session.scalars(
        select(VerificationDeliveryOutbox)
        .options(
            joinedload(VerificationDeliveryOutbox.challenge).joinedload(
                IdentityVerificationChallenge.identity
            )
        )
        .where(
            VerificationDeliveryOutbox.delivered_at.is_(None),
            VerificationDeliveryOutbox.discarded_at.is_(None),
            VerificationDeliveryOutbox.available_at <= now,
        )
        .order_by(VerificationDeliveryOutbox.id)
        .limit(batch_size)
        .with_for_update(of=VerificationDeliveryOutbox, skip_locked=True)
    ).all()

    result = {"delivered": 0, "discarded": 0, "failed": 0}
    for delivery in deliveries:
        challenge = delivery.challenge
        if (
            delivery.delivery_nonce is None
            or challenge.consumed_at is not None
            or _as_utc(challenge.expires_at) <= now
        ):
            delivery.discarded_at = now
            delivery.delivery_nonce = None
            result["discarded"] += 1
            continue

        code = derive_verification_code(delivery.delivery_nonce)
        try:
            sender.send_verification_code(to=challenge.identity.display_value, code=code)
        except Exception as error:  # noqa: BLE001 - delivery failures are retryable worker data
            delivery.attempt_count += 1
            delivery.available_at = now + timedelta(seconds=min(2**delivery.attempt_count, 300))
            delivery.last_error = type(error).__name__[:255]
            result["failed"] += 1
        else:
            delivery.delivered_at = now
            delivery.delivery_nonce = None
            delivery.last_error = None
            result["delivered"] += 1

    db.session.commit()
    return result


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
