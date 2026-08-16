import asyncio
import json
import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost/api/v1")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test-agent")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test-chat")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test-dataset")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.domain_record import DomainRecord
from app.services.learning_diagnosis.activity_listener import ActivityListener
from app.services.learning_diagnosis.contracts import LearningActivityEvent
from app.services.learning_diagnosis.git_practice_service import GitPracticeService
from app.services.learning_diagnosis.hint_service import HintService
from app.services.learning_diagnosis.workflow import DiagnosisWorkflow
from app.services.learning_diagnosis.knowledge_retriever import KnowledgeChunk, KnowledgeRetrievalResult


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
                    "success_criteria": ["能够解释并实现遍历"],
                    "search_query": "树的遍历",
                }
            ],
        }


class _HintModel:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {}
        self.error = error
        self.calls = []

    async def ainvoke(self, prompt):
        self.calls.append(prompt)
        if self.error:
            raise self.error
        return type("Response", (), {"content": json.dumps(self.payload, ensure_ascii=False)})()


class _GitService:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def get_learning_evidence(self, *, student_id, session):
        self.calls += 1
        return self.payload


class LearningDiagnosisIntelligentLoopTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def _workflow(self, **kwargs):
        return DiagnosisWorkflow(
            self.db,
            retriever_mode="mock",
            goal_orchestrator=_GoalOrchestrator(),
            **kwargs,
        )

    def test_hint_service_returns_traceable_ai_content_and_fallback(self):
        model = _HintModel({"content": "先找递归终止条件", "focus": "空节点", "based_on_attempt": "未处理空树"})
        task = {"task_id": "task-1", "task_type": "GUIDED_PRACTICE", "title": "树遍历", "content_payload": {}}
        result = asyncio.run(HintService(model_client=model).generate(task, 2, attempt={"answer": "只写了递归"}))
        self.assertEqual(result["content"], "先找递归终止条件")
        self.assertEqual(result["focus"], "空节点")
        self.assertEqual(result["based_on_attempt"], "未处理空树")
        self.assertEqual(result["model_metadata"]["status"], "AI_GENERATED")

        fallback = asyncio.run(HintService(model_client=_HintModel(error=RuntimeError("offline"))).generate(task, 1, attempt={}))
        self.assertTrue(fallback["content"])
        self.assertEqual(fallback["model_metadata"]["status"], "DEGRADED")
        self.assertIn("offline", fallback["model_metadata"]["error"])

    def test_hint_checks_task_membership_and_retest_never_exceeds_level_one(self):
        workflow = self._workflow(hint_service=HintService(model_client=_HintModel({"content": "检查边界", "focus": "边界", "based_on_attempt": "本次尝试"})))
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        retest = next(task for task in created["path"]["tasks"] if task["task_type"] == "INDEPENDENT_RETEST")
        first = asyncio.run(workflow.request_hint(created["session"]["id"], "student-1", retest["task_id"], 5, attempt={"code": "pass"}))
        second = asyncio.run(workflow.request_hint(created["session"]["id"], "student-1", retest["task_id"], 5, attempt={"code": "pass"}))
        self.assertEqual(first["approved_level"], 1)
        self.assertEqual(second["approved_level"], 1)
        with self.assertRaisesRegex(KeyError, "TASK_NOT_IN_CURRENT_PATH"):
            asyncio.run(workflow.request_hint(created["session"]["id"], "student-1", "foreign-task", 1))

    def test_non_coding_submission_uses_answer_without_running_sandbox(self):
        workflow = self._workflow()
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        review = next(task for task in created["path"]["tasks"] if task["task_type"] == "KNOWLEDGE_REVIEW")

        class _ForbiddenSandbox:
            def run(self, *args, **kwargs):
                raise AssertionError("non-coding answer must not enter CodeSandbox")

        workflow.code_sandbox = _ForbiddenSandbox()
        result = asyncio.run(workflow.submit_task(
            created["session"]["id"], "student-1", review["task_id"], code="", answer="递归终止于空节点，并按根左右遍历"
        ))
        self.assertEqual(result["status"], "RECORDED")
        self.assertIsNone(result["execution_id"])
        evidence = next(item for item in workflow.store.list_evidence("student-1") if item["evidence_id"] == result["evidence_id"])
        self.assertEqual(evidence["result"]["task_type"], "KNOWLEDGE_REVIEW")
        self.assertGreater(evidence["result"]["score"], 0)

    def test_text_submission_prefers_ai_semantic_evaluation(self):
        class _Evaluator:
            async def evaluate(self, task, answer):
                return {"score": 91, "status": "AI_EVALUATED", "provider": "agent_tutor", "feedback": "概念和边界说明完整", "criteria": []}

        workflow = self._workflow()
        workflow.answer_evaluator = _Evaluator()
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        review = next(task for task in created["path"]["tasks"] if task["task_type"] == "KNOWLEDGE_REVIEW")
        result = asyncio.run(workflow.submit_task(created["session"]["id"], "student-1", review["task_id"], code="", answer="我会从递归终止和边界场景解释。"))
        evidence = next(item for item in workflow.store.list_evidence("student-1") if item["evidence_id"] == result["evidence_id"])
        self.assertEqual(evidence["result"]["score"], 91)
        self.assertEqual(evidence["result"]["evaluation_status"], "AI_EVALUATED")

    def test_successful_submission_marks_task_completed_in_new_path(self):
        workflow = self._workflow()
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        review = next(task for task in created["path"]["tasks"] if task["task_type"] == "KNOWLEDGE_REVIEW")
        result = asyncio.run(workflow.submit_task(created["session"]["id"], "student-1", review["task_id"], code="", answer="完整说明递归终止条件、正常场景、边界场景和验证方法。"))
        updated = next(task for task in result["path"]["tasks"] if task["task_id"] == review["task_id"])
        self.assertEqual(updated["status"], "COMPLETED")
        self.assertTrue(updated["completed_at"])

    def test_create_session_builds_content_associations(self):
        workflow = self._workflow()
        workflow.store.store.create("exams", "question", {"id": "question-tree", "title": "树的遍历", "knowledgeTags": ["tree_traversal"]}, prefix="question")
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        rows = workflow.store.list_content_associations("student-1", created["session"]["current_goal_version"])
        self.assertEqual(rows[0]["content_id"], "question-tree")

    def test_rag_chunk_becomes_task_material_and_source(self):
        class _Retriever:
            async def retrieve(self, request):
                return KnowledgeRetrievalResult(status="OK", provider="ragflow", chunks=[KnowledgeChunk(chunk_id="chunk-tree", title="树遍历课件", content="前序遍历按照根、左、右访问。", score=.93, dataset_id="ds", source_name="数据结构课件")])

        workflow = self._workflow(retriever=_Retriever())
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        review = next(task for task in created["path"]["tasks"] if task["task_type"] == "KNOWLEDGE_REVIEW")
        self.assertEqual(review["source_type"], "RAG_GENERATED")
        self.assertEqual(review["source_ref"], "chunk-tree")
        self.assertIn("前序遍历", review["content_payload"]["content"])

    def test_coding_submission_uses_task_test_cases_not_caller_answer(self):
        workflow = self._workflow()
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        coding = next(task for task in created["path"]["tasks"] if task["task_type"] == "CODING_PRACTICE")
        captured = {}

        class _Sandbox:
            def run(self, code, language, test_cases):
                captured["test_cases"] = test_cases
                return {"total": len(test_cases), "passed": len(test_cases), "results": []}

        workflow.code_sandbox = _Sandbox()
        asyncio.run(workflow.submit_task(created["session"]["id"], "student-1", coding["task_id"], code="def solve(x): return x", answer="not code"))
        self.assertEqual(captured["test_cases"], coding["content_payload"]["test_cases"])

    def test_independent_retest_submission_carries_type_and_coverage_into_mastery(self):
        workflow = self._workflow()
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        retest = next(task for task in created["path"]["tasks"] if task["task_type"] == "INDEPENDENT_RETEST")

        class _PassingSandbox:
            def run(self, code, language, test_cases):
                return {"total": len(test_cases), "passed": len(test_cases), "results": [{"passed": True} for _ in test_cases]}

        workflow.code_sandbox = _PassingSandbox()
        result = asyncio.run(workflow.submit_task(
            created["session"]["id"], "student-1", retest["task_id"], code="def solve(x): return x", hint_level=1, assessment_mode=True
        ))
        stored = next(item for item in workflow.store.list_evidence("student-1") if item["evidence_id"] == result["evidence_id"])
        assessment = next(item for item in result["snapshot"]["assessments"] if item["knowledge_point_id"] == "tree_traversal")
        self.assertEqual(stored["result"]["task_type"], "INDEPENDENT_RETEST")
        self.assertEqual(set(stored["result"]["coverage"]), {"NORMAL", "BOUNDARY", "EXCEPTION"})
        self.assertTrue(assessment["independent_retest_passed"])
        self.assertEqual(set(assessment["independent_retest_coverage"]), {"NORMAL", "BOUNDARY", "EXCEPTION"})
        self.assertEqual(assessment["state"], "mastered")

    def test_activity_listener_matches_active_goal_is_idempotent_and_ignores_unrelated(self):
        workflow = self._workflow()
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        goal_id = created["session"]["current_goal_version"]
        workflow.store.create_content_association({
            "association_id": "assoc-exam-1", "goal_version_id": goal_id, "student_id": "student-1",
            "content_type": "EXAM_QUESTION", "content_id": "question-1", "source_module": "exams",
            "knowledge_point_ids": ["tree_traversal"], "relevance_score": .9, "relevance_level": "HIGH",
            "match_method": "RULE", "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
        })
        listener = ActivityListener(workflow.store, refresh_callback=workflow.refresh_session)
        event = LearningActivityEvent(
            student_id="student-1", source_module="exams", content_type="EXAM_QUESTION", content_id="question-1",
            attempt_id="attempt-1", result_payload={"score": 88, "passed": True}, status="COMPLETED", occurred_at=datetime.now(timezone.utc),
        )
        first = asyncio.run(listener.handle(event))
        second = asyncio.run(listener.handle(event))
        self.assertEqual(first["status"], "PROCESSED")
        self.assertEqual(second["status"], "DUPLICATE")
        self.assertEqual(len(workflow.store.list_processing_receipts("student-1", event.event_id)), 1)
        self.assertEqual(len([e for e in workflow.store.list_evidence("student-1") if e.get("source_ref") == "exams:question-1:attempt-1"]), 1)
        assessment = next(item for item in first["snapshot"]["assessments"] if item["knowledge_point_id"] == "tree_traversal")
        self.assertEqual(assessment["mastery_score"], 88)
        self.assertIn("activity-", first["receipt"]["evidence_id"])

        unrelated = event.model_copy(update={"content_id": "not-related", "attempt_id": "attempt-2", "event_id": "", "deduplication_key": ""})
        ignored = asyncio.run(listener.handle(unrelated))
        self.assertEqual(ignored["status"], "IGNORED")

    def test_activity_listener_failure_is_retry_pending(self):
        workflow = self._workflow()
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        goal_id = created["session"]["current_goal_version"]
        workflow.store.create_content_association({
            "association_id": "assoc-homework", "goal_version_id": goal_id, "student_id": "student-1",
            "content_type": "HOMEWORK", "content_id": "hw-1", "source_module": "homework",
            "knowledge_point_ids": ["tree_traversal"], "relevance_score": .9, "relevance_level": "HIGH",
            "match_method": "RULE", "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
        })

        async def _broken_refresh(*args, **kwargs):
            raise RuntimeError("snapshot failure")

        listener = ActivityListener(workflow.store, refresh_callback=_broken_refresh)
        event = LearningActivityEvent(
            student_id="student-1", source_module="homework", content_type="HOMEWORK", content_id="hw-1",
            attempt_id="attempt-1", result_payload={"score": 80}, status="COMPLETED", occurred_at=datetime.now(timezone.utc),
        )
        result = asyncio.run(listener.handle(event))
        stored = workflow.store.get_activity_event(event.event_id, "student-1")
        self.assertEqual(result["status"], "RETRY_PENDING")
        self.assertEqual(stored["processing_status"], "RETRY_PENDING")
        self.assertEqual(stored["retry_count"], 1)

    def test_git_toggle_never_calls_service_when_off_and_filters_evidence_when_closed(self):
        service = _GitService({"knowledge_point_ids": ["tree_traversal"], "practice_score": 76, "source_ref": "repo/a.py", "relevant_files": ["a.py"]})
        workflow = self._workflow(git_practice_service=GitPracticeService(service=service))
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构", "include_git_evidence": False}))
        session_id = created["session"]["id"]
        off = asyncio.run(workflow.set_git_evidence(session_id, "student-1", False))
        self.assertEqual(service.calls, 0)
        self.assertFalse(off["session"]["include_git_evidence"])

        enabled = asyncio.run(workflow.set_git_evidence(session_id, "student-1", True))
        self.assertEqual(service.calls, 1)
        self.assertTrue(enabled["session"]["include_git_evidence"])
        git_items = [item for item in workflow.store.list_evidence("student-1") if item["source_type"] == "GIT"]
        self.assertEqual(git_items[-1]["result"]["practice_score"], 76)
        self.assertLess(git_items[-1]["provenance"]["reliability"], 0.8)
        self.assertTrue(git_items[-1]["result"]["uncertainty"])

        disabled = asyncio.run(workflow.set_git_evidence(session_id, "student-1", False))
        self.assertFalse(disabled["snapshot"]["include_git_evidence"])
        self.assertFalse(any(ref.startswith("git-") for ref in disabled["snapshot"]["evidence_refs"]))
        self.assertTrue(all(item["practice_score"] is None for item in disabled["snapshot"]["assessments"]))

    def test_git_no_relevant_code_produces_insufficient_data(self):
        service = _GitService({"knowledge_point_ids": [], "relevant_files": [], "summary": "未发现目标相关代码"})
        result = GitPracticeService(service=service).collect("student-1", {"include_git_evidence": True, "current_knowledge_points": [{"id": "tree_traversal"}]})
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["practice_score"])
        self.assertEqual(result["evidence"], [])

    def test_git_practice_aggregation_uses_reliability_weight(self):
        from app.services.learning_diagnosis.contracts import EvidenceRecord, Provenance
        from app.services.learning_diagnosis.rule_engine import RuleEngine

        now = datetime.now(timezone.utc)
        records = [
            EvidenceRecord(evidence_id="git-low", student_id="student-1", source_type="GIT", knowledge_point_ids=["tree_traversal"], result={"practice_score": 100}, observed_at=now, provenance=Provenance(source="git", reliability=.2), include_git_evidence=True),
            EvidenceRecord(evidence_id="git-high", student_id="student-1", source_type="GIT", knowledge_point_ids=["tree_traversal"], result={"practice_score": 50}, observed_at=now, provenance=Provenance(source="git", reliability=.6), include_git_evidence=True),
        ]
        result = RuleEngine().assess(records, ["tree_traversal"], True)["tree_traversal"]
        self.assertEqual(result["practice_score"], 62.5)


if __name__ == "__main__":
    unittest.main()
