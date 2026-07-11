from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from competehub_api.extensions import db
from competehub_api.models.enums import IdentityVerificationStatus, UserRole, UserStatus
from competehub_api.models.mixins import TimestampMixin


def enum_values(enum_cls):
    return [item.value for item in enum_cls]


id_column_type = BigInteger().with_variant(Integer, "sqlite")


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(id_column_type, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    student_no: Mapped[str | None] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    session_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    capabilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
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

    identities: Mapped[list[UserIdentity]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    profile: Mapped[StudentProfile | None] = relationship(back_populates="user", uselist=False)


class UserIdentity(db.Model, TimestampMixin):
    __tablename__ = "user_identities"

    id: Mapped[int] = mapped_column(id_column_type, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    identity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False)
    display_value: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_status: Mapped[IdentityVerificationStatus] = mapped_column(
        SAEnum(
            IdentityVerificationStatus,
            values_callable=enum_values,
            name="identity_verification_status",
        ),
        default=IdentityVerificationStatus.PENDING,
        nullable=False,
    )
    verification_method: Mapped[str | None] = mapped_column(String(64))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="identities")
    challenges: Mapped[list[IdentityVerificationChallenge]] = relationship(
        back_populates="identity",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint("identity_type", "normalized_value", name="uq_identity_type_value"),
    )


class IdentityVerificationChallenge(db.Model, TimestampMixin):
    __tablename__ = "identity_verification_challenges"

    id: Mapped[int] = mapped_column(id_column_type, primary_key=True)
    user_identity_id: Mapped[int] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    identity: Mapped[UserIdentity] = relationship(back_populates="challenges")


class StudentProfile(db.Model, TimestampMixin):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(id_column_type, primary_key=True)
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
