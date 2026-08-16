import json
import os
import unittest
from datetime import datetime, timezone

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

from app.core.security import verify_password
from app.demo_data.target_user_mistake_seed import seed_target_user_mistake_data
from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore


class TargetUserMistakeSeedTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _mistakes(self, db):
        rows = (
            db.query(DomainRecord)
            .filter(
                DomainRecord.module == "exams",
                DomainRecord.record_type == "mistake",
                DomainRecord.owner_id == "23001020119",
            )
            .order_by(DomainRecord.record_key)
            .all()
        )
        return [json.loads(row.payload) for row in rows]

    def test_seed_upserts_curated_target_user_mistakes(self):
        db = self.SessionLocal()
        try:
            JsonStore(db).upsert(
                "exams",
                "mistake",
                "target-23001020119-showcase-mistake-01",
                {
                    "id": "target-23001020119-showcase-mistake-01",
                    "studentId": "23001020119",
                    "studentName": "谢渝",
                    "questionTitle": "旧展示错题",
                    "studentAnswer": "按课堂模板完成了主流程，但边界条件说明不完整。",
                    "correctAnswer": "旧正确答案",
                    "wrongCount": 2,
                    "mastered": False,
                    "aiAnalysis": {"diagnosis": "旧分析"},
                },
                owner_id="23001020119",
                status="active",
            )

            summary = seed_target_user_mistake_data(
                db,
                anchor_now=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
                password="123456",
            )
            seed_target_user_mistake_data(
                db,
                anchor_now=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
                password="123456",
            )

            self.assertEqual(summary["targetUser"], "23001020119")
            self.assertEqual(summary["mistakes"], 8)

            account = db.query(UserAccount).filter(UserAccount.username == "23001020119").one()
            self.assertEqual(account.role, "student")
            self.assertEqual(account.real_name, "谢渝")
            self.assertTrue(verify_password("123456", account.password_hash))

            mistakes = self._mistakes(db)
            self.assertEqual(len(mistakes), 8)
            self.assertFalse(any(item["id"].startswith("target-23001020119-showcase-mistake-") for item in mistakes))
            self.assertTrue(all(item["studentId"] == "23001020119" for item in mistakes))
            self.assertTrue(all(item["studentName"] == "谢渝" for item in mistakes))
            self.assertTrue(all(item["studentAnswer"] != item["correctAnswer"] for item in mistakes))
            self.assertTrue(all("按课堂模板" not in item["studentAnswer"] for item in mistakes))
            self.assertTrue(all(item["aiAnalysis"]["diagnosis"] for item in mistakes))
            self.assertTrue(any("Dijkstra" in item["questionTitle"] and "visited" in item["studentAnswer"] for item in mistakes))
            self.assertTrue(any("覆盖索引" in item["questionTitle"] and "WHERE" in item["studentAnswer"] for item in mistakes))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
