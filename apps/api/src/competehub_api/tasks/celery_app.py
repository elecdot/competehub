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
            "competehub_api.tasks.reminders",
            "competehub_api.tasks.verification_delivery",
        ],
    )
    celery.conf.beat_schedule = {
        "dispatch-verification-delivery-outbox": {
            "task": "competehub.auth.dispatch_verification_deliveries",
            "schedule": 1.0,
        }
    }

    class FlaskContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = FlaskContextTask
    return celery


celery_app = make_celery()
