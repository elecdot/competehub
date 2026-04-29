from celery import Celery

from app.core.config import BaseConfig


celery_app = Celery(
    "competehub",
    broker=BaseConfig.REDIS_URL,
    backend=BaseConfig.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
)

