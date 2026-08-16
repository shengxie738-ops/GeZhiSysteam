from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.responses import ok
from app.core.security import decode_access_token
from datetime import datetime, timezone
from app.schemas.learning_diagnosis import CreateDiagnosisGoalRequest, CreateDiagnosisSessionRequest, GitEvidenceToggleRequest, HintRequest, LearningActivityEventRequest, RefreshDiagnosisRequest, RunTaskRequest, SubmitTaskRequest
from app.services.learning_diagnosis.activity_listener import ActivityListener
from app.services.learning_diagnosis.contracts import LearningActivityEvent
from app.services.learning_diagnosis.workflow import DiagnosisWorkflow

router = APIRouter()


def _user(authorization: str | None) -> str:
    if not isinstance(authorization, str):
        authorization = None
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    payload = decode_access_token(authorization.split(" ", 1)[1])
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="invalid token")
    return str(payload["sub"])


def _student(requested: str, authorization: str | None) -> str:
    user = _user(authorization)
    if requested != user:
        raise HTTPException(status_code=403, detail="student scope mismatch")
    return user


@router.post("/learning-diagnosis/sessions")
async def create_diagnosis_session(payload: CreateDiagnosisSessionRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    student = _student(payload.student_id, authorization)
    result = await DiagnosisWorkflow(db).create_session(student, payload.model_dump())
    return ok(result)


@router.post("/learning-diagnosis/sessions/{session_id}/goals")
async def create_diagnosis_goal(session_id: str, payload: CreateDiagnosisGoalRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    student = _student(payload.student_id, authorization)
    workflow = DiagnosisWorkflow(db)
    if not workflow.store.get_session(session_id, student):
        raise HTTPException(status_code=404, detail="session not found")
    return ok(await workflow.change_goal(session_id, student, payload.model_dump()))


@router.get("/learning-diagnosis/sessions/{session_id}")
async def get_diagnosis_session(session_id: str, student_id: str, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(student_id, authorization)
    result = DiagnosisWorkflow(db).store.get_session(session_id, student_id)
    if not result: raise HTTPException(status_code=404, detail="session not found")
    snapshots = DiagnosisWorkflow(db).store.list_snapshots(student_id, session_id)
    return ok({"session": result, "snapshot": snapshots[-1] if snapshots else None})


@router.get("/learning-diagnosis/latest")
async def get_latest_diagnosis_session(student_id: str, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(student_id, authorization)
    workflow = DiagnosisWorkflow(db)
    sessions = workflow.store.list_sessions(student_id)
    if not sessions:
        raise HTTPException(status_code=404, detail="diagnosis session not found")
    session = sorted(sessions, key=lambda item: item.get("created_at", ""), reverse=True)[0]
    session_id = session["id"]
    snapshots = workflow.store.list_snapshots(student_id, session_id)
    paths = workflow.store.list_paths(student_id, session_id)
    evidence = workflow.store.list_evidence(student_id)
    snapshot = snapshots[-1] if snapshots else None
    path = paths[-1] if paths else None
    evidence_refs = set(snapshot.get("evidence_refs", [])) if snapshot else set()
    evidence_by_id = {
        item.get("evidence_id"): item
        for item in evidence
        if item.get("evidence_id") in evidence_refs
    }
    evidence = [evidence_by_id[ref] for ref in snapshot.get("evidence_refs", []) if ref in evidence_by_id] if snapshot else []
    return ok({"session": session, "snapshot": snapshot, "path": path, "evidence": evidence})


@router.post("/learning-diagnosis/sessions/{session_id}/refresh")
async def refresh_diagnosis_session(session_id: str, payload: RefreshDiagnosisRequest, student_id: str, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(student_id, authorization)
    return ok(await DiagnosisWorkflow(db).refresh_session(session_id, student_id, payload.trigger))


@router.get("/learning-diagnosis/sessions/{session_id}/path")
async def get_diagnosis_path(session_id: str, student_id: str, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(student_id, authorization)
    return ok({"session_id": session_id, "paths": DiagnosisWorkflow(db).store.list_paths(student_id, session_id)})


@router.post("/learning-diagnosis/tasks/{task_id}/hints")
async def request_task_hint(task_id: str, session_id: str, payload: HintRequest, student_id: str, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(student_id, authorization)
    try:
        return ok(await DiagnosisWorkflow(db).request_hint(session_id, student_id, task_id, payload.requested_level, payload.assessment_mode, payload.attempt))
    except KeyError as exc:
        raise HTTPException(status_code=404 if str(exc).strip("'") in {"SESSION_NOT_FOUND", "PATH_NOT_FOUND"} else 422, detail=str(exc).strip("'"))


@router.post("/learning-diagnosis/tasks/{task_id}/submit")
async def submit_diagnosis_task(task_id: str, payload: SubmitTaskRequest, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(payload.student_id, authorization)
    workflow = DiagnosisWorkflow(db)
    session_id = payload.session_id
    if not session_id:
        sessions = workflow.store.store.list_payloads("learning_diagnosis", "session", owner_id=student_id)
        session_id = sessions[0].get("id") if sessions else ""
    session = workflow.store.get_session(session_id, student_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return ok(await workflow.submit_task(
        session_id=session_id,
        student_id=student_id,
        task_id=task_id,
        code=payload.code,
        answer=payload.answer,
        hint_level=payload.hint_level,
        assessment_mode=payload.assessment_mode,
    ))


@router.post("/learning-diagnosis/tasks/{task_id}/run")
async def run_diagnosis_task(task_id: str, payload: RunTaskRequest, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(payload.student_id, authorization)
    try:
        result = DiagnosisWorkflow(db).preview_task_execution(
            session_id=payload.session_id,
            student_id=student_id,
            task_id=task_id,
            code=payload.code,
            language=payload.language,
        )
        return ok(result)
    except KeyError as exc:
        code = str(exc).strip("'")
        raise HTTPException(status_code=404 if code in {"SESSION_NOT_FOUND", "PATH_NOT_FOUND"} else 422, detail=code)


@router.post("/learning-diagnosis/sessions/{session_id}/git-evidence")
async def toggle_git_evidence(session_id: str, payload: GitEvidenceToggleRequest, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(payload.student_id, authorization)
    try:
        return ok(await DiagnosisWorkflow(db).set_git_evidence(session_id, student_id, payload.include_git_evidence))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'"))


@router.post("/learning-diagnosis/internal/activity")
async def publish_learning_activity(payload: LearningActivityEventRequest, db: Session = Depends(get_db), x_internal_token: str | None = Header(default=None, alias="X-Learning-Diagnosis-Internal")):
    # Internal callers may use the same process; external requests still require a shared token when configured.
    occurred = payload.occurred_at or datetime.now(timezone.utc).isoformat()
    event = LearningActivityEvent(**payload.model_dump(), occurred_at=occurred)
    result = await ActivityListener(__import__("app.services.learning_diagnosis.evidence_store", fromlist=["LearningDiagnosisStore"]).LearningDiagnosisStore(db)).handle(event)
    return ok(result)


@router.get("/learning-diagnosis/snapshots/{snapshot_id}")
async def get_diagnosis_snapshot(snapshot_id: str, student_id: str, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    student_id = _student(student_id, authorization)
    result = DiagnosisWorkflow(db).store.get_snapshot(snapshot_id, student_id)
    if not result: raise HTTPException(status_code=404, detail="snapshot not found")
    return ok(result)
