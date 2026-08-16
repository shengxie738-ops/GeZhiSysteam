from sqlalchemy import Column, Integer, String, TIMESTAMP, Text, text
from sqlalchemy.sql import func

from app.core.database import Base


class GiteaAccountBinding(Base):
    __tablename__ = "gitea_account_bindings"

    campus_user_id = Column(String(255), primary_key=True, index=True)
    role = Column(String(32), nullable=False, default="student")
    student_id = Column(String(50), nullable=False, default="")
    teacher_id = Column(String(64), nullable=False, default="")
    class_name = Column(String(100), nullable=False, default="")
    gitea_user_id = Column(Integer, nullable=True, index=True)
    gitea_username = Column(String(255), nullable=False, unique=True, index=True)
    gitea_email = Column(String(255), nullable=False, unique=True, index=True)
    token_name = Column(String(255), nullable=False, default="campus-learning-system")
    token_last_four = Column(String(16), nullable=False, default="")
    token_created_at = Column(TIMESTAMP, nullable=True)
    sync_status = Column(String(32), nullable=False, default="mock")
    sync_error = Column(Text, nullable=False, default="")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())
