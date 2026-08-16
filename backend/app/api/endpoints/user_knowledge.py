from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.miniprogram_response import api_response, is_miniprogram_client
from app.core.responses import ok
from app.services.rag_service import get_course_datasets
from app.services.user_knowledge_service import (
    create_repository,
    delete_repository,
    delete_repository_document,
    list_user_knowledge,
    upload_document_to_repository,
)

router = APIRouter()


class RepositoryCreate(BaseModel):
    user_id: str
    name: str


async def _upload_knowledge_document_impl(
    user_id: str,
    repository_id: str,
    file: UploadFile,
    db: Session,
) -> dict:
    file_bytes = await file.read()
    if not file_bytes:
        raise ValueError("file is empty")
    return upload_document_to_repository(
        db,
        user_id=user_id,
        repository_id=repository_id,
        file_bytes=file_bytes,
        filename=file.filename or "untitled",
        file_size=len(file_bytes),
    )


@router.get("/user/knowledge")
async def get_user_knowledge(user_id: str, db: Session = Depends(get_db)):
    try:
        return ok(list_user_knowledge(db, user_id, sync_remote=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/knowledge/courses")
async def get_course_knowledge_bases():
    """返回可用课程知识库列表，供前端渲染选择器。"""
    return ok(get_course_datasets())


@router.post("/user/knowledge/repositories")
async def create_user_knowledge_repository(payload: RepositoryCreate, db: Session = Depends(get_db)):
    try:
        return ok(create_repository(db, payload.user_id, payload.name), message="repository created")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/user/knowledge/documents")
async def upload_user_knowledge_document(
    user_id: str = Form(...),
    repository_id: str = Form(...),
    file: UploadFile = File(...),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
    db: Session = Depends(get_db),
):
    try:
        document = await _upload_knowledge_document_impl(user_id, repository_id, file, db)
        if is_miniprogram_client(x_gezhi_client):
            return api_response(document)
        return ok(document, message="document uploaded")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/user/knowledge/upload")
async def upload_user_knowledge_document_alias(
    user_id: str = Form(...),
    repository_id: str = Form(...),
    file: UploadFile = File(...),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
    db: Session = Depends(get_db),
):
    try:
        document = await _upload_knowledge_document_impl(user_id, repository_id, file, db)
        if is_miniprogram_client(x_gezhi_client):
            return api_response(document)
        return ok(document, message="document uploaded")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/user/knowledge/documents/{document_id}")
async def delete_user_knowledge_document(document_id: str, user_id: str, db: Session = Depends(get_db)):
    try:
        return ok(delete_repository_document(db, user_id=user_id, document_id=document_id), message="document deleted")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/user/knowledge/repositories/{repository_id}")
async def delete_user_knowledge_repository(repository_id: str, user_id: str, db: Session = Depends(get_db)):
    try:
        return ok(delete_repository(db, user_id=user_id, repository_id=repository_id), message="repository deleted")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
