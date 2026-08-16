from __future__ import annotations

from typing import Any
import json
import asyncio
import os

from pydantic import BaseModel, Field

from app.services.default_agents import get_default_agents
from app.services.model_registry import get_cached_chat_model


class ExplanationOutput(BaseModel):
    summary: str = ""
    strengths: list[dict[str, Any]] = Field(default_factory=list)
    weaknesses: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    provider: str = "deterministic"
    status: str = "DEGRADED"
    degraded_reason: str | None = None


class LlmExplainer:
    def __init__(self, model_client=None, timeout_seconds: float | None = None):
        self.model_client = model_client
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else os.getenv("LEARNING_DIAGNOSIS_AI_TIMEOUT_SECONDS", "3"))
        tutor = next((item for item in get_default_agents() if item.get("id") == "agent_tutor"), {})
        self.model_id = tutor.get("model") or "qwen3.7-plus"

    def validate_output(self, payload: dict[str, Any], valid_evidence_refs: set[str], valid_rag_refs: set[str]) -> ExplanationOutput:
        result = ExplanationOutput.model_validate(payload)
        for section in [*result.strengths, *result.weaknesses, *result.recommended_actions]:
            for evidence_ref in section.get("evidenceRefs", section.get("evidence_refs", [])):
                if evidence_ref not in valid_evidence_refs:
                    raise ValueError(f"unknown evidence reference: {evidence_ref}")
            for rag_ref in section.get("ragRefs", section.get("rag_refs", [])):
                if rag_ref not in valid_rag_refs:
                    raise ValueError(f"unknown RAG reference: {rag_ref}")
        return result

    async def explain(self, rule_facts: dict[str, Any], evidence_summaries: list[dict[str, Any]], rag_references: list[dict[str, Any]]) -> ExplanationOutput:
        valid_evidence = {item.get("evidenceId") or item.get("evidence_id") for item in evidence_summaries}
        valid_rag = {item.get("chunkId") or item.get("chunk_id") for item in rag_references}
        try:
            model = self.model_client or get_cached_chat_model(self.model_id, temperature=0.1)
            prompt = json.dumps({
                "instruction": "请仅返回JSON，解释规则评估结果；所有evidenceRefs和ragRefs必须来自给定列表。",
                "rule_facts": rule_facts,
                "evidence": evidence_summaries,
                "rag_references": rag_references,
            }, ensure_ascii=False)
            response = await asyncio.wait_for(model.ainvoke(prompt), timeout=self.timeout_seconds)
            content = getattr(response, "content", response)
            if isinstance(content, list):
                content = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
            if isinstance(content, dict):
                payload = content
            else:
                text = str(content).strip()
                if text.startswith("```"):
                    text = text.strip("`")
                    if text.startswith("json"):
                        text = text[4:].strip()
                payload = json.loads(text)
            payload = {**payload, "provider": "llm", "status": "AI_GENERATED", "degraded_reason": None}
            return self.validate_output(payload, valid_evidence, valid_rag)
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}" if not str(exc) else str(exc)
            return self._fallback(rule_facts, valid_evidence, valid_rag, reason)

    def _fallback(self, rule_facts: dict[str, Any], valid_evidence: set[str], valid_rag: set[str], reason: str) -> ExplanationOutput:
        payload = {
            "summary": "当前知识点已有部分基础，但边界条件仍需通过独立复测确认。",
            "strengths": [],
            "weaknesses": [{"knowledgePointId": rule_facts.get("knowledge_point_id", ""), "text": "边界场景处理不稳定。", "evidenceRefs": sorted(valid_evidence), "ragRefs": sorted(valid_rag)}],
            "recommended_actions": [{"actionType": "BOUNDARY_PRACTICE", "text": "完成空链表和单节点分类练习。"}],
            "uncertainty_notes": ["独立复测完成前，不将当前结果解释为已掌握。"],
        }
        payload.update({"provider": "deterministic", "status": "DEGRADED", "degraded_reason": reason})
        result = self.validate_output(payload, valid_evidence, valid_rag)
        return result
