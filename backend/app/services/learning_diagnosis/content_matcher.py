"""将学习目标与站内可学习内容建立可解释、可去重的关联。

匹配顺序固定为：结构化知识标签 > 文本关键词 > 可注入语义提供者。默认只读取
现有 JsonStore，不生成不存在的内容；语义提供者仅作为后续 RAG/AI 扩展点。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .contracts import GoalContentAssociation, GoalVersion


class ContentMatcher:
    SNAPSHOT_FIELDS = {
        "title", "name", "description", "content", "text", "type", "questionType",
        "questionTitle", "correctAnswer", "correctAnswers", "options", "starterCode",
        "starter_code", "functionName", "funcName", "function_name", "publicCases",
        "testCases", "test_cases", "examples", "inputFormat", "input_format",
        "outputFormat", "output_format", "constraints", "hint", "language",
        "knowledgePoint", "knowledgeTags", "knowledge_points", "knowledgePointIds",
    }
    MODULE_TYPES = {
        "exams": "EXAM",
        "exam_questions": "EXAM",
        "homework": "HOMEWORK",
        "homeworks": "HOMEWORK",
        "course": "COURSEWARE",
        "courseware": "COURSEWARE",
        "courses": "COURSEWARE",
        "ranked": "RANKED",
        "coding": "CODING",
        "code_repository": "CODING",
        "mistakes": "WRONG_QUESTION",
    }

    def __init__(self, *, db=None, store=None, catalog: Iterable[dict[str, Any]] | None = None,
                 semantic_provider: Callable[[GoalVersion, list[dict[str, Any]]], Iterable[dict[str, Any]]] | None = None):
        self._store = store
        self._catalog = list(catalog) if catalog is not None else None
        self._semantic_provider = semantic_provider
        self._associations: dict[tuple[str, str, str], GoalContentAssociation] = {}
        if self._store is None and db is not None:
            from .evidence_store import LearningDiagnosisStore
            self._store = LearningDiagnosisStore(db)

    def _load_catalog(self, goal: GoalVersion) -> list[dict[str, Any]]:
        if self._catalog is not None:
            return [item for item in self._catalog if self._belongs_to_student(item, goal.student_id)]
        if self._store is None:
            return []
        # 只查询已知模块，避免把诊断自身记录再次当成学习内容。
        result: list[dict[str, Any]] = []
        raw_store = getattr(self._store, "store", None)
        db = getattr(raw_store, "db", None)
        if db is None:
            return result
        for module, content_type in self.MODULE_TYPES.items():
            # 题库/课件通常是公共记录（owner_id 为空），学生作答记录则按学生隔离；
            # 先取模块全量，再在下方按 owner 字段过滤，兼容两种历史存储方式。
            for payload in raw_store.list_payloads(module):
                item = dict(payload)
                if not self._belongs_to_student(item, goal.student_id):
                    continue
                if module in {"homework", "homeworks"} and isinstance(item.get("questions"), list):
                    for question in item["questions"]:
                        if not isinstance(question, dict) or not question.get("id"):
                            continue
                        expanded = dict(question)
                        expanded.setdefault("content_type", "HOMEWORK")
                        expanded.setdefault("source_module", "homework")
                        expanded.setdefault("content_id", f"{item.get('id')}:{question['id']}")
                        expanded.setdefault("source_route", f"homework-detail:{item.get('id')}")
                        expanded.setdefault("description", expanded.get("desc") or "")
                        if expanded.get("knowledgePoint") and not expanded.get("knowledgeTags"):
                            expanded["knowledgeTags"] = [expanded["knowledgePoint"]]
                        result.append(expanded)
                if module == "exams" and (
                    item.get("questionTitle") or item.get("knowledgeTags") or
                    (isinstance(item.get("source"), dict) and item["source"].get("type") in {"exam", "homework"})
                ):
                    item["content_type"] = "WRONG_QUESTION"
                item.setdefault("content_type", content_type)
                item.setdefault("source_module", module)
                item.setdefault("content_id", item.get("id") or item.get("questionId") or item.get("contentId"))
                if item.get("content_id"):
                    result.append(item)
        try:
            from app.models.ranked_question import RankedQuestion

            for question in db.query(RankedQuestion).all():
                result.append({
                    "content_type": "RANKED",
                    "content_id": question.question_id,
                    "source_module": "ranked",
                    "source_route": f"ranked-question:{question.question_id}",
                    "title": question.title,
                    "description": question.description,
                    "type": "programming",
                    "knowledgeTags": self._json_list(question.knowledge_tags),
                    "examples": self._json_list(question.examples),
                    "inputFormat": question.input_format,
                    "outputFormat": question.output_format,
                    "constraints": question.constraints,
                    "hint": question.hint,
                })
        except Exception:
            # Older deployments may not have the ranked question table yet.
            pass
        return result

    @staticmethod
    def _json_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value or "[]")
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    @staticmethod
    def _belongs_to_student(item: dict[str, Any], student_id: str) -> bool:
        owner = item.get("student_id", item.get("studentId", item.get("ownerId")))
        return owner in (None, "", student_id)

    @staticmethod
    def _goal_points(goal: GoalVersion) -> list[dict[str, str]]:
        points = goal.parsed_success_criteria.get("knowledge_points", []) if goal.parsed_success_criteria else []
        normalized: list[dict[str, str]] = []
        for point in points:
            if isinstance(point, str):
                normalized.append({"id": point, "name": point})
            elif isinstance(point, dict) and point.get("id"):
                normalized.append({"id": str(point["id"]), "name": str(point.get("name") or point["id"])})
        if normalized:
            return normalized
        return [{"id": "goal", "name": goal.raw_goal_text}]

    @staticmethod
    def _text(item: dict[str, Any]) -> str:
        values: list[str] = []
        for key in ("title", "name", "description", "content", "questionTitle", "subject", "course", "readme", "text", "desc"):
            value = item.get(key)
            if isinstance(value, str):
                values.append(value)
        for key in ("tags", "knowledgeTags", "knowledge_points", "knowledgePointIds"):
            value = item.get(key)
            if isinstance(value, list):
                values.extend(str(v) for v in value)
        return " ".join(values).lower()

    @staticmethod
    def _tokens(text: str) -> set[str]:
        # 中英文混合内容：英文按词切分，中文保留连续片段并由知识点名称做显式包含判断。
        return set(re.findall(r"[a-zA-Z][a-zA-Z0-9_+#.-]*|[\u4e00-\u9fff]{2,}", text.lower()))

    def _association(self, goal: GoalVersion, item: dict[str, Any], point_ids: list[str], score: float,
                     method: str, reason: str) -> GoalContentAssociation:
        content_type = str(item.get("content_type") or self.MODULE_TYPES.get(str(item.get("source_module")), "CONTENT"))
        content_id = str(item.get("content_id") or item.get("id"))
        digest = hashlib.sha256(f"{goal.goal_version_id}:{content_type}:{content_id}".encode()).hexdigest()[:24]
        now = datetime.now(timezone.utc)
        existing = self._associations.get((goal.goal_version_id, content_type, content_id))
        association = GoalContentAssociation(
            association_id=existing.association_id if existing else f"assoc-{digest}",
            goal_version_id=goal.goal_version_id,
            student_id=goal.student_id,
            content_type=content_type,
            content_id=content_id,
            source_module=str(item.get("source_module") or ""),
            source_route=str(item.get("source_route") or item.get("route") or ""),
            knowledge_point_ids=sorted(set(point_ids)),
            relevance_score=round(max(0.0, min(1.0, score)), 4),
            relevance_level="HIGH" if score >= .8 else ("MEDIUM" if score >= .5 else "LOW"),
            match_method=method,
            match_reason=reason,
            model_version=str(item.get("model_version") or ""),
            content_version=str(item.get("content_version") or item.get("updatedAt") or ""),
            content_snapshot={key: value for key, value in item.items() if key in self.SNAPSHOT_FIELDS},
            active=True,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._associations[(goal.goal_version_id, content_type, content_id)] = association
        if self._store is not None:
            self._store.create_content_association(association)
        return association

    @staticmethod
    def _as_goal(goal: GoalVersion | dict[str, Any]) -> GoalVersion:
        if isinstance(goal, GoalVersion):
            return goal
        payload = {key: value for key, value in dict(goal).items() if key != "id"}
        return GoalVersion.model_validate(payload)

    def match_goal(self, goal: GoalVersion | dict[str, Any], *, rebuild: bool = False) -> list[GoalContentAssociation]:
        goal = self._as_goal(goal)
        if rebuild:
            self._associations = {key: value for key, value in self._associations.items() if key[0] != goal.goal_version_id}
        points = self._goal_points(goal)
        catalog = self._load_catalog(goal)
        matches: list[GoalContentAssociation] = []
        for item in catalog:
            tags = item.get("knowledgeTags") or item.get("knowledge_tags") or item.get("knowledgePointIds") or item.get("knowledge_point_ids") or []
            tags = {str(tag).lower() for tag in tags} if isinstance(tags, list) else set()
            structured = [point["id"] for point in points if point["id"].lower() in tags]
            if structured:
                matches.append(self._association(goal, item, structured, .95, "STRUCTURED_TAG", "内容知识标签与目标知识点直接一致"))
                continue
            text = self._text(item)
            matched = [point for point in points if point["name"].lower() in text or point["id"].lower() in text or bool(self._tokens(point["name"]) & self._tokens(text))]
            if matched:
                ids = [point["id"] for point in matched]
                score = min(.85, .55 + .1 * len(ids))
                matches.append(self._association(goal, item, ids, score, "TEXT_KEYWORD", f"标题或正文包含目标知识点关键词：{', '.join(ids)}"))
        if not matches and self._semantic_provider is not None:
            for item in self._semantic_provider(goal, catalog) or []:
                if item.get("content_id") and item.get("knowledge_point_ids"):
                    matches.append(self._association(goal, item, list(item["knowledge_point_ids"]), float(item.get("relevance_score", .5)), "SEMANTIC_PROVIDER", str(item.get("match_reason") or "语义提供者返回匹配")))
        return sorted(matches, key=lambda item: item.relevance_score, reverse=True)

    def rebuild_for_goal(self, goal: GoalVersion | dict[str, Any]) -> list[GoalContentAssociation]:
        return self.match_goal(goal, rebuild=True)

    def list_for_goal(self, goal_version_id: str, student_id: str) -> list[GoalContentAssociation]:
        if self._store is not None:
            rows = self._store.list_content_associations(student_id, goal_version_id)
            return [GoalContentAssociation.model_validate(row) for row in rows]
        return [item for key, item in self._associations.items() if key[0] == goal_version_id and item.student_id == student_id and item.active]
