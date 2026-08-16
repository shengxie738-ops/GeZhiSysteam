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

from app.api.endpoints.chat import OpenAIChatMessage, OpenAIChatRequest, build_openai_runtime_config


class OpenAIModelRoutingTest(unittest.TestCase):
    def test_openai_compatible_request_model_is_passed_to_agent_runtime(self):
        request = OpenAIChatRequest(
            model="qwen3.6-max-preview",
            messages=[OpenAIChatMessage(role="user", content="hi")],
        )

        config = build_openai_runtime_config(request, thread_id="thread-1", message="hi")

        self.assertEqual(config["configurable"]["thread_id"], "thread-1")
        self.assertEqual(config["configurable"]["agent_model"], "qwen3.6-max-preview")

    def test_openai_compatible_invalid_model_falls_back_to_tutor_default(self):
        request = OpenAIChatRequest(
            model="not-a-real-model",
            messages=[OpenAIChatMessage(role="user", content="hi")],
        )

        config = build_openai_runtime_config(request, thread_id="thread-1", message="hi")

        self.assertEqual(config["configurable"]["agent_model"], "qwen3.7-plus")


if __name__ == "__main__":
    unittest.main()
