from __future__ import annotations

from .contracts import PathVersion
from .task_templates import build_task


class LearningPathPlanner:
    def plan(
        self,
        assessments,
        goal,
        previous_path,
        failure_count=0,
        trigger_type="INITIAL",
        knowledge_point_meta=None,
        retrieved_content=None,
    ) -> PathVersion:
        version = (previous_path.path_version + 1) if previous_path else 1
        knowledge_point_ids = list(assessments) or ["course_core_concept"]
        knowledge_point_id = knowledge_point_ids[0]
        meta_map = knowledge_point_meta or {}
        point_meta = meta_map.get(knowledge_point_id, {})
        point_name = str(point_meta.get("name") or knowledge_point_id.replace("_", " "))
        tasks = []
        reasons = []
        if not previous_path:
            for point_id in knowledge_point_ids:
                slug = point_id.replace("_", "-")
                task_meta = meta_map.get(point_id, {})
                point_retrieved = (retrieved_content or {}).get(point_id, []) if isinstance(retrieved_content, dict) else (retrieved_content or [])
                tasks.extend([
                    build_task("linked-list-review", point_id, task_id=f"task-{slug}-review", knowledge_point_meta=task_meta, retrieved_content=point_retrieved),
                    build_task("linked-list-guided", point_id, task_id=f"task-{slug}-guided", knowledge_point_meta=task_meta, retrieved_content=point_retrieved),
                    build_task("linked-list-coding", point_id, task_id=f"task-{slug}-coding", knowledge_point_meta=task_meta, retrieved_content=point_retrieved),
                    build_task("linked-list-retest", point_id, task_id=f"task-{slug}-retest", allowed_hint_levels=[1], knowledge_point_meta=task_meta, retrieved_content=point_retrieved),
                ])
            reasons.append("INITIAL_DIAGNOSIS")
        elif failure_count >= 3:
            remediation = build_task(
                "linked-list-guided",
                knowledge_point_id,
                task_id=f"task-remediation-{version}",
                title=f"Remediation · {point_name}",
                difficulty=1,
                parent_task_id=f"task-{knowledge_point_id.replace('_', '-')}-coding",
                return_task_id=f"task-{knowledge_point_id.replace('_', '-')}-coding",
                knowledge_point_meta=point_meta,
            )
            tasks = [remediation] + list(previous_path.tasks)
            reasons.extend(["CONSECUTIVE_FAILURES", "PREREQUISITE_REMEDIATION"])
        elif failure_count >= 2:
            micro_tasks = [
                build_task("linked-list-guided", knowledge_point_id, task_id=f"task-micro-empty-{version}", title=f"Micro task · {point_name} boundary A", difficulty=1, parent_task_id=f"task-{knowledge_point_id.replace('_', '-')}-guided", knowledge_point_meta=point_meta),
                build_task("linked-list-guided", knowledge_point_id, task_id=f"task-micro-single-{version}", title=f"Micro task · {point_name} boundary B", difficulty=1, parent_task_id=f"task-{knowledge_point_id.replace('_', '-')}-guided", knowledge_point_meta=point_meta),
            ]
            tasks = micro_tasks + list(previous_path.tasks)
            reasons.extend(["CONSECUTIVE_FAILURES", "TASK_SPLIT"])
        else:
            tasks = list(previous_path.tasks)
            reasons.append("BOUNDARY_CASES_IMPROVED" if trigger_type == "REMEDIATION_COMPLETED" else trigger_type)

        old_ids = {task.task_id for task in previous_path.tasks} if previous_path else set()
        new_ids = {task.task_id for task in tasks}
        return PathVersion(
            path_version=version,
            previous_version=previous_path.path_version if previous_path else None,
            trigger_type=trigger_type,
            change_reason_codes=reasons,
            tasks=tasks,
            added_tasks=sorted(new_ids - old_ids),
            removed_tasks=sorted(old_ids - new_ids),
            retained_tasks=sorted(old_ids & new_ids),
            evidence_refs=[],
        )
