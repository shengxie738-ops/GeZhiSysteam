import unittest
import os

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

from app.core.database import Base
from app.models.chat_message import ChatMessage
from app.services.chat_history import (
    build_agent_thread_id,
    list_chat_history,
    normalize_agent_mode,
    save_chat_message,
)


class ChatHistoryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_history_is_isolated_by_agent_mode(self):
        db = self.SessionLocal()
        try:
            save_chat_message(db, user_id="alice", agent_mode="tutor", role="user", content="learn dfs")
            save_chat_message(db, user_id="alice", agent_mode="tutor", role="assistant", content="start with nodes")
            save_chat_message(db, user_id="alice", agent_mode="rag", role="user", content="search bfs")
            save_chat_message(db, user_id="bob", agent_mode="tutor", role="user", content="other user")

            tutor_history = list_chat_history(db, user_id="alice", agent_mode="tutor")
            rag_history = list_chat_history(db, user_id="alice", agent_mode="rag")

            self.assertEqual([item["content"] for item in tutor_history], ["learn dfs", "start with nodes"])
            self.assertEqual([item["content"] for item in rag_history], ["search bfs"])
            self.assertTrue(all(item["agent_mode"] == "tutor" for item in tutor_history))
            self.assertTrue(all(item["created_at"] for item in tutor_history))
        finally:
            db.close()

    def test_agent_mode_normalization_and_thread_ids_are_stable(self):
        self.assertEqual(normalize_agent_mode("rag"), "rag")
        self.assertEqual(normalize_agent_mode("anything-else"), "tutor")
        self.assertEqual(build_agent_thread_id("alice", "rag"), "alice:rag")
        self.assertEqual(build_agent_thread_id("", "tutor"), "guest_user:tutor")


if __name__ == "__main__":
    unittest.main()
