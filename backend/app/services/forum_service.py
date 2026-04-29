from app.core.errors import AppError
from app.extensions import db
from app.models.forum import Comment, Post


class ForumService:
    @staticmethod
    def list_posts(args):
        query = Post.query.filter(Post.status == "published")
        post_type = args.get("post_type")
        if post_type:
            query = query.filter(Post.post_type == post_type)
        keyword = args.get("keyword")
        if keyword:
            query = query.filter(Post.title.ilike(f"%{keyword}%"))
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
    def create_comment(author_id: int, post_id: int, payload: dict) -> Comment:
        ForumService.get_post(post_id)
        comment = Comment(author_id=author_id, post_id=post_id, **payload)
        db.session.add(comment)
        db.session.commit()
        return comment

