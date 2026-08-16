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
from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount


class RealisticDemoSeedTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        StudentProfile.__table__.create(bind=self.engine)
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.fixture_root = Path(self.temp_dir.name)
        (self.fixture_root / "头像").mkdir()
        (self.fixture_root / "学生姓名.txt").write_text(
            "\n".join(
                [
                    "# 男生姓名（25个）",
                    "1. 江景珩",
                    "2. 陆知屿",
                    "3. 沈砚辞",
                    "# 女生姓名（6个）",
                    "1. 苏晚晴",
                    "2. 温知予",
                    "3. 夏清禾",
                ]
            ),
            encoding="utf-8",
        )
        for index in range(1, 7):
            (self.fixture_root / "头像" / f"头像 ({index}).jpg").write_bytes(b"fake-image")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _payloads(self, db, module, record_type):
        rows = (
            db.query(DomainRecord)
            .filter(DomainRecord.module == module, DomainRecord.record_type == record_type)
            .all()
        )
        return [json.loads(row.payload) for row in rows]

    def test_seed_creates_coherent_demo_dataset_with_real_accounts(self):
        from app.demo_data.realistic_seed import seed_realistic_demo_data

        db = self.SessionLocal()
        try:
            result = seed_realistic_demo_data(
                db,
                data_root=self.fixture_root,
                static_root=self.fixture_root / "static",
                anchor_now=datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc),
                reset_demo=True,
            )

            self.assertEqual(result["students"], 6)
            self.assertEqual(result["codeRepositories"], 20)
            self.assertGreaterEqual(result["homeworks"], 6)
            self.assertGreaterEqual(result["exams"], 4)
            self.assertGreaterEqual(result["mistakes"], 12)
            self.assertGreaterEqual(result["forumPosts"], 12)
            self.assertEqual(result["teamProjects"], 2)

            student = db.query(UserAccount).filter(UserAccount.username == "20230001").one()
            teacher = db.query(UserAccount).filter(UserAccount.username == "teacher_chen").one()
            self.assertEqual(student.real_name, "江景珩")
            self.assertEqual(student.role, "student")
            self.assertTrue(student.avatar_path.endswith(".jpg"))
            self.assertTrue(verify_password("Demo@2026", student.password_hash))
            self.assertTrue(verify_password("Teacher@2026", teacher.password_hash))
            self.assertTrue((self.fixture_root / "static" / "avatars" / student.avatar_path).exists())

            repositories = self._payloads(db, "code_repository", "project")
            self.assertEqual(len(repositories), 20)
            self.assertTrue(all(item["status"] == "active" for item in repositories))
            self.assertTrue(any("类图" in item["readme"] and "```mermaid" in item["readme"] for item in repositories))
            self.assertTrue(any(item["language"] == "Vue" for item in repositories))
            self.assertTrue(any(item["language"] == "Python" for item in repositories))

            homeworks = self._payloads(db, "homework", "homework")
            submissions = self._payloads(db, "homework", "submission")
            homework_ids = {item["id"] for item in homeworks}
            self.assertTrue(all(item["homeworkId"] in homework_ids for item in submissions))
            self.assertTrue(all("T23:" not in item.get("submittedAt", "") for item in submissions))
            self.assertTrue(any(any(q["type"] == "programming" for q in hw["questions"]) for hw in homeworks))

            exams = self._payloads(db, "exams", "exam")
            attempts = self._payloads(db, "exams", "attempt")
            mistakes = self._payloads(db, "exams", "mistake")
            exam_ids = {item["id"] for item in exams}
            self.assertTrue(all(item["examId"] in exam_ids for item in attempts))
            self.assertTrue(all(item["source"]["type"] in {"homework", "exam"} for item in mistakes))
            self.assertTrue(any(item["source"]["type"] == "homework" for item in mistakes))
            self.assertTrue(any(item["source"]["type"] == "exam" for item in mistakes))

            team_projects = self._payloads(db, "team_collaboration_git", "project")
            self.assertEqual(len(team_projects), 2)
            for project in team_projects:
                self.assertIn(len(project["memberProgress"]), {3, 4, 5})
                self.assertGreaterEqual(len(project["recentCommits"]), 5)
                self.assertGreaterEqual(len(project["pullRequests"]), 2)
                self.assertGreaterEqual(len(project["gitEvents"]), 5)
                self.assertTrue(project["repositoryHome"]["teacherComment"])
                self.assertTrue(project["repositoryHome"]["revisionSuggestions"])
                self.assertTrue(project["repositoryHome"]["classDiagram"])
                contributions = {member["contribution"] for member in project["memberProgress"]}
                self.assertGreater(len(contributions), 1)

            forums = self._payloads(db, "forum", "post")
            self.assertTrue(any(len(post.get("replies", [])) >= 2 for post in forums))
            self.assertTrue(any("PR" in post["content"] or "索引" in post["content"] for post in forums))
        finally:
            db.close()

    def test_seed_is_idempotent_for_demo_records(self):
        from app.demo_data.realistic_seed import seed_realistic_demo_data

        db = self.SessionLocal()
        try:
            kwargs = {
                "data_root": self.fixture_root,
                "static_root": self.fixture_root / "static",
                "anchor_now": datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc),
                "reset_demo": True,
            }
            seed_realistic_demo_data(db, **kwargs)
            seed_realistic_demo_data(db, **kwargs)

            self.assertEqual(db.query(UserAccount).filter(UserAccount.role == "student").count(), 6)
            self.assertEqual(
                db.query(DomainRecord)
                .filter(DomainRecord.module == "code_repository", DomainRecord.record_type == "project")
                .count(),
                20,
            )
            self.assertEqual(
                db.query(DomainRecord)
                .filter(DomainRecord.module == "team_collaboration_git", DomainRecord.record_type == "project")
                .count(),
                2,
            )
        finally:
            db.close()

    def test_reset_removes_smoke_records_but_keeps_non_demo_user_records(self):
        from app.demo_data.realistic_seed import seed_realistic_demo_data

        db = self.SessionLocal()
        try:
            db.add(
                DomainRecord(
                    module="homework",
                    record_type="homework",
                    record_key="codex-hw-smoke",
                    owner_id="",
                    role="",
                    status="unsubmitted",
                    payload=json.dumps({"id": "codex-hw-smoke", "title": "Codex smoke homework"}),
                )
            )
            db.add(
                DomainRecord(
                    module="homework",
                    record_type="homework",
                    record_key="real-teacher-homework",
                    owner_id="",
                    role="",
                    status="unsubmitted",
                    payload=json.dumps({"id": "real-teacher-homework", "title": "教师临时作业"}, ensure_ascii=False),
                )
            )
            db.commit()

            seed_realistic_demo_data(
                db,
                data_root=self.fixture_root,
                static_root=self.fixture_root / "static",
                anchor_now=datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc),
                reset_demo=True,
            )

            self.assertIsNone(db.query(DomainRecord).filter(DomainRecord.record_key == "codex-hw-smoke").first())
            self.assertIsNotNone(db.query(DomainRecord).filter(DomainRecord.record_key == "real-teacher-homework").first())
        finally:
            db.close()

    def test_cli_script_exposes_dry_run_and_reset_options(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "init_realistic_demo_data.py"

        self.assertTrue(script.exists())
        content = script.read_text(encoding="utf-8")
        self.assertIn("--dry-run", content)
        self.assertIn("--reset-demo", content)
        self.assertIn("seed_realistic_demo_data", content)


if __name__ == "__main__":
    unittest.main()
