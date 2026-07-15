from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from competehub_api.extensions import db
from competehub_api.models.enums import ReminderStatus, SubscriptionStatus
from competehub_api.models.mixins import TimestampMixin
from competehub_api.models.user import enum_values

if TYPE_CHECKING:
    from competehub_api.models.user import User


class Favorite(db.Model, TimestampMixin):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "competition_id",
            name="uq_favorites_user_competition",
        ),
    )


class Subscription(db.Model, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, values_callable=enum_values, name="subscription_status"),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remind_days: Mapped[int] = mapped_column(default=3, nullable=False)
    node_types: Mapped[list | None] = mapped_column(JSON)
    reminder_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "competition_id",
            name="uq_subscriptions_user_competition",
        ),
        db.CheckConstraint(
            "remind_days >= 0 AND remind_days <= 30",
            name="ck_subscriptions_remind_days_range",
        ),
    )


class ReminderSetting(db.Model, TimestampMixin):
    __tablename__ = "reminder_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_remind_days: Mapped[int] = mapped_column(default=3, nullable=False)
    node_types: Mapped[list | None] = mapped_column(JSON)

    user: Mapped[User] = relationship(back_populates="reminder_settings")


class Reminder(db.Model, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    time_node_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("competition_time_nodes.id"),
        nullable=False,
    )
    logical_node_key: Mapped[str] = mapped_column(String(120), nullable=False)
    time_node_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    node_type: Mapped[str] = mapped_column(String(80), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReminderStatus] = mapped_column(
        SAEnum(ReminderStatus, values_callable=enum_values, name="reminder_status"),
        default=ReminderStatus.PENDING,
        nullable=False,
        index=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(String(80))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "competition_id",
            "logical_node_key",
            "time_node_revision",
            name="uq_reminders_ordinary_plan",
        ),
    )


class Message(db.Model, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reminder_id: Mapped[int | None] = mapped_column(ForeignKey("reminders.id"))
    competition_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("competitions.id", name="fk_messages_competition_id_competitions"),
        index=True,
    )
    message_type: Mapped[str | None] = mapped_column(String(80), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160))
    event_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reminder: Mapped[Reminder | None] = relationship()

    __table_args__ = (
        db.UniqueConstraint("user_id", "idempotency_key", name="uq_message_user_event"),
    )
