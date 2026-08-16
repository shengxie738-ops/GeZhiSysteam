import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Literal

from langchain_openai import ChatOpenAI


ModelCategory = Literal["text", "image"]


@dataclass(frozen=True)
class AIModelConfig:
    model_id: str
    label: str
    provider: str
    category: ModelCategory
    base_url: str
    api_key: str
    api_model: str = ""
    hint: str = ""
    endpoint: str = ""
    enable_thinking: bool = False

    def to_public_dict(self) -> dict:
        data = {
            "id": self.model_id,
            "label": self.label,
            "provider": self.provider,
            "category": self.category,
            "base_url": self.base_url,
        }
        if self.api_model:
            data["api_model"] = self.api_model
        if self.hint:
            data["hint"] = self.hint
        if self.endpoint:
            data["endpoint"] = self.endpoint
        if self.enable_thinking:
            data["enable_thinking"] = True
        return data


# 密钥一律从环境变量读取，严禁在代码中硬编码（开源仓库安全要求）。
# QWEN_TEXT_API_KEY 未配置时回退到 OPENAI_API_KEY；ZHIPU_API_KEY 未配置时回退到 AI_LESSON_PREP_API_KEY。
QWEN_API_KEY = os.getenv("QWEN_TEXT_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
QWEN_TEXT_BASE_URL = os.getenv(
    "QWEN_TEXT_BASE_URL",
    "https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
)
QWEN_IMAGE_BASE_URL = os.getenv(
    "QWEN_IMAGE_API_BASE_URL",
    "https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/api/v1",
)
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY") or os.getenv("AI_LESSON_PREP_API_KEY") or ""
ZHIPU_TEXT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
IMAGE_GENERATION_ENDPOINT = "/services/aigc/multimodal-generation/generation"


_MODEL_CONFIGS: dict[str, AIModelConfig] = {
    "qwen3.7-plus": AIModelConfig(
        model_id="qwen3.7-plus",
        label="qwen3.7-plus",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="综合讲解",
    ),
    "qwen3.7-max": AIModelConfig(
        model_id="qwen3.7-max",
        label="qwen3.7-max",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="复杂规划",
    ),
    "qwen3.8-max": AIModelConfig(
        model_id="qwen3.8-max",
        label="qwen3.8-max",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="旗舰推理",
        enable_thinking=True,
    ),
    "qwen3.7-flash": AIModelConfig(
        model_id="qwen3.7-flash",
        label="qwen3.7-flash",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="轻量快速",
        enable_thinking=True,
    ),
    "qwen3.6-plus": AIModelConfig(
        model_id="qwen3.6-plus",
        label="qwen3.6-plus",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="稳定检索",
    ),
    "qwen3.6-max-preview": AIModelConfig(
        model_id="qwen3.6-max-preview",
        label="qwen3.6-max-preview",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="高阶推理",
    ),
    "qwen3.5-plus": AIModelConfig(
        model_id="qwen3.5-plus",
        label="qwen3.5-plus",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="日常问答",
    ),
    "deepseek-v4-pro": AIModelConfig(
        model_id="deepseek-v4-pro",
        label="deepseek-v4-pro",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="深度分析",
    ),
    "deepseek-v4-flash": AIModelConfig(
        model_id="deepseek-v4-flash",
        label="deepseek-v4-flash",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="极速响应",
        enable_thinking=True,
    ),
    "glm-5.2": AIModelConfig(
        model_id="glm-5.2",
        label="glm-5.2",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="通用协作",
    ),
    "glm-5.1": AIModelConfig(
        model_id="glm-5.1",
        label="glm-5.1",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="逻辑推理",
        enable_thinking=True,
    ),
    "glm-4.5-air": AIModelConfig(
        model_id="glm-4.5-air",
        label="glm-4.5-air",
        provider="智谱 AI",
        category="text",
        base_url=ZHIPU_TEXT_BASE_URL,
        api_key=ZHIPU_API_KEY,
        hint="轻量响应",
    ),
    "glm-4.6v": AIModelConfig(
        model_id="glm-4.6v",
        label="glm-4.6v",
        provider="智谱 AI",
        category="text",
        base_url=ZHIPU_TEXT_BASE_URL,
        api_key=ZHIPU_API_KEY,
        hint="视觉理解",
    ),
    "kimi-k2.7-code": AIModelConfig(
        model_id="kimi-k2.7-code",
        label="kimi-k2.7-code",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="代码生成",
    ),
    "kimi-k2.6": AIModelConfig(
        model_id="kimi-k2.6",
        label="kimi-k2.6",
        provider="阿里云百炼",
        category="text",
        base_url=QWEN_TEXT_BASE_URL,
        api_key=QWEN_API_KEY,
        hint="长文理解",
        enable_thinking=True,
    ),
    "qwen-image-2.0": AIModelConfig(
        model_id="qwen-image-2.0",
        label="qwen-image-2.0",
        provider="阿里云百炼",
        category="image",
        base_url=QWEN_IMAGE_BASE_URL,
        endpoint=IMAGE_GENERATION_ENDPOINT,
        api_key=QWEN_API_KEY,
    ),
    "qwen-image-2.0-pro": AIModelConfig(
        model_id="qwen-image-2.0-pro",
        label="qwen-image-2.0-pro",
        provider="阿里云百炼",
        category="image",
        base_url=QWEN_IMAGE_BASE_URL,
        endpoint=IMAGE_GENERATION_ENDPOINT,
        api_key=QWEN_API_KEY,
    ),
    "qwen-image-max": AIModelConfig(
        model_id="qwen-image-max",
        label="qwen-image-max",
        provider="阿里云百炼",
        category="image",
        base_url=QWEN_IMAGE_BASE_URL,
        endpoint=IMAGE_GENERATION_ENDPOINT,
        api_key=QWEN_API_KEY,
    ),
    "z-image-turbo": AIModelConfig(
        model_id="z-image-turbo",
        label="z-image-turbo",
        provider="阿里云 DashScope",
        category="image",
        base_url="https://dashscope.aliyuncs.com/api/v1",
        endpoint=IMAGE_GENERATION_ENDPOINT,
        api_key=QWEN_API_KEY,
    ),
}


def _resolve_registry_key(model_id: str | None) -> str:
    requested = (model_id or "").strip()
    if requested in _MODEL_CONFIGS:
        return requested

    for registry_key, config in _MODEL_CONFIGS.items():
        if config.api_model and config.api_model == requested:
            return registry_key
    return requested


def get_model_config(model_id: str | None, *, category: ModelCategory = "text") -> AIModelConfig:
    config = _MODEL_CONFIGS.get(_resolve_registry_key(model_id))
    if not config or config.category != category:
        raise ValueError(f"Unsupported {category} model: {model_id}")
    return config


def has_model(model_id: str | None, *, category: ModelCategory = "text") -> bool:
    try:
        get_model_config(model_id, category=category)
        return True
    except ValueError:
        return False


def list_public_models() -> dict[str, list[dict]]:
    return {
        "text": [config.to_public_dict() for config in _MODEL_CONFIGS.values() if config.category == "text"],
        "image": [config.to_public_dict() for config in _MODEL_CONFIGS.values() if config.category == "image"],
    }


@lru_cache(maxsize=64)
def _build_cached_chat_model(model_id: str, temperature: float) -> ChatOpenAI:
    return build_chat_model(model_id, temperature=temperature)


def get_cached_chat_model(model_id: str, *, temperature: float = 0.1) -> ChatOpenAI:
    return _build_cached_chat_model(model_id, float(temperature))


def build_chat_model(
    model_id: str,
    *,
    temperature: float = 0.1,
    client_factory: Callable[..., object] = ChatOpenAI,
):
    config = get_model_config(model_id, category="text")
    provider_model = config.api_model or config.model_id
    thinking_kwargs = {"extra_body": {"enable_thinking": True}} if config.enable_thinking else {}
    return client_factory(
        model=provider_model,
        openai_api_key=config.api_key,
        openai_api_base=config.base_url,
        base_url=config.base_url,
        temperature=temperature,
        **thinking_kwargs,
    )
