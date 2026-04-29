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


@reminders_bp.put("/settings")
@jwt_required()
def update_settings():
    setting = ReminderService.update_settings(current_user_id(), request.get_json() or {})
    return success(setting.to_dict(), "提醒设置已更新")

