from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app import create_app
from app.extensions import bcrypt, db
from app.models.competition import Competition
from app.models.user import User, UserProfile


def upsert_user(username: str, password: str, role: str):
    user = User.query.filter_by(username=username).first()
    if user:
        return user
    user = User(
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
    )
    user.profile = UserProfile(
        major="计算机科学与技术",
        grade="大二",
        interests=["人工智能", "程序设计"],
        goals=["能力提升", "简历提升"],
    )
    db.session.add(user)
    return user


def seed_competitions(admin: User):
    if Competition.query.count() > 0:
        return
    items = [
        Competition(
            title="蓝桥杯全国软件和信息技术专业人才大赛",
            summary="面向程序设计和算法能力提升的高关注度赛事。",
            description="包含软件类、电子类等多个方向，适合计算机及相关专业学生参与。",
            category="程序设计",
            level="国家级",
            organizer="工业和信息化部人才交流中心",
            target_majors=["计算机科学与技术", "软件工程", "人工智能"],
            target_grades=["大一", "大二", "大三"],
            tags=["程序设计", "算法", "软件"],
            status="published",
            registration_deadline_at=datetime.utcnow() + timedelta(days=12),
            official_url="https://dasai.lanqiao.cn/",
            heat=45,
            score=88,
            created_by=admin.id,
        ),
        Competition(
            title="全国大学生数学建模竞赛",
            summary="综合考察建模、编程和论文写作能力。",
            description="适合数学、统计、计算机、经管等多专业学生组队参与。",
            category="数学建模",
            level="国家级",
            organizer="中国工业与应用数学学会",
            target_majors=["数学", "统计学", "计算机科学与技术"],
            target_grades=["大二", "大三", "大四"],
            tags=["数学建模", "数据分析", "论文"],
            status="published",
            registration_deadline_at=datetime.utcnow() + timedelta(days=28),
            heat=60,
            score=92,
            created_by=admin.id,
        ),
    ]
    db.session.add_all(items)


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        admin = upsert_user("admin", "admin123", "admin")
        upsert_user("student", "student123", "student")
        db.session.commit()
        seed_competitions(admin)
        db.session.commit()
        print("Seed completed. admin/admin123 student/student123")


if __name__ == "__main__":
    main()

