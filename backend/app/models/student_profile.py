from sqlalchemy import Column, String, Integer, TIMESTAMP, text
from app.core.database import Base

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id = Column(String(255), primary_key=True, index=True)
    knowledge = Column(Integer, default=50)  # 知识基础 (0-100)
    cognitive = Column(String(255), default="渐进理解型")  # 认知风格
    pace = Column(Integer, default=50)  # 学习步调 (0-100)
    error_pattern = Column(String(512), default="易错点：数组越界，指针空悬")  # 易错点偏好
    goal = Column(String(512), default="掌握核心数据结构与算法")  # 学习目标
    background = Column(String(255), default="电子信息与计算机类")  # 专业背景
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
