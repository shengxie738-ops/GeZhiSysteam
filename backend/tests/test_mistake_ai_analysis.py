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

from app.api.endpoints.exams import FreePayload, request_mistake_ai_analysis
from app.models.domain_record import DomainRecord
from app.repositories.json_store import JsonStore


class FakeAiMessage:
    content = json.dumps(
        {
            "diagnosis": "The student confused B+ tree leaf nodes with internal nodes.",
            "concept": "In a B+ tree, records or record pointers are stored in leaf nodes.",
            "practice": "Compare one B tree and one B+ tree insertion example.",
            "path": ["review original answer", "compare node roles", "practice variant", "retest"],
        }
    )


class FakeChatModel:
    def __init__(self):
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return FakeAiMessage()


class MistakeAiAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_ai_analysis_uses_model_context_and_persists_result(self):
        db = self.SessionLocal()
        model = FakeChatModel()
        try:
            JsonStore(db).upsert(
                "exams",
                "mistake",
                "mistake-1",
                {
                    "id": "mistake-1",
                    "studentId": "student-1",
                    "subject": "Database Systems",
                    "questionTitle": "Why does a B+ tree range query not always scan the primary key?",
                    "studentAnswer": "It always walks the primary key index.",
                    "correctAnswer": "It can use a secondary index and may need table lookup.",
                    "errorReason": "Mixed index scan with table lookup.",
                    "knowledgeTags": ["B+ tree", "index", "table lookup"],
                    "wrongCount": 3,
                },
                owner_id="student-1",
                status="active",
            )

            with patch("app.api.endpoints.exams.build_chat_model", return_value=model) as build_model:
                response = asyncio.run(
                    request_mistake_ai_analysis(
                        "mistake-1",
                        FreePayload(
                            userId="student-1",
                            agentId="agent_mistake_analyst",
                            agentName="错题分析师",
                            agentModel="deepseek-v4-pro",
                            agentPrompt="Focus on the misconception and produce a retest path.",
                        ),
                        db,
                    )
                )

            analysis = response["data"]
            build_model.assert_called_once()
            self.assertEqual(build_model.call_args.args[0], "deepseek-v4-pro")
            self.assertIn("B+ tree", model.prompts[0])
            self.assertIn("It always walks the primary key index.", model.prompts[0])
            self.assertIn("Focus on the misconception", model.prompts[0])
            self.assertEqual(analysis["diagnosis"], "The student confused B+ tree leaf nodes with internal nodes.")
            self.assertEqual(analysis["source"], "ai")
            self.assertEqual(analysis["agentId"], "agent_mistake_analyst")
            self.assertEqual(analysis["agentName"], "错题分析师")

            stored = JsonStore(db).get_payload("exams", "mistake", "mistake-1")
            self.assertEqual(stored["aiAnalysis"]["concept"], analysis["concept"])
            self.assertEqual(stored["aiAnalysis"]["source"], "ai")
            self.assertEqual(stored["aiAnalysis"]["agentId"], "agent_mistake_analyst")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
