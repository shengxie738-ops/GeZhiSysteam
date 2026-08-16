from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, text

from app.core.database import Base


class DomainRecord(Base):
    __tablename__ = "domain_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    module = Column(String(64), index=True, nullable=False)
    record_type = Column(String(64), index=True, nullable=False)
    record_key = Column(String(255), index=True, nullable=False)
    owner_id = Column(String(255), index=True, default="")
    role = Column(String(32), default="")
    status = Column(String(64), default="")
    payload = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
