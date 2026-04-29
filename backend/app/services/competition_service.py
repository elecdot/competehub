from datetime import datetime

from sqlalchemy import or_

from app.core.errors import AppError
from app.extensions import db
from app.models.competition import Competition
from app.models.engagement import BehaviorLog, Favorite, Subscription


class CompetitionService:
    @staticmethod
    def list_competitions(args, include_unpublished: bool = False):
        query = Competition.query
        if not include_unpublished:
            query = query.filter(Competition.status == "published")

        keyword = args.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Competition.title.ilike(like),
                    Competition.organizer.ilike(like),
                    Competition.summary.ilike(like),
                )
            )

        for field in ["category", "level", "status"]:
            value = args.get(field)
            if value:
                query = query.filter(getattr(Competition, field) == value)

        deadline_before = args.get("deadline_before")
        if deadline_before:
            query = query.filter(Competition.registration_deadline_at <= datetime.fromisoformat(deadline_before))

        sort = args.get("sort", "deadline")
        if sort == "heat":
            query = query.order_by(Competition.heat.desc(), Competition.created_at.desc())
        elif sort == "score":
            query = query.order_by(Competition.score.desc(), Competition.created_at.desc())
        else:
            query = query.order_by(Competition.registration_deadline_at.asc().nullslast(), Competition.created_at.desc())

        return query

    @staticmethod
    def get_competition(competition_id: int, user_id: int | None = None) -> Competition:
        competition = db.session.get(Competition, competition_id)
        if competition is None:
            raise AppError("赛事不存在", 40401, 404)
        if user_id:
            competition.heat += 1
            db.session.add(BehaviorLog(user_id=user_id, target_type="competition", target_id=competition_id, action="view"))
            db.session.commit()
        return competition

    @staticmethod
    def create_competition(payload: dict, creator_id: int | None = None, status: str = "pending") -> Competition:
        competition = Competition(**payload, status=status, created_by=creator_id)
        db.session.add(competition)
        db.session.commit()
        return competition

    @staticmethod
    def update_competition(competition_id: int, payload: dict) -> Competition:
        competition = CompetitionService.get_competition(competition_id)
        for key, value in payload.items():
            if hasattr(competition, key):
                setattr(competition, key, value)
        db.session.commit()
        return competition

    @staticmethod
    def favorite(user_id: int, competition_id: int) -> Favorite:
        CompetitionService.get_competition(competition_id)
        record = Favorite.query.filter_by(user_id=user_id, competition_id=competition_id).first()
        if record is None:
            record = Favorite(user_id=user_id, competition_id=competition_id)
            db.session.add(record)
            db.session.add(BehaviorLog(user_id=user_id, target_type="competition", target_id=competition_id, action="favorite"))
            db.session.commit()
        return record

    @staticmethod
    def subscribe(user_id: int, competition_id: int, remind_days_before: int = 3) -> Subscription:
        CompetitionService.get_competition(competition_id)
        record = Subscription.query.filter_by(user_id=user_id, competition_id=competition_id).first()
        if record is None:
            record = Subscription(
                user_id=user_id,
                competition_id=competition_id,
                remind_days_before=remind_days_before,
            )
            db.session.add(record)
        else:
            record.remind_days_before = remind_days_before
            record.enabled = True
        db.session.add(BehaviorLog(user_id=user_id, target_type="competition", target_id=competition_id, action="subscribe"))
        db.session.commit()
        return record

