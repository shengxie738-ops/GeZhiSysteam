import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount
from app.repositories.json_store import load_payload
from app.demo_data.academic_forum_showcase_seed import (
    FORUM_SHOWCASE_PREFIX,
    parse_forum_classmate_accounts,
    seed_academic_forum_showcase_data,
)


CHINA_TZ = timezone(timedelta(hours=8))


class AcademicForumShowcaseSeedTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.accounts_file = self.root / "演示账号的同学用户.txt"
        self.accounts_file.write_text(
            "\n".join(
                [
                    "顾清寒 ，学号：23001020120。密码：123456",
                    "段奕寒，学号：23001020121。密码：123456",
                    "江辰，   学号：23001020122。密码：123456",
                    "陆子昂，学号：23001020123。密码：123456",
                    "谢临风，学号：23001020124。密码：123456",
                    "沈砚之，学号：23001020125。密码：123456",
                    "肖楚墨， 学号：23001020126。密码：123456",
                    "林暮白，学号：23001020127。密码：123456",
                    "苏晏清，学号：23004020128。密码：123456",
                    "温知遥，学号：23004020129。密码：123456",
                    "许砚秋，学号：23004020130。密码：123456",
                    "周慕笙，学号：23004020131。密码：123456",
                    "傅云深，学号：23004020132。密码：123456",
                    "柳听澜，学号：23004020133。密码：123456",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _forum_payloads(self, db, record_type="post"):
        records = (
            db.query(DomainRecord)
            .filter(DomainRecord.module == "forum", DomainRecord.record_type == record_type)
            .order_by(DomainRecord.record_key)
            .all()
        )
        return [load_payload(row) for row in records], records

    def test_parse_forum_classmate_accounts_extracts_all_given_students(self):
        accounts = parse_forum_classmate_accounts(self.accounts_file)

        self.assertEqual(len(accounts), 14)
        self.assertEqual(accounts[0].real_name, "顾清寒")
        self.assertEqual(accounts[0].student_id, "23001020120")
        self.assertEqual(accounts[0].password, "123456")
        self.assertEqual(accounts[-1].real_name, "柳听澜")
        self.assertEqual(accounts[-1].student_id, "23004020133")

    def test_seed_writes_real_forum_posts_comments_and_hot_topics(self):
        db = self.SessionLocal()
        anchor = datetime(2026, 7, 14, 15, 0, tzinfo=CHINA_TZ)
        try:
            first = seed_academic_forum_showcase_data(
                db,
                accounts_file=self.accounts_file,
                anchor_now=anchor,
                reset_forum_showcase=True,
            )
            second = seed_academic_forum_showcase_data(
                db,
                accounts_file=self.accounts_file,
                anchor_now=anchor,
            )

            self.assertEqual(first["accounts"], 14)
            self.assertGreaterEqual(first["forumPosts"], 25)
            self.assertEqual(second["forumPosts"], first["forumPosts"])

            student_ids = {account.student_id for account in parse_forum_classmate_accounts(self.accounts_file)}
            for student_id in student_ids:
                account = db.query(UserAccount).filter(UserAccount.username == student_id).one()
                self.assertEqual(account.role, "student")
                self.assertEqual(account.student_id, student_id)
                self.assertTrue(verify_password("123456", account.password_hash))

            posts, records = self._forum_payloads(db)
            seeded_posts = [post for post in posts if post["id"].startswith(FORUM_SHOWCASE_PREFIX)]
            seeded_records = [row for row in records if row.record_key.startswith(FORUM_SHOWCASE_PREFIX)]
            self.assertEqual(len(seeded_posts), first["forumPosts"])
            self.assertEqual(len(seeded_records), first["forumPosts"])
            self.assertGreaterEqual(len(seeded_posts), 25)

            categories = {post["category"] for post in seeded_posts}
            self.assertEqual(categories, {"qna", "competition", "experience", "chat"})
            labels = {post["categoryLabel"] for post in seeded_posts}
            self.assertTrue({"课程答疑", "竞赛交流", "经验分享", "日常闲聊"}.issubset(labels))
            self.assertTrue(any("蓝桥杯" in post["title"] or "蓝桥杯" in post["content"] for post in seeded_posts))
            self.assertTrue(any("CCPC" in post["title"] or "程序设计竞赛" in post["content"] for post in seeded_posts))
            self.assertTrue(any("计算机应用能力与数字素养" in post["content"] for post in seeded_posts))
            self.assertTrue(any("机器学习" in post["title"] or "机器学习" in post["tags"] for post in seeded_posts))

            lower_bound = anchor - timedelta(days=35)
            for post, record in zip(seeded_posts, seeded_records, strict=True):
                created = datetime.fromisoformat(post["createdAt"])
                self.assertGreaterEqual(created, lower_bound)
                self.assertLessEqual(created, anchor)
                self.assertGreaterEqual(created.hour, 8)
                self.assertLessEqual(created.hour, 20)
                self.assertIn(post["authorUsername"], student_ids)
                self.assertEqual(len(post.get("replies", [])), 3)
                self.assertEqual(record.owner_id, post["authorUsername"])
                self.assertEqual(record.status, "published")
                self.assertEqual(record.role, "student")
                self.assertEqual(record.created_at.replace(tzinfo=CHINA_TZ), created.replace(tzinfo=CHINA_TZ))
                self.assertLess(len(json.dumps(post, ensure_ascii=False)), 12000)
                for reply in post["replies"]:
                    self.assertIn(reply["authorUsername"], student_ids)
                    self.assertNotEqual(reply["authorUsername"], post["authorUsername"])
                    reply_time = datetime.fromisoformat(reply["createdAt"])
                    self.assertGreaterEqual(reply_time, created)
                    self.assertGreaterEqual(reply_time.hour, 8)
                    self.assertLessEqual(reply_time.hour, 21)

            hot_topics, _ = self._forum_payloads(db, record_type="hot_topic")
            seeded_hot_topics = [topic for topic in hot_topics if topic["id"].startswith(FORUM_SHOWCASE_PREFIX)]
            self.assertGreaterEqual(len(seeded_hot_topics), 10)
        finally:
            db.close()

    def test_cli_script_exposes_forum_showcase_options(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "inject_academic_forum_showcase_data.py"

        self.assertTrue(script.exists())
        content = script.read_text(encoding="utf-8")
        self.assertIn("seed_academic_forum_showcase_data", content)
        self.assertIn("--accounts-file", content)
        self.assertIn("--reset-forum-showcase", content)


if __name__ == "__main__":
    unittest.main()
