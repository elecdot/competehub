from __future__ import annotations

from celery import Celery

from competehub_api.app import create_app


def make_celery() -> Celery:
    flask_app = create_app()
    celery = Celery(
        flask_app.import_name,
        broker=flask_app.config["CELERY_BROKER_URL"],
        backend=flask_app.config["CELERY_RESULT_BACKEND"],
        include=[
            "competehub_api.tasks.outbound_clicks",
            "competehub_api.tasks.reminders",
            "competehub_api.tasks.verification_delivery",
        ],
    )
    celery.conf.task_ignore_result = True
    celery.conf.beat_schedule = {
        "dispatch-verification-delivery-outbox": {
            "task": "competehub.auth.dispatch_verification_deliveries",
            "schedule": 1.0,
        },
        "aggregate-recorded-outbound-clicks": {
            "task": "competehub.outbound_clicks.aggregate",
            "schedule": 3600.0,
        },
        "dispatch-due-reminders": {
            "task": "competehub.reminders.dispatch_due",
            "schedule": float(flask_app.config["REMINDER_DISPATCH_INTERVAL_SECONDS"]),
        },
        "requeue-failed-reminders": {
            "task": "competehub.reminders.requeue_failed",
            "schedule": float(flask_app.config["REMINDER_REQUEUE_INTERVAL_SECONDS"]),
        },
        "purge-expired-messages": {
            "task": "competehub.messages.purge_expired",
            "schedule": float(flask_app.config["MESSAGE_RETENTION_INTERVAL_SECONDS"]),
        },
    }

    class FlaskContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = FlaskContextTask
    return celery


celery_app = make_celery()
