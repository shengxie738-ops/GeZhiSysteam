from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


IndexStatus = Literal[
    "NOT_INDEXED",
    "INDEXED",
    "EMPTY_TEXT",
    "EXTRACTION_FAILED",
    "PYPDF_UNAVAILABLE",
    "PYTHON_PPTX_UNAVAILABLE",
    "UNSUPPORTED_LEGACY_PPT",
]


class CoursewareResource(BaseModel):
    id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    name: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    extension: Literal[".pdf", ".ppt", ".pptx"]
    size_bytes: int = Field(ge=0)
    frontend_url: str = Field(min_length=1)
    index_status: IndexStatus
    searchable: bool


class CoursewareSummary(BaseModel):
    total: int = Field(ge=0)
    pdf: int = Field(ge=0)
    slides: int = Field(ge=0)
    ppt: int = Field(ge=0)
    pptx: int = Field(ge=0)
    searchable: int = Field(ge=0)


class CoursewareCatalogResult(BaseModel):
    summary: CoursewareSummary
    resources: list[CoursewareResource] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    resource_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    text: str = Field(min_length=1)


class DocumentIndexResult(BaseModel):
    resource_id: str = Field(min_length=1)
    status: IndexStatus
    searchable: bool
    chunks: list[DocumentChunk] = Field(default_factory=list)
    message: str = ""


class CoursewareSearchMatch(BaseModel):
    resource_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    excerpt: str = Field(min_length=1)
    score: float = Field(gt=0)
    course: str = ""
    name: str = ""
    frontend_url: str = ""


class CoursewareSearchResult(BaseModel):
    query: str
    matches: list[CoursewareSearchMatch] = Field(default_factory=list)
    index_results: list[DocumentIndexResult] = Field(default_factory=list)


class LessonPrepSearchRequest(StrictRequestModel):
    query: str = Field(min_length=1, max_length=200)
    resource_ids: list[str] = Field(min_length=1, max_length=10)
    limit: int = Field(default=10, ge=1, le=50)


class LessonPrepSummaryRequest(StrictRequestModel):
    resource_ids: list[str] = Field(min_length=1, max_length=10)
    query: str = Field(default="", max_length=200)


class LessonPlanGenerateRequest(StrictRequestModel):
    topic: str = Field(min_length=1, max_length=200)
    course_name: str = Field(default="", max_length=200)
    audience: str = Field(default="", max_length=200)
    duration_minutes: int = Field(default=45, ge=1, le=600)
    resource_ids: list[str] = Field(min_length=1, max_length=10)
    requirements: str = Field(default="", max_length=4000)


class LessonPrepDraftRequest(StrictRequestModel):
    draft_id: str = Field(default="", max_length=255)
    title: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(default=45, ge=1, le=600)
    resource_ids: list[str] = Field(default_factory=list, max_length=10)
    content: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_resource_ids(self) -> "LessonPrepDraftRequest":
        self.resource_ids = list(dict.fromkeys(self.resource_ids))
        if len(str(self.content)) > 200000:
            raise ValueError("draft content is too large")
        return self


class TeachingStageExport(StrictRequestModel):
    stage: str = Field(min_length=1, max_length=200)
    minutes: int = Field(ge=0, le=600)
    content: str = Field(min_length=1, max_length=4000)


class CitationExport(StrictRequestModel):
    name: str = Field(default="", max_length=200)
    page: int = Field(default=0, ge=0)
    excerpt: str = Field(default="", max_length=4000)


class LessonPlanExportRequest(StrictRequestModel):
    title: str = Field(min_length=1, max_length=200)
    topic: str = Field(default="", max_length=200)
    course_name: str = Field(default="", max_length=200)
    audience: str = Field(default="", max_length=200)
    duration_minutes: int = Field(default=45, ge=1, le=600)
    objectives: list[str] = Field(default_factory=list, max_length=200)
    key_points: list[str] = Field(default_factory=list, max_length=200)
    difficulties: list[str] = Field(default_factory=list, max_length=200)
    questions: list[str] = Field(default_factory=list, max_length=200)
    exercises: list[str] = Field(default_factory=list, max_length=200)
    homework: list[str] = Field(default_factory=list, max_length=200)
    teaching_flow: list[TeachingStageExport] = Field(default_factory=list, max_length=100)
    summary: str = Field(default="", max_length=8000)
    citations: list[CitationExport] = Field(default_factory=list, max_length=50)

    @field_validator(
        "objectives",
        "key_points",
        "difficulties",
        "questions",
        "exercises",
        "homework",
        mode="after",
    )
    @classmethod
    def _drop_blank_items(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class AILessonSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    content: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list)


class AITeachingStage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    stage: str = Field(min_length=1)
    minutes: int = Field(gt=0)
    content: str = Field(min_length=1)


class AILessonPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1)
    objectives: list[str]
    key_points: list[str]
    difficulties: list[str]
    teaching_flow: list[AITeachingStage] = Field(min_length=1)
    questions: list[str]
    exercises: list[str]
    homework: list[str]
