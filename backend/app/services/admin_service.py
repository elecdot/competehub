from app.extensions import db
from app.models.competition import Competition
from app.models.engagement import Favorite, Subscription
from app.models.forum import CertificationRequest, Post
from app.models.user import TeamPreference, User


class AdminService:
    @staticmethod
    def statistics() -> dict:
        return {
            "users": db.session.query(User).count(),
            "competitions": db.session.query(Competition).count(),
            "published_competitions": Competition.query.filter_by(status="published").count(),
            "favorites": db.session.query(Favorite).count(),
            "subscriptions": db.session.query(Subscription).count(),
            "posts": db.session.query(Post).count(),
            "certifications_pending": CertificationRequest.query.filter_by(status="pending").count(),
        }

    @staticmethod
    def list_users() -> list[dict]:
        users = User.query.order_by(User.created_at.desc()).all()
        result = []
        for user in users:
            payload = user.public_dict()
            payload["profile"] = user.profile.to_dict() if user.profile else None
            preference = TeamPreference.query.filter_by(user_id=user.id).first()
            payload["team_preference"] = preference.to_dict() if preference else None
            payload["post_count"] = Post.query.filter_by(author_id=user.id).count()
            payload["certifications"] = [
                item.to_dict()
                for item in CertificationRequest.query.filter_by(user_id=user.id)
                .order_by(CertificationRequest.created_at.desc())
                .all()
            ]
            result.append(payload)
        return result

    @staticmethod
    def list_posts(user_id: int | None = None) -> list[dict]:
        query = Post.query
        if user_id:
            query = query.filter(Post.author_id == user_id)
        posts = query.order_by(Post.created_at.desc()).limit(200).all()
        result = []
        for post in posts:
            payload = post.to_dict()
            author = db.session.get(User, post.author_id)
            payload["author"] = author.public_dict() if author else None
            result.append(payload)
        return result

    @staticmethod
    def delete_post(post_id: int) -> Post:
        post = db.session.get(Post, post_id)
        if post is None:
            return None
        post.status = "deleted"
        db.session.commit()
        return post

    @staticmethod
    def list_certifications() -> list[dict]:
        records = CertificationRequest.query.order_by(CertificationRequest.created_at.desc()).all()
        result = []
        for record in records:
            payload = record.to_dict()
            user = db.session.get(User, record.user_id)
            payload["user"] = user.public_dict() if user else None
            result.append(payload)
        return result

    @staticmethod
    def review_certification(certification_id: int, status: str, reviewer_id: int, comment: str | None = None):
        record = db.session.get(CertificationRequest, certification_id)
        if record is None:
            return None
        record.status = status
        record.reviewer_id = reviewer_id
        record.review_comment = comment
        db.session.commit()
        return record
