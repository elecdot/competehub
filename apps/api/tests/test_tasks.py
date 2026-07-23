from competehub_api.tasks.celery_app import celery_app


def test_celery_app_ignores_task_results_by_default() -> None:
    assert celery_app.conf.task_ignore_result is True


def test_celery_app_loads_verification_delivery_task_and_schedule() -> None:
    celery_app.loader.import_default_modules()

    assert "competehub.auth.dispatch_verification_deliveries" in celery_app.tasks
    assert celery_app.conf.beat_schedule["dispatch-verification-delivery-outbox"] == {
        "task": "competehub.auth.dispatch_verification_deliveries",
        "schedule": 1.0,
    }

    assert "competehub.reminders.dispatch_due" in celery_app.tasks
    assert "competehub.reminders.requeue_failed" in celery_app.tasks
    assert "competehub.messages.purge_expired" in celery_app.tasks
    assert celery_app.conf.beat_schedule["dispatch-due-reminders"] == {
        "task": "competehub.reminders.dispatch_due",
        "schedule": 15.0,
    }
    assert celery_app.conf.beat_schedule["requeue-failed-reminders"] == {
        "task": "competehub.reminders.requeue_failed",
        "schedule": 30.0,
    }
    assert celery_app.conf.beat_schedule["purge-expired-messages"] == {
        "task": "competehub.messages.purge_expired",
        "schedule": 86400.0,
    }
