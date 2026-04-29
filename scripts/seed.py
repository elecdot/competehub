from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "scripts"))

from app import create_app
from app.extensions import bcrypt, db
from app.models.competition import Competition, CompetitionSource
from app.models.forum import CertificationRequest, Post
from app.models.user import TeamPreference, User, UserProfile
from competition_catalog_2023 import CATALOG_ITEMS, OFFICIAL_INFO


CATALOG_SCORE = {"A": 95, "B": 84, "C": 72, "D": 60}
CATALOG_HEAT = {"A": 90, "B": 62, "C": 42, "D": 25}
CATEGORY_RULES = [
    ("创新创业", ["互联网", "挑战杯", "创新创业", "创青春", "鼎新", "服务外包", "电商"]),
    ("计算机与软件", ["程序", "ICPC", "蓝桥", "软件", "计算机", "开源", "信息安全", "IEEE", "ICT"]),
    ("电子信息与智能", ["电子", "电路", "集成电路", "通信", "嵌入式", "智能车", "机器人", "传感器", "物联网", "芯片"]),
    ("数学建模与理学", ["数学", "建模", "统计", "物理", "化学", "力学", "光电"]),
    ("机械材料与制造", ["机械", "成图", "三维", "金相", "焊接", "材料", "制造", "工程制作"]),
    ("城市建设与交通", ["建筑", "结构", "土木", "交通", "给排水", "城市", "BIM", "规划", "水利", "桥"]),
    ("环境能源与生命", ["环境", "能源", "节能", "减排", "生物", "化工", "制冷", "水下"]),
    ("人文语言与设计", ["英语", "日语", "法庭", "人文", "社会", "广告", "设计", "美术", "动漫", "金犊", "华灿"]),
    ("经管商科", ["市场调查", "能源经济", "企业竞争", "会计", "商业个案"]),
    ("体育", ["运动会", "体育"]),
]


def upsert_user(username: str, password: str, role: str):
    user = User.query.filter_by(username=username).first()
    if user is None:
        user = User(
            username=username,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
            role=role,
        )
        db.session.add(user)

    if user.profile is None:
        user.profile = UserProfile()
    user.profile.major = user.profile.major or "计算机科学与技术"
    user.profile.grade = user.profile.grade or "大二"
    user.profile.interests = user.profile.interests or ["人工智能", "程序设计"]
    user.profile.goals = user.profile.goals or ["能力提升", "简历提升"]

    return user


def ensure_team_preference(user: User) -> None:
    preference = TeamPreference.query.filter_by(user_id=user.id).first()
    if preference is None:
        db.session.add(
            TeamPreference(
                user_id=user.id,
                looking_for_teammates=True,
                required_skills=["Python", "算法", "前端"],
                required_awards=["蓝桥杯省奖", "数学建模经历"],
                target_competitions=["蓝桥杯", "中国大学生计算机设计大赛"],
                contact_preference="站内联系",
            )
        )


def infer_category(name: str) -> str:
    for category, keywords in CATEGORY_RULES:
        if any(keyword in name for keyword in keywords):
            return category
    return "综合竞赛"


def infer_tags(name: str, catalog_level: str, category: str) -> list[str]:
    tags = [f"{catalog_level}类竞赛", category]
    keyword_tags = [
        "数学建模",
        "程序设计",
        "人工智能",
        "创新创业",
        "机器人",
        "电子设计",
        "软件",
        "英语",
        "建筑设计",
        "材料",
        "交通",
    ]
    tags.extend(tag for tag in keyword_tags if tag in name)
    return list(dict.fromkeys(tags))


def match_official_info(name: str) -> dict:
    for official_name, info in OFFICIAL_INFO.items():
        if official_name in name or name in official_name:
            return info
    return {}


def upsert_source(competition: Competition, source_name: str, source_url: str, raw_payload: dict) -> None:
    existing = CompetitionSource.query.filter_by(
        competition_id=competition.id,
        source_name=source_name,
        raw_title=competition.title,
    ).first()
    if existing is None:
        db.session.add(
            CompetitionSource(
                competition_id=competition.id,
                source_name=source_name,
                source_url=source_url,
                raw_title=competition.title,
                raw_payload=raw_payload,
                trust_level="official" if source_url.startswith("http") else "school_catalog",
            )
        )
    else:
        existing.source_url = source_url
        existing.raw_payload = raw_payload


def upsert_catalog_competitions(admin: User) -> None:
    for item in CATALOG_ITEMS:
        catalog_level = item["catalog_level"]
        name = item["name"]
        category = infer_category(name)
        official_info = match_official_info(name)
        score = CATALOG_SCORE[catalog_level]
        official_url = official_info.get("url")
        timeline = official_info.get("timeline") or "关键时间节点待根据赛事官网或校内通知补充，当前系统先保留目录认定信息。"
        description = (
            f"来源：北京工业大学本科生科技竞赛认定目录（2023版）{catalog_level}类竞赛。"
            f"项目编码：{item['code']}。关键时间节点：{timeline}"
        )
        competition = Competition.query.filter_by(title=name).first()
        if competition is None:
            competition = Competition(title=name, created_by=admin.id)
            db.session.add(competition)

        competition.summary = f"{catalog_level}类认定竞赛，方向：{category}"
        competition.description = description
        competition.category = category
        competition.level = f"{catalog_level}类"
        competition.organizer = competition.organizer or "以竞赛官网/校内通知为准"
        competition.target_majors = competition.target_majors or []
        competition.target_grades = competition.target_grades or ["大一", "大二", "大三", "大四"]
        competition.tags = infer_tags(name, catalog_level, category)
        competition.status = "published"
        competition.registration_deadline_at = None
        competition.competition_start_at = None
        competition.competition_end_at = None
        competition.official_url = official_url
        competition.heat = max(competition.heat or 0, CATALOG_HEAT[catalog_level])
        competition.score = max(competition.score or 0, score)
        competition.score_reason = [
            f"{catalog_level}类竞赛目录认定",
            f"{category}方向",
            "已纳入北京工业大学2023版本科生科技竞赛认定目录",
        ]
    db.session.commit()

    for item in CATALOG_ITEMS:
        competition = Competition.query.filter_by(title=item["name"]).first()
        if competition is None:
            continue
        upsert_source(
            competition,
            "北京工业大学本科生科技竞赛认定目录（2023版）",
            f"bjut-catalog-2023:{item['catalog_level']}",
            {"catalog_level": item["catalog_level"], "number": item["number"], "code": item["code"]},
        )
        if competition.official_url:
            upsert_source(
                competition,
                "赛事官网",
                competition.official_url,
                {"timeline_note": match_official_info(competition.title).get("timeline")},
            )
    db.session.commit()


def seed_forum(student: User) -> None:
    if Post.query.count() > 0:
        return
    posts = [
        Post(
            author_id=student.id,
            title="蓝桥杯组队刷题，有没有同方向同学？",
            content="我主要做 Python 和算法，希望找 2-3 位同学一起刷题和复盘。",
            post_type="team",
            tags=["蓝桥杯", "程序设计", "组队"],
        ),
        Post(
            author_id=student.id,
            title="数学建模省赛资料整理",
            content="整理了一些建模论文模板和常用模型，欢迎补充。",
            post_type="experience",
            tags=["数学建模", "资料"],
        ),
    ]
    db.session.add_all(posts)
    db.session.commit()


def seed_certification(student: User) -> None:
    exists = CertificationRequest.query.filter_by(user_id=student.id, status="approved").first()
    if exists:
        return
    db.session.add(
        CertificationRequest(
            user_id=student.id,
            certification_type="premium",
            description="蓝桥杯省级一等奖，算法与程序设计方向指导人",
            status="approved",
            review_comment="种子认证，用于演示 premium 指导人标识。",
        )
    )
    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        admin = upsert_user("admin", "admin123", "admin")
        student = upsert_user("student", "student123", "student")
        teammate = upsert_user("teammate", "student123", "student")
        teammate.profile.real_name = teammate.profile.real_name or "组队样例同学"
        teammate.profile.major = "软件工程"
        teammate.profile.interests = ["Python", "算法", "蓝桥杯", "前端"]
        teammate.profile.competition_experiences = [
            {"competition": "蓝桥杯", "category": "程序设计", "level": "省一", "year": "2025"}
        ]
        db.session.commit()
        ensure_team_preference(student)
        ensure_team_preference(teammate)
        db.session.commit()
        upsert_catalog_competitions(admin)
        seed_forum(student)
        seed_certification(student)
        print(f"Seed completed. competitions={Competition.query.count()} admin/admin123 student/student123")


if __name__ == "__main__":
    main()
