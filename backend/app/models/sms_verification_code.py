from sqlalchemy import Column, DateTime, Integer, String, text

from app.core.database import Base


class SmsVerificationCode(Base):
    __tablename__ = "sms_verification_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(32), nullable=False, index=True)
    purpose = Column(String(32), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False)
    sent_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
