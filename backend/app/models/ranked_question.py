"""
ranked_question.py
排位竞赛题目 ORM 模型 — ranked_questions 表
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, text
from sqlalchemy.sql import func

from app.core.database import Base


class RankedQuestion(Base):
    """排位竞赛编程题目，按难度/段位进行对战匹配。"""

    __tablename__ = "ranked_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 业务唯一标识，格式: q001 ~ q030
    question_id = Column(String(64), unique=True, index=True, nullable=False)

    # 题目基本信息
    title = Column(String(255), nullable=False)
    difficulty = Column(String(16), nullable=False, index=True)  # easy / medium / hard
    min_tier = Column(String(16), nullable=False, index=True)    # bronze / silver / gold / platinum / diamond / king
    category = Column(String(64), nullable=False)                # 课程模块，如 数据结构-图
    knowledge_tags = Column(Text, nullable=False, default="[]")  # JSON 数组

    # 题目内容（Markdown 友好）
    description = Column(Text, nullable=False)
    input_format = Column(Text, nullable=False)
    output_format = Column(Text, nullable=False)
    examples = Column(Text, nullable=False, default="[]")        # JSON 数组 [{input, output, explanation}]
    constraints = Column(Text, nullable=False, default="")
    hint = Column(Text, nullable=False, default="")

    # 积分设置
    score_reward = Column(Integer, nullable=False, default=50)   # 胜利获得积分
    score_penalty = Column(Integer, nullable=False, default=20)  # 失败扣除积分
    time_limit_sec = Column(Integer, nullable=False, default=1800) # 答题时间限制（秒），默认 1800 秒 = 30 分钟

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())
