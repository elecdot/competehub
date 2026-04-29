from app.extensions import db
from app.models.forum import CertificationRequest
from app.models.user import TeamPreference, User, UserProfile
from app.services.reminder_service import ReminderService


class UserService:
    @staticmethod
    def _json_values(values) -> list[str]:
        result = []
        for value in values or []:
            if isinstance(value, dict):
                result.extend(str(item) for item in value.values() if item)
            elif value:
                result.append(str(value))
        return result

    @staticmethod
    def get_me(user_id: int) -> dict:
        user = db.session.get(User, user_id)
        profile = user.profile if user else None
        team_preference = TeamPreference.query.filter_by(user_id=user_id).first()
        return {
            "user": user.public_dict() if user else None,
            "profile": profile.to_dict() if profile else None,
            "team_preference": team_preference.to_dict() if team_preference else None,
            "certifications": UserService.list_certifications(user_id, approved_only=False),
        }

    @staticmethod
    def update_profile(user_id: int, payload: dict) -> dict:
        team_payload = payload.pop("team_preference", None) or {}
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile is None:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)

        for key, value in payload.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        team_preference = TeamPreference.query.filter_by(user_id=user_id).first()
        if team_preference is None:
            team_preference = TeamPreference(user_id=user_id)
            db.session.add(team_preference)
        for key, value in team_payload.items():
            if hasattr(team_preference, key):
                setattr(team_preference, key, value)
        db.session.commit()
        return {"profile": profile.to_dict(), "team_preference": team_preference.to_dict()}

    @staticmethod
    def list_certifications(user_id: int, approved_only: bool = True) -> list[dict]:
        query = CertificationRequest.query.filter_by(user_id=user_id)
        if approved_only:
            query = query.filter(CertificationRequest.status == "approved")
        return [item.to_dict() for item in query.order_by(CertificationRequest.created_at.desc()).all()]

    @staticmethod
    def create_certification(user_id: int, payload: dict) -> CertificationRequest:
        description = payload.get("description", "")
        if any(keyword in description for keyword in ["国一", "国家级一等奖", "全国一等奖", "国家一等奖"]):
            payload["certification_type"] = "premium"
        request = CertificationRequest(user_id=user_id, **payload)
        db.session.add(request)
        db.session.commit()
        return request

    @staticmethod
    def contact_user(from_user_id: int, target_user_id: int, payload: dict) -> dict:
        sender = db.session.get(User, from_user_id)
        target = db.session.get(User, target_user_id)
        if target is None:
            return {}
        message = payload.get("message") or "希望和你交流组队。"
        ReminderService.create_notification(
            target_user_id,
            f"{sender.username if sender else '有同学'} 想与你交流",
            f"{message} 联系方式：邮箱 {sender.email or '未填写'}，手机 {sender.phone or '未填写'}。",
            "teammate_contact",
        )
        db.session.commit()
        return {
            "target": target.public_dict(),
            "sender_contact": {
                "username": sender.username if sender else "",
                "email": sender.email if sender else None,
                "phone": sender.phone if sender else None,
            },
            "target_contact": {
                "username": target.username,
                "email": target.email,
                "phone": target.phone,
            },
        }

    @staticmethod
    def list_matchmaking(user_id: int, args) -> list[dict]:
        current = UserService.get_me(user_id)
        current_profile = current.get("profile") or {}
        current_pref = current.get("team_preference") or {}
        keyword = (args.get("keyword") or "").strip()

        query = User.query.join(UserProfile).outerjoin(TeamPreference).filter(User.id != user_id, User.role == "student")
        if args.get("looking") in {"1", "true", "yes"}:
            query = query.filter(TeamPreference.looking_for_teammates.is_(True))
        users = query.limit(100).all()

        current_tags = set(current_profile.get("interests") or [])
        current_tags.update(current_pref.get("target_competitions") or [])
        current_tags.update(current_pref.get("required_skills") or [])

        matches = []
        for user in users:
            profile = user.profile
            preference = TeamPreference.query.filter_by(user_id=user.id).first()
            profile_dict = profile.to_dict() if profile else {}
            pref_dict = preference.to_dict() if preference else {}
            haystack = " ".join(
                [
                    user.username,
                    profile_dict.get("major") or "",
                    " ".join(profile_dict.get("interests") or []),
                    " ".join(UserService._json_values(profile_dict.get("competition_experiences"))),
                    " ".join(pref_dict.get("target_competitions") or []),
                    " ".join(pref_dict.get("required_skills") or []),
                ]
            )
            if keyword and keyword not in haystack:
                continue
            other_tags = set(profile_dict.get("interests") or [])
            other_tags.update(pref_dict.get("target_competitions") or [])
            other_tags.update(pref_dict.get("required_skills") or [])
            shared = sorted(current_tags & other_tags)
            matches.append(
                {
                    "user": user.public_dict(),
                    "profile": profile_dict,
                    "team_preference": pref_dict,
                    "certifications": UserService.list_certifications(user.id),
                    "shared_tags": shared,
                    "match_score": len(shared) * 20 + (30 if pref_dict.get("looking_for_teammates") else 0),
                }
            )
        return sorted(matches, key=lambda item: item["match_score"], reverse=True)
