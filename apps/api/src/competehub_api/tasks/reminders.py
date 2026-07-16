from __future__ import annotations

from competehub_api.services.messages import purge_expired_messages
from competehub_api.services.reminder_delivery import (
    dispatch_due_reminders as dispatch_due_reminders_service,
)
from competehub_api.services.reminder_delivery import (
    requeue_failed_reminders as requeue_failed_reminders_service,
)
from competehub_api.tasks.celery_app import celery_app


@celery_app.task(name="competehub.reminders.dispatch_due")
def dispatch_due_reminders() -> dict[str, int]:
    return dispatch_due_reminders_service()


@celery_app.task(name="competehub.reminders.requeue_failed")
def requeue_failed_reminders() -> dict[str, int]:
    return requeue_failed_reminders_service()


@celery_app.task(name="competehub.messages.purge_expired")
def purge_retained_messages() -> dict[str, int]:
    return purge_expired_messages()
