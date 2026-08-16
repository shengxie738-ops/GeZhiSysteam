import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost/api/v1")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.domain_record import DomainRecord
from app.services.learning_diagnosis.evidence_providers import (
    ExistingSystemEvidenceProvider,
    GitEvidenceProvider,
    MockEvidenceProvider,
    SandboxEvidenceProvider,
)
from app.services.learning_diagnosis.evidence_store import LearningDiagnosisStore


class LearningDiagnosisEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.store = LearningDiagnosisStore(self.db)

    def tearDown(self):
        self.db.close()

    def test_mock_provider_returns_linked_list_evidence(self):
        evidence = MockEvidenceProvider().collect("student-1", {"include_git_evidence": False})
        self.assertGreaterEqual(len(evidence), 3)
        self.assertTrue(any(item.source_type == "SANDBOX" for item in evidence))
        self.assertTrue(all(item.student_id == "student-1" for item in evidence))

    def test_git_provider_skips_service_when_opt_in_is_false(self):
        service = Mock()
        evidence = GitEvidenceProvider(service).collect("student-1", {"include_git_evidence": False})
        self.assertEqual(evidence, [])
        service.assert_not_called()

    def test_git_provider_marks_scope_when_opt_in_is_true(self):
        service = Mock()
        service.get_learning_evidence.return_value = {
            "scope": ["PROJECT_CODE", "TEST_RESULT"],
            "summary": "脱敏项目测试结果",
            "source_ref": "repo-1",
        }
        evidence = GitEvidenceProvider(service).collect("student-1", {"include_git_evidence": True})
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].source_type, "GIT")
        self.assertTrue(evidence[0].include_git_evidence)
        self.assertEqual(evidence[0].result["scope"], ["PROJECT_CODE", "TEST_RESULT"])

    def test_sandbox_provider_maps_structured_result(self):
        execution = {
            "executionId": "exec-1",
            "status": "TEST_FAILED",
            "testSummary": {"total": 2, "passed": 1, "failed": 1},
            "knowledgePointIds": ["linked_list_boundary"],
        }
        evidence = SandboxEvidenceProvider().from_execution("student-1", execution)
        self.assertEqual(evidence[0].source_type, "SANDBOX")
        self.assertEqual(evidence[0].result["status"], "TEST_FAILED")

    def test_snapshot_store_creates_new_version_without_overwriting_previous(self):
        first = self.store.create_snapshot(
            {
                "snapshot_id": "snap-1",
                "session_id": "session-1",
                "student_id": "student-1",
                "version": 1,
                "path_version": 1,
                "trigger_type": "INITIAL",
                "include_git_evidence": False,
                "evidence_refs": [],
                "assessments": [],
            }
        )
        second = self.store.create_snapshot(
            {
                "snapshot_id": "snap-2",
                "session_id": "session-1",
                "student_id": "student-1",
                "version": 2,
                "path_version": 2,
                "trigger_type": "RETEST",
                "include_git_evidence": False,
                "evidence_refs": ["ev-1"],
                "assessments": [],
            }
        )
        self.assertEqual(first["version"], 1)
        self.assertEqual(second["version"], 2)
        self.assertEqual(len(self.store.list_snapshots("student-1")), 2)


if __name__ == "__main__":
    unittest.main()
