from __future__ import annotations

from typing import Any

from app.repositories.json_store import JsonStore

from .contracts import (
    DiagnosisSnapshot,
    EvidenceProcessingReceipt,
    EvidenceRecord,
    GoalContentAssociation,
    GoalVersion,
    LearningActivityEvent,
    PathVersion,
)


class LearningDiagnosisStore:
    MODULE = "learning_diagnosis"

    def __init__(self, db):
        self.store = JsonStore(db)

    def create_evidence(self, evidence: EvidenceRecord | dict[str, Any]) -> dict[str, Any]:
        model = evidence if isinstance(evidence, EvidenceRecord) else EvidenceRecord.model_validate(evidence)
        return self.store.create(
            self.MODULE,
            "evidence",
            model.model_dump(mode="json"),
            prefix="evidence",
            owner_id=model.student_id,
            status="COLLECTED",
        )

    def list_evidence(self, student_id: str) -> list[dict[str, Any]]:
        return self.store.list_payloads(self.MODULE, "evidence", owner_id=student_id)

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.store.create(self.MODULE, "session", payload, prefix="session", owner_id=str(payload["student_id"]), status=payload.get("status", "CREATED"))

    def get_session(self, session_id: str, student_id: str) -> dict[str, Any] | None:
        return self.store.get_payload(self.MODULE, "session", session_id, owner_id=student_id)

    def update_session(self, session_id: str, student_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        return self.store.patch(self.MODULE, "session", session_id, patch, owner_id=student_id)

    def create_snapshot(self, snapshot: DiagnosisSnapshot | dict[str, Any]) -> dict[str, Any]:
        model = snapshot if isinstance(snapshot, DiagnosisSnapshot) else DiagnosisSnapshot.model_validate(snapshot)
        return self.store.create(self.MODULE, "snapshot", model.model_dump(mode="json"), prefix="snapshot", owner_id=model.student_id, status=model.status)

    def list_snapshots(self, student_id: str, session_id: str | None = None) -> list[dict[str, Any]]:
        items = self.store.list_payloads(self.MODULE, "snapshot", owner_id=student_id)
        if session_id is not None:
            items = [item for item in items if item.get("session_id") == session_id]
        return sorted(items, key=lambda item: int(item.get("version", 0)))

    def get_snapshot(self, snapshot_id: str, student_id: str) -> dict[str, Any] | None:
        return self.store.get_payload(self.MODULE, "snapshot", snapshot_id, owner_id=student_id)

    def create_path(self, path: PathVersion | dict[str, Any], student_id: str, session_id: str | None = None) -> dict[str, Any]:
        model = path if isinstance(path, PathVersion) else PathVersion.model_validate(path)
        payload = model.model_dump(mode="json")
        payload["student_id"] = student_id
        if session_id:
            payload["session_id"] = session_id
        return self.store.create(self.MODULE, "path_version", payload, prefix="path", owner_id=student_id, status="ACTIVE")

    def list_paths(self, student_id: str, session_id: str | None = None) -> list[dict[str, Any]]:
        items = self.store.list_payloads(self.MODULE, "path_version", owner_id=student_id)
        if session_id is not None:
            items = [item for item in items if item.get("session_id") == session_id]
        return sorted(items, key=lambda item: int(item.get("path_version", 0)))

    def update_path(self, path_id: str, student_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        return self.store.patch(self.MODULE, "path_version", path_id, patch, owner_id=student_id)

    def list_sessions(self, student_id: str) -> list[dict[str, Any]]:
        return self.store.list_payloads(self.MODULE, "session", owner_id=student_id)

    def create_goal_version(self, goal: GoalVersion | dict[str, Any]) -> dict[str, Any]:
        model = goal if isinstance(goal, GoalVersion) else GoalVersion.model_validate(goal)
        return self.store.upsert(
            self.MODULE,
            "goal_version",
            model.goal_version_id,
            model.model_dump(mode="json"),
            owner_id=model.student_id,
            status="ACTIVE",
        )

    def get_goal_version(self, goal_version_id: str, student_id: str) -> dict[str, Any] | None:
        return self.store.get_payload(self.MODULE, "goal_version", goal_version_id, owner_id=student_id)

    def list_goal_versions(self, student_id: str, session_id: str | None = None) -> list[dict[str, Any]]:
        items = self.store.list_payloads(self.MODULE, "goal_version", owner_id=student_id)
        if session_id is not None:
            items = [item for item in items if item.get("session_id") == session_id]
        return sorted(items, key=lambda item: str(item.get("created_at", "")))

    def update_goal_version(self, goal_version_id: str, student_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        if any(key in (patch or {}) for key in {"goal_version_id", "raw_goal_text", "course_id", "course_name", "deadline", "session_id", "student_id"}):
            raise ValueError("goal update is metadata-only; create a new GoalVersion for goal changes")
        current = self.get_goal_version(goal_version_id, student_id)
        if current is None:
            return None
        payload = {key: value for key, value in current.items() if key != "id"}
        payload.update(patch or {})
        return self.create_goal_version(GoalVersion.model_validate(payload))

    def create_content_association(
        self, association: GoalContentAssociation | dict[str, Any]
    ) -> dict[str, Any]:
        model = association if isinstance(association, GoalContentAssociation) else GoalContentAssociation.model_validate(association)
        return self.store.upsert(
            self.MODULE,
            "content_association",
            model.association_id,
            model.model_dump(mode="json"),
            owner_id=model.student_id,
            status="ACTIVE" if model.active else "INACTIVE",
        )

    def get_content_association(self, association_id: str, student_id: str) -> dict[str, Any] | None:
        return self.store.get_payload(self.MODULE, "content_association", association_id, owner_id=student_id)

    def list_content_associations(
        self, student_id: str, goal_version_id: str | None = None, active: bool | None = None
    ) -> list[dict[str, Any]]:
        items = self.store.list_payloads(self.MODULE, "content_association", owner_id=student_id)
        if goal_version_id is not None:
            items = [item for item in items if item.get("goal_version_id") == goal_version_id]
        if active is not None:
            items = [item for item in items if bool(item.get("active", True)) is active]
        return items

    def find_content_association(
        self, goal_version_id: str, content_type: str, content_id: str, student_id: str
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self.list_content_associations(student_id, goal_version_id)
                if item.get("content_type") == content_type and item.get("content_id") == content_id
            ),
            None,
        )

    def update_content_association(
        self, association_id: str, student_id: str, patch: dict[str, Any]
    ) -> dict[str, Any] | None:
        current = self.get_content_association(association_id, student_id)
        if current is None:
            return None
        payload = {key: value for key, value in current.items() if key != "id"}
        payload.update(patch or {})
        return self.create_content_association(GoalContentAssociation.model_validate(payload))

    def create_activity_event(self, event: LearningActivityEvent | dict[str, Any]) -> dict[str, Any]:
        model = event if isinstance(event, LearningActivityEvent) else LearningActivityEvent.model_validate(event)
        existing = self.find_activity_event_by_deduplication_key(model.deduplication_key, model.student_id)
        if existing is not None:
            payload = {key: value for key, value in existing.items() if key != "id"}
            payload.update(model.model_dump(mode="json"))
            return self.store.upsert(
                self.MODULE,
                "activity_event",
                existing["event_id"],
                payload,
                owner_id=model.student_id,
                status=model.processing_status,
            )
        return self.store.upsert(
            self.MODULE,
            "activity_event",
            model.event_id,
            model.model_dump(mode="json"),
            owner_id=model.student_id,
            status=model.processing_status,
        )

    def get_activity_event(self, event_id: str, student_id: str) -> dict[str, Any] | None:
        return self.store.get_payload(self.MODULE, "activity_event", event_id, owner_id=student_id)

    def list_activity_events(
        self, student_id: str, processing_status: str | None = None
    ) -> list[dict[str, Any]]:
        items = self.store.list_payloads(self.MODULE, "activity_event", owner_id=student_id)
        if processing_status is not None:
            items = [item for item in items if item.get("processing_status") == processing_status]
        return sorted(items, key=lambda item: str(item.get("occurred_at", "")))

    def find_activity_event_by_deduplication_key(
        self, deduplication_key: str, student_id: str
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self.list_activity_events(student_id)
                if item.get("deduplication_key") == deduplication_key
            ),
            None,
        )

    def update_activity_event(self, event_id: str, student_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get_activity_event(event_id, student_id)
        if current is None:
            return None
        payload = {key: value for key, value in current.items() if key != "id"}
        payload.update(patch or {})
        model = LearningActivityEvent.model_validate(payload)
        return self.store.upsert(
            self.MODULE,
            "activity_event",
            model.event_id,
            model.model_dump(mode="json"),
            owner_id=student_id,
            status=model.processing_status,
        )

    def create_processing_receipt(
        self, receipt: EvidenceProcessingReceipt | dict[str, Any]
    ) -> dict[str, Any]:
        model = receipt if isinstance(receipt, EvidenceProcessingReceipt) else EvidenceProcessingReceipt.model_validate(receipt)
        event_record = self.store.get_record(self.MODULE, "activity_event", model.event_id)
        if event_record is None:
            raise ValueError("activity event does not exist")
        owner_id = event_record.owner_id
        existing = self.find_processing_receipt_by_deduplication_key(model.deduplication_key, owner_id)
        if existing is not None:
            return existing
        return self.store.upsert(
            self.MODULE,
            "processing_receipt",
            model.receipt_id,
            model.model_dump(mode="json"),
            owner_id=owner_id,
            status="CREATED",
        )

    def get_processing_receipt(self, receipt_id: str, student_id: str) -> dict[str, Any] | None:
        return self.store.get_payload(self.MODULE, "processing_receipt", receipt_id, owner_id=student_id)

    def list_processing_receipts(self, student_id: str, event_id: str | None = None) -> list[dict[str, Any]]:
        items = self.store.list_payloads(self.MODULE, "processing_receipt", owner_id=student_id)
        if event_id is not None:
            items = [item for item in items if item.get("event_id") == event_id]
        return items

    def find_processing_receipt_by_deduplication_key(
        self, deduplication_key: str, student_id: str
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self.list_processing_receipts(student_id)
                if item.get("deduplication_key") == deduplication_key
            ),
            None,
        )

    def update_processing_receipt(
        self, receipt_id: str, student_id: str, patch: dict[str, Any]
    ) -> dict[str, Any] | None:
        current = self.get_processing_receipt(receipt_id, student_id)
        if current is None:
            return None
        payload = {key: value for key, value in current.items() if key != "id"}
        payload.update(patch or {})
        model = EvidenceProcessingReceipt.model_validate(payload)
        return self.store.upsert(
            self.MODULE,
            "processing_receipt",
            model.receipt_id,
            model.model_dump(mode="json"),
            owner_id=student_id,
            status="CREATED",
        )
