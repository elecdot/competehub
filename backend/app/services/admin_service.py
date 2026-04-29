from app.extensions import db
from app.models.competition import Competition
from app.models.engagement import Favorite, Subscription
from app.models.forum import Post
from app.models.user import User


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
        }

