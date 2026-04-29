from app.core.errors import AppError
from app.extensions import db
from app.models.forum import CertificationRequest, Comment, Post, PostInterest
from app.models.user import User
from app.services.reminder_service import ReminderService


class ForumService:
    @staticmethod
    def _author_payload(user_id: int) -> dict:
        user = db.session.get(User, user_id)
        if user is None:
            return {"id": user_id, "username": "已注销用户", "role": "unknown"}
        certifications = (
            CertificationRequest.query.filter_by(user_id=user_id, status="approved")
            .order_by(CertificationRequest.created_at.desc())
            .all()
        )
        payload = user.public_dict()
        payload["certifications"] = [item.to_dict() for item in certifications]
        payload["premium"] = any(item.certification_type == "premium" for item in certifications)
        return payload

    @staticmethod
    def serialize_post(post: Post, viewer_id: int | None = None) -> dict:
        data = post.to_dict()
        data["author"] = ForumService._author_payload(post.author_id)
        data["interest_count"] = PostInterest.query.filter_by(post_id=post.id, status="interested").count()
        data["comment_count"] = Comment.query.filter_by(post_id=post.id, status="published").count()
        data["interested"] = False
        if viewer_id:
            data["interested"] = (
                PostInterest.query.filter_by(post_id=post.id, user_id=viewer_id, status="interested").first()
                is not None
            )
        return data

    @staticmethod
    def serialize_comment(comment: Comment) -> dict:
        data = comment.to_dict()
        data["author"] = ForumService._author_payload(comment.author_id)
        return data

    @staticmethod
    def list_posts(args):
        query = Post.query.filter(Post.status == "published")
        post_type = args.get("post_type")
        if post_type:
            query = query.filter(Post.post_type == post_type)
        keyword = args.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter((Post.title.ilike(like)) | (Post.content.ilike(like)))
        tag = args.get("tag")
        if tag:
            query = query.filter(Post.tags.contains([tag]))
        return query.order_by(Post.created_at.desc())

    @staticmethod
    def create_post(author_id: int, payload: dict) -> Post:
        post = Post(author_id=author_id, **payload)
        db.session.add(post)
        db.session.commit()
        return post

    @staticmethod
    def get_post(post_id: int) -> Post:
        post = db.session.get(Post, post_id)
        if post is None or post.status != "published":
            raise AppError("帖子不存在", 40402, 404)
        post.view_count += 1
        db.session.commit()
        return post

    @staticmethod
    def list_comments(post_id: int) -> list[dict]:
        ForumService.get_post(post_id)
        comments = (
            Comment.query.filter_by(post_id=post_id, status="published")
            .order_by(Comment.created_at.asc())
            .all()
        )
        return [ForumService.serialize_comment(comment) for comment in comments]

    @staticmethod
    def create_comment(author_id: int, post_id: int, payload: dict) -> Comment:
        post = ForumService.get_post(post_id)
        comment = Comment(author_id=author_id, post_id=post_id, **payload)
        db.session.add(comment)
        if post.author_id != author_id:
            author = db.session.get(User, author_id)
            ReminderService.create_notification(
                post.author_id,
                f"你的帖子《{post.title}》有新回复",
                f"{author.username if author else '有同学'} 回复：{comment.content}",
                "forum_comment",
            )
        parent_id = payload.get("parent_id")
        if parent_id:
            parent = db.session.get(Comment, parent_id)
            if parent and parent.author_id not in {author_id, post.author_id}:
                author = db.session.get(User, author_id)
                ReminderService.create_notification(
                    parent.author_id,
                    f"你在《{post.title}》下的评论有新回复",
                    f"{author.username if author else '有同学'} 回复：{comment.content}",
                    "forum_reply",
                )
        db.session.commit()
        return comment

    @staticmethod
    def like_post(user_id: int, post_id: int) -> dict:
        post = ForumService.get_post(post_id)
        post.like_count += 1
        if post.author_id != user_id:
            user = db.session.get(User, user_id)
            ReminderService.create_notification(
                post.author_id,
                f"你的帖子《{post.title}》收到点赞",
                f"{user.username if user else '有同学'} 点赞了你的帖子。",
                "forum_like",
            )
        db.session.commit()
        return ForumService.serialize_post(post, user_id)

    @staticmethod
    def mark_interest(user_id: int, post_id: int, payload: dict) -> dict:
        post = ForumService.get_post(post_id)
        if post.author_id == user_id:
            raise AppError("不能对自己的帖子标记意向", 40011, 400)
        record = PostInterest.query.filter_by(post_id=post_id, user_id=user_id).first()
        if record is None:
            record = PostInterest(post_id=post_id, user_id=user_id)
            db.session.add(record)
        record.status = "interested"
        record.message = payload.get("message")
        viewer = db.session.get(User, user_id)
        ReminderService.create_notification(
            post.author_id,
            f"有人对你的组队帖《{post.title}》感兴趣",
            f"{viewer.username if viewer else '有同学'} 标记了有意向。留言：{record.message or '未填写'}。"
            f"联系方式：邮箱 {viewer.email or '未填写'}，手机 {viewer.phone or '未填写'}。",
            "team_interest",
        )
        db.session.commit()

        author = db.session.get(User, post.author_id)
        return {
            "interest": record.to_dict(),
            "author_contact": {
                "username": author.username if author else "",
                "email": author.email if author else None,
                "phone": author.phone if author else None,
            },
            "viewer_contact": {
                "username": viewer.username if viewer else "",
                "email": viewer.email if viewer else None,
                "phone": viewer.phone if viewer else None,
            },
        }
