import json
import re
from statistics import mean
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import ok
from app.core.security import decode_access_token
from app.repositories.json_store import JsonStore, make_record_key
from app.core.config import Settings
from app.services.model_registry import build_chat_model
from app.services.learning_diagnosis.activity_listener import publish_learning_activity_safely
from app.utils.datetime import utc_now_iso


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

router = APIRouter()

CLASS_SIZE = 48


def _blocks_to_questions(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将教师端画布 blocks 转换为学生端 questions"""
    questions: list[dict[str, Any]] = []
    q_index = 1
    for block in blocks:
        btype = block.get("type")
        config = block.get("config") or {}
        if btype == "ai_objective":
            qtype = config.get("qType", "choice")
            count = int(config.get("count", 3))
            difficulty = config.get("difficulty", "medium")
            knowledge_point = config.get("knowledgePoint", "")
            for _ in range(count):
                if qtype == "choice":
                    questions.append({
                        "id": f"q{q_index}",
                        "type": "choice",
                        "title": f"[AI生成·{difficulty}] 第 {q_index} 题",
                        "options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"],
                        "correctAnswer": "A",
                        "knowledgePoint": knowledge_point,
                    })
                elif qtype == "blank":
                    questions.append({
                        "id": f"q{q_index}",
                        "type": "blank",
                        "title": f"[AI生成·{difficulty}] 第 {q_index} 题（填空）",
                        "correctAnswers": [f"答案_{q_index}_1", f"答案_{q_index}_2"],
                        "knowledgePoint": knowledge_point,
                    })
                else:
                    questions.append({
                        "id": f"q{q_index}",
                        "type": qtype,
                        "title": f"[AI生成·{difficulty}] 第 {q_index} 题",
                        "knowledgePoint": knowledge_point,
                    })
                q_index += 1
        elif btype == "programming":
            try:
                count = int(config.get("count", 1))
            except (ValueError, TypeError):
                count = 1
            for _ in range(count):
                questions.append({
                    "id": f"q{q_index}",
                    "type": "programming",
                    "title": f"编程实战题 {q_index}",
                    "desc": config.get("template", "请完成编程任务"),
                    "starterCode": config.get("template", ""),
                    "correctAnswers": [],
                    "knowledgePoint": "",
                })
                q_index += 1
        elif btype == "document":
            questions.append({
                "id": f"q{q_index}",
                "type": "text",
                "title": f"文档作业：{config.get('fileName', '实验报告')}",
                "desc": config.get("rubric", "请按评分细则提交"),
                "knowledgePoint": "",
            })
            q_index += 1
    return questions


class FreePayload(BaseModel):
    class Config:
        extra = "allow"


def _ai_score(submission: dict[str, Any]) -> int | None:
    diagnosis = submission.get("diagnosis") or {}
    scores = diagnosis.get("scores") or {}
    values = [value for value in scores.values() if isinstance(value, (int, float))]
    if values:
        return round(mean(values))
    if submission.get("grade"):
        return {"A": 92, "B": 82, "C": 72, "D": 62, "E": 52}.get(str(submission["grade"]).upper())
    return None


def _grade_from_score(score: int | None) -> str:
    if score is None:
        return "-"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "E"


def _compute_question_results(homework: dict[str, Any] | None, submission: dict[str, Any]) -> dict[str, Any]:
    """比对学生答案与正确答案，返回每题对错结果"""
    questions = (homework or {}).get("questions") or []
    answers = submission.get("answers") or {}
    results: dict[str, Any] = {}
    for q in questions:
        qid = q.get("id")
        if not qid:
            continue
        qtype = q.get("type", "")
        if qtype == "choice":
            student_ans = str(answers.get(qid, "")).strip().upper()
            correct_ans = str(q.get("correctAnswer", "")).strip().upper()
            results[qid] = student_ans == correct_ans if student_ans else None
        elif qtype == "blank":
            correct_answers = q.get("correctAnswers") or []
            if not correct_answers:
                results[qid] = None
            else:
                all_correct = True
                for i, ca in enumerate(correct_answers):
                    student_ans = str(answers.get(f"{qid}_{i}", "")).strip().lower()
                    if student_ans != str(ca).strip().lower():
                        all_correct = False
                        break
                results[qid] = all_correct
        elif qtype == "programming":
            code = str(answers.get(qid, ""))
            correct_keywords = q.get("correctAnswers") or []
            if correct_keywords:
                results[qid] = all(kw.lower() in code.lower() for kw in correct_keywords)
            else:
                results[qid] = bool(code.strip())
        else:
            results[qid] = None
    return results


def _build_insight(question: dict[str, Any], error_rate: float) -> str:
    """根据错误率生成题目洞察文本"""
    if error_rate >= 70:
        return f"该题集中错误率达 {error_rate}%，建议重点讲解核心概念。"
    elif error_rate >= 30:
        return f"该题错误率 {error_rate}%，存在中等程度的理解偏差。"
    elif error_rate > 0:
        return f"该题错误率 {error_rate}%，属于低频错误。"
    return "该题无错误记录。"


def _submission_view(homework: dict[str, Any] | None, submission: dict[str, Any]) -> dict[str, Any]:
    score = _ai_score(submission)
    view = dict(submission)
    view["aiScore"] = score
    view["recommendedGrade"] = _grade_from_score(score)
    view.setdefault("homeworkTitle", (homework or {}).get("title", ""))
    view["questionResults"] = _compute_question_results(homework, submission)
    return view


def _build_thought_genealogy(
    homework: dict[str, Any] | None,
    submissions: list[dict[str, Any]],
    question_stats: list[dict[str, Any]],
    total: int,
) -> dict[str, Any]:
    """基于错题数据生成思路族谱，按错误模式聚类为三个分支"""
    top_question = question_stats[0] if question_stats else {}
    branches: list[dict[str, Any]] = []

    # 预计算所有 submission 的 question_results，避免三次重复计算
    precomputed = []
    for sub in submissions:
        results = _compute_question_results(homework, sub)
        precomputed.append((sub, results))

    # 分支 1：全对路径（标准代理）
    all_correct_students = []
    for sub, results in precomputed:
        if results and all(v is True for v in results.values()):
            all_correct_students.append(sub.get("studentName", "unknown"))
    if all_correct_students:
        branches.append({
            "id": "branch-correct",
            "label": "标准路径：全题正确",
            "studentCount": len(all_correct_students),
            "description": "该分支学生掌握了全部知识点，建议安排进阶任务。",
            "students": all_correct_students[:5],
        })

    # 分支 2：部分对路径（属性直读）
    partial_students = []
    for sub, results in precomputed:
        if results:
            values = [v for v in results.values() if v is not None]
            if values and not all(v for v in values) and any(v for v in values):
                partial_students.append(sub.get("studentName", "unknown"))
    if partial_students:
        branches.append({
            "id": "branch-partial",
            "label": "部分正确：存在知识盲区",
            "studentCount": len(partial_students),
            "description": "该分支学生部分掌握，需针对性补弱。",
            "students": partial_students[:5],
        })

    # 分支 3：全错路径（依赖错位）
    all_wrong_students = []
    for sub, results in precomputed:
        if results:
            values = [v for v in results.values() if v is not None]
            if values and not any(v for v in values):
                all_wrong_students.append(sub.get("studentName", "unknown"))
    if all_wrong_students:
        branches.append({
            "id": "branch-wrong",
            "label": "全部错误：需要重建基础概念",
            "studentCount": len(all_wrong_students),
            "description": "该分支学生需要从基础概念重新学习。",
            "students": all_wrong_students[:5],
        })

    return {
        "questionTitle": top_question.get("title", ""),
        "totalAnalyzed": total,
        "branches": branches,
    }


def _analysis(homework: dict[str, Any] | None, submissions: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [_ai_score(item) for item in submissions]
    scores = [score for score in scores if score is not None]
    submitted_count = len(submissions)
    pending_count = len([item for item in submissions if item.get("status") != "graded"])
    average_score = round(mean(scores)) if scores else 0
    questions = (homework or {}).get("questions") or []
    question_stats = []
    for index, question in enumerate(questions):
        qid = question.get("id", f"q{index + 1}")
        wrong_students: list[str] = []
        correct_count = 0
        for sub in submissions:
            results = _compute_question_results(homework, sub)
            if results.get(qid) is True:
                correct_count += 1
            elif results.get(qid) is False:
                wrong_students.append(sub.get("studentName", "unknown"))
        wrong_count = len(wrong_students)
        error_rate = round(wrong_count / submitted_count * 100) if submitted_count else 0
        question_stats.append(
            {
                "id": qid,
                "label": f"Q{index + 1}",
                "title": question.get("title", ""),
                "type": question.get("type", ""),
                "knowledgePoint": question.get("knowledgePoint") or question.get("title", "")[:32],
                "wrongCount": wrong_count,
                "correctCount": correct_count,
                "totalCount": submitted_count,
                "errorRate": error_rate,
                "wrongStudents": wrong_students,
                "insight": _build_insight(question, error_rate),
                "typicalWrongCode": None,
            }
        )
    return {
        "homeworkId": (homework or {}).get("id"),
        "homeworkTitle": (homework or {}).get("title", ""),
        "submittedCount": submitted_count,
        "classSize": CLASS_SIZE,
        "submitRate": round(submitted_count / CLASS_SIZE * 100) if CLASS_SIZE else 0,
        "gradedCount": len([item for item in submissions if item.get("status") == "graded"]),
        "pendingCount": pending_count,
        "averageAiScore": average_score,
        "topErrorQuestion": question_stats[0] if question_stats else None,
        "weakKnowledgePoints": [],
        "thoughtGenealogy": _build_thought_genealogy(homework, submissions, question_stats, submitted_count),
        "questionStats": question_stats,
        "highRiskStudents": [
            item.get("studentName") for item in submissions if (_ai_score(item) or 100) < 60
        ],
        "generatedAt": utc_now_iso(),
    }


@router.get("/homework/student/list")
async def get_student_homework_list(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    userId = _require_auth_user(authorization)
    store = JsonStore(db)
    homeworks = store.list_payloads("homework", "homework")
    submissions = store.list_payloads("homework", "submission", owner_id=userId)
    by_homework = {item.get("homeworkId"): item for item in submissions}
    result = []
    for homework in homeworks:
        item = dict(homework)
        submission = by_homework.get(homework.get("id"))
        if submission:
            item["status"] = submission.get("status", "submitted")
            item["submittedAnswers"] = submission.get("answers", {})
            item["submittedFile"] = submission.get("file")
            item["grade"] = submission.get("grade")
            item["teacherComment"] = submission.get("teacherComment", "")
            item["diagnosis"] = submission.get("diagnosis")
        else:
            item.setdefault("status", "unsubmitted")
        result.append(item)
    return ok(result)


@router.get("/homework/teacher/overview")
async def get_teacher_homework_overview(db: Session = Depends(get_db)):
    store = JsonStore(db)
    homeworks = store.list_payloads("homework", "homework")
    submissions = store.list_payloads("homework", "submission")
    views = []
    for homework in homeworks:
        related = [item for item in submissions if item.get("homeworkId") == homework.get("id")]
        analysis = _analysis(homework, related)
        views.append(
            {
                "id": homework.get("id"),
                "title": homework.get("title"),
                "type": homework.get("type"),
                "subject": homework.get("subjectName") or homework.get("subject"),
                "deadline": homework.get("deadline"),
                "questions": homework.get("questions", []),
                "submitRate": analysis["submitRate"],
                "gradedCount": analysis["gradedCount"],
                "pendingCount": analysis["pendingCount"],
                "totalCount": len(related),
                "classSize": CLASS_SIZE,
                "averageAiScore": analysis["averageAiScore"],
                "topErrorQuestion": analysis["topErrorQuestion"],
                "weakKnowledgePoints": analysis["weakKnowledgePoints"],
                "thoughtGenealogy": analysis["thoughtGenealogy"],
            }
        )
    scores = [_ai_score(item) for item in submissions]
    scores = [score for score in scores if score is not None]
    return ok(
        {
            "summary": {
                "activeHomeworks": len(homeworks),
                "totalSubmissions": len(submissions),
                "pendingGrading": len([item for item in submissions if item.get("status") != "graded"]),
                "averageAiScore": round(mean(scores)) if scores else 0,
            },
            "homeworks": views,
        }
    )


@router.get("/homework/teacher/submissions")
async def get_homework_submissions(homeworkId: str, db: Session = Depends(get_db)):
    store = JsonStore(db)
    homework = store.get_payload("homework", "homework", homeworkId)
    submissions = [
        _submission_view(homework, item)
        for item in store.list_payloads("homework", "submission")
        if item.get("homeworkId") == homeworkId
    ]
    return ok(submissions)


@router.get("/homework/teacher/analysis")
async def get_homework_analysis(homeworkId: str, db: Session = Depends(get_db)):
    store = JsonStore(db)
    homework = store.get_payload("homework", "homework", homeworkId)
    submissions = [item for item in store.list_payloads("homework", "submission") if item.get("homeworkId") == homeworkId]
    return ok(_analysis(homework, submissions))


@router.post("/homework/teacher/report")
async def generate_homework_report(payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    homework_id = data.get("homeworkId")
    store = JsonStore(db)
    homework = store.get_payload("homework", "homework", homework_id) if homework_id else None
    submissions = [item for item in store.list_payloads("homework", "submission") if item.get("homeworkId") == homework_id]
    analysis = _analysis(homework, submissions)

    # 兜底报告内容
    default_suggestions = ["检查待批改的提交，尽快给出反馈。", "如有需要，创建一个简短的后续任务巩固薄弱知识点。"]
    default_student_insight = "本次作业数据已从数据库同步，请关注薄弱知识点的复习。"
    default_layered_adv = {
        "advanced": "为高分学生安排拓展任务。",
        "middle": "用引导示例复习核心概念。",
        "risk": "为高风险学生发送针对性补弱任务。",
    }

    # 尝试调用 AI 生成报告
    teacher_suggestions = default_suggestions
    student_insight = default_student_insight
    layered_adv = default_layered_adv
    try:
        error_qs = [q.get("title", "") for q in analysis["questionStats"][:3] if q.get("errorRate", 0) > 0]
        high_risk = analysis.get("highRiskStudents", [])
        prompt = (
            f"你是班级作业分析报告生成专家。请基于以下数据生成报告。\n\n"
            f"作业标题: {(homework or {}).get('title', '')}\n"
            f"提交人数: {analysis['submittedCount']}/{analysis['classSize']}\n"
            f"平均分: {analysis['averageAiScore']}\n"
            f"高错误率题目: {error_qs}\n"
            f"高风险学生: {high_risk}\n\n"
            f"请返回JSON格式:\n"
            f'{{"teacherSuggestions": ["建议1", "建议2", "建议3"], '
            f'"studentInsight": "给学生的洞察文本", '
            f'"layeredAdvice": {{"advanced": "高分学生建议", "middle": "中等学生建议", "risk": "高风险学生建议"}}}}'
        )
        model_id = Settings().LLM_MODEL_DEFAULT
        response = build_chat_model(model_id, temperature=0.4).invoke(prompt)
        content = getattr(response, "content", str(response))
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            if "teacherSuggestions" in parsed:
                teacher_suggestions = parsed["teacherSuggestions"]
            if "studentInsight" in parsed:
                student_insight = parsed["studentInsight"]
            if "layeredAdvice" in parsed:
                layered_adv = parsed["layeredAdvice"]
    except Exception:
        pass  # 使用兜底内容

    report = {
        "homeworkId": homework_id,
        "title": f"{(homework or {}).get('title', 'Homework')} AI Report",
        "generatedAt": utc_now_iso(),
        "overview": {
            "submittedCount": analysis["submittedCount"],
            "classSize": analysis["classSize"],
            "gradedCount": analysis["gradedCount"],
            "pendingCount": analysis["pendingCount"],
            "averageAiScore": analysis["averageAiScore"],
            "masteryLevel": "stable" if analysis["averageAiScore"] >= 75 else "needs intervention",
        },
        "topErrorQuestions": analysis["questionStats"][:3],
        "weakKnowledgePoints": analysis["weakKnowledgePoints"],
        "layeredAdvice": layered_adv,
        "teacherSuggestions": teacher_suggestions,
        "studentInsight": student_insight,
        "summary": "Report generated successfully.",
    }
    return ok(report)


@router.post("/homework/attempts/{attempt_id}/grade")
async def grade_homework(attempt_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    store = JsonStore(db)
    patch = payload.model_dump()
    updated = store.patch(
        "homework",
        "submission",
        attempt_id,
        {
            "status": "graded",
            "grade": patch.get("grade"),
            "teacherComment": patch.get("comment") or patch.get("teacherComment", ""),
            "classInsight": patch.get("classInsight", ""),
            "gradedAt": utc_now_iso(),
        },
    )
    return ok({"success": bool(updated), "gradedAt": utc_now_iso()})


@router.post("/homework")
async def create_homework(payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    homework_id = str(data.get("id") or make_record_key("hw"))
    blocks = data.get("blocks") or []
    questions_from_blocks = _blocks_to_questions(blocks) if blocks else []
    questions = data.get("questions") or questions_from_blocks
    homework = {
        **{k: v for k, v in data.items() if k not in ("questions", "blocks", "id", "status", "grade", "teacherComment", "diagnosis", "submittedAnswers", "submittedFile")},
        "id": homework_id,
        "subjectId": data.get("subjectId") or "GENERAL",
        "subjectName": data.get("subject") or data.get("subjectName") or "General",
        "type": data.get("type") or "daily",
        "title": data.get("title") or "Untitled homework",
        "deadline": data.get("deadline") or "",
        "urgent": bool(data.get("urgent", False)),
        "status": "unsubmitted",
        "grade": None,
        "teacherComment": "",
        "diagnosis": None,
        "questions": questions,
        "blocks": blocks,
        "submittedAnswers": {},
        "submittedFile": None,
    }
    return ok(JsonStore(db).upsert("homework", "homework", homework_id, homework))


@router.get("/homework/{homework_id}")
async def get_homework_details(homework_id: str, userId: str = "guest_user", db: Session = Depends(get_db)):
    store = JsonStore(db)
    homework = store.get_payload("homework", "homework", homework_id) or {
        "id": homework_id,
        "title": "Homework not found",
        "questions": [],
        "status": "unsubmitted",
    }
    submission = store.get_payload("homework", "submission", f"{homework_id}:{userId}", owner_id=userId)
    if submission:
        homework.update(
            {
                "status": submission.get("status", "submitted"),
                "submittedAnswers": submission.get("answers", {}),
                "submittedFile": submission.get("file"),
                "grade": submission.get("grade"),
                "teacherComment": submission.get("teacherComment", ""),
                "diagnosis": submission.get("diagnosis"),
            }
        )
    return ok(homework)


@router.post("/homework/{homework_id}/submit")
async def submit_homework(homework_id: str, payload: FreePayload, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    auth_username = _require_auth_user(authorization)
    data = payload.model_dump()
    # Use authenticated user's ID, ignore client-provided identity
    student_id = auth_username
    homework = JsonStore(db).get_payload("homework", "homework", homework_id) or {}
    submission_id = str(data.get("id") or f"{homework_id}:{student_id}")
    submission = {
        "id": submission_id,
        "studentId": student_id,
        "studentName": data.get("studentName") or student_id,
        "className": data.get("className") or "",
        "homeworkId": homework_id,
        "homeworkTitle": homework.get("title", ""),
        "submittedAt": utc_now_iso(),
        "answers": data.get("answers", {}),
        "file": data.get("file"),
        "status": "pending",
        "grade": None,
        "teacherComment": "",
        "diagnosis": data.get("diagnosis"),
    }
    JsonStore(db).upsert("homework", "submission", submission_id, submission, owner_id=str(student_id), status="pending")
    try:
        await publish_learning_activity_safely(db, {
            "student_id": str(student_id), "source_module": "homework", "content_type": "HOMEWORK",
            "content_id": homework_id, "attempt_id": submission_id,
            "result_payload": {"status": "submitted", "answer_count": len(submission["answers"]) if isinstance(submission["answers"], dict) else 1},
            "status": "COMPLETED", "occurred_at": submission["submittedAt"],
        })
    except Exception:
        pass
    return ok({"success": True, "submittedAt": submission["submittedAt"], "attemptId": submission_id})


@router.post("/homework/{homework_id}/diagnose")
async def diagnose_homework(homework_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    student_id = data.get("userId") or data.get("studentId") or data.get("username") or "guest_user"
    answers = data.get("answers", {})
    store = JsonStore(db)
    homework = store.get_payload("homework", "homework", homework_id) or {}
    questions = homework.get("questions") or []

    # 兜底诊断逻辑
    text = " ".join(str(value) for value in answers.values()) if isinstance(answers, dict) else str(answers)
    base = min(95, max(55, 60 + len(text) // 20))
    fallback_diagnosis = {
        "scores": {"alina": base, "codeninja": min(100, base + 3), "profx": max(0, base - 2)},
        "alinaMsg": "学习路线诊断已生成（兜底）。",
        "codeninjaMsg": "代码质量信号已记录（兜底）。",
        "profxMsg": "概念复习建议已生成（兜底）。",
        "generatedAt": utc_now_iso(),
        "source": "fallback",
    }

    # 构建 AI prompt
    prompt_parts = ["你是多智能体协同作业诊断系统。请基于以下学生作业作答数据生成三维度诊断。\n"]
    for q in questions:
        qid = q.get("id", "")
        prompt_parts.append(
            f"题目: {q.get('title', '')}\n"
            f"类型: {q.get('type', '')}\n"
            f"正确答案: {q.get('correctAnswer', q.get('correctAnswers', ''))}\n"
            f"学生答案: {answers.get(qid, '未作答')}\n"
        )
    prompt_parts.append(
        "\n请返回JSON格式（不要包含其他文本）:\n"
        '{"scores": {"alina": 0-100, "codeninja": 0-100, "profx": 0-100}, '
        '"alinaMsg": "Alina维度评语", "codeninjaMsg": "CodeNinja维度评语", "profxMsg": "Prof.X维度评语"}'
    )
    prompt = "\n".join(prompt_parts)

    # 尝试调用真实 AI
    diagnosis = fallback_diagnosis
    try:
        model_id = Settings().LLM_MODEL_DEFAULT
        response = build_chat_model(model_id, temperature=0.3).invoke(prompt)
        content = getattr(response, "content", str(response))
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            # 验证AI返回的JSON格式
            if "scores" in parsed and isinstance(parsed["scores"], dict):
                scores = parsed["scores"]
                # 验证scores包含必要的键且值为数字
                required_keys = ["alina", "codeninja", "profx"]
                if all(key in scores and isinstance(scores[key], (int, float)) for key in required_keys):
                    # 验证分数范围在0-100之间
                    if all(0 <= scores[key] <= 100 for key in required_keys):
                        diagnosis = {**parsed, "generatedAt": utc_now_iso(), "source": "ai"}
    except Exception as e:
        import logging
        logging.exception("AI call failed: %s", e)  # 使用兜底诊断

    # 持久化诊断记录
    record_id = make_record_key("diag")
    store.upsert("homework", "diagnosis", record_id, {"id": record_id, "homeworkId": homework_id, **diagnosis})

    # 回写到 submission 记录
    submission_id = f"{homework_id}:{student_id}"
    existing = store.get_payload("homework", "submission", submission_id)
    if existing:
        existing["diagnosis"] = diagnosis
        store.upsert(
            "homework", "submission", submission_id, existing,
            owner_id=student_id, status=existing.get("status", "pending"),
        )

    return ok(diagnosis)
