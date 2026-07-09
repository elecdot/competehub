from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from competehub_api.extensions import db
from competehub_api.models.enums import UserRole, UserStatus
from competehub_api.models.mixins import TimestampMixin

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


def enum_values(enum_cls):
    return [item.value for item in enum_cls]


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    student_no: Mapped[str | None] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, values_callable=enum_values, name="user_role"),
        default=UserRole.STUDENT,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, values_callable=enum_values, name="user_status"),
        default=UserStatus.ACTIVE,
        nullable=False,
    )

    profile: Mapped[StudentProfile | None] = relationship(back_populates="user", uselist=False)


class StudentProfile(db.Model, TimestampMixin):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    college: Mapped[str | None] = mapped_column(String(120))
    major: Mapped[str | None] = mapped_column(String(120))
    grade: Mapped[str | None] = mapped_column(String(40))
    interest_tags: Mapped[list | None] = mapped_column(JSON)
    competition_experience: Mapped[str | None] = mapped_column(Text)
    goal_preferences: Mapped[list | None] = mapped_column(JSON)
    blocked_tags: Mapped[list | None] = mapped_column(JSON)
    default_remind_days: Mapped[int] = mapped_column(default=3, nullable=False)
    message_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="profile")
