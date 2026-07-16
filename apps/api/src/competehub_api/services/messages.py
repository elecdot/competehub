from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus

from flask import current_app

from competehub_api.extensions import db
from competehub_api.models import Message
from competehub_api.repositories.competitions import list_available_public_detail_ids
from competehub_api.repositories.engagement import (
    MessagePage,
    MessageQuery,
    count_retained_unread_messages,
    get_retained_message_for_update,
    list_expired_messages_for_update,
    list_messages_for_user,
    mark_all_retained_messages_read,
)
from competehub_api.repositories.users import get_user_for_update
from competehub_api.services.errors import ServiceError


@dataclass(frozen=True)
class MessageView:
    message: Message
    target_available: bool
    target_url: str | None

    def __getattr__(self, name: str):
        return getattr(self.message, name)


@dataclass(frozen=True)
class MarkMessageReadResult:
    message: MessageView
    unread_count: int


def list_student_messages(user_id: int, query: MessageQuery) -> MessagePage:
    now = datetime.now(UTC)
    page = list_messages_for_user(user_id, query, now=now)
    views = _message_views(page.items)
    return MessagePage(
        items=views,
        page=page.page,
        page_size=page.page_size,
        total=page.total,
    )


def unread_message_count(user_id: int) -> int:
    return count_retained_unread_messages(user_id, now=datetime.now(UTC))


def mark_message_read(user_id: int, message_id: int) -> MarkMessageReadResult:
    now = datetime.now(UTC)
    _lock_user_message_authority(user_id)
    message = get_retained_message_for_update(user_id, message_id, now=now)
    if message is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "message not found")
    if not message.is_read:
        message.is_read = True
        message.read_at = now
    unread_count = count_retained_unread_messages(user_id, now=now)
    db.session.commit()
    return MarkMessageReadResult(
        message=_message_views([message])[0],
        unread_count=unread_count,
    )


def mark_all_messages_read(user_id: int) -> dict[str, int]:
    now = datetime.now(UTC)
    _lock_user_message_authority(user_id)
    updated_count = mark_all_retained_messages_read(user_id, now)
    unread_count = count_retained_unread_messages(user_id, now=now)
    db.session.commit()
    return {"updated_count": updated_count, "unread_count": unread_count}


def _lock_user_message_authority(user_id: int) -> None:
    if get_user_for_update(user_id) is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "user not found")


def purge_expired_messages(
    *, now: datetime | None = None, limit: int | None = None
) -> dict[str, int]:
    now = now or datetime.now(UTC)
    batch_size = limit or current_app.config["MESSAGE_RETENTION_BATCH_SIZE"]
    purged = 0
    while True:
        messages = list_expired_messages_for_update(now, batch_size)
        if not messages:
            break
        for message in messages:
            db.session.delete(message)
        purged += len(messages)
        db.session.commit()
        if len(messages) < batch_size:
            break
    return {"purged": purged}


def _message_views(messages: list[Message]) -> list[MessageView]:
    available_ids = list_available_public_detail_ids(
        {message.competition_id for message in messages}
    )
    return [
        MessageView(
            message=message,
            target_available=message.competition_id in available_ids,
            target_url=(
                f"/competitions/{message.competition_id}"
                if message.competition_id in available_ids
                else None
            ),
        )
        for message in messages
    ]
