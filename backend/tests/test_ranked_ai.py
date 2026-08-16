import asyncio
import json
import os
import unittest
from unittest.mock import patch

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

from app.api.endpoints.ranked import (
    RankedCoachPayload,
    RankedMistakeAiPayload,
    analyze_ranked_mistake,
    ask_ranked_coach,
    get_ranked_mistakes,
)
from app.models.domain_record import DomainRecord
from app.repositories.json_store import JsonStore


class FakeAiMessage:
    content = json.dumps(
        {
            "diagnosis": "DFS 缺少边界判断，导致访问越界。",
            "concept": "网格 DFS 需要先判断坐标合法性和访问状态。",
            "practice": "连续完成 5 道网格 DFS 递进题。",
            "path": ["复盘模板", "重写边界判断", "限时训练", "排位复测"],
        },
        ensure_ascii=False,
    )


class FakeChatModel:
    def __init__(self):
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return FakeAiMessage()


class RankedAiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_ranked_coach_uses_selected_model_and_prompt(self):
        db = self.SessionLocal()
        model = FakeChatModel()
        try:
            with patch("app.api.endpoints.ranked.build_chat_model", return_value=model) as build_model:
                response = asyncio.run(
                    ask_ranked_coach(
                        RankedCoachPayload(
                            userId="student-1",
                            agentId="agent_ranked_coach",
                            agentName="排位赛AI教练",
                            agentModel="deepseek-v4-pro",
                            agentPrompt="Only give ranked improvement advice.",
                            question="我的失误在哪里？",
                            context={"score": 1980, "streak": 5},
                        ),
                        db,
                    )
                )["data"]

            build_model.assert_called_once()
            self.assertEqual(build_model.call_args.args[0], "deepseek-v4-pro")
            self.assertEqual(response["model"], "deepseek-v4-pro")
            self.assertEqual(response["agentId"], "agent_ranked_coach")
            self.assertIn("Only give ranked improvement advice.", model.prompts[0])
            self.assertIn("我的失误在哪里？", model.prompts[0])
            self.assertIn("1980", model.prompts[0])
        finally:
            db.close()

    def test_ranked_mistake_analysis_persists_ai_analysis(self):
        db = self.SessionLocal()
        model = FakeChatModel()
        try:
            mistake = asyncio.run(get_ranked_mistakes("student-1", db))["data"][0]
            with patch("app.api.endpoints.ranked.build_chat_model", return_value=model) as build_model:
                response = asyncio.run(
                    analyze_ranked_mistake(
                        mistake["id"],
                        RankedMistakeAiPayload(
                            userId="student-1",
                            agentId="agent_ranked_coach",
                            agentName="排位赛AI教练",
                            agentModel="glm-4.6v",
                            agentPrompt="Focus on ranked mistakes.",
                        ),
                        db,
                    )
                )["data"]

            build_model.assert_called_once()
            self.assertEqual(build_model.call_args.args[0], "glm-4.6v")
            self.assertEqual(response["agentId"], "agent_ranked_coach")
            self.assertEqual(response["model"], "glm-4.6v")
            self.assertEqual(response["diagnosis"], "DFS 缺少边界判断，导致访问越界。")

            stored = JsonStore(db).get_payload("ranked", "mistake", mistake["id"])
            self.assertEqual(stored["aiAnalysis"]["model"], "glm-4.6v")
            self.assertEqual(stored["aiAnalysis"]["agentId"], "agent_ranked_coach")
            self.assertIn("DFS", model.prompts[0])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
