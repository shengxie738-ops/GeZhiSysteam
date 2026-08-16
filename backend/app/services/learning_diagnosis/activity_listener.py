from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from .contracts import EvidenceProcessingReceipt, EvidenceRecord, LearningActivityEvent, Provenance


class ActivityListener:
    """Process trusted site activity without changing the originating business result."""

    SOURCE_TYPES = {
        "EXAM": "ASSIGNMENT",
        "EXAM_QUESTION": "ASSIGNMENT",
        "WRONG_QUESTION": "EXAM_WRONG",
        "RANKED": "RANKED_RESULT",
        "RANKED_QUESTION": "RANKED_RESULT",
        "HOMEWORK": "ASSIGNMENT",
    }

    def __init__(self, store, refresh_callback: Callable[..., Awaitable[dict[str, Any]]] | None = None):
        self.store = store
        self.refresh_callback = refresh_callback

    async def handle(self, event: LearningActivityEvent | dict[str, Any]) -> dict[str, Any]:
        model = event if isinstance(event, LearningActivityEvent) else LearningActivityEvent.model_validate(event)
        existing_receipt = self.store.find_processing_receipt_by_deduplication_key(model.deduplication_key, model.student_id)
        if existing_receipt:
            return {"status": "DUPLICATE", "event_id": model.event_id, "receipt": existing_receipt}
        self.store.create_activity_event(model)
        sessions = sorted(self.store.list_sessions(model.student_id), key=lambda item: str(item.get("created_at", "")), reverse=True)
        matched = None
        session = None
        for candidate in sessions:
            goal_id = str(candidate.get("current_goal_version") or candidate.get("goal_version_id") or "")
            for association in self.store.list_content_associations(model.student_id, goal_id, active=True):
                if association.get("content_type") == model.content_type and association.get("content_id") == model.content_id:
                    matched, session = association, candidate
                    break
            if matched:
                break
        if not matched or not session:
            self.store.update_activity_event(model.event_id, model.student_id, {"processing_status": "PROCESSED", "processed_at": datetime.now(timezone.utc), "failure_reason": None})
            return {"status": "IGNORED", "event_id": model.event_id, "reason": "NO_ACTIVE_GOAL_ASSOCIATION"}
        try:
            evidence = self._to_evidence(model, matched)
            stored_evidence = self.store.create_evidence(evidence)
            if self.refresh_callback is None:
                from .workflow import DiagnosisWorkflow
                refreshed = await DiagnosisWorkflow(self.store.store.db).refresh_session(session["id"], model.student_id, {"trigger_type": "CROSS_ROUTE_ACTIVITY"})
            else:
                refreshed = await self.refresh_callback(session["id"], model.student_id, {"trigger_type": "CROSS_ROUTE_ACTIVITY"})
            receipt = EvidenceProcessingReceipt(
                receipt_id=f"receipt-{uuid4().hex[:12]}", event_id=model.event_id, session_id=str(session["id"]),
                goal_version_id=str(matched["goal_version_id"]), association_id=str(matched["association_id"]),
                evidence_id=str(stored_evidence["evidence_id"]), snapshot_id=str(refreshed["snapshot"]["snapshot_id"]),
                path_version=int(refreshed["path"]["path_version"]), deduplication_key=model.deduplication_key,
                created_at=datetime.now(timezone.utc),
            )
            stored_receipt = self.store.create_processing_receipt(receipt)
            self.store.update_activity_event(model.event_id, model.student_id, {"processing_status": "PROCESSED", "processed_at": datetime.now(timezone.utc), "failure_reason": None})
            return {"status": "PROCESSED", "event_id": model.event_id, "receipt": stored_receipt, "snapshot": refreshed["snapshot"]}
        except Exception as exc:
            self.store.update_activity_event(model.event_id, model.student_id, {
                "processing_status": "RETRY_PENDING", "failure_reason": str(exc), "retry_count": model.retry_count + 1,
            })
            return {"status": "RETRY_PENDING", "event_id": model.event_id, "error": str(exc)}

    def _to_evidence(self, event: LearningActivityEvent, association: dict[str, Any]) -> EvidenceRecord:
        result = dict(event.result_payload)
        result.setdefault("status", event.status)
        reliability = min(.95, max(.45, float(association.get("relevance_score") or .5) * .9))
        source_ref = f"{event.source_module}:{event.content_id}:{event.attempt_id}"
        return EvidenceRecord(
            evidence_id=f"activity-{event.event_id.removeprefix('activity-')}", student_id=event.student_id,
            source_type=self.SOURCE_TYPES.get(event.content_type, "ASSIGNMENT"), source_ref=source_ref,
            knowledge_point_ids=list(association.get("knowledge_point_ids") or []), result=result,
            observed_at=event.occurred_at, provenance=Provenance(source=f"activity:{event.source_module}", reliability=reliability, source_ref=source_ref),
            summary=f"{event.source_module} 中与当前目标相关的 {event.content_type} 已产生学习活动证据。",
        )


async def publish_learning_activity_safely(db, payload: dict[str, Any]) -> dict[str, Any]:
    """Best-effort publisher for existing routes; failures never escape to their transaction."""
    try:
        from .evidence_store import LearningDiagnosisStore
        return await ActivityListener(LearningDiagnosisStore(db)).handle(payload)
    except Exception as exc:
        return {"status": "RETRY_PENDING", "error": str(exc)}
