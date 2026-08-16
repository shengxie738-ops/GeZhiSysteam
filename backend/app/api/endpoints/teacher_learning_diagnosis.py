from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import ok
from app.core.security import decode_access_token
from app.schemas.teacher_learning_diagnosis import ReviewNoteRequest, ReviewStateRequest, WatchFlagRequest
from app.services.learning_diagnosis.teacher_review_service import TeacherLearningDiagnosisReviewService

router = APIRouter()


def _teacher(authorization: str | None) -> str:
    if not isinstance(authorization, str) or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    payload = decode_access_token(authorization.split(" ", 1)[1])
    if not payload or payload.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="teacher role required")
    return str(payload["sub"])


@router.get("/teacher/learning-diagnosis/reviews")
async def list_diagnosis_reviews(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
):
    teacher = _teacher(authorization)
    data = TeacherLearningDiagnosisReviewService(db).list_reviews(teacher, status=status, risk_level=risk_level)
    return ok({"reviewer": teacher, **data})


@router.get("/teacher/learning-diagnosis/reviews/{snapshot_id}")
async def get_review_detail(snapshot_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    teacher = _teacher(authorization)
    return ok(TeacherLearningDiagnosisReviewService(db).get_detail(snapshot_id, teacher))


@router.post("/teacher/learning-diagnosis/reviews/{snapshot_id}")
async def review_diagnosis_snapshot(
    snapshot_id: str,
    payload: ReviewStateRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    teacher = _teacher(authorization)
    return ok(TeacherLearningDiagnosisReviewService(db).save_review_state(snapshot_id, teacher, payload))


@router.patch("/teacher/learning-diagnosis/reviews/{snapshot_id}/state")
async def update_review_state(
    snapshot_id: str,
    payload: ReviewStateRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    teacher = _teacher(authorization)
    return ok(TeacherLearningDiagnosisReviewService(db).save_review_state(snapshot_id, teacher, payload))


@router.post("/teacher/learning-diagnosis/reviews/{snapshot_id}/notes")
async def add_review_note(
    snapshot_id: str,
    payload: ReviewNoteRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    teacher = _teacher(authorization)
    return ok(TeacherLearningDiagnosisReviewService(db).add_note(snapshot_id, teacher, payload))


@router.put("/teacher/learning-diagnosis/watch-flags/{student_id}")
async def upsert_watch_flag(
    student_id: str,
    payload: WatchFlagRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    teacher = _teacher(authorization)
    return ok(TeacherLearningDiagnosisReviewService(db).upsert_watch_flag(student_id, teacher, payload))


@router.delete("/teacher/learning-diagnosis/watch-flags/{student_id}")
async def delete_watch_flag(
    student_id: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    teacher = _teacher(authorization)
    return ok(TeacherLearningDiagnosisReviewService(db).delete_watch_flag(student_id, teacher))


@router.get("/teacher/learning-diagnosis/weak-points")
async def list_weak_points(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    _teacher(authorization)
    return ok(TeacherLearningDiagnosisReviewService(db).weak_points())
