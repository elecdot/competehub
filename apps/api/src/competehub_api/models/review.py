from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from competehub_api.extensions import db
from competehub_api.models.enums import ReviewStatus
from competehub_api.models.mixins import TimestampMixin
from competehub_api.models.user import enum_values

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class ReviewRecord(db.Model, TimestampMixin):
    __tablename__ = "review_records"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    submitted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ReviewStatus] = mapped_column(
        SAEnum(ReviewStatus, values_callable=enum_values, name="review_status"),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    differences: Mapped[list | None] = mapped_column(JSON)
    impact: Mapped[dict | None] = mapped_column(JSON)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(db.Model, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    result: Mapped[str] = mapped_column(String(80), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON)
