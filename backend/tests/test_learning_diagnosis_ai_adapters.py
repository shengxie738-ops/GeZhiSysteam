import asyncio
import time
import unittest
from unittest.mock import patch

from app.services.learning_diagnosis.knowledge_retriever import KnowledgeRetrievalRequest, RagFlowKnowledgeRetriever, select_knowledge_retriever
from app.services.learning_diagnosis.llm_explainer import LlmExplainer
from app.services.learning_diagnosis.output_guard import AnswerLeakageGuard


class LearningDiagnosisAiAdaptersTest(unittest.TestCase):
    def test_llm_explainer_timeout_degrades_without_blocking(self):
        class _HangingModel:
            async def ainvoke(self, prompt):
                await asyncio.sleep(0.2)
                return type("Response", (), {"content": "{}"})()

        started = time.perf_counter()
        result = asyncio.run(LlmExplainer(model_client=_HangingModel(), timeout_seconds=0.01).explain({"knowledge_point_ids": ["tree"]}, [], []))
        elapsed = time.perf_counter() - started
        self.assertEqual(result.status, "DEGRADED")
        self.assertIn("Timeout", result.degraded_reason or "")
        self.assertLess(elapsed, 0.15)

    def test_llm_explainer_default_path_invokes_registered_model(self):
        class _Model:
            def __init__(self):
                self.calls = []

            async def ainvoke(self, prompt):
                self.calls.append(prompt)
                return type("Response", (), {"content": '{"summary":"来自默认模型","strengths":[],"weaknesses":[],"recommended_actions":[],"uncertainty_notes":[]}'})()

        model = _Model()
        with patch("app.services.learning_diagnosis.llm_explainer.get_cached_chat_model", return_value=model):
            result = asyncio.run(LlmExplainer().explain({"knowledge_point_ids": ["tree"]}, [], []))
        self.assertEqual(result.status, "AI_GENERATED")
        self.assertEqual(result.provider, "llm")
        self.assertEqual(len(model.calls), 1)

    def test_mock_retriever_returns_cited_course_chunk(self):
        retriever = select_knowledge_retriever("mock")
        result = asyncio.run(retriever.retrieve(KnowledgeRetrievalRequest(knowledge_point_id="linked_list_boundary")))
        self.assertEqual(result.provider, "mock")
        self.assertTrue(result.chunks[0].chunk_id)

    def test_mock_retriever_empty_point_reports_empty(self):
        result = asyncio.run(select_knowledge_retriever("mock").retrieve(KnowledgeRetrievalRequest(knowledge_point_id="unknown")))
        self.assertEqual(result.status, "EMPTY")
        self.assertEqual(result.chunks, [])

    def test_ragflow_retriever_uses_existing_service_adapter(self):
        import app.services.learning_diagnosis.knowledge_retriever as module

        original = module.retrieve_from_datasets
        try:
            module.retrieve_from_datasets = lambda dataset_ids, query, top_k_per_dataset=4, **kwargs: [{
                "id": "chunk-1",
                "content": "链表边界",
                "document_name": "数据结构课程",
                "similarity": 0.91,
                "dataset_id": dataset_ids[0],
            }]
            retriever = RagFlowKnowledgeRetriever(base_url="https://ragflow.example/api/v1", api_key="key", dataset_ids=["ds-1"])
            result = asyncio.run(retriever.retrieve(KnowledgeRetrievalRequest(knowledge_point_id="linked_list_boundary", query="链表边界")))
            self.assertEqual(result.status, "OK")
            self.assertEqual(result.chunks[0].chunk_id, "chunk-1")
        finally:
            module.retrieve_from_datasets = original

    def test_llm_explainer_rejects_unknown_evidence_reference(self):
        explainer = LlmExplainer(model_client=None)
        with self.assertRaises(ValueError):
            explainer.validate_output(
                {"summary": "x", "weaknesses": [{"evidenceRefs": ["missing"]}]},
                valid_evidence_refs={"ev-1"},
                valid_rag_refs=set(),
            )

    def test_answer_guard_blocks_complete_answer_for_level_four(self):
        guard = AnswerLeakageGuard()
        result = guard.inspect("public class Main { public static void main(String[] args) { return; } }", hint_level=4)
        self.assertFalse(result.allowed)
        self.assertIn("COMPLETE_CODE", result.reason_codes)

    def test_answer_guard_allows_short_pseudocode_for_level_four(self):
        result = AnswerLeakageGuard().inspect("if head is null: return; then update predecessor", hint_level=4)
        self.assertTrue(result.allowed)


if __name__ == "__main__":
    unittest.main()
