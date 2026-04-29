from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.core.response import success
from app.services.reminder_service import ReminderService
from app.utils.auth import current_user_id

reminders_bp = Blueprint("reminders", __name__)


@reminders_bp.get("/calendar")
@jwt_required()
def calendar():
    return success(ReminderService.calendar(current_user_id()))


@reminders_bp.get("/notifications")
@jwt_required()
def notifications():
    return success(ReminderService.notifications(current_user_id()))


@reminders_bp.put("/notifications/<int:notification_id>/read")
@jwt_required()
def read_notification(notification_id: int):
    ReminderService.mark_read(current_user_id(), notification_id)
    return success(None, "通知已读")


@reminders_bp.put("/notifications/read-all")
@jwt_required()
def read_all_notifications():
    ReminderService.mark_read(current_user_id())
    return success(None, "通知已全部标记已读")


@reminders_bp.put("/settings")
@jwt_required()
def update_settings():
    setting = ReminderService.update_settings(current_user_id(), request.get_json() or {})
    return success(setting.to_dict(), "提醒设置已更新")
