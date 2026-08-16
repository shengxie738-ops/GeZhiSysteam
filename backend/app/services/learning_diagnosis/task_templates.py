from __future__ import annotations

from uuid import uuid4

from .catalog import TASK_TEMPLATES, KNOWLEDGE_POINTS
from .contracts import PathTask
from .task_resolver import TaskResolver


def build_task(template_id: str, knowledge_point_id: str, **overrides) -> PathTask:
    template = TASK_TEMPLATES[template_id]
    meta = dict(overrides.pop("knowledge_point_meta", {}) or {})
    catalog_meta = KNOWLEDGE_POINTS.get(knowledge_point_id, {})
    name = str(meta.get("name") or catalog_meta.get("name") or knowledge_point_id.replace("_", " "))
    description = str(meta.get("description") or f"围绕{name}完成本阶段学习任务")
    criteria = list(meta.get("success_criteria") or [f"能够解释{name}并完成对应练习"])
    task_type = template["task_type"]
    retrieved_content = list(overrides.pop("retrieved_content", []) or [])
    payload = dict(overrides.pop("content_payload", {}) or {})
    resolved = TaskResolver().resolve(task_type, knowledge_point_id, retrieved_content)
    payload.update(resolved.get("content_payload") or {})
    payload.setdefault("knowledge_point_ids", [knowledge_point_id])
    payload.setdefault("knowledge_point_name", name)
    payload.setdefault("description", description)
    payload.setdefault("success_criteria", criteria)
    source_type = overrides.get("source_type") or resolved.get("source_type")
    source_ref = overrides.get("source_ref") or resolved.get("source_ref")
    if retrieved_content and not resolved:
        source = retrieved_content[0]
        source_type = str(source.get("source_type") or source.get("sourceType") or "RAG_GENERATED")
        source_ref = str(source.get("source_ref") or source.get("sourceRef") or source.get("chunk_id") or source.get("chunkId") or source.get("content_id") or "") or None
        material = str(source.get("content") or source.get("text") or source.get("description") or "").strip()
        if material:
            payload.setdefault("content", material)
        payload.setdefault("material_title", str(source.get("title") or source.get("name") or "关联学习材料"))
        payload.setdefault("material_source", str(source.get("source_name") or source.get("sourceName") or source.get("source_module") or source_type))
    if task_type == "KNOWLEDGE_REVIEW":
        payload.setdefault("content", f"阅读并复述{name}：{description}")
    elif task_type == "GUIDED_PRACTICE":
        payload.setdefault("guided_steps", [f"识别{name}的输入与边界", f"根据提示完成{name}练习", "检查结果并总结"])
    elif task_type in {"CODING_PRACTICE", "INDEPENDENT_RETEST"}:
        payload.setdefault("function_name", f"solve_{knowledge_point_id}")
        payload.setdefault("starter_code", f"def solve_{knowledge_point_id}(value):\n    # 请围绕{name}实现\n    pass\n")
        payload.setdefault("contract", {"language": "python", "function_name": f"solve_{knowledge_point_id}"})
        payload.setdefault("test_cases", [
            {"input": ["normal"], "expected": "normal", "compareMode": "exact"},
            {"input": ["boundary"], "expected": "boundary", "compareMode": "exact"},
            {"input": ["empty"], "expected": "empty", "compareMode": "exact"},
        ])
    return PathTask(
        task_id=overrides.get("task_id", f"{template_id}-{uuid4().hex[:8]}"),
        title=overrides.get("title", resolved.get("title") or template["title"]),
        knowledge_point_ids=[knowledge_point_id],
        task_type=template["task_type"],
        difficulty=overrides.get("difficulty", template["difficulty"]),
        estimated_minutes=overrides.get("estimated_minutes", template["minutes"]),
        parent_task_id=overrides.get("parent_task_id"),
        return_task_id=overrides.get("return_task_id"),
        allowed_hint_levels=overrides.get("allowed_hint_levels", [1, 2, 3, 4, 5]),
        learning_objective=overrides.get("learning_objective", f"掌握{name}"),
        why_this_task=overrides.get("why_this_task", f"该任务用于验证你对{name}的理解与应用"),
        source_type=source_type or "AI_GENERATED",
        source_ref=source_ref,
        content_payload=payload,
        priority=overrides.get("priority", resolved.get("priority", 50)),
        prerequisite_task_ids=overrides.get("prerequisite_task_ids", []),
        generation_metadata=overrides.get("generation_metadata", resolved.get("generation_metadata") or {"method": "retrieved_content" if retrieved_content else "goal_specific_template", "knowledge_point": knowledge_point_id}),
    )
