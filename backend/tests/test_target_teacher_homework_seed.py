import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
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


class TargetTeacherHomeworkSeedTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.teacher_root = Path(self.temp_dir.name) / "teacher"
        self.static_root = Path(self.temp_dir.name) / "static"
        self.teacher_root.mkdir(parents=True)
        (self.teacher_root / "头像.jpg").write_bytes(b"teacher-avatar")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _homeworks(self, db):
        rows = (
            db.query(DomainRecord)
            .filter(DomainRecord.module == "homework", DomainRecord.record_type == "homework")
            .order_by(DomainRecord.record_key)
            .all()
        )
        return [load_payload(row) for row in rows]

    def test_seed_creates_su_teacher_account_and_visible_choice_blank_homeworks(self):
        from app.demo_data.target_teacher_homework_seed import seed_target_teacher_homework_data

        db = self.SessionLocal()
        try:
            summary = seed_target_teacher_homework_data(
                db,
                teacher_root=self.teacher_root,
                static_root=self.static_root,
                anchor_now=datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc),
                reset_homeworks=True,
            )

            self.assertEqual(summary["teacherUsername"], "teacher_su")
            self.assertEqual(summary["homeworks"], 8)
            self.assertEqual(summary["targetStudent"], "23001020119")

            teacher = db.query(UserAccount).filter(UserAccount.username == "teacher_su").one()
            self.assertEqual(teacher.role, "teacher")
            self.assertEqual(teacher.real_name, "苏老师")
            self.assertEqual(teacher.teacher_id, "T-SU-2026")
            self.assertEqual(teacher.avatar_path, "teacher_su.jpg")
            self.assertTrue(verify_password("123456", teacher.password_hash))
            self.assertEqual((self.static_root / "avatars" / "teacher_su.jpg").read_bytes(), b"teacher-avatar")

            homeworks = self._homeworks(db)
            self.assertEqual(len(homeworks), 8)
            self.assertTrue(all(item["teacherId"] == "teacher_su" for item in homeworks))
            self.assertTrue(all(item["teacherName"] == "苏老师" for item in homeworks))
            self.assertTrue(all(item["targetStudentId"] == "23001020119" for item in homeworks))
            self.assertTrue(all(item["status"] == "unsubmitted" for item in homeworks))
            self.assertTrue(all(item["questions"] for item in homeworks))
            question_types = {question["type"] for item in homeworks for question in item["questions"]}
            self.assertEqual(question_types, {"choice", "blank"})
            self.assertTrue(all("correctAnswer" in q or "correctAnswers" in q for item in homeworks for q in item["questions"]))

            payload_size = len(json.dumps(homeworks, ensure_ascii=False))
            self.assertLess(payload_size, 30000)
        finally:
            db.close()

    def test_seed_is_idempotent_for_teacher_homeworks(self):
        from app.demo_data.target_teacher_homework_seed import seed_target_teacher_homework_data

        db = self.SessionLocal()
        try:
            kwargs = {
                "teacher_root": self.teacher_root,
                "static_root": self.static_root,
                "anchor_now": datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc),
                "reset_homeworks": True,
            }
            seed_target_teacher_homework_data(db, **kwargs)
            seed_target_teacher_homework_data(db, **kwargs)

            self.assertEqual(len(self._homeworks(db)), 8)
            self.assertEqual(db.query(UserAccount).filter(UserAccount.username == "teacher_su").count(), 1)
        finally:
            db.close()

    def test_cli_script_exposes_teacher_homework_seed_options(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "inject_target_teacher_homeworks.py"

        self.assertTrue(script.exists())
        content = script.read_text(encoding="utf-8")
        self.assertIn("seed_target_teacher_homework_data", content)
        self.assertIn("--teacher-root", content)
        self.assertIn("--reset-homeworks", content)


if __name__ == "__main__":
    unittest.main()
