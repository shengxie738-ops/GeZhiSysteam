from __future__ import annotations

from typing import Any


class TaskResolver:
    """Resolve a path stage from trusted site content before using RAG fallback."""

    SOURCE_TYPES = {
        "WRONG_QUESTION": "EXISTING_WRONG_QUESTION",
        "EXAM": "EXISTING_EXAM",
        "HOMEWORK": "EXISTING_HOMEWORK",
        "COURSEWARE": "EXISTING_COURSEWARE",
        "COURSE": "EXISTING_COURSEWARE",
        "RANKED": "EXISTING_RANKED",
        "CODING": "EXISTING_SANDBOX",
    }
    PRIORITY = {
        "WRONG_QUESTION": 100,
        "EXAM": 95,
        "HOMEWORK": 90,
        "RANKED": 85,
        "COURSEWARE": 80,
        "COURSE": 80,
        "CODING": 75,
        "RAG_GENERATED": 50,
    }

    def resolve(self, task_type: str, knowledge_point_id: str, sources: list[dict[str, Any]] | None) -> dict[str, Any]:
        candidates = [dict(item) for item in (sources or [])]
        candidates.sort(key=lambda item: self._rank(item, task_type), reverse=True)
        for candidate in candidates:
            resolved = self._resolve_candidate(candidate, task_type, knowledge_point_id)
            if resolved is not None:
                return resolved
        return {}

    def _rank(self, item: dict[str, Any], task_type: str) -> tuple[float, float]:
        content_type = str(item.get("content_type") or item.get("source_type") or "").upper()
        executable = self._is_programming(item) if task_type in {"CODING_PRACTICE", "INDEPENDENT_RETEST"} else True
        return (float(self.PRIORITY.get(content_type, 0)) + (20 if executable else -100), float(item.get("relevance_score") or item.get("score") or 0))

    @staticmethod
    def _snapshot(item: dict[str, Any]) -> dict[str, Any]:
        return dict(item.get("content_snapshot") or item)

    def _is_programming(self, item: dict[str, Any]) -> bool:
        snapshot = self._snapshot(item)
        qtype = str(snapshot.get("type") or snapshot.get("questionType") or "").lower()
        return qtype in {"programming", "coding", "code", "编程题"} or bool(snapshot.get("starterCode") or snapshot.get("starter_code"))

    def _resolve_candidate(self, item: dict[str, Any], task_type: str, knowledge_point_id: str) -> dict[str, Any] | None:
        content_type = str(item.get("content_type") or item.get("source_type") or "").upper()
        snapshot = self._snapshot(item)
        if task_type in {"CODING_PRACTICE", "INDEPENDENT_RETEST"} and not self._is_programming(item):
            return None
        source_type = self.SOURCE_TYPES.get(content_type, "RAG_GENERATED" if content_type == "RAG_GENERATED" else "")
        if not source_type:
            return None
        source_ref = str(item.get("content_id") or item.get("chunk_id") or item.get("source_ref") or "") or None
        title = str(snapshot.get("questionTitle") or snapshot.get("title") or snapshot.get("name") or "")
        description = str(snapshot.get("description") or snapshot.get("content") or snapshot.get("text") or snapshot.get("desc") or "")
        payload: dict[str, Any] = {
            "knowledge_point_ids": [knowledge_point_id],
            "description": description,
            "material_title": title,
            "material_source": str(item.get("source_module") or item.get("source_name") or source_type),
        }
        if task_type == "KNOWLEDGE_REVIEW":
            payload["content"] = description or title
        elif task_type == "GUIDED_PRACTICE":
            payload["prompt"] = description or title
            payload["question"] = title
            if snapshot.get("options"):
                payload["options"] = snapshot["options"]
        else:
            function_name = str(snapshot.get("functionName") or snapshot.get("funcName") or snapshot.get("function_name") or f"solve_{knowledge_point_id}")
            cases = snapshot.get("testCases") or snapshot.get("test_cases") or snapshot.get("publicCases") or snapshot.get("examples") or []
            payload.update({
                "problem_statement": description or title,
                "function_name": function_name,
                "starter_code": str(snapshot.get("starterCode") or snapshot.get("starter_code") or ""),
                "contract": {"language": str(snapshot.get("language") or "python"), "function_name": function_name},
                "test_cases": self._normalize_cases(cases),
            })
        return {
            "source_type": source_type,
            "source_ref": source_ref,
            "title": title,
            "content_payload": payload,
            "priority": int(min(100, self.PRIORITY.get(content_type, 50))),
            "generation_metadata": {"method": "existing_content" if source_type.startswith("EXISTING_") else "rag_retrieval", "content_type": content_type},
        }

    @staticmethod
    def _normalize_cases(cases: Any) -> list[dict[str, Any]]:
        normalized = []
        for case in cases if isinstance(cases, list) else []:
            if not isinstance(case, dict):
                continue
            normalized.append({
                "input": case.get("input", []),
                "expected": case.get("expected", case.get("output")),
                "compareMode": case.get("compareMode", "exact"),
            })
        return normalized
