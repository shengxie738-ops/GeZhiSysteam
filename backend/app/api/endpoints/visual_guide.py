from fastapi import APIRouter
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.services.visual_guide_service import VisualGuideGenerationRequest, VisualGuideService

router = APIRouter()
visual_guide_service = VisualGuideService()


class VisualGuideRequest(BaseModel):
    prompt: str
    guide_type: str = "concept"
    session_id: str | None = None
    style: str | None = None
    context: dict | None = None
    image_model: str | None = None
    text_model: str | None = None
    agent_id: str | None = None
    agent_prompt: str | None = None


@router.post("/visual-guide/generate")
async def generate_visual_guide(payload: VisualGuideRequest):
    request = VisualGuideGenerationRequest(
        prompt=payload.prompt,
        guide_type=payload.guide_type,
        session_id=payload.session_id,
        style=payload.style,
        context=payload.context,
        model=payload.image_model,
        text_model=payload.text_model,
        agent_id=payload.agent_id,
        agent_prompt=payload.agent_prompt,
    )
    return await run_in_threadpool(visual_guide_service.generate, request)
