from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.json_store import JsonStore
from app.services.default_agents import get_default_agents

router = APIRouter()


class AgentConfigPayload(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    avatar: Optional[str] = None
    icon: Optional[str] = None
    colorClass: Optional[str] = None
    isThinking: Optional[bool] = None
    isActive: Optional[bool] = None
    modelCategory: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    avatarShellClass: Optional[str] = None
    iconTextClass: Optional[str] = None


def _clean_payload(payload: AgentConfigPayload) -> dict:
    return {key: value for key, value in payload.model_dump().items() if value is not None}


def _merge_agent_configs(db: Session) -> list[dict]:
    defaults = get_default_agents()
    by_id = {agent["id"]: agent for agent in defaults}
    store = JsonStore(db)
    stored = store.list_payloads("agents", record_type="config")

    for payload in stored:
        agent_id = payload.get("id")
        if not agent_id:
            continue
        if agent_id in by_id:
            by_id[agent_id] = {**by_id[agent_id], **payload}
        else:
            by_id[agent_id] = payload

    ordered = []
    seen = set()
    for agent in defaults:
        agent_id = agent["id"]
        ordered.append(by_id[agent_id])
        seen.add(agent_id)
    for agent_id, agent in by_id.items():
        if agent_id not in seen:
            ordered.append(agent)
    return ordered


@router.get("/agents")
async def get_agents(db: Session = Depends(get_db)):
    return {"status": "success", "data": _merge_agent_configs(db)}


@router.put("/agents/{agent_id}")
async def save_agent_config(agent_id: str, payload: AgentConfigPayload, db: Session = Depends(get_db)):
    store = JsonStore(db)
    current = next((agent for agent in _merge_agent_configs(db) if agent["id"] == agent_id), {"id": agent_id})
    updated = {**current, **_clean_payload(payload), "id": agent_id}
    store.upsert("agents", "config", agent_id, updated, owner_id="system", status="active")
    return {"status": "success", "data": updated}


@router.delete("/agents/{agent_id}")
async def delete_agent_config(agent_id: str, db: Session = Depends(get_db)):
    store = JsonStore(db)
    defaults = {agent["id"] for agent in get_default_agents()}
    if agent_id in defaults:
        current = next((agent for agent in _merge_agent_configs(db) if agent["id"] == agent_id), {"id": agent_id})
        updated = {**current, "id": agent_id, "isActive": False}
        store.upsert("agents", "config", agent_id, updated, owner_id="system", status="disabled")
        return {"status": "success", "data": updated}
    deleted = store.delete("agents", "config", agent_id)
    return {"status": "success", "data": {"id": agent_id, "deleted": deleted}}
