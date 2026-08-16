import unittest

from app.services.learning_diagnosis.task_resolver import TaskResolver


class LearningDiagnosisTaskResolverTest(unittest.TestCase):
    def test_existing_programming_question_has_priority_over_rag_and_keeps_payload(self):
        sources = [
            {
                "content_type": "HOMEWORK",
                "content_id": "hw-1-q-2",
                "source_module": "homework",
                "relevance_score": 0.92,
                "content_snapshot": {
                    "title": "实现二叉树前序遍历",
                    "description": "返回节点访问顺序",
                    "type": "programming",
                    "starterCode": "def preorder(root):\n    pass\n",
                    "functionName": "preorder",
                    "publicCases": [{"input": [[1, 2, 3]], "expected": [1, 2, 3]}],
                },
            },
            {"chunk_id": "rag-1", "title": "树遍历讲义", "content": "RAGFlow 内容", "source_type": "RAG_GENERATED"},
        ]
        resolved = TaskResolver().resolve("CODING_PRACTICE", "tree_traversal", sources)
        self.assertEqual(resolved["source_type"], "EXISTING_HOMEWORK")
        self.assertEqual(resolved["source_ref"], "hw-1-q-2")
        self.assertEqual(resolved["title"], "实现二叉树前序遍历")
        self.assertEqual(resolved["content_payload"]["starter_code"], "def preorder(root):\n    pass\n")
        self.assertEqual(resolved["content_payload"]["test_cases"][0]["expected"], [1, 2, 3])

    def test_rag_is_used_when_no_existing_content_can_execute(self):
        resolved = TaskResolver().resolve(
            "KNOWLEDGE_REVIEW",
            "tree_traversal",
            [{"chunk_id": "rag-1", "title": "树遍历讲义", "content": "先访问根节点。", "source_type": "RAG_GENERATED"}],
        )
        self.assertEqual(resolved["source_type"], "RAG_GENERATED")
        self.assertEqual(resolved["content_payload"]["content"], "先访问根节点。")


if __name__ == "__main__":
    unittest.main()
