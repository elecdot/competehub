from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from competehub_api.extensions import db
from competehub_api.models.enums import CompetitionStatus
from competehub_api.models.mixins import TimestampMixin
from competehub_api.models.user import enum_values

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class Competition(db.Model, TimestampMixin):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    short_title: Mapped[str | None] = mapped_column(String(120), index=True)
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    organizer: Mapped[str | None] = mapped_column(String(255))
    host: Mapped[str | None] = mapped_column(String(255))
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    official_url: Mapped[str | None] = mapped_column(String(1024))
    attachment_url: Mapped[str | None] = mapped_column(String(1024))
    summary: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    eligibility: Mapped[str | None] = mapped_column(Text)
    team_size: Mapped[str | None] = mapped_column(String(120))
    participant_form: Mapped[str | None] = mapped_column(String(120))
    suitable_majors: Mapped[list | None] = mapped_column(JSON)
    suitable_grades: Mapped[list | None] = mapped_column(JSON)
    value_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CompetitionStatus] = mapped_column(
        SAEnum(CompetitionStatus, values_callable=enum_values, name="competition_status"),
        default=CompetitionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    time_nodes: Mapped[list[CompetitionTimeNode]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )
    tag_links: Mapped[list[CompetitionTagLink]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )


class CompetitionTimeNode(db.Model, TimestampMixin):
    __tablename__ = "competition_time_nodes"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    node_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    competition: Mapped[Competition] = relationship(back_populates="time_nodes")


class CompetitionTag(db.Model, TimestampMixin):
    __tablename__ = "competition_tags"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tag_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)


class CompetitionTagLink(db.Model, TimestampMixin):
    __tablename__ = "competition_tag_links"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("competition_tags.id"), nullable=False)

    competition: Mapped[Competition] = relationship(back_populates="tag_links")
    tag: Mapped[CompetitionTag] = relationship()
