from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.core.pagination import get_page_params, pagination_payload
from app.core.response import success
from app.schemas.forum import CommentCreateSchema, PostCreateSchema
from app.services.forum_service import ForumService
from app.utils.auth import current_user_id

forum_bp = Blueprint("forum", __name__)


@forum_bp.get("/posts")
def list_posts():
    page, page_size = get_page_params()
    query = ForumService.list_posts(request.args)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return success(pagination_payload(pagination))


@forum_bp.post("/posts")
@jwt_required()
def create_post():
    payload = PostCreateSchema().load(request.get_json() or {})
    post = ForumService.create_post(current_user_id(), payload)
    return success(post.to_dict(), "帖子已发布", status=201)


@forum_bp.get("/posts/<int:post_id>")
def get_post(post_id: int):
    post = ForumService.get_post(post_id)
    return success(post.to_dict())


@forum_bp.post("/posts/<int:post_id>/comments")
@jwt_required()
def create_comment(post_id: int):
    payload = CommentCreateSchema().load(request.get_json() or {})
    comment = ForumService.create_comment(current_user_id(), post_id, payload)
    return success(comment.to_dict(), "评论已发布", status=201)

