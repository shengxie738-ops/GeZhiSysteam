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

from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount
from app.services.code_repository_service import get_user_repository_profile
from app.services.team_git_service import get_repository_home


class TargetUserDemoInjectionTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.fixture_root = Path(self.temp_dir.name) / "fixtures"
        self.static_root = Path(self.temp_dir.name) / "static"
        (self.fixture_root / "头像").mkdir(parents=True)
        (self.fixture_root / "学生姓名.txt").write_text(
            "\n".join(
                [
                    "# 男生姓名（4个）",
                    "1. 江景珩",
                    "2. 陆知屿",
                    "3. 沈砚辞",
                    "4. 顾星辞",
                    "# 女生姓名（3个）",
                    "1. 苏晚晴",
                    "2. 温知予",
                    "3. 夏清禾",
                ]
            ),
            encoding="utf-8",
        )
        for index in range(1, 8):
            (self.fixture_root / "头像" / f"头像 ({index}).jpg").write_bytes(f"avatar-{index}".encode("utf-8"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def _payloads(self, db, module, record_type, owner_id=None):
        query = db.query(DomainRecord).filter(
            DomainRecord.module == module,
            DomainRecord.record_type == record_type,
        )
        if owner_id is not None:
            query = query.filter(DomainRecord.owner_id == owner_id)
        return [json.loads(row.payload) for row in query.order_by(DomainRecord.record_key).all()]

    def test_seed_target_user_creates_realistic_repository_and_mistake_dataset(self):
        from app.demo_data.target_user_demo_seed import seed_target_user_demo_data

        db = self.SessionLocal()
        try:
            summary = seed_target_user_demo_data(
                db,
                data_root=self.fixture_root,
                static_root=self.static_root,
                anchor_now=datetime(2026, 7, 5, 12, 0, tzinfo=timezone.utc),
                reset_target=True,
            )

            self.assertEqual(summary["targetUser"], "23001020119")
            self.assertEqual(summary["personalRepositories"], 3)
            self.assertEqual(summary["teamRepositories"], 2)
            self.assertGreaterEqual(summary["mistakes"], 8)

            user = db.query(UserAccount).filter(UserAccount.username == "23001020119").one()
            self.assertEqual(user.real_name, "谢渝")
            self.assertEqual(user.student_id, "23001020119")
            self.assertEqual(user.class_name, "23006")
            self.assertTrue(user.avatar_path.endswith(".jpg"))
            self.assertTrue((self.static_root / "avatars" / user.avatar_path).exists())

            profile = get_user_repository_profile(db, "23001020119")
            own_projects = profile["ownProjects"]
            self.assertEqual(len(own_projects), 3)
            self.assertTrue(all(item["author"] == "23001020119" for item in own_projects))
            self.assertTrue({item["language"] for item in own_projects} >= {"Python", "TypeScript", "Java"})
            for project in own_projects:
                self.assertTrue(project["archiveUrl"].startswith("/static/demo_repositories/"))
                self.assertTrue((self.static_root / project["archiveUrl"].removeprefix("/static/")).exists())
                self.assertGreaterEqual(len(project["sourceFiles"]), 4)
                self.assertTrue(any(file["path"].endswith(("main.py", "app.ts", "Application.java")) for file in project["sourceFiles"]))
                self.assertIn("项目介绍", project["readme"])
                self.assertIn("运行方式", project["readme"])

            mistakes = self._payloads(db, "exams", "mistake", owner_id="23001020119")
            self.assertGreaterEqual(len(mistakes), 8)
            self.assertTrue(any("B+树" in item["questionTitle"] for item in mistakes))
            self.assertTrue(any(item["source"]["type"] == "homework" for item in mistakes))
            self.assertTrue(all(item["studentName"] == "谢渝" for item in mistakes))
            self.assertTrue(all(item["aiAnalysis"] for item in mistakes if item["wrongCount"] >= 2))

            teams = self._payloads(db, "team_collaboration_git", "project")
            self.assertEqual(len(teams), 2)
            for team in teams:
                self.assertTrue(any(member["id"] == "23001020119" for member in team["memberProgress"]))
                self.assertGreaterEqual(len(team["repositoryHome"]["files"]), 5)
                self.assertTrue(team["repositoryHome"]["teacherComment"])
                self.assertTrue(team["repositoryHome"]["revisionSuggestions"])
                self.assertTrue(team["repositoryHome"]["archiveUrl"].startswith("/static/demo_repositories/"))
                self.assertTrue((self.static_root / team["repositoryHome"]["archiveUrl"].removeprefix("/static/")).exists())
                self.assertTrue(any(member.get("teacherComment") for member in team["memberProgress"]))
                self.assertGreaterEqual(len(team["pullRequests"]), 2)
                self.assertGreaterEqual(len(team["recentCommits"]), 5)

            get_repository_home(
                db,
                "target-23001020119-team-oj-review",
                actor={"username": "23001020119", "studentId": "23001020119", "name": "谢渝", "role": "student", "className": "23006"},
            )
            self.assertEqual(len(self._payloads(db, "team_collaboration_git", "project")), 2)
        finally:
            db.close()

    def test_seed_target_user_is_idempotent(self):
        from app.demo_data.target_user_demo_seed import seed_target_user_demo_data

        db = self.SessionLocal()
        try:
            kwargs = {
                "data_root": self.fixture_root,
                "static_root": self.static_root,
                "anchor_now": datetime(2026, 7, 5, 12, 0, tzinfo=timezone.utc),
                "reset_target": True,
            }
            seed_target_user_demo_data(db, **kwargs)
            seed_target_user_demo_data(db, **kwargs)

            self.assertEqual(len(self._payloads(db, "code_repository", "project", "23001020119")), 3)
            self.assertEqual(len(self._payloads(db, "exams", "mistake", "23001020119")), 8)
            self.assertEqual(len(self._payloads(db, "team_collaboration_git", "project")), 2)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
