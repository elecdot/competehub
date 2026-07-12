from competehub_api.tasks.celery_app import celery_app


def test_celery_app_loads_verification_delivery_task_and_schedule() -> None:
    celery_app.loader.import_default_modules()

    assert "competehub.auth.dispatch_verification_deliveries" in celery_app.tasks
    assert celery_app.conf.beat_schedule["dispatch-verification-delivery-outbox"] == {
        "task": "competehub.auth.dispatch_verification_deliveries",
        "schedule": 1.0,
    }
