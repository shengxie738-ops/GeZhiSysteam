from pydantic import BaseModel, Field, model_validator


class CreateDiagnosisSessionRequest(BaseModel):
    student_id: str
    course: str = ""
    deadline: str | None = None
    weekly_minutes: int = Field(default=180, ge=1)
    self_reported_difficulty: str = ""
    include_git_evidence: bool = False
    raw_goal_text: str = ""
    goal_text: str = ""
    course_id: str = ""
    course_name: str = ""
    reuse_existing_evidence: bool = True

    @model_validator(mode="after")
    def require_goal_source(self):
        if not any(str(value or "").strip() for value in (self.course, self.raw_goal_text, self.goal_text, self.course_name)):
            raise ValueError("course, raw_goal_text, goal_text or course_name is required")
        if not self.course and self.course_name:
            self.course = self.course_name
        return self


class CreateDiagnosisGoalRequest(BaseModel):
    student_id: str
    raw_goal_text: str = ""
    goal_text: str = ""
    course_id: str = ""
    course_name: str = ""
    deadline: str | None = None
    weekly_minutes: int = Field(default=180, ge=1)
    self_reported_difficulty: str = ""
    reuse_existing_evidence: bool = True


class RefreshDiagnosisRequest(BaseModel):
    trigger: dict = Field(default_factory=dict)


class SubmitTaskRequest(BaseModel):
    student_id: str
    session_id: str = ""
    code: str = ""
    answer: str = ""
    hint_level: int = Field(default=0, ge=0, le=5)
    assessment_mode: bool = False


class RunTaskRequest(BaseModel):
    student_id: str
    session_id: str
    code: str = ""
    language: str = "python"


class HintRequest(BaseModel):
    requested_level: int = Field(ge=1, le=5)
    assessment_mode: bool = False
    attempt: dict = Field(default_factory=dict)


class GitEvidenceToggleRequest(BaseModel):
    student_id: str
    include_git_evidence: bool


class LearningActivityEventRequest(BaseModel):
    student_id: str
    source_module: str
    content_type: str
    content_id: str
    attempt_id: str
    result_payload: dict = Field(default_factory=dict)
    status: str
    occurred_at: str | None = None
