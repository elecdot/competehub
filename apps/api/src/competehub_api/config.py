from __future__ import annotations

import os


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///competehub_dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    JSON_SORT_KEYS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    EMAIL_VERIFICATION_SENDER = None
    AUTH_TRUST_PROXY_HEADERS = False
    AUTH_VERIFICATION_MAX_ATTEMPTS = 5
    AUTH_RATE_LIMIT_ENABLED = True
    AUTH_RATE_LIMIT_MAX_ATTEMPTS = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS = 60


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def config_from_env() -> type[BaseConfig]:
    env = os.getenv("COMPETEHUB_ENV", "development").lower()
    if env == "testing":
        return TestingConfig
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig
