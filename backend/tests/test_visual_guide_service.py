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

from app.services.visual_guide_service import (
    ImageGenerationResult,
    VisualGuideGenerationRequest,
    VisualGuideService,
    build_background_prompt,
)


class FakeQwenImageClient:
    def __init__(self, result=None, error=None):
        self.result = result or ImageGenerationResult(image_url="https://example.com/bg.png", request_id="req-1")
        self.error = error
        self.calls = []

    def generate_image(self, *, prompt, model, size, negative_prompt):
        self.calls.append(
            {
                "prompt": prompt,
                "model": model,
                "size": size,
                "negative_prompt": negative_prompt,
            }
        )
        if self.error:
            raise self.error
        return self.result


class FakeTextModel:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        return type("Message", (), {"content": self.content})()


class VisualGuideServiceTest(unittest.TestCase):
    def test_generates_structured_svg_when_qwen_is_disabled(self):
        service = VisualGuideService(image_enabled=False)

        result = service.generate(
            VisualGuideGenerationRequest(
                prompt="解释一下什么是 Transformer 架构",
                guide_type="concept",
                session_id="alice",
                style="gezhi-ink-glass",
                context={"mode": "guided_learning", "agent": "Mira"},
            )
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider"], "structured_svg")
        self.assertIn("<svg", result["svg"])
        self.assertIn("Transformer", result["svg"])
        self.assertIn("先建立定义", result["svg"])
        self.assertEqual(result["caption"], "Mira 已生成概念引导图。")
        self.assertEqual(result["nodes"], ["先建立定义", "拆解组成部分", "看清信息流", "迁移到例子"])
        self.assertEqual(result["metadata"]["render_mode"], "structured_svg")
        self.assertEqual(result["metadata"]["qwen_enabled"], False)
        self.assertEqual(result["background_url"], "")

    def test_concept_calls_qwen_for_background_only_when_enabled(self):
        client = FakeQwenImageClient()
        service = VisualGuideService(
            image_client=client,
            image_enabled=True,
            model="qwen-image-2.0-pro",
            size="1472*1104",
        )

        result = service.generate(
            VisualGuideGenerationRequest(
                prompt="用概念图说明 Dijkstra 算法如何工作",
                guide_type="concept",
                session_id="alice",
                context={"course": "数据结构"},
            )
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider"], "structured_svg+qwen")
        self.assertIn("<svg", result["svg"])
        self.assertIn("Dijkstra", result["svg"])
        self.assertIn("先建立定义", result["svg"])
        self.assertEqual(result["background_url"], "https://example.com/bg.png")
        self.assertEqual(result["nodes"], ["先建立定义", "拆解组成部分", "看清信息流", "迁移到例子"])
        self.assertEqual(client.calls[0]["model"], "qwen-image-2.0-pro")
        self.assertEqual(client.calls[0]["size"], "1472*1104")
        self.assertIn("纯背景插画", client.calls[0]["prompt"])
        self.assertIn("严格禁止", client.calls[0]["prompt"])
        self.assertIn("任何文字", client.calls[0]["prompt"])
        self.assertIn("Dijkstra", client.calls[0]["prompt"])
        self.assertNotIn("节点文字使用简洁中文", client.calls[0]["prompt"])

    def test_request_level_image_model_overrides_service_default(self):
        client = FakeQwenImageClient()
        service = VisualGuideService(
            image_client=client,
            image_enabled=True,
            model="qwen-image-2.0-pro",
            size="1472*1104",
        )

        service.generate(
            VisualGuideGenerationRequest(
                prompt="解释一下 B+ 树索引",
                guide_type="concept",
                model="qwen-image-max",
            )
        )

        self.assertEqual(client.calls[0]["model"], "qwen-image-max")

    def test_keeps_svg_when_qwen_background_fails(self):
        client = FakeQwenImageClient(error=RuntimeError("upstream timeout"))
        service = VisualGuideService(image_client=client, image_enabled=True)

        result = service.generate(
            VisualGuideGenerationRequest(prompt="概念解释数据库索引", guide_type="concept")
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider"], "structured_svg")
        self.assertIn("数据库索引", result["svg"])
        self.assertIn("先建立定义", result["svg"])
        self.assertEqual(result["metadata"]["background_error"], "upstream timeout")

    def test_background_prompt_forbids_text(self):
        prompt = build_background_prompt("请告诉我数据结构当中的栈和队列", "concept")
        self.assertIn("严格禁止", prompt)
        self.assertIn("任何文字", prompt)
        self.assertIn("栈和队列", prompt)

    def test_steps_uses_prof_x_text_model_without_qwen_image(self):
        image_client = FakeQwenImageClient()
        text_model = FakeTextModel(
            """
            {
              "diagram_type": "mermaid",
              "title": "代码架构图：Transformer",
              "caption": "Prof. X 已生成代码架构图。",
              "mermaid": "flowchart TD\\n  A[输入序列] --> B[Embedding]\\n  B --> C[Self-Attention]\\n  C --> D[Feed Forward]",
              "nodes": ["输入序列", "Embedding", "Self-Attention", "Feed Forward"],
              "edges": ["输入", "编码", "注意力", "输出"]
            }
            """
        )
        created_models = []

        def text_model_factory(model_id, *, temperature=0.1):
            created_models.append((model_id, temperature))
            return text_model

        service = VisualGuideService(
            image_client=image_client,
            image_enabled=True,
            text_model_factory=text_model_factory,
        )

        result = service.generate(
            VisualGuideGenerationRequest(
                prompt="解释一下什么是 Transformer 架构",
                guide_type="steps",
                model="qwen-image-2.0-pro",
                text_model="qwen3.7-plus",
                context={"agent": "Prof. X", "agent_id": "agent_tutor"},
            )
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider"], "prof_x_text_architecture")
        self.assertEqual(result["diagram_type"], "mermaid")
        self.assertIn("flowchart TD", result["mermaid"])
        self.assertEqual(result["metadata"]["render_mode"], "text_architecture")
        self.assertEqual(result["metadata"]["agent_id"], "agent_tutor")
        self.assertEqual(result["metadata"]["text_model"], "qwen3.7-plus")
        self.assertEqual(created_models, [("qwen3.7-plus", 0.1)])
        self.assertEqual(image_client.calls, [])
        self.assertIn("Prof. X", text_model.calls[0])
        self.assertIn("只返回 JSON", text_model.calls[0])


if __name__ == "__main__":
    unittest.main()
