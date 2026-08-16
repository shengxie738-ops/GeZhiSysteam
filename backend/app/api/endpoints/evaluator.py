from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.miniprogram_response import api_response, page_items
from app.repositories.json_store import JsonStore, make_record_key
from app.utils.datetime import utc_now_iso

router = APIRouter()


DEFAULT_QUIZ = {
    "id": "quiz_001",
    "title": "Binary Tree Checkpoint",
    "topicTags": ["data-structures", "binary-tree"],
    "difficulty": 3,
    "estimatedMinutes": 15,
    "questions": [
        {
            "id": "q_001",
            "type": "choice",
            "content": "Which order describes preorder traversal of a binary tree?",
            "options": [
                {"key": "A", "text": "root-left-right"},
                {"key": "B", "text": "left-root-right"},
                {"key": "C", "text": "left-right-root"},
                {"key": "D", "text": "right-root-left"},
            ],
            "correctAnswer": "A",
            "explanation": "Preorder visits the root before the left and right subtrees.",
            "topicTags": ["binary-tree", "traversal"],
        },
        {
            "id": "q_002",
            "type": "judge",
            "content": "A full binary tree is always a complete binary tree.",
            "correctAnswer": True,
            "explanation": "In this checkpoint definition, a full tree fills every level.",
            "topicTags": ["binary-tree"],
        },
    ],
}


class AttemptCreate(BaseModel):
    quizId: str
    userId: str = "guest_user"


class AttemptSubmit(BaseModel):
    answers: dict[str, Any]


def _ensure_quizzes(store: JsonStore) -> list[dict[str, Any]]:
    quizzes = store.list_payloads("evaluator", "quiz")
    if quizzes:
        return quizzes
    stored = store.upsert("evaluator", "quiz", DEFAULT_QUIZ["id"], DEFAULT_QUIZ, status="active")
    return [stored]


def _get_quiz(store: JsonStore, quiz_id: str) -> dict[str, Any] | None:
    for quiz in _ensure_quizzes(store):
        if quiz.get("id") == quiz_id:
            return quiz
    return None


def _quiz_summary(quiz: dict[str, Any]) -> dict[str, Any]:
    questions = quiz.get("questions") or []
    return {
        "id": quiz.get("id"),
        "title": quiz.get("title"),
        "topicTags": quiz.get("topicTags") or [],
        "difficulty": quiz.get("difficulty"),
        "estimatedMinutes": quiz.get("estimatedMinutes"),
        "questionCount": len(questions),
    }


def _question_for_attempt(question: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in question.items() if key not in ("correctAnswer", "explanation")}


@router.get("/evaluator/quizzes")
async def list_quizzes(
    tag: str = "",
    difficulty: int | None = None,
    cursor: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
):
    quizzes = [_quiz_summary(quiz) for quiz in _ensure_quizzes(JsonStore(db))]
    if tag:
        quizzes = [quiz for quiz in quizzes if tag in (quiz.get("topicTags") or [])]
    if difficulty is not None:
        quizzes = [quiz for quiz in quizzes if int(quiz.get("difficulty") or 0) == difficulty]
    return api_response(page_items(quizzes, cursor=cursor or None, limit=limit))


@router.post("/evaluator/attempts")
async def create_attempt(payload: AttemptCreate, db: Session = Depends(get_db)):
    store = JsonStore(db)
    quiz = _get_quiz(store, payload.quizId)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    attempt_id = make_record_key("attempt")
    attempt = {
        "id": attempt_id,
        "quizId": payload.quizId,
        "userId": payload.userId,
        "status": "in_progress",
        "answers": {},
        "createdAt": utc_now_iso(),
    }
    store.upsert("evaluator", "attempt", attempt_id, attempt, owner_id=payload.userId, status="in_progress")
    return api_response(
        {
            "id": attempt_id,
            "quizId": payload.quizId,
            "status": "in_progress",
            "createdAt": attempt["createdAt"],
        }
    )


@router.get("/evaluator/attempts/{attempt_id}")
async def get_attempt(attempt_id: str, db: Session = Depends(get_db)):
    store = JsonStore(db)
    attempt = store.get_payload("evaluator", "attempt", attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    quiz = _get_quiz(store, str(attempt.get("quizId")))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = [_question_for_attempt(question) for question in quiz.get("questions", [])]
    return api_response(
        {
            "id": attempt_id,
            "quizId": quiz["id"],
            "title": quiz["title"],
            "topicTags": quiz.get("topicTags") or [],
            "status": attempt["status"],
            "questions": questions,
        }
    )


@router.post("/evaluator/attempts/{attempt_id}/submit")
async def submit_attempt(attempt_id: str, payload: AttemptSubmit, db: Session = Depends(get_db)):
    store = JsonStore(db)
    attempt = store.get_payload("evaluator", "attempt", attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    quiz = _get_quiz(store, str(attempt.get("quizId")))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = quiz.get("questions", [])
    correct_count = sum(
        1
        for question in questions
        if payload.answers.get(str(question.get("id"))) == question.get("correctAnswer")
    )
    total_questions = len(questions)
    score = int((correct_count / max(1, total_questions)) * 100)
    result_questions = [
        {
            **question,
            "userAnswer": payload.answers.get(str(question.get("id"))),
            "isCorrect": payload.answers.get(str(question.get("id"))) == question.get("correctAnswer"),
        }
        for question in questions
    ]
    result = {
        "attemptId": attempt_id,
        "quizId": quiz["id"],
        "title": quiz["title"],
        "score": score,
        "totalQuestions": total_questions,
        "correctCount": correct_count,
        "timeTaken": "00:00",
        "weakTags": [],
        "questions": result_questions,
    }
    submitted_at = utc_now_iso()
    attempt.update(
        {
            "status": "submitted",
            "answers": payload.answers,
            "result": result,
            "submittedAt": submitted_at,
        }
    )
    store.upsert(
        "evaluator",
        "attempt",
        attempt_id,
        attempt,
        owner_id=str(attempt.get("userId") or ""),
        status="submitted",
    )
    return api_response(
        {
            "attemptId": attempt_id,
            "quizId": quiz["id"],
            "status": "submitted",
            "score": score,
            "correctCount": correct_count,
            "totalQuestions": total_questions,
            "submittedAt": submitted_at,
        }
    )


@router.get("/evaluator/attempts/{attempt_id}/result")
async def get_attempt_result(attempt_id: str, db: Session = Depends(get_db)):
    attempt = JsonStore(db).get_payload("evaluator", "attempt", attempt_id)
    if not attempt or not attempt.get("result"):
        raise HTTPException(status_code=404, detail="Result not found")
    return api_response(attempt["result"])
