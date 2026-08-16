import asyncio
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints.learning_diagnosis import (
    create_diagnosis_session,
    create_diagnosis_goal,
    get_diagnosis_session,
    get_latest_diagnosis_session,
    get_diagnosis_path,
    request_task_hint,
    submit_diagnosis_task,
)
from app.core.security import create_access_token
from app.models.domain_record import DomainRecord
from app.schemas.learning_diagnosis import CreateDiagnosisGoalRequest, CreateDiagnosisSessionRequest, HintRequest, SubmitTaskRequest


class LearningDiagnosisApiTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def auth(self):
        return f"Bearer {create_access_token('student-1', 'student')}"

    def test_create_requires_authentication(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(create_diagnosis_session(CreateDiagnosisSessionRequest(student_id="student-1", course="数据结构"), None, self.db))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_latest_session_restores_dashboard_state(self):
        created = asyncio.run(create_diagnosis_session(CreateDiagnosisSessionRequest(student_id="student-1", course="数据结构"), self.auth(), self.db))
        result = asyncio.run(get_latest_diagnosis_session("student-1", self.db, self.auth()))
        self.assertEqual(result["data"]["session"]["id"], created["data"]["session"]["id"])
        self.assertTrue(result["data"]["snapshot"]["assessments"])
        self.assertTrue(result["data"]["path"]["tasks"])
        self.assertEqual(result["data"]["evidence"], [])

    def test_latest_session_returns_each_snapshot_evidence_once(self):
        payload = CreateDiagnosisSessionRequest(
            student_id="student-1",
            course="数据结构",
            existing_evidence=[
                {
                    "evidence_id": "evidence-one",
                    "source_type": "ASSIGNMENT",
                    "source_ref": "assignment-one",
                    "knowledge_point_ids": ["course_core_concept"],
                    "result": {"score": 70},
                    "reliability": 0.8,
                    "summary": "一次真实作业证据",
                }
            ],
        )
        asyncio.run(create_diagnosis_session(payload, self.auth(), self.db))
        # 模拟历史重复写入同一业务证据 ID，API 仍应按快照引用去重。
        asyncio.run(create_diagnosis_session(payload, self.auth(), self.db))
        result = asyncio.run(get_latest_diagnosis_session("student-1", self.db, self.auth()))
        refs = result["data"]["snapshot"]["evidence_refs"]
        evidence = result["data"]["evidence"]
        self.assertEqual([item["evidence_id"] for item in evidence], refs)
        self.assertEqual(len(evidence), len(set(refs)))

    def test_create_and_get_student_session(self):
        created = asyncio.run(create_diagnosis_session(CreateDiagnosisSessionRequest(student_id="student-1", course="数据结构"), self.auth(), self.db))
        self.assertEqual(created["code"], 200)
        session_id = created["data"]["session"]["id"]
        fetched = asyncio.run(get_diagnosis_session(session_id, "student-1", self.db, self.auth()))
        self.assertEqual(fetched["data"]["session"]["id"], session_id)

    def test_hint_request_is_progressive_in_assessment(self):
        created = asyncio.run(create_diagnosis_session(CreateDiagnosisSessionRequest(student_id="student-1", course="数据结构"), self.auth(), self.db))
        session_id = created["data"]["session"]["id"]
        task_id = created["data"]["path"]["tasks"][-1]["task_id"]
        result = asyncio.run(request_task_hint(task_id, session_id, HintRequest(requested_level=5, assessment_mode=True), "student-1", self.db, self.auth()))
        self.assertEqual(result["data"]["approved_level"], 1)

    def test_submit_task_returns_traceable_execution(self):
        created = asyncio.run(create_diagnosis_session(CreateDiagnosisSessionRequest(student_id="student-1", course="数据结构"), self.auth(), self.db))
        session_id = created["data"]["session"]["id"]
        task_id = created["data"]["path"]["tasks"][2]["task_id"]
        result = asyncio.run(submit_diagnosis_task(task_id, SubmitTaskRequest(student_id="student-1", session_id=session_id, code="print('ok')"), self.db, self.auth()))
        self.assertEqual(result["data"]["status"], "RECORDED")
        self.assertTrue(result["data"]["execution_id"])
        self.assertEqual(result["data"]["snapshot"]["session_id"], session_id)

    def test_path_endpoint_scopes_result_to_requested_session(self):
        first = asyncio.run(create_diagnosis_session(CreateDiagnosisSessionRequest(student_id="student-1", course="鏁版嵁缁撴瀯"), self.auth(), self.db))
        second = asyncio.run(create_diagnosis_session(CreateDiagnosisSessionRequest(student_id="student-1", course="Python"), self.auth(), self.db))
        first_id = first["data"]["session"]["id"]
        second_id = second["data"]["session"]["id"]
        result = asyncio.run(get_diagnosis_path(first_id, "student-1", self.db, self.auth()))
        paths = result["data"]["paths"]
        self.assertTrue(paths)
        self.assertTrue(all(path["session_id"] == first_id for path in paths))
        self.assertFalse(any(path["session_id"] == second_id for path in paths))

    def test_goal_request_schema_supports_new_and_legacy_fields(self):
        legacy = CreateDiagnosisSessionRequest(student_id="student-1", course="数据结构")
        modern = CreateDiagnosisGoalRequest(
            student_id="student-1",
            raw_goal_text="四周掌握树算法",
            course_id="course-ds",
            course_name="数据结构",
            deadline="2026-09-01",
            weekly_minutes=240,
            self_reported_difficulty="MEDIUM",
            reuse_existing_evidence=False,
        )
        self.assertEqual(legacy.course, "数据结构")
        self.assertEqual(modern.raw_goal_text, "四周掌握树算法")
        self.assertFalse(modern.reuse_existing_evidence)

    def test_create_goal_rejects_cross_student_scope(self):
        created = asyncio.run(create_diagnosis_session(CreateDiagnosisSessionRequest(student_id="student-1", course="数据结构"), self.auth(), self.db))
        session_id = created["data"]["session"]["id"]
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(create_diagnosis_goal(
                session_id,
                CreateDiagnosisGoalRequest(student_id="student-2", goal_text="掌握树", course_name="数据结构"),
                self.auth(),
                self.db,
            ))
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
