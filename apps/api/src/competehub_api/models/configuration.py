from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from competehub_api.extensions import db
from competehub_api.models.enums import RecommendationRuleSetStatus
from competehub_api.models.mixins import TimestampMixin
from competehub_api.models.user import enum_values

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class RecommendationRuleSet(db.Model, TimestampMixin):
    __tablename__ = "recommendation_rule_sets"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        Index(
            "uq_recommendation_rule_sets_active",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    status: Mapped[RecommendationRuleSetStatus] = mapped_column(
        SAEnum(
            RecommendationRuleSetStatus,
            values_callable=enum_values,
            name="recommendation_rule_set_status",
        ),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    submitted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    cloned_from_rule_set_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendation_rule_sets.id")
    )
    base_rule_set_id: Mapped[int | None] = mapped_column(ForeignKey("recommendation_rule_sets.id"))
    review_comment: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rules: Mapped[list[RecommendationRule]] = relationship(
        back_populates="rule_set",
        cascade="all, delete-orphan",
        order_by="RecommendationRule.code",
    )


class RecommendationRule(db.Model, TimestampMixin):
    __tablename__ = "recommendation_rules"
    __table_args__ = (
        CheckConstraint("weight >= 1 AND weight <= 100", name="weight_range"),
        UniqueConstraint("rule_set_id", "code", name="uq_recommendation_rules_rule_set_code"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    rule_set_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_rule_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    weight: Mapped[int] = mapped_column(nullable=False)
    conditions: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason_template: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    rule_set: Mapped[RecommendationRuleSet] = relationship(back_populates="rules")


class SystemConfig(db.Model, TimestampMixin):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    value: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
