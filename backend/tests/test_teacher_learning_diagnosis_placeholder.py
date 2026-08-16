import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints.teacher_learning_diagnosis import (
    add_review_note,
    delete_watch_flag,
    get_review_detail,
    list_diagnosis_reviews,
    list_weak_points,
    review_diagnosis_snapshot,
    upsert_watch_flag,
)
from app.core.security import create_access_token
from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore
from app.schemas.teacher_learning_diagnosis import ReviewNoteRequest, ReviewStateRequest, WatchFlagRequest
from app.services.learning_diagnosis.workflow import DiagnosisWorkflow


class TeacherLearningDiagnosisPlaceholderTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=engine)
        UserAccount.__table__.create(bind=engine)
        self.db = sessionmaker(bind=engine)()
        created = asyncio.run(DiagnosisWorkflow(self.db).create_session("student-1", {"course": "data-structures"}))
        self.session_id = created["session"]["id"]
        self.snapshot_id = created["snapshot"]["id"]
        self.student_id = created["snapshot"]["student_id"]
        self.baseline_snapshots = self.db.query(DomainRecord).filter_by(module="learning_diagnosis", record_type="snapshot").count()
        self.baseline_evidence = self.db.query(DomainRecord).filter_by(module="learning_diagnosis", record_type="evidence").count()
        self.baseline_sessions = self.db.query(DomainRecord).filter_by(module="learning_diagnosis", record_type="session").count()

    def tearDown(self):
        self.db.close()

    def test_student_cannot_access_review_list(self):
        token = create_access_token("student-1", "student")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(list_diagnosis_reviews(f"Bearer {token}", self.db))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_teacher_review_writes_teacher_module_only(self):
        token = create_access_token("teacher-1", "teacher")
        with patch("app.services.learning_diagnosis.workflow.DiagnosisWorkflow.refresh_session", side_effect=AssertionError("refresh_session must not be called")):
            result = asyncio.run(
                review_diagnosis_snapshot(
                    self.snapshot_id,
                    ReviewStateRequest(status="RISK_CONFIRMED", comment="continue_observing", risk_level="high"),
                    f"Bearer {token}",
                    self.db,
                )
            )

        self.assertEqual(result["data"]["review_state"]["status"], "RISK_CONFIRMED")
        self.assertEqual(result["data"]["snapshot"]["id"], self.snapshot_id)
        self.assertEqual(result["data"]["snapshot"]["review"], {})
        self.assertEqual(self.db.query(DomainRecord).filter_by(module="learning_diagnosis", record_type="snapshot").count(), self.baseline_snapshots)
        self.assertEqual(self.db.query(DomainRecord).filter_by(module="learning_diagnosis", record_type="evidence").count(), self.baseline_evidence)
        self.assertEqual(self.db.query(DomainRecord).filter_by(module="learning_diagnosis", record_type="session").count(), self.baseline_sessions)
        teacher_records = self.db.query(DomainRecord).filter_by(module="teacher_learning_diagnosis").all()
        self.assertTrue(any(record.record_type == "review_state" for record in teacher_records))
        self.assertFalse(any(record.record_type in {"snapshot", "evidence", "session", "path_version", "activity_event", "processing_receipt"} for record in teacher_records))

    def test_teacher_note_and_watch_flag_are_saved_in_teacher_module(self):
        token = create_access_token("teacher-1", "teacher")
        note_result = asyncio.run(
            add_review_note(
                self.snapshot_id,
                ReviewNoteRequest(comment="focus_on_reasoning_steps", note_type="observation"),
                f"Bearer {token}",
                self.db,
            )
        )
        watch_result = asyncio.run(
            upsert_watch_flag(
                self.student_id,
                WatchFlagRequest(pinned=True, reason="follow_up"),
                f"Bearer {token}",
                self.db,
            )
        )
        detail = asyncio.run(get_review_detail(self.snapshot_id, f"Bearer {token}", self.db))
        weak_points = asyncio.run(list_weak_points(f"Bearer {token}", self.db))
        delete_result = asyncio.run(delete_watch_flag(self.student_id, f"Bearer {token}", self.db))

        self.assertEqual(note_result["data"]["notes"][-1]["comment"], "focus_on_reasoning_steps")
        self.assertTrue(watch_result["data"]["watch_flag"]["pinned"])
        self.assertFalse(delete_result["data"]["watch_flag"]["pinned"])
        self.assertEqual(detail["data"]["watch_flag"]["student_id"], self.student_id)
        self.assertEqual(detail["data"]["notes"][-1]["comment"], "focus_on_reasoning_steps")
        self.assertIn("weak_points", weak_points["data"])
        self.assertEqual(self.db.query(DomainRecord).filter_by(module="learning_diagnosis", record_type="snapshot").count(), self.baseline_snapshots)
        self.assertEqual(self.db.query(DomainRecord).filter_by(module="learning_diagnosis", record_type="evidence").count(), self.baseline_evidence)

    def test_review_list_uses_real_student_accounts_with_latest_snapshot_only(self):
        self.db.add_all(
            [
                UserAccount(username="20230001", role="student", real_name="林知行", student_id="20230001", class_name="计科 2301"),
                UserAccount(username="20230002", role="student", real_name="周明远", student_id="20230002", class_name="计科 2302"),
                UserAccount(username="teacher-1", role="teacher", real_name="张老师", teacher_id="T001", class_name="计科 2301"),
            ]
        )
        self.db.commit()

        store = JsonStore(self.db)
        old_snapshot = {
            "snapshot_id": "snapshot-old-real",
            "student_id": "20230001",
            "version": 1,
            "assessments": [{"knowledge_point_id": "array", "mastery_score": 88}],
        }
        latest_snapshot = {
            "snapshot_id": "snapshot-latest-real",
            "student_id": "20230001",
            "version": 2,
            "assessments": [{"knowledge_point_id": "linked_list", "mastery_score": 61}],
        }
        orphan_snapshot = {
            "snapshot_id": "snapshot-orphan",
            "student_id": "demo-student",
            "version": 1,
            "assessments": [{"knowledge_point_id": "stack", "mastery_score": 42}],
        }
        store.upsert("learning_diagnosis", "snapshot", old_snapshot["snapshot_id"], old_snapshot, owner_id="20230001", status="GENERATED")
        store.upsert("learning_diagnosis", "snapshot", latest_snapshot["snapshot_id"], latest_snapshot, owner_id="20230001", status="GENERATED")
        store.upsert("learning_diagnosis", "snapshot", orphan_snapshot["snapshot_id"], orphan_snapshot, owner_id="demo-student", status="GENERATED")

        token = create_access_token("teacher-1", "teacher")
        result = asyncio.run(list_diagnosis_reviews(f"Bearer {token}", self.db, status=None, risk_level=None))

        reviews = result["data"]["reviews"]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["snapshot"]["id"], "snapshot-latest-real")
        self.assertEqual(reviews[0]["snapshot"]["student_id"], "20230001")
        self.assertEqual(reviews[0]["snapshot"]["student_name"], "林知行")
        self.assertEqual(reviews[0]["snapshot"]["class_name"], "计科 2301")
        self.assertEqual(reviews[0]["snapshot"]["username"], "20230001")


if __name__ == "__main__":
    unittest.main()
