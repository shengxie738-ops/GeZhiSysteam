import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost/api/v1")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.services.learning_diagnosis.contracts import (
    DiagnosisSnapshot,
    EvidenceProcessingReceipt,
    EvidenceRecord,
    GoalContentAssociation,
    GoalVersion,
    KnowledgeAssessment,
    LearningActivityEvent,
    PathTask,
    Provenance,
)
from app.models.domain_record import DomainRecord
from app.services.learning_diagnosis.evidence_store import LearningDiagnosisStore
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class LearningDiagnosisContractsTest(unittest.TestCase):
    def test_evidence_requires_provenance_and_knowledge_points(self):
        evidence = EvidenceRecord(
            evidence_id="ev-1",
            student_id="student-1",
            source_type="SANDBOX",
            knowledge_point_ids=["linked_list_boundary"],
            result={"status": "PASSED"},
            observed_at=datetime.now(timezone.utc),
            provenance=Provenance(source="mock", reliability=0.9),
        )
        self.assertEqual(evidence.provenance.source, "mock")
        with self.assertRaises(ValueError):
            EvidenceRecord(
                evidence_id="ev-2",
                student_id="student-1",
                source_type="SANDBOX",
                knowledge_point_ids=[],
                result={},
                observed_at=datetime.now(timezone.utc),
                provenance=Provenance(source="mock", reliability=0.9),
            )

    def test_git_disabled_keeps_practice_score_null(self):
        assessment = KnowledgeAssessment(
            knowledge_point_id="linked_list_boundary",
            mastery_score=58,
            practice_score=None,
            state="unstable",
            confidence=0.86,
        )
        self.assertIsNone(assessment.practice_score)
        with self.assertRaises(ValueError):
            DiagnosisSnapshot(
                snapshot_id="snap-1",
                session_id="session-1",
                student_id="student-1",
                version=1,
                path_version=1,
                trigger_type="INITIAL",
                include_git_evidence=False,
                evidence_refs=[],
                assessments=[assessment.model_copy(update={"practice_score": 0})],
            )

    def test_snapshot_is_versioned_and_refs_evidence(self):
        snapshot = DiagnosisSnapshot(
            snapshot_id="snap-1",
            session_id="session-1",
            student_id="student-1",
            version=2,
            path_version=2,
            trigger_type="INDEPENDENT_RETEST_COMPLETED",
            include_git_evidence=False,
            evidence_refs=["ev-1"],
            assessments=[],
        )
        self.assertEqual(snapshot.version, 2)
        self.assertEqual(snapshot.evidence_refs, ["ev-1"])

    def test_mastered_requires_independent_retest_flag(self):
        with self.assertRaises(ValueError):
            KnowledgeAssessment(
                knowledge_point_id="linked_list_boundary",
                mastery_score=100,
                state="mastered",
                confidence=0.95,
                independent_retest_passed=False,
            )

    def test_path_task_extended_fields_keep_legacy_construction_compatible(self):
        legacy = PathTask(
            task_id="task-legacy",
            title="链表边界练习",
            knowledge_point_ids=["linked_list_boundary"],
            task_type="CODING_PRACTICE",
            difficulty=2,
            estimated_minutes=20,
        )
        self.assertEqual(legacy.status, "PENDING")
        self.assertEqual(legacy.prerequisite_task_ids, [])
        self.assertEqual(legacy.content_payload, {})

        enriched = legacy.model_copy(
            update={
                "learning_objective": "能够独立处理空链表和单节点链表",
                "why_this_task": "当前证据显示边界条件不稳定",
                "source_type": "EXISTING_EXAM",
                "source_ref": "exam-12/question-3",
                "content_payload": {"question_id": "question-3"},
                "priority": 90,
                "prerequisite_task_ids": ["task-review"],
                "status": "IN_PROGRESS",
                "generation_metadata": {"match_method": "RULE"},
            }
        )
        self.assertEqual(enriched.source_ref, "exam-12/question-3")
        self.assertEqual(enriched.priority, 90)

        with self.assertRaises(ValueError):
            PathTask(
                task_id="task-invalid-source",
                title="无效来源",
                knowledge_point_ids=["linked_list_boundary"],
                task_type="CODING_PRACTICE",
                difficulty=2,
                estimated_minutes=20,
                source_type="UNTRUSTED_SOURCE",
            )
        with self.assertRaises(ValueError):
            PathTask(
                task_id="task-invalid-hints",
                title="无效提示等级",
                knowledge_point_ids=["linked_list_boundary"],
                task_type="CODING_PRACTICE",
                difficulty=2,
                estimated_minutes=20,
                allowed_hint_levels=[0, 1, 6],
            )

    def test_goal_association_event_and_receipt_contracts_are_structured(self):
        now = datetime.now(timezone.utc)
        goal = GoalVersion(
            goal_version_id="goal-1",
            session_id="session-1",
            student_id="student-1",
            raw_goal_text="四周内掌握链表并完成相关编程题",
            course_id="course-data-structure",
            course_name="数据结构",
            deadline=now,
            weekly_minutes=180,
            self_reported_difficulty="MEDIUM",
            reuse_existing_evidence=True,
            parsed_success_criteria={"required_score": 80},
            created_at=now,
        )
        association = GoalContentAssociation(
            association_id="assoc-1",
            goal_version_id=goal.goal_version_id,
            student_id=goal.student_id,
            content_type="EXAM_QUESTION",
            content_id="question-3",
            source_module="exam",
            source_route="/student/exams/exam-12",
            knowledge_point_ids=["linked_list_boundary"],
            relevance_score=0.92,
            relevance_level="HIGH",
            match_method="HYBRID",
            match_reason="题目覆盖链表边界条件",
            model_version="agent-planner-v1",
            content_version="v2",
            active=True,
            created_at=now,
            updated_at=now,
        )
        event_a = LearningActivityEvent(
            student_id=goal.student_id,
            source_module=association.source_module,
            content_type=association.content_type,
            content_id=association.content_id,
            attempt_id="attempt-7",
            result_payload={"passed": True, "score": 92},
            status="COMPLETED",
            occurred_at=now,
        )
        event_b = LearningActivityEvent(
            student_id=goal.student_id,
            source_module=association.source_module,
            content_type=association.content_type,
            content_id=association.content_id,
            attempt_id="attempt-7",
            result_payload={"passed": True, "score": 92},
            status="COMPLETED",
            occurred_at=now + timedelta(seconds=30),
        )
        receipt = EvidenceProcessingReceipt(
            receipt_id="receipt-1",
            event_id=event_a.event_id,
            session_id=goal.session_id,
            goal_version_id=goal.goal_version_id,
            association_id=association.association_id,
            evidence_id="evidence-1",
            snapshot_id="snapshot-2",
            path_version=2,
            deduplication_key=event_a.deduplication_key,
            created_at=now,
        )

        self.assertEqual(event_a.event_id, event_b.event_id)
        self.assertEqual(event_a.deduplication_key, event_b.deduplication_key)
        self.assertEqual(event_a.processing_status, "PENDING")
        self.assertEqual(event_a.retry_count, 0)
        self.assertEqual(receipt.path_version, 2)

        with self.assertRaises(ValueError):
            event_a.model_copy(update={"status": "UNKNOWN"}).model_validate(
                event_a.model_copy(update={"status": "UNKNOWN"}).model_dump()
            )
        with self.assertRaises(ValueError):
            event_a.model_copy(update={"processing_status": "UNKNOWN"}).model_validate(
                event_a.model_copy(update={"processing_status": "UNKNOWN"}).model_dump()
            )


class LearningDiagnosisContractStoreTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.store = LearningDiagnosisStore(self.db)
        self.now = datetime.now(timezone.utc)

    def tearDown(self):
        self.db.close()

    def test_store_crud_and_idempotency_lookup_for_new_contracts(self):
        goal = self.store.create_goal_version(
            {
                "goal_version_id": "goal-1",
                "session_id": "session-1",
                "student_id": "student-1",
                "raw_goal_text": "掌握链表",
                "course_name": "数据结构",
                "weekly_minutes": 180,
                "created_at": self.now,
            }
        )
        self.assertEqual(self.store.get_goal_version("goal-1", "student-1")["raw_goal_text"], "掌握链表")
        updated_goal = self.store.update_goal_version("goal-1", "student-1", {"weekly_minutes": 240})
        self.assertEqual(updated_goal["weekly_minutes"], 240)
        self.assertEqual(len(self.store.list_goal_versions("student-1", "session-1")), 1)

        association = self.store.create_content_association(
            {
                "association_id": "assoc-1",
                "goal_version_id": "goal-1",
                "student_id": "student-1",
                "content_type": "EXAM_QUESTION",
                "content_id": "question-3",
                "source_module": "exam",
                "knowledge_point_ids": ["linked_list_boundary"],
                "relevance_score": 0.9,
                "relevance_level": "HIGH",
                "match_method": "RULE",
                "created_at": self.now,
                "updated_at": self.now,
            }
        )
        self.assertEqual(association["association_id"], "assoc-1")
        self.assertEqual(
            self.store.find_content_association("goal-1", "EXAM_QUESTION", "question-3", "student-1")["association_id"],
            "assoc-1",
        )
        self.assertFalse(self.store.update_content_association("assoc-1", "student-1", {"active": False})["active"])

        event_payload = {
            "student_id": "student-1",
            "source_module": "exam",
            "content_type": "EXAM_QUESTION",
            "content_id": "question-3",
            "attempt_id": "attempt-7",
            "result_payload": {"passed": True},
            "status": "COMPLETED",
            "occurred_at": self.now,
        }
        event = self.store.create_activity_event(event_payload)
        duplicate = self.store.create_activity_event(event_payload)
        self.assertEqual(event["event_id"], duplicate["event_id"])
        self.assertEqual(len(self.store.list_activity_events("student-1")), 1)
        self.assertEqual(
            self.store.find_activity_event_by_deduplication_key(event["deduplication_key"], "student-1")["event_id"],
            event["event_id"],
        )
        processed = self.store.update_activity_event(event["event_id"], "student-1", {"processing_status": "PROCESSED"})
        self.assertEqual(processed["processing_status"], "PROCESSED")

        receipt_payload = {
            "receipt_id": "receipt-1",
            "event_id": event["event_id"],
            "session_id": "session-1",
            "goal_version_id": "goal-1",
            "association_id": "assoc-1",
            "evidence_id": "evidence-1",
            "snapshot_id": "snapshot-2",
            "path_version": 2,
            "deduplication_key": event["deduplication_key"],
            "created_at": self.now,
        }
        receipt = self.store.create_processing_receipt(receipt_payload)
        self.assertEqual(self.store.get_processing_receipt("receipt-1", "student-1")["event_id"], event["event_id"])
        self.assertEqual(
            self.store.find_processing_receipt_by_deduplication_key(event["deduplication_key"], "student-1")["receipt_id"],
            receipt["receipt_id"],
        )
        self.assertEqual(
            self.store.update_processing_receipt("receipt-1", "student-1", {"snapshot_id": "snapshot-3"})["snapshot_id"],
            "snapshot-3",
        )

    def test_same_attempt_updates_one_event_even_when_result_and_status_change(self):
        base = {
            "student_id": "student-1",
            "source_module": "exam",
            "content_type": "EXAM_QUESTION",
            "content_id": "question-3",
            "attempt_id": "attempt-7",
            "result_payload": {"passed": False, "score": 40},
            "status": "FAILED",
            "occurred_at": self.now,
        }
        first = self.store.create_activity_event(base)
        latest = self.store.create_activity_event(
            {
                **base,
                "result_payload": {"passed": True, "score": 92},
                "status": "COMPLETED",
                "occurred_at": self.now + timedelta(seconds=30),
            }
        )

        self.assertEqual(first["event_id"], latest["event_id"])
        self.assertEqual(first["deduplication_key"], latest["deduplication_key"])
        self.assertEqual(latest["status"], "COMPLETED")
        self.assertEqual(latest["result_payload"]["score"], 92)
        self.assertEqual(len(self.store.list_activity_events("student-1")), 1)

    def test_processing_receipt_rejects_unknown_event_and_inherits_owner(self):
        receipt = {
            "receipt_id": "receipt-unknown",
            "event_id": "activity-does-not-exist",
            "session_id": "session-1",
            "goal_version_id": "goal-1",
            "association_id": "assoc-1",
            "evidence_id": "evidence-1",
            "snapshot_id": "snapshot-2",
            "path_version": 2,
            "deduplication_key": "learning-activity:unknown",
            "created_at": self.now,
        }
        with self.assertRaisesRegex(ValueError, "activity event does not exist"):
            self.store.create_processing_receipt(receipt)

        event = self.store.create_activity_event(
            {
                "student_id": "student-1",
                "source_module": "exam",
                "content_type": "EXAM_QUESTION",
                "content_id": "question-3",
                "attempt_id": "attempt-7",
                "result_payload": {"passed": True},
                "status": "COMPLETED",
                "occurred_at": self.now,
            }
        )
        created = self.store.create_processing_receipt(
            {
                **receipt,
                "receipt_id": "receipt-1",
                "event_id": event["event_id"],
                "deduplication_key": event["deduplication_key"],
            }
        )
        self.assertEqual(created["receipt_id"], "receipt-1")
        self.assertIsNone(self.store.get_processing_receipt("receipt-1", "student-2"))
        self.assertIsNotNone(self.store.get_processing_receipt("receipt-1", "student-1"))

    def test_goal_change_creates_new_version_and_preserves_history(self):
        first = self.store.create_goal_version(
            {
                "goal_version_id": "goal-1",
                "session_id": "session-1",
                "student_id": "student-1",
                "raw_goal_text": "掌握链表",
                "created_at": self.now,
            }
        )
        second = self.store.create_goal_version(
            {
                "goal_version_id": "goal-2",
                "session_id": "session-1",
                "student_id": "student-1",
                "raw_goal_text": "掌握二叉树",
                "created_at": self.now + timedelta(seconds=30),
            }
        )

        history = self.store.list_goal_versions("student-1", "session-1")
        self.assertEqual([item["goal_version_id"] for item in history], [first["goal_version_id"], second["goal_version_id"]])
        self.assertEqual(self.store.get_goal_version("goal-1", "student-1")["raw_goal_text"], "掌握链表")
        with self.assertRaisesRegex(ValueError, "metadata-only"):
            self.store.update_goal_version("goal-1", "student-1", {"raw_goal_text": "覆盖旧目标"})


if __name__ == "__main__":
    unittest.main()
