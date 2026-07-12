from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
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
from competehub_api.models.enums import CompetitionRevisionStatus, CompetitionStatus
from competehub_api.models.mixins import TimestampMixin
from competehub_api.models.user import enum_values

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class CompetitionSeries(db.Model, TimestampMixin):
    __tablename__ = "competition_series"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    editions: Mapped[list[Competition]] = relationship(back_populates="series")


class Competition(db.Model, TimestampMixin):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    series_id: Mapped[int | None] = mapped_column(ForeignKey("competition_series.id"), index=True)
    edition_label: Mapped[str | None] = mapped_column(String(120), index=True)
    published_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "competition_revisions.id",
            name="fk_competitions_published_revision_id_competition_revisions",
            use_alter=True,
        ),
        index=True,
    )
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
    registration_applicability: Mapped[str | None] = mapped_column(String(32))
    team_size: Mapped[str | None] = mapped_column(String(120))
    participant_form: Mapped[str | None] = mapped_column(String(120))
    participant_forms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    major_scope: Mapped[str | None] = mapped_column(String(32))
    grade_scope: Mapped[str | None] = mapped_column(String(32))
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

    series: Mapped[CompetitionSeries | None] = relationship(back_populates="editions")
    revisions: Mapped[list[CompetitionRevision]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
        foreign_keys="CompetitionRevision.competition_id",
        order_by="CompetitionRevision.revision_number",
    )
    published_revision: Mapped[CompetitionRevision | None] = relationship(
        foreign_keys=[published_revision_id],
        post_update=True,
    )

    time_nodes: Mapped[list[CompetitionTimeNode]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )
    tag_links: Mapped[list[CompetitionTagLink]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("series_id", "edition_label", name="uq_competition_series_edition"),
    )


class CompetitionRevision(db.Model, TimestampMixin):
    __tablename__ = "competition_revisions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    base_revision_id: Mapped[int | None] = mapped_column(ForeignKey("competition_revisions.id"))
    revision_status: Mapped[CompetitionRevisionStatus] = mapped_column(
        SAEnum(
            CompetitionRevisionStatus,
            values_callable=enum_values,
            name="competition_revision_status",
        ),
        default=CompetitionRevisionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_title: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(120))
    organizer: Mapped[str | None] = mapped_column(String(255))
    host: Mapped[str | None] = mapped_column(String(255))
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    official_url: Mapped[str | None] = mapped_column(String(1024))
    attachment_url: Mapped[str | None] = mapped_column(String(1024))
    summary: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    eligibility: Mapped[str | None] = mapped_column(Text)
    registration_applicability: Mapped[str | None] = mapped_column(String(32))
    team_size: Mapped[str | None] = mapped_column(String(120))
    participant_forms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    major_scope: Mapped[str | None] = mapped_column(String(32))
    grade_scope: Mapped[str | None] = mapped_column(String(32))
    suitable_majors: Mapped[list | None] = mapped_column(JSON)
    suitable_grades: Mapped[list | None] = mapped_column(JSON)
    value_notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    submitted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    competition: Mapped[Competition] = relationship(
        back_populates="revisions",
        foreign_keys=[competition_id],
    )
    stages: Mapped[list[CompetitionStage]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
        order_by="CompetitionStage.stage_order",
    )
    time_nodes: Mapped[list[CompetitionTimeNode]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
        foreign_keys="CompetitionTimeNode.competition_revision_id",
    )
    tag_links: Mapped[list[CompetitionTagLink]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
        foreign_keys="CompetitionTagLink.competition_revision_id",
    )

    __table_args__ = (
        UniqueConstraint("competition_id", "revision_number", name="uq_competition_revision"),
        Index(
            "uq_active_competition_revision",
            "competition_id",
            unique=True,
            postgresql_where=text("revision_status IN ('draft', 'pending_review')"),
            sqlite_where=text("revision_status IN ('draft', 'pending_review')"),
        ),
    )


class CompetitionStage(db.Model, TimestampMixin):
    __tablename__ = "competition_stages"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    competition_revision_id: Mapped[int] = mapped_column(
        ForeignKey("competition_revisions.id"),
        nullable=False,
    )
    stage_key: Mapped[str] = mapped_column(String(120), nullable=False)
    stage_type: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)

    revision: Mapped[CompetitionRevision] = relationship(back_populates="stages")
    time_nodes: Mapped[list[CompetitionTimeNode]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="CompetitionTimeNode.occurs_at",
    )

    __table_args__ = (
        UniqueConstraint(
            "competition_revision_id",
            "stage_key",
            name="uq_competition_revision_stage_key",
        ),
        UniqueConstraint(
            "competition_revision_id",
            "stage_order",
            name="uq_competition_revision_stage_order",
        ),
    )


class CompetitionTimeNode(db.Model, TimestampMixin):
    __tablename__ = "competition_time_nodes"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id"))
    competition_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("competition_revisions.id"),
        index=True,
    )
    stage_id: Mapped[int | None] = mapped_column(ForeignKey("competition_stages.id"), index=True)
    logical_node_key: Mapped[str | None] = mapped_column(String(120))
    node_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    node_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    occurs_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    prominence: Mapped[str] = mapped_column(String(20), default="secondary", nullable=False)
    prominence_override_reason: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    competition: Mapped[Competition] = relationship(back_populates="time_nodes")
    revision: Mapped[CompetitionRevision | None] = relationship(
        back_populates="time_nodes",
        foreign_keys=[competition_revision_id],
    )
    stage: Mapped[CompetitionStage | None] = relationship(back_populates="time_nodes")

    __table_args__ = (
        UniqueConstraint(
            "competition_revision_id",
            "logical_node_key",
            name="uq_competition_revision_node_key",
        ),
    )


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
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id"))
    competition_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("competition_revisions.id"),
        index=True,
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("competition_tags.id"), nullable=False)

    competition: Mapped[Competition] = relationship(back_populates="tag_links")
    revision: Mapped[CompetitionRevision | None] = relationship(
        back_populates="tag_links",
        foreign_keys=[competition_revision_id],
    )
    tag: Mapped[CompetitionTag] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "competition_revision_id",
            "tag_id",
            name="uq_competition_revision_tag",
        ),
    )
