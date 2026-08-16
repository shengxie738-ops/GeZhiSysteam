import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import ok
from app.core.security import decode_access_token
from app.schemas.teacher_lesson_prep import (
    LessonPlanExportRequest,
    LessonPlanGenerateRequest,
    LessonPrepDraftRequest,
    LessonPrepSearchRequest,
    LessonPrepSummaryRequest,
)
from app.services.teacher_lesson_prep.service import lesson_prep_service


MAX_JSON_BODY_BYTES = 256 * 1024


class LimitedBodyRoute(APIRoute):
    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await super().handle(scope, receive, send)
            return

        messages = []
        received = 0
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                messages.append(message)
                break
            received += len(message.get("body", b""))
            if received > MAX_JSON_BODY_BYTES:
                await JSONResponse(status_code=413, content={"detail": "request body is too large"})(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive():
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        await super().handle(scope, replay_receive, send)


router = APIRouter(route_class=LimitedBodyRoute)


def _teacher(authorization: str | None) -> str:
    if not isinstance(authorization, str) or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    payload = decode_access_token(authorization.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="invalid access token")
    if payload.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="teacher role required")
    return str(payload["sub"])


@router.get("/teacher/lesson-prep/config")
async def get_lesson_prep_config(authorization: str | None = Header(default=None)):
    _teacher(authorization)
    return ok(lesson_prep_service.public_config())


@router.get("/teacher/lesson-prep/resources")
async def list_lesson_prep_resources(
    authorization: str | None = Header(default=None),
    course: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    query: str | None = Query(default=None),
):
    _teacher(authorization)
    data = await asyncio.to_thread(lesson_prep_service.list_resources, course=course, file_type=file_type, query=query)
    return ok(data)


@router.post("/teacher/lesson-prep/search")
async def search_lesson_prep_resources(payload: LessonPrepSearchRequest, authorization: str | None = Header(default=None)):
    _teacher(authorization)
    return ok(await asyncio.to_thread(lesson_prep_service.search, payload))


@router.post("/teacher/lesson-prep/summarize")
async def summarize_lesson_prep_resources(payload: LessonPrepSummaryRequest, authorization: str | None = Header(default=None)):
    _teacher(authorization)
    return ok(await lesson_prep_service.summarize(payload))


@router.post("/teacher/lesson-prep/generate")
async def generate_lesson_plan(payload: LessonPlanGenerateRequest, authorization: str | None = Header(default=None)):
    _teacher(authorization)
    return ok(await lesson_prep_service.generate_plan(payload))


@router.post("/teacher/lesson-prep/export-docx")
def export_lesson_plan_docx(payload: LessonPlanExportRequest, authorization: str | None = Header(default=None)):
    _teacher(authorization)
    document_bytes, filename = lesson_prep_service.export_docx(payload)
    encoded = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename=\"lesson-plan.docx\"; filename*=UTF-8''{encoded}",
        "Content-Length": str(len(document_bytes)),
    }
    return Response(
        content=document_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


@router.post("/teacher/lesson-prep/drafts")
def save_lesson_prep_draft(
    payload: LessonPrepDraftRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    teacher = _teacher(authorization)
    return ok(lesson_prep_service.save_draft(db, teacher, payload))


@router.get("/teacher/lesson-prep/drafts")
def list_lesson_prep_drafts(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    teacher = _teacher(authorization)
    return ok(lesson_prep_service.list_drafts(db, teacher))


@router.get("/teacher/lesson-prep/drafts/{draft_id}")
def get_lesson_prep_draft(
    draft_id: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    teacher = _teacher(authorization)
    return ok(lesson_prep_service.get_draft(db, teacher, draft_id))
