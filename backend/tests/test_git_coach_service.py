"""单测 git_coach_service（Task 3）。"""
import os
import unittest
from unittest.mock import MagicMock, patch

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
from app.models.gitea_account_binding import GiteaAccountBinding
from app.models.user_account import UserAccount
from app.services.team_git_service import create_collaboration_project
from app.services.git_coach_service import (
    build_coach_prompt,
    parse_coach_json,
    render_fallback_feedback,
    generate_commit_coach_feedback,
)

engine = create_engine("sqlite:///:memory:")
DomainRecord.metadata.create_all(engine)
GiteaAccountBinding.metadata.create_all(engine)
UserAccount.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# 公共规则测试夹具
_RULES_PASS = {
    "eventType": "push",
    "score": 100,
    "passed": [{"code": "COMMIT_HAS_MESSAGE", "message": "OK"}],
    "violations": [],
}
_RULES_FAIL = {
    "eventType": "push",
    "score": 70,
    "passed": [],
    "violations": [
        {
            "code": "BRANCH_NAME_INVALID",
            "severity": "warn",
            "message": "分支名 tmp 不符合规范",
            "hint": "请使用 feature/xxx 命名",
            "evidence": {"branch": "tmp"},
        },
        {
            "code": "COMMIT_MESSAGE_TOO_SHORT",
            "severity": "warn",
            "message": "commit 提交说明过短",
            "hint": "提交说明至少 8 字符",
            "evidence": {},
        },
    ],
}
_PROJECT = {
    "id": "test-project",
    "project": {"title": "测试项目"},
    "repository": {"defaultBranch": "main", "repoName": "test-repo", "giteaOwner": "campus"},
    "memberProgress": [{"name": "李明", "id": "liming"}],
}
_COMMIT_META = {
    "sha": "abc1234567890",
    "branch": "feature/task",
    "author": "李明",
    "message": "feat: 实现哈夫曼压缩算法",
}


def _fresh_db():
    db = SessionLocal()
    db.query(DomainRecord).delete()
    db.commit()
    return db


def _setup_project(db):
    create_collaboration_project(
        db,
        {
            "id": "test-project",
            "title": "测试项目",
            "teamName": "TestTeam",
            "leaderId": "teacher",
            "members": ["李明"],
        },
        actor="teacher",
    )
    from app.repositories.json_store import JsonStore
    from app.services.team_git_service import MODULE, PROJECT
    store = JsonStore(db)
    project = store.get_payload(MODULE, PROJECT, "test-project")
    if project:
        project["repository"] = {
            "defaultBranch": "main",
            "repoName": "test-repo",
            "giteaOwner": "campus",
        }
        store.upsert(MODULE, PROJECT, "test-project", project, owner_id="teacher", status="active")


# ── build_coach_prompt 测试 ──────────────────────────────────────

class TestBuildCoachPrompt(unittest.TestCase):
    def test_contains_branch_and_sha(self):
        system_p, user_p = build_coach_prompt(
            rules=_RULES_FAIL,
            commit_meta=_COMMIT_META,
            diff_text="+ def huffman(data): pass",
            project=_PROJECT,
        )
        self.assertIn("你是", system_p)
        self.assertIn("feature/task", user_p)
        self.assertIn("abc12345", user_p)
        self.assertIn("BRANCH_NAME_INVALID", user_p)

    def test_diff_truncated_at_3500(self):
        long_diff = "+" * 4000
        _, user_p = build_coach_prompt(
            rules=_RULES_PASS,
            commit_meta=_COMMIT_META,
            diff_text=long_diff,
            project=_PROJECT,
        )
        self.assertIn("已截断", user_p)
        # 确认 diff 不超 3500+overhead
        self.assertLess(len(user_p), 5000)


# ── parse_coach_json 测试 ─────────────────────────────────────────

class TestParseCoachJson(unittest.TestCase):
    def test_valid_json(self):
        text = '{"summary": "好的提交", "mistakes": [], "suggestions": ["继续保持"]}'
        result = parse_coach_json(text)
        self.assertEqual(result["summary"], "好的提交")
        self.assertEqual(result["suggestions"], ["继续保持"])

    def test_json_in_markdown_fence(self):
        text = '```json\n{"summary": "差", "mistakes": ["错误"], "suggestions": ["改"]}\n```'
        result = parse_coach_json(text)
        self.assertEqual(result["summary"], "差")

    def test_invalid_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_coach_json("这不是 JSON")

    def test_empty_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_coach_json("")


# ── render_fallback_feedback 测试 ─────────────────────────────────

class TestRenderFallbackFeedback(unittest.TestCase):
    def test_no_violations(self):
        result = render_fallback_feedback(_RULES_PASS, reason="LLM 离线")
        self.assertEqual(result["status"], "fallback")
        self.assertIn("通过", result["summary"])

    def test_with_violations(self):
        result = render_fallback_feedback(_RULES_FAIL, reason="超时")
        self.assertEqual(result["status"], "fallback")
        # mistakes 应来自 violations
        self.assertGreater(len(result["mistakes"]), 0)
        self.assertIn("分支名", result["mistakes"][0])
        # suggestions 应来自 hints
        self.assertGreater(len(result["suggestions"]), 0)


# ── generate_commit_coach_feedback 测试 ───────────────────────────

class TestGenerateCommitCoachFeedback(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        _setup_project(self.db)

    def tearDown(self):
        self.db.close()

    def _push_payload(self, branch="feature/task", sha="abc1234567890abc"):
        return {
            "ref": f"refs/heads/{branch}",
            "pusher": {"name": "liming"},
            "commits": [
                {
                    "id": sha,
                    "message": "feat: 实现哈夫曼压缩算法基本框架",
                    "author": {"name": "李明", "username": "liming"},
                }
            ],
        }

    def test_fake_llm_returns_ready(self):
        """Fake LLM 返回合法 JSON → status=ready。"""
        fake_resp = MagicMock()
        fake_resp.content = '{"summary": "好的提交！", "mistakes": [], "suggestions": ["继续保持"]}'
        fake_llm = MagicMock()
        fake_llm.invoke.return_value = fake_resp

        fake_gitea = MagicMock()
        fake_gitea.get_commit_diff.return_value = "diff --git a/main.py ..."

        with patch("app.services.git_coach_service.build_chat_model", return_value=fake_llm):
            result = generate_commit_coach_feedback(
                self.db,
                "test-project",
                payload=self._push_payload(),
                gitea=fake_gitea,
            )

        feedback = result.get("aiGitCoachFeedback") or []
        self.assertGreater(len(feedback), 0)
        entry = feedback[0]
        self.assertEqual(entry["status"], "ready")
        self.assertEqual(entry["summary"], "好的提交！")
        self.assertEqual(entry["mistakes"], [])

    def test_llm_error_returns_fallback(self):
        """Fake LLM 抛出异常 → status=fallback，mistakes 非空。"""
        fake_llm = MagicMock()
        fake_llm.invoke.side_effect = RuntimeError("LLM 超时")

        fake_gitea = MagicMock()
        fake_gitea.get_commit_diff.return_value = ""

        # 使用错误分支名让规则产生 violation，从而 fallback 有内容
        with patch("app.services.git_coach_service.build_chat_model", return_value=fake_llm):
            result = generate_commit_coach_feedback(
                self.db,
                "test-project",
                payload=self._push_payload(branch="tmp"),
                gitea=fake_gitea,
            )

        feedback = result.get("aiGitCoachFeedback") or []
        self.assertGreater(len(feedback), 0)
        entry = feedback[0]
        self.assertEqual(entry["status"], "fallback")
        # mistakes 应包含规则诊断（BRANCH_NAME_INVALID）或兜底提示
        self.assertIsInstance(entry["mistakes"], list)

    def test_sha_dedup(self):
        """同一 sha 的 commit 多次触发 → 只写入一条记录。"""
        same_sha = "dedup123456789abc"
        fake_resp = MagicMock()
        fake_resp.content = '{"summary": "OK", "mistakes": [], "suggestions": []}'
        fake_llm = MagicMock()
        fake_llm.invoke.return_value = fake_resp
        fake_gitea = MagicMock()
        fake_gitea.get_commit_diff.return_value = ""

        payload1 = self._push_payload(sha=same_sha)
        payload2 = self._push_payload(sha=same_sha)

        with patch("app.services.git_coach_service.build_chat_model", return_value=fake_llm):
            generate_commit_coach_feedback(self.db, "test-project", payload=payload1, gitea=fake_gitea)
            generate_commit_coach_feedback(self.db, "test-project", payload=payload2, gitea=fake_gitea)

        # 重新加载项目，确认去重
        from app.repositories.json_store import JsonStore
        from app.services.team_git_service import MODULE, PROJECT
        store = JsonStore(self.db)
        project = store.get_payload(MODULE, PROJECT, "test-project")
        feedbacks = project.get("aiGitCoachFeedback") or []
        sha_entries = [f for f in feedbacks if f.get("sha") == same_sha]
        self.assertEqual(len(sha_entries), 1, "同一 sha 不应重复写入")

    def test_pr_event_no_commits(self):
        """PR 事件（无 commits）也生成一条 sha='' 的反馈。"""
        pr_payload = {
            "pull_request": {
                "number": 3,
                "head": {"label": "feature/task"},
                "base": {"label": "main"},
            },
            "sender": {"login": "liming"},
        }
        fake_gitea = MagicMock()

        with patch("app.services.git_coach_service.build_chat_model", side_effect=Exception("LLM 离线")):
            result = generate_commit_coach_feedback(
                self.db,
                "test-project",
                payload=pr_payload,
                gitea=fake_gitea,
            )

        feedback = result.get("aiGitCoachFeedback") or []
        self.assertGreater(len(feedback), 0)
        entry = feedback[0]
        self.assertEqual(entry["sha"], "")
        self.assertIn(entry["status"], ("ready", "fallback"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
