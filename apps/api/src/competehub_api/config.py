from __future__ import annotations

import os


def _env_bool(name: str, *, default: bool = False) -> bool:
    return os.getenv(name, str(default)).casefold() == "true"


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
    EMAIL_VERIFICATION_SENDER_DSN = os.getenv("EMAIL_VERIFICATION_SENDER_DSN")
    PUBLIC_EMAIL_REGISTRATION_ENABLED = _env_bool("PUBLIC_EMAIL_REGISTRATION_ENABLED")
    AUTH_TRUST_PROXY_HEADERS = False
    AUTH_VERIFICATION_MAX_ATTEMPTS = 5
    AUTH_RATE_LIMIT_ENABLED = True
    AUTH_RATE_LIMIT_MAX_ATTEMPTS = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS = 60
    PROFILE_ALLOWED_GRADES = ("大一", "大二", "大三", "大四", "研一", "研二", "研三")
    PROFILE_ALLOWED_MAJORS_BY_COLLEGE = {
        "计算机学院": ("软件工程", "计算机科学与技术", "人工智能", "网络工程"),
        "经济管理学院": ("金融学", "工商管理", "会计学"),
    }
    PROFILE_ALLOWED_INTEREST_TAGS = (
        "人工智能",
        "创新创业",
        "程序设计",
        "数据分析",
        "数学建模",
        "网络安全",
    )


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
