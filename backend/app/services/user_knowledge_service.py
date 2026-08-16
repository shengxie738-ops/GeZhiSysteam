import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_knowledge import UserKnowledgeDocument, UserKnowledgeRepository
from app.models.user_rag import UserRagMapping
from app.services.rag_service import (
    build_document_metadata,
    classify_supported_file,
    create_user_dataset,
    delete_document_from_dataset,
    list_dataset_documents,
    map_ragflow_run_to_status,
    upload_and_run_document,
)


DEFAULT_REPOSITORY_NAME = "默认资料库"


def _new_id() -> str:
    return uuid.uuid4().hex


def _clean_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("repository name is required")
    if len(cleaned) > 100:
        raise ValueError("repository name must not exceed 100 characters")
    return cleaned


def _serialize_repository(repo: UserKnowledgeRepository, documents: list[UserKnowledgeDocument] | None = None) -> dict:
    docs = [_serialize_document(doc) for doc in documents or []]
    return {
        "id": repo.id,
        "user_id": repo.user_id,
        "name": repo.name,
        "created_at": repo.created_at.isoformat() if repo.created_at else "",
        "document_count": len(docs),
        "documents": docs,
    }


def _serialize_document(doc: UserKnowledgeDocument) -> dict:
    return {
        "id": doc.id,
        "user_id": doc.user_id,
        "repository_id": doc.repository_id,
        "dataset_id": doc.dataset_id,
        "rag_document_id": doc.rag_document_id,
        "filename": doc.filename,
        "file_size": doc.file_size,
        "status": doc.status,
        "created_at": doc.created_at.isoformat() if doc.created_at else "",
    }


def create_repository(db: Session, user_id: str, name: str) -> dict:
    user = (user_id or "").strip()
    if not user:
        raise ValueError("user_id is required")

    repo = UserKnowledgeRepository(id=_new_id(), user_id=user, name=_clean_name(name))
    db.add(repo)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("repository name already exists") from exc
    db.refresh(repo)
    return _serialize_repository(repo)


def get_or_create_default_repository(db: Session, user_id: str) -> UserKnowledgeRepository:
    repo = (
        db.query(UserKnowledgeRepository)
        .filter(UserKnowledgeRepository.user_id == user_id, UserKnowledgeRepository.name == DEFAULT_REPOSITORY_NAME)
        .first()
    )
    if repo:
        return repo

    repo = UserKnowledgeRepository(id=_new_id(), user_id=user_id, name=DEFAULT_REPOSITORY_NAME)
    db.add(repo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        repo = (
            db.query(UserKnowledgeRepository)
            .filter(UserKnowledgeRepository.user_id == user_id, UserKnowledgeRepository.name == DEFAULT_REPOSITORY_NAME)
            .one()
        )
        return repo
    db.refresh(repo)
    return repo


def _get_repository(db: Session, user_id: str, repository_id: str) -> UserKnowledgeRepository:
    repo = (
        db.query(UserKnowledgeRepository)
        .filter(UserKnowledgeRepository.id == repository_id, UserKnowledgeRepository.user_id == user_id)
        .first()
    )
    if not repo:
        raise ValueError("repository not found")
    return repo


def _ensure_user_dataset(db: Session, user_id: str) -> str:
    record = db.query(UserRagMapping).filter(UserRagMapping.user_id == user_id).first()
    if record:
        return record.dataset_id

    dataset_id = create_user_dataset(user_id)
    record = UserRagMapping(user_id=user_id, dataset_id=dataset_id)
    db.add(record)
    db.commit()
    return dataset_id


def upload_document_to_repository(
    db: Session,
    *,
    user_id: str,
    repository_id: str,
    file_bytes: bytes,
    filename: str,
    file_size: int,
) -> dict:
    user = (user_id or "").strip()
    if not user:
        raise ValueError("user_id is required")
    if not filename:
        raise ValueError("filename is required")

    _get_repository(db, user, repository_id)
    parser = classify_supported_file(filename)
    metadata = build_document_metadata(user, repository_id, filename)
    dataset_id = _ensure_user_dataset(db, user)
    rag_document_id = upload_and_run_document(
        dataset_id,
        file_bytes,
        filename,
        metadata=metadata,
        parser=parser,
    )

    document = UserKnowledgeDocument(
        id=_new_id(),
        user_id=user,
        repository_id=repository_id,
        dataset_id=dataset_id,
        rag_document_id=rag_document_id,
        filename=filename,
        file_size=int(file_size),
        status="parsing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return _serialize_document(document)


def upload_document_to_default_repository(
    db: Session,
    *,
    user_id: str,
    file_bytes: bytes,
    filename: str,
    file_size: int,
) -> dict:
    user = (user_id or "").strip()
    if not user:
        raise ValueError("user_id is required")
    repo = get_or_create_default_repository(db, user)
    return upload_document_to_repository(
        db,
        user_id=repo.user_id,
        repository_id=repo.id,
        file_bytes=file_bytes,
        filename=filename,
        file_size=file_size,
    )


def _sync_remote_document_statuses(db: Session, user_id: str, dataset_id: str | None) -> None:
    if not dataset_id:
        return

    local_docs = (
        db.query(UserKnowledgeDocument)
        .filter(UserKnowledgeDocument.user_id == user_id, UserKnowledgeDocument.dataset_id == dataset_id)
        .all()
    )
    if not local_docs:
        return

    try:
        remote_docs = list_dataset_documents(dataset_id)
    except Exception as exc:
        print(f"[Knowledge] Failed to sync RAGFlow document status: {exc}")
        return

    status_by_rag_id = {
        item.get("id"): map_ragflow_run_to_status(item.get("run"))
        for item in remote_docs
        if isinstance(item, dict) and item.get("id")
    }
    changed = False
    for doc in local_docs:
        next_status = status_by_rag_id.get(doc.rag_document_id)
        if next_status and doc.status != next_status:
            doc.status = next_status
            changed = True
    if changed:
        db.commit()


def list_user_knowledge(db: Session, user_id: str, *, sync_remote: bool = False) -> dict:
    user = (user_id or "").strip()
    if not user:
        raise ValueError("user_id is required")

    dataset = db.query(UserRagMapping).filter(UserRagMapping.user_id == user).first()
    if sync_remote and dataset:
        _sync_remote_document_statuses(db, user, dataset.dataset_id)

    repos = (
        db.query(UserKnowledgeRepository)
        .filter(UserKnowledgeRepository.user_id == user)
        .order_by(UserKnowledgeRepository.created_at.asc())
        .all()
    )
    documents = (
        db.query(UserKnowledgeDocument)
        .filter(UserKnowledgeDocument.user_id == user)
        .order_by(UserKnowledgeDocument.created_at.desc())
        .all()
    )
    docs_by_repo: dict[str, list[UserKnowledgeDocument]] = {}
    for doc in documents:
        docs_by_repo.setdefault(doc.repository_id, []).append(doc)

    return {
        "user_id": user,
        "dataset_id": dataset.dataset_id if dataset else "",
        "repositories": [_serialize_repository(repo, docs_by_repo.get(repo.id, [])) for repo in repos],
    }


def delete_repository_document(db: Session, *, user_id: str, document_id: str) -> dict:
    user = (user_id or "").strip()
    document = (
        db.query(UserKnowledgeDocument)
        .filter(UserKnowledgeDocument.id == document_id, UserKnowledgeDocument.user_id == user)
        .first()
    )
    if not document:
        raise ValueError("document not found")

    serialized = _serialize_document(document)
    delete_document_from_dataset(document.dataset_id, document.rag_document_id)
    db.delete(document)
    db.commit()
    return serialized


def delete_repository(db: Session, *, user_id: str, repository_id: str) -> dict:
    user = (user_id or "").strip()
    if not user:
        raise ValueError("user_id is required")

    repo = _get_repository(db, user, repository_id)
    documents = (
        db.query(UserKnowledgeDocument)
        .filter(UserKnowledgeDocument.user_id == user, UserKnowledgeDocument.repository_id == repo.id)
        .order_by(UserKnowledgeDocument.created_at.asc())
        .all()
    )
    serialized = _serialize_repository(repo, documents)

    for document in documents:
        delete_document_from_dataset(document.dataset_id, document.rag_document_id)

    for document in documents:
        db.delete(document)
    db.delete(repo)
    db.commit()
    return serialized
