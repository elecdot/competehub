from app.extensions import db
from app.models.base import SerializerMixin, TimestampMixin


class Post(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(32), default="question", nullable=False, index=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True, index=True)
    tags = db.Column(db.JSON, default=list, nullable=False)
    status = db.Column(db.String(32), default="published", nullable=False, index=True)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    like_count = db.Column(db.Integer, default=0, nullable=False)


class Comment(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="published", nullable=False)


class CertificationRequest(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "certification_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True)
    certification_type = db.Column(db.String(64), nullable=False)
    evidence_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="pending", nullable=False, index=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    review_comment = db.Column(db.String(500), nullable=True)


class ResourceArchive(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "resource_archives"

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    resource_type = db.Column(db.String(64), default="experience", nullable=False, index=True)
    attachment_url = db.Column(db.String(500), nullable=True)
    tags = db.Column(db.JSON, default=list, nullable=False)
    status = db.Column(db.String(32), default="published", nullable=False)

