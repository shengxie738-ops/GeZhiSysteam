import json
import re
from datetime import datetime, timezone, timedelta
from statistics import mean
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.miniprogram_response import api_response, is_miniprogram_client, page_items
from app.core.responses import ok
from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore, make_record_key
from app.core.config import Settings
from app.services.model_registry import build_chat_model
from app.utils.datetime import utc_now_iso

router = APIRouter()


RADAR_INDICATORS = [
    {"name": "规划一致性", "max": 100},
    {"name": "代码质量与工程", "max": 100},
    {"name": "理论逻辑完备度", "max": 100},
    {"name": "学术论坛活跃度", "max": 100},
    {"name": "专注度均值", "max": 100},
    {"name": "Checkpoint完成率", "max": 100},
]

WEEKLY_ACTIVITY_DATES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class FreePayload(BaseModel):
    class Config:
        extra = "allow"


GRADE_LETTER_MAP = {"A": 92, "B": 82, "C": 72, "D": 62, "E": 52}


def _safe_int(val, default: int = 50) -> int:
    """安全转换为 int，失败时返回默认值"""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _author_matches(item: dict[str, Any], username: str, real_name: str) -> bool:
    author_username = str(item.get("authorUsername") or "").strip()
    author = str(item.get("author") or "").strip()
    if author_username and author_username == username:
        return True
    if real_name and author == real_name:
        return True
    if author and author == username:
        return True
    return False


def _submission_numeric_score(sub: dict[str, Any]) -> int | None:
    grade = sub.get("grade")
    if grade is not None:
        letter = str(grade).upper()
        if letter in GRADE_LETTER_MAP:
            return GRADE_LETTER_MAP[letter]
        try:
            return int(float(grade))
        except (ValueError, TypeError):
            pass
    if sub.get("aiScore") is not None:
        return _safe_int(sub.get("aiScore"), 0)
    return None


def _compute_radar_values(
    username: str,
    real_name: str,
    profile: StudentProfile | None,
    store: JsonStore | None,
    *,
    all_homeworks: list[dict[str, Any]] | None = None,
    forum_posts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """基于作业诊断、考试、论坛、画像与日常 Checkpoint 计算六维雷达。"""
    knowledge = _safe_int(getattr(profile, "knowledge", 50) or 50)
    pace = _safe_int(getattr(profile, "pace", 50) or 50)

    submissions = store.list_payloads("homework", "submission", owner_id=username) if store else []
    attempts = store.list_payloads("exams", "attempt", owner_id=username) if store else []
    mistakes = store.list_payloads("exams", "mistake", owner_id=username) if store else []

    alina_scores: list[int] = []
    ninja_scores: list[int] = []
    profx_scores: list[int] = []
    homework_numeric: list[int] = []
    for sub in submissions:
        scores = ((sub.get("diagnosis") or {}).get("scores") or {})
        if scores.get("alina") is not None:
            alina_scores.append(_safe_int(scores.get("alina"), 0))
        if scores.get("codeninja") is not None:
            ninja_scores.append(_safe_int(scores.get("codeninja"), 0))
        if scores.get("profx") is not None:
            profx_scores.append(_safe_int(scores.get("profx"), 0))
        numeric = _submission_numeric_score(sub)
        if numeric is not None:
            homework_numeric.append(numeric)

    homework_avg = round(mean(homework_numeric)) if homework_numeric else knowledge

    exam_scores: list[int] = []
    prog_scores: list[int] = []
    obj_pcts: list[int] = []
    for att in attempts:
        if att.get("programmingScore") is not None:
            prog_scores.append(_safe_int(att.get("programmingScore"), 0))
        obj = att.get("objectiveScore")
        max_obj = att.get("maxObjectiveScore") or att.get("objectiveMax")
        if obj is not None and max_obj is not None:
            try:
                max_val = float(max_obj)
                if max_val > 0:
                    obj_pcts.append(round(float(obj) / max_val * 100))
                    continue
            except (ValueError, TypeError):
                pass
        if obj is not None:
            exam_scores.append(_safe_int(obj, 0))
        elif att.get("totalScore") is not None:
            exam_scores.append(_safe_int(att.get("totalScore"), 0))

    exam_avg = round(mean(exam_scores)) if exam_scores else knowledge

    # 1 规划一致性 ← Alina 诊断均值，兜底 pace
    if alina_scores:
        planning = round(mean(alina_scores))
        planning_evidence = {
            "source": "diagnosis.scores.alina",
            "label": f"Alina诊断 {len(alina_scores)} 次均值 {planning}",
            "sampleCount": len(alina_scores),
            "rawMean": planning,
        }
    else:
        planning = pace
        planning_evidence = {
            "source": "profile.pace",
            "label": f"画像步调兜底 {planning}",
            "sampleCount": 0,
            "rawMean": planning,
        }

    # 2 代码质量与工程 ← CodeNinja 0.7 + 编程分 0.3
    ninja_avg = round(mean(ninja_scores)) if ninja_scores else None
    prog_avg = round(mean(prog_scores)) if prog_scores else None
    if ninja_avg is not None and prog_avg is not None:
        code_quality = round(ninja_avg * 0.7 + prog_avg * 0.3)
        code_evidence = {
            "source": "diagnosis.codeninja+exam.programmingScore",
            "label": f"CodeNinja {ninja_avg} ×0.7 + 编程分 {prog_avg} ×0.3",
            "sampleCount": len(ninja_scores) + len(prog_scores),
            "rawMean": code_quality,
        }
    elif ninja_avg is not None:
        code_quality = ninja_avg
        code_evidence = {
            "source": "diagnosis.scores.codeninja",
            "label": f"CodeNinja诊断 {len(ninja_scores)} 次均值 {code_quality}",
            "sampleCount": len(ninja_scores),
            "rawMean": code_quality,
        }
    elif prog_avg is not None:
        code_quality = prog_avg
        code_evidence = {
            "source": "exam.programmingScore",
            "label": f"考试编程分均值 {code_quality}",
            "sampleCount": len(prog_scores),
            "rawMean": code_quality,
        }
    else:
        code_quality = exam_avg if exam_scores else knowledge
        code_evidence = {
            "source": "exam_avg" if exam_scores else "profile.knowledge",
            "label": f"{'考试均分' if exam_scores else '画像知识'}兜底 {code_quality}",
            "sampleCount": len(exam_scores),
            "rawMean": code_quality,
        }

    # 3 理论逻辑完备度 ← Prof.X + 客观题得分率
    profx_avg = round(mean(profx_scores)) if profx_scores else None
    obj_avg = round(mean(obj_pcts)) if obj_pcts else (round(mean(exam_scores)) if exam_scores else None)
    theory_parts = [v for v in [profx_avg, obj_avg] if v is not None]
    if theory_parts:
        theory = round(mean(theory_parts))
        if profx_avg is not None and obj_avg is not None:
            theory_source = "diagnosis.profx+exam.objective"
            theory_label = f"Prof.X {profx_avg} 与客观题 {obj_avg} 均值"
        elif profx_avg is not None:
            theory_source = "diagnosis.scores.profx"
            theory_label = f"Prof.X诊断 {len(profx_scores)} 次均值 {theory}"
        else:
            theory_source = "exam.objective"
            theory_label = f"考试客观题均值 {theory}"
        theory_evidence = {
            "source": theory_source,
            "label": theory_label,
            "sampleCount": len(profx_scores) + len(obj_pcts) + (len(exam_scores) if not obj_pcts else 0),
            "rawMean": theory,
        }
    else:
        theory = homework_avg
        theory_evidence = {
            "source": "homework_avg",
            "label": f"作业均分兜底 {theory}",
            "sampleCount": len(homework_numeric),
            "rawMean": theory,
        }

    # 4 学术论坛活跃度 ← 发帖+10 / 回帖+5，封顶 100
    posts = forum_posts if forum_posts is not None else (store.list_payloads("forum", "post") if store else [])
    activity = 0
    post_count = 0
    reply_count = 0
    for post in posts:
        if _author_matches(post, username, real_name):
            activity += 10
            post_count += 1
        for reply in post.get("replies") or []:
            if _author_matches(reply, username, real_name):
                activity += 5
                reply_count += 1
    forum_score = min(100, activity)
    forum_evidence = {
        "source": "forum/post+replies",
        "label": f"发帖 {post_count} · 回帖 {reply_count}",
        "sampleCount": post_count + reply_count,
        "rawMean": forum_score,
    }

    # 5 专注度均值 ← 0.6*pace + 0.4*错题代理
    unmastered = [m for m in mistakes if not m.get("mastered")]
    repeated = [m for m in unmastered if _safe_int(m.get("wrongCount", 1), 1) > 1]
    mistake_proxy = max(0, 100 - len(unmastered) * 5 - len(repeated) * 8)
    focus = min(100, max(0, round(0.6 * pace + 0.4 * mistake_proxy)))
    focus_evidence = {
        "source": "profile.pace+mistakes",
        "label": f"步调 {pace} · 未掌握 {len(unmastered)} · 反复错 {len(repeated)}",
        "sampleCount": len(mistakes),
        "rawMean": focus,
    }

    # 6 Checkpoint完成率 ← 仅 type==daily
    homeworks = all_homeworks if all_homeworks is not None else (store.list_payloads("homework", "homework") if store else [])
    daily = [h for h in homeworks if h.get("type") == "daily"]
    sub_by_hw = {str(sub.get("homeworkId")): sub for sub in submissions if sub.get("homeworkId")}
    completed = 0
    for hw in daily:
        status = (sub_by_hw.get(str(hw.get("id"))) or {}).get("status")
        if status in ("submitted", "graded"):
            completed += 1
    checkpoint_rate = round(completed / len(daily) * 100) if daily else 0
    checkpoint_evidence = {
        "source": "homework.type=daily",
        "label": f"日常 Checkpoint {completed}/{len(daily)}",
        "sampleCount": len(daily),
        "rawMean": checkpoint_rate,
    }

    radar_values = [planning, code_quality, theory, forum_score, focus, checkpoint_rate]
    return {
        "radarValues": radar_values,
        "radarEvidence": {
            "规划一致性": planning_evidence,
            "代码质量与工程": code_evidence,
            "理论逻辑完备度": theory_evidence,
            "学术论坛活跃度": forum_evidence,
            "专注度均值": focus_evidence,
            "Checkpoint完成率": checkpoint_evidence,
        },
        "homeworkAvg": homework_avg,
        "examAvg": exam_avg,
        "focus": focus,
        "progress": homework_avg,
        "errorCount": len(mistakes),
        "unmasteredCount": len(unmastered),
        "forumCount": post_count,
        "checkpointRate": checkpoint_rate,
    }


def _student_card(
    account: UserAccount,
    profile: StudentProfile | None,
    index: int,
    store: JsonStore | None = None,
    *,
    all_homeworks: list[dict[str, Any]] | None = None,
    forum_posts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """生成学生卡片，聚合真实作业/考试/论坛/诊断数据"""
    username = account.username
    real_name = account.real_name or username
    metrics = _compute_radar_values(
        username,
        real_name,
        profile,
        store,
        all_homeworks=all_homeworks,
        forum_posts=forum_posts,
    )
    progress = metrics["progress"]
    focus = metrics["focus"]

    return {
        "id": index,
        "userId": username,
        "username": username,
        "name": real_name,
        "className": account.class_name or "",
        "progress": progress,
        "focus": focus,
        "goal": getattr(profile, "goal", "") if profile else "",
        "status": "online",
        "currentAgent": "Alina",
        "alert": progress < 50 or focus < 50,
        "errorCount": metrics["errorCount"],
        "forumCount": metrics["forumCount"],
        "activeRate": focus,
        "radarValues": metrics["radarValues"],
        "radarEvidence": metrics["radarEvidence"],
        "checkpointRate": metrics["checkpointRate"],
    }


def _student_cards(db: Session) -> list[dict[str, Any]]:
    students = db.query(UserAccount).filter(UserAccount.role == "student").order_by(UserAccount.created_at.asc()).all()
    profiles = {
        item.user_id: item
        for item in db.query(StudentProfile).filter(StudentProfile.user_id.in_([student.username for student in students] or [""])).all()
    }
    store = JsonStore(db)
    all_homeworks = store.list_payloads("homework", "homework")
    forum_posts = store.list_payloads("forum", "post")
    return [
        _student_card(
            student,
            profiles.get(student.username),
            index + 1,
            store,
            all_homeworks=all_homeworks,
            forum_posts=forum_posts,
        )
        for index, student in enumerate(students)
    ]


def _build_student_timeline(matched: dict[str, Any], error_count: int, pending_intervention: bool = False) -> list[dict[str, Any]]:
    progress = _safe_int(matched.get("progress"), 0)
    alert = bool(matched.get("alert")) or pending_intervention
    return [
        {
            "label": "作业提交",
            "value": "节奏稳定" if progress >= 60 else "低于班级均值",
            "tone": "good" if progress >= 60 else "risk",
        },
        {
            "label": "错题新增",
            "value": f"{error_count} 个卡点",
            "tone": "risk" if error_count > 2 else "normal",
        },
        {
            "label": "AI 会诊",
            "value": matched.get("currentAgent") or "Alina",
            "tone": "good",
        },
        {
            "label": "教师干预",
            "value": "待跟进" if alert else "暂无异常",
            "tone": "risk" if alert else "good",
        },
    ]


def _rounded_mean(values: list[int | float], default: int = 0) -> int:
    return round(mean(values)) if values else default


def _class_radar_values(students: list[dict[str, Any]]) -> list[int]:
    if not students:
        return [0, 0, 0, 0, 0, 0]

    radar_rows = [item.get("radarValues") or [] for item in students]
    return [
        _rounded_mean([int(row[index] or 0) for row in radar_rows if len(row) > index])
        for index in range(6)
    ]


def _weekly_activity_rates(students: list[dict[str, Any]], store: JsonStore | None = None) -> list[int]:
    """基于真实提交时间戳按星期聚合周活跃率，无数据时降级为默认偏移"""
    student_count = len(students)
    if student_count == 0:
        return [0] * 7

    if store:
        # 按星期几聚合所有学生的提交时间戳（0=周一, 6=周日）
        weekday_active = [0] * 7
        all_submissions = store.list_payloads("homework", "submission")
        all_attempts = store.list_payloads("exams", "attempt")

        active_students_per_day = [set() for _ in range(7)]

        for sub in all_submissions:
            if sub.get("status") == "graded":
                submitted_at = sub.get("submittedAt") or sub.get("createdAt")
                if submitted_at:
                    try:
                        dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
                        wd = dt.weekday()  # 0=周一
                        active_students_per_day[wd].add(sub.get("studentId", ""))
                    except Exception:
                        pass

        for att in all_attempts:
            submitted_at = att.get("submittedAt")
            if submitted_at:
                try:
                    dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
                    wd = dt.weekday()
                    active_students_per_day[wd].add(att.get("studentId", ""))
                except Exception:
                    pass

        # 如果有真实提交数据，计算每天的活跃率
        total_active = sum(len(s) for s in active_students_per_day)
        if total_active > 0:
            return [
                min(100, max(0, round(len(active_students_per_day[d]) / student_count * 100)))
                for d in range(7)
            ]

    # 降级：使用原有基线偏移方案
    baseline = _rounded_mean([int(item.get("activeRate") or item.get("focus") or 0) for item in students], 0)
    offsets = [-16, -8, -4, 2, 6, 10, 12]
    return [min(100, max(0, baseline + offset)) for offset in offsets]


def _hourly_active_data(students: list[dict[str, Any]], store: JsonStore | None = None) -> list[int]:
    """基于真实提交/考试时间戳聚合24小时活跃分布，无数据时使用合理默认曲线"""
    student_count = len(students)
    if student_count == 0:
        return [0] * 24

    # 默认曲线（在无真实数据时作为兜底）
    default_curve = [
        0.08, 0.04, 0.02, 0.00, 0.00, 0.02,
        0.12, 0.32, 0.54, 0.72, 0.86, 0.78,
        0.52, 0.58, 0.76, 0.88, 0.72, 0.56,
        0.82, 0.94, 1.00, 0.84, 0.58, 0.28,
    ]

    if not store:
        return [min(student_count, round(student_count * ratio)) for ratio in default_curve]

    # 从真实数据聚合每小时活跃学生数
    hourly_active: dict[int, set[str]] = {h: set() for h in range(24)}

    # 收集作业提交时间
    try:
        submissions = store.list_payloads("homework", "submission")
        for sub in submissions:
            ts = sub.get("submittedAt") or sub.get("createdAt") or sub.get("updatedAt")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    hourly_active[dt.hour].add(sub.get("studentId") or sub.get("ownerId") or "")
                except (ValueError, AttributeError):
                    pass
    except Exception:
        pass

    # 收集考试提交时间
    try:
        attempts = store.list_payloads("exams", "attempt")
        for att in attempts:
            ts = att.get("submittedAt") or att.get("clientStartedAt") or att.get("createdAt")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    hourly_active[dt.hour].add(att.get("studentId") or att.get("ownerId") or "")
                except (ValueError, AttributeError):
                    pass
    except Exception:
        pass

    # 统计每小时活跃学生数
    result = [len(hourly_active[h]) for h in range(24)]

    # 如果没有任何真实数据，使用默认曲线
    if sum(result) == 0:
        return [min(student_count, round(student_count * ratio)) for ratio in default_curve]

    return result


def _weak_points(db: Session, students: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mistakes = JsonStore(db).list_payloads("exams", "mistake")
    total_students = max(1, len(students))
    weak_points = []

    for index, item in enumerate(mistakes[:6], start=1):
        wrong_count = int(item.get("wrongCount") or item.get("count") or 1)
        weak_points.append(
            {
                "id": item.get("id") or f"wp-{index}",
                "topic": item.get("questionTitle") or item.get("title") or item.get("topic") or "未命名薄弱点",
                "errorRate": min(100, max(0, round(wrong_count / total_students * 100))),
                "subject": item.get("subject") or "综合能力诊断",
                "category": item.get("category") or "错题诊断",
                "details": item.get("analysis")
                or item.get("details")
                or "系统基于学生错题、提交记录与课堂行为聚合生成该薄弱点。",
            }
        )

    return weak_points


def _auto_generate_advices(store: JsonStore, students: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """自动生成 AI 建议（供 overview 自动初始化使用，不调用 AI 时使用规则兜底）"""
    mistakes = store.list_payloads("exams", "mistake")
    submissions = store.list_payloads("homework", "submission")

    high_risk_count = len([s for s in students if s.get("alert")])
    unmastered_count = len([m for m in mistakes if not m.get("mastered")])
    submitted_count = len([s for s in submissions if s.get("status") in ("submitted", "graded")])

    tag_counts: dict[str, int] = {}
    for m in mistakes:
        if not m.get("mastered"):
            for tag in (m.get("knowledgeTags") or []):
                tag_counts[str(tag)] = tag_counts.get(str(tag), 0) + 1

    advices = [
        {"id": make_record_key("adv"), "type": "urgency", "title": "紧急：关注高危学生",
         "reason": f"当前有 {high_risk_count} 名学生进度低于50%",
         "suggestion": "安排一对一辅导或下发补弱作业", "active": True},
        {"id": make_record_key("adv"), "type": "knowledge", "title": "知识薄弱点补强",
         "reason": f"未掌握错题 {unmastered_count} 道",
         "suggestion": "针对高频错题知识点创建专项练习", "active": True},
        {"id": make_record_key("adv"), "type": "engagement", "title": "提升作业完成率",
         "reason": f"已提交作业 {submitted_count} 份",
         "suggestion": "对未提交学生发送催交提醒", "active": False},
    ]

    for adv in advices:
        store.upsert("analytics", "advice", adv["id"], adv)

    return advices


def _auto_generate_actions(store: JsonStore, students: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """自动生成行动队列（供 overview 自动初始化使用，纯规则引擎）"""
    mistakes = store.list_payloads("exams", "mistake")
    homeworks = store.list_payloads("homework", "homework")
    now_iso = utc_now_iso()
    actions: list[dict[str, Any]] = []

    # 规则 1：高危学生 → 督学行动
    high_risk = [s for s in students if s.get("alert")]
    for s in high_risk[:5]:
        actions.append({
            "id": make_record_key("act"), "type": "nudge",
            "studentName": s["name"], "studentId": s.get("username", ""),
            "title": f"督学提醒：{s['name']} 进度落后",
            "status": "pending", "reason": f"进度 {s['progress']}%，需关注",
            "createdAt": now_iso,
        })

    # 规则 2：未掌握高频错题 → 补弱行动
    unmastered = [m for m in mistakes if not m.get("mastered")]
    tag_counts: dict[str, int] = {}
    for m in unmastered:
        for tag in (m.get("knowledgeTags") or []):
            tag_counts[str(tag)] = tag_counts.get(str(tag), 0) + 1
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
        actions.append({
            "id": make_record_key("act"), "type": "remediation",
            "studentName": "全班", "studentId": "",
            "title": f"补弱作业：{tag}（{count}人错题）",
            "status": "pending", "reason": f"该知识点有 {count} 道未掌握错题",
            "createdAt": now_iso,
        })

    # 规则 3：即将截止作业 → 催交行动
    for hw in homeworks:
        deadline = hw.get("deadline", "")
        if deadline and hw.get("status") != "submitted":
            actions.append({
                "id": make_record_key("act"), "type": "reminder",
                "studentName": "全班", "studentId": "",
                "title": f"催交提醒：{hw.get('title', '作业')}",
                "status": "pending", "reason": f"截止时间: {deadline}",
                "createdAt": now_iso,
            })

    for action in actions:
        store.upsert("analytics", "action", action["id"], action)

    return actions


@router.get("/analytics/overview")
async def get_overview_stats(db: Session = Depends(get_db)):
    students = _student_cards(db)
    progress_values = [item["progress"] for item in students]
    focus_values = [item["focus"] for item in students]
    interactions = JsonStore(db).list_payloads("analytics", "interaction")
    store = JsonStore(db)

    # 自动初始化：如果 AI 建议为空，自动生成一次
    advices = store.list_payloads("analytics", "advice")
    if not advices:
        try:
            advices = _auto_generate_advices(store, students)
        except Exception:
            advices = []

    # 自动初始化：如果行动队列为空，自动生成一次
    actions = store.list_payloads("analytics", "action")
    if not actions:
        try:
            actions = _auto_generate_actions(store, students)
        except Exception:
            actions = []

    return ok(
        {
            "radarIndicators": RADAR_INDICATORS,
            "classRadarValues": _class_radar_values(students),
            "weeklyActivityDates": WEEKLY_ACTIVITY_DATES,
            "weeklyActivityRates": _weekly_activity_rates(students, store),
            "hourlyActiveData": _hourly_active_data(students, store),
            "weakPoints": _weak_points(db, students),
            "summary": {
                "studentCount": len(students),
                "averageProgress": round(mean(progress_values)) if progress_values else 0,
                "averageFocus": round(mean(focus_values)) if focus_values else 0,
                "activeInterventions": len([item for item in interactions if item.get("status") == "running"]),
            },
            "aiAdvices": advices,
            "actionQueue": actions,
            "interactionRecords": interactions,
        }
    )


@router.get("/analytics/students")
async def get_student_list(db: Session = Depends(get_db)):
    return ok(_student_cards(db))


@router.get("/analytics/students/search")
async def search_students(q: str = "", db: Session = Depends(get_db)):
    keyword = (q or "").strip().lower()
    students = _student_cards(db)
    if not keyword:
        return ok({"query": q, "matches": [], "total": 0})

    scored: list[tuple[int, dict[str, Any]]] = []
    for item in students:
        name = str(item.get("name") or "").lower()
        username = str(item.get("username") or item.get("userId") or "").lower()
        class_name = str(item.get("className") or "").lower()
        if keyword == name or keyword == username:
            score = 0
        elif name.startswith(keyword) or username.startswith(keyword):
            score = 1
        elif keyword in name or keyword in username or keyword in class_name:
            score = 2
        else:
            continue
        scored.append((score, item))

    scored.sort(key=lambda pair: (pair[0], str(pair[1].get("name") or "")))
    matches = [item for _, item in scored]
    return ok({"query": q, "matches": matches, "total": len(matches), "bestMatch": matches[0] if matches else None})


@router.get("/analytics/students/me")
async def get_my_radar(user_id: str = "", db: Session = Depends(get_db)):
    """学生端同源六维雷达：与教师端同一套 _compute_radar_values。"""
    username = (user_id or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="user_id is required")

    students = _student_cards(db)
    matched = next(
        (item for item in students if item.get("username") == username or item.get("userId") == username),
        None,
    )
    class_values = [80, 75, 63, 72, 78, 69]

    if not matched:
        account = db.query(UserAccount).filter(UserAccount.username == username).first()
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == username).first()
        store = JsonStore(db)
        metrics = _compute_radar_values(
            username,
            (account.real_name if account else None) or username,
            profile,
            store,
        )
        return ok(
            {
                "studentId": username,
                "name": (account.real_name if account else None) or username,
                "radarIndicators": RADAR_INDICATORS,
                "radarValues": metrics["radarValues"],
                "classRadarValues": class_values,
                "radarEvidence": metrics["radarEvidence"],
                "progress": metrics["progress"],
                "focus": metrics["focus"],
                "goal": getattr(profile, "goal", "") if profile else "",
            }
        )

    return ok(
        {
            "studentId": matched.get("id") or username,
            "name": matched.get("name", username),
            "radarIndicators": RADAR_INDICATORS,
            "radarValues": matched.get("radarValues", []),
            "classRadarValues": class_values,
            "radarEvidence": matched.get("radarEvidence", {}),
            "progress": matched.get("progress", 0),
            "focus": matched.get("focus", 0),
            "goal": matched.get("goal", ""),
            "agentName": matched.get("currentAgent", ""),
        }
    )


@router.get("/analytics/students/{student_id}")
async def get_student_details(student_id: str, db: Session = Depends(get_db)):
    store = JsonStore(db)
    students = _student_cards(db)
    matched = next(
        (
            item
            for item in students
            if str(item["id"]) == str(student_id) or item["username"] == student_id or item.get("userId") == student_id
        ),
        None,
    )
    if not matched:
        matched = {
            "id": student_id,
            "username": student_id,
            "name": student_id,
            "progress": 0,
            "focus": 0,
            "goal": "",
            "currentAgent": "",
            "alert": False,
            "radarValues": [0, 0, 0, 0, 0, 0],
            "radarEvidence": {},
        }

    username = matched.get("username") or matched.get("userId") or student_id
    mistakes = [
        item
        for item in store.list_payloads("exams", "mistake")
        if item.get("studentId") == username or item.get("studentId") == student_id
    ]
    pending_nudges = store.list_payloads("analytics", "nudge", owner_id=username)
    pending_intervention = bool(matched.get("alert")) or any(
        item.get("status") in (None, "sent", "unread", "active") for item in pending_nudges
    )

    return ok(
        {
            "studentId": matched.get("id") or student_id,
            "username": username,
            "name": matched.get("name", student_id),
            "progress": matched.get("progress", 0),
            "focus": matched.get("focus", 0),
            "goal": matched.get("goal", ""),
            "agentName": matched.get("currentAgent", ""),
            "errors": [
                {
                    "id": item.get("id"),
                    "topic": item.get("questionTitle") or item.get("title", ""),
                    "severity": "high" if item.get("wrongCount", 0) > 2 else "medium",
                    "count": item.get("wrongCount", 1),
                    "date": item.get("lastWrongAt") or item.get("createdAt", ""),
                }
                for item in mistakes
            ],
            "radarValues": matched.get("radarValues", []),
            "radarEvidence": matched.get("radarEvidence", {}),
            "radarIndicators": RADAR_INDICATORS,
            "timeline": _build_student_timeline(matched, len(mistakes), pending_intervention),
        }
    )


@router.post("/analytics/students/{student_id}/nudge")
async def send_nudge_message(student_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    # 优先用 username 作为 owner_id，保证学生端 list_payloads(owner_id=username) 能读到
    students = _student_cards(db)
    matched = next(
        (
            item
            for item in students
            if str(item["id"]) == str(student_id) or item["username"] == student_id or item.get("userId") == student_id
        ),
        None,
    )
    owner_id = (matched or {}).get("username") or data.get("username") or student_id
    record_id = make_record_key("nudge")
    JsonStore(db).upsert(
        "analytics",
        "nudge",
        record_id,
        {
            "id": record_id,
            "studentId": owner_id,
            "message": data.get("message", ""),
            "createdAt": utc_now_iso(),
            "status": "sent",
        },
        owner_id=owner_id,
        status="sent",
    )
    return ok({"success": True, "nudgedAt": utc_now_iso(), "studentId": owner_id})


@router.get("/analytics/advices")
async def get_ai_intervention_advices(db: Session = Depends(get_db)):
    return ok(JsonStore(db).list_payloads("analytics", "advice"))


@router.get("/analytics/action-queue")
async def get_action_queue(db: Session = Depends(get_db)):
    return ok(JsonStore(db).list_payloads("analytics", "action"))


@router.get("/analytics/interactions")
async def get_interaction_records(
    db: Session = Depends(get_db),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
):
    interactions = JsonStore(db).list_payloads("analytics", "interaction")
    if is_miniprogram_client(x_gezhi_client):
        return api_response(page_items(interactions, limit=len(interactions) or 20))
    return ok(interactions)


@router.post("/analytics/interactions")
async def dispatch_student_interaction(payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    record_id = str(data.get("id") or make_record_key("ir"))
    target = data.get("target") or {}
    target_label = target.get("label") if isinstance(target, dict) else str(target or "all")
    student_ids = target.get("studentIds", []) if isinstance(target, dict) else []
    # 将数字 id 解析为 username，保证学生端按 username 过滤可见
    if student_ids:
        cards = _student_cards(db)
        resolved: list[str] = []
        for sid in student_ids:
            matched = next(
                (
                    item
                    for item in cards
                    if str(item["id"]) == str(sid) or item.get("username") == sid or item.get("userId") == sid
                ),
                None,
            )
            resolved.append((matched or {}).get("username") or str(sid))
        student_ids = resolved
    initial_count = len(student_ids) or 48
    record = {
        "id": record_id,
        "type": data.get("type"),
        "title": data.get("title") or data.get("topic") or "Interaction task",
        "targetLabel": target_label or "all",
        "studentIds": student_ids,
        "completionRate": data.get("completionRate", 0),
        "unreadCount": data.get("unreadCount", initial_count),
        "pendingCount": data.get("pendingCount", initial_count),
        "completedCount": data.get("completedCount", 0),
        "createdAt": utc_now_iso(),
        "status": data.get("status") or "running",
        "nextAction": data.get("nextAction") or "Track student response.",
        "payload": data.get("payload") or {},
        "source": data.get("source") or {},
    }
    JsonStore(db).upsert("analytics", "interaction", record_id, record, status=record["status"])

    # 个人提醒同步写入 analytics/nudge，学生仪表盘可直接拉取
    if data.get("type") == "nudge" and student_ids:
        message = (data.get("payload") or {}).get("desc") or data.get("title") or "教师学习提醒"
        for owner_id in student_ids:
            nudge_id = make_record_key("nudge")
            JsonStore(db).upsert(
                "analytics",
                "nudge",
                nudge_id,
                {
                    "id": nudge_id,
                    "studentId": owner_id,
                    "message": message,
                    "interactionId": record_id,
                    "createdAt": utc_now_iso(),
                    "status": "sent",
                },
                owner_id=owner_id,
                status="sent",
            )

    return ok({"success": True, "record": record})


@router.patch("/analytics/interactions/{record_id}")
async def update_interaction_record(record_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    store = JsonStore(db)
    data = payload.model_dump()
    updated = store.patch("analytics", "interaction", record_id, data)

    # 如果是补发提醒（更新 unreadCount），写入通知记录供学生端拉取
    if "unreadCount" in data:
        existing = store.get_payload("analytics", "interaction", record_id) or {}
        notification_id = make_record_key("notif")
        store.upsert("dashboard", "notification", notification_id, {
            "id": notification_id,
            "type": "interaction_reminder",
            "interactionId": record_id,
            "title": existing.get("title") or "教师补发提醒",
            "targetLabel": existing.get("targetLabel") or "全班",
            "studentIds": existing.get("studentIds") or [],
            "message": data.get("message") or "教师针对此任务发送了新的提醒，请及时查看。",
            "createdAt": utc_now_iso(),
        }, status="unread")

    return ok({"success": True, "record": updated or {"id": record_id, **data}})


@router.post("/analytics/dispatch")
async def dispatch_intervention_task(payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    record_id = make_record_key("ir")
    record = {
        "id": record_id,
        "type": data.get("type"),
        "title": data.get("topic") or data.get("title") or "Intervention task",
        "targetLabel": (data.get("target") or {}).get("label", "all") if isinstance(data.get("target"), dict) else "all",
        "completionRate": 0,
        "unreadCount": 48,
        "pendingCount": 48,
        "completedCount": 0,
        "createdAt": utc_now_iso(),
        "status": "running",
        "nextAction": "Track student response.",
        "payload": data.get("payload") or {},
        "source": {"module": "teacher-analytics", "weakPointId": data.get("targetId")},
    }
    JsonStore(db).upsert("analytics", "interaction", record_id, record, status="running")
    return ok({"success": True, "dispatchedAt": utc_now_iso(), "record": record})


@router.post("/analytics/interactions/{record_id}/complete")
async def mark_interaction_complete(record_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    """学生标记交互任务完成，自动更新 completionRate 等计数（防重复提交）"""
    store = JsonStore(db)
    record = store.get_payload("analytics", "interaction", record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Interaction record not found")

    data = payload.model_dump()
    user_id = data.get("userId") or data.get("studentId") or ""

    # 防重复提交：检查该学生是否已完成此任务
    completion_id = f"{record_id}:{user_id}"
    existing_completion = store.get_payload("analytics", "interaction_completion", completion_id)
    if existing_completion:
        # 已完成过，直接返回当前状态
        return ok({
            "success": True,
            "alreadyCompleted": True,
            "completionRate": record.get("completionRate", 0),
            "completedCount": record.get("completedCount", 0),
        })

    # 更新计数
    completed = record.get("completedCount", 0) + 1
    pending = max(0, record.get("pendingCount", 0) - 1)
    unread = max(0, record.get("unreadCount", 0) - 1)
    total = completed + pending
    completion_rate = round(completed / total * 100) if total > 0 else 0

    patch = {
        "completedCount": completed,
        "pendingCount": pending,
        "unreadCount": unread,
        "completionRate": completion_rate,
        "status": "completed" if pending == 0 else "running",
    }
    store.patch("analytics", "interaction", record_id, patch)

    # 记录学生完成状态
    store.upsert("analytics", "interaction_completion", completion_id, {
        "id": completion_id,
        "interactionId": record_id,
        "userId": user_id,
        "completedAt": utc_now_iso(),
        "result": data.get("result", {}),
    }, owner_id=user_id, status="completed")

    return ok({"success": True, "completionRate": completion_rate, "completedCount": completed})


@router.post("/analytics/advices/generate")
async def generate_ai_advices(payload: FreePayload = None, db: Session = Depends(get_db)):
    """基于班级学情数据调用 AI 生成干预建议"""
    store = JsonStore(db)
    students = _student_cards(db)
    mistakes = store.list_payloads("exams", "mistake")
    submissions = store.list_payloads("homework", "submission")

    # 聚合班级数据
    student_count = len(students)
    high_risk = [s for s in students if s.get("alert")]
    high_risk_count = len(high_risk)
    avg_progress = round(mean([s["progress"] for s in students])) if students else 0
    unmastered_count = len([m for m in mistakes if not m.get("mastered")])
    submitted_count = len([s for s in submissions if s.get("status") in ("submitted", "graded")])

    # 薄弱知识点聚合
    tag_counts: dict[str, int] = {}
    for m in mistakes:
        if not m.get("mastered"):
            for tag in (m.get("knowledgeTags") or []):
                tag_counts[str(tag)] = tag_counts.get(str(tag), 0) + 1
    weak_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # 兜底建议
    fallback_advices = [
        {"id": "adv-1", "type": "urgency", "title": "紧急：关注高危学生",
         "reason": f"当前有 {high_risk_count} 名学生进度低于50%",
         "suggestion": "安排一对一辅导或下发补弱作业", "active": True},
        {"id": "adv-2", "type": "knowledge", "title": "知识薄弱点补强",
         "reason": f"未掌握错题 {unmastered_count} 道",
         "suggestion": "针对高频错题知识点创建专项练习", "active": True},
        {"id": "adv-3", "type": "engagement", "title": "提升作业完成率",
         "reason": f"已提交作业 {submitted_count} 份",
         "suggestion": "对未提交学生发送催交提醒", "active": False},
    ]

    advices = fallback_advices
    try:
        prompt = (
            f"你是教学干预策略AI助手。请基于以下班级学情数据生成3-5条干预建议。\n\n"
            f"学生总数: {student_count}\n"
            f"高危学生数: {high_risk_count}\n"
            f"平均进度: {avg_progress}\n"
            f"未掌握错题数: {unmastered_count}\n"
            f"已提交作业数: {submitted_count}\n"
            f"薄弱知识点: {weak_tags}\n\n"
            f"请返回JSON数组格式:\n"
            f'[{{"id": "adv-1", "type": "urgency|knowledge|engagement", '
            f'"title": "标题", "reason": "原因", "suggestion": "建议", "active": true}}]'
        )
        response = build_chat_model(Settings().LLM_MODEL_DEFAULT, temperature=0.4).invoke(prompt)
        content = getattr(response, "content", str(response))
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            if isinstance(parsed, list) and len(parsed) > 0:
                advices = parsed
    except Exception:
        pass

    # 持久化
    for adv in advices:
        adv_id = adv.get("id") or make_record_key("adv")
        adv["id"] = adv_id
        store.upsert("analytics", "advice", adv_id, adv)

    return ok(advices)


@router.post("/analytics/action-queue/generate")
async def generate_action_queue(payload: FreePayload = None, db: Session = Depends(get_db)):
    """基于规则引擎 + AI 生成今日行动队列"""
    store = JsonStore(db)
    students = _student_cards(db)
    mistakes = store.list_payloads("exams", "mistake")
    homeworks = store.list_payloads("homework", "homework")

    actions: list[dict[str, Any]] = []
    now_iso = utc_now_iso()

    # 规则 1：高危学生 → 督学行动
    high_risk = [s for s in students if s.get("alert")]
    for s in high_risk[:5]:
        actions.append({
            "id": make_record_key("act"),
            "type": "nudge",
            "studentName": s["name"],
            "studentId": s.get("username", ""),
            "title": f"督学提醒：{s['name']} 进度落后",
            "status": "pending",
            "reason": f"进度 {s['progress']}%，需关注",
            "createdAt": now_iso,
        })

    # 规则 2：未掌握高频错题 → 补弱行动
    unmastered = [m for m in mistakes if not m.get("mastered")]
    tag_counts: dict[str, int] = {}
    for m in unmastered:
        for tag in (m.get("knowledgeTags") or []):
            tag_counts[str(tag)] = tag_counts.get(str(tag), 0) + 1
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
        actions.append({
            "id": make_record_key("act"),
            "type": "remediation",
            "studentName": "全班",
            "studentId": "",
            "title": f"补弱作业：{tag}（{count}人错题）",
            "status": "pending",
            "reason": f"该知识点有 {count} 道未掌握错题",
            "createdAt": now_iso,
        })

    # 规则 3：即将截止作业 → 催交行动
    for hw in homeworks:
        deadline = hw.get("deadline", "")
        if deadline and hw.get("status") != "submitted":
            actions.append({
                "id": make_record_key("act"),
                "type": "reminder",
                "studentName": "全班",
                "studentId": "",
                "title": f"催交提醒：{hw.get('title', '作业')}",
                "status": "pending",
                "reason": f"截止时间: {deadline}",
                "createdAt": now_iso,
            })

    # 持久化
    for action in actions:
        store.upsert("analytics", "action", action["id"], action)

    return ok(actions)
