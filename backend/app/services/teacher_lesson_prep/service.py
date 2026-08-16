import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.json_store import JsonStore, make_record_key
from app.schemas.teacher_lesson_prep import (
    AILessonPlanResponse,
    AILessonSummaryResponse,
    LessonPlanExportRequest,
    LessonPlanGenerateRequest,
    LessonPrepDraftRequest,
    LessonPrepSearchRequest,
    LessonPrepSummaryRequest,
)
from app.services.teacher_lesson_prep.ai_client import LessonPrepAIClient
from app.services.teacher_lesson_prep.courseware_catalog import CoursewareCatalog
from app.services.teacher_lesson_prep.docx_exporter import build_docx_filename, build_lesson_plan_docx
from app.services.teacher_lesson_prep.document_retriever import DocumentRetriever


class TeacherLessonPrepService:
    MODULE = "teacher_lesson_prep"
    RECORD_TYPE = "draft"

    def __init__(self, catalog: CoursewareCatalog | None = None, ai_client: LessonPrepAIClient | None = None):
        repository_root = Path(__file__).resolve().parents[4]
        self.catalog = catalog or CoursewareCatalog(repository_root)
        self.retriever = DocumentRetriever(self.catalog)
        self.ai_client = ai_client or LessonPrepAIClient()

    def public_config(self) -> dict[str, Any]:
        return {
            "model": settings.AI_LESSON_PREP_MODEL,
            "ai_ready": bool(settings.AI_LESSON_PREP_API_KEY),
            "max_input_tokens": settings.AI_LESSON_PREP_MAX_INPUT_TOKENS,
            "max_output_tokens": settings.AI_LESSON_PREP_MAX_OUTPUT_TOKENS,
            "supported_search_formats": ["pdf", "pptx"],
        }

    def list_resources(self, *, course: str | None = None, file_type: str | None = None, query: str | None = None) -> dict[str, Any]:
        result = self.catalog.list_resources().model_dump()
        resources = result["resources"]
        normalized_course = str(course or "").strip().casefold()
        normalized_type = str(file_type or "").strip().lower().lstrip(".")
        normalized_query = str(query or "").strip().casefold()
        if normalized_course:
            resources = [item for item in resources if str(item["course"]).casefold() == normalized_course]
        if normalized_type:
            resources = [item for item in resources if str(item["extension"]).lower().lstrip(".") == normalized_type]
        if normalized_query:
            resources = [item for item in resources if normalized_query in f"{item['course']} {item['name']}".casefold()]
        result["resources"] = resources
        result["filtered_total"] = len(resources)
        return result

    def search(self, payload: LessonPrepSearchRequest) -> dict[str, Any]:
        try:
            return self.retriever.search(payload.query, resource_ids=payload.resource_ids, limit=payload.limit).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    async def summarize(self, payload: LessonPrepSummaryRequest) -> dict[str, Any]:
        query = payload.query.strip() or "课程核心概念 重点 难点"
        try:
            evidence = (await asyncio.to_thread(
                self.retriever.search,
                query,
                resource_ids=payload.resource_ids,
                limit=8,
                fallback_to_chunks=True,
            )).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not evidence["matches"]:
            raise HTTPException(status_code=422, detail="selected courseware has no searchable text")
        result = await self._complete_ai(
            system_prompt="你是教师备课助手。只依据课件证据总结，不虚构页码或内容，只返回 JSON。",
            user_prompt=json.dumps({
                "task": "总结课件内容",
                "query": payload.query,
                "required_schema": {"content": "string", "key_points": ["string"]},
                "evidence": evidence["matches"],
            }, ensure_ascii=False),
        )
        try:
            validated = self._validate_summary_result(result)
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="AI summary response is invalid") from exc
        return {
            **validated,
            "citations": evidence["matches"],
            "model": settings.AI_LESSON_PREP_MODEL,
        }

    async def generate_plan(self, payload: LessonPlanGenerateRequest) -> dict[str, Any]:
        try:
            evidence = (await asyncio.to_thread(
                self.retriever.search,
                payload.topic,
                resource_ids=payload.resource_ids,
                limit=10,
                fallback_to_chunks=True,
            )).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not evidence["matches"]:
            raise HTTPException(status_code=422, detail="selected courseware has no searchable text")
        required_schema = {
            "title": "string",
            "objectives": ["string"],
            "key_points": ["string"],
            "difficulties": ["string"],
            "teaching_flow": [{"stage": "string", "minutes": 5, "content": "string"}],
            "questions": ["string"],
            "exercises": ["string"],
            "homework": ["string"],
        }
        system_prompt = (
            "你是高校教师备课助手。严格依据给定课件证据生成可编辑教案。"
            "只返回 JSON；教学流程总时长必须等于指定课时；不得捏造引用。"
        )
        generation_request = {
            "task": "生成教案",
            "topic": payload.topic,
            "course_name": payload.course_name,
            "audience": payload.audience,
            "duration_minutes": payload.duration_minutes,
            "requirements": payload.requirements,
            "required_schema": required_schema,
            "evidence": evidence["matches"],
        }
        result = await self._complete_ai(
            system_prompt=system_prompt,
            user_prompt=json.dumps(generation_request, ensure_ascii=False),
            temperature=0.3,
        )
        try:
            validated = self._validate_plan_result(result, payload.duration_minutes, payload.topic)
        except ValueError as first_error:
            repaired = await self._complete_ai(
                system_prompt=(
                    "你是教案 JSON 校验修复器。根据校验错误修正给定 JSON。"
                    "只返回修正后的完整 JSON，不添加解释，不改变课件事实或目标课时。"
                ),
                user_prompt=json.dumps({
                    "task": "修复教案 JSON",
                    "validation_error": str(first_error),
                    "duration_minutes": payload.duration_minutes,
                    "required_schema": required_schema,
                    "invalid_response": result,
                }, ensure_ascii=False),
                temperature=0.1,
            )
            try:
                validated = self._validate_plan_result(repaired, payload.duration_minutes, payload.topic)
            except ValueError as second_error:
                raise HTTPException(status_code=502, detail="AI lesson plan response is invalid") from second_error
        return {
            **validated,
            "duration_minutes": payload.duration_minutes,
            "citations": evidence["matches"],
            "model": settings.AI_LESSON_PREP_MODEL,
        }

    def export_docx(self, payload: LessonPlanExportRequest) -> tuple[bytes, str]:
        """把导出请求组装为教案字典并渲染为 docx，返回 (文档字节流, 下载文件名)。"""
        plan = {
            "title": payload.title,
            "topic": payload.topic,
            "course_name": payload.course_name,
            "audience": payload.audience,
            "duration_minutes": payload.duration_minutes,
            "objectives": list(payload.objectives),
            "key_points": list(payload.key_points),
            "difficulties": list(payload.difficulties),
            "questions": list(payload.questions),
            "exercises": list(payload.exercises),
            "homework": list(payload.homework),
            "teaching_flow": [stage.model_dump() for stage in payload.teaching_flow],
            "summary": payload.summary,
            "citations": [citation.model_dump() for citation in payload.citations],
        }
        try:
            document_bytes = build_lesson_plan_docx(plan)
            filename = build_docx_filename(payload.title)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail="教案文档生成失败") from exc
        return document_bytes, filename

    def save_draft(self, db: Session, teacher_id: str, payload: LessonPrepDraftRequest) -> dict[str, Any]:
        store = JsonStore(db)
        draft_id = payload.draft_id or make_record_key("lesson-draft")
        existing = store.get_payload(self.MODULE, self.RECORD_TYPE, draft_id, owner_id=teacher_id)
        if payload.draft_id and existing is None:
            raise HTTPException(status_code=404, detail="lesson prep draft not found")
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "draft_id": draft_id,
            "title": payload.title,
            "topic": payload.topic,
            "duration_minutes": payload.duration_minutes,
            "resource_ids": payload.resource_ids,
            "content": payload.content,
            "status": "DRAFT",
            "created_at": (existing or {}).get("created_at") or now,
            "updated_at": now,
        }
        saved = store.upsert(self.MODULE, self.RECORD_TYPE, draft_id, data, owner_id=teacher_id, role="teacher", status="DRAFT")
        saved["draft_id"] = draft_id
        saved.pop("id", None)
        return saved

    def list_drafts(self, db: Session, teacher_id: str) -> dict[str, Any]:
        drafts = JsonStore(db).list_payloads(self.MODULE, self.RECORD_TYPE, owner_id=teacher_id)
        normalized = [self._draft_payload(item) for item in drafts]
        return {"drafts": normalized, "total": len(normalized)}

    def get_draft(self, db: Session, teacher_id: str, draft_id: str) -> dict[str, Any]:
        payload = JsonStore(db).get_payload(self.MODULE, self.RECORD_TYPE, draft_id, owner_id=teacher_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="lesson prep draft not found")
        return self._draft_payload(payload)

    @staticmethod
    def _draft_payload(payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload)
        result["draft_id"] = str(result.get("draft_id") or result.get("id") or "")
        result.pop("id", None)
        return result

    async def _complete_ai(self, **kwargs: Any) -> dict[str, Any]:
        try:
            return await self.ai_client.complete(**kwargs)
        except RuntimeError as exc:
            if "api key is not configured" in str(exc).casefold():
                raise HTTPException(
                    status_code=503,
                    detail="AI备课服务未配置，请在 backend/.env 中设置 AI_LESSON_PREP_API_KEY",
                ) from exc
            raise HTTPException(
                status_code=502,
                detail="AI备课服务返回了无效响应",
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail="AI备课服务暂时不可用，请检查网络或服务配置",
            ) from exc

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []

    def _validate_summary_result(self, result: dict[str, Any]) -> dict[str, Any]:
        validated = AILessonSummaryResponse.model_validate(result)
        return validated.model_dump()

    def _validate_plan_result(self, result: dict[str, Any], duration_minutes: int, topic: str) -> dict[str, Any]:
        validated = AILessonPlanResponse.model_validate(result)
        normalized = validated.model_dump()
        total_minutes = sum(item["minutes"] for item in normalized["teaching_flow"])
        if total_minutes != duration_minutes:
            raise ValueError("AI lesson plan duration does not match requested duration")
        return normalized


lesson_prep_service = TeacherLessonPrepService()
