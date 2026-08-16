import json
import re
from typing import Any

import httpx

from app.core.config import settings


class LessonPrepAIClient:
    def __init__(self, client_factory=httpx.AsyncClient):
        self.client_factory = client_factory

    async def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict[str, Any]:
        if not settings.AI_LESSON_PREP_API_KEY:
            raise RuntimeError("AI lesson preparation API key is not configured")
        payload = {
            "model": settings.AI_LESSON_PREP_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": settings.AI_LESSON_PREP_MAX_OUTPUT_TOKENS,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.AI_LESSON_PREP_API_KEY}",
            "Content-Type": "application/json",
        }
        async with self.client_factory(timeout=settings.AI_LESSON_PREP_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.AI_LESSON_PREP_BASE_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("AI response does not contain choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, dict):
            return content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("AI response content is empty")
        return self._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("AI response must be a JSON object")
        return value
