import asyncio
import os
import unittest
from datetime import datetime, timezone

os.environ.pop("KNOWLEDGE_RETRIEVER_MODE", None)

from app.services.learning_diagnosis.goal_orchestrator import GoalOrchestrator
from app.services.learning_diagnosis.knowledge_retriever import (
    KnowledgeRetrievalRequest,
    RagFlowKnowledgeRetriever,
    UnavailableKnowledgeRetriever,
    select_knowledge_retriever,
)


class FakePlannerModel:
    async def ainvoke(self, prompt):
        return {
            "knowledge_points": [
                {"id": "tree_traversal", "name": "树的遍历", "description": "掌握前序、中序和后序遍历", "success_criteria": ["能区分三种遍历"], "search_query": "树的遍历"},
                {"id": "tree_recursion", "name": "递归实现", "description": "使用递归实现树遍历", "success_criteria": ["能写出递归遍历"], "search_query": "树遍历递归"},
            ]
        }


class LearningDiagnosisGoalTest(unittest.TestCase):
    def test_explicit_knowledge_points_are_preserved_for_demo_goal(self):
        points = [
            {"id": "linked_list_boundary", "name": "链表边界", "description": "处理空链表和单节点", "success_criteria": ["能处理边界"], "search_query": "链表边界"},
            {"id": "linked_list_delete", "name": "链表删除", "description": "删除节点", "success_criteria": ["能完成删除"], "search_query": "链表删除"},
        ]
        result = asyncio.run(GoalOrchestrator(model_client=None).parse_goal({"course": "数据结构", "goal_text": "链表", "knowledge_points": points}))
        self.assertEqual([item["id"] for item in result["knowledge_points"]], ["linked_list_boundary", "linked_list_delete"])

    def test_goal_orchestrator_uses_injected_planner_and_returns_dynamic_points(self):
        result = asyncio.run(GoalOrchestrator(model_client=FakePlannerModel()).parse_goal({
            "raw_goal_text": "两周内掌握二叉树遍历",
            "course_name": "数据结构",
            "weekly_minutes": 120,
            "deadline": "2026-08-24",
        }))
        self.assertEqual(result["provider"], "agent_planner")
        self.assertEqual(result["status"], "AI_GENERATED")
        self.assertEqual([item["id"] for item in result["knowledge_points"]], ["tree_traversal", "tree_recursion"])
        self.assertTrue(all(item["search_query"] for item in result["knowledge_points"]))

    def test_goal_orchestrator_deterministic_fallback_is_transparent_when_model_fails(self):
        class BrokenModel:
            async def ainvoke(self, prompt):
                raise RuntimeError("provider unavailable")

        result = asyncio.run(GoalOrchestrator(model_client=BrokenModel()).parse_goal({
            "goal_text": "掌握数据结构",
            "course": "数据结构",
        }))
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["provider"], "deterministic")
        self.assertIn("provider unavailable", result["error"])
        self.assertGreaterEqual(len(result["knowledge_points"]), 2)

    def test_auto_retriever_uses_settings_and_degrades_only_when_configuration_is_missing(self):
        old = {key: os.environ.get(key) for key in ("RAGFLOW_BASE_URL", "RAGFLOW_API_KEY", "RAGFLOW_DATASET_ID")}
        try:
            for key in old:
                os.environ.pop(key, None)
            retriever = select_knowledge_retriever()
            if all(getattr(__import__("app.core.config", fromlist=["settings"]).settings, key, "") for key in ("RAGFLOW_BASE_URL", "RAGFLOW_API_KEY", "RAGFLOW_DATASET_ID")):
                self.assertIsInstance(retriever, RagFlowKnowledgeRetriever)
            else:
                self.assertIsInstance(retriever, UnavailableKnowledgeRetriever)
                result = asyncio.run(retriever.retrieve(KnowledgeRetrievalRequest(knowledge_point_id="tree_traversal")))
                self.assertEqual(result.status, "UNAVAILABLE")
                self.assertEqual(result.provider, "unavailable")
        finally:
            for key, value in old.items():
                if value is not None:
                    os.environ[key] = value

    def test_explicit_mock_mode_remains_available_for_tests(self):
        retriever = select_knowledge_retriever("mock")
        result = asyncio.run(retriever.retrieve(KnowledgeRetrievalRequest(knowledge_point_id="linked_list_boundary")))
        self.assertEqual(result.provider, "mock")
        self.assertEqual(result.status, "OK")


if __name__ == "__main__":
    unittest.main()
