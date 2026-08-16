import json
import re
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.core.miniprogram_response import api_response, is_miniprogram_client
from app.core.responses import ok
from app.repositories.json_store import JsonStore, make_record_key
from app.services.code_sandbox import CodeSandbox
from app.services.learning_diagnosis.activity_listener import publish_learning_activity_safely
from app.services.model_registry import build_chat_model, has_model
from app.utils.datetime import utc_now_iso

router = APIRouter()


class FreePayload(BaseModel):
    class Config:
        extra = "allow"


def _exam_status(exam: dict[str, Any]) -> str:
    return exam.get("status") or "draft"


def _as_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, (list, tuple, set)):
        return "、".join(_as_text(item) for item in value if _as_text(item))
    text = str(value).strip()
    return text or default


def _analysis_path(value: Any) -> list[str]:
    if isinstance(value, list):
        path = [_as_text(item) for item in value]
    else:
        path = re.split(r"\s*(?:->|→|,|，|、|\n)\s*", _as_text(value))
    path = [item for item in path if item]
    return path or ["复盘原题", "补齐概念", "同类练习", "隔天重测"]


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    elif "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.find("{"): cleaned.rfind("}") + 1]
    try:
        parsed = json.loads(cleaned)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_ai_analysis(
    raw: Any,
    mistake_id: str,
    *,
    model_id: str,
    agent_id: str = "agent_mistake_analyst",
    agent_name: str = "错题分析师",
    fallback_text: str = "",
) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else _extract_json_object(_as_text(raw))
    data = data or {}
    diagnosis = _as_text(data.get("diagnosis"), _as_text(raw, fallback_text))
    return {
        "mistakeId": mistake_id,
        "diagnosis": diagnosis,
        "concept": _as_text(data.get("concept"), "请围绕题目涉及的核心概念重新比较错误答案与正确答案。"),
        "practice": _as_text(data.get("practice"), "完成 3 道同知识点变式题，并记录每一步订正依据。"),
        "path": _analysis_path(data.get("path")),
        "source": "ai",
        "model": model_id,
        "agentId": agent_id,
        "agentName": agent_name,
        "generatedAt": utc_now_iso(),
    }


def _build_mistake_ai_prompt(
    mistake_id: str,
    mistake: dict[str, Any],
    payload: dict[str, Any],
    *,
    agent_name: str = "错题分析师",
    agent_prompt: str = "",
) -> str:
    fields = {
        "题目ID": mistake_id,
        "学生": mistake.get("studentName") or payload.get("studentName") or payload.get("userId") or mistake.get("studentId"),
        "科目": mistake.get("subject") or payload.get("subject"),
        "题型": mistake.get("questionType") or payload.get("questionType"),
        "题目": mistake.get("questionTitle") or payload.get("questionTitle"),
        "学生答案": mistake.get("studentAnswer") or payload.get("studentAnswer"),
        "正确答案": mistake.get("correctAnswer") or payload.get("correctAnswer"),
        "系统记录错因": mistake.get("errorReason") or payload.get("errorReason"),
        "知识标签": mistake.get("knowledgeTags") or payload.get("knowledgeTags"),
        "错误次数": mistake.get("wrongCount") or payload.get("wrongCount"),
    }
    context = "\n".join(f"- {key}: {_as_text(value, '未提供')}" for key, value in fields.items())
    agent_instruction = (
        f"\n\n当前执行分析的 Agent 是「{agent_name}」。"
        f"\n该 Agent 的系统指令是：{agent_prompt}"
        if agent_prompt else
        f"\n\n当前执行分析的 Agent 是「{agent_name}」。"
    )
    return (
        "你是学生端错题本的 AI 错因分析助手。请基于下面真实错题数据生成个性化分析，"
        "不要输出模板化英文，不要编造题目之外的学生信息。\n\n"
        f"{context}\n\n"
        f"{agent_instruction}\n\n"
        "请只返回 JSON 对象，字段必须是：\n"
        "{\n"
        '  "diagnosis": "指出学生错在什么认知环节，结合他的错误答案",\n'
        '  "concept": "解释相关知识点，并对比正确答案",\n'
        '  "practice": "给出具体订正练习建议",\n'
        '  "path": ["复盘原题", "补齐概念", "同类练习", "隔天重测"]\n'
        "}\n"
        "每个字段使用中文，内容可以多句，但保持面向学生。"
    )


def _fallback_mistake_ai_analysis(
    mistake_id: str,
    mistake: dict[str, Any],
    error: Exception | None = None,
    *,
    agent_id: str = "agent_mistake_analyst",
    agent_name: str = "错题分析师",
) -> dict[str, Any]:
    tags = _as_text(mistake.get("knowledgeTags"), "相关知识点")
    wrong_answer = _as_text(mistake.get("studentAnswer"), "原答案")
    correct_answer = _as_text(mistake.get("correctAnswer"), "正确答案")
    reason = _as_text(mistake.get("errorReason"), "系统记录显示该题需要重新梳理概念边界。")
    return {
        "mistakeId": mistake_id,
        "diagnosis": f"你的错误主要集中在 {tags} 的判断条件上。结合答案“{wrong_answer}”，需要先回到题干确认真正考查的对象。",
        "concept": f"{reason} 复习时请把错误答案与“{correct_answer}”逐项对照，写出两者差异。",
        "practice": "先独立重做原题，再完成 3 道同知识点变式题；每题后记录触发条件、解题依据和易混点。",
        "path": ["复盘原题", "补齐概念", "同类练习", "隔天重测"],
        "source": "fallback",
        "agentId": agent_id,
        "agentName": agent_name,
        "modelError": str(error) if error else "",
        "generatedAt": utc_now_iso(),
    }


@router.get("/exams/student/{user_id}/overview")
async def get_student_exam_overview(user_id: str, db: Session = Depends(get_db)):
    store = JsonStore(db)
    exams = store.list_payloads("exams", "exam")
    attempts = store.list_payloads("exams", "attempt", owner_id=user_id)
    attempt_by_exam = {item.get("examId"): item for item in attempts}
    exam_views = []
    for exam in exams:
        item = dict(exam)
        attempt = attempt_by_exam.get(exam.get("id"))
        if attempt:
            item["attemptId"] = attempt.get("id")
            item["score"] = attempt.get("score")
            item["submittedAt"] = attempt.get("submittedAt")
            if attempt.get("status") == "submitted":
                item["status"] = "completed"
        exam_views.append(item)
    summary = {
        "upcoming": len([item for item in exam_views if item.get("status") in ("upcoming", "scheduled")]),
        "active": len([item for item in exam_views if item.get("status") in ("active", "running")]),
        "completed": len([item for item in exam_views if item.get("status") == "completed"]),
        "programming": len([item for item in exam_views if item.get("programming") or item.get("programmingProblems")]),
    }
    return ok({"summary": summary, "exams": exam_views, "waitingSubjects": []})


@router.get("/exams/teacher/dashboard")
async def get_teacher_exam_dashboard(db: Session = Depends(get_db)):
    store = JsonStore(db)
    exams = store.list_payloads("exams", "exam")
    attempts = store.list_payloads("exams", "attempt")
    dashboard_exams = []
    for exam in exams:
        related = [item for item in attempts if item.get("examId") == exam.get("id")]
        dashboard_exams.append(
            {
                "id": exam.get("id"),
                "title": exam.get("title"),
                "subject": exam.get("subject"),
                "status": _exam_status(exam),
                "startsAt": exam.get("startsAt"),
                "durationMinutes": exam.get("durationMinutes"),
                "entrants": len(related),
                "submitted": len([item for item in related if item.get("status") == "submitted"]),
                "abnormal": len([item for item in related if item.get("abnormal")]),
            }
        )
    return ok(
        {
            "summary": {
                "today": len(exams),
                "draft": len([item for item in exams if _exam_status(item) == "draft"]),
                "running": len([item for item in exams if _exam_status(item) in ("active", "running")]),
                "review": len([item for item in attempts if item.get("status") == "submitted"]),
            },
            "exams": dashboard_exams,
            "submissions": [
                {
                    "id": item.get("id"),
                    "student": item.get("studentName") or item.get("studentId"),
                    "exam": item.get("examTitle", ""),
                    "status": item.get("status", "started"),
                    "progress": item.get("progress", 0),
                    "lastSavedAt": item.get("lastSavedAt"),
                    "abnormal": item.get("abnormal", False),
                }
                for item in attempts
            ],
        }
    )


@router.get("/exams/teacher/error-analysis")
async def get_teacher_error_analysis(db: Session = Depends(get_db)):
    mistakes = JsonStore(db).list_payloads("exams", "mistake")
    tags: dict[str, int] = {}
    for mistake in mistakes:
        for tag in mistake.get("knowledgeTags", []) or []:
            tags[str(tag)] = tags.get(str(tag), 0) + 1
    weak = [
        {"tag": tag, "errorRate": min(100, count * 10), "questionCount": count, "suggestion": "Create a review task."}
        for tag, count in sorted(tags.items(), key=lambda item: item[1], reverse=True)
    ]
    return ok(
        {
            "summary": {
                "highRiskQuestions": len(mistakes),
                "averageErrorRate": weak[0]["errorRate"] if weak else 0,
                "affectedStudents": len({item.get("studentId") for item in mistakes}),
                "generatedReviewTasks": len(JsonStore(db).list_payloads("exams", "review_task")),
            },
            "weakKnowledge": weak,
            "questionRanking": mistakes,
        }
    )


@router.get("/exams/questions/{question_id}/wrong-students")
async def get_wrong_students(question_id: str, db: Session = Depends(get_db)):
    mistakes = [
        item for item in JsonStore(db).list_payloads("exams", "mistake")
        if item.get("questionId") == question_id or item.get("id") == question_id
    ]
    return ok(
        [
            {
                "id": item.get("studentId") or item.get("id"),
                "name": item.get("studentName") or item.get("studentId") or "unknown",
                "className": item.get("className", ""),
                "answer": item.get("studentAnswer", ""),
                "score": item.get("score", 0),
                "status": "pending",
            }
            for item in mistakes
        ]
    )


@router.post("/exams/questions/{question_id}/review-task")
async def create_review_task(question_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    task_id = make_record_key("review")
    task = {"id": task_id, "taskId": task_id, "questionId": question_id, "status": "created", "createdAt": utc_now_iso(), **data}
    JsonStore(db).upsert("exams", "review_task", task_id, task)
    return ok({"taskId": task_id, "status": "created", "createdAt": task["createdAt"]})


@router.post("/exams")
async def create_exam(payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    exam_id = str(data.get("id") or make_record_key("exam"))
    exam = {
        **{k: v for k, v in data.items() if k not in ("id", "title", "subject", "status", "startsAt", "durationMinutes", "location", "rules", "questionTypes", "programmingProblems", "objectiveQuestions")},
        "id": exam_id,
        "title": data.get("title") or "Untitled exam",
        "subject": data.get("subject") or "",
        "status": data.get("status") or "draft",
        "startsAt": data.get("startsAt"),
        "durationMinutes": data.get("durationMinutes", 60),
        "location": data.get("location") or "online",
        "rules": data.get("rules") or [],
        "questionTypes": data.get("questionTypes") or [],
        "programmingProblems": data.get("programmingProblems") or [],
        "objectiveQuestions": data.get("objectiveQuestions") or [],
    }
    return ok(JsonStore(db).upsert("exams", "exam", exam_id, exam, status=exam["status"]))


@router.get("/exams/{exam_id}")
async def get_exam_detail(exam_id: str, user_id: str = "guest_user", db: Session = Depends(get_db)):
    exam = JsonStore(db).get_payload("exams", "exam", exam_id) or {
        "id": exam_id,
        "title": "Exam not found",
        "status": "draft",
        "programmingProblems": [],
        "objectiveQuestions": [],
    }
    attempt = JsonStore(db).get_payload("exams", "attempt", f"{exam_id}:{user_id}", owner_id=user_id)
    if attempt:
        exam["attemptId"] = attempt.get("id")
        exam["answers"] = attempt.get("answers", {})
    return ok(exam)


@router.post("/exams/{exam_id}/attempts")
async def start_exam_attempt(exam_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    user_id = str(data.get("userId") or data.get("studentId") or data.get("username") or "guest_user")
    exam = JsonStore(db).get_payload("exams", "exam", exam_id) or {}
    attempt_id = str(data.get("attemptId") or f"{exam_id}:{user_id}")
    attempt = {
        "id": attempt_id,
        "attemptId": attempt_id,
        "examId": exam_id,
        "examTitle": exam.get("title", ""),
        "studentId": user_id,
        "studentName": data.get("studentName") or user_id,
        "status": "started",
        "answers": {},
        "progress": 0,
        "startedAt": utc_now_iso(),
    }
    JsonStore(db).upsert("exams", "attempt", attempt_id, attempt, owner_id=user_id, status="started")
    return ok({"attemptId": attempt_id, "startedAt": attempt["startedAt"], "status": "started"})


@router.put("/exams/attempts/{attempt_id}/answers")
async def save_answer(attempt_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    store = JsonStore(db)
    attempt = store.get_payload("exams", "attempt", attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
        
    exam = store.get_payload("exams", "exam", attempt.get("examId"))
    if exam and exam.get("startsAt"):
        try:
            starts_at = datetime.fromisoformat(exam["startsAt"].replace("Z", "+00:00"))
            duration = int(exam.get("durationMinutes", 60))
            ends_at = starts_at + timedelta(minutes=duration, seconds=30)
            if datetime.now(starts_at.tzinfo) > ends_at:
                raise HTTPException(status_code=403, detail="考试已结束，无法继续保存答案")
        except (ValueError, AttributeError, TypeError):
            pass

    data = payload.model_dump()
    answers = attempt.get("answers") or {}
    question_id = data.get("questionId") or data.get("id")
    if question_id:
        answers[str(question_id)] = data.get("answer")
    else:
        answers.update(data.get("answers", {}))
    attempt.update({"answers": answers, "lastSavedAt": utc_now_iso(), "progress": data.get("progress", attempt.get("progress", 0))})
    store.upsert("exams", "attempt", attempt_id, attempt, owner_id=attempt.get("studentId", ""), status=attempt.get("status", "started"))
    return ok({"status": "saved", "savedAt": attempt["lastSavedAt"]})


@router.post("/exams/attempts/{attempt_id}/submit")
async def submit_attempt(attempt_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    store = JsonStore(db)
    attempt = store.get_payload("exams", "attempt", attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
        
    exam = store.get_payload("exams", "exam", attempt.get("examId"))
    if exam and exam.get("startsAt"):
        try:
            starts_at = datetime.fromisoformat(exam["startsAt"].replace("Z", "+00:00"))
            duration = int(exam.get("durationMinutes", 60))
            ends_at = starts_at + timedelta(minutes=duration, seconds=120)
            if datetime.now(starts_at.tzinfo) > ends_at:
                attempt["abnormal"] = True
        except (ValueError, AttributeError, TypeError):
            pass

    data = payload.model_dump()
    # 白名单提取：仅允许客户端更新 answers 字段，保护关键字段不被篡改
    if "answers" in data:
        attempt["answers"] = data["answers"]
    attempt.update({"status": "submitted", "submittedAt": utc_now_iso(), "progress": 100})

    answers = attempt.get("answers", {})
    objective_questions = (exam or {}).get("objectiveQuestions") or []

    # 真实判分：逐题比对答案
    objective_score = 0
    correct_count = 0
    wrong_questions: list[dict[str, Any]] = []

    for q in objective_questions:
        qid = q.get("id")
        if not qid:
            continue
        student_answer = str(answers.get(qid, "")).strip()
        qtype = q.get("type", "choice")
        is_correct = False

        if qtype == "choice":
            is_correct = student_answer.upper() == str(q.get("correctAnswer", "")).strip().upper()
        elif qtype == "blank":
            correct_answers = q.get("correctAnswers") or []
            if correct_answers:
                is_correct = all(
                    str(answers.get(f"{qid}_{i}") or answers.get(qid, "")).strip().lower() == str(correct_answers[i]).strip().lower()
                    for i in range(len(correct_answers))
                )
        elif qtype == "programming":
            # 编程题暂不在此处判分，由专门的评测端点处理
            pass

        if is_correct:
            objective_score += q.get("score", 4)
            correct_count += 1
        elif student_answer:
            wrong_questions.append({
                "questionId": qid,
                "questionTitle": q.get("title", ""),
                "questionType": qtype,
                "studentAnswer": student_answer,
                "correctAnswer": q.get("correctAnswer", q.get("correctAnswers", "")),
                "subject": (exam or {}).get("subject", ""),
                "knowledgeTags": q.get("knowledgeTags") or [],
            })

    attempt["objectiveScore"] = objective_score
    attempt["correctCount"] = correct_count
    attempt["wrongCount"] = len(wrong_questions)

    store.upsert("exams", "attempt", attempt_id, attempt, owner_id=attempt.get("studentId", ""), status="submitted")

    # 自动生成错题记录
    student_id = attempt.get("studentId", "")
    for wq in wrong_questions:
        existing_mistakes = [
            m for m in store.list_payloads("exams", "mistake", owner_id=student_id)
            if m.get("questionId") == wq["questionId"] and m.get("examId") == (exam or {}).get("id")
        ]
        if existing_mistakes:
            # 累加错误次数
            m = existing_mistakes[0]
            m["wrongCount"] = m.get("wrongCount", 1) + 1
            m["lastWrongAt"] = utc_now_iso()
            m["studentAnswer"] = wq["studentAnswer"]
            store.upsert("exams", "mistake", m["id"], m, owner_id=student_id)
        else:
            # 新增错题记录
            mistake_id = make_record_key("mistake")
            mistake = {
                "id": mistake_id,
                "studentId": student_id,
                "studentName": attempt.get("studentName", ""),
                "examId": (exam or {}).get("id", ""),
                "examTitle": (exam or {}).get("title", ""),
                "subject": wq["subject"],
                "questionId": wq["questionId"],
                "questionType": wq["questionType"],
                "questionTitle": wq["questionTitle"],
                "studentAnswer": wq["studentAnswer"],
                "correctAnswer": str(wq["correctAnswer"]),
                "errorReason": "",
                "knowledgeTags": wq["knowledgeTags"],
                "wrongCount": 1,
                "mastered": False,
                "lastWrongAt": utc_now_iso(),
                "createdAt": utc_now_iso(),
            }
            store.upsert("exams", "mistake", mistake_id, mistake, owner_id=student_id)

    # 学习诊断是旁路消费者；其失败不能改变考试已提交的业务结果。
    try:
        await publish_learning_activity_safely(db, {
            "student_id": student_id,
            "source_module": "exams",
            "content_type": "EXAM",
            "content_id": str((exam or {}).get("id") or attempt.get("examId") or ""),
            "attempt_id": attempt_id,
            "result_payload": {"score": objective_score, "correct_count": correct_count, "wrong_count": len(wrong_questions), "status": "submitted"},
            "status": "COMPLETED",
            "occurred_at": attempt["submittedAt"],
        })
        for question in objective_questions:
            question_id = str(question.get("id") or "")
            if not question_id or question_id not in answers:
                continue
            await publish_learning_activity_safely(db, {
                "student_id": student_id, "source_module": "exams", "content_type": "EXAM_QUESTION",
                "content_id": question_id, "attempt_id": f"{attempt_id}:{question_id}",
                "result_payload": {"answer": answers.get(question_id), "score": question.get("score", 0) if question_id not in {item['questionId'] for item in wrong_questions} else 0},
                "status": "COMPLETED", "occurred_at": attempt["submittedAt"],
            })
    except Exception:
        pass

    return ok({
        "status": "submitted",
        "submittedAt": attempt["submittedAt"],
        "objectiveScore": objective_score,
        "correctCount": correct_count,
        "wrongCount": len(wrong_questions),
        "programmingStatus": "pending_judge",
    })


@router.post("/exams/{exam_id}/programming-problems")
async def create_programming_problem(exam_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    problem_id = str(data.get("id") or make_record_key("prog"))
    problem = {"id": problem_id, "examId": exam_id, **data}
    store = JsonStore(db)
    exam = store.get_payload("exams", "exam", exam_id)
    if exam:
        problems = exam.get("programmingProblems") or []
        problems.append(problem)
        exam["programmingProblems"] = problems
        store.upsert("exams", "exam", exam_id, exam, status=exam.get("status", "draft"))
    return ok(problem)


@router.get("/exams/{exam_id}/submissions")
async def get_exam_submissions(exam_id: str, db: Session = Depends(get_db)):
    attempts = [item for item in JsonStore(db).list_payloads("exams", "attempt") if item.get("examId") == exam_id]
    return ok(attempts)


@router.post("/exams/attempts/{attempt_id}/judge-programming")
async def judge_programming(attempt_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    """对提交中的编程题进行自动评测"""
    store = JsonStore(db)
    attempt = store.get_payload("exams", "attempt", attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    exam = store.get_payload("exams", "exam", attempt.get("examId"))
    programming_problems = (exam or {}).get("programmingProblems") or []
    answers = attempt.get("answers") or {}

    sandbox = CodeSandbox()
    programming_results: list[dict[str, Any]] = []
    programming_score = 0

    for problem in programming_problems:
        pid = problem.get("id")
        if not pid:
            continue
        student_code = str(answers.get(pid, ""))
        language = problem.get("language", "python")
        test_cases = problem.get("testCases") or []

        if not student_code.strip():
            programming_results.append({
                "problemId": pid,
                "passed": 0,
                "total": len(test_cases),
                "status": "no_answer",
            })
            continue

        result = sandbox.run(student_code, language, test_cases)
        if result.get("passed", 0) > 0 and result.get("total", 0) > 0:
            score_per_case = (problem.get("score", 20)) / result["total"]
            programming_score += int(result["passed"] * score_per_case)

        programming_results.append({
            "problemId": pid,
            "passed": result.get("passed", 0),
            "total": result.get("total", 0),
            "status": "accepted" if result.get("passed") == result.get("total") else "partial" if result.get("passed", 0) > 0 else "wrong_answer",
            "details": result.get("results", []),
            "error": result.get("error"),
        })

    attempt["programmingScore"] = programming_score
    attempt["programmingResults"] = programming_results
    attempt["totalScore"] = (attempt.get("objectiveScore") or 0) + programming_score

    store.upsert("exams", "attempt", attempt_id, attempt, owner_id=attempt.get("studentId", ""), status=attempt.get("status", "submitted"))

    return ok({
        "programmingScore": programming_score,
        "totalScore": attempt["totalScore"],
        "results": programming_results,
    })


@router.get("/exams/student/{user_id}/mistakes")
async def get_student_mistakes(
    user_id: str,
    db: Session = Depends(get_db),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
):
    mistakes = JsonStore(db).list_payloads("exams", "mistake", owner_id=user_id)
    data = {
        "summary": {
            "total": len(mistakes),
            "unresolved": len([item for item in mistakes if not item.get("mastered")]),
            "repeated": len([item for item in mistakes if item.get("wrongCount", 0) > 1]),
            "aiAnalyzed": len([item for item in mistakes if item.get("aiAnalysis")]),
        },
        "filters": {"subjects": ["all"], "types": ["all"], "mastery": ["all"]},
        "mistakes": mistakes,
    }
    if is_miniprogram_client(x_gezhi_client):
        return api_response(data)
    return ok(data)


@router.get("/exams/student/{user_id}/review-tasks")
async def get_student_review_tasks(user_id: str, db: Session = Depends(get_db)):
    """获取学生可见的讲评任务（全班任务 + 针对该学生的任务）"""
    store = JsonStore(db)
    all_tasks = store.list_payloads("exams", "review_task")
    # 讲评任务通常面向全班，但也可能针对特定学生
    visible_tasks = [
        task for task in all_tasks
        if not task.get("studentIds")  # 无指定学生 = 全班任务
        or user_id in (task.get("studentIds") or [])
        or user_id == task.get("targetStudentId")
    ]
    return ok({"total": len(visible_tasks), "tasks": visible_tasks})


VALID_STATUS_TRANSITIONS = {
    "draft": ["scheduled"],
    "scheduled": ["running", "draft"],
    "running": ["completed", "scheduled"],
    "completed": ["running"],
}


@router.patch("/exams/{exam_id}/status")
async def update_exam_status(exam_id: str, payload: FreePayload, db: Session = Depends(get_db)):
    """考试状态管理：draft → scheduled → running → completed"""
    store = JsonStore(db)
    exam = store.get_payload("exams", "exam", exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    data = payload.model_dump()
    new_status = data.get("status")
    current_status = exam.get("status", "draft")

    allowed = VALID_STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"不允许的状态转换: {current_status} → {new_status}。允许的转换: {allowed}",
        )

    exam["status"] = new_status
    if new_status == "completed":
        exam["endsAt"] = utc_now_iso()

    store.upsert("exams", "exam", exam_id, exam)
    return ok({"id": exam_id, "status": new_status, "updatedAt": utc_now_iso()})


@router.post("/exams/mistakes")
async def create_mistake(
    payload: FreePayload,
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    user_id = str(data.get("userId") or data.get("studentId") or "guest_user")
    question = str(data.get("question") or data.get("questionTitle") or "")
    answer = str(data.get("answer") or data.get("studentAnswer") or "")
    mistake_id = make_record_key("mistake")
    mistake = {
        "id": mistake_id,
        "studentId": user_id,
        "questionTitle": question,
        "problem": question,
        "answer": answer,
        "studentAnswer": answer,
        "correctAnswer": data.get("correctAnswer") or answer,
        "source": data.get("source") or "manual",
        "quizId": data.get("quizId") or "",
        "category": data.get("category") or "data-structures",
        "knowledgeTags": data.get("knowledgeTags") or [],
        "mastered": False,
        "aiAnalysis": None,
        "createdAt": utc_now_iso(),
    }
    stored = JsonStore(db).upsert("exams", "mistake", mistake_id, mistake, owner_id=user_id, status="active")
    if is_miniprogram_client(x_gezhi_client):
        return api_response(stored)
    return ok(stored)


@router.post("/exams/mistakes/{mistake_id}/ai-analysis")
async def request_mistake_ai_analysis(
    mistake_id: str,
    payload: FreePayload,
    db: Session = Depends(get_db),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
):
    store = JsonStore(db)
    mistake = store.get_payload("exams", "mistake", mistake_id)
    data = payload.model_dump()
    context = {**data, **(mistake or {})}
    agent_id = str(data.get("agentId") or "agent_mistake_analyst")
    agent_name = str(data.get("agentName") or "错题分析师")
    agent_prompt = str(data.get("agentPrompt") or "")
    default_model = Settings().LLM_MODEL_DEFAULT
    requested_model = str(data.get("agentModel") or data.get("model") or default_model)
    model_id = requested_model if has_model(requested_model, category="text") else default_model

    try:
        prompt = _build_mistake_ai_prompt(
            mistake_id,
            context,
            data,
            agent_name=agent_name,
            agent_prompt=agent_prompt,
        )
        response = build_chat_model(model_id, temperature=0.1).invoke(prompt)
        analysis = _normalize_ai_analysis(
            getattr(response, "content", response),
            mistake_id,
            model_id=model_id,
            agent_id=agent_id,
            agent_name=agent_name,
        )
    except Exception as error:
        analysis = _fallback_mistake_ai_analysis(
            mistake_id,
            context,
            error,
            agent_id=agent_id,
            agent_name=agent_name,
        )

    if mistake:
        mistake["aiAnalysis"] = analysis
        store.upsert("exams", "mistake", mistake_id, mistake, owner_id=mistake.get("studentId", ""))
    if is_miniprogram_client(x_gezhi_client):
        return api_response(analysis)
    return ok(analysis)


@router.patch("/exams/mistakes/{mistake_id}")
async def update_mistake(
    mistake_id: str,
    payload: FreePayload,
    db: Session = Depends(get_db),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
):
    updated = JsonStore(db).patch("exams", "mistake", mistake_id, {**payload.model_dump(), "updatedAt": utc_now_iso()})
    if updated is None:
        raise HTTPException(status_code=404, detail="Mistake not found")
    if bool(updated.get("mastered")):
        try:
            await publish_learning_activity_safely(db, {
                "student_id": str(updated.get("studentId") or "guest_user"), "source_module": "exams",
                "content_type": "WRONG_QUESTION", "content_id": str(updated.get("questionId") or mistake_id),
                "attempt_id": f"correction:{mistake_id}:{updated.get('updatedAt')}",
                "result_payload": {"passed": True, "score": 100, "mastered": True, "mistake_id": mistake_id},
                "status": "COMPLETED", "occurred_at": updated.get("updatedAt") or utc_now_iso(),
            })
        except Exception:
            pass
    if is_miniprogram_client(x_gezhi_client):
        return api_response(updated)
    return ok(updated)
