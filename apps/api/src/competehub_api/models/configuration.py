from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from competehub_api.extensions import db
from competehub_api.models.mixins import TimestampMixin


class RecommendationRule(db.Model, TimestampMixin):
    __tablename__ = "recommendation_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    weight: Mapped[int] = mapped_column(default=1, nullable=False)
    conditions: Mapped[dict | None] = mapped_column(JSON)
    reason_template: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SystemConfig(db.Model, TimestampMixin):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    value: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
