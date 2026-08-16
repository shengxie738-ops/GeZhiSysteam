from sqlalchemy import Column, String, TIMESTAMP, text
from app.core.database import Base

class UserRagMapping(Base):
    __tablename__ = "user_rag_mappings"

    user_id = Column(String(255), primary_key=True, index=True)
    dataset_id = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
