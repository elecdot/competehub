from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.core.pagination import get_page_params
from app.core.response import success
from app.schemas.forum import CommentCreateSchema, PostCreateSchema, PostInterestSchema
from app.services.forum_service import ForumService
from app.utils.auth import current_user_id

forum_bp = Blueprint("forum", __name__)


def _viewer_id() -> int | None:
    identity = get_jwt_identity()
    return int(identity) if identity else None


@forum_bp.get("/posts")
@jwt_required(optional=True)
def list_posts():
    page, page_size = get_page_params()
    query = ForumService.list_posts(request.args)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return success(
        {
            "items": [ForumService.serialize_post(item, _viewer_id()) for item in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "page_size": pagination.per_page,
            "pages": pagination.pages,
        }
    )


@forum_bp.post("/posts")
@jwt_required()
def create_post():
    payload = PostCreateSchema().load(request.get_json() or {})
    post = ForumService.create_post(current_user_id(), payload)
    return success(ForumService.serialize_post(post, current_user_id()), "帖子已发布", status=201)


@forum_bp.get("/posts/<int:post_id>")
@jwt_required(optional=True)
def get_post(post_id: int):
    post = ForumService.get_post(post_id)
    return success(ForumService.serialize_post(post, _viewer_id()))


@forum_bp.get("/posts/<int:post_id>/comments")
def list_comments(post_id: int):
    return success(ForumService.list_comments(post_id))


@forum_bp.post("/posts/<int:post_id>/comments")
@jwt_required()
def create_comment(post_id: int):
    payload = CommentCreateSchema().load(request.get_json() or {})
    comment = ForumService.create_comment(current_user_id(), post_id, payload)
    return success(ForumService.serialize_comment(comment), "评论已发布", status=201)


@forum_bp.post("/posts/<int:post_id>/interest")
@jwt_required()
def mark_interest(post_id: int):
    payload = PostInterestSchema().load(request.get_json() or {})
    result = ForumService.mark_interest(current_user_id(), post_id, payload)
    return success(result, "已标记意向，双方可交换联系方式")
