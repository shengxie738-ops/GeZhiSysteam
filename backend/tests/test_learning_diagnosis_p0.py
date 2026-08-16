import asyncio
import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.domain_record import DomainRecord
from app.schemas.learning_diagnosis import CreateDiagnosisSessionRequest
from app.services.learning_diagnosis.contracts import EvidenceRecord, Provenance
from app.services.learning_diagnosis.llm_explainer import LlmExplainer
from app.services.learning_diagnosis.path_planner import LearningPathPlanner
from app.services.learning_diagnosis.workflow import DiagnosisWorkflow


class _GoalOrchestrator:
    async def parse_goal(self, goal):
        return {
            "provider": "test",
            "status": "TEST",
            "error": None,
            "normalized_goal": {**goal, "course_name": goal.get("course_name") or goal.get("course") or "数据结构"},
            "knowledge_points": [
                {
                    "id": "tree_traversal",
                    "name": "树的遍历",
                    "description": "掌握树的前中后序遍历",
                    "success_criteria": ["能够实现遍历"],
                    "search_query": "树的遍历",
                },
            ],
        }


class _AsyncModel:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def ainvoke(self, prompt):
        self.calls.append(prompt)
        return type("Response", (), {"content": json.dumps(self.payload, ensure_ascii=False)})()


class LearningDiagnosisP0Test(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_default_session_has_no_mock_evidence_without_existing_records(self):
        workflow = DiagnosisWorkflow(
            self.db,
            retriever_mode="mock",
            goal_orchestrator=_GoalOrchestrator(),
        )
        result = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        self.assertEqual(result["snapshot"]["evidence_refs"], [])
        self.assertEqual(workflow.store.list_evidence("student-1"), [])

    def test_planner_builds_goal_specific_task_payload(self):
        path = LearningPathPlanner().plan(
            assessments={"tree_traversal": {"state": "unstable", "mastery_score": 40}},
            goal={"course_name": "数据结构", "raw_goal_text": "掌握树的遍历"},
            previous_path=None,
            knowledge_point_meta={
                "tree_traversal": {
                    "name": "树的遍历",
                    "description": "掌握树的前中后序遍历",
                    "success_criteria": ["能够实现遍历"],
                    "search_query": "树的遍历",
                }
            },
        )
        self.assertEqual([task.task_type for task in path.tasks], ["KNOWLEDGE_REVIEW", "GUIDED_PRACTICE", "CODING_PRACTICE", "INDEPENDENT_RETEST"])
        for task in path.tasks:
            self.assertTrue(task.learning_objective)
            self.assertTrue(task.why_this_task)
            self.assertTrue(task.source_type)
            self.assertEqual(task.knowledge_point_ids, ["tree_traversal"])
            self.assertTrue(task.content_payload)
        coding = next(task for task in path.tasks if task.task_type == "CODING_PRACTICE")
        self.assertNotEqual(coding.content_payload.get("test_cases", [{}])[0].get("expected"), "ok")

    def test_submit_rejects_task_not_in_current_path(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=_GoalOrchestrator())
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        with self.assertRaises(KeyError):
            asyncio.run(workflow.submit_task(created["session"]["id"], "student-1", "task-from-other-session", "print('ok')"))

    def test_change_goal_does_not_reuse_unrelated_evidence(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=_GoalOrchestrator())
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        workflow.store.create_evidence(
            EvidenceRecord(
                evidence_id="ev-unrelated",
                student_id="student-1",
                source_type="ASSIGNMENT",
                knowledge_point_ids=["sorting"],
                result={"score": 99},
                observed_at=created["snapshot"].get("created_at") or "2026-01-01T00:00:00Z",
                provenance=Provenance(source="test"),
                summary="unrelated",
            )
        )
        changed = asyncio.run(workflow.change_goal(created["session"]["id"], "student-1", {"course": "数据结构", "raw_goal_text": "树遍历"}))
        self.assertEqual(changed["snapshot"]["evidence_refs"], [])

    def test_schema_accepts_modern_goal_without_legacy_course(self):
        request = CreateDiagnosisSessionRequest(
            student_id="student-1",
            raw_goal_text="四周掌握树的遍历",
            course_name="数据结构",
        )
        self.assertEqual(request.course_name, "数据结构")

    def test_llm_explainer_calls_injected_model_and_validates_refs(self):
        model = _AsyncModel(
            {
                "summary": "基于证据的解释",
                "strengths": [{"text": "完成练习", "evidenceRefs": ["ev-1"]}],
                "weaknesses": [],
                "recommended_actions": [],
                "uncertainty_notes": [],
            }
        )
        explainer = LlmExplainer(model_client=model)
        result = asyncio.run(
            explainer.explain(
                {"knowledge_point_ids": ["tree_traversal"]},
                [{"evidenceId": "ev-1", "fact": "score=80"}],
                [],
            )
        )
        self.assertEqual(result.summary, "基于证据的解释")
        self.assertEqual(len(model.calls), 1)


if __name__ == "__main__":
    unittest.main()
