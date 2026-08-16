"""为演示账号 23001020119 注入"编程学习诊断"真实数据并增强展示效果。

流程：
  1. 运行现有种子 scripts/seed_learning_diagnosis_demo.py（幂等，创建目标为
     「链表边界与删除」的诊断 session + 多版本学习路径，全部走真实
     DiagnosisWorkflow，不伪造快照结构）；
  2. 后处理：把最新学习路径中已完成的任务标记为 COMPLETED（带真实时间线），
     并补充对应的 SANDBOX 通过证据与文本作答证据，使诊断页呈现
     「目标进行中、已完成大半」的优秀学习者状态。
幂等：证据使用固定 evidence_id，任务状态仅在未完成时更新。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

sys.path.insert(0, str(BACKEND_ROOT / "scripts"))

from app.core.database import SessionLocal  # noqa: E402
from app.services.learning_diagnosis.workflow import DiagnosisWorkflow  # noqa: E402
from seed_learning_diagnosis_demo import seed as seed_diagnosis_demo  # noqa: E402

STUDENT_ID = "23001020119"
CHINA_TZ = timezone(timedelta(hours=8))


def _at(days_ago: int, hour: int, minute: int) -> str:
    moment = datetime.now(CHINA_TZ) - timedelta(days=days_ago)
    return moment.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


# 已完成任务时间线：(task_id 后缀匹配, 开始时间, 完成时间)
COMPLETED_TASK_PLAN = [
    ("task-linked-list-boundary-review", _at(7, 20, 12), _at(7, 20, 58)),
    ("task-linked-list-boundary-guided", _at(6, 21, 5), _at(6, 21, 51)),
    ("task-linked-list-boundary-coding", _at(5, 19, 40), _at(5, 20, 36)),
    ("task-linked-list-boundary-retest", _at(3, 20, 18), _at(3, 20, 44)),
    ("task-linked-list-delete-review", _at(2, 20, 26), _at(2, 20, 49)),
    ("task-linked-list-delete-guided", _at(1, 21, 7), _at(1, 21, 39)),
]

EXTRA_EVIDENCE = [
    {
        "evidence_id": "sandbox-xieyu-linked-list-boundary-coding",
        "student_id": STUDENT_ID,
        "source_type": "SANDBOX",
        "source_ref": "exec-xieyu-linked-list-boundary-coding",
        "knowledge_point_ids": ["linked_list_boundary"],
        "result": {
            "status": "PASSED",
            "task_id": "task-linked-list-boundary-coding",
            "task_type": "CODING_PRACTICE",
            "hint_level": 1,
            "assessment_mode": False,
            "test_summary": {"total": 8, "passed": 8, "failed": 0},
            "test_cases": [
                {"name": "empty_list", "passed": True},
                {"name": "single_node", "passed": True},
                {"name": "two_nodes", "passed": True},
                {"name": "head_delete", "passed": True},
                {"name": "tail_delete", "passed": True},
                {"name": "middle_delete", "passed": True},
                {"name": "boundary_k_equals_len", "passed": True},
                {"name": "stress_10000", "passed": True},
            ],
        },
        "observed_at": datetime.now(timezone.utc) - timedelta(days=5),
        "provenance": {"source": "code_sandbox", "reliability": 0.95, "source_ref": "exec-xieyu-linked-list-boundary-coding"},
        "summary": "链表边界删除练习通过全部 8 个用例，仅使用 1 级提示。",
    },
    {
        "evidence_id": "sandbox-xieyu-linked-list-boundary-retest",
        "student_id": STUDENT_ID,
        "source_type": "SANDBOX",
        "source_ref": "exec-xieyu-linked-list-boundary-retest",
        "knowledge_point_ids": ["linked_list_boundary"],
        "result": {
            "status": "PASSED",
            "task_id": "task-linked-list-boundary-retest",
            "task_type": "INDEPENDENT_RETEST",
            "hint_level": 0,
            "assessment_mode": True,
            "test_summary": {"total": 6, "passed": 6, "failed": 0},
            "coverage": ["NORMAL", "BOUNDARY", "EXCEPTION"],
        },
        "observed_at": datetime.now(timezone.utc) - timedelta(days=3),
        "provenance": {"source": "code_sandbox", "reliability": 0.95, "source_ref": "exec-xieyu-linked-list-boundary-retest"},
        "summary": "独立复测无提示通过，空链表/单节点/头尾边界全覆盖。",
    },
    {
        "evidence_id": "answer-xieyu-linked-list-delete-guided",
        "student_id": STUDENT_ID,
        "source_type": "ASSIGNMENT",
        "source_ref": "learning-diagnosis-guided-linked-list-delete",
        "knowledge_point_ids": ["linked_list_delete"],
        "result": {
            "status": "COMPLETED",
            "score": 88,
            "task_id": "task-linked-list-delete-guided",
            "task_type": "GUIDED_PRACTICE",
            "hint_level": 1,
            "answer_length": 216,
            "evaluation_status": "OK",
            "evaluation_provider": "deterministic",
        },
        "observed_at": datetime.now(timezone.utc) - timedelta(days=1),
        "provenance": {"source": "learning_diagnosis_answer", "reliability": 0.75, "source_ref": "learning-diagnosis-guided-linked-list-delete"},
        "summary": "删除节点时先定位前驱、再改 prev.next 指向的表述完整，能指出哑结点对删除头节点的作用。",
    },
]


def _enhance_latest_path(workflow: DiagnosisWorkflow) -> dict:
    sessions = workflow.store.list_sessions(STUDENT_ID)
    if not sessions:
        return {"error": "NO_SESSION"}
    latest = sorted(sessions, key=lambda item: item.get("created_at", ""), reverse=True)[0]
    session_id = latest["id"]
    paths = workflow.store.list_paths(STUDENT_ID, session_id)
    if not paths:
        return {"error": "NO_PATH"}
    current = paths[-1]
    tasks = [dict(task) for task in current.get("tasks") or []]
    completed = 0
    for suffix, started_at, finished_at in COMPLETED_TASK_PLAN:
        for task in tasks:
            task_id = str(task.get("task_id") or "")
            if task_id == suffix and task.get("status") != "COMPLETED":
                task["status"] = "COMPLETED"
                task["started_at"] = started_at
                task["completed_at"] = finished_at
                completed += 1
    workflow.store.update_path(str(current.get("id") or current.get("path_id")), STUDENT_ID, {"tasks": tasks})
    return {
        "sessionId": session_id,
        "pathId": str(current.get("id") or current.get("path_id")),
        "pathVersion": current.get("path_version"),
        "tasksTotal": len(tasks),
        "tasksCompleted": sum(1 for t in tasks if t.get("status") == "COMPLETED"),
        "newlyMarked": completed,
        "taskStatuses": [{"id": t.get("task_id"), "status": t.get("status")} for t in tasks],
    }


def _add_extra_evidence(workflow: DiagnosisWorkflow) -> int:
    existing = {item.get("evidence_id") for item in workflow.store.list_evidence(STUDENT_ID)}
    added = 0
    for item in EXTRA_EVIDENCE:
        if item["evidence_id"] in existing:
            continue
        workflow.store.create_evidence(item)
        added += 1
    return added


async def run() -> dict:
    seed_result = await seed_diagnosis_demo()
    db = SessionLocal()
    try:
        workflow = DiagnosisWorkflow(db)
        enhancement = _enhance_latest_path(workflow)
        evidence_added = _add_extra_evidence(workflow)
        sessions = workflow.store.list_sessions(STUDENT_ID)
        latest = sorted(sessions, key=lambda item: item.get("created_at", ""), reverse=True)[0]
        return {
            "seed": {
                student_id: {"created": result.get("created", False), "sessionId": result["session"]["id"]}
                for student_id, result in seed_result.items()
            },
            "enhancement": enhancement,
            "evidenceAdded": evidence_added,
            "evidenceTotal": len(workflow.store.list_evidence(STUDENT_ID)),
            "snapshots": len(workflow.store.list_snapshots(STUDENT_ID, latest["id"])),
            "paths": len(workflow.store.list_paths(STUDENT_ID, latest["id"])),
        }
    finally:
        db.close()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
