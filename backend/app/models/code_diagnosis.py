from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, text
from app.core.database import Base

class CodeDiagnosis(Base):
    __tablename__ = "code_diagnoses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), index=True, nullable=False)
    problem_id = Column(String(255), nullable=False)
    problem_title = Column(String(255), nullable=False)
    user_code = Column(Text, nullable=False)
    diagnosis_result = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
