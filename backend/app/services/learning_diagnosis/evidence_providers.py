from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from .contracts import EvidenceRecord, Provenance


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceProvider(Protocol):
    def collect(self, student_id: str, session: dict[str, Any]) -> list[EvidenceRecord]: ...


class ExistingSystemEvidenceProvider:
    """将现有模块已经汇总的只读结果映射为统一证据。"""

    def collect(self, student_id: str, session: dict[str, Any]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for item in session.get("existing_evidence", []):
            source_type = str(item.get("source_type", "ASSIGNMENT"))
            records.append(
                EvidenceRecord(
                    evidence_id=str(item.get("evidence_id") or f"ev-{uuid4().hex[:10]}"),
                    student_id=student_id,
                    source_type=source_type,
                    source_ref=item.get("source_ref"),
                    knowledge_point_ids=list(item.get("knowledge_point_ids") or ["linked_list_boundary"]),
                    result=dict(item.get("result") or {}),
                    observed_at=item.get("observed_at") or _now(),
                    provenance=Provenance(
                        source="existing_system",
                        reliability=float(item.get("reliability", 0.8)),
                        source_ref=item.get("source_ref"),
                    ),
                    summary=str(item.get("summary") or ""),
                )
            )
        return records


class MockEvidenceProvider:
    def collect(self, student_id: str, session: dict[str, Any]) -> list[EvidenceRecord]:
        now = _now()
        return [
            EvidenceRecord(
                evidence_id=f"mock-assignment-{uuid4().hex[:8]}",
                student_id=student_id,
                source_type="ASSIGNMENT",
                source_ref="mock-assignment-linked-list",
                knowledge_point_ids=["linked_list_delete", "linked_list_boundary"],
                result={"score": 62, "failed_cases": ["EMPTY_LIST", "SINGLE_NODE"]},
                observed_at=now,
                provenance=Provenance(source="mock", reliability=0.8, source_ref="mock-assignment-linked-list"),
                summary="作业中的空链表和单节点场景反复失分。",
            ),
            EvidenceRecord(
                evidence_id=f"mock-exam-{uuid4().hex[:8]}",
                student_id=student_id,
                source_type="EXAM_WRONG",
                source_ref="mock-exam-linked-list",
                knowledge_point_ids=["linked_list_boundary"],
                result={"score": 58, "failed_cases": ["EMPTY_LIST"]},
                observed_at=now,
                provenance=Provenance(source="mock", reliability=0.85, source_ref="mock-exam-linked-list"),
                summary="考试错题显示空输入边界判断不稳定。",
            ),
            EvidenceRecord(
                evidence_id=f"mock-sandbox-{uuid4().hex[:8]}",
                student_id=student_id,
                source_type="SANDBOX",
                source_ref="mock-execution-linked-list",
                knowledge_point_ids=["linked_list_delete", "linked_list_boundary"],
                result={
                    "status": "TEST_FAILED",
                    "test_summary": {"total": 6, "passed": 4, "failed": 2},
                    "failed_cases": ["EMPTY_LIST", "SINGLE_NODE"],
                },
                observed_at=now,
                provenance=Provenance(source="mock-sandbox", reliability=0.95, source_ref="mock-execution-linked-list"),
                summary="代码沙箱通过 4/6 个测试，两个边界场景失败。",
            ),
        ]


class GitEvidenceProvider:
    def __init__(self, service: Any):
        self.service = service

    def collect(self, student_id: str, session: dict[str, Any]) -> list[EvidenceRecord]:
        if not bool(session.get("include_git_evidence", session.get("includeGitEvidence", False))):
            return []
        payload = self.service.get_learning_evidence(student_id=student_id, session=session)
        payload = payload or {}
        source_ref = payload.get("source_ref") or payload.get("sourceRef") or "git-project"
        return [
            EvidenceRecord(
                evidence_id=f"git-{uuid4().hex[:10]}",
                student_id=student_id,
                source_type="GIT",
                source_ref=source_ref,
                knowledge_point_ids=list(payload.get("knowledge_point_ids") or ["linked_list_delete"]),
                result={
                    "scope": list(payload.get("scope") or []),
                    "summary": str(payload.get("summary") or ""),
                },
                observed_at=_now(),
                provenance=Provenance(source="git", reliability=float(payload.get("reliability", 0.55)), source_ref=source_ref),
                summary=str(payload.get("summary") or "Git 项目证据已按用户选择纳入。"),
                include_git_evidence=True,
            )
        ]


class SandboxEvidenceProvider:
    def collect(self, student_id: str, session: dict[str, Any]) -> list[EvidenceRecord]:
        return [self.from_execution(student_id, item)[0] for item in session.get("sandbox_executions", [])]

    def from_execution(self, student_id: str, execution: dict[str, Any]) -> list[EvidenceRecord]:
        summary = execution.get("testSummary") or execution.get("test_summary") or {}
        knowledge_points = execution.get("knowledgePointIds") or execution.get("knowledge_point_ids") or ["linked_list_boundary"]
        status = execution.get("status", "SANDBOX_ERROR")
        return [
            EvidenceRecord(
                evidence_id=f"sandbox-{execution.get('executionId') or execution.get('execution_id') or uuid4().hex[:10]}",
                student_id=student_id,
                source_type="SANDBOX",
                source_ref=execution.get("executionId") or execution.get("execution_id"),
                knowledge_point_ids=list(knowledge_points),
                result={"status": status, "test_summary": dict(summary), "test_cases": list(execution.get("testCases") or execution.get("test_cases") or [])},
                observed_at=_now(),
                provenance=Provenance(source="code_sandbox", reliability=0.95, source_ref=execution.get("executionId")),
                summary=f"代码沙箱状态：{status}。",
            )
        ]
