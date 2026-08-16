import html
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.services.model_registry import AIModelConfig, build_chat_model, get_model_config


GUIDE_TYPES = {
    "concept": {
        "label": "概念图",
        "caption": "Mira 已生成概念引导图。",
        "nodes": ["先建立定义", "拆解组成部分", "看清信息流", "迁移到例子"],
        "edges": ["是什么", "由什么组成", "如何运转", "怎么应用"],
        "instruction": "生成一张适合学生理解概念关系的概念图，突出定义、组成、运行机制和应用例子。",
        "accent": "#b91c1c",
    },
    "steps": {
        "label": "步骤图",
        "caption": "Mira 已生成步骤引导图。",
        "nodes": ["明确问题", "定位前置知识", "推导关键机制", "做题巩固"],
        "edges": ["Step 1", "Step 2", "Step 3", "Step 4"],
        "instruction": "生成一张适合学生按步骤学习的流程图，突出问题、前置知识、推导和练习。",
        "accent": "#1d4ed8",
    },
}

DEFAULT_NEGATIVE_PROMPT = (
    "文字，字母，数字，汉字，标签，水印，UI界面，按钮，边框，"
    "低清晰度，结构混乱，过度装饰，广告风，人物特写，危险内容"
)


@dataclass
class VisualGuideGenerationRequest:
    prompt: str
    guide_type: str = "concept"
    session_id: str | None = None
    style: str | None = None
    context: dict[str, Any] | None = None
    model: str | None = None
    text_model: str | None = None
    agent_id: str | None = None
    agent_prompt: str | None = None


@dataclass
class ImageGenerationResult:
    image_url: str | None = None
    image_base64: str | None = None
    request_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class QwenImageClientConfig:
    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com"
    endpoint: str = "/api/v1/services/aigc/multimodal-generation/generation"
    timeout_seconds: int = 30
    prompt_extend: bool = False
    watermark: bool = False


class QwenImageClient:
    def __init__(self, config: QwenImageClientConfig):
        self.config = config

    def generate_image(self, *, prompt: str, model: str, size: str, negative_prompt: str) -> ImageGenerationResult:
        if not self.config.api_key:
            raise ValueError("QWEN_IMAGE_API_KEY is not configured")

        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": {
                "negative_prompt": negative_prompt,
                "size": size,
                "n": 1,
                "prompt_extend": self.config.prompt_extend,
                "watermark": self.config.watermark,
            },
        }
        request = urllib.request.Request(
            self._url(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Qwen image API HTTP {error.code}: {body}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Qwen image API request failed: {error.reason}") from error

        return _parse_qwen_image_response(response_payload)

    def _url(self) -> str:
        return self.config.base_url.rstrip("/") + "/" + self.config.endpoint.lstrip("/")


class VisualGuideService:
    def __init__(
        self,
        *,
        image_client: QwenImageClient | None = None,
        image_enabled: bool | None = None,
        model: str | None = None,
        size: str | None = None,
        text_model_factory=build_chat_model,
    ):
        self.image_enabled = settings.QWEN_IMAGE_ENABLED if image_enabled is None else image_enabled
        self.model = model or settings.QWEN_IMAGE_MODEL
        self.size = size or settings.QWEN_IMAGE_SIZE
        self.image_client = image_client
        self.text_model_factory = text_model_factory

    def generate(self, request: VisualGuideGenerationRequest) -> dict[str, Any]:
        clean_prompt = _clean_prompt(request.prompt)
        guide_type = _normalize_guide_type(request.guide_type)
        if guide_type == "steps":
            return self._generate_text_architecture(clean_prompt, request)

        guide_spec = GUIDE_TYPES[guide_type]
        keyword = extract_keyword(clean_prompt)
        model_config = self._resolve_model_config(request.model)
        background_prompt = build_background_prompt(clean_prompt, guide_type, request.context)

        metadata = {
            "guide_type": guide_type,
            "session_id": request.session_id,
            "render_mode": "structured_svg",
            "qwen_enabled": self.image_enabled,
            "model": model_config.model_id,
            "size": self.size,
            "background_prompt": background_prompt,
        }

        svg_payload = _build_svg_payload(
            prompt=clean_prompt,
            keyword=keyword,
            guide_type=guide_type,
            metadata=metadata,
        )

        if not self.image_enabled:
            return svg_payload

        try:
            image_client = self.image_client or _build_qwen_client_from_model_config(model_config)
            image_result = image_client.generate_image(
                prompt=background_prompt,
                model=model_config.model_id,
                size=self.size,
                negative_prompt=DEFAULT_NEGATIVE_PROMPT,
            )
            return {
                **svg_payload,
                "provider": "structured_svg+qwen",
                "background_url": image_result.image_url or "",
                "background_base64": image_result.image_base64 or "",
                "metadata": {
                    **metadata,
                    "background_provider": "qwen",
                    "request_id": image_result.request_id,
                },
            }
        except Exception as error:
            svg_payload["metadata"] = {
                **metadata,
                "background_error": str(error),
            }
            return svg_payload

    def _resolve_model_config(self, requested_model: str | None = None) -> AIModelConfig:
        for model_id in (requested_model, self.model, settings.QWEN_IMAGE_MODEL, "qwen-image-2.0-pro"):
            try:
                return get_model_config(model_id, category="image")
            except ValueError:
                continue
        raise ValueError("No supported image model configured")

    def _generate_text_architecture(self, prompt: str, request: VisualGuideGenerationRequest) -> dict[str, Any]:
        model_id = _resolve_text_model_id(request)
        metadata = {
            "guide_type": "steps",
            "session_id": request.session_id,
            "render_mode": "text_architecture",
            "agent_id": request.agent_id or (request.context or {}).get("agent_id") or "agent_tutor",
            "agent": (request.context or {}).get("agent") or "Prof. X",
            "text_model": model_id,
            "qwen_image_skipped": True,
        }
        architecture_prompt = build_architecture_prompt(prompt, request)

        try:
            text_model = self.text_model_factory(model_id, temperature=0.1)
            response = text_model.invoke(architecture_prompt)
            architecture = _parse_architecture_response(_message_content(response), prompt)
        except Exception as error:
            architecture = _fallback_architecture_payload(prompt)
            metadata["text_model_error"] = str(error)

        return {
            "status": "success",
            "provider": "prof_x_text_architecture",
            "diagram_type": architecture["diagram_type"],
            "title": architecture["title"],
            "caption": architecture["caption"],
            "mermaid": architecture["mermaid"],
            "tree_text": architecture["tree_text"],
            "background_url": "",
            "background_base64": "",
            "image_alt": f"{extract_keyword(prompt)} Prof. X 知识结构图",
            "nodes": architecture["nodes"],
            "edges": architecture["edges"],
            "metadata": metadata,
        }


def build_background_prompt(prompt: str, guide_type: str, context: dict[str, Any] | None = None) -> str:
    guide_spec = GUIDE_TYPES[_normalize_guide_type(guide_type)]
    keyword = extract_keyword(prompt)
    context_lines = []
    if context:
        for key in ("course", "chapter", "mode", "agent"):
            value = context.get(key)
            if value:
                context_lines.append(f"{key}: {value}")
    context_block = "\n".join(context_lines) if context_lines else "mode: guided_learning\nagent: Mira"

    return (
        "生成一张教育场景用的纯背景插画，供前端叠加 SVG 引导图使用。\n"
        f"学习主题：{keyword}\n"
        f"学生问题：{prompt}\n"
        f"图类型氛围：{guide_spec['label']}\n"
        f"学习上下文：\n{context_block}\n"
        "画面要求：16:9 或 4:3，浅色纸张/水墨质感，抽象几何或柔和色块，主体居中留白。\n"
        "严格禁止：任何文字、字母、数字、汉字、标签、水印、UI 界面、按钮、边框、信息图节点。\n"
        "风格要求：简洁、柔和、适合作为学习引导图背景，不要抢视觉焦点。"
    )


def build_architecture_prompt(prompt: str, request: VisualGuideGenerationRequest) -> str:
    context = request.context or {}
    agent_prompt = (request.agent_prompt or context.get("agent_prompt") or "").strip()
    agent_name = context.get("agent") or "Prof. X"
    keyword = extract_keyword(prompt)
    guide_instruction = GUIDE_TYPES["steps"]["instruction"]
    return (
        f"你是{agent_name}，现在为学生端 Mira 的“步骤图”生成知识结构图。\n"
        "这次不要生成图片，不要调用生图模型；只用文本模型产出可渲染的知识结构图数据。\n"
        f"学生问题：{prompt}\n"
        f"主题关键词：{keyword}\n"
        f"教学指导：{agent_prompt or '请用费曼技巧解释复杂概念，并给出清晰的知识结构。'}\n"
        f"步骤图要求：{guide_instruction}\n"
        "请根据学生问题，分析其中涉及的核心知识点，生成一张知识结构图。\n"
        "要求：\n"
        "1. 从问题中提取具体的知识点（不是泛泛的学习步骤），用 subgraph 分组展示不同知识模块。\n"
        "2. 每个知识点作为独立节点，节点之间用 --> 或 -.-> 表示学习顺序或依赖关系。\n"
        "3. 如果问题涉及多个概念的比较（如“栈与队列的区别”），分别用 subgraph 展示每个概念的知识点。\n"
        "4. 节点内容应该是具体的知识点名称，如“LIFO后进先出”“FIFO先进先出”“入栈操作”等，而非“Step 1”。\n"
        "5. edges 应描述知识点之间的关系，如“对比”“前置”“包含”“区别于”等。\n"
        "示例（问题“栈与队列的区别”）：\n"
        "flowchart TD\n"
        "  subgraph 栈\n"
        "    S1[LIFO后进先出] --> S2[入栈push]\n"
        "    S2 --> S3[出栈pop]\n"
        "    S3 --> S4[栈顶元素]\n"
        "  end\n"
        "  subgraph 队列\n"
        "    Q1[FIFO先进先出] --> Q2[入队enqueue]\n"
        "    Q2 --> Q3[出队dequeue]\n"
        "    Q3 --> Q4[队头队尾]\n"
        "  end\n"
        "  S1 -.->|区别于| Q1\n"
        "只返回 JSON，不要 Markdown 解释，不要代码围栏。JSON 字段必须为：\n"
        "{\n"
        '  "diagram_type": "mermaid",\n'
        '  "title": "知识结构图：主题",\n'
        '  "caption": "一句中文说明",\n'
        '  "mermaid": "flowchart TD\\n  subgraph 模块A\\n    A1[知识点1] --> A2[知识点2]\\n  end",\n'
        '  "tree_text": "",\n'
        '  "nodes": ["知识点1", "知识点2", "知识点3", "知识点4"],\n'
        '  "edges": ["包含", "前置", "对比", "区别于"]\n'
        "}\n"
        "Mermaid 只使用 flowchart TD、subgraph、-->、-.->、节点方括号，节点文案用简短中文。"
    )


def _resolve_text_model_id(request: VisualGuideGenerationRequest) -> str:
    context = request.context or {}
    for candidate in (
        request.text_model,
        context.get("text_model"),
        context.get("agent_model"),
        "qwen3.7-plus",
    ):
        if not candidate:
            continue
        try:
            return get_model_config(str(candidate), category="text").model_id
        except ValueError:
            continue
    return "qwen3.7-plus"


def _message_content(response: Any) -> str:
    if response is None:
        return ""
    content = getattr(response, "content", response)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _parse_architecture_response(content: str, prompt: str) -> dict[str, Any]:
    parsed = _extract_json_object(content)
    fallback = _fallback_architecture_payload(prompt)
    if not parsed:
        return fallback

    mermaid = _clean_mermaid(parsed.get("mermaid") or "")
    tree_text = _clean_tree_text(parsed.get("tree_text") or parsed.get("treeText") or "")
    diagram_type = str(parsed.get("diagram_type") or parsed.get("diagramType") or "").strip()
    if diagram_type not in {"mermaid", "tree"}:
        diagram_type = "tree" if tree_text and not mermaid else "mermaid"
    if not mermaid and not tree_text:
        return fallback

    nodes = _clean_string_list(parsed.get("nodes"), fallback["nodes"])
    edges = _clean_string_list(parsed.get("edges"), fallback["edges"])
    return {
        "diagram_type": diagram_type,
        "title": str(parsed.get("title") or fallback["title"])[:48],
        "caption": str(parsed.get("caption") or "Prof. X 已生成代码架构图。")[:96],
        "mermaid": mermaid,
        "tree_text": tree_text,
        "nodes": nodes,
        "edges": edges,
    }


def _extract_json_object(content: str) -> dict[str, Any] | None:
    raw = (content or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()
    candidates = [raw]
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def _clean_mermaid(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^```(?:mermaid)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    if not text:
        return ""
    if not re.match(r"^(flowchart|graph)\s+(TD|LR|TB|RL)", text):
        return ""
    return text[:4000]


def _clean_tree_text(value: str) -> str:
    return str(value or "").strip()[:3000]


def _clean_string_list(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    cleaned = [str(item).strip()[:24] for item in value if str(item).strip()]
    return cleaned[:6] or fallback


def _fallback_architecture_payload(prompt: str) -> dict[str, Any]:
    keyword = extract_keyword(prompt)
    mermaid = (
        "flowchart TD\n"
        f"  A[核心概念：{keyword}] --> B[基本定义]\n"
        f"  A --> C[关键特性]\n"
        f"  A --> D[应用场景]\n"
        f"  B --> E[重要知识点]"
    )
    return {
        "diagram_type": "mermaid",
        "title": f"知识结构图：{keyword}",
        "caption": "Prof. X 已生成知识结构图。",
        "mermaid": mermaid,
        "tree_text": "",
        "nodes": ["核心概念", "基本定义", "关键特性", "应用场景", "重要知识点"],
        "edges": ["定义", "特性", "应用", "展开"],
    }


def extract_keyword(prompt: str) -> str:
    cleaned = re.sub(r"[，。？！、,.!?：:；;（）()\[\]【】\"'“”]", " ", prompt)
    cleaned = re.sub(
        r"(解释一下|什么是|帮我|请|如何|怎么|用步骤图说明|用类比解释|说明|学习|生成|画|图)",
        " ",
        cleaned,
    )
    parts = [part.strip() for part in cleaned.split() if part.strip()]
    if not parts:
        return "核心概念"
    for part in parts:
        if re.search(r"[A-Za-z0-9]", part):
            return part[:18]
    return parts[0][:12]


def _parse_qwen_image_response(payload: dict[str, Any]) -> ImageGenerationResult:
    output = payload.get("output") or {}
    candidates: list[Any] = []
    candidates.extend(output.get("results") or [])
    for choice in output.get("choices") or []:
        message = choice.get("message") or {}
        candidates.extend(message.get("content") or [])
    candidates.extend(payload.get("results") or [])

    for item in candidates:
        if not isinstance(item, dict):
            continue
        image_url = item.get("image") or item.get("url") or item.get("image_url")
        image_base64 = item.get("image_base64") or item.get("b64_json")
        if image_url or image_base64:
            return ImageGenerationResult(
                image_url=image_url,
                image_base64=image_base64,
                request_id=payload.get("request_id"),
                raw=payload,
            )

    raise RuntimeError("Qwen image API response did not include an image URL or base64 payload")


def _build_svg_payload(*, prompt: str, keyword: str, guide_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
    guide_spec = GUIDE_TYPES[guide_type]
    return {
        "status": "success",
        "provider": "structured_svg",
        "svg": _build_svg(
            title=f"{guide_spec['label']}：{keyword}",
            center=keyword,
            caption=f"围绕「{prompt}」生成学习支架。",
            nodes=guide_spec["nodes"],
            edges=guide_spec["edges"],
            accent=guide_spec["accent"],
        ),
        "background_url": "",
        "background_base64": "",
        "caption": guide_spec["caption"],
        "image_alt": f"{keyword} {guide_spec['label']}学习引导图",
        "nodes": guide_spec["nodes"],
        "edges": guide_spec["edges"],
        "metadata": metadata,
    }


def _build_svg(*, title: str, center: str, caption: str, nodes: list[str], edges: list[str], accent: str) -> str:
    safe_title = html.escape(title[:48])
    safe_center = html.escape(center[:24])
    safe_caption = html.escape(caption[:68])
    positions = [(90, 120), (330, 80), (500, 215), (255, 295)]
    node_markup = []
    for index, node in enumerate(nodes[:4]):
        edge = edges[index] if index < len(edges) else ""
        x, y = positions[index]
        safe_node = html.escape(node[:24])
        safe_edge = html.escape(edge[:18])
        node_markup.append(
            f'<line x1="330" y1="190" x2="{x + 64}" y2="{y + 22}" stroke="{accent}" stroke-opacity=".24" stroke-width="2"/>'
        )
        node_markup.append(
            f'<rect x="{x}" y="{y}" width="128" height="48" rx="12" fill="#ffffff" stroke="{accent}" stroke-opacity=".28"/>'
        )
        node_markup.append(
            f'<text x="{x + 64}" y="{y + 23}" text-anchor="middle" fill="#1c2b38" font-size="12" font-weight="700">{safe_node}</text>'
        )
        node_markup.append(
            f'<text x="{x + 64}" y="{y + 39}" text-anchor="middle" fill="{accent}" font-size="10">{safe_edge}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="660" height="390" viewBox="0 0 660 390">
<rect width="660" height="390" rx="24" fill="#f8fbfc"/>
<circle cx="330" cy="190" r="72" fill="#fff" stroke="{accent}" stroke-opacity=".35" stroke-width="2"/>
<text x="330" y="184" text-anchor="middle" fill="{accent}" font-size="18" font-weight="800">{safe_center}</text>
<text x="330" y="207" text-anchor="middle" fill="#64748b" font-size="11">Mira visual guide</text>
{''.join(node_markup)}
<text x="34" y="44" fill="#1c2b38" font-size="20" font-weight="800">{safe_title}</text>
<text x="34" y="68" fill="#64748b" font-size="12">{safe_caption}</text>
</svg>'''


def _build_default_qwen_client() -> QwenImageClient:
    api_key = settings.QWEN_IMAGE_API_KEY or os.getenv("DASHSCOPE_API_KEY", "")
    return QwenImageClient(
        QwenImageClientConfig(
            api_key=api_key,
            base_url=settings.QWEN_IMAGE_BASE_URL,
            endpoint=settings.QWEN_IMAGE_ENDPOINT,
            timeout_seconds=settings.QWEN_IMAGE_TIMEOUT_SECONDS,
            prompt_extend=settings.QWEN_IMAGE_PROMPT_EXTEND,
            watermark=settings.QWEN_IMAGE_WATERMARK,
        )
    )


def _build_qwen_client_from_model_config(model_config: AIModelConfig) -> QwenImageClient:
    return QwenImageClient(
        QwenImageClientConfig(
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            endpoint=model_config.endpoint or settings.QWEN_IMAGE_ENDPOINT,
            timeout_seconds=settings.QWEN_IMAGE_TIMEOUT_SECONDS,
            prompt_extend=settings.QWEN_IMAGE_PROMPT_EXTEND,
            watermark=settings.QWEN_IMAGE_WATERMARK,
        )
    )


def _clean_prompt(prompt: str) -> str:
    clean_prompt = (prompt or "").strip()
    return clean_prompt or "请生成一个学习引导图"


def _normalize_guide_type(guide_type: str) -> str:
    return guide_type if guide_type in GUIDE_TYPES else "concept"
