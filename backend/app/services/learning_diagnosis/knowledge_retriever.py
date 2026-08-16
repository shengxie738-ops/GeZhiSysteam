from __future__ import annotations

import os
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import settings
from app.services.rag_service import get_course_datasets, get_public_dataset_ids, retrieve_from_datasets


@dataclass
class KnowledgeRetrievalRequest:
    knowledge_point_id: str
    query: str = ""
    dataset_ids: list[str] = field(default_factory=list)


@dataclass
class KnowledgeChunk:
    chunk_id: str
    title: str
    content: str
    score: float
    dataset_id: str = ""
    source_name: str = ""


@dataclass
class KnowledgeRetrievalResult:
    status: str
    provider: str
    chunks: list[KnowledgeChunk] = field(default_factory=list)
    retrieved_at: str | None = None
    error_code: str | None = None


class KnowledgeRetriever(Protocol):
    async def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult: ...


class UnavailableKnowledgeRetriever:
    async def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        return KnowledgeRetrievalResult(
            status="UNAVAILABLE",
            provider="unavailable",
            error_code="RAGFLOW_CONFIG_MISSING",
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )


class RagFlowKnowledgeRetriever:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, dataset_ids: list[str] | None = None):
        self.base_url = base_url or os.getenv("RAGFLOW_BASE_URL") or settings.RAGFLOW_BASE_URL
        self.api_key = api_key or os.getenv("RAGFLOW_API_KEY") or settings.RAGFLOW_API_KEY
        configured = dataset_ids or [item["id"] for item in get_course_datasets()]
        self.dataset_ids = configured or get_public_dataset_ids() or ([settings.RAGFLOW_DATASET_ID] if settings.RAGFLOW_DATASET_ID else [])

    async def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        if not self.base_url or not self.api_key or not self.dataset_ids:
            return KnowledgeRetrievalResult(status="UNAVAILABLE", provider="ragflow", error_code="RAGFLOW_CONFIG_MISSING")
        query = request.query or request.knowledge_point_id.replace("_", " ")
        try:
            chunks = retrieve_from_datasets(self.dataset_ids, query, top_k_per_dataset=4)
        except Exception as exc:
            return KnowledgeRetrievalResult(status="UNAVAILABLE", provider="ragflow", error_code="RAGFLOW_REQUEST_FAILED")
        mapped = [KnowledgeChunk(
            chunk_id=str(item.get("id") or item.get("chunk_id") or f"rag-{index}"),
            title=str(item.get("document_name") or item.get("title") or "课程知识片段"),
            content=str(item.get("content") or item.get("text") or ""),
            score=float(item.get("similarity") or item.get("score") or 0),
            dataset_id=str(item.get("dataset_id") or ""),
            source_name=str(item.get("document_name") or "RAGFlow"),
        ) for index, item in enumerate(chunks)]
        if not mapped:
            return KnowledgeRetrievalResult(status="EMPTY", provider="ragflow", chunks=[], retrieved_at=datetime.now(timezone.utc).isoformat())
        return KnowledgeRetrievalResult(status="OK", provider="ragflow", chunks=mapped, retrieved_at=datetime.now(timezone.utc).isoformat())


def select_knowledge_retriever(mode: str | None = None) -> KnowledgeRetriever:
    selected = (mode or os.getenv("KNOWLEDGE_RETRIEVER_MODE", "auto")).lower()
    if selected == "ragflow":
        return RagFlowKnowledgeRetriever()
    if selected == "auto":
        configured_base_url = os.getenv("RAGFLOW_BASE_URL") or settings.RAGFLOW_BASE_URL
        configured_api_key = os.getenv("RAGFLOW_API_KEY") or settings.RAGFLOW_API_KEY
        configured_dataset = (
            os.getenv("RAGFLOW_DATASET_ID")
            or settings.RAGFLOW_DATASET_ID
            or get_course_datasets()
            or get_public_dataset_ids()
        )
        if configured_base_url and configured_api_key and configured_dataset:
            return RagFlowKnowledgeRetriever()
        return UnavailableKnowledgeRetriever()
    if selected == "unavailable":
        return UnavailableKnowledgeRetriever()
    from .mock_knowledge import MockKnowledgeRetriever

    return MockKnowledgeRetriever()
