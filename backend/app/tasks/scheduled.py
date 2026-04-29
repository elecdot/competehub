from app.tasks.celery_app import celery_app


@celery_app.task(name="competition.refresh_status")
def refresh_competition_status():
    return {"status": "queued"}


@celery_app.task(name="reminder.generate_due_notifications")
def generate_due_notifications():
    return {"status": "queued"}

