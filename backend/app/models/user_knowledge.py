from sqlalchemy import Column, Index, Integer, String, TIMESTAMP, UniqueConstraint, text

from app.core.database import Base


class UserKnowledgeRepository(Base):
    __tablename__ = "user_knowledge_repositories"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_knowledge_repo_user_name"),
        Index("ix_user_knowledge_repo_user_created", "user_id", "created_at"),
    )


class UserKnowledgeDocument(Base):
    __tablename__ = "user_knowledge_documents"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    repository_id = Column(String(64), nullable=False, index=True)
    dataset_id = Column(String(255), nullable=False, index=True)
    rag_document_id = Column(String(255), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="parsing")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    __table_args__ = (
        Index("ix_user_knowledge_doc_user_repo_created", "user_id", "repository_id", "created_at"),
    )
