"""幂等写入学习诊断演示数据，供本地验收和手动测试使用。"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.services.learning_diagnosis.workflow import DiagnosisWorkflow  # noqa: E402


STUDENT_IDS = ("demo-student", "23001020119")
GOAL = {
    "course": "数据结构",
    "course_name": "数据结构",
    "goal_text": "四周内掌握链表结构、指针引用与边界条件，并完成相关编程练习",
    "deadline": "2026-09-06",
    "weeks_remaining": 4,
    "weekly_minutes": 180,
    "self_reported_difficulty": "链表指针更新与边界条件容易遗漏",
    "include_git_evidence": False,
    "knowledge_points": [
        {"id": "linked_list_boundary", "name": "链表边界条件", "description": "处理空链表、单节点和头尾节点边界", "success_criteria": ["能识别并处理空链表与单节点"], "search_query": "链表 边界条件 空链表 单节点"},
        {"id": "linked_list_delete", "name": "链表删除操作", "description": "实现删除节点并维护前后指针关系", "success_criteria": ["能完成删除并维护指针"], "search_query": "链表 删除节点 指针"},
    ],
}


DEMO_EXISTING_EVIDENCE = [
    {
        "evidence_id": "demo-assignment-linked-list",
        "source_type": "ASSIGNMENT",
        "source_ref": "assignment-demo-linked-list-01",
        "knowledge_point_ids": ["linked_list_structure", "pointer_reference"],
        "result": {"score": 72, "completed": True, "failed_cases": ["SINGLE_NODE"]},
        "reliability": 0.82,
        "summary": "演示作业已完成，但单节点指针更新仍有一次失误。",
    },
    {
        "evidence_id": "demo-exam-linked-list",
        "source_type": "EXAM_WRONG",
        "source_ref": "exam-demo-linked-list-02",
        "knowledge_point_ids": ["linked_list_boundary"],
        "result": {"score": 58, "completed": True, "failed_cases": ["EMPTY_LIST", "SINGLE_NODE"]},
        "reliability": 0.88,
        "summary": "演示考试错题暴露空链表和单节点边界判断薄弱。",
    },
    {
        "evidence_id": "demo-ranked-linked-list",
        "source_type": "RANKED_RESULT",
        "source_ref": "ranked-demo-linked-list-03",
        "knowledge_point_ids": ["linked_list_delete", "linked_list_boundary"],
        "result": {"score": 66, "completed": True, "ranked": True},
        "reliability": 0.76,
        "summary": "演示排位题完成，删除操作基本正确但边界用例耗时较长。",
    },
]

DEMO_HISTORY_TRIGGERS = (
    {"trigger_type": "TASK_SUBMISSION", "failure_count": 2},
    {"trigger_type": "TASK_SUBMISSION", "failure_count": 3},
    {"trigger_type": "REMEDIATION_COMPLETED", "failure_count": 0},
)


async def ensure_path_history(workflow: DiagnosisWorkflow, student_id: str, result: dict, minimum_versions: int = 4) -> dict:
    session = result["session"]
    session_id = session["id"]
    paths = list(workflow.store.list_paths(student_id, session_id))
    if paths:
        result["path"] = paths[-1]
    while len(paths) < minimum_versions:
        trigger_index = min(max(len(paths) - 1, 0), len(DEMO_HISTORY_TRIGGERS) - 1)
        trigger = DEMO_HISTORY_TRIGGERS[trigger_index]
        result = await workflow.refresh_session(session_id, student_id, dict(trigger))
        paths.append(result["path"])
    return result


async def seed_student(workflow: DiagnosisWorkflow, student_id: str) -> dict:
    existing = workflow.store.list_sessions(student_id)
    if existing:
        latest = sorted(existing, key=lambda item: item.get("created_at", ""), reverse=True)[0]
        snapshots = workflow.store.list_snapshots(student_id, latest["id"])
        paths = workflow.store.list_paths(student_id, latest["id"])
        latest_snapshot = snapshots[-1] if snapshots else None
        latest_path = paths[-1] if paths else None
        stale_mock = any(str(ref).startswith("mock-") for ref in (latest_snapshot or {}).get("evidence_refs", []))
        stale_contract = any(not (item.get("content_payload") or item.get("learning_objective")) for item in (latest_path or {}).get("tasks", []))
        stale_missing_demo_evidence = not latest.get("existing_evidence") and not any(str(ref).startswith("demo-") for ref in (latest_snapshot or {}).get("evidence_refs", []))
        current_points = latest.get("current_knowledge_points")
        current_point_ids = {str(item.get("id")) for item in (current_points or [])}
        stale_goal_contract = bool(current_points) and not {"linked_list_boundary", "linked_list_delete"}.issubset(current_point_ids)
        if not stale_mock and not stale_contract and not stale_missing_demo_evidence and not stale_goal_contract and str(latest.get("status", "")).upper() != "ARCHIVED":
            result = await ensure_path_history(workflow, student_id, {"session": latest, "snapshot": latest_snapshot, "path": latest_path})
            return {"created": False, **result}
        # 旧版本曾经把 Mock 证据写入生产诊断快照。仅归档旧 session，确保最新演示链路完全由结构化 existing evidence 驱动。
        if hasattr(workflow.store, "update_session"):
            workflow.store.update_session(latest["id"], student_id, {"status": "ARCHIVED", "archived_reason": "stale_mock_demo"})
    goal = {**GOAL, "existing_evidence": [dict(item) for item in DEMO_EXISTING_EVIDENCE]}
    result = await workflow.create_session(student_id, goal)
    return {"created": True, **(await ensure_path_history(workflow, student_id, result))}


async def seed() -> dict:
    db = SessionLocal()
    try:
        workflow = DiagnosisWorkflow(db)
        return {student_id: await seed_student(workflow, student_id) for student_id in STUDENT_IDS}
    finally:
        db.close()


if __name__ == "__main__":
    print(asyncio.run(seed()))
