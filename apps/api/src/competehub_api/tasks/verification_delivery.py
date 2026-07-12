from __future__ import annotations

from competehub_api.services.verification_delivery import dispatch_verification_deliveries
from competehub_api.tasks.celery_app import celery_app


@celery_app.task(name="competehub.auth.dispatch_verification_deliveries")
def dispatch_verification_delivery_outbox() -> dict[str, int]:
    return dispatch_verification_deliveries()
