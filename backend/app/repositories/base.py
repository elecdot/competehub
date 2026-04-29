from app.extensions import db


class BaseRepository:
    model = None

    @classmethod
    def get(cls, item_id: int):
        return db.session.get(cls.model, item_id)

    @classmethod
    def add(cls, instance):
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, instance) -> None:
        db.session.delete(instance)
        db.session.commit()

