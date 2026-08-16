from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .contracts import EvidenceRecord, Provenance


class GitPracticeService:
    """Turn opt-in, goal-related source-code analysis into low-weight evidence."""

    def __init__(self, service: Any | None = None):
        self.service = service

    def collect(self, student_id: str, session: dict[str, Any]) -> dict[str, Any]:
        if not bool(session.get("include_git_evidence")):
            return {"status": "disabled", "practice_score": None, "evidence": []}
        if self.service is None:
            return {"status": "insufficient_data", "practice_score": None, "evidence": [], "reason": "git service unavailable"}
        payload = self.service.get_learning_evidence(student_id=student_id, session=session) or {}
        target_ids = {str(item.get("id")) for item in session.get("current_knowledge_points", []) if item.get("id")}
        point_ids = [str(item) for item in payload.get("knowledge_point_ids", []) if str(item) in target_ids]
        relevant_files = list(payload.get("relevant_files") or payload.get("scope") or [])
        score = payload.get("practice_score")
        if not point_ids or not relevant_files or not isinstance(score, (int, float)):
            return {"status": "insufficient_data", "practice_score": None, "evidence": [], "reason": str(payload.get("summary") or "no relevant code")}
        bounded_score = round(max(0.0, min(100.0, float(score))), 2)
        source_ref = str(payload.get("source_ref") or "git-project")
        uncertainty = str(payload.get("uncertainty") or "仓库代码可能来自协作、复制或未提交修改，不能单独证明学生掌握；本证据仅作降权参考。")
        evidence = EvidenceRecord(
            evidence_id=f"git-{uuid4().hex[:12]}",
            student_id=student_id,
            source_type="GIT",
            source_ref=source_ref,
            knowledge_point_ids=point_ids,
            result={
                "status": "ANALYZED",
                "practice_score": bounded_score,
                "relevant_files": relevant_files,
                "analysis_basis": list(payload.get("analysis_basis") or ["目标知识点与代码结构/测试的语义相关性"]),
                "uncertainty": uncertainty,
                "summary": str(payload.get("summary") or "已找到与学习目标相关的代码证据"),
            },
            observed_at=datetime.now(timezone.utc),
            provenance=Provenance(source="gitea_goal_code_analysis", reliability=min(float(payload.get("reliability") or .55), .65), source_ref=source_ref),
            summary=str(payload.get("summary") or "Git 目标相关代码已按低权重纳入实践应用度。"),
            include_git_evidence=True,
        )
        return {"status": "analyzed", "practice_score": bounded_score, "evidence": [evidence]}
