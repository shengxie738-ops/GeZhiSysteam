from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .constants import KNOWLEDGE_STATES, SANDBOX_STATUSES, SOURCE_TYPES, TASK_TYPES


PATH_TASK_SOURCE_TYPES = {
    "EXISTING_EXAM",
    "EXISTING_WRONG_QUESTION",
    "EXISTING_COURSEWARE",
    "EXISTING_HOMEWORK",
    "EXISTING_RANKED",
    "EXISTING_SANDBOX",
    "AI_GENERATED",
    "RAG_GENERATED",
}
PATH_TASK_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "LOCKED", "SKIPPED"}
ACTIVITY_STATUSES = {"STARTED", "SUBMITTED", "COMPLETED", "FAILED", "CANCELLED"}
ACTIVITY_PROCESSING_STATUSES = {"PENDING", "PROCESSING", "PROCESSED", "FAILED", "RETRY_PENDING"}


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(StrictContract):
    source: str = Field(min_length=1)
    reliability: float = Field(default=0.8, ge=0, le=1)
    captured_at: datetime | None = None
    source_ref: str | None = None


class EvidenceRecord(StrictContract):
    evidence_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    source_type: Literal["ASSIGNMENT", "EXAM_WRONG", "RANKED_RESULT", "SANDBOX", "INDEPENDENT_RETEST", "GIT"]
    source_ref: str | None = None
    knowledge_point_ids: list[str] = Field(min_length=1)
    result: dict[str, Any]
    observed_at: datetime
    provenance: Provenance
    summary: str = ""
    include_git_evidence: bool = False

    @model_validator(mode="after")
    def validate_git_scope(self) -> "EvidenceRecord":
        if self.source_type == "GIT" and not self.include_git_evidence:
            raise ValueError("Git evidence requires include_git_evidence=true")
        return self


class KnowledgeAssessment(StrictContract):
    knowledge_point_id: str = Field(min_length=1)
    mastery_score: float | None = Field(default=None, ge=0, le=100)
    practice_score: float | None = Field(default=None, ge=0, le=100)
    state: str
    confidence: float = Field(default=0, ge=0, le=1)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    independent_retest_passed: bool = False
    independent_retest_coverage: set[str] = Field(default_factory=set)
    highest_hint_level: int = Field(default=0, ge=0, le=5)

    @model_validator(mode="after")
    def validate_state_and_scores(self) -> "KnowledgeAssessment":
        if self.state not in KNOWLEDGE_STATES:
            raise ValueError(f"unsupported knowledge state: {self.state}")
        if self.practice_score is not None and self.state == "insufficient_data":
            raise ValueError("insufficient data cannot have a practice score")
        if self.state == "mastered":
            required = {"NORMAL", "BOUNDARY", "EXCEPTION"}
            if not self.independent_retest_passed or not required.issubset(self.independent_retest_coverage):
                raise ValueError("mastered requires multi-scenario independent retest")
            if self.highest_hint_level > 1:
                raise ValueError("mastered cannot use Level 2-5 hints")
        return self


class DiagnosisSnapshot(StrictContract):
    snapshot_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    path_version: int = Field(ge=1)
    trigger_type: str = Field(min_length=1)
    include_git_evidence: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    assessments: list[KnowledgeAssessment] = Field(default_factory=list)
    explanation: dict[str, Any] = Field(default_factory=dict)
    rag_references: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "GENERATED"
    review: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_git_scores(self) -> "DiagnosisSnapshot":
        if not self.include_git_evidence and any(item.practice_score is not None for item in self.assessments):
            raise ValueError("practice score must be null when Git evidence is disabled")
        return self


class PathTask(StrictContract):
    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    knowledge_point_ids: list[str] = Field(min_length=1)
    task_type: Literal["KNOWLEDGE_REVIEW", "GUIDED_PRACTICE", "CODING_PRACTICE", "INDEPENDENT_RETEST"]
    difficulty: int = Field(ge=1, le=5)
    estimated_minutes: int = Field(ge=1)
    parent_task_id: str | None = None
    return_task_id: str | None = None
    allowed_hint_levels: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    learning_objective: str = ""
    why_this_task: str = ""
    source_type: str = ""
    source_ref: str | None = None
    content_payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=100)
    prerequisite_task_ids: list[str] = Field(default_factory=list)
    status: str = "PENDING"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    generation_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source_hints_and_status(self) -> "PathTask":
        if self.source_type and self.source_type not in PATH_TASK_SOURCE_TYPES:
            raise ValueError(f"unsupported path task source type: {self.source_type}")
        if not self.allowed_hint_levels or any(level < 1 or level > 5 for level in self.allowed_hint_levels):
            raise ValueError("allowed hint levels must be within Level 1-5")
        if len(set(self.allowed_hint_levels)) != len(self.allowed_hint_levels):
            raise ValueError("allowed hint levels cannot contain duplicates")
        if self.status not in PATH_TASK_STATUSES:
            raise ValueError(f"unsupported path task status: {self.status}")
        return self


class GoalVersion(StrictContract):
    goal_version_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    raw_goal_text: str = Field(min_length=1)
    course_id: str = ""
    course_name: str = ""
    deadline: datetime | None = None
    weekly_minutes: int = Field(default=180, ge=1)
    self_reported_difficulty: str = ""
    reuse_existing_evidence: bool = True
    parsed_success_criteria: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class GoalContentAssociation(StrictContract):
    association_id: str = Field(min_length=1)
    goal_version_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    content_id: str = Field(min_length=1)
    source_module: str = Field(min_length=1)
    source_route: str = ""
    knowledge_point_ids: list[str] = Field(min_length=1)
    relevance_score: float = Field(ge=0, le=1)
    relevance_level: str = Field(min_length=1)
    match_method: str = Field(min_length=1)
    match_reason: str = ""
    model_version: str = ""
    content_version: str = ""
    content_snapshot: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    created_at: datetime
    updated_at: datetime


class LearningActivityEvent(StrictContract):
    event_id: str = ""
    student_id: str = Field(min_length=1)
    source_module: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    content_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(min_length=1)
    occurred_at: datetime
    processing_status: str = "PENDING"
    processed_at: datetime | None = None
    failure_reason: str | None = None
    retry_count: int = Field(default=0, ge=0)
    deduplication_key: str = ""

    @model_validator(mode="after")
    def populate_stable_identifiers(self) -> "LearningActivityEvent":
        if self.status not in ACTIVITY_STATUSES:
            raise ValueError(f"unsupported activity status: {self.status}")
        if self.processing_status not in ACTIVITY_PROCESSING_STATUSES:
            raise ValueError(f"unsupported activity processing status: {self.processing_status}")
        identity_payload = {
            "student_id": self.student_id,
            "source_module": self.source_module,
            "content_type": self.content_type,
            "content_id": self.content_id,
            "attempt_id": self.attempt_id,
        }
        encoded = json.dumps(identity_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        if not self.deduplication_key:
            self.deduplication_key = f"learning-activity:{digest}"
        if not self.event_id:
            self.event_id = f"activity-{digest[:24]}"
        return self


class EvidenceProcessingReceipt(StrictContract):
    receipt_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    goal_version_id: str = Field(min_length=1)
    association_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    path_version: int = Field(ge=1)
    deduplication_key: str = Field(min_length=1)
    created_at: datetime


class PathVersion(StrictContract):
    path_version: int = Field(ge=1)
    previous_version: int | None = None
    trigger_type: str = Field(min_length=1)
    change_reason_codes: list[str] = Field(default_factory=list)
    tasks: list[PathTask] = Field(default_factory=list)
    added_tasks: list[str] = Field(default_factory=list)
    removed_tasks: list[str] = Field(default_factory=list)
    retained_tasks: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    include_git_evidence: bool = False


class SandboxExecutionResult(StrictContract):
    execution_id: str = Field(min_length=1)
    status: str
    language: str = ""
    exit_code: int | None = None
    compile_result: dict[str, Any] = Field(default_factory=dict)
    test_summary: dict[str, int] = Field(default_factory=dict)
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    resource_usage: dict[str, Any] = Field(default_factory=dict)
    knowledge_point_ids: list[str] = Field(default_factory=list)
    sandbox_policy_version: str = "v1"

    @model_validator(mode="after")
    def validate_status(self) -> "SandboxExecutionResult":
        if self.status not in SANDBOX_STATUSES:
            raise ValueError(f"unsupported sandbox status: {self.status}")
        return self
