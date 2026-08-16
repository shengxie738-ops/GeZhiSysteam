import asyncio
import os
import unittest

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints.agents import AgentConfigPayload, get_agents, save_agent_config
from app.models.domain_record import DomainRecord


class AgentsApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_default_agents_include_ranked_coach(self):
        db = self.SessionLocal()
        try:
            response = asyncio.run(get_agents(db))

            ranked = next(agent for agent in response["data"] if agent["id"] == "agent_ranked_coach")
            self.assertEqual(ranked["name"], "排位赛AI教练")
            self.assertEqual(ranked["role"], "排位诊断与冲分策略教练")
            self.assertEqual(ranked["modelCategory"], "text")
            self.assertEqual(ranked["model"], "qwen3.7-plus")
            self.assertTrue(ranked["isActive"])
        finally:
            db.close()

    def test_agent_model_update_persists_to_domain_records(self):
        db = self.SessionLocal()
        try:
            asyncio.run(
                save_agent_config(
                    "agent_ranked_coach",
                    AgentConfigPayload(model="deepseek-v4-pro", prompt="用排位赛视角分析学生失误。"),
                    db,
                )
            )

            response = asyncio.run(get_agents(db))
            ranked = next(agent for agent in response["data"] if agent["id"] == "agent_ranked_coach")
            self.assertEqual(ranked["model"], "deepseek-v4-pro")
            self.assertEqual(ranked["prompt"], "用排位赛视角分析学生失误。")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
