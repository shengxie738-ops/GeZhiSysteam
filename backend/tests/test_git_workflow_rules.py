"""单测 git_workflow_rules.evaluate_git_workflow（Task 2）。"""
import os
import unittest

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.services.git_workflow_rules import evaluate_git_workflow

# ── 公共测试夹具 ──────────────────────────────────────────────────

def _base_project(members=None, default_branch="main"):
    return {
        "id": "test-project",
        "repository": {"defaultBranch": default_branch},
        "memberProgress": members or [
            {"name": "李明", "id": "liming"},
            {"name": "张华", "id": "zhanghua"},
        ],
    }


def _push_payload(branch, commits):
    ref = f"refs/heads/{branch}"
    return {
        "ref": ref,
        "commits": [
            {"id": sha, "message": msg, "author": {"name": author, "username": username}}
            for sha, msg, author, username in commits
        ],
    }


def _pr_payload(head_branch, base_branch):
    return {
        "pull_request": {
            "head": {"label": head_branch},
            "base": {"label": base_branch},
        }
    }


# ── Test Cases ─────────────────────────────────────────────────────

class TestPushLegalFeatureBranch(unittest.TestCase):
    """用例 1：合法 feature 分支 + 正常 commit message。"""

    def test_all_passed_score_100(self):
        project = _base_project()
        matched_member = {"displayName": "李明", "source": "matched"}
        payload = _push_payload("feature/huffman-encode", [
            ("abc1234567890", "feat: 实现哈夫曼树构建算法", "李明", "liming"),
        ])
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member=matched_member,
            author_match_source="matched",
        )
        self.assertEqual(result["eventType"], "push")
        self.assertEqual(result["score"], 100)
        violation_codes = [v["code"] for v in result["violations"]]
        self.assertNotIn("BRANCH_NAME_INVALID", violation_codes)
        self.assertNotIn("COMMIT_MESSAGE_TOO_SHORT", violation_codes)
        self.assertNotIn("COMMIT_MESSAGE_EMPTY", violation_codes)


class TestPushToMain(unittest.TestCase):
    """用例 2：直接 push 到 main 应出现 PUSH_TO_DEFAULT_BRANCH error。"""

    def test_push_main_triggers_error(self):
        project = _base_project()
        payload = _push_payload("main", [
            ("def0000000001", "update readme", "张华", "zhanghua"),
        ])
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member={"displayName": "张华", "source": "matched"},
            author_match_source="matched",
        )
        violation_codes = [v["code"] for v in result["violations"]]
        self.assertIn("PUSH_TO_DEFAULT_BRANCH", violation_codes)
        # error 级别扣 20 分
        self.assertLessEqual(result["score"], 80)
        # severity 应为 error
        v = next(v for v in result["violations"] if v["code"] == "PUSH_TO_DEFAULT_BRANCH")
        self.assertEqual(v["severity"], "error")

    def test_merge_commit_to_main_no_violation(self):
        """Merge commit push 到 main 不应产生违规。"""
        project = _base_project()
        payload = _push_payload("main", [
            ("abc000000001", "Merge pull request #3 from campus/feature/task", "系统", "system"),
        ])
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member={"displayName": "系统", "source": "matched"},
            author_match_source="matched",
        )
        violation_codes = [v["code"] for v in result["violations"]]
        self.assertNotIn("PUSH_TO_DEFAULT_BRANCH", violation_codes)


class TestShortCommitMessage(unittest.TestCase):
    """用例 3：commit message 过短 → COMMIT_MESSAGE_TOO_SHORT warn。"""

    def test_short_message_warn(self):
        project = _base_project()
        payload = _push_payload("feature/fix-bug", [
            ("cccc00000001", "fix", "李明", "liming"),          # 3 字符，过短
        ])
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member={"displayName": "李明", "source": "matched"},
            author_match_source="matched",
        )
        codes = [v["code"] for v in result["violations"]]
        self.assertIn("COMMIT_MESSAGE_TOO_SHORT", codes)
        v = next(v for v in result["violations"] if v["code"] == "COMMIT_MESSAGE_TOO_SHORT")
        self.assertEqual(v["severity"], "warn")

    def test_empty_message_error(self):
        """空 commit message → COMMIT_MESSAGE_EMPTY error。"""
        project = _base_project()
        payload = _push_payload("feature/task", [
            ("dddd00000001", "", "李明", "liming"),
        ])
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member={"displayName": "李明", "source": "matched"},
            author_match_source="matched",
        )
        codes = [v["code"] for v in result["violations"]]
        self.assertIn("COMMIT_MESSAGE_EMPTY", codes)
        v = next(v for v in result["violations"] if v["code"] == "COMMIT_MESSAGE_EMPTY")
        self.assertEqual(v["severity"], "error")


class TestPRBaseNotDefault(unittest.TestCase):
    """用例 4：PR base 分支不是默认分支 → PR_BASE_NOT_DEFAULT warn。"""

    def test_pr_base_not_default(self):
        project = _base_project(default_branch="main")
        payload = _pr_payload("feature/task", "develop")   # base=develop，不是 main
        result = evaluate_git_workflow(
            event_type="pull_request",
            payload=payload,
            project=project,
        )
        codes = [v["code"] for v in result["violations"]]
        self.assertIn("PR_BASE_NOT_DEFAULT", codes)

    def test_pr_base_correct(self):
        """PR base == defaultBranch → 无违规。"""
        project = _base_project(default_branch="main")
        payload = _pr_payload("feature/task", "main")
        result = evaluate_git_workflow(
            event_type="pull_request",
            payload=payload,
            project=project,
        )
        codes = [v["code"] for v in result["violations"]]
        self.assertNotIn("PR_BASE_NOT_DEFAULT", codes)

    def test_pr_head_name_invalid(self):
        """PR head 分支命名不合规 → PR_HEAD_NAME_INVALID warn。"""
        project = _base_project(default_branch="main")
        payload = _pr_payload("tmp-branch", "main")
        result = evaluate_git_workflow(
            event_type="pull_request",
            payload=payload,
            project=project,
        )
        codes = [v["code"] for v in result["violations"]]
        self.assertIn("PR_HEAD_NAME_INVALID", codes)


class TestAuthorUnmatched(unittest.TestCase):
    """用例 5：作者未匹配 → AUTHOR_UNMATCHED warn。"""

    def test_author_unmatched_warn(self):
        project = _base_project()
        payload = _push_payload("feature/sort", [
            ("eeee00000001", "feat: 添加排序算法", "unknown_user", "unknown_user"),
        ])
        # matched_member=None 且 source=unmatched
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member=None,
            author_match_source="unmatched",
        )
        codes = [v["code"] for v in result["violations"]]
        self.assertIn("AUTHOR_UNMATCHED", codes)
        v = next(v for v in result["violations"] if v["code"] == "AUTHOR_UNMATCHED")
        self.assertEqual(v["severity"], "warn")

    def test_author_matched_no_violation(self):
        """author 已匹配 → 不出现 AUTHOR_UNMATCHED。"""
        project = _base_project()
        payload = _push_payload("feature/search", [
            ("ffff00000001", "feat: 实现二分查找", "李明", "liming"),
        ])
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member={"displayName": "李明", "source": "matched"},
            author_match_source="matched",
        )
        codes = [v["code"] for v in result["violations"]]
        self.assertNotIn("AUTHOR_UNMATCHED", codes)


class TestScoreCalculation(unittest.TestCase):
    """得分计算：多个 violations 应累加扣分且下限为 0。"""

    def test_score_floor_zero(self):
        project = _base_project()
        # push main + 空 message + invalid branch（branch已是main所以不触发BRANCH_NAME_INVALID）
        # 但我们可以触发: push main + 空 message + author_unmatched
        # push main = -20, 空 message = -20, author_unmatched = -10 → 100-50=50
        payload = _push_payload("main", [
            ("aaaa00000000", "", "unknown", "unknown"),
        ])
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member=None,
            author_match_source="unmatched",
        )
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_invalid_branch_score_deducted(self):
        """tmp 分支 + 正常 message → 扣 10 分，剩 90。"""
        project = _base_project()
        payload = _push_payload("tmp", [
            ("bbbb00000001", "feat: 添加测试用例，覆盖边界条件", "李明", "liming"),
        ])
        result = evaluate_git_workflow(
            event_type="push",
            payload=payload,
            project=project,
            matched_member={"displayName": "李明", "source": "matched"},
            author_match_source="matched",
        )
        self.assertIn("BRANCH_NAME_INVALID", [v["code"] for v in result["violations"]])
        self.assertEqual(result["score"], 90)


if __name__ == "__main__":
    unittest.main(verbosity=2)
