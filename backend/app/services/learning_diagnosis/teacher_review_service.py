from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_

from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore, make_record_key
from app.schemas.teacher_learning_diagnosis import (
    ReviewNoteRequest,
    ReviewStateRequest,
    TeacherReviewDetail,
    TeacherReviewListItem,
    TeacherReviewListResponse,
    TeacherReviewNote,
    TeacherReviewState,
    TeacherWatchFlag,
    WatchFlagRequest,
)


class TeacherLearningDiagnosisReviewService:
    MODULE = "teacher_learning_diagnosis"
    STUDENT_MODULE = "learning_diagnosis"

    def __init__(self, db):
        self.db = db
        self.store = JsonStore(db)

    def list_reviews(self, teacher_id: str, status: str | None = None, risk_level: str | None = None) -> dict[str, Any]:
        snapshots = self._latest_real_student_snapshots()
        items = []
        for snapshot in snapshots:
            state = self._review_state(snapshot, teacher_id)
            if status and state.status != status:
                continue
            if risk_level and self._snapshot_risk_level(snapshot) != risk_level:
                continue
            notes = self._notes_for_snapshot(snapshot["id"], teacher_id)
            flag = self._watch_flag(snapshot, teacher_id)
            items.append(self._build_list_item(snapshot, state, notes, flag))
        summary = self._summary(items)
        return TeacherReviewListResponse(teacher_id=teacher_id, reviews=items, summary=summary).model_dump(mode="json")

    def get_detail(self, snapshot_id: str, teacher_id: str) -> dict[str, Any]:
        snapshot = self._student_snapshot(snapshot_id)
        if snapshot is None:
            raise KeyError("snapshot not found")
        detail = TeacherReviewDetail(
            snapshot=snapshot,
            review_state=self._review_state(snapshot, teacher_id),
            notes=self._notes_for_snapshot(snapshot_id, teacher_id),
            watch_flag=self._watch_flag(snapshot, teacher_id),
        )
        return detail.model_dump(mode="json")

    def save_review_state(self, snapshot_id: str, teacher_id: str, payload: ReviewStateRequest) -> dict[str, Any]:
        snapshot = self._student_snapshot(snapshot_id)
        if snapshot is None:
            raise KeyError("snapshot not found")
        state = TeacherReviewState(
            snapshot_id=snapshot["id"],
            student_id=snapshot["student_id"],
            teacher_id=teacher_id,
            status=payload.status,
            comment=payload.comment.strip(),
            risk_level=payload.risk_level.strip(),
            last_action="SAVE_REVIEW_STATE",
            updated_at=datetime.now(timezone.utc),
        )
        self.store.upsert(
            self.MODULE,
            "review_state",
            snapshot["id"],
            state.model_dump(mode="json"),
            owner_id=teacher_id,
            status=state.status,
        )
        return self.get_detail(snapshot_id, teacher_id)

    def add_note(self, snapshot_id: str, teacher_id: str, payload: ReviewNoteRequest) -> dict[str, Any]:
        snapshot = self._student_snapshot(snapshot_id)
        if snapshot is None:
            raise KeyError("snapshot not found")
        note = TeacherReviewNote(
            note_id=make_record_key("note"),
            snapshot_id=snapshot["id"],
            student_id=snapshot["student_id"],
            teacher_id=teacher_id,
            comment=payload.comment.strip(),
            note_type=payload.note_type,
            created_at=datetime.now(timezone.utc),
        )
        self.store.create(
            self.MODULE,
            "review_note",
            note.model_dump(mode="json"),
            prefix="note",
            owner_id=teacher_id,
            status="ACTIVE",
        )
        return self.get_detail(snapshot_id, teacher_id)

    def upsert_watch_flag(self, student_id: str, teacher_id: str, payload: WatchFlagRequest) -> dict[str, Any]:
        snapshot = self._latest_snapshot_for_student(student_id)
        if snapshot is None:
            raise KeyError("snapshot not found")
        flag = TeacherWatchFlag(
            student_id=student_id,
            teacher_id=teacher_id,
            snapshot_id=snapshot["id"],
            pinned=bool(payload.pinned),
            reason=payload.reason.strip(),
            updated_at=datetime.now(timezone.utc),
        )
        self.store.upsert(
            self.MODULE,
            "watch_flag",
            self._watch_flag_key(student_id, teacher_id),
            flag.model_dump(mode="json"),
            owner_id=teacher_id,
            status="PINNED" if payload.pinned else "UNPINNED",
        )
        return self.get_detail(snapshot["id"], teacher_id)

    def delete_watch_flag(self, student_id: str, teacher_id: str) -> dict[str, Any]:
        self.store.delete(self.MODULE, "watch_flag", self._watch_flag_key(student_id, teacher_id))
        snapshot = self._latest_snapshot_for_student(student_id)
        if snapshot is None:
            raise KeyError("snapshot not found")
        return self.get_detail(snapshot["id"], teacher_id)

    def weak_points(self) -> dict[str, Any]:
        weak_points = []
        for snapshot in self._student_snapshots():
            risk = self._snapshot_risk_level(snapshot)
            if risk in {"medium", "high"}:
                weak_points.append(
                    {
                        "snapshot_id": snapshot["id"],
                        "student_id": snapshot["student_id"],
                        "risk_level": risk,
                        "min_mastery_score": self._min_mastery_score(snapshot),
                        "knowledge_points": [item.get("knowledge_point_id") for item in snapshot.get("assessments", []) if item.get("knowledge_point_id")],
                    }
                )
        return {"weak_points": weak_points[:50], "count": len(weak_points)}

    def _student_snapshots(self) -> list[dict[str, Any]]:
        snapshots = self.store.list_payloads(self.STUDENT_MODULE, "snapshot")
        return sorted(snapshots, key=lambda item: (str(item.get("student_id", "")), int(item.get("version", 0)), str(item.get("id", ""))))

    def _latest_real_student_snapshots(self) -> list[dict[str, Any]]:
        latest_by_student: dict[str, dict[str, Any]] = {}
        for snapshot in self._student_snapshots():
            student_id = str(snapshot.get("student_id") or "").strip()
            if not student_id:
                continue
            current = latest_by_student.get(student_id)
            if current is None or self._snapshot_sort_key(snapshot) > self._snapshot_sort_key(current):
                latest_by_student[student_id] = snapshot

        enriched = []
        for student_id, snapshot in latest_by_student.items():
            account = self._student_account(student_id)
            if account is None:
                continue
            enriched.append(self._enrich_snapshot_with_account(snapshot, account))
        return sorted(enriched, key=lambda item: (str(item.get("class_name", "")), str(item.get("student_name", "")), str(item.get("student_id", ""))))

    def _student_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        return self.store.get_payload(self.STUDENT_MODULE, "snapshot", snapshot_id)

    def _latest_snapshot_for_student(self, student_id: str) -> dict[str, Any] | None:
        snapshots = [item for item in self._student_snapshots() if item.get("student_id") == student_id]
        if not snapshots:
            return None
        return sorted(snapshots, key=self._snapshot_sort_key)[-1]

    def _snapshot_sort_key(self, snapshot: dict[str, Any]) -> tuple[int, str]:
        try:
            version = int(snapshot.get("version", 0) or 0)
        except (TypeError, ValueError):
            version = 0
        return (version, str(snapshot.get("id") or snapshot.get("snapshot_id") or ""))

    def _student_account(self, student_id: str) -> UserAccount | None:
        return (
            self.db.query(UserAccount)
            .filter(
                UserAccount.role == "student",
                or_(UserAccount.username == student_id, UserAccount.student_id == student_id),
            )
            .first()
        )

    def _enrich_snapshot_with_account(self, snapshot: dict[str, Any], account: UserAccount) -> dict[str, Any]:
        enriched = dict(snapshot)
        enriched["student_id"] = account.student_id or account.username
        enriched["username"] = account.username
        enriched["student_name"] = account.real_name or account.username
        enriched["class_name"] = account.class_name or ""
        enriched["avatar_path"] = account.avatar_path or ""
        return enriched

    def _teacher_records(self, record_type: str, teacher_id: str) -> list[dict[str, Any]]:
        return self.store.list_payloads(self.MODULE, record_type, owner_id=teacher_id)

    def _review_state(self, snapshot: dict[str, Any], teacher_id: str) -> TeacherReviewState:
        record = self.store.get_payload(self.MODULE, "review_state", snapshot["id"], owner_id=teacher_id)
        if record is None:
            return TeacherReviewState(snapshot_id=snapshot["id"], student_id=snapshot["student_id"], teacher_id=teacher_id)
        return TeacherReviewState.model_validate(record)

    def _notes_for_snapshot(self, snapshot_id: str, teacher_id: str) -> list[TeacherReviewNote]:
        notes = [
            TeacherReviewNote.model_validate(record)
            for record in self._teacher_records("review_note", teacher_id)
            if record.get("snapshot_id") == snapshot_id
        ]
        return sorted(notes, key=lambda item: str(item.created_at or ""))

    def _watch_flag_key(self, student_id: str, teacher_id: str) -> str:
        return f"{teacher_id}:{student_id}"

    def _watch_flag(self, snapshot: dict[str, Any], teacher_id: str) -> TeacherWatchFlag:
        record = self.store.get_payload(self.MODULE, "watch_flag", self._watch_flag_key(snapshot["student_id"], teacher_id), owner_id=teacher_id)
        if record is None:
            return TeacherWatchFlag(snapshot_id=snapshot["id"], student_id=snapshot["student_id"], teacher_id=teacher_id)
        return TeacherWatchFlag.model_validate(record)

    def _build_list_item(self, snapshot: dict[str, Any], state: TeacherReviewState, notes: list[TeacherReviewNote], flag: TeacherWatchFlag) -> TeacherReviewListItem:
        return TeacherReviewListItem(snapshot=snapshot, review_state=state, notes_count=len(notes), watch_flag=flag)

    def _summary(self, items: list[TeacherReviewListItem]) -> dict[str, Any]:
        summary = {
            "total": len(items),
            "pending": 0,
            "reviewed": 0,
            "risk_confirmed": 0,
            "risk_dismissed": 0,
            "observing": 0,
            "pinned": 0,
        }
        for item in items:
            if item.review_state.status == "PENDING":
                summary["pending"] += 1
            elif item.review_state.status == "REVIEWED":
                summary["reviewed"] += 1
            elif item.review_state.status == "RISK_CONFIRMED":
                summary["risk_confirmed"] += 1
            elif item.review_state.status == "RISK_DISMISSED":
                summary["risk_dismissed"] += 1
            elif item.review_state.status == "OBSERVING":
                summary["observing"] += 1
            if item.watch_flag.pinned:
                summary["pinned"] += 1
        return summary

    def _min_mastery_score(self, snapshot: dict[str, Any]) -> float:
        scores = [float(item["mastery_score"]) for item in snapshot.get("assessments", []) if item.get("mastery_score") is not None]
        if not scores:
            return 100.0
        return min(scores)

    def _snapshot_risk_level(self, snapshot: dict[str, Any]) -> str:
        score = self._min_mastery_score(snapshot)
        if score < 50:
            return "high"
        if score < 70:
            return "medium"
        return "low"
