from __future__ import annotations

import json
import asyncio
import os
from typing import Any

from app.services.default_agents import get_default_agents
from app.services.model_registry import get_cached_chat_model


class HintService:
    """Generate progressive, attempt-aware tutoring hints with a transparent fallback."""

    def __init__(self, model_client=None, model_id: str | None = None, timeout_seconds: float | None = None):
        self.model_client = model_client
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else os.getenv("LEARNING_DIAGNOSIS_AI_TIMEOUT_SECONDS", "3"))
        tutor = next((item for item in get_default_agents() if item.get("id") == "agent_tutor"), {})
        self.model_id = model_id or tutor.get("model") or "qwen3.7-plus"

    async def generate(self, task: dict[str, Any], level: int, attempt: dict[str, Any] | None = None) -> dict[str, Any]:
        attempt = dict(attempt or {})
        try:
            model = self.model_client or get_cached_chat_model(self.model_id, temperature=0.1)
            response = await asyncio.wait_for(model.ainvoke(self._prompt(task, level, attempt)), timeout=self.timeout_seconds)
            payload = self._decode(response)
            content = str(payload.get("content") or "").strip()
            if not content:
                raise ValueError("hint content is empty")
            return {
                "content": content,
                "focus": str(payload.get("focus") or task.get("title") or "当前任务"),
                "based_on_attempt": str(payload.get("based_on_attempt") or payload.get("basedOnAttempt") or self._attempt_summary(attempt)),
                "model_metadata": {"status": "AI_GENERATED", "provider": "agent_tutor", "model_id": self.model_id, "error": None},
            }
        except Exception as exc:
            return self._fallback(task, level, attempt, str(exc))

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

    def _prompt(self, task: dict[str, Any], level: int, attempt: dict[str, Any]) -> str:
        payload = task.get("content_payload") or {}
        return (
            "你是编程学习诊断中的 Tutor Agent。只返回 JSON，字段为 content、focus、based_on_attempt。"
            "提示必须针对学生本次尝试，逐级增加信息量，不直接虚构运行结果。"
            f"当前 Level={level}/5。Level 1 只指出方向，Level 2 指出关键概念，Level 3 给步骤，"
            "Level 4 给局部伪代码，Level 5 才允许参考答案。独立复测只允许 Level 1。"
            f"任务={json.dumps({'task_id': task.get('task_id'), 'title': task.get('title'), 'task_type': task.get('task_type'), 'objective': task.get('learning_objective'), 'payload': payload}, ensure_ascii=False)};"
            f"本次尝试={json.dumps(attempt, ensure_ascii=False, default=str)}"
        )

    @staticmethod
    def _attempt_summary(attempt: dict[str, Any]) -> str:
        if attempt.get("error"):
            return f"本次尝试出现错误：{attempt['error']}"
        text = str(attempt.get("answer") or attempt.get("code") or "").strip()
        return "已结合本次作答内容" if text else "尚无可分析的本次作答"

    def _fallback(self, task: dict[str, Any], level: int, attempt: dict[str, Any], error: str) -> dict[str, Any]:
        payload = task.get("content_payload") or {}
        point = str(payload.get("knowledge_point_name") or task.get("learning_objective") or task.get("title") or "当前知识点")
        templates = {
            1: f"先确认题目的输入、输出和 {point} 的边界条件，再定位第一处不满足要求的步骤。",
            2: f"把 {point} 拆成正常、边界、异常三类场景，逐一检查当前作答是否覆盖。",
            3: f"建议按三步处理：列出条件；执行核心过程；用最小边界样例验证结果。",
            4: f"先写出局部伪代码：validate_input -> solve_{point} -> verify_output，再补全缺失部分。",
            5: str(payload.get("reference_answer") or payload.get("starter_code") or f"请依据任务契约完成 {point}，并逐个运行任务内测试用例。"),
        }
        return {
            "content": templates[max(1, min(int(level), 5))],
            "focus": point,
            "based_on_attempt": self._attempt_summary(attempt),
            "model_metadata": {"status": "DEGRADED", "provider": "deterministic", "model_id": self.model_id, "error": error},
        }
