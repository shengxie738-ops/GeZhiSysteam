from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage


VALID_AGENT_MODES = {"tutor", "rag"}


def normalize_agent_mode(agent_mode: str | None) -> str:
    return agent_mode if agent_mode in VALID_AGENT_MODES else "tutor"


def normalize_user_id(user_id: str | None) -> str:
    cleaned = (user_id or "").strip()
    return cleaned or "guest_user"


def build_agent_thread_id(user_id: str | None, agent_mode: str | None) -> str:
    return f"{normalize_user_id(user_id)}:{normalize_agent_mode(agent_mode)}"


def save_chat_message(
    db: Session,
    *,
    user_id: str,
    agent_mode: str,
    role: str,
    content: str,
    sender_id: str | None = None,
) -> ChatMessage:
    record = ChatMessage(
        user_id=normalize_user_id(user_id),
        agent_mode=normalize_agent_mode(agent_mode),
        role=role,
        content=content or "",
        sender_id=sender_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_chat_history(db: Session, *, user_id: str, agent_mode: str, limit: int = 200) -> list[dict]:
    records = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == normalize_user_id(user_id),
            ChatMessage.agent_mode == normalize_agent_mode(agent_mode),
        )
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
    return [serialize_chat_message(record) for record in records]


def serialize_chat_message(record: ChatMessage) -> dict:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "agent_mode": record.agent_mode,
        "role": record.role,
        "content": record.content,
        "sender_id": record.sender_id,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else None,
    }


def delete_chat_message(db: Session, *, user_id: str, message_id: int) -> bool:
    record = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.user_id == normalize_user_id(user_id),
        )
        .first()
    )
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def clear_chat_history(db: Session, *, user_id: str, agent_mode: str) -> int:
    deleted = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == normalize_user_id(user_id),
            ChatMessage.agent_mode == normalize_agent_mode(agent_mode),
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return int(deleted or 0)
