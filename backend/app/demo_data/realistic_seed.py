from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.domain_record import DomainRecord
from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore


DEMO_PASSWORD = "Demo@2026"
TEACHER_PASSWORD = "Teacher@2026"
DEMO_ROLE = "demo_realistic_seed"
CHINA_TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class DemoStudent:
    username: str
    real_name: str
    student_id: str
    class_name: str
    phone: str
    avatar_path: str
    knowledge: int
    pace: int
    cognitive: str
    error_pattern: str
    goal: str
    background: str


@dataclass(frozen=True)
class DemoTeacher:
    username: str
    real_name: str
    teacher_id: str
    class_name: str
    phone: str


from app.services.gitea_account_service import ensure_gitea_account_for_user


def _sync_seed_gitea_accounts(db: Session, accounts: list[UserAccount]) -> dict:
    summary = {"synced": 0, "mock": 0, "failed": 0}
    for account in accounts:
        try:
            identity = ensure_gitea_account_for_user(db, account)
            if identity.sync_status == "synced":
                summary["synced"] += 1
            elif identity.sync_status == "mock":
                summary["mock"] += 1
            else:
                summary["failed"] += 1
        except Exception:
            summary["failed"] += 1
    return summary


def seed_realistic_demo_data(
    db: Session,
    *,
    data_root: str | Path = r"D:\软件杯测试数据注入",
    static_root: str | Path | None = None,
    anchor_now: datetime | None = None,
    reset_demo: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Seed a coherent, realistic demo dataset into the current database session."""
    root = Path(data_root)
    if static_root is None:
        static_root = Path(__file__).resolve().parents[1] / "static"
    static_path = Path(static_root)
    now = _normalize_now(anchor_now)

    names = _parse_student_names(root / "学生姓名.txt")
    avatar_files = _avatar_files(root / "头像")
    students = _build_students(names, avatar_files)
    teachers = _build_teachers()
    dataset = _build_dataset(students, teachers, now)
    summary = {
        "students": len(students),
        "teachers": len(teachers),
        "homeworks": len(dataset["homeworks"]),
        "submissions": len(dataset["homework_submissions"]),
        "exams": len(dataset["exams"]),
        "examAttempts": len(dataset["exam_attempts"]),
        "mistakes": len(dataset["mistakes"]),
        "forumPosts": len(dataset["forum_posts"]),
        "codeRepositories": len(dataset["code_repositories"]),
        "teamProjects": len(dataset["team_projects"]),
        "analyticsRecords": len(dataset["analytics"]),
    }
    if dry_run:
        return summary

    if reset_demo:
        _reset_demo_records(db)

    _copy_avatars(students, avatar_files, static_path / "avatars")
    for student in students:
        _upsert_student(db, student)
    for teacher in teachers:
        _upsert_teacher(db, teacher)

    store = JsonStore(db)
    _upsert_payloads(store, "homework", "homework", dataset["homeworks"])
    _upsert_payloads(store, "homework", "submission", dataset["homework_submissions"], owner_field="studentId")
    _upsert_payloads(store, "homework", "diagnosis", dataset["homework_diagnoses"])
    _upsert_payloads(store, "exams", "exam", dataset["exams"], status_field="status")
    _upsert_payloads(store, "exams", "attempt", dataset["exam_attempts"], owner_field="studentId", status_field="status")
    _upsert_payloads(store, "exams", "mistake", dataset["mistakes"], owner_field="studentId")
    _upsert_payloads(store, "exams", "review_task", dataset["review_tasks"], status_field="status")
    _upsert_payloads(store, "forum", "post", dataset["forum_posts"])
    _upsert_payloads(store, "forum", "announcement", dataset["announcements"])
    _upsert_payloads(store, "forum", "hot_topic", dataset["hot_topics"])
    _upsert_payloads(store, "forum", "ai_reply_log", dataset["ai_reply_logs"], status_field="status")
    _upsert_payloads(store, "code_repository", "project", dataset["code_repositories"], owner_field="author", status_field="status")
    _upsert_payloads(store, "code_repository", "star", dataset["stars"], owner_field="userId", status_field="status")
    _upsert_payloads(store, "code_repository", "favorite", dataset["favorites"], owner_field="userId", status_field="status")
    _upsert_payloads(store, "code_repository", "report", dataset["repo_reports"], owner_field="reporter", status_field="status")
    _upsert_payloads(store, "team_collaboration_git", "project", dataset["team_projects"], owner_field="ownerId", status_field="status")
    _upsert_payloads(store, "analytics", "advice", dataset["analytics_advices"], status_field="status")
    _upsert_payloads(store, "analytics", "action", dataset["analytics_actions"], status_field="status")
    _upsert_payloads(store, "analytics", "interaction", dataset["analytics"], status_field="status")
    created_accounts = db.query(UserAccount).filter(UserAccount.role.in_(["student", "teacher"])).all()
    summary["gitea_accounts"] = _sync_seed_gitea_accounts(db, created_accounts)
    return summary


def _normalize_now(anchor_now: datetime | None) -> datetime:
    now = anchor_now or datetime.now(CHINA_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CHINA_TZ)
    return now.astimezone(CHINA_TZ)


def _parse_student_names(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"学生姓名文件不存在: {path}")
    names: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^\d+[\.、]\s*(.+?)\s*$", line)
        if match:
            names.append(match.group(1))
    if not names:
        raise ValueError(f"学生姓名文件没有解析到姓名: {path}")
    return names


def _avatar_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    files = [item for item in path.iterdir() if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]

    def sort_key(item: Path) -> tuple[int, str]:
        match = re.search(r"\((\d+)\)", item.name)
        return (int(match.group(1)) if match else 9999, item.name)

    return sorted(files, key=sort_key)


def _build_students(names: list[str], avatar_files: list[Path]) -> list[DemoStudent]:
    class_names = ["计科 2301", "计科 2302", "软工 2301"]
    cognitives = ["偏好代码实践", "递进拆解型", "先画图再编码", "喜欢反例纠错", "重视公式推导"]
    error_patterns = [
        "链表指针更新顺序、递归返回条件",
        "SQL JOIN 条件遗漏、索引选择性判断",
        "哈希表建模慢、复杂度估计不稳",
        "Proxy receiver 语义、响应式依赖收集",
        "事务隔离级别与 B+ 树叶子节点职责",
        "矩阵维度推导、Softmax 梯度饱和",
    ]
    students: list[DemoStudent] = []
    for index, name in enumerate(names, start=1):
        student_id = f"202300{index:02d}"
        avatar_ext = avatar_files[index - 1].suffix.lower() if index - 1 < len(avatar_files) else ".jpg"
        knowledge = 62 + (index * 7) % 31
        if index % 9 == 0:
            knowledge = 48
        pace = 58 + (index * 5) % 34
        students.append(
            DemoStudent(
                username=student_id,
                real_name=name,
                student_id=student_id,
                class_name=class_names[(index - 1) % len(class_names)],
                phone=f"139{index:08d}"[-11:],
                avatar_path=f"{student_id}{avatar_ext}",
                knowledge=knowledge,
                pace=pace,
                cognitive=cognitives[(index - 1) % len(cognitives)],
                error_pattern=error_patterns[(index - 1) % len(error_patterns)],
                goal=["补齐数据结构薄弱点", "完成团队实训 PR 闭环", "把课程项目整理成可展示仓库"][index % 3],
                background=["计算机科学与技术", "软件工程", "人工智能实验班"][index % 3],
            )
        )
    return students


def _build_teachers() -> list[DemoTeacher]:
    return [
        DemoTeacher("teacher_chen", "陈思远", "T202601", "计科 2301", "13800010001"),
        DemoTeacher("teacher_li", "李清岚", "T202602", "计科 2302", "13800010002"),
        DemoTeacher("teacher_wu", "吴彦章", "T202603", "软工 2301", "13800010003"),
    ]


def _copy_avatars(students: list[DemoStudent], avatar_files: list[Path], avatar_dir: Path) -> None:
    avatar_dir.mkdir(parents=True, exist_ok=True)
    for index, student in enumerate(students):
        if index >= len(avatar_files):
            continue
        shutil.copyfile(avatar_files[index], avatar_dir / student.avatar_path)


def _upsert_student(db: Session, student: DemoStudent) -> None:
    account = db.query(UserAccount).filter(UserAccount.username == student.username).first()
    if not account:
        account = UserAccount(username=student.username)
        db.add(account)
    account.role = "student"
    account.password_hash = get_password_hash(DEMO_PASSWORD)
    account.phone = student.phone
    account.real_name = student.real_name
    account.student_id = student.student_id
    account.teacher_id = ""
    account.class_name = student.class_name
    account.avatar_path = student.avatar_path

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == student.username).first()
    if not profile:
        profile = StudentProfile(user_id=student.username)
        db.add(profile)
    profile.knowledge = student.knowledge
    profile.cognitive = student.cognitive
    profile.pace = student.pace
    profile.error_pattern = student.error_pattern
    profile.goal = student.goal
    profile.background = student.background
    db.commit()


def _upsert_teacher(db: Session, teacher: DemoTeacher) -> None:
    account = db.query(UserAccount).filter(UserAccount.username == teacher.username).first()
    if not account:
        account = UserAccount(username=teacher.username)
        db.add(account)
    account.role = "teacher"
    account.password_hash = get_password_hash(TEACHER_PASSWORD)
    account.phone = teacher.phone
    account.real_name = teacher.real_name
    account.student_id = ""
    account.teacher_id = teacher.teacher_id
    account.class_name = teacher.class_name
    account.avatar_path = ""
    db.commit()


def _reset_demo_records(db: Session) -> None:
    demo_modules = {
        "homework",
        "exams",
        "forum",
        "code_repository",
        "team_collaboration_git",
        "analytics",
    }
    records = (
        db.query(DomainRecord)
        .filter(
            DomainRecord.module.in_(demo_modules),
            (DomainRecord.record_key.like("demo-%")) | (DomainRecord.record_key.like("codex-%")),
        )
        .all()
    )
    for record in records:
        db.delete(record)
    db.commit()


def _upsert_payloads(
    store: JsonStore,
    module: str,
    record_type: str,
    payloads: list[dict[str, Any]],
    *,
    owner_field: str | None = None,
    status_field: str | None = None,
) -> None:
    for payload in payloads:
        owner_id = str(payload.get(owner_field) or "") if owner_field else ""
        if owner_field == "ownerId":
            owner_id = str(payload.get("project", {}).get("createdBy") or payload.get("ownerId") or "")
            payload = {key: value for key, value in payload.items() if key != "ownerId"}
        status = str(payload.get(status_field) or "") if status_field else str(payload.get("status") or "")
        store.upsert(module, record_type, str(payload["id"]), payload, owner_id=owner_id, role=DEMO_ROLE, status=status)


def _build_dataset(students: list[DemoStudent], teachers: list[DemoTeacher], now: datetime) -> dict[str, Any]:
    homeworks, submissions, diagnoses, homework_mistakes = _build_homework_data(students, now)
    exams, exam_attempts, exam_mistakes, review_tasks = _build_exam_data(students, now)
    forum_posts, announcements, hot_topics, ai_logs = _build_forum_data(students, teachers, now)
    repos, stars, favorites, reports = _build_code_repository_data(students, teachers, now)
    team_projects = _build_team_projects(students, teachers, now)
    advices, actions, interactions = _build_analytics_data(students, homework_mistakes + exam_mistakes, now)
    return {
        "homeworks": homeworks,
        "homework_submissions": submissions,
        "homework_diagnoses": diagnoses,
        "exams": exams,
        "exam_attempts": exam_attempts,
        "mistakes": homework_mistakes + exam_mistakes,
        "review_tasks": review_tasks,
        "forum_posts": forum_posts,
        "announcements": announcements,
        "hot_topics": hot_topics,
        "ai_reply_logs": ai_logs,
        "code_repositories": repos,
        "stars": stars,
        "favorites": favorites,
        "repo_reports": reports,
        "team_projects": team_projects,
        "analytics_advices": advices,
        "analytics_actions": actions,
        "analytics": interactions,
    }


def _ts(now: datetime, days_ago: int, hour: int, minute: int = 0) -> str:
    return (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


def _date_label(now: datetime, days_ago: int, hour: int, minute: int = 0) -> str:
    return (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0).strftime("%Y/%m/%d %H:%M:%S")


def _score_for(student_index: int, base: int = 76) -> int:
    score = base + ((student_index * 9) % 22) - (8 if student_index % 7 == 0 else 0)
    return max(45, min(98, score))


def _diagnosis(score: int, weak: str, strong: str) -> dict[str, Any]:
    return {
        "scores": {
            "alina": max(40, min(100, score - 2)),
            "codeninja": max(40, min(100, score + 3)),
            "profx": max(40, min(100, score)),
        },
        "alinaMsg": f"Alina诊断：学习路径基本稳定，下一步建议围绕「{weak}」做一次结构化复盘。",
        "codeninjaMsg": f"CodeNinja诊断：代码实现中「{strong}」表现较好，但边界用例还需要继续补齐。",
        "profxMsg": f"Prof. X诊断：理论表达能覆盖主干概念，建议把错因写成可复用的解题模板。",
    }


def _build_homework_data(students: list[DemoStudent], now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    specs = [
        {
            "id": "demo-hw-ds-linked-stack",
            "subjectId": "DS-201",
            "subjectName": "数据结构与算法",
            "type": "daily",
            "title": "链表指针更新与栈递归现场复盘",
            "deadline": _date_label(now, 1, 17, 30),
            "knowledgePoint": "链表指针顺序与递归调用栈",
            "questions": [
                {
                    "id": "q1",
                    "type": "choice",
                    "title": "删除单链表中间节点时，为什么必须先保存 next 指针？",
                    "options": ["避免节点丢失", "提升 CPU 缓存命中", "减少栈空间", "改变链表长度"],
                    "correctAnswer": "避免节点丢失",
                    "knowledgePoint": "链表断链风险",
                },
                {"id": "q2", "type": "blank", "title": "递归调用现场由 ______ 结构保存。", "correctAnswers": ["栈"], "knowledgePoint": "调用栈"},
                {
                    "id": "q3",
                    "type": "programming",
                    "title": "原地反转单链表",
                    "desc": "实现 reverseList(head)，要求 O(1) 额外空间，并说明 curr.next 备份的必要性。",
                    "starterCode": "function reverseList(head) {\n  let prev = null;\n  let curr = head;\n  // TODO\n}",
                    "knowledgePoint": "链表反转",
                },
            ],
        },
        {
            "id": "demo-hw-db-index-join",
            "subjectId": "DB-301",
            "subjectName": "数据库系统原理",
            "type": "daily",
            "title": "SQL 多表查询与 B+ 树索引分析",
            "deadline": _date_label(now, 3, 16, 40),
            "knowledgePoint": "JOIN 条件与 B+ 树叶子节点",
            "questions": [
                {"id": "q1", "type": "choice", "title": "B+ 树中真实记录指针通常位于哪里？", "options": ["根节点", "内部节点", "叶子节点", "日志文件"], "correctAnswer": "叶子节点", "knowledgePoint": "B+ 树索引"},
                {"id": "q2", "type": "text", "title": "解释覆盖索引为什么能减少回表。", "desc": "请结合 SELECT 字段和二级索引结构说明。", "knowledgePoint": "覆盖索引"},
                {"id": "q3", "type": "programming", "title": "写出课程成绩 Top-N 查询 SQL", "desc": "给定 students、scores、courses 三张表，查询每门课前三名。", "starterCode": "-- 使用窗口函数完成\n", "knowledgePoint": "窗口函数"},
            ],
        },
        {
            "id": "demo-hw-fe-reactive",
            "subjectId": "FE-401",
            "subjectName": "高级前端程序设计",
            "type": "daily",
            "title": "Vue 响应式系统 Proxy 与 Reflect",
            "deadline": _date_label(now, 5, 17, 0),
            "knowledgePoint": "Proxy receiver 与依赖收集",
            "questions": [
                {"id": "q1", "type": "choice", "title": "Reflect.get(target, key, receiver) 中 receiver 的主要价值是什么？", "options": ["修复 getter this 指向", "加快解析速度", "触发宏任务", "减少闭包"], "correctAnswer": "修复 getter this 指向", "knowledgePoint": "Reflect receiver"},
                {"id": "q2", "type": "blank", "title": "get 阶段收集依赖通常称为 ______，set 阶段触发更新称为 ______。", "correctAnswers": ["track", "trigger"], "knowledgePoint": "track/trigger"},
                {"id": "q3", "type": "programming", "title": "实现最小 reactive", "desc": "补全 get/set 拦截，要求使用 Reflect，并调用 track/trigger。", "starterCode": "function reactive(target) {\n  return new Proxy(target, {\n    get(target, key, receiver) {},\n    set(target, key, value, receiver) {}\n  })\n}", "knowledgePoint": "响应式实现"},
            ],
        },
        {
            "id": "demo-hw-ai-attention",
            "subjectId": "AI-101",
            "subjectName": "人工智能技术基础",
            "type": "milestone",
            "title": "自注意力矩阵维度与缩放因子推导",
            "deadline": _date_label(now, 7, 15, 30),
            "knowledgePoint": "Scaled Dot-Product Attention",
            "questions": [
                {"id": "q1", "type": "choice", "title": "Attention 中除以 sqrt(d_k) 的原因是？", "options": ["避免 Softmax 过饱和", "减少参数量", "增强位置编码", "替代归一化层"], "correctAnswer": "避免 Softmax 过饱和", "knowledgePoint": "注意力缩放"},
                {"id": "q2", "type": "text", "title": "推导 QK^T 的矩阵维度。", "desc": "从 Batch、SeqLen、d_model、head_dim 逐步说明。", "knowledgePoint": "矩阵维度"},
            ],
        },
        {
            "id": "demo-hw-co-cache",
            "subjectId": "CO-202",
            "subjectName": "计算机组成原理",
            "type": "daily",
            "title": "Cache 映射策略与缺失率分析",
            "deadline": _date_label(now, 9, 16, 0),
            "knowledgePoint": "Cache 直接映射与组相联",
            "questions": [
                {"id": "q1", "type": "choice", "title": "直接映射 Cache 最容易出现哪类冲突？", "options": ["冲突缺失", "容量无限", "TLB 失效", "写穿透"], "correctAnswer": "冲突缺失", "knowledgePoint": "Cache 冲突"},
                {"id": "q2", "type": "text", "title": "计算给定地址的 tag/index/offset。", "desc": "请写出拆分过程和二进制位数。", "knowledgePoint": "地址拆分"},
            ],
        },
        {
            "id": "demo-hw-se-pr-review",
            "subjectId": "SE-501",
            "subjectName": "软件工程综合实训",
            "type": "capstone",
            "title": "接口契约、单元测试与 Pull Request 评审",
            "deadline": _date_label(now, 11, 17, 20),
            "knowledgePoint": "API 契约与 PR 审核",
            "questions": [
                {"id": "q1", "type": "text", "title": "为仓库主页接口写出验收清单。", "desc": "包含字段、权限、错误码和回归测试。", "knowledgePoint": "接口契约"},
                {"id": "q2", "type": "programming", "title": "补充 repository service 的单元测试", "desc": "用伪 Gitea 服务验证 README、Star、收藏、举报审核四个流程。", "starterCode": "def test_repository_detail_reads_readme():\n    pass\n", "knowledgePoint": "服务测试"},
            ],
        },
    ]
    homeworks: list[dict[str, Any]] = []
    submissions: list[dict[str, Any]] = []
    diagnoses: list[dict[str, Any]] = []
    mistakes: list[dict[str, Any]] = []
    for spec_index, spec in enumerate(specs):
        homework = {
            **spec,
            "urgent": spec_index < 2,
            "status": "unsubmitted",
            "grade": None,
            "teacherComment": "",
            "diagnosis": None,
            "submittedAnswers": {},
            "submittedFile": None,
            "createdAt": _ts(now, 13 - spec_index * 2, 9, 20),
            "updatedAt": _ts(now, max(1, 12 - spec_index * 2), 15, 10),
            "teacherId": "teacher_chen" if spec_index % 2 == 0 else "teacher_li",
        }
        homeworks.append(homework)
        for student_index, student in enumerate(students):
            if student_index % 5 == spec_index % 5 and spec_index > 2:
                continue
            score = _score_for(student_index + spec_index, 72 + spec_index * 2)
            status = "graded" if score >= 65 and student_index % 4 != 0 else "pending"
            if score < 60:
                status = "review"
            submitted_at = _ts(now, max(1, 12 - spec_index * 2), 9 + (student_index % 8), (student_index * 7) % 50)
            diagnosis = _diagnosis(score, spec["knowledgePoint"], spec["questions"][-1]["knowledgePoint"])
            submission_id = f"{spec['id']}:{student.username}"
            submissions.append(
                {
                    "id": submission_id,
                    "studentId": student.username,
                    "studentName": student.real_name,
                    "className": student.class_name,
                    "homeworkId": spec["id"],
                    "homeworkTitle": spec["title"],
                    "submittedAt": submitted_at,
                    "answers": _answers_for(spec, score),
                    "file": None if spec_index % 3 else f"{student.username}-{spec['id']}.zip",
                    "status": status,
                    "grade": _grade(score) if status == "graded" else None,
                    "teacherComment": _teacher_homework_comment(score, spec["knowledgePoint"]) if status == "graded" else "",
                    "diagnosis": diagnosis,
                    "classInsight": "本次作业共性问题已经同步到错题本和教师学情决策台。",
                    "questionResults": _question_results(score, spec),
                }
            )
            diag_id = f"demo-diag-{spec['id']}-{student.username}"
            diagnoses.append({"id": diag_id, "homeworkId": spec["id"], "studentId": student.username, **diagnosis, "generatedAt": submitted_at})
            if score < 78 or student_index % 6 == 0:
                question = spec["questions"][-1]
                mistakes.append(
                    _mistake(
                        id_=f"demo-mistake-hw-{spec_index}-{student.username}",
                        student=student,
                        subject=spec["subjectName"],
                        question_id=f"{spec['id']}-{question['id']}",
                        question_type=_question_type_label(question["type"]),
                        question_title=question["title"],
                        student_answer=_wrong_answer_for(spec),
                        correct_answer=_correct_answer_for(question),
                        error_reason=_homework_error_reason(spec["knowledgePoint"]),
                        tags=[spec["knowledgePoint"], question["knowledgePoint"], "作业错题"],
                        last_wrong_at=submitted_at,
                        source={"type": "homework", "homeworkId": spec["id"], "submissionId": submission_id},
                        wrong_count=1 + ((student_index + spec_index) % 3),
                        mastered=score >= 72,
                    )
                )
    return homeworks, submissions, diagnoses, mistakes


def _answers_for(spec: dict[str, Any], score: int) -> dict[str, str]:
    answers: dict[str, str] = {}
    for question in spec["questions"]:
        if question["type"] == "choice":
            answers[question["id"]] = question.get("correctAnswer", "") if score >= 70 else "队列"
        elif question["type"] == "blank":
            values = question.get("correctAnswers") or []
            for index, value in enumerate(values):
                answers[f"{question['id']}_{index}"] = value if score >= 70 else "collect"
        elif question["type"] == "programming":
            answers[question["id"]] = _programming_answer(spec["id"], score)
        else:
            answers[question["id"]] = "我先列出定义，再结合课堂例子说明边界条件和工程取舍。"
    return answers


def _programming_answer(homework_id: str, score: int) -> str:
    if "linked" in homework_id:
        return "while (curr) { const next = curr.next; curr.next = prev; prev = curr; curr = next; }" if score >= 70 else "while (curr) { curr.next = prev; curr = curr.next; }"
    if "reactive" in homework_id:
        return "get(t,k,r){ track(t,k); return Reflect.get(t,k,r) } set(t,k,v,r){ const ok=Reflect.set(t,k,v,r); trigger(t,k,v); return ok }" if score >= 70 else "get(t,k){ return t[k] } set(t,k,v){ t[k]=v; return true }"
    if "se-pr" in homework_id:
        return "self.assertIn('readme', detail); self.assertEqual(state['starCount'], 1)" if score >= 70 else "assert service is not None"
    return "SELECT * FROM ranked WHERE rn <= 3;"


def _question_results(score: int, spec: dict[str, Any]) -> dict[str, bool]:
    return {question["id"]: score >= (75 if question["type"] == "programming" else 65) for question in spec["questions"]}


def _question_type_label(kind: str) -> str:
    return {"choice": "选择题", "blank": "填空题", "programming": "编程题", "text": "简答题"}.get(kind, kind)


def _correct_answer_for(question: dict[str, Any]) -> str:
    if question.get("correctAnswer"):
        return str(question["correctAnswer"])
    if question.get("correctAnswers"):
        return "、".join(question["correctAnswers"])
    return question.get("desc") or "参考课堂标准解法和代码评审意见。"


def _wrong_answer_for(spec: dict[str, Any]) -> str:
    if "链表" in spec["knowledgePoint"]:
        return "直接 curr = curr.next，未保存 next，导致链断开。"
    if "JOIN" in spec["knowledgePoint"]:
        return "把筛选条件写在 WHERE 后但遗漏课程表关联，结果出现重复行。"
    if "Proxy" in spec["knowledgePoint"]:
        return "直接 target[key]，没有传 receiver。"
    if "Attention" in spec["knowledgePoint"]:
        return "把 QK^T 的维度写成 [d_k, d_k]。"
    return "只给出结论，没有写出推导过程。"


def _homework_error_reason(point: str) -> str:
    return f"对「{point}」的触发条件和工程边界理解不稳定，容易套用熟悉模板而忽略题目约束。"


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "E"


def _teacher_homework_comment(score: int, point: str) -> str:
    if score >= 90:
        return f"完成度高，能把 {point} 放到具体代码场景中解释，建议补充一组边界测试。"
    if score >= 75:
        return f"主干思路正确，{point} 的细节还有一点跳步，订正时把关键变量变化写清楚。"
    return f"需要重新复盘 {point}，先按课堂例题画出状态变化，再提交订正版。"


def _mistake(
    *,
    id_: str,
    student: DemoStudent,
    subject: str,
    question_id: str,
    question_type: str,
    question_title: str,
    student_answer: str,
    correct_answer: str,
    error_reason: str,
    tags: list[str],
    last_wrong_at: str,
    source: dict[str, Any],
    wrong_count: int,
    mastered: bool,
) -> dict[str, Any]:
    return {
        "id": id_,
        "studentId": student.username,
        "studentName": student.real_name,
        "className": student.class_name,
        "examId": source.get("examId") or source.get("homeworkId") or "",
        "examTitle": source.get("examTitle") or source.get("homeworkTitle") or "作业错题订正",
        "subject": subject,
        "questionId": question_id,
        "questionType": question_type,
        "questionTitle": question_title,
        "studentAnswer": student_answer,
        "correctAnswer": correct_answer,
        "errorReason": error_reason,
        "knowledgeTags": tags,
        "wrongCount": wrong_count,
        "lastWrongAt": last_wrong_at,
        "mastered": mastered,
        "aiAnalysis": {
            "diagnosis": f"这道题暴露出「{tags[0]}」还没有形成稳定判断条件。",
            "concept": f"先回到 {tags[0]} 的定义，再看题目要求的是结构、过程还是边界。",
            "practice": "完成 2 道同类题，并在错题本写出“为什么不能用原来的方法”。",
            "path": ["复盘原题", "重建概念", "同类迁移", "隔天再测"],
        } if wrong_count >= 2 else None,
        "source": source,
        "updatedAt": last_wrong_at,
    }


def _build_exam_data(students: list[DemoStudent], now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    exams = [
        {
            "id": "demo-exam-code-practical",
            "title": "计算机程序设计上机考试",
            "subject": "计算机程序设计",
            "status": "active",
            "startsAt": _ts(now, 0, 9, 30),
            "durationMinutes": 120,
            "location": "编程考试入口",
            "rules": ["仅允许使用内置 IDE", "可运行公开样例", "隐藏用例由后端判题"],
            "programming": True,
            "questionTypes": [{"type": "programming", "label": "编程题", "count": 3, "score": 100}],
            "programmingProblems": _programming_problems(),
            "objectiveQuestions": [],
        },
        {
            "id": "demo-exam-db-closed",
            "title": "数据库系统原理闭卷测验",
            "subject": "数据库系统原理",
            "status": "completed",
            "startsAt": _ts(now, 4, 10, 0),
            "durationMinutes": 80,
            "location": "线上考试中心",
            "rules": ["闭卷答题", "提交后显示客观题得分"],
            "questionTypes": [{"type": "choice", "label": "选择题", "count": 25, "score": 50}, {"type": "blank", "label": "填空题", "count": 10, "score": 30}, {"type": "text", "label": "简答题", "count": 2, "score": 20}],
            "programmingProblems": [],
            "objectiveQuestions": [
                {"id": "db-q1", "type": "choice", "title": "B+ 树叶子节点主要保存什么？", "options": ["路由键", "记录指针", "事务日志", "锁表"], "score": 4},
                {"id": "db-q2", "type": "blank", "title": "事务的持久性通常依赖 ______ 日志。", "score": 4},
            ],
        },
        {
            "id": "demo-exam-ds-midterm",
            "title": "数据结构期中综合考试",
            "subject": "数据结构与算法",
            "status": "completed",
            "startsAt": _ts(now, 8, 14, 0),
            "durationMinutes": 90,
            "location": "线上考试中心",
            "rules": ["开考前 15 分钟进入候考", "系统自动保存答案"],
            "questionTypes": [{"type": "choice", "label": "选择题", "count": 20, "score": 40}, {"type": "programming", "label": "编程题", "count": 2, "score": 60}],
            "programmingProblems": [_programming_problems()[0]],
            "objectiveQuestions": [{"id": "ds-q1", "type": "choice", "title": "递归调用现场由哪种结构保存？", "options": ["队列", "栈", "堆", "图"], "score": 4}],
        },
        {
            "id": "demo-exam-ai-stage",
            "title": "人工智能技术阶段测评",
            "subject": "人工智能技术基础",
            "status": "scheduled",
            "startsAt": _ts(now, -1, 15, 0),
            "durationMinutes": 60,
            "location": "线上考试中心",
            "rules": ["单选、填空与推导题混合", "考试期间自动保存"],
            "questionTypes": [{"type": "choice", "label": "选择题", "count": 18, "score": 54}, {"type": "text", "label": "推导题", "count": 2, "score": 46}],
            "programmingProblems": [],
            "objectiveQuestions": [{"id": "ai-q1", "type": "choice", "title": "Scaled Attention 缩放因子用于缓解什么问题？", "options": ["Softmax 饱和", "过拟合", "位置偏移", "梯度爆炸"], "score": 4}],
        },
    ]
    attempts: list[dict[str, Any]] = []
    mistakes: list[dict[str, Any]] = []
    for exam_index, exam in enumerate(exams[:3]):
        for student_index, student in enumerate(students):
            score = _score_for(student_index + exam_index, 70 + exam_index * 3)
            submitted = exam["status"] != "active" or student_index % 3 == 0
            started_at = _ts(now, max(0, 4 + exam_index * 3), 9 + (student_index % 6), (student_index * 5) % 45)
            submitted_at = _ts(now, max(0, 4 + exam_index * 3), 10 + (student_index % 6), (student_index * 7) % 50) if submitted else ""
            attempt_id = f"{exam['id']}:{student.username}"
            attempts.append(
                {
                    "id": attempt_id,
                    "attemptId": attempt_id,
                    "examId": exam["id"],
                    "examTitle": exam["title"],
                    "studentId": student.username,
                    "studentName": student.real_name,
                    "status": "submitted" if submitted else "started",
                    "answers": _exam_answers(exam, score),
                    "progress": 100 if submitted else 35 + student_index % 55,
                    "startedAt": started_at,
                    "lastSavedAt": submitted_at or started_at,
                    "submittedAt": submitted_at,
                    "objectiveScore": min(60, max(20, score - 28)),
                    "score": score if submitted else None,
                    "abnormal": student_index % 17 == 0 and exam["status"] == "active",
                }
            )
            if score < 80 or student_index % 5 == 0:
                mistakes.append(
                    _exam_mistake(exam, student, student_index, score, submitted_at or started_at)
                )
    review_tasks = [
        {
            "id": "demo-review-hash-map",
            "taskId": "demo-review-hash-map",
            "questionId": "prog-two-sum",
            "title": "哈希表建模专项订正",
            "status": "created",
            "createdAt": _ts(now, 2, 11, 20),
            "targetClass": "计科 2301",
            "createdBy": "teacher_chen",
        },
        {
            "id": "demo-review-bplus-index",
            "taskId": "demo-review-bplus-index",
            "questionId": "db-q1",
            "title": "B+ 树叶子节点职责复盘",
            "status": "created",
            "createdAt": _ts(now, 1, 15, 10),
            "targetClass": "计科 2302",
            "createdBy": "teacher_li",
        },
    ]
    return exams, attempts, mistakes, review_tasks


def _programming_problems() -> list[dict[str, Any]]:
    return [
        {
            "id": "prog-two-sum",
            "title": "两数之和",
            "language": "javascript",
            "timeLimitMs": 1000,
            "memoryLimitMb": 128,
            "score": 35,
            "description": "给定整数数组 nums 和目标值 target，返回两个和为 target 的下标。",
            "inputHint": "nums: number[], target: number",
            "outputHint": "number[]",
            "funcName": "twoSum",
            "starterCode": "function twoSum(nums, target) {\n  return [];\n}",
            "publicCases": [{"label": "样例 1", "input": [[2, 7, 11, 15], 9], "expected": [0, 1]}],
        },
        {
            "id": "prog-valid-brackets",
            "title": "括号有效性",
            "language": "javascript",
            "timeLimitMs": 1000,
            "memoryLimitMb": 128,
            "score": 30,
            "description": "判断只包含 ()[]{} 的字符串是否有效闭合。",
            "inputHint": "s: string",
            "outputHint": "boolean",
            "funcName": "isValid",
            "starterCode": "function isValid(s) {\n  return false;\n}",
            "publicCases": [{"label": "样例 1", "input": ["()[]{}"], "expected": True}],
        },
        {
            "id": "prog-lru-cache",
            "title": "LRU 缓存",
            "language": "javascript",
            "timeLimitMs": 1500,
            "memoryLimitMb": 256,
            "score": 35,
            "description": "实现 get/put 均为 O(1) 的 LRUCache。",
            "inputHint": "capacity, operations",
            "outputHint": "operation results",
            "funcName": "LRUCache",
            "starterCode": "class LRUCache {\n  constructor(capacity) {}\n  get(key) {}\n  put(key, value) {}\n}",
            "publicCases": [{"label": "样例", "input": [2, ["put", "put", "get"]], "expected": [None, None, 1]}],
        },
    ]


def _exam_answers(exam: dict[str, Any], score: int) -> dict[str, str]:
    answers = {}
    for question in exam.get("objectiveQuestions") or []:
        answers[question["id"]] = "记录指针" if score >= 70 else "根节点"
    for problem in exam.get("programmingProblems") or []:
        answers[problem["id"]] = "const map = new Map(); for (let i=0;i<nums.length;i++){ const need=target-nums[i]; if(map.has(need)) return [map.get(need), i]; map.set(nums[i], i); }"
    return answers


def _exam_mistake(exam: dict[str, Any], student: DemoStudent, student_index: int, score: int, last_wrong_at: str) -> dict[str, Any]:
    if exam["subject"].startswith("计算机程序"):
        question_id = "prog-two-sum"
        title = "两数之和"
        answer = "双层循环未提前返回，重复数字时下标覆盖。"
        correct = "使用哈希表保存已访问数字，O(n) 查询补数。"
        tags = ["哈希表建模", "数组", "复杂度"]
    elif exam["subject"].startswith("数据库"):
        question_id = "db-q1"
        title = "B+ 树叶子节点记录指针位置"
        answer = "内部节点"
        correct = "叶子节点"
        tags = ["B+ 树索引", "数据库存储", "索引结构"]
    else:
        question_id = "ds-q1"
        title = "递归调用现场保存结构"
        answer = "队列"
        correct = "栈"
        tags = ["栈", "递归", "函数调用"]
    return _mistake(
        id_=f"demo-mistake-exam-{exam['id']}-{student.username}",
        student=student,
        subject=exam["subject"],
        question_id=question_id,
        question_type="编程题" if question_id.startswith("prog") else "选择题",
        question_title=title,
        student_answer=answer,
        correct_answer=correct,
        error_reason=f"考试中对 {tags[0]} 的识别不够快，先用了熟悉但不匹配的做法。",
        tags=tags + ["考试错题"],
        last_wrong_at=last_wrong_at,
        source={"type": "exam", "examId": exam["id"], "examTitle": exam["title"], "attemptId": f"{exam['id']}:{student.username}"},
        wrong_count=1 + (student_index % 4),
        mastered=score >= 74,
    )


def _build_forum_data(students: list[DemoStudent], teachers: list[DemoTeacher], now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    topics = [
        ("demo-post-bplus-leaf", "B+ 树叶子节点到底存数据还是指针？", "今天复盘数据库测验，发现我一直把 B 树和 B+ 树混着记。我的理解是内部节点只负责路由，叶子节点串成链表，真正的记录指针都在叶子上。这样范围查询才顺。这个说法对吗？", "qna", ["数据库", "B+树", "索引"]),
        ("demo-post-two-sum-map", "两数之和用 Map 的时候重复数字怎么处理比较稳？", "我之前写成先 map.set 再判断 need，碰到 [3,3] target=6 会把自己匹配上。后来改成先判断再 set，样例才过。这个顺序是不是可以当成哈希题模板？", "qna", ["哈希表", "编程题"]),
        ("demo-post-pr-review", "PR 被队长打回：接口测试只测了成功路径", "仓库主页接口我只测了 200，队长要求补 403 和空 README 的情况。感觉 PR 审核比写代码还细，但确实能提前发现问题。你们一般怎么写 review checklist？", "experience", ["PR", "单元测试", "软件工程"]),
        ("demo-post-reactive-receiver", "Reflect.get 的 receiver 用一个例子终于看懂了", "如果对象上有 getter，getter 里面访问 this.xxx，直接 target[key] 会让 this 指到原对象。换成 Reflect.get(target,key,receiver) 后，继承代理对象时依赖才能收集到正确对象。这个点之前一直以为只是语法规范。", "experience", ["Vue3", "Proxy", "前端"]),
        ("demo-post-attention-dim", "Attention 维度推导有没有更直观的记法？", "Q 是 [B, H, L, D]，K 转置后是 [B, H, D, L]，所以 QK^T 是 [B, H, L, L]。我现在用“每个 token 看所有 token”来记最后两个 L。", "qna", ["AI", "Transformer"]),
        ("demo-post-cache-index", "Cache 地址拆分题总在 index 位数上出错", "如果块大小 64B，组数 128，我理解 offset 是 6 位，index 是 7 位，剩下是 tag。老师说先算块内偏移，再算有多少组，这个顺序挺关键。", "qna", ["计组", "Cache"]),
        ("demo-post-team-git", "团队实训里分支命名最好一开始统一", "我们组一开始 feature/login、auth-dev、lm-login 混着来，后来 PR 列表很乱。现在统一 feature/{模块}-{姓名拼音}，看事件日志清楚很多。", "experience", ["团队协作", "Git"]),
        ("demo-post-sql-window", "窗口函数 Top-N 查询终于不用自连接了", "ROW_NUMBER() OVER(PARTITION BY course_id ORDER BY score DESC) 这个写法太适合成绩排名题了。自连接也能做，但可读性差很多。", "experience", ["SQL", "窗口函数"]),
        ("demo-post-lru-cache", "LRU 题用 Map + 双向链表还是直接 Map？", "JS 的 Map 有插入顺序，面试题可以利用 delete 再 set 维护热度。但如果要解释底层，还是应该说哈希表 + 双向链表，get/put 都 O(1)。", "qna", ["LRU", "数据结构"]),
        ("demo-post-rag-course", "课程 RAG 助教引用来源怎么避免答非所问？", "我发现检索前先把问题改写成“课程名 + 知识点 + 题型”会稳定很多，比如“数据库系统原理 B+树 选择题 错因”。大家有没有更好的 query 模板？", "competition", ["RAG", "课程项目"]),
        ("demo-post-api-contract", "后端接口字段命名统一真的能省很多事", "这周前端对接作业接口时，status 一会儿 pending 一会儿 review，组件判断写得很乱。后来我们把状态枚举写到 README，问题少了很多。", "experience", ["API", "前后端"]),
        ("demo-post-judge-hidden", "隐藏用例一般会卡哪些边界？", "两数之和我被重复数字、负数、无序数组都卡过。现在写完公开样例后，会自己再补一个重复值和一个大数组。", "qna", ["OJ", "边界测试"]),
    ]
    posts: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    for index, (post_id, title, content, category, tags) in enumerate(topics):
        author = students[index % len(students)]
        created = _ts(now, 13 - index, 9 + (index % 8), 10 + (index * 3) % 45)
        replies = [
            {
                "id": f"{post_id}-reply-1",
                "author": students[(index + 2) % len(students)].real_name,
                "avatar": f"/static/avatars/{students[(index + 2) % len(students)].avatar_path}",
                "isAi": False,
                "content": _student_reply_for(tags[0]),
                "createdAt": _ts(now, 12 - index if index < 12 else 1, 10 + (index % 6), 20),
                "likes": 2 + index % 5,
            },
            {
                "id": f"{post_id}-reply-2",
                "author": "Prof. X (AI导师)",
                "avatar": "",
                "isAi": True,
                "content": _ai_reply_for(tags[0]),
                "createdAt": _ts(now, 12 - index if index < 12 else 1, 11 + (index % 5), 5),
                "likes": 1 + index % 4,
            },
        ]
        posts.append(
            {
                "id": post_id,
                "title": title,
                "content": content,
                "author": author.real_name,
                "avatar": f"/static/avatars/{author.avatar_path}",
                "category": category,
                "categoryLabel": {"qna": "课程答疑", "experience": "经验分享", "competition": "竞赛交流"}.get(category, "课程答疑"),
                "tags": tags,
                "likes": 8 + index * 2,
                "isLiked": False,
                "views": 40 + index * 17,
                "createdAt": created,
                "replies": replies,
                "isPinned": index in {0, 2},
            }
        )
        logs.append(
            {
                "id": f"demo-ai-log-{index + 1}",
                "postId": post_id,
                "postTitle": title,
                "replyId": f"{post_id}-reply-2",
                "agentName": "Prof. X (AI导师)",
                "content": replies[1]["content"],
                "time": replies[1]["createdAt"],
                "status": "approved" if index % 3 else "pending_audit",
            }
        )
    announcements = [
        {"id": "demo-ann-exam-window", "title": "本周四 15:00 人工智能阶段测评，请提前完成设备检测", "content": "考试入口将在开考前 15 分钟开放。", "date": _ts(now, 1, 10, 0)},
        {"id": "demo-ann-pr-rule", "title": "团队实训 PR 审核要求：必须包含 README 更新和至少一条测试记录", "content": "队长初审后再提交教师合并。", "date": _ts(now, 2, 14, 30)},
    ]
    hot_topics = [
        {"id": "哈希表建模", "tag": "哈希表建模", "count": 36},
        {"id": "B+树索引", "tag": "B+树索引", "count": 31},
        {"id": "PR审核", "tag": "PR审核", "count": 27},
        {"id": "Proxy", "tag": "Proxy", "count": 22},
        {"id": "团队协作", "tag": "团队协作", "count": 19},
    ]
    return posts, announcements, hot_topics, logs


def _student_reply_for(topic: str) -> str:
    replies = {
        "数据库": "我也是这样记的：内部节点像目录，叶子节点才是能顺着链表扫的内容区。范围查询的时候这个区别最明显。",
        "哈希表": "先查再写这个顺序确实稳，尤其是重复数字。可以顺手把 key 和 index 的含义写在注释里，review 时很好看。",
        "PR": "我们组 checklist 里固定有权限、空数据、异常码、回归截图四项，少一项就不合并。",
        "Vue3": "receiver 那个例子最好自己敲一遍，有 getter 继承时一下就能看出差别。",
    }
    return replies.get(topic, "这个问题课堂上讲过但实践里容易忘，我一般会把错因写到 README 的 troubleshooting 里。")


def _ai_reply_for(topic: str) -> str:
    return f"建议把「{topic}」拆成概念、触发条件、反例三个部分复盘。先写最小例子验证，再把结论沉淀到项目 README 或错题本，后续 PR 审核时会更容易发现同类问题。"


def _build_code_repository_data(students: list[DemoStudent], teachers: list[DemoTeacher], now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    specs = [
        ("demo-repo-graph-visual-lab", "图算法可视化实验室", "Vue", "数据结构与算法", ["图算法", "可视化", "课程项目"], "把 BFS、DFS、Dijkstra 的遍历过程做成可交互动画，支持导入邻接表。"),
        ("demo-repo-course-rag-assistant", "课程 RAG 助教插件", "TypeScript", "人工智能技术基础", ["RAG", "引用来源", "知识库"], "面向课程 PDF 的轻量检索问答插件，强调引用来源和检索解释。"),
        ("demo-repo-db-index-playground", "数据库索引实验场", "Python", "数据库系统原理", ["B+树", "索引", "Explain"], "模拟不同索引选择下的查询计划、回表次数和范围扫描过程。"),
        ("demo-repo-vue-reactive-runtime", "Mini Vue Reactive Runtime", "TypeScript", "高级前端程序设计", ["Vue3", "Proxy", "响应式"], "从 track/trigger 到 effect 调度器的最小响应式运行时。"),
        ("demo-repo-compiler-lexer-lab", "Mini Compiler Lexer Lab", "Python", "编译原理", ["词法分析", "递归下降", "AST"], "课程实验用迷你编译器，覆盖词法、语法和简单中间表示。"),
        ("demo-repo-campus-market-api", "校园二手市场 Spring API", "Java", "软件工程综合实训", ["Spring", "REST", "权限"], "以课程项目方式实现商品发布、订单、消息和教师审核后台。"),
        ("demo-repo-homework-grader", "作业智能批改分析器", "Python", "人工智能技术基础", ["作业分析", "错题", "NLP"], "聚合作业提交和错题标签，生成班级薄弱点和个体订正建议。"),
        ("demo-repo-network-packet-lab", "网络协议抓包实验台", "Python", "计算机网络", ["TCP", "抓包", "协议分析"], "解析 pcap 样例并可视化 TCP 三次握手、重传和窗口变化。"),
        ("demo-repo-distributed-cache", "分布式缓存一致性实验", "Java", "分布式系统", ["缓存", "一致性", "Redis"], "比较旁路缓存、写穿透和延迟双删在课程场景下的差异。"),
        ("demo-repo-cpp-stl-notes", "C++ STL 源码阅读笔记", "C++", "程序设计基础", ["STL", "迭代器", "容器"], "按 vector、map、unordered_map 整理源码阅读和复杂度实验。"),
        ("demo-repo-judge-service", "课程 OJ 判题服务", "Python", "计算机程序设计", ["OJ", "沙箱", "测试用例"], "封装编程题公开样例、隐藏用例和提交记录分析。"),
        ("demo-repo-transaction-lab", "事务隔离级别实验脚本", "Python", "数据库系统原理", ["事务", "隔离级别", "MySQL"], "用两个连接复现脏读、不可重复读和幻读。"),
        ("demo-repo-webgl-sorting", "WebGL 排序过程仪表盘", "TypeScript", "数据结构与算法", ["排序", "WebGL", "性能"], "用 Canvas/WebGL 展示排序算法比较次数和交换次数。"),
        ("demo-repo-query-planner-notes", "MySQL Query Planner Notes", "Python", "数据库系统原理", ["Explain", "优化器", "索引"], "收集课程 SQL 的 EXPLAIN 结果并生成可读报告。"),
        ("demo-repo-ai-code-review", "AI Code Review Bot", "Python", "软件工程综合实训", ["代码审查", "LLM", "PR"], "根据 diff、测试结果和课程规范生成 PR 审核建议。"),
        ("demo-repo-schedule-optimizer", "课程排课约束求解器", "Java", "算法设计", ["回溯", "约束求解", "排课"], "用回溯和剪枝解决教室、教师、班级冲突。"),
        ("demo-repo-co-cache-sim", "Cache 映射策略模拟器", "C++", "计算机组成原理", ["Cache", "组相联", "命中率"], "输入访存序列，输出直接映射和组相联命中率对比。"),
        ("demo-repo-secure-login", "短信登录与权限演示", "TypeScript", "Web 安全基础", ["认证", "短信", "RBAC"], "演示学生/教师角色登录、Token 校验和页面权限保护。"),
        ("demo-repo-forum-semantic-search", "课程论坛语义搜索", "Python", "人工智能技术基础", ["论坛", "向量检索", "问答"], "对论坛历史讨论做向量检索，帮助学生找已有解法。"),
        ("demo-repo-lru-cache-visual", "LRU Cache 可视化练习", "Vue", "数据结构与算法", ["LRU", "链表", "哈希表"], "用动画解释哈希表 + 双向链表如何保持 O(1)。"),
    ]
    repos: list[dict[str, Any]] = []
    stars: list[dict[str, Any]] = []
    favorites: list[dict[str, Any]] = []
    for index, (repo_id, title, language, course, tags, description) in enumerate(specs):
        author = students[index % len(students)]
        collaborators = [students[(index + 3) % len(students)].username, students[(index + 5) % len(students)].username]
        created = _ts(now, 13 - (index % 12), 9 + (index % 7), 12)
        updated = _ts(now, max(0, 4 - (index % 5)), 10 + (index % 6), 22)
        repos.append(
            {
                "id": repo_id,
                "title": title,
                "slug": repo_id.replace("demo-repo-", ""),
                "description": description,
                "author": author.username,
                "authorName": author.real_name,
                "avatar": f"/static/avatars/{author.avatar_path}",
                "language": language,
                "course": course,
                "tags": tags,
                "collaborators": collaborators,
                "visibility": "public" if index % 6 else "private",
                "status": "active",
                "recommendScore": 70 + (index * 7) % 29,
                "giteaOwner": "campus",
                "giteaRepo": repo_id.replace("demo-repo-", ""),
                "htmlUrl": f"https://gezhisystem.com/gitea/campus/{repo_id.replace('demo-repo-', '')}",
                "cloneUrl": f"https://gezhisystem.com/gitea/campus/{repo_id.replace('demo-repo-', '')}.git",
                "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/{repo_id.replace('demo-repo-', '')}.git",
                "defaultBranch": "main",
                "archiveUrl": f"https://gezhisystem.com/gitea/campus/{repo_id.replace('demo-repo-', '')}/archive/main.zip",
                "readme": _repo_readme(title, description, language, course, tags),
                "classDiagram": _repo_class_diagram(title),
                "fileTree": _repo_file_tree(language),
                "createdAt": created,
                "updatedAt": updated,
            }
        )
        for offset in range(1, 1 + (index % 5) + 2):
            user = students[(index + offset) % len(students)].username
            key = f"{repo_id}:{user}"
            stars.append({"id": key, "projectId": repo_id, "userId": user, "active": True, "status": "active", "updatedAt": _ts(now, offset, 10 + offset, 0)})
        for offset in range(2, 2 + (index % 3) + 1):
            user = students[(index + offset * 2) % len(students)].username
            key = f"{repo_id}:{user}"
            favorites.append({"id": key, "projectId": repo_id, "userId": user, "active": True, "status": "active", "updatedAt": _ts(now, offset + 1, 11 + offset, 15)})
    reports = [
        {
            "id": "demo-repo-report-readme-citation",
            "projectId": "demo-repo-query-planner-notes",
            "projectTitle": "MySQL Query Planner Notes",
            "projectAuthor": students[13 % len(students)].username,
            "reporter": students[2 % len(students)].username,
            "reason": "引用来源待核实",
            "description": "README 的两张 EXPLAIN 截图缺少课程实验来源说明，建议教师审核后要求补引用。",
            "status": "pending",
            "createdAt": _ts(now, 2, 16, 5),
            "auditedAt": "",
            "auditor": "",
            "note": "",
        }
    ]
    return repos, stars, favorites, reports


def _repo_readme(title: str, description: str, language: str, course: str, tags: list[str]) -> str:
    return f"""# {title}

{description}

## 项目背景

本仓库来自《{course}》课程项目，目标不是做一个炫技 demo，而是把课堂概念变成可以复现实验、可以互相 review 的代码资产。

## 主要模块

- `src/core`：核心算法或业务逻辑，保留必要的边界注释。
- `src/adapters`：课程数据、测试样例和页面交互的适配层。
- `tests`：公开样例、异常路径和至少一个回归用例。
- `docs`：实验记录、错题复盘和课堂汇报材料。

## 技术栈

- 主语言：{language}
- 关联课程：{course}
- 标签：{", ".join(tags)}

## 类图

```mermaid
classDiagram
    class DemoController {{
      +loadCase()
      +run()
    }}
    class CourseService {{
      +validateInput()
      +buildResult()
    }}
    class Repository {{
      +readFixture()
      +saveSnapshot()
    }}
    DemoController --> CourseService
    CourseService --> Repository
```

## 运行记录

最近一次小组 review 主要关注输入边界、README 是否能独立复现实验，以及测试结果能否解释课程知识点。后续计划补充失败样例截图和一次课堂展示脚本。
"""


def _repo_class_diagram(title: str) -> str:
    return f"classDiagram\n    class {re.sub(r'[^A-Za-z0-9]', '', title) or 'CourseProject'}Controller\n    class CourseService\n    class Repository\n    Controller --> CourseService\n    CourseService --> Repository"


def _repo_file_tree(language: str) -> list[dict[str, Any]]:
    source = "src" if language in {"TypeScript", "Vue", "Java", "C++"} else "app"
    return [
        {"name": source, "type": "dir", "lastCommit": "feat: 整理课程核心模块"},
        {"name": "tests", "type": "dir", "lastCommit": "test: 补充边界样例"},
        {"name": "docs", "type": "dir", "lastCommit": "docs: 更新实验记录"},
        {"name": "README.md", "type": "file", "lastCommit": "docs: 完善项目说明和类图"},
    ]


def _build_team_projects(students: list[DemoStudent], teachers: list[DemoTeacher], now: datetime) -> list[dict[str, Any]]:
    teams = [
        {
            "id": "demo-team-campus-oj",
            "title": "课程 OJ 判题与错题回流平台",
            "course": "软件工程综合实训",
            "teamName": "栈帧工作室",
            "description": "面向程序设计课的判题、提交记录分析和错题本回流系统，支持公开样例、隐藏用例和教师端复盘。",
            "members": students[:4],
            "status": "PR 待审核",
            "repoStatus": "collaborating",
            "progress": [88, 74, 63, 42],
            "contribution": [34, 28, 23, 15],
        },
        {
            "id": "demo-team-rag-forum",
            "title": "课程论坛语义检索与 RAG 助教",
            "course": "人工智能技术基础",
            "teamName": "向量小队",
            "description": "把论坛高质量问答、课程 PDF 和错题分析接入轻量检索，帮助学生在提问前找到已有解法。",
            "members": students[4:9] if len(students) >= 9 else students[-3:],
            "status": "待修改",
            "repoStatus": "waiting_upload",
            "progress": [91, 67, 55, 36, 18],
            "contribution": [31, 24, 20, 15, 10],
        },
    ]
    projects: list[dict[str, Any]] = []
    for team_index, spec in enumerate(teams):
        members = spec["members"]
        leader = members[0]
        repo_name = spec["id"].replace("demo-team-", "")
        html_url = f"https://gezhisystem.com/gitea/campus/{repo_name}"
        member_progress = []
        for index, student in enumerate(members):
            progress = spec["progress"][index]
            merged = progress >= 88
            open_pr = 65 <= progress < 88
            pushed = progress >= 55
            member_progress.append(
                {
                    "id": student.username,
                    "name": student.real_name,
                    "role": "队长" if index == 0 else "学生",
                    "task": _team_task(spec["title"], index),
                    "branch": f"feature/{_slug(student.real_name)}-{index + 1}",
                    "cloneStatus": "done" if progress >= 35 else "pending",
                    "commitCount": 2 + index + team_index,
                    "pushStatus": "detected" if pushed else "pending",
                    "prStatus": "merged" if merged else ("open" if open_pr else ("needs_pr" if pushed else "not_created")),
                    "mergeStatus": "merged" if merged else "pending",
                    "statusLabel": "已合并" if merged else ("PR 待审核" if open_pr else ("PR 待创建" if pushed else "未开始")),
                    "lastCommitAt": _ts(now, max(0, 5 - index), 10 + index, 15 + index * 4),
                    "score": 92 - index * 5 if progress >= 60 else 0,
                    "contribution": spec["contribution"][index],
                    "progress": progress,
                    "teacherComment": _member_teacher_comment(progress),
                }
            )
        commits = _team_commits(members, now, team_index)
        prs = _team_pull_requests(members, html_url, now, team_index)
        events = _team_events(members, now, team_index)
        project = {
            "id": spec["id"],
            "status": "active",
            "project": {
                "id": spec["id"],
                "title": spec["title"],
                "course": spec["course"],
                "teamName": spec["teamName"],
                "description": spec["description"],
                "leaderId": leader.real_name,
                "createdBy": leader.username,
                "teacherId": teachers[team_index % len(teachers)].username,
                "className": leader.class_name,
                "status": "active",
                "createdAt": _ts(now, 13, 9 + team_index, 0),
            },
            "repository": {
                "repoName": repo_name,
                "giteaOwner": "campus",
                "htmlUrl": html_url,
                "cloneUrl": f"{html_url}.git",
                "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/{repo_name}.git",
                "defaultBranch": "main",
                "taskBranch": "feature/team-start",
                "status": spec["repoStatus"],
                "statusLabel": spec["status"],
                "webhookConfigured": True,
                "lastSyncedAt": _ts(now, 0, 10 + team_index, 20),
            },
            "memberProgress": member_progress,
            "pullRequests": prs,
            "recentCommits": commits,
            "gitEvents": events,
            "chatMessages": _team_chat(members, now, team_index),
            "reminders": [],
            "teacherEvaluation": {
                "summary": "团队协作过程有持续提交记录，贡献度差异合理。下一阶段重点检查测试覆盖和 README 可复现性。",
                "auditor": teachers[team_index % len(teachers)].username,
                "updatedAt": _ts(now, 1, 16, 20),
            },
            "repositoryHome": _team_repository_home(spec, repo_name, html_url, members, member_progress, now, team_index),
            "updatedAt": _ts(now, 0, 11 + team_index, 30),
            "ownerId": leader.username,
        }
        projects.append(project)
    return projects


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.encode("utf-8").hex()[:8].lower()).strip("-") or "member"


def _team_task(title: str, index: int) -> str:
    tasks = [
        f"{title} 的接口契约与项目 README",
        "后端服务、数据模型和 API 联调",
        "前端页面状态、异常提示和交互闭环",
        "测试用例、CI 记录和演示脚本",
        "论坛/RAG 数据整理与检索评估",
    ]
    return tasks[index % len(tasks)]


def _member_teacher_comment(progress: int) -> str:
    if progress >= 85:
        return "任务推进稳定，commit 粒度清楚，可以承担最终合并前检查。"
    if progress >= 60:
        return "功能主线已经跑通，但测试和异常路径还需要补。"
    if progress >= 35:
        return "已有提交记录，建议尽快整理 PR 描述和自测截图。"
    return "需要队长跟进任务拆分，先完成最小可运行版本。"


def _team_commits(members: list[DemoStudent], now: datetime, team_index: int) -> list[dict[str, Any]]:
    messages = [
        "docs: 补充项目 README 和接口契约",
        "feat: 完成提交记录聚合接口",
        "test: 增加作业错题回流用例",
        "fix: 修复空 README 时仓库主页渲染",
        "feat: 接入教师评语和修改建议",
        "refactor: 拆分仓库服务的数据适配层",
    ]
    commits = []
    for index, message in enumerate(messages):
        author = members[index % len(members)]
        commits.append({"id": f"demo-c-{team_index}-{index}", "author": author.real_name, "branch": f"feature/{index + 1}", "message": message, "time": _ts(now, max(0, 6 - index), 9 + index, 18)})
    return commits


def _team_pull_requests(members: list[DemoStudent], html_url: str, now: datetime, team_index: int) -> list[dict[str, Any]]:
    first = members[0]
    second = members[1 if len(members) > 1 else 0]
    third = members[2 if len(members) > 2 else 0]
    return [
        {
            "id": "pr-3",
            "number": 3,
            "title": "feat: 接入教师评语与修改建议展示",
            "creator": first.real_name,
            "sourceBranch": "feature/repository-feedback",
            "targetBranch": "main",
            "status": "open",
            "statusLabel": "PR 待审核",
            "leaderReviewStatus": "recommended",
            "leaderReviewer": first.real_name,
            "teacherReviewStatus": "pending",
            "reviewComment": "自测通过，建议老师重点看空评语时的兜底文案。",
            "createdAt": _ts(now, 1, 14, 20),
            "updatedAt": _ts(now, 1, 16, 5),
            "url": f"{html_url}/pulls/3",
        },
        {
            "id": "pr-2",
            "number": 2,
            "title": "fix: 修复提交时间线排序和状态标签",
            "creator": second.real_name,
            "sourceBranch": "feature/timeline-status",
            "targetBranch": "main",
            "status": "merged",
            "statusLabel": "已合并",
            "leaderReviewStatus": "recommended",
            "teacherReviewStatus": "approved",
            "teacherReviewer": "teacher_chen",
            "reviewComment": "合并后教师端和学生端列表一致。",
            "createdAt": _ts(now, 4, 10, 40),
            "updatedAt": _ts(now, 3, 15, 25),
            "url": f"{html_url}/pulls/2",
        },
        {
            "id": "pr-1",
            "number": 1,
            "title": "docs: 初始化项目结构与类图说明",
            "creator": third.real_name,
            "sourceBranch": "feature/project-docs",
            "targetBranch": "main",
            "status": "changes_requested",
            "statusLabel": "待修改",
            "leaderReviewStatus": "changes_requested",
            "reviewComment": "类图需要补 Service 到 Repository 的依赖方向。",
            "createdAt": _ts(now, 7 + team_index, 11, 15),
            "updatedAt": _ts(now, 6 + team_index, 17, 0),
            "url": f"{html_url}/pulls/1",
        },
    ]


def _team_events(members: list[DemoStudent], now: datetime, team_index: int) -> list[dict[str, Any]]:
    actors = [member.real_name for member in members]
    return [
        {"id": f"event-{team_index}-1", "type": "repository_created", "actor": actors[0], "text": f"{actors[0]} 创建了团队仓库并初始化 README", "time": _ts(now, 13, 9, 30)},
        {"id": f"event-{team_index}-2", "type": "push", "actor": actors[1 % len(actors)], "text": f"{actors[1 % len(actors)]} 推送 feature/timeline-status 分支", "time": _ts(now, 5, 10, 10)},
        {"id": f"event-{team_index}-3", "type": "pull_request", "actor": actors[1 % len(actors)], "text": f"{actors[1 % len(actors)]} 创建 Pull Request #2", "time": _ts(now, 4, 10, 40)},
        {"id": f"event-{team_index}-4", "type": "merge", "actor": "teacher_chen", "text": "teacher_chen 合并 PR #2 并要求补充 README 截图", "time": _ts(now, 3, 15, 25)},
        {"id": f"event-{team_index}-5", "type": "review", "actor": actors[0], "text": f"{actors[0]} 初审 PR #3，建议教师合并前检查空状态", "time": _ts(now, 1, 16, 5)},
        {"id": f"event-{team_index}-6", "type": "feedback", "actor": "teacher_chen", "text": "教师更新仓库主页评语和修改建议", "time": _ts(now, 1, 16, 20)},
    ]


def _team_chat(members: list[DemoStudent], now: datetime, team_index: int) -> list[dict[str, Any]]:
    return [
        {"id": 1, "sender": members[0].real_name, "content": "我把 README 的运行步骤补了，大家按这个重新拉一下依赖。", "time": _ts(now, 5, 10, 30)},
        {"id": 2, "sender": members[1 % len(members)].real_name, "content": "PR #2 的状态标签问题已经修，教师端列表能同步了。", "time": _ts(now, 4, 15, 10)},
        {"id": 3, "sender": members[-1].real_name, "content": "类图我今晚前补到 docs/class-diagram.md，先不合并 PR #1。", "time": _ts(now, 2, 17, 30)},
    ]


def _team_repository_home(spec: dict[str, Any], repo_name: str, html_url: str, members: list[DemoStudent], member_progress: list[dict[str, Any]], now: datetime, team_index: int) -> dict[str, Any]:
    files = [
        {"name": "backend", "type": "dir", "lastCommit": "feat: 完成后端核心接口", "updatedAt": _ts(now, 3, 15, 25)},
        {"name": "frontend", "type": "dir", "lastCommit": "feat: 接入仓库主页和 PR 状态", "updatedAt": _ts(now, 2, 11, 40)},
        {"name": "docs", "type": "dir", "lastCommit": "docs: 补充项目说明与类图", "updatedAt": _ts(now, 1, 16, 5)},
        {"name": "README.md", "type": "file", "lastCommit": "docs: 更新演示运行步骤", "updatedAt": _ts(now, 1, 16, 5)},
        {"name": "tests", "type": "dir", "lastCommit": "test: 增加接口回归用例", "updatedAt": _ts(now, 4, 10, 40)},
    ]
    return {
        "namespace": "campus",
        "repoName": repo_name,
        "visibility": "private",
        "course": spec["course"],
        "about": spec["description"],
        "readme": f"# {spec['title']}\n\n{spec['description']}\n\n## 当前进展\n\n- 队长负责接口契约和 README\n- 成员按功能分支提交 PR\n- 教师评语已同步到仓库主页\n\n## 本周风险\n\n测试覆盖和类图说明还需要继续补齐。",
        "classDiagram": "classDiagram\n    class WebController\n    class CollaborationService\n    class DomainRecordRepository\n    class TeacherReview\n    WebController --> CollaborationService\n    CollaborationService --> DomainRecordRepository\n    TeacherReview --> CollaborationService",
        "teacherComment": "项目推进节奏真实，有持续 commit 和 PR 审核记录。下一轮重点看异常路径测试和演示脚本是否能独立运行。",
        "revisionSuggestions": "1. README 补充一键启动命令和截图。\n2. 类图中标清 Controller、Service、Repository 的职责。\n3. PR 描述里增加自测结果，不只写实现内容。",
        "teacherFeedbackUpdatedAt": _ts(now, 1, 16, 20),
        "teacherFeedbackUpdatedBy": "teacher_chen",
        "cloneUrlMockOnly": True,
        "defaultBranch": "main",
        "cloneUrl": f"{html_url}.git",
        "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/{repo_name}.git",
        "updatedAt": _ts(now, 1, 16, 20),
        "languageStats": [
            {"name": "Python", "percent": 42 if team_index == 0 else 35, "color": "#3572A5"},
            {"name": "TypeScript", "percent": 34 if team_index == 0 else 40, "color": "#3178c6"},
            {"name": "Markdown", "percent": 14, "color": "#083fa1"},
            {"name": "SQL", "percent": 10 if team_index == 0 else 11, "color": "#e38c00"},
        ],
        "files": files,
        "memberContribution": [{"name": item["name"], "contribution": item["contribution"], "commitCount": item["commitCount"]} for item in member_progress],
    }


def _build_analytics_data(students: list[DemoStudent], mistakes: list[dict[str, Any]], now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    advices = [
        {
            "id": "demo-advice-hash-map",
            "title": "哈希表建模薄弱，需要发布 15 分钟随堂练习",
            "topic": "哈希表建模",
            "subject": "计算机程序设计",
            "target": {"scope": "class", "label": "计科 2301", "studentIds": [s.username for s in students[:8]]},
            "priority": "high",
            "active": True,
            "status": "active",
            "createdAt": _ts(now, 1, 10, 20),
        },
        {
            "id": "demo-advice-bplus",
            "title": "B+ 树索引结构需课堂复盘",
            "topic": "B+ 树索引",
            "subject": "数据库系统原理",
            "target": {"scope": "class", "label": "计科 2302", "studentIds": [s.username for s in students[1:9]]},
            "priority": "medium",
            "active": True,
            "status": "active",
            "createdAt": _ts(now, 2, 15, 0),
        },
    ]
    actions = [
        {"id": "demo-action-review-hash", "title": "创建哈希表补弱作业", "type": "homework", "status": "pending", "createdAt": _ts(now, 1, 10, 35), "targetAdviceId": "demo-advice-hash-map"},
        {"id": "demo-action-review-bplus", "title": "推送 B+ 树错题讲评", "type": "mistake_review", "status": "pending", "createdAt": _ts(now, 2, 15, 20), "targetAdviceId": "demo-advice-bplus"},
    ]
    interactions = [
        {
            "id": "demo-interaction-hash-map",
            "type": "homework",
            "title": "哈希表建模订正任务",
            "targetLabel": "计科 2301 8名学生",
            "completionRate": 62,
            "unreadCount": 1,
            "pendingCount": 3,
            "completedCount": 5,
            "createdAt": _ts(now, 1, 11, 0),
            "status": "running",
            "nextAction": "明天课前检查 3 名未完成学生的提交。",
            "payload": {"homeworkId": "demo-hw-ds-linked-stack"},
            "source": {"module": "teacher-analytics", "weakPointId": "demo-advice-hash-map"},
        },
        {
            "id": "demo-interaction-bplus-review",
            "type": "mistake_review",
            "title": "B+ 树索引错题复盘",
            "targetLabel": "计科 2302",
            "completionRate": 78,
            "unreadCount": 0,
            "pendingCount": 2,
            "completedCount": 7,
            "createdAt": _ts(now, 2, 15, 40),
            "status": "completed",
            "nextAction": "已完成，等待下一次测验验证迁移效果。",
            "payload": {"mistakeIds": [item["id"] for item in mistakes[:4]]},
            "source": {"module": "teacher-analytics", "weakPointId": "demo-advice-bplus"},
        },
    ]
    return advices, actions, interactions
