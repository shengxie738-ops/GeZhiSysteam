import json
from typing import Any

import requests
from requests.exceptions import RequestException
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import ok
from app.core.security import decode_access_token
from app.models.user_account import UserAccount
from app.services.code_repository_service import (
    apply_code_repository_gitea_webhook,
    audit_repository_report,
    create_repository_report,
    delete_repository_project,
    get_repository_archive,
    get_repository_blob,
    get_repository_detail,
    get_repository_languages,
    get_repository_tree,
    get_user_repository_profile,
    list_repositories,
    list_repository_reports,
    publish_repository,
    enqueue_code_repository_git_coach_feedback,
    toggle_repository_favorite,
    toggle_repository_star,
)
from app.api.endpoints.team_git import verify_gitea_signature
from app.core.config import settings

router = APIRouter()


class FreePayload(BaseModel):
    class Config:
        extra = "allow"


def _payload(payload: FreePayload) -> dict[str, Any]:
    return payload.model_dump()


def _current_user_id(authorization: str | None, db: Session) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        decoded = decode_access_token(authorization.split(" ", 1)[1])
        if decoded:
            username = decoded.get("sub") or ""
            if username and db.query(UserAccount).filter(UserAccount.username == username).first():
                return username
    return ""


def _actor(authorization: str | None, db: Session, fallback: str = "anonymous") -> str:
    return _current_user_id(authorization, db) or fallback


@router.get("/code-repositories")
async def get_code_repositories(
    q: str = "",
    language: str = "",
    tag: str = "",
    sort: str = "latest",
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    viewer = _current_user_id(authorization, db)
    return ok(list_repositories(db, viewer=viewer, query=q, language=language, tag=tag, sort=sort))


@router.post("/code-repositories")
async def create_code_repository(
    payload: FreePayload,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    data = _payload(payload)
    actor = _actor(authorization, db, data.get("author") or "anonymous")
    try:
        return ok(publish_repository(db, data, current_user=actor))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/code-repositories/reports")
async def get_code_repository_reports(status: str = "", db: Session = Depends(get_db)):
    return ok(list_repository_reports(db, status=status or None))


@router.get("/code-repositories/{project_id}")
async def get_code_repository(
    project_id: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    try:
        return ok(get_repository_detail(db, project_id, viewer=_current_user_id(authorization, db)))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/code-repositories/{project_id}/download")
async def download_code_repository(project_id: str, db: Session = Depends(get_db)):
    try:
        return ok(get_repository_archive(db, project_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/code-repositories/{project_id}/tree")
async def get_code_repository_tree(
    project_id: str,
    path: str = "",
    ref: str = "",
    db: Session = Depends(get_db),
):
    try:
        return ok(get_repository_tree(db, project_id, path=path, ref=ref or None))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Gitea 文件目录读取失败：{exc}") from exc


@router.get("/code-repositories/{project_id}/blob")
async def get_code_repository_blob(
    project_id: str,
    path: str,
    ref: str = "",
    db: Session = Depends(get_db),
):
    if not path.strip():
        raise HTTPException(status_code=400, detail="path is required")
    try:
        return ok(get_repository_blob(db, project_id, path=path, ref=ref or None))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Gitea 文件预览失败：{exc}") from exc


@router.get("/code-repositories/{project_id}/languages")
async def get_code_repository_languages(project_id: str, db: Session = Depends(get_db)):
    try:
        return ok(get_repository_languages(db, project_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Gitea 语言统计读取失败：{exc}") from exc


@router.post("/code-repositories/{project_id}/star")
async def star_code_repository(
    project_id: str,
    payload: FreePayload | None = None,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    data = _payload(payload) if payload else {}
    user_id = _actor(authorization, db, data.get("userId") or "anonymous")
    try:
        return ok(toggle_repository_star(db, project_id, user_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/code-repositories/{project_id}/favorite")
async def favorite_code_repository(
    project_id: str,
    payload: FreePayload | None = None,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    data = _payload(payload) if payload else {}
    user_id = _actor(authorization, db, data.get("userId") or "anonymous")
    try:
        return ok(toggle_repository_favorite(db, project_id, user_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/code-repositories/{project_id}/reports")
async def report_code_repository(
    project_id: str,
    payload: FreePayload,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    data = _payload(payload)
    reporter = _actor(authorization, db, data.get("reporter") or "anonymous")
    try:
        return ok(create_repository_report(db, project_id, data, reporter=reporter))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/code-repositories/reports/{report_id}")
async def audit_code_repository_report(
    report_id: str,
    payload: FreePayload,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    data = _payload(payload)
    teacher_id = _actor(authorization, db, data.get("teacherId") or "teacher")
    try:
        return ok(audit_repository_report(db, report_id, data, teacher_id=teacher_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/code-repositories/{project_id}")
async def remove_code_repository(
    project_id: str,
    payload: FreePayload | None = None,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    data = _payload(payload) if payload else {}
    teacher_id = _actor(authorization, db, data.get("teacherId") or "teacher")
    try:
        return ok(delete_repository_project(db, project_id, teacher_id=teacher_id, reason=data.get("reason") or "教师审核删除"))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/code-repositories/{project_id}/webhooks/gitea")
async def receive_code_repository_webhook(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_gitea_signature: str | None = Header(default=None, alias="X-Gitea-Signature"),
    db: Session = Depends(get_db),
):
    body = await request.body()
    if not verify_gitea_signature(body, settings.GITEA_WEBHOOK_SECRET, x_gitea_signature):
        raise HTTPException(status_code=403, detail="invalid gitea webhook signature")
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid gitea webhook payload") from exc
    try:
        result = apply_code_repository_gitea_webhook(db, project_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    background_tasks.add_task(enqueue_code_repository_git_coach_feedback, project_id, payload)
    return ok(result)


@router.get("/users/{user_id}/code-repositories")
async def get_user_code_repository_profile(user_id: str, db: Session = Depends(get_db)):
    return ok(get_user_repository_profile(db, user_id))
