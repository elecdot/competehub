from app.extensions import db
from app.models.base import SerializerMixin, TimestampMixin


class User(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    phone = db.Column(db.String(32), unique=True, nullable=True, index=True)
    student_no = db.Column(db.String(64), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), default="student", nullable=False, index=True)
    status = db.Column(db.String(32), default="active", nullable=False, index=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    profile = db.relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def public_dict(self) -> dict:
        data = self.to_dict()
        data.pop("password_hash", None)
        return data


class UserProfile(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    real_name = db.Column(db.String(64), nullable=True)
    school = db.Column(db.String(128), nullable=True)
    college = db.Column(db.String(128), nullable=True)
    major = db.Column(db.String(128), nullable=True, index=True)
    grade = db.Column(db.String(32), nullable=True, index=True)
    interests = db.Column(db.JSON, default=list, nullable=False)
    competition_experiences = db.Column(db.JSON, default=list, nullable=False)
    goals = db.Column(db.JSON, default=list, nullable=False)
    ability_level = db.Column(db.String(32), default="beginner", nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="profile")

