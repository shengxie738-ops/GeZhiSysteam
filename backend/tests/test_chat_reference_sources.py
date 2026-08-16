import os
import unittest

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.api.endpoints.chat import (
    build_reference_source_block,
    build_verified_reference_reply,
    should_emit_reference_sources,
    strip_reference_source_block,
)


class ChatReferenceSourcesTest(unittest.TestCase):
    def test_only_rag_mode_emits_reference_sources(self):
        ref_docs = {"3-栈.pdf", "2-线性表.pdf"}

        self.assertTrue(should_emit_reference_sources("rag"))
        self.assertFalse(should_emit_reference_sources("tutor"))

        rag_block = build_reference_source_block(ref_docs, "rag")
        self.assertIn("【知识库引用来源】", rag_block)
        self.assertIn("- 2-线性表.pdf", rag_block)
        self.assertIn("- 3-栈.pdf", rag_block)

        self.assertEqual(build_reference_source_block(ref_docs, "tutor"), "")

    def test_strip_reference_source_block_removes_saved_tutor_artifacts(self):
        content = (
            "今天我们聊队列。\n\n"
            "【知识库引用来源】:\n"
            "- 2-线性表.pdf\n"
            "- 3-栈.pdf\n"
            "- ch13 泛型机制—模板（最终版）.ppt"
        )

        self.assertEqual(strip_reference_source_block(content), "今天我们聊队列。")

    def test_strip_data_structure_tool_reference_heading(self):
        content = "正文\n\n【数据结构知识库引用来源】:\n- 4-队列.pdf"

        self.assertEqual(strip_reference_source_block(content), "正文")

    def test_verified_reply_drops_model_generated_fake_sources(self):
        model_answer = (
            "答案正文\n\n"
            "【知识库引用来源】:\n"
            "- fake-source.pdf\n"
            "- hallucinated.ppt"
        )

        reply = build_verified_reference_reply(model_answer, {"real-source.pdf"}, "rag")

        self.assertIn("答案正文", reply)
        self.assertIn("- real-source.pdf", reply)
        self.assertNotIn("fake-source.pdf", reply)
        self.assertNotIn("hallucinated.ppt", reply)


if __name__ == "__main__":
    unittest.main()
