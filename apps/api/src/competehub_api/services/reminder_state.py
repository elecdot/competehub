from __future__ import annotations

from competehub_api.models import Reminder
from competehub_api.models.enums import ReminderStatus


def revoke_pending_reminder(reminder: Reminder, reason: str) -> ReminderStatus:
    """Revoke pending work without erasing evidence from a requeued failed attempt."""
    if reminder.status != ReminderStatus.PENDING:
        return reminder.status
    if (
        reminder.attempt_count > 0
        or reminder.failed_at is not None
        or reminder.last_error_code is not None
    ):
        reminder.status = ReminderStatus.FAILED
    else:
        reminder.status = ReminderStatus.CANCELLED
    reminder.next_attempt_at = None
    reminder.cancel_reason = reason
    return reminder.status
