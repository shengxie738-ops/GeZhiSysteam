from sqlalchemy import Column, String, TIMESTAMP, text
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.security import get_password_hash


class UserAccount(Base):
    __tablename__ = "user_accounts"

    username = Column(String(255), primary_key=True, index=True)
    role = Column(String(32), nullable=False, default="student")
    password_hash = Column(String(255), nullable=False, default="")
    phone = Column(String(32), default="")
    real_name = Column(String(100), default="")
    student_id = Column(String(50), default="")
    teacher_id = Column(String(64), default="")
    class_name = Column(String(100), default="")
    avatar_path = Column(String(512), default="")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())


def hash_password(password: str) -> str:
    return get_password_hash(password)
