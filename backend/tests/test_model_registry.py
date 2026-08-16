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
os.environ.setdefault("ZHIPU_API_KEY", "test")

from app.services.model_registry import build_chat_model, get_model_config, list_public_models


class FakeChatModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class ModelRegistryTest(unittest.TestCase):
    def test_resolves_text_model_from_backend_registry(self):
        config = get_model_config("qwen3.7-plus", category="text")

        self.assertEqual(config.model_id, "qwen3.7-plus")
        self.assertEqual(config.category, "text")
        self.assertIn("/compatible-mode/v1", config.base_url)
        self.assertTrue(config.api_key)

    def test_resolves_image_model_from_backend_registry(self):
        config = get_model_config("qwen-image-2.0-pro", category="image")

        self.assertEqual(config.model_id, "qwen-image-2.0-pro")
        self.assertEqual(config.category, "image")
        self.assertIn("/api/v1", config.base_url)

    def test_rejects_unknown_or_wrong_category_model(self):
        for model_id in ("not-a-real-model", "spark Ultra-32K", "spark Lite", "spark-x", "mimo-v2.5", "glm-4.7"):
            with self.subTest(model_id=model_id):
                with self.assertRaises(ValueError):
                    get_model_config(model_id, category="text")

        with self.assertRaises(ValueError):
            get_model_config("qwen-image-2.0-pro", category="text")

    def test_public_model_list_does_not_expose_api_keys(self):
        public_models = list_public_models()

        self.assertIn("text", public_models)
        self.assertIn("image", public_models)
        self.assertTrue(any(model["id"] == "kimi-k2.7-code" for model in public_models["text"]))
        self.assertFalse(any("api_key" in model for models in public_models.values() for model in models))

    def test_build_chat_model_uses_selected_model_credentials(self):
        client = build_chat_model("qwen3.7-plus", temperature=0.25, client_factory=FakeChatModel)

        self.assertEqual(client.kwargs["model"], "qwen3.7-plus")
        self.assertEqual(client.kwargs["temperature"], 0.25)
        self.assertEqual(client.kwargs["base_url"], "https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
        self.assertTrue(client.kwargs["openai_api_key"])

    def test_zhipu_glm_models_use_bigmodel_chat_endpoint(self):
        for model_id in ("glm-4.5-air", "glm-4.6v"):
            with self.subTest(model_id=model_id):
                config = get_model_config(model_id, category="text")
                client = build_chat_model(model_id, client_factory=FakeChatModel)

                self.assertEqual(config.provider, "智谱 AI")
                self.assertEqual(config.base_url, "https://open.bigmodel.cn/api/paas/v4")
                self.assertEqual(client.kwargs["model"], model_id)
                self.assertEqual(client.kwargs["base_url"], "https://open.bigmodel.cn/api/paas/v4")
                self.assertTrue(client.kwargs["openai_api_key"])

    def test_thinking_models_enable_reasoning_via_extra_body(self):
        for model_id in ("deepseek-v4-flash", "qwen3.8-max", "qwen3.7-flash", "kimi-k2.6", "glm-5.1"):
            with self.subTest(model_id=model_id):
                config = get_model_config(model_id, category="text")
                client = build_chat_model(model_id, client_factory=FakeChatModel)

                self.assertEqual(config.provider, "阿里云百炼")
                self.assertIn("/compatible-mode/v1", config.base_url)
                self.assertTrue(config.enable_thinking)
                self.assertEqual(client.kwargs["model"], model_id)
                self.assertEqual(client.kwargs["extra_body"], {"enable_thinking": True})

        legacy_client = build_chat_model("qwen3.7-plus", client_factory=FakeChatModel)
        self.assertNotIn("extra_body", legacy_client.kwargs)

        public_thinking_models = {
            model["id"]: model for model in list_public_models()["text"]
        }
        self.assertEqual(public_thinking_models["qwen3.8-max"]["enable_thinking"], True)
        self.assertNotIn("enable_thinking", public_thinking_models["qwen3.7-plus"])


if __name__ == "__main__":
    unittest.main()
