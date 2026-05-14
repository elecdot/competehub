from __future__ import annotations

from competehub_api.tasks.celery_app import celery_app


@celery_app.task(name="competehub.reminders.dispatch_due")
def dispatch_due_reminders() -> dict[str, int]:
    # Reminder dispatch will query pending reminders and create messages idempotently.
    return {"dispatched": 0}
