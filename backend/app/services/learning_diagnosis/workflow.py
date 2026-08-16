from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.services.code_sandbox import CodeSandbox

from .contracts import DiagnosisSnapshot, EvidenceRecord, KnowledgeAssessment, PathVersion, Provenance
from .content_matcher import ContentMatcher
from .answer_evaluator import AnswerEvaluator
from .evidence_providers import ExistingSystemEvidenceProvider, SandboxEvidenceProvider
from .evidence_store import LearningDiagnosisStore
from .goal_orchestrator import GoalOrchestrator
from .git_practice_service import GitPracticeService
from .hint_service import HintService
from .knowledge_retriever import KnowledgeRetrievalRequest, select_knowledge_retriever
from .llm_explainer import LlmExplainer
from .path_planner import LearningPathPlanner
from .rule_engine import RuleEngine
from .sandbox_adapter import SandboxAdapter


class DiagnosisWorkflow:
    def __init__(
        self,
        db,
        retriever_mode: str | None = None,
        goal_orchestrator=None,
        model_client=None,
        retriever=None,
        hint_service=None,
        git_practice_service=None,
    ):
        self.store = LearningDiagnosisStore(db)
        self.retriever = retriever or select_knowledge_retriever(retriever_mode)
        self.goal_orchestrator = goal_orchestrator or GoalOrchestrator(model_client=model_client)
        self.rule_engine = RuleEngine()
        self.planner = LearningPathPlanner()
        self.explainer = LlmExplainer(model_client=model_client)
        self.code_sandbox = CodeSandbox()
        self.sandbox_adapter = SandboxAdapter()
        self.hint_service = hint_service or HintService(model_client=model_client)
        self.git_practice_service = git_practice_service or GitPracticeService()
        self.content_matcher = ContentMatcher(store=self.store)
        self.answer_evaluator = AnswerEvaluator(model_client=model_client)

    async def create_session(self, student_id: str, goal: dict) -> dict:
        session_id = f"session-{uuid4().hex[:12]}"
        parsed_goal = await self.goal_orchestrator.parse_goal(goal)
        normalized_goal = dict(parsed_goal.get("normalized_goal") or goal)
        goal_version_id = f"goal-{uuid4().hex[:12]}"
        goal_version = self.store.create_goal_version({
            "goal_version_id": goal_version_id,
            "session_id": session_id,
            "student_id": student_id,
            "raw_goal_text": normalized_goal.get("raw_goal_text") or normalized_goal.get("goal_text") or normalized_goal.get("course_name") or "",
            "course_id": normalized_goal.get("course_id", ""),
            "course_name": normalized_goal.get("course_name") or normalized_goal.get("course", ""),
            "deadline": normalized_goal.get("deadline"),
            "weekly_minutes": normalized_goal.get("weekly_minutes", 180),
            "self_reported_difficulty": normalized_goal.get("self_reported_difficulty", ""),
            "reuse_existing_evidence": normalized_goal.get("reuse_existing_evidence", True),
            "parsed_success_criteria": {"knowledge_points": parsed_goal.get("knowledge_points", []), "provider": parsed_goal.get("provider"), "status": parsed_goal.get("status"), "error": parsed_goal.get("error")},
            "created_at": datetime.now(timezone.utc),
        })
        session = self.store.create_session(
            {
                "id": session_id,
                "student_id": student_id,
                "goal": normalized_goal,
                "existing_evidence": list(normalized_goal.get("existing_evidence") or []),
                "goal_parse": parsed_goal,
                "goal_version_id": goal_version_id,
                "current_goal_version": goal_version_id,
                "current_knowledge_points": parsed_goal.get("knowledge_points", []),
                "include_git_evidence": bool(goal.get("include_git_evidence", goal.get("includeGitEvidence", False))),
                "current_hint_level": 0,
                "status": "LEARNING",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.content_matcher.rebuild_for_goal(goal_version)
        evidence = ExistingSystemEvidenceProvider().collect(student_id, session)
        for item in evidence:
            self.store.create_evidence(item)
        return await self._generate_snapshot(session, evidence, previous_path=None, trigger_type="INITIAL")

    async def change_goal(self, session_id: str, student_id: str, goal: dict) -> dict:
        session = self.store.get_session(session_id, student_id)
        if not session:
            raise KeyError("SESSION_NOT_FOUND")
        parsed_goal = await self.goal_orchestrator.parse_goal(goal)
        normalized_goal = dict(parsed_goal.get("normalized_goal") or goal)
        goal_version_id = f"goal-{uuid4().hex[:12]}"
        self.store.create_goal_version({
            "goal_version_id": goal_version_id,
            "session_id": session_id,
            "student_id": student_id,
            "raw_goal_text": normalized_goal.get("raw_goal_text") or normalized_goal.get("goal_text") or normalized_goal.get("course_name") or "",
            "course_id": normalized_goal.get("course_id", ""),
            "course_name": normalized_goal.get("course_name") or normalized_goal.get("course", ""),
            "deadline": normalized_goal.get("deadline"),
            "weekly_minutes": normalized_goal.get("weekly_minutes", 180),
            "self_reported_difficulty": normalized_goal.get("self_reported_difficulty", ""),
            "reuse_existing_evidence": normalized_goal.get("reuse_existing_evidence", True),
            "parsed_success_criteria": {"knowledge_points": parsed_goal.get("knowledge_points", []), "provider": parsed_goal.get("provider"), "status": parsed_goal.get("status"), "error": parsed_goal.get("error")},
            "created_at": datetime.now(timezone.utc),
        })
        session = self.store.update_session(session_id, student_id, {"goal": normalized_goal, "goal_parse": parsed_goal, "goal_version_id": goal_version_id, "current_goal_version": goal_version_id, "current_knowledge_points": parsed_goal.get("knowledge_points", [])})
        self.content_matcher.rebuild_for_goal(self.store.get_goal_version(goal_version_id, student_id))
        target_ids = {str(item.get("id")) for item in (parsed_goal.get("knowledge_points") or []) if item.get("id")}
        evidence = [
            EvidenceRecord.model_validate({key: value for key, value in item.items() if key != "id"})
            for item in self.store.list_evidence(student_id)
            if target_ids.intersection(set(item.get("knowledge_point_ids") or []))
        ] if normalized_goal.get("reuse_existing_evidence", True) else []
        return await self._generate_snapshot(session, evidence, previous_path=None, trigger_type="GOAL_CHANGED")

    async def _generate_snapshot(
        self,
        session: dict,
        evidence: list[EvidenceRecord],
        previous_path: PathVersion | None,
        trigger_type: str,
        failure_count: int = 0,
    ) -> dict:
        student_id = str(session["student_id"])
        session_id = str(session["id"])
        goal = dict(session.get("goal") or {})
        knowledge_points = [str(item.get("id")) for item in session.get("current_knowledge_points", []) if item.get("id")]
        knowledge_points = knowledge_points or ["course_core_concept"]
        rag_results = []
        point_meta = {str(item.get("id")): item for item in session.get("current_knowledge_points", [])}
        for point_id in knowledge_points:
            rag = await self.retriever.retrieve(KnowledgeRetrievalRequest(knowledge_point_id=point_id, query=str(point_meta.get(point_id, {}).get("search_query") or point_id)))
            rag_results.append(rag)
        rag_chunks = [chunk for result in rag_results for chunk in result.chunks]
        retrieved_content = {}
        for point_id in knowledge_points:
            associations = self.store.list_content_associations(student_id, session.get("current_goal_version"))
            related = [item for item in associations if point_id in (item.get("knowledge_point_ids") or [])]
            retrieved_content[point_id] = related + [{"chunk_id": chunk.chunk_id, "title": chunk.title, "content": chunk.content, "source_name": chunk.source_name, "source_type": "RAG_GENERATED"} for chunk in rag_chunks]
        assessments = self.rule_engine.assess(evidence, knowledge_points, session["include_git_evidence"])
        path = self.planner.plan(assessments, goal, previous_path, failure_count=failure_count, trigger_type=trigger_type, knowledge_point_meta=point_meta, retrieved_content=retrieved_content)
        stored_path = self.store.create_path(path, student_id, session_id=session_id)
        assessments_models = []
        for point_id in knowledge_points:
            assessment_payload = assessments[point_id]
            assessments_models.append(KnowledgeAssessment(knowledge_point_id=point_id, mastery_score=assessment_payload["mastery_score"], practice_score=assessment_payload["practice_score"], state=assessment_payload["state"], confidence=assessment_payload["confidence"], reason_codes=assessment_payload["reason_codes"], evidence_refs=assessment_payload.get("evidence_refs", []), independent_retest_passed=assessment_payload.get("independent_retest_passed", False), independent_retest_coverage=set(assessment_payload.get("independent_retest_coverage", [])), highest_hint_level=assessment_payload.get("highest_hint_level", 0)))
        explanation = await self.explainer.explain(
            {"knowledge_point_ids": knowledge_points},
            [{"evidenceId": item.evidence_id, "fact": item.summary} for item in evidence],
            [{"chunkId": chunk.chunk_id, "title": chunk.title} for chunk in rag_chunks],
        )
        snapshot = DiagnosisSnapshot(
            snapshot_id=f"snapshot-{uuid4().hex[:12]}",
            session_id=session_id,
            student_id=student_id,
            version=len(self.store.list_snapshots(student_id, session_id)) + 1,
            path_version=path.path_version,
            trigger_type=trigger_type,
            include_git_evidence=session["include_git_evidence"],
            evidence_refs=[item.evidence_id for item in evidence],
            assessments=assessments_models,
            explanation=explanation.model_dump(mode="json"),
            rag_references=[chunk.__dict__ for chunk in rag_chunks],
        )
        stored_snapshot = self.store.create_snapshot(snapshot)
        return {"session": session, "snapshot": stored_snapshot, "path": stored_path}

    async def refresh_session(self, session_id: str, student_id: str, trigger: dict) -> dict:
        session = self.store.get_session(session_id, student_id)
        if not session:
            raise KeyError("SESSION_NOT_FOUND")
        paths = self.store.list_paths(student_id, session_id)
        snapshots = self.store.list_snapshots(student_id, session_id)
        old_path = paths[-1] if paths else None
        if trigger.get("sandbox_status") == "SANDBOX_ERROR":
            return {"session": session, "snapshot": snapshots[-1], "path": old_path}
        previous_path = None
        if old_path:
            previous_path = PathVersion.model_validate({key: old_path[key] for key in PathVersion.model_fields if key in old_path})
        if str(trigger.get("trigger_type") or "").upper() == "GIT_EVIDENCE_TOGGLE":
            enabled = bool(trigger.get("include_git_evidence", trigger.get("includeGitEvidence", False)))
            return await self.set_git_evidence(session_id, student_id, enabled)
        evidence = self._evidence_for_session(session)
        return await self._generate_snapshot(
            session,
            evidence,
            previous_path=previous_path,
            trigger_type=str(trigger.get("trigger_type") or "MANUAL_REFRESH"),
            failure_count=int(trigger.get("failure_count") or 0),
        )

    def _current_task(self, session_id: str, student_id: str, task_id: str | None) -> dict:
        paths = self.store.list_paths(student_id, session_id)
        if not paths:
            raise KeyError("PATH_NOT_FOUND")
        tasks = list(paths[-1].get("tasks") or [])
        if task_id is None:
            return next((task for task in tasks if task.get("status") != "COMPLETED"), tasks[0] if tasks else None) or (_ for _ in ()).throw(KeyError("PATH_NOT_FOUND"))
        task = next((item for item in tasks if item.get("task_id") == task_id), None)
        if task is None:
            raise KeyError("TASK_NOT_IN_CURRENT_PATH")
        return task

    def _evidence_for_session(self, session: dict) -> list[EvidenceRecord]:
        point_ids = {str(item.get("id")) for item in session.get("current_knowledge_points", []) if item.get("id")}
        include_git = bool(session.get("include_git_evidence"))
        records = []
        for item in self.store.list_evidence(str(session["student_id"])):
            if item.get("source_type") == "GIT" and not include_git:
                continue
            if point_ids and not point_ids.intersection(set(item.get("knowledge_point_ids") or [])):
                continue
            records.append(EvidenceRecord.model_validate({key: value for key, value in item.items() if key != "id"}))
        return records

    async def request_hint(
        self,
        session_id: str,
        student_id: str,
        task_id: str | int | None = None,
        requested_level: int = 1,
        assessment_mode: bool = False,
        attempt: dict | None = None,
    ) -> dict:
        session = self.store.get_session(session_id, student_id)
        if not session:
            raise KeyError("SESSION_NOT_FOUND")
        # Preserve the old direct-call shape while all API calls now supply task_id.
        if isinstance(task_id, int):
            requested_level, task_id = task_id, None
        task = self._current_task(session_id, student_id, task_id)
        is_retest = task.get("task_type") == "INDEPENDENT_RETEST" or bool(assessment_mode)
        hint_levels = dict(session.get("task_hint_levels") or {})
        current = int(hint_levels.get(task["task_id"], 0))
        allowed_max = min(max(task.get("allowed_hint_levels") or [1]), 1 if is_retest else 5)
        approved = min(max(current + 1, 1), allowed_max, int(requested_level))
        hint_levels[task["task_id"]] = approved
        self.store.update_session(session_id, student_id, {"current_hint_level": approved, "task_hint_levels": hint_levels})
        generated = await self.hint_service.generate(task, approved, attempt=attempt)
        return {
            "task_id": task["task_id"],
            "requested_level": int(requested_level),
            "approved_level": approved,
            "assessment_mode": is_retest,
            "reference_answer_allowed": bool(approved == 5 and not is_retest),
            **generated,
        }

    async def submit_task(
        self,
        session_id: str,
        student_id: str,
        task_id: str,
        code: str,
        answer: str = "",
        hint_level: int = 0,
        assessment_mode: bool = False,
        language: str = "python",
    ) -> dict:
        session = self.store.get_session(session_id, student_id)
        if not session:
            raise KeyError("SESSION_NOT_FOUND")
        task_payload = self._current_task(session_id, student_id, task_id)
        if task_payload.get("task_type") in {"KNOWLEDGE_REVIEW", "GUIDED_PRACTICE"}:
            return await self._submit_non_coding_task(session, task_payload, answer, hint_level, assessment_mode)
        test_cases = list((task_payload.get("content_payload") or {}).get("test_cases") or [])
        if not test_cases:
            test_cases = [{"input": ["normal"], "expected": "normal"}]
        raw = self.code_sandbox.run(code, language, test_cases)
        status = "PASSED" if raw.get("total") and raw.get("passed") == raw.get("total") else "TEST_FAILED"
        if raw.get("error"):
            status = "SECURITY_VIOLATION" if "涓嶅厑璁" in str(raw["error"]) else "RUNTIME_ERROR"
        normalized = self.sandbox_adapter.normalize({
            "status": status,
            "language": language,
            "testSummary": {
                "total": int(raw.get("total") or 0),
                "passed": int(raw.get("passed") or 0),
                "failed": max(0, int(raw.get("total") or 0) - int(raw.get("passed") or 0)),
            },
            "testCases": list(raw.get("results") or []),
            "knowledgePointIds": list(task_payload.get("knowledge_point_ids") or []),
            "stderr": str(raw.get("error") or ""),
        })
        evidence = SandboxEvidenceProvider().from_execution(student_id, normalized.model_dump(mode="json"))[0]
        evidence.result["task_id"] = task_id
        evidence.result["task_type"] = task_payload.get("task_type")
        evidence.result["hint_level"] = int(hint_level)
        evidence.result["assessment_mode"] = bool(assessment_mode)
        evidence.result["test_summary"] = dict(normalized.test_summary)
        if task_payload.get("task_type") == "INDEPENDENT_RETEST":
            evidence.result["coverage"] = self._coverage_from_test_cases(test_cases)
        stored_evidence = self.store.create_evidence(evidence)
        failures = [
            item for item in self.store.list_evidence(student_id)
            if item.get("source_type") == "SANDBOX"
            and item.get("result", {}).get("task_id") == task_id
            and item.get("result", {}).get("status") == "TEST_FAILED"
        ]
        refreshed = await self.refresh_session(session_id, student_id, {
            "trigger_type": "TASK_SUBMISSION",
            "sandbox_status": normalized.status,
            "failure_count": len(failures),
        })
        return {
            "task_id": task_id,
            "status": "RECORDED",
            "execution_id": normalized.execution_id,
            "execution": normalized.model_dump(mode="json"),
            "evidence_id": stored_evidence["evidence_id"],
            "snapshot": refreshed["snapshot"],
            "path": refreshed["path"],
        }

    @staticmethod
    def _coverage_from_test_cases(test_cases: list[dict]) -> list[str]:
        """Normalize task case labels into the three independent-retest scenarios."""
        coverage: list[str] = []
        for index, case in enumerate(test_cases):
            text = " ".join(str(case.get(key, "")) for key in ("coverage", "scenario", "category", "name", "input")).upper()
            if any(token in text for token in ("EXCEPTION", "EMPTY", "NULL", "ERROR")):
                label = "EXCEPTION"
            elif "BOUNDARY" in text:
                label = "BOUNDARY"
            elif "NORMAL" in text or "TYPICAL" in text:
                label = "NORMAL"
            else:
                label = ("NORMAL", "BOUNDARY", "EXCEPTION")[min(index, 2)]
            if label not in coverage:
                coverage.append(label)
        return coverage

    def preview_task_execution(
        self,
        session_id: str,
        student_id: str,
        task_id: str,
        code: str,
        language: str = "python",
    ) -> dict:
        session = self.store.get_session(session_id, student_id)
        if not session:
            raise KeyError("SESSION_NOT_FOUND")
        task_payload = self._current_task(session_id, student_id, task_id)
        if task_payload.get("task_type") not in {"CODING_PRACTICE", "INDEPENDENT_RETEST"}:
            raise KeyError("TASK_NOT_CODING")
        test_cases = list((task_payload.get("content_payload") or {}).get("test_cases") or [])
        if not test_cases:
            test_cases = [{"input": ["normal"], "expected": "normal"}]
        raw = self.code_sandbox.run(code, language, test_cases)
        status = "PASSED" if raw.get("total") and raw.get("passed") == raw.get("total") else "TEST_FAILED"
        if raw.get("error"):
            status = "SECURITY_VIOLATION" if "不允许" in str(raw["error"]) else "RUNTIME_ERROR"
        normalized = self.sandbox_adapter.normalize({
            "status": status,
            "language": language,
            "testSummary": {
                "total": int(raw.get("total") or 0),
                "passed": int(raw.get("passed") or 0),
                "failed": max(0, int(raw.get("total") or 0) - int(raw.get("passed") or 0)),
            },
            "testCases": list(raw.get("results") or []),
            "knowledgePointIds": list(task_payload.get("knowledge_point_ids") or []),
            "stderr": str(raw.get("error") or ""),
        })
        return normalized.model_dump(mode="json")

    async def _submit_non_coding_task(self, session: dict, task: dict, answer: str, hint_level: int, assessment_mode: bool) -> dict:
        text = str(answer or "").strip()
        criteria = list((task.get("content_payload") or {}).get("success_criteria") or [])
        completion = min(1.0, len(text) / 80.0) if text else 0.0
        keyword_hits = sum(1 for item in criteria if any(token in text for token in str(item).replace("，", " ").split() if len(token) >= 2))
        ai_result = await self.answer_evaluator.evaluate(task, text) if text else {"score": None, "status": "DEGRADED", "provider": "deterministic", "feedback": "", "criteria": []}
        rule_score = round(min(100.0, completion * 70 + min(30, keyword_hits * 15)), 2)
        score = float(ai_result.get("score")) if isinstance(ai_result.get("score"), (int, float)) else rule_score
        source_ref = f"learning-diagnosis:{session['id']}:{task['task_id']}"
        evidence = EvidenceRecord(
            evidence_id=f"answer-{uuid4().hex[:12]}", student_id=str(session["student_id"]), source_type="ASSIGNMENT",
            source_ref=source_ref, knowledge_point_ids=list(task.get("knowledge_point_ids") or []),
            result={"status": "COMPLETED" if text else "FAILED", "score": score, "completion": completion, "task_id": task["task_id"], "task_type": task["task_type"], "hint_level": int(hint_level), "assessment_mode": bool(assessment_mode), "answer_length": len(text), "evaluation_status": ai_result.get("status"), "evaluation_provider": ai_result.get("provider"), "evaluation_feedback": ai_result.get("feedback"), "evaluation_error": ai_result.get("error")},
            observed_at=datetime.now(timezone.utc), provenance=Provenance(source="learning_diagnosis_answer", reliability=.75, source_ref=source_ref),
            summary=f"学生完成了 {task.get('title') or task['task_id']} 的文本作答，系统按完成度和目标要点形成规则证据。",
        )
        stored = self.store.create_evidence(evidence)
        self._mark_task_status(session, task["task_id"], "COMPLETED" if text else "IN_PROGRESS")
        refreshed = await self.refresh_session(str(session["id"]), str(session["student_id"]), {"trigger_type": "TASK_SUBMISSION"})
        return {"task_id": task["task_id"], "status": "RECORDED", "execution_id": None, "execution": None, "evidence_id": stored["evidence_id"], "snapshot": refreshed["snapshot"], "path": refreshed["path"]}

    def _mark_task_status(self, session: dict, task_id: str, status: str) -> None:
        paths = self.store.list_paths(str(session["student_id"]), str(session["id"]))
        if not paths:
            return
        latest = dict(paths[-1])
        tasks = [dict(item) for item in latest.get("tasks") or []]
        now = datetime.now(timezone.utc).isoformat()
        for item in tasks:
            if item.get("task_id") == task_id:
                item["status"] = status
                if status == "COMPLETED":
                    item["completed_at"] = now
                elif not item.get("started_at"):
                    item["started_at"] = now
        latest["tasks"] = tasks
        self.store.update_path(str(latest.get("id") or latest.get("path_id")), str(session["student_id"]), {"tasks": tasks})

    async def set_git_evidence(self, session_id: str, student_id: str, enabled: bool) -> dict:
        session = self.store.get_session(session_id, student_id)
        if not session:
            raise KeyError("SESSION_NOT_FOUND")
        session = self.store.update_session(session_id, student_id, {"include_git_evidence": bool(enabled)})
        if enabled:
            result = self.git_practice_service.collect(student_id, session)
            for evidence in result.get("evidence") or []:
                self.store.create_evidence(evidence)
        paths = self.store.list_paths(student_id, session_id)
        previous = PathVersion.model_validate({key: paths[-1][key] for key in PathVersion.model_fields if key in paths[-1]}) if paths else None
        return await self._generate_snapshot(session, self._evidence_for_session(session), previous, "GIT_EVIDENCE_ENABLED" if enabled else "GIT_EVIDENCE_DISABLED")
