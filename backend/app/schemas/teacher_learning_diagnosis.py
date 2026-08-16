from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ReviewStatus = Literal["PENDING", "REVIEWED", "RISK_CONFIRMED", "RISK_DISMISSED", "OBSERVING"]


class ReviewStateRequest(BaseModel):
    status: ReviewStatus = "REVIEWED"
    comment: str = ""
    risk_level: str = ""


class ReviewNoteRequest(BaseModel):
    comment: str = Field(min_length=1)
    note_type: str = "general"


class WatchFlagRequest(BaseModel):
    pinned: bool = True
    reason: str = ""


ReviewActionPayload = ReviewStateRequest


class TeacherReviewState(BaseModel):
    snapshot_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    teacher_id: str = Field(min_length=1)
    status: ReviewStatus = "PENDING"
    comment: str = ""
    risk_level: str = ""
    last_action: str = "NOT_REVIEWED"
    updated_at: datetime | None = None


class TeacherReviewNote(BaseModel):
    note_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    teacher_id: str = Field(min_length=1)
    comment: str = Field(min_length=1)
    note_type: str = "general"
    created_at: datetime | None = None


class TeacherWatchFlag(BaseModel):
    student_id: str = Field(min_length=1)
    teacher_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    pinned: bool = False
    reason: str = ""
    updated_at: datetime | None = None


class TeacherReviewDetail(BaseModel):
    snapshot: dict
    review_state: TeacherReviewState
    notes: list[TeacherReviewNote] = Field(default_factory=list)
    watch_flag: TeacherWatchFlag


class TeacherReviewListItem(BaseModel):
    snapshot: dict
    review_state: TeacherReviewState
    notes_count: int = 0
    watch_flag: TeacherWatchFlag


class TeacherReviewListResponse(BaseModel):
    teacher_id: str = Field(min_length=1)
    reviews: list[TeacherReviewListItem] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
