from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from competehub_api.extensions import db
from competehub_api.models.mixins import TimestampMixin

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class OutboundClickEvent(db.Model, TimestampMixin):
    __tablename__ = "outbound_click_events"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False, index=True
    )
    competition_revision_id: Mapped[int] = mapped_column(
        ForeignKey("competition_revisions.id"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_surface: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    aggregated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )


class OutboundClickDailyStat(db.Model, TimestampMixin):
    __tablename__ = "outbound_click_daily_stats"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_surface: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "stat_date",
            "competition_id",
            "target_type",
            "source_surface",
            "actor_kind",
            name="uq_outbound_click_daily_stat_dimensions",
        ),
    )
