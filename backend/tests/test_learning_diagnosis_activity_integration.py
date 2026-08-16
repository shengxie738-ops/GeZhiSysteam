import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost/api/v1")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test-agent")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test-chat")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test-dataset")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "test-dataset")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints.exams import FreePayload as ExamPayload, submit_attempt, update_mistake
from app.api.endpoints.homework import FreePayload as HomeworkPayload, submit_homework
from app.api.endpoints.ranked import RankedMatchSubmitPayload, submit_ranked_match
from app.core.security import create_access_token
from app.models.domain_record import DomainRecord
from app.repositories.json_store import JsonStore


class ActivityPublishingIntegrationTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_exam_submit_and_mistake_correction_publish_after_original_write(self):
        store = JsonStore(self.db)
        store.upsert("exams", "exam", "exam-1", {"id": "exam-1", "objectiveQuestions": [{"id": "q-1", "type": "choice", "correctAnswer": "A", "score": 10}]})
        store.upsert("exams", "attempt", "attempt-1", {"id": "attempt-1", "examId": "exam-1", "studentId": "student-1", "answers": {"q-1": "A"}}, owner_id="student-1")
        with patch("app.api.endpoints.exams.publish_learning_activity_safely", new=AsyncMock(return_value={"status": "PROCESSED"})) as publisher:
            result = asyncio.run(submit_attempt("attempt-1", ExamPayload(), self.db))
            self.assertEqual(result["data"]["status"], "submitted")
            self.assertTrue(publisher.await_count >= 1)
            self.assertEqual(publisher.await_args_list[0].args[1]["content_type"], "EXAM")

            store.upsert("exams", "mistake", "mistake-1", {"id": "mistake-1", "studentId": "student-1", "questionId": "q-1", "mastered": False}, owner_id="student-1")
            asyncio.run(update_mistake("mistake-1", ExamPayload(mastered=True), self.db, None))
            self.assertTrue(any(call.args[1]["content_type"] == "WRONG_QUESTION" for call in publisher.await_args_list))

    def test_homework_submit_returns_success_even_when_listener_fails(self):
        token = f"Bearer {create_access_token('student-1', 'student')}"
        with patch("app.api.endpoints.homework.publish_learning_activity_safely", new=AsyncMock(side_effect=RuntimeError("listener failed"))):
            result = asyncio.run(submit_homework("hw-1", HomeworkPayload(answers={"q": "a"}), token, self.db))
        self.assertTrue(result["data"]["success"])
        self.assertIsNotNone(JsonStore(self.db).get_payload("homework", "submission", "hw-1:student-1", owner_id="student-1"))

    def test_ranked_settlement_publishes_without_changing_success(self):
        store = JsonStore(self.db)
        store.upsert("ranked", "match", "match-1", {"id": "match-1", "studentId": "student-1", "status": "active", "questionId": "ranked-q-1", "question": {"questionId": "ranked-q-1", "scoreReward": 10}}, owner_id="student-1")
        payload = RankedMatchSubmitPayload(userId="student-1", result="win", durationSeconds=30, passedCount=1, totalCount=1, testResults=[])
        with patch("app.api.endpoints.ranked.publish_learning_activity_safely", new=AsyncMock(return_value={"status": "PROCESSED"})) as publisher:
            result = asyncio.run(submit_ranked_match("match-1", payload, self.db))
        self.assertEqual(result["status"], "success")
        publisher.assert_awaited_once()
        self.assertEqual(publisher.await_args.args[1]["content_type"], "RANKED_QUESTION")


if __name__ == "__main__":
    unittest.main()
