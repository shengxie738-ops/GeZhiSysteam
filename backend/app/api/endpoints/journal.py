from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.miniprogram_response import api_response, page_items
from app.repositories.json_store import JsonStore, make_record_key
from app.utils.datetime import utc_now_iso


router = APIRouter()


class JournalEventPayload(BaseModel):
    type: str
    title: str
    summary: str = ""
    relatedIds: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    scoreDelta: int = 0
    userId: str = "guest_user"


@router.post("/journal/events")
async def create_journal_event(payload: JournalEventPayload, db: Session = Depends(get_db)):
    event_id = make_record_key("evt")
    event = {
        "id": event_id,
        "type": payload.type,
        "title": payload.title,
        "summary": payload.summary,
        "relatedIds": payload.relatedIds,
        "tags": payload.tags,
        "scoreDelta": payload.scoreDelta,
        "createdAt": utc_now_iso(),
    }
    stored = JsonStore(db).upsert(
        "journal",
        "event",
        event_id,
        event,
        owner_id=payload.userId,
        status=payload.type,
    )
    return api_response(
        {
            "id": stored["id"],
            "type": stored["type"],
            "title": stored["title"],
            "createdAt": stored["createdAt"],
        }
    )


@router.get("/journal/events")
async def list_journal_events(
    user_id: str = "guest_user",
    cursor: str = "",
    limit: int = 20,
    type: str = "",
    db: Session = Depends(get_db),
):
    events = JsonStore(db).list_payloads("journal", "event", owner_id=user_id)
    if type:
        events = [event for event in events if event.get("type") == type]
    return api_response(page_items(events, cursor=cursor or None, limit=limit))


@router.get("/journal/events/day")
async def get_journal_events_by_day(
    date: str,
    user_id: str = "guest_user",
    cursor: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
):
    events = [
        event
        for event in JsonStore(db).list_payloads("journal", "event", owner_id=user_id)
        if str(event.get("createdAt", "")).startswith(date)
    ]
    return api_response({"date": date, **page_items(events, cursor=cursor or None, limit=limit)})
