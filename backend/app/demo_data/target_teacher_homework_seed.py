from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore


TARGET_STUDENT_ID = "23001020119"
TEACHER_USERNAME = "teacher_su"
TEACHER_REAL_NAME = "苏老师"
TEACHER_ID = "T-SU-2026"
TEACHER_PASSWORD = "123456"
ROLE = "target_teacher_homework_seed"
HOMEWORK_PREFIX = "target-teacher-su-hw"
CHINA_TZ = timezone(timedelta(hours=8))


def seed_target_teacher_homework_data(
    db: Session,
    *,
    teacher_root: str | Path = r"D:\演示账号的同学文件\团队仓库测试\教师账户",
    static_root: str | Path | None = None,
    anchor_now: datetime | None = None,
    reset_homeworks: bool = False,
) -> dict[str, Any]:
    """Create Su teacher and publish target-student demo homework records."""
    now = _normalize_now(anchor_now)
    if static_root is None:
        static_root = Path(__file__).resolve().parents[1] / "static"
    static_path = Path(static_root)

    teacher_avatar = _copy_teacher_avatar(Path(teacher_root), static_path / "avatars")
    _upsert_teacher(db, teacher_avatar)

    if reset_homeworks:
        _delete_seed_homeworks(db)

    homeworks = _build_homeworks(now)
    store = JsonStore(db)
    for homework in homeworks:
        store.upsert(
            "homework",
            "homework",
            homework["id"],
            homework,
            owner_id=TEACHER_USERNAME,
            role=ROLE,
            status=homework["status"],
        )

    return {
        "teacherUsername": TEACHER_USERNAME,
        "teacherName": TEACHER_REAL_NAME,
        "teacherId": TEACHER_ID,
        "targetStudent": TARGET_STUDENT_ID,
        "homeworks": len(homeworks),
        "avatar": teacher_avatar,
        "staticRoot": str(static_path),
    }


def _normalize_now(anchor_now: datetime | None) -> datetime:
    now = anchor_now or datetime.now(CHINA_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CHINA_TZ)
    return now.astimezone(CHINA_TZ)


def _copy_teacher_avatar(teacher_root: Path, avatar_dir: Path) -> str:
    source = teacher_root / "头像.jpg"
    if not source.exists():
        candidates = [
            item
            for item in teacher_root.iterdir()
            if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ] if teacher_root.exists() else []
        if not candidates:
            raise FileNotFoundError(f"teacher avatar not found under {teacher_root}")
        source = candidates[0]

    avatar_dir.mkdir(parents=True, exist_ok=True)
    avatar_name = "teacher_su.jpg"
    shutil.copyfile(source, avatar_dir / avatar_name)
    return avatar_name


def _upsert_teacher(db: Session, avatar_path: str) -> None:
    account = db.query(UserAccount).filter(UserAccount.username == TEACHER_USERNAME).first()
    if not account:
        account = UserAccount(username=TEACHER_USERNAME)
        db.add(account)
    account.role = "teacher"
    account.password_hash = get_password_hash(TEACHER_PASSWORD)
    account.phone = ""
    account.real_name = TEACHER_REAL_NAME
    account.student_id = ""
    account.teacher_id = TEACHER_ID
    account.class_name = "23006"
    account.avatar_path = avatar_path
    db.commit()


def _delete_seed_homeworks(db: Session) -> None:
    rows = (
        db.query(DomainRecord)
        .filter(
            DomainRecord.module == "homework",
            DomainRecord.record_type == "homework",
            DomainRecord.record_key.like(f"{HOMEWORK_PREFIX}-%"),
        )
        .all()
    )
    for row in rows:
        db.delete(row)
    db.commit()


def _deadline(now: datetime, days: int, hour: int = 18, minute: int = 0) -> str:
    return (now + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0).strftime("%Y/%m/%d %H:%M:%S")


def _ts(now: datetime, minutes_ago: int) -> str:
    return (now - timedelta(minutes=minutes_ago)).replace(second=0, microsecond=0).isoformat()


def _build_homeworks(now: datetime) -> list[dict[str, Any]]:
    specs = [
        {
            "id": f"{HOMEWORK_PREFIX}-ds-stack-queue",
            "subjectId": "DS-201",
            "subjectName": "数据结构与算法",
            "title": "栈与队列基础概念随堂练习",
            "deadlineDays": 1,
            "urgent": True,
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "栈结构最典型的访问规则是？",
                    "options": ["先进先出", "后进先出", "随机访问", "按权重访问"],
                    "correctAnswer": "后进先出",
                    "knowledgePoint": "栈",
                },
                {
                    "id": "q2",
                    "type": "blank",
                    "title": "队列结构通常遵循 ______ 的访问规则。",
                    "correctAnswers": ["先进先出", "FIFO"],
                    "knowledgePoint": "队列",
                },
            ],
        },
        {
            "id": f"{HOMEWORK_PREFIX}-db-index",
            "subjectId": "DB-301",
            "subjectName": "数据库系统原理",
            "title": "B+ 树索引与覆盖索引小测",
            "deadlineDays": 2,
            "urgent": True,
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "B+ 树中真实数据记录通常保存在什么节点？",
                    "options": ["根节点", "内部节点", "叶子节点", "日志节点"],
                    "correctAnswer": "叶子节点",
                    "knowledgePoint": "B+ 树索引",
                },
                {
                    "id": "q2",
                    "type": "blank",
                    "title": "查询所需字段都能从索引中取得时，该索引可称为 ______。",
                    "correctAnswers": ["覆盖索引"],
                    "knowledgePoint": "覆盖索引",
                },
            ],
        },
        {
            "id": f"{HOMEWORK_PREFIX}-python-basic",
            "subjectId": "PY-101",
            "subjectName": "Python 程序设计",
            "title": "Python 列表与字典基础题",
            "deadlineDays": 3,
            "urgent": False,
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "以下哪种结构最适合按键快速查找值？",
                    "options": ["list", "tuple", "dict", "set"],
                    "correctAnswer": "dict",
                    "knowledgePoint": "字典",
                },
                {
                    "id": "q2",
                    "type": "blank",
                    "title": "Python 中列表推导式常用一对 ______ 包裹表达式。",
                    "correctAnswers": ["方括号", "[]"],
                    "knowledgePoint": "列表推导式",
                },
            ],
        },
        {
            "id": f"{HOMEWORK_PREFIX}-network-http",
            "subjectId": "NET-202",
            "subjectName": "计算机网络",
            "title": "HTTP 状态码与请求方法练习",
            "deadlineDays": 4,
            "urgent": False,
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "HTTP 404 状态码通常表示什么？",
                    "options": ["请求成功", "资源未找到", "服务器内部错误", "未认证"],
                    "correctAnswer": "资源未找到",
                    "knowledgePoint": "HTTP 状态码",
                },
                {
                    "id": "q2",
                    "type": "blank",
                    "title": "REST 风格中，创建资源常使用 ______ 请求方法。",
                    "correctAnswers": ["POST"],
                    "knowledgePoint": "HTTP 方法",
                },
            ],
        },
        {
            "id": f"{HOMEWORK_PREFIX}-ai-attention",
            "subjectId": "AI-101",
            "subjectName": "人工智能技术基础",
            "title": "Attention 机制选择与填空",
            "deadlineDays": 5,
            "urgent": False,
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "Scaled Dot-Product Attention 中除以 sqrt(d_k) 的主要目的是什么？",
                    "options": ["减少参数量", "避免 Softmax 过饱和", "替代位置编码", "增加序列长度"],
                    "correctAnswer": "避免 Softmax 过饱和",
                    "knowledgePoint": "注意力缩放",
                },
                {
                    "id": "q2",
                    "type": "blank",
                    "title": "Transformer 中 Query、Key、Value 通常简称为 ______。",
                    "correctAnswers": ["QKV", "Q K V"],
                    "knowledgePoint": "注意力输入",
                },
            ],
        },
        {
            "id": f"{HOMEWORK_PREFIX}-software-test",
            "subjectId": "SE-501",
            "subjectName": "软件工程综合实训",
            "title": "单元测试与 Pull Request Review",
            "deadlineDays": 6,
            "urgent": False,
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "单元测试最核心的目标是？",
                    "options": ["替代所有人工测试", "验证最小功能单元行为", "生成 UI 截图", "发布生产版本"],
                    "correctAnswer": "验证最小功能单元行为",
                    "knowledgePoint": "单元测试",
                },
                {
                    "id": "q2",
                    "type": "blank",
                    "title": "Pull Request 中通常需要说明变更范围、自测结果和 ______。",
                    "correctAnswers": ["风险点", "影响范围"],
                    "knowledgePoint": "代码评审",
                },
            ],
        },
        {
            "id": f"{HOMEWORK_PREFIX}-os-process",
            "subjectId": "OS-202",
            "subjectName": "操作系统",
            "title": "进程线程与同步互斥练习",
            "deadlineDays": 7,
            "urgent": False,
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "多个线程共享同一进程的哪类资源？",
                    "options": ["地址空间", "独立页表", "独立进程号", "独立文件系统"],
                    "correctAnswer": "地址空间",
                    "knowledgePoint": "线程资源共享",
                },
                {
                    "id": "q2",
                    "type": "blank",
                    "title": "用于保护临界区的常见机制包括互斥锁和 ______。",
                    "correctAnswers": ["信号量"],
                    "knowledgePoint": "同步互斥",
                },
            ],
        },
        {
            "id": f"{HOMEWORK_PREFIX}-frontend-vue",
            "subjectId": "FE-401",
            "subjectName": "高级前端程序设计",
            "title": "Vue 响应式原理基础练习",
            "deadlineDays": 8,
            "urgent": False,
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "Vue 3 响应式系统主要依赖哪项 JavaScript 能力？",
                    "options": ["Proxy", "XMLHttpRequest", "Canvas", "WebSocket"],
                    "correctAnswer": "Proxy",
                    "knowledgePoint": "Vue 响应式",
                },
                {
                    "id": "q2",
                    "type": "blank",
                    "title": "依赖收集和触发更新常被称为 track 与 ______。",
                    "correctAnswers": ["trigger"],
                    "knowledgePoint": "track/trigger",
                },
            ],
        },
    ]

    homeworks = []
    for index, spec in enumerate(specs):
        created_at = _ts(now, 90 - index * 7)
        homework = {
            "id": spec["id"],
            "subjectId": spec["subjectId"],
            "subjectName": spec["subjectName"],
            "subject": spec["subjectName"],
            "type": "daily",
            "title": spec["title"],
            "deadline": _deadline(now, spec["deadlineDays"]),
            "urgent": spec["urgent"],
            "status": "unsubmitted",
            "grade": None,
            "teacherComment": "",
            "diagnosis": None,
            "submittedAnswers": {},
            "submittedFile": None,
            "questions": spec["questions"],
            "blocks": [],
            "teacherId": TEACHER_USERNAME,
            "teacherName": TEACHER_REAL_NAME,
            "targetStudentId": TARGET_STUDENT_ID,
            "className": "23006",
            "createdAt": created_at,
            "updatedAt": created_at,
        }
        homeworks.append(homework)
    return homeworks
