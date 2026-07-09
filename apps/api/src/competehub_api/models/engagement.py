from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from competehub_api.extensions import db
from competehub_api.models.enums import ReminderStatus, SubscriptionStatus
from competehub_api.models.mixins import TimestampMixin
from competehub_api.models.user import enum_values

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class Favorite(db.Model, TimestampMixin):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Subscription(db.Model, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
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


class ReminderSetting(db.Model, TimestampMixin):
    __tablename__ = "reminder_settings"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_remind_days: Mapped[int] = mapped_column(default=3, nullable=False)
    node_types: Mapped[list | None] = mapped_column(JSON)


class Reminder(db.Model, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    time_node_id: Mapped[int | None] = mapped_column(ForeignKey("competition_time_nodes.id"))
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
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(db.Model, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reminder_id: Mapped[int | None] = mapped_column(ForeignKey("reminders.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reminder: Mapped[Reminder | None] = relationship()
