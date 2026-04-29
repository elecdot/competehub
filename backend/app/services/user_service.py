from app.extensions import db
from app.models.user import User, UserProfile


class UserService:
    @staticmethod
    def get_me(user_id: int) -> dict:
        user = db.session.get(User, user_id)
        profile = user.profile if user else None
        return {
            "user": user.public_dict() if user else None,
            "profile": profile.to_dict() if profile else None,
        }

    @staticmethod
    def update_profile(user_id: int, payload: dict) -> UserProfile:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile is None:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)

        for key, value in payload.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        db.session.commit()
        return profile

