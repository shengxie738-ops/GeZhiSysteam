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

from app.core.security import get_password_hash, verify_password
from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount
from app.repositories.json_store import load_payload
from app.demo_data.target_user_showcase_seed import (
    TARGET_USER_ID,
    parse_classmate_accounts,
    seed_target_user_showcase_data,
)


class TargetUserShowcaseSeedTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        DomainRecord.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.classmates_root = self.root / "classmates"
        self.team_repo_root = self.root / "team-repos"
        self.static_root = self.root / "static"
        (self.classmates_root / "同学头像").mkdir(parents=True)
        self._write_classmates_file()
        for index in range(1, 17):
            (self.classmates_root / "同学头像" / f"1 ({index}).jpg").write_bytes(f"avatar-{index}".encode("utf-8"))
        self._write_team_repo("OJ Review", "oj-review", "# OJ Review\n\n在线评测与教学复盘系统。\n")
        self._write_team_repo("RAG Course", "", "# RAG Course\n\n课程语义检索与 RAG 助教系统。\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_classmates_file(self):
        (self.classmates_root / "演示账号的同学用户.txt").write_text(
            "\n".join(
                [
                    "顾清寒 ，学号：23001020120。密码：123456",
                    "",
                    "段奕寒，学号：23001020121。密码：123456",
                    "江辰，   学号：23001020122。密码：123456",
                    "陆子昂，学号：23001020123。密码：123456",
                    "谢临风，学号：23001020124。密码：123456",
                    "沈砚之，学号：23001020125。密码：123456",
                    "肖楚墨，   学号：23001020126。密码：123456",
                    "林暮白，学号：23001020127。密码：123456",
                    "许知远，学号：23001020128。密码：123456",
                    "赵云舒，学号：23001020129。密码：123456",
                    "陈星澜，学号：23001020130。密码：123456",
                    "周庭安，学号：23001020131。密码：123456",
                    "罗景行，学号：23001020132。密码：123456",
                    "韩知夏，学号：23001020133。密码：123456",
                    "宋明澈，学号：23001020134。密码：123456",
                    "唐屿白，学号：23001020135。密码：123456",
                ]
            ),
            encoding="utf-8",
        )

    def _write_team_repo(self, folder_name: str, nested: str, readme: str):
        base = self.team_repo_root / folder_name
        repo = base / nested if nested else base
        (repo / "src").mkdir(parents=True)
        (repo / "docs").mkdir()
        (repo / "tests").mkdir()
        (repo / "README.md").write_text(readme + ("\n详细设计说明。" * 2500), encoding="utf-8")
        (repo / "src" / "main.py").write_text("def run():\n    return 'ok'\n" + ("# implementation note\n" * 1500), encoding="utf-8")
        (repo / "docs" / "api.md").write_text("# API\n\n接口说明。\n", encoding="utf-8")
        (repo / "tests" / "test_main.py").write_text("from src.main import run\n\ndef test_run():\n    assert run() == 'ok'\n", encoding="utf-8")

    def _payloads(self, db, module, record_type, owner_id=None):
        query = db.query(DomainRecord).filter(
            DomainRecord.module == module,
            DomainRecord.record_type == record_type,
        )
        if owner_id is not None:
            query = query.filter(DomainRecord.owner_id == owner_id)
        return [load_payload(row) for row in query.order_by(DomainRecord.record_key).all()]

    def test_parse_classmate_accounts_extracts_name_student_id_and_password(self):
        accounts = parse_classmate_accounts(self.classmates_root / "演示账号的同学用户.txt")

        self.assertEqual(len(accounts), 16)
        self.assertEqual(accounts[0].real_name, "顾清寒")
        self.assertEqual(accounts[0].student_id, "23001020120")
        self.assertEqual(accounts[0].password, "123456")

    def test_seed_creates_showcase_data_without_rewriting_target_avatar_or_code_repositories(self):
        db = self.SessionLocal()
        try:
            db.add(
                UserAccount(
                    username=TARGET_USER_ID,
                    role="student",
                    real_name="谢渝",
                    student_id=TARGET_USER_ID,
                    class_name="23006",
                    avatar_path="23001020119.jpg",
                    password_hash=get_password_hash("123456"),
                )
            )
            db.add(
                DomainRecord(
                    module="code_repository",
                    record_type="project",
                    record_key="target-personal-repo",
                    owner_id=TARGET_USER_ID,
                    status="active",
                    payload=json.dumps({"id": "target-personal-repo", "title": "保留的个人仓库"}, ensure_ascii=False),
                )
            )
            db.commit()

            kwargs = {
                "classmates_root": self.classmates_root,
                "team_repo_root": self.team_repo_root,
                "static_root": self.static_root,
                "anchor_now": datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc),
                "reset_target": True,
            }
            first = seed_target_user_showcase_data(db, **kwargs)
            second = seed_target_user_showcase_data(db, **kwargs)

            self.assertEqual(first["classmates"], 16)
            self.assertEqual(first["teamProjects"], 2)
            self.assertEqual(second["teamProjects"], 2)
            self.assertEqual(second["preservedCodeRepositories"], 1)

            target = db.query(UserAccount).filter(UserAccount.username == TARGET_USER_ID).one()
            self.assertEqual(target.avatar_path, "23001020119.jpg")
            self.assertTrue(verify_password("123456", target.password_hash))

            code_repos = self._payloads(db, "code_repository", "project", owner_id=TARGET_USER_ID)
            self.assertEqual(len(code_repos), 1)
            self.assertEqual(code_repos[0]["title"], "保留的个人仓库")

            for student_id in [f"230010201{suffix}" for suffix in range(20, 28)]:
                account = db.query(UserAccount).filter(UserAccount.username == student_id).one()
                self.assertEqual(account.role, "student")
                self.assertEqual(account.class_name, "23006")
                self.assertTrue(verify_password("123456", account.password_hash))
                self.assertTrue((self.static_root / "avatars" / account.avatar_path).exists())

            teams = self._payloads(db, "team_collaboration_git", "project", owner_id=TARGET_USER_ID)
            self.assertEqual(len(teams), 2)
            all_member_ids = {
                member["id"]
                for team in teams
                for member in team["memberProgress"]
            }
            self.assertIn(TARGET_USER_ID, all_member_ids)
            self.assertTrue({f"230010201{suffix}" for suffix in range(20, 28)}.issubset(all_member_ids))
            for team in teams:
                self.assertLess(len(json.dumps(team, ensure_ascii=False)), 35000)
                home = team["repositoryHome"]
                self.assertTrue(home["archiveUrl"].startswith("/static/demo_repositories/"))
                self.assertTrue((self.static_root / home["archiveUrl"].removeprefix("/static/")).exists())
                self.assertIn("#", home["readme"])
                self.assertGreaterEqual(len(home["sourceFiles"]), 3)
                self.assertGreaterEqual(len(team["pullRequests"]), 4)
                self.assertGreaterEqual(len(team["recentCommits"]), 8)
                self.assertGreaterEqual(len(team["gitEvents"]), 8)
                self.assertGreaterEqual(len(team["aiGitCoachFeedback"]), 6)
                self.assertTrue(team["repository"]["webhookConfigured"])
                self.assertEqual(team["repository"]["webhookStatus"], "configured")
                self.assertIn("2026-07-14", team["repository"]["lastSyncedAt"])
                self.assertTrue(any(item.get("source") == "gitea_webhook" for item in team["pullRequests"]))
                self.assertTrue(any(item.get("source") == "gitea" for item in team["pullRequests"]))
                self.assertTrue(any(event["type"] == "push" for event in team["gitEvents"]))
                self.assertTrue(any(event["type"] == "pull_request" for event in team["gitEvents"]))
                self.assertTrue(any("Webhook" in event["text"] or "Gitea" in event["text"] for event in team["gitEvents"]))
                self.assertTrue(all("2026-07-14" in item["createdAt"] for item in team["aiGitCoachFeedback"][:4]))

            mistakes = self._payloads(db, "exams", "mistake", owner_id=TARGET_USER_ID)
            self.assertEqual(len(mistakes), 8)
            self.assertTrue(all(item["studentName"] == "谢渝" for item in mistakes))
            self.assertTrue(any("RAG" in item["questionTitle"] for item in mistakes))

            ranked_profile = self._payloads(db, "ranked", "profile", owner_id=TARGET_USER_ID)
            ranked_matches = self._payloads(db, "ranked", "match", owner_id=TARGET_USER_ID)
            ranked_mistakes = self._payloads(db, "ranked", "mistake", owner_id=TARGET_USER_ID)
            self.assertEqual(len(ranked_profile), 1)
            self.assertEqual(ranked_profile[0]["name"], "谢渝")
            self.assertGreaterEqual(len(ranked_matches), 3)
            self.assertEqual(len(ranked_mistakes), 10)
            self.assertTrue(all(item["studentId"] == TARGET_USER_ID for item in ranked_mistakes))
            self.assertTrue(all(item["status"] == "review" for item in ranked_mistakes))
            self.assertTrue(all(item.get("errorPhenomenon") and item.get("note") for item in ranked_mistakes))
            self.assertTrue(any("期末周" in item["note"] for item in ranked_mistakes))
        finally:
            db.close()

    def test_cli_script_exposes_showcase_options(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "inject_target_user_showcase_data.py"

        self.assertTrue(script.exists())
        content = script.read_text(encoding="utf-8")
        self.assertIn("seed_target_user_showcase_data", content)
        self.assertIn("--classmates-root", content)
        self.assertIn("--team-repo-root", content)
        self.assertIn("--reset-target", content)


if __name__ == "__main__":
    unittest.main()
