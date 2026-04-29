from app.extensions import db
from app.models.base import SerializerMixin, TimestampMixin


class Competition(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "competitions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    summary = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=False, index=True)
    level = db.Column(db.String(32), nullable=False, index=True)
    organizer = db.Column(db.String(200), nullable=True, index=True)
    target_majors = db.Column(db.JSON, default=list, nullable=False)
    target_grades = db.Column(db.JSON, default=list, nullable=False)
    tags = db.Column(db.JSON, default=list, nullable=False)
    status = db.Column(db.String(32), default="draft", nullable=False, index=True)
    registration_start_at = db.Column(db.DateTime, nullable=True)
    registration_deadline_at = db.Column(db.DateTime, nullable=True, index=True)
    competition_start_at = db.Column(db.DateTime, nullable=True)
    competition_end_at = db.Column(db.DateTime, nullable=True)
    official_url = db.Column(db.String(500), nullable=True)
    attachment_url = db.Column(db.String(500), nullable=True)
    heat = db.Column(db.Integer, default=0, nullable=False)
    score = db.Column(db.Float, default=0, nullable=False)
    score_reason = db.Column(db.JSON, default=list, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    nodes = db.relationship("CompetitionNode", back_populates="competition", cascade="all, delete-orphan")
    sources = db.relationship("CompetitionSource", back_populates="competition", cascade="all, delete-orphan")


class CompetitionNode(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "competition_nodes"

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False, index=True)
    node_type = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(128), nullable=False)
    occurs_at = db.Column(db.DateTime, nullable=False, index=True)
    description = db.Column(db.String(500), nullable=True)

    competition = db.relationship("Competition", back_populates="nodes")


class CompetitionSource(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "competition_sources"

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True, index=True)
    source_name = db.Column(db.String(128), nullable=False)
    source_url = db.Column(db.String(500), nullable=False)
    raw_title = db.Column(db.String(255), nullable=True)
    raw_payload = db.Column(db.JSON, default=dict, nullable=False)
    trust_level = db.Column(db.String(32), default="official", nullable=False)

    competition = db.relationship("Competition", back_populates="sources")


class CompetitionTag(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "competition_tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    category = db.Column(db.String(64), nullable=True)

