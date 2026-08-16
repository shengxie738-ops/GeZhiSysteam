"""
仪表盘聚合端点
为学生仪表盘提供一次性获取全量数据的接口，减少前端多次请求的开销。
包含：今日待提交作业、各科目截止时间、考试通知、易错点追踪、错题本复盘

教师端交互端点：
- 教师下发的干预任务（作业补弱、短测、错题订正、学情提醒）
- 教师端学情大屏所需的班级聚合数据
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import ok
from app.core.security import decode_access_token
from app.repositories.json_store import JsonStore, make_record_key
from app.utils.datetime import utc_now_iso

router = APIRouter()


def _require_auth_user(authorization: str | None) -> str:
    """Extract and validate user from JWT token. Returns username."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    payload = decode_access_token(authorization.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="invalid token")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid token payload")
    return username

CHINA_TZ = timezone(timedelta(hours=8))

# 科目颜色映射（与前端 mockSubjects 保持一致）
SUBJECT_COLORS: dict[str, str] = {
    "FE-401": "#6366f1",
    "DS-201": "#00e5ff",
    "AI-101": "#10b981",
    "DB-301": "#f59e0b",
    "CO-202": "#f97316",
    "SE-501": "#8b5cf6",
}

DEFAULT_COLOR = "#94a3b8"


class FreePayload(BaseModel):
    class Config:
        extra = "allow"


# ─── 工具函数 ─────────────────────────────────────────────────

def _now_china() -> datetime:
    return datetime.now(CHINA_TZ)


def _parse_deadline(deadline_str: str, now: datetime) -> dict[str, Any]:
    """
    解析截止时间字符串，返回剩余时间标签与是否紧急。
    支持格式：
    - ISO 8601: "2026-07-08T17:30:00"
    - 年月日时分: "2026/07/08 17:30:00"
    """
    if not deadline_str:
        return {"remaining": "", "urgent": False, "deadlineTs": None}

    try:
        # 尝试解析 ISO / 标准格式
        deadline_str_clean = deadline_str.replace("Z", "+00:00")
        if "/" in deadline_str_clean:
            dt = datetime.strptime(deadline_str_clean.split("+")[0], "%Y/%m/%d %H:%M:%S")
            dt = dt.replace(tzinfo=CHINA_TZ)
        else:
            dt = datetime.fromisoformat(deadline_str_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=CHINA_TZ)

        diff_seconds = (dt - now).total_seconds()
        diff_hours = diff_seconds / 3600

        if diff_seconds <= 0:
            return {"remaining": "已截止", "urgent": False, "deadlineTs": dt.isoformat()}
        elif diff_hours <= 2:
            return {"remaining": f"剩余 {int(diff_seconds / 60)} 分钟", "urgent": True, "deadlineTs": dt.isoformat()}
        elif diff_hours <= 24:
            return {"remaining": f"剩余 {int(diff_hours)} 小时", "urgent": True, "deadlineTs": dt.isoformat()}
        elif diff_hours <= 48:
            return {"remaining": "剩余 1 天", "urgent": False, "deadlineTs": dt.isoformat()}
        else:
            days = int(diff_hours / 24)
            return {"remaining": f"剩余 {days} 天", "urgent": False, "deadlineTs": dt.isoformat()}
    except Exception:
        # 兜底：返回原始字符串
        return {"remaining": "", "urgent": False, "deadlineTs": None}


def _format_exam_date(iso_str: str | None) -> str:
    """返回 ISO 格式日期时间，前端负责格式化显示"""
    return iso_str or ""


def _build_homework_dashboard(user_id: str, store: JsonStore, now: datetime) -> dict[str, Any]:
    """
    构建作业仪表盘数据：
    - homeworkList: 仪表盘作业卡片列表（格式适配后）
    - deadlines: 各科目截止时间聚合（未提交作业中最早截止的）
    - pendingCount / submittedCount
    """
    homeworks = store.list_payloads("homework", "homework")
    submissions = store.list_payloads("homework", "submission", owner_id=user_id)
    by_homework = {item.get("homeworkId") or item.get("id"): item for item in submissions}

    homework_list = []
    subject_deadline_map: dict[str, dict[str, Any]] = {}  # subjectId -> homework

    for hw in homeworks:
        hw_id = hw.get("id", "")
        submission = by_homework.get(hw_id)
        status = submission.get("status", "submitted") if submission else hw.get("status", "unsubmitted")
        submitted = status in ("submitted", "pending", "graded", "review")

        subject_id = hw.get("subjectId", "GENERAL")
        subject_name = hw.get("subjectName") or hw.get("subject") or "通用"
        deadline_str = hw.get("deadline", "")
        deadline_info = _parse_deadline(deadline_str, now)
        urgent = hw.get("urgent", False) or deadline_info["urgent"]

        # 仪表盘格式（与前端模板字段对齐）
        homework_list.append({
            "id": hw_id,
            "title": hw.get("title", "未命名作业"),
            "subject": subject_name,
            "subjectId": subject_id,
            "deadline": deadline_str,
            "urgent": urgent,
            "submitted": submitted,
            "status": status,
            "grade": submission.get("grade") if submission else None,
            "type": hw.get("type", "daily"),
        })

        # 聚合各科目最近未提交截止时间（用于 deadlines 面板）
        if not submitted and deadline_info["deadlineTs"]:
            existing = subject_deadline_map.get(subject_id)
            if existing is None or deadline_info["deadlineTs"] < existing["_ts"]:
                subject_deadline_map[subject_id] = {
                    "_ts": deadline_info["deadlineTs"],
                    "subject": subject_name,
                    "subjectId": subject_id,
                    "date": deadline_str,
                    "remaining": deadline_info["remaining"],
                    "urgent": deadline_info["urgent"],
                    "color": SUBJECT_COLORS.get(subject_id, DEFAULT_COLOR),
                }

    deadlines = [
        {k: v for k, v in item.items() if not k.startswith("_")}
        for item in sorted(subject_deadline_map.values(), key=lambda x: x["_ts"])
    ]

    pending_count = sum(1 for h in homework_list if not h["submitted"])
    submitted_count = sum(1 for h in homework_list if h["submitted"])

    return {
        "homeworkList": homework_list,
        "deadlines": deadlines,
        "pendingCount": pending_count,
        "submittedCount": submitted_count,
    }


def _build_exam_dashboard(user_id: str, store: JsonStore, now: datetime) -> dict[str, Any]:
    """
    构建考试通知数据：
    - 仅返回 upcoming / scheduled / active 状态的考试
    - 格式化为前端 examAlerts 所需字段
    """
    exams = store.list_payloads("exams", "exam")
    attempts = store.list_payloads("exams", "attempt", owner_id=user_id)
    attempt_by_exam = {item.get("examId"): item for item in attempts}

    exam_alerts = []
    for exam in exams:
        status = exam.get("status", "draft")
        exam_id = exam.get("id", "")

        # 只向仪表盘推送即将开始/进行中的考试
        if status not in ("upcoming", "scheduled", "active", "running"):
            # 也推送 completed 状态但最近完成的（3天内），让学生能看到历史
            if status == "completed":
                starts_at = exam.get("startsAt", "")
                deadline_info = _parse_deadline(starts_at, now)
                if deadline_info["deadlineTs"]:
                    try:
                        dt = datetime.fromisoformat(deadline_info["deadlineTs"])
                        if (now - dt.astimezone(CHINA_TZ)).total_seconds() > 3 * 86400:
                            continue
                    except Exception:
                        continue
                else:
                    continue
            else:
                continue

        attempt = attempt_by_exam.get(exam_id)
        date_str = _format_exam_date(exam.get("startsAt"))
        duration = exam.get("durationMinutes", 60)
        types = exam.get("questionTypes") or []
        type_labels = "、".join(t.get("label", "") for t in types if isinstance(t, dict) and t.get("label"))
        readiness = exam.get("readiness", "")

        note_parts = []
        if duration:
            note_parts.append(f"考试时长 {duration} 分钟")
        if type_labels:
            note_parts.append(f"题型：{type_labels}")
        if readiness:
            note_parts.append(readiness)
        if attempt and attempt.get("status") == "submitted":
            note_parts.append("（已提交）")

        exam_alerts.append({
            "id": exam_id,
            "name": exam.get("title", "未命名考试"),
            "subject": exam.get("subject", ""),
            "date": date_str,
            "status": status,
            "note": "。".join(note_parts) + "。" if note_parts else "",
            "attemptId": attempt.get("id") if attempt else None,
            "score": attempt.get("score") if attempt else None,
        })

    # 按开考时间正序排列
    exam_alerts.sort(key=lambda x: x.get("date", ""))
    return {"examAlerts": exam_alerts}


def _build_mistake_dashboard(user_id: str, store: JsonStore) -> dict[str, Any]:
    """
    构建错题本数据：
    - errorNotebook: 最近 5 条错题（仪表盘复盘卡片）
    - errorPoints: 未掌握的高频错题知识点（易错点面板）
    """
    mistakes = store.list_payloads("exams", "mistake", owner_id=user_id)

    # errorNotebook：最近 5 条（按 lastWrongAt 倒序）
    sorted_mistakes = sorted(
        mistakes,
        key=lambda x: x.get("lastWrongAt", "") or x.get("updatedAt", ""),
        reverse=True,
    )
    error_notebook = []
    for m in sorted_mistakes[:5]:
        last_ts = m.get("lastWrongAt") or m.get("updatedAt") or ""
        # 提取月日格式：2026-07-05T14:00:00 → 07-05
        date_label = ""
        if last_ts:
            try:
                dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                date_label = f"{dt.month:02d}-{dt.day:02d}"
            except Exception:
                date_label = last_ts[:10]
        error_notebook.append({
            "id": m.get("id"),
            "subject": m.get("subject", ""),
            "date": date_label,
            "question": m.get("questionTitle", ""),
            "mastered": bool(m.get("mastered", False)),
            "wrongCount": m.get("wrongCount", 1),
        })

    # errorPoints：未掌握的知识点聚合（按 wrongCount 倒序，最多取 5 个）
    unmastered = [m for m in mistakes if not m.get("mastered", False)]
    unmastered.sort(key=lambda x: x.get("wrongCount", 1), reverse=True)
    error_points = []
    seen_titles: set[str] = set()
    for m in unmastered:
        title = m.get("questionTitle", "")[:40]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        wrong_count = m.get("wrongCount", 1)
        severity = "high" if wrong_count >= 3 else "medium" if wrong_count >= 2 else "low"
        tags = m.get("knowledgeTags") or []
        detail = m.get("errorReason") or ("、".join(tags) if tags else "")
        error_points.append({
            "id": m.get("id"),
            "topic": title,
            "count": wrong_count,
            "severity": severity,
            "detail": detail,
            "subject": m.get("subject", ""),
        })
        if len(error_points) >= 5:
            break

    # 错题概要统计
    mistake_summary = {
        "total": len(mistakes),
        "unresolved": len([m for m in mistakes if not m.get("mastered")]),
        "repeated": len([m for m in mistakes if m.get("wrongCount", 1) > 1]),
        "aiAnalyzed": len([m for m in mistakes if m.get("aiAnalysis")]),
    }

    return {
        "errorNotebook": error_notebook,
        "errorPoints": error_points,
        "mistakeSummary": mistake_summary,
    }


# ─── 学生仪表盘聚合端点 ──────────────────────────────────────

@router.get("/dashboard/student/{user_id}")
async def get_student_dashboard(user_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    # Require authentication and validate user_id matches token
    auth_username = _require_auth_user(authorization)
    if user_id != auth_username:
        raise HTTPException(status_code=403, detail="forbidden: cannot access other user's dashboard")
    """
    学生仪表盘一站式聚合接口。
    汇聚以下数据模块：
    - homeworkList: 作业列表（已适配仪表盘格式）
    - deadlines: 各科目最近未提交截止时间
    - examAlerts: 即将/进行中的考试通知
    - errorNotebook: 最近 5 条错题复盘
    - errorPoints: 未掌握的高频易错点
    - mistakeSummary: 错题统计
    - pendingCount / submittedCount: 作业完成状态统计
    """
    store = JsonStore(db)
    now = _now_china()

    hw_data = _build_homework_dashboard(user_id, store, now)
    exam_data = _build_exam_dashboard(user_id, store, now)
    mistake_data = _build_mistake_dashboard(user_id, store)

    # 聚合干预任务和 nudge
    interventions = store.list_payloads("dashboard", "intervention", owner_id=user_id)
    nudges = store.list_payloads("analytics", "nudge", owner_id=user_id)
    # 聚合通知（补发提醒等）
    all_notifications = store.list_payloads("dashboard", "notification")
    # 过滤属于该学生的通知（全班通知 + 针对个人的通知）
    notifications = [
        n for n in all_notifications
        if not n.get("studentIds")  # 全班通知（无 studentIds 字段）
        or user_id in (n.get("studentIds") or [])  # 精确匹配个人通知
    ]

    return ok({
        **hw_data,
        **exam_data,
        **mistake_data,
        "interventions": interventions,
        "nudges": nudges,
        "notifications": notifications,
        "userId": user_id,
        "generatedAt": utc_now_iso(),
    })


# ─── 教师干预交互端点 ─────────────────────────────────────────

@router.post("/dashboard/teacher/intervention")
async def create_teacher_intervention(payload: FreePayload, db: Session = Depends(get_db)):
    """
    教师端下发干预任务到学生仪表盘。
    支持类型：homework（补弱作业）、quiz（短测）、mistake（错题订正）、nudge（学情提醒）、ai-guide（AI引导）
    
    下发后：
    1. 将任务写入 domain_records（intervention 类型）
    2. 如果是 homework/quiz 类型，同步写入 homework 模块
    3. 如果是 mistake 类型，同步写入 exams.mistake 模块
    """
    data = payload.model_dump()
    intervention_type = data.get("type", "nudge")
    target_user_id = data.get("targetUserId") or data.get("userId") or ""
    teacher_id = data.get("teacherId") or data.get("createdBy") or ""
    now_iso = utc_now_iso()

    record_id = str(data.get("recordId") or make_record_key("intervention"))
    intervention = {
        "id": record_id,
        "type": intervention_type,
        "teacherId": teacher_id,
        "targetUserId": target_user_id,
        "title": data.get("title") or data.get("topic") or "教师下发任务",
        "subject": data.get("subject") or "",
        "desc": data.get("desc") or "",
        "deadline": data.get("deadline") or "",
        "status": "active",
        "createdAt": now_iso,
        "payload": data,
    }
    JsonStore(db).upsert("dashboard", "intervention", record_id, intervention,
                         owner_id=target_user_id, status="active")

    # 如果是作业/短测类型，同步写入 homework 模块让学生作业页可见
    if intervention_type in ("homework", "quiz"):
        hw_id = data.get("homeworkId") or make_record_key("teacher-hw")
        homework = {
            "id": hw_id,
            "subjectId": data.get("subjectId") or "GENERAL",
            "subjectName": data.get("subject") or "通用",
            "type": "daily" if intervention_type == "homework" else "quiz",
            "title": intervention["title"],
            "deadline": intervention["deadline"],
            "urgent": True,
            "status": "unsubmitted",
            "grade": None,
            "teacherComment": "",
            "diagnosis": None,
            "questions": data.get("questions") or [],
            "submittedAnswers": {},
            "submittedFile": None,
            "teacherId": teacher_id,
            "fromIntervention": record_id,
            "createdAt": now_iso,
        }
        JsonStore(db).upsert("homework", "homework", hw_id, homework, status="unsubmitted")
        intervention["homeworkId"] = hw_id

    # 如果是错题订正类型，同步写入 exams.mistake 模块
    if intervention_type == "mistake":
        mistake_id = data.get("mistakeId") or make_record_key("teacher-mistake")
        mistake = {
            "id": mistake_id,
            "studentId": target_user_id,
            "subject": data.get("subject") or "",
            "questionTitle": intervention["title"],
            "questionType": "订正题",
            "studentAnswer": "",
            "correctAnswer": data.get("correctAnswer") or "",
            "errorReason": data.get("desc") or "教师下发错题订正任务",
            "knowledgeTags": data.get("knowledgeTags") or [],
            "wrongCount": 1,
            "mastered": False,
            "fromIntervention": record_id,
            "lastWrongAt": now_iso,
        }
        JsonStore(db).upsert("exams", "mistake", mistake_id, mistake, owner_id=target_user_id)
        intervention["mistakeId"] = mistake_id

    return ok({
        "success": True,
        "recordId": record_id,
        "intervention": intervention,
        "createdAt": now_iso,
    })


@router.get("/dashboard/teacher/interventions")
async def get_teacher_interventions(
    teacherId: str = "",
    targetUserId: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    """
    查询教师下发的干预任务列表。
    支持按 teacherId / targetUserId / status 过滤。
    """
    store = JsonStore(db)
    interventions = store.list_payloads("dashboard", "intervention",
                                        owner_id=targetUserId if targetUserId else None,
                                        status=status if status else None)
    if teacherId:
        interventions = [i for i in interventions if i.get("teacherId") == teacherId]

    return ok({
        "total": len(interventions),
        "interventions": interventions,
    })


@router.get("/dashboard/teacher/class-overview")
async def get_teacher_class_overview(classId: str = "", db: Session = Depends(get_db)):
    """
    教师端班级学情大屏聚合数据。
    返回：作业提交率、平均分、高危学生、错题热点、考试进度。
    """
    store = JsonStore(db)
    homeworks = store.list_payloads("homework", "homework")
    submissions = store.list_payloads("homework", "submission")
    mistakes = store.list_payloads("exams", "mistake")
    exams = store.list_payloads("exams", "exam")

    if classId:
        submissions = [s for s in submissions if s.get("className") == classId]
        mistakes = [m for m in mistakes if m.get("className") == classId]

    # 作业提交统计
    total_submissions = len(submissions)
    graded_submissions = len([s for s in submissions if s.get("status") == "graded"])
    pending_submissions = len([s for s in submissions if s.get("status") in ("pending", "review")])

    # 错题热点（按知识点聚合）
    tag_counts: dict[str, int] = {}
    for m in mistakes:
        for tag in (m.get("knowledgeTags") or []):
            tag_counts[str(tag)] = tag_counts.get(str(tag), 0) + 1
    hot_topics = [
        {"tag": tag, "count": count}
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    ]

    # 高危学生（错题数 >= 3 且未掌握）
    student_mistake_counts: dict[str, int] = {}
    for m in mistakes:
        if not m.get("mastered"):
            sid = m.get("studentId", "")
            student_mistake_counts[sid] = student_mistake_counts.get(sid, 0) + 1
    high_risk = [
        {"studentId": sid, "unmasteredCount": count}
        for sid, count in sorted(student_mistake_counts.items(), key=lambda x: x[1], reverse=True)
        if count >= 2
    ][:10]

    return ok({
        "homework": {
            "total": len(homeworks),
            "totalSubmissions": total_submissions,
            "graded": graded_submissions,
            "pending": pending_submissions,
        },
        "mistakes": {
            "total": len(mistakes),
            "hotTopics": hot_topics,
            "highRiskStudents": high_risk,
        },
        "exams": {
            "total": len(exams),
            "active": len([e for e in exams if e.get("status") in ("active", "running")]),
            "upcoming": len([e for e in exams if e.get("status") in ("upcoming", "scheduled")]),
        },
        "generatedAt": utc_now_iso(),
    })


# ─── 学生端交互任务端点 ────────────────────────────────────────

@router.get("/dashboard/student/{user_id}/interactions")
async def get_student_interactions(user_id: str, db: Session = Depends(get_db)):
    """获取学生可见的干预任务、nudge 和 interaction"""
    store = JsonStore(db)
    interventions = store.list_payloads("dashboard", "intervention", owner_id=user_id)
    nudges = store.list_payloads("analytics", "nudge", owner_id=user_id)
    all_interactions = store.list_payloads("analytics", "interaction")

    # 筛选属于该学生的 interaction：无定向 = 全班，或按 studentIds 精确匹配（username）
    student_interactions = [
        item for item in all_interactions
        if not item.get("studentIds")
        or user_id in (item.get("studentIds") or [])
        or str(user_id) in [str(x) for x in (item.get("studentIds") or [])]
    ]

    return ok({
        "interventions": interventions,
        "nudges": nudges,
        "interactions": student_interactions,
    })
