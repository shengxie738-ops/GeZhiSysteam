import json
from typing import Any

from pydantic_settings import BaseSettings


DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://gezhisystem.com",
    "https://www.gezhisystem.com",
]


def parse_cors_origins(value: Any) -> list[str]:
    raw = value if value not in (None, "") else DEFAULT_CORS_ORIGINS
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raw = DEFAULT_CORS_ORIGINS
        elif text.startswith("["):
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                raw = text.split(",")
        else:
            raw = text.split(",")
    if not isinstance(raw, (list, tuple, set)):
        raw = [raw]

    origins: list[str] = []
    seen: set[str] = set()
    for item in raw:
        origin = str(item or "").strip().rstrip("/")
        if not origin or origin in seen:
            continue
        seen.add(origin)
        origins.append(origin)
    return origins

class Settings(BaseSettings):
    APP_SECRET_KEY: str = "change-me-before-production"
    ENVIRONMENT: str = "development"
    BACKEND_PORT: int = 8516
    BACKEND_CORS_ORIGINS: str = ""

    # RAGFlow
    RAGFLOW_API_KEY: str
    RAGFLOW_BASE_URL: str
    RAGFLOW_AGENT_ID: str
    RAGFLOW_CHAT_ID: str
    RAGFLOW_DATASET_ID: str
    RAGFLOW_PUBLIC_DATASET_IDS: str
    RAGFLOW_COURSE_DATASETS: str = ""
    
    # LLM
    OPENAI_API_KEY: str
    OPENAI_API_BASE: str
    LLM_MODEL: str = "qwen3.7-max"
    LLM_MODEL_MAX: str = "qwen3.7-max"
    LLM_MODEL_FLASH: str = "qwen3.7-flash"

    # Teacher AI lesson preparation
    AI_LESSON_PREP_API_KEY: str = ""
    AI_LESSON_PREP_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    AI_LESSON_PREP_MODEL: str = "glm-4.5-air"
    AI_LESSON_PREP_MAX_INPUT_TOKENS: int = 81920
    AI_LESSON_PREP_MAX_OUTPUT_TOKENS: int = 49152
    AI_LESSON_PREP_TIMEOUT_SECONDS: int = 90
    LLM_MODEL_DEFAULT: str = "qwen3.7-plus"  # 作业/考试/学情分析默认使用的模型

    # Qwen image generation
    QWEN_IMAGE_ENABLED: bool = False
    QWEN_IMAGE_API_KEY: str = ""
    QWEN_IMAGE_BASE_URL: str = "https://dashscope.aliyuncs.com"
    QWEN_IMAGE_ENDPOINT: str = "/api/v1/services/aigc/multimodal-generation/generation"
    QWEN_IMAGE_MODEL: str = "qwen-image-2.0-pro"
    QWEN_IMAGE_SIZE: str = "1472*1104"
    QWEN_IMAGE_TIMEOUT_SECONDS: int = 30
    QWEN_IMAGE_PROMPT_EXTEND: bool = False
    QWEN_IMAGE_WATERMARK: bool = False

    # SMS verification
    SMS_MOCK_ENABLED: bool = True
    SMS_CODE_EXPIRE_MINUTES: int = 5
    SMS_SEND_COOLDOWN_SECONDS: int = 60
    SMS_MAX_VERIFY_ATTEMPTS: int = 5
    ALIYUN_SMS_REGION_ID: str = "cn-hangzhou"
    ALIYUN_SMS_ENDPOINT: str = "dypnsapi.aliyuncs.com"
    ALIYUN_SMS_ACCESS_KEY_ID: str = ""
    ALIYUN_SMS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_SMS_SIGN_NAME: str = ""
    ALIYUN_SMS_TEMPLATE_CODE: str = ""
    
    # DB
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASS: str = "root"
    DB_NAME: str = "Software_Cup"

    # Gitea code repository integration
    GITEA_ENABLED: bool = False
    GITEA_BASE_URL: str = "http://127.0.0.1:3000"
    GITEA_PUBLIC_BASE_URL: str = "https://gezhisystem.com/gitea"
    GITEA_SSH_DOMAIN: str = "gezhisystem.com"
    GITEA_SSH_PORT: int = 2222
    GITEA_SSH_USER: str = "git"
    GITEA_API_TOKEN: str = ""
    GITEA_ORG: str = "campus"
    GITEA_DEFAULT_PRIVATE: bool = False
    GITEA_WEBHOOK_SECRET: str = "gezhi_webhook_secret_default"
    GITEA_PUBLIC_BACKEND_URL: str = "https://gezhisystem.com"
    GITEA_SYNC_MAX_BRANCHES: int = 20
    
    @property
    def DATABASE_URL(self):
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
