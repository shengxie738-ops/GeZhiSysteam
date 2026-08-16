from __future__ import annotations

from uuid import uuid4

from .contracts import SandboxExecutionResult


class SandboxAdapter:
    def normalize(self, payload: dict) -> SandboxExecutionResult:
        status = payload.get("status", "SANDBOX_ERROR")
        return SandboxExecutionResult(
            execution_id=str(payload.get("executionId") or payload.get("execution_id") or f"exec-{uuid4().hex[:10]}"),
            status=status,
            language=str(payload.get("language") or "python"),
            exit_code=payload.get("exitCode", payload.get("exit_code")),
            compile_result=dict(payload.get("compileResult") or payload.get("compile_result") or {}),
            test_summary=dict(payload.get("testSummary") or payload.get("test_summary") or {}),
            test_cases=list(payload.get("testCases") or payload.get("test_cases") or []),
            stdout=str(payload.get("stdout") or ""),
            stderr=str(payload.get("stderr") or ""),
            resource_usage=dict(payload.get("resourceUsage") or payload.get("resource_usage") or {}),
            knowledge_point_ids=list(payload.get("knowledgePointIds") or payload.get("knowledge_point_ids") or []),
        )
