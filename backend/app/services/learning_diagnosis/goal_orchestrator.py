from __future__ import annotations

import json
import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from app.services.default_agents import get_default_agents
from app.services.model_registry import get_cached_chat_model


class GoalOrchestrator:
    """将学生目标解析为可追踪的目标版本和动态知识点集合。"""

    def __init__(self, model_client=None, model_id: str | None = None, timeout_seconds: float | None = None):
        self.model_client = model_client
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else os.getenv("LEARNING_DIAGNOSIS_AI_TIMEOUT_SECONDS", "3"))
        if model_client is None:
            planner = next(item for item in get_default_agents() if item.get("id") == "agent_planner")
            self.model_id = model_id or planner.get("model") or "qwen3.7-max"

    async def parse_goal(self, goal: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_goal(goal)
        explicit_points = self._validate_points(goal.get("knowledge_points") or goal.get("knowledgePoints"))
        if len(explicit_points) >= 2:
            return {"provider": "existing_system", "status": "STRUCTURED", "error": None, "normalized_goal": normalized, "knowledge_points": explicit_points}
        model = self.model_client
        if model is None:
            try:
                model = get_cached_chat_model(self.model_id, temperature=0)
            except Exception as exc:
                return self._fallback(normalized, f"model unavailable: {exc}")
        prompt = self._prompt(normalized)
        try:
            response = await asyncio.wait_for(model.ainvoke(prompt), timeout=self.timeout_seconds)
            payload = self._decode_response(response)
            points = self._validate_points(payload.get("knowledge_points") or payload.get("knowledgePoints"))
            if len(points) < 2:
                raise ValueError("planner must return at least two knowledge points")
            return {
                "provider": "agent_planner",
                "status": "AI_GENERATED",
                "error": None,
                "normalized_goal": normalized,
                "knowledge_points": points,
            }
        except Exception as exc:
            return self._fallback(normalized, str(exc))

    def _normalize_goal(self, goal: dict[str, Any]) -> dict[str, Any]:
        raw = goal.get("raw_goal_text") or goal.get("goal_text") or goal.get("goal") or ""
        course_name = goal.get("course_name") or goal.get("course") or ""
        deadline = goal.get("deadline")
        if deadline:
            try:
                deadline = datetime.fromisoformat(str(deadline).replace("Z", "+00:00")).isoformat()
            except ValueError:
                deadline = str(deadline)
        return {
            "raw_goal_text": str(raw or f"掌握{course_name or '课程核心知识'}"),
            "course_id": str(goal.get("course_id") or ""),
            "course_name": str(course_name),
            "deadline": deadline,
            "weekly_minutes": int(goal.get("weekly_minutes") or 180),
            "self_reported_difficulty": str(goal.get("self_reported_difficulty") or ""),
            "reuse_existing_evidence": bool(goal.get("reuse_existing_evidence", goal.get("include_git_evidence", True))),
            "existing_evidence": [dict(item) for item in (goal.get("existing_evidence") or []) if isinstance(item, dict)],
        }

    def _prompt(self, goal: dict[str, Any]) -> str:
        return (
            "你是学习路径规划 Agent。请仅返回 JSON，不要 Markdown。"
            "根据目标拆解至少两个动态知识点，每个知识点必须有 id、name、description、success_criteria、search_query。"
            f"目标：{json.dumps(goal, ensure_ascii=False)}"
        )

    def _decode_response(self, response: Any) -> dict[str, Any]:
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
        if isinstance(content, dict):
            return content
        text = str(content).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def _validate_points(self, points: Any) -> list[dict[str, Any]]:
        if not isinstance(points, list):
            return []
        result = []
        for item in points:
            if not isinstance(item, dict):
                continue
            point_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            description = str(item.get("description") or "").strip()
            criteria = item.get("success_criteria") or item.get("successCriteria") or []
            query = str(item.get("search_query") or item.get("searchQuery") or name).strip()
            if point_id and name and description and isinstance(criteria, list) and criteria and query:
                result.append({"id": point_id, "name": name, "description": description, "success_criteria": criteria, "search_query": query})
        return result

    def _fallback(self, goal: dict[str, Any], error: str) -> dict[str, Any]:
        text = f"{goal['raw_goal_text']} {goal['course_name']}".lower()
        if "树" in text or "tree" in text:
            points = [
                {"id": "tree_traversal", "name": "树的遍历", "description": "掌握前序、中序和后序遍历", "success_criteria": ["能区分三种遍历"], "search_query": "树的遍历"},
                {"id": "tree_recursion", "name": "递归实现", "description": "使用递归实现树遍历", "success_criteria": ["能写出递归遍历"], "search_query": "树遍历递归"},
            ]
        else:
            points = [
                {"id": "course_core_concept", "name": "核心概念", "description": f"理解{goal['course_name'] or '课程'}的核心概念", "success_criteria": ["能够解释核心概念"], "search_query": goal["course_name"] or goal["raw_goal_text"]},
                {"id": "course_practice", "name": "实践应用", "description": "将核心概念应用到典型问题", "success_criteria": ["能够完成一道综合练习"], "search_query": f"{goal['course_name']} 综合练习"},
            ]
        return {"provider": "deterministic", "status": "DEGRADED", "error": error, "normalized_goal": goal, "knowledge_points": points}
