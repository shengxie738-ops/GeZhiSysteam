import asyncio
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.domain_record import DomainRecord
from app.repositories.json_store import JsonStore
from app.services.learning_diagnosis.workflow import DiagnosisWorkflow


class StaticGoalOrchestrator:
    async def parse_goal(self, goal):
        course = goal.get("course_name") or goal.get("course") or "数据结构"
        return {
            "provider": "test",
            "status": "TEST",
            "error": None,
            "normalized_goal": {**goal, "course_name": course, "raw_goal_text": goal.get("raw_goal_text") or goal.get("goal_text") or f"掌握{course}"},
            "knowledge_points": [
                {"id": "tree_traversal", "name": "树的遍历", "description": "掌握树的遍历", "success_criteria": ["能完成遍历"], "search_query": "树的遍历"},
                {"id": "tree_recursion", "name": "递归实现", "description": "掌握递归遍历", "success_criteria": ["能实现递归"], "search_query": "递归遍历"},
            ],
        }


class LearningDiagnosisWorkflowTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_demo_creates_snapshot_and_path(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        result = asyncio.run(workflow.create_session("student-1", {"course": "数据结构", "weeks_remaining": 4, "weekly_minutes": 180}))
        self.assertEqual(result["snapshot"]["version"], 1)
        self.assertEqual(result["path"]["path_version"], 1)
        self.assertEqual(result["snapshot"]["evidence_refs"], [])
        self.assertTrue(any(item["state"] == "insufficient_data" for item in result["snapshot"]["assessments"]))

    def test_existing_system_evidence_is_preserved_in_session_snapshot(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        evidence = [{
            "evidence_id": "demo-assignment",
            "source_type": "ASSIGNMENT",
            "source_ref": "assignment-1",
            "knowledge_point_ids": ["tree_traversal"],
            "result": {"score": 80},
            "summary": "existing assignment",
        }]
        result = asyncio.run(workflow.create_session("student-1", {"course": "数据结构", "existing_evidence": evidence}))
        self.assertEqual(result["snapshot"]["evidence_refs"], ["demo-assignment"])

    def test_sandbox_error_keeps_old_path(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        refreshed = asyncio.run(workflow.refresh_session(created["session"]["id"], "student-1", {"sandbox_status": "SANDBOX_ERROR"}))
        self.assertEqual(refreshed["path"]["path_version"], 1)
        self.assertEqual(refreshed["snapshot"]["status"], "GENERATED")

    def test_hint_request_cannot_skip_levels_or_unlock_retest(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        result = asyncio.run(workflow.request_hint(created["session"]["id"], "student-1", requested_level=5, assessment_mode=True))
        self.assertEqual(result["approved_level"], 1)
        self.assertFalse(result["reference_answer_allowed"])

    def test_refresh_keeps_session_and_creates_next_snapshot_version(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        created = asyncio.run(workflow.create_session("student-1", {"course": "鏁版嵁缁撴瀯"}))
        refreshed = asyncio.run(workflow.refresh_session(created["session"]["id"], "student-1", {"trigger_type": "MANUAL_REFRESH"}))
        self.assertEqual(refreshed["session"]["id"], created["session"]["id"])
        self.assertEqual(refreshed["snapshot"]["session_id"], created["session"]["id"])
        self.assertEqual(refreshed["snapshot"]["version"], 2)

    def test_hint_request_persists_current_level(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        created = asyncio.run(workflow.create_session("student-1", {"course": "鏁版嵁缁撴瀯"}))
        session_id = created["session"]["id"]
        asyncio.run(workflow.request_hint(session_id, "student-1", requested_level=3, assessment_mode=False))
        stored = workflow.store.get_session(session_id, "student-1")
        self.assertEqual(stored["current_hint_level"], 1)

    def test_submit_task_records_sandbox_evidence(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        created = asyncio.run(workflow.create_session("student-1", {"course": "鏁版嵁缁撴瀯"}))
        task_id = created["path"]["tasks"][2]["task_id"]
        result = asyncio.run(workflow.submit_task(
            session_id=created["session"]["id"],
            student_id="student-1",
            task_id=task_id,
            code="print('ok')",
            hint_level=0,
            assessment_mode=False,
        ))
        self.assertEqual(result["status"], "RECORDED")
        self.assertTrue(result["execution_id"])
        self.assertTrue(any(item["source_type"] == "SANDBOX" for item in workflow.store.list_evidence("student-1")))

    def test_path_uses_matched_existing_homework_programming_content(self):
        JsonStore(self.db).upsert("homework", "homework", "hw-tree-1", {
            "id": "hw-tree-1",
            "title": "树遍历作业",
            "questions": [{
                "id": "q-preorder",
                "type": "programming",
                "title": "实现二叉树前序遍历",
                "desc": "返回节点访问顺序",
                "starterCode": "def preorder(root):\\n    pass\\n",
                "functionName": "preorder",
                "publicCases": [{"input": [[1, 2, 3]], "expected": [1, 2, 3]}],
                "knowledgeTags": ["tree_traversal"],
            }],
        })
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        result = asyncio.run(workflow.create_session("student-1", {"course": "数据结构"}))
        coding = next(task for task in result["path"]["tasks"] if task["task_type"] == "CODING_PRACTICE" and "tree_traversal" in task["knowledge_point_ids"])
        self.assertEqual(coding["source_type"], "EXISTING_HOMEWORK")
        self.assertEqual(coding["source_ref"], "hw-tree-1:q-preorder")
        self.assertEqual(coding["content_payload"]["starter_code"], "def preorder(root):\\n    pass\\n")
        self.assertEqual(coding["content_payload"]["test_cases"][0]["expected"], [1, 2, 3])

    def test_create_and_replace_goal_persist_versions_and_dynamic_points(self):
        workflow = DiagnosisWorkflow(self.db, retriever_mode="mock", goal_orchestrator=StaticGoalOrchestrator())
        created = asyncio.run(workflow.create_session("student-1", {"course": "数据结构", "goal_text": "掌握树"}))
        session_id = created["session"]["id"]
        first_goal_id = created["session"]["current_goal_version"]
        self.assertEqual([item["knowledge_point_id"] for item in created["snapshot"]["assessments"]], ["tree_traversal", "tree_recursion"])

        changed = asyncio.run(workflow.change_goal(session_id, "student-1", {"raw_goal_text": "掌握递归树算法", "course_name": "数据结构"}))
        second_goal_id = changed["session"]["current_goal_version"]
        self.assertNotEqual(first_goal_id, second_goal_id)
        self.assertEqual(len(workflow.store.list_goal_versions("student-1", session_id)), 2)
        self.assertEqual([item["id"] for item in changed["session"]["current_knowledge_points"]], ["tree_traversal", "tree_recursion"])
        self.assertEqual(changed["snapshot"]["trigger_type"], "GOAL_CHANGED")


if __name__ == "__main__":
    unittest.main()
