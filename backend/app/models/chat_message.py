from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, text, Index

from app.core.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    agent_mode = Column(String(32), nullable=False, index=True)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    sender_id = Column(String(64), nullable=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (
        Index("ix_chat_messages_user_mode_created", "user_id", "agent_mode", "created_at"),
    )
