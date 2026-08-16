from __future__ import annotations

from datetime import datetime, timezone

from .knowledge_retriever import KnowledgeChunk, KnowledgeRetrievalRequest, KnowledgeRetrievalResult


class MockKnowledgeRetriever:
    chunks = {
        "linked_list_boundary": KnowledgeChunk(
            chunk_id="mock-chunk-linked-list-boundary",
            title="链表操作的边界条件",
            content="处理空链表、单节点链表和删除头结点时，必须先确认指针和返回值的边界状态。",
            score=0.94,
            dataset_id="mock-data-structure",
            source_name="数据结构课程讲义",
        ),
        "linked_list_delete": KnowledgeChunk(
            chunk_id="mock-chunk-linked-list-delete",
            title="链表删除流程",
            content="删除节点前需要定位前驱节点，并在删除头结点时更新 head。",
            score=0.91,
            dataset_id="mock-data-structure",
            source_name="数据结构课程讲义",
        ),
    }

    async def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        chunk = self.chunks.get(request.knowledge_point_id)
        if not chunk:
            return KnowledgeRetrievalResult(status="EMPTY", provider="mock", retrieved_at=datetime.now(timezone.utc).isoformat())
        return KnowledgeRetrievalResult(status="OK", provider="mock", chunks=[chunk], retrieved_at=datetime.now(timezone.utc).isoformat())
