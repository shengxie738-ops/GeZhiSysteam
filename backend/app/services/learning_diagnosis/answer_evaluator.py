from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from app.services.default_agents import get_default_agents
from app.services.model_registry import get_cached_chat_model


class AnswerEvaluator:
    """文字任务的 AI 语义评价适配器，失败时返回可解释的降级信号。"""

    def __init__(self, model_client=None, timeout_seconds: float | None = None):
        self.model_client = model_client
        agent = next((item for item in get_default_agents() if item.get("id") == "agent_homework_diagnoser"), {})
        self.model_id = agent.get("model") or "qwen3.7-plus"
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else os.getenv("LEARNING_DIAGNOSIS_AI_TIMEOUT_SECONDS", "3"))

    async def evaluate(self, task: dict[str, Any], answer: str) -> dict[str, Any]:
        try:
            model = self.model_client or get_cached_chat_model(self.model_id, temperature=0)
            prompt = json.dumps({
                "instruction": "只返回JSON，字段 score(0-100)、status、feedback、criteria；根据任务目标和成功标准评价学生答案，不要臆造未提供的事实。",
                "task": {"title": task.get("title"), "objective": task.get("learning_objective"), "success_criteria": (task.get("content_payload") or {}).get("success_criteria", [])},
                "answer": answer,
            }, ensure_ascii=False)
            response = await asyncio.wait_for(model.ainvoke(prompt), timeout=self.timeout_seconds)
            payload = self._decode(response)
            score = float(payload.get("score"))
            if not 0 <= score <= 100:
                raise ValueError("score out of range")
            return {"score": round(score, 2), "status": "AI_EVALUATED", "provider": "agent_homework_diagnoser", "feedback": str(payload.get("feedback") or ""), "criteria": payload.get("criteria") if isinstance(payload.get("criteria"), list) else []}
        except Exception as exc:
            return {"score": None, "status": "DEGRADED", "provider": "deterministic", "feedback": "AI 评价暂不可用，已使用规则评分。", "criteria": [], "error": f"{type(exc).__name__}: {exc}"}

    @staticmethod
    def _decode(response: Any) -> dict[str, Any]:
        content = getattr(response, "content", response)
        if isinstance(content, dict):
            return content
        if isinstance(content, list):
            content = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
        text = str(content or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
