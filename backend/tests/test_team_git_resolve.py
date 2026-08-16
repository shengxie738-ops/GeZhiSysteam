"""Unit tests for resolve_team_project_id and find_project_id_by_repo_name (Task 1)."""
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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.domain_record import DomainRecord
from app.services.team_git_service import (
    find_project_id_by_repo_name,
    resolve_team_project_id,
    create_collaboration_project,
)

engine = create_engine("sqlite:///:memory:")
DomainRecord.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


def _fresh_db():
    db = SessionLocal()
    # 清空所有 domain_record
    db.query(DomainRecord).delete()
    db.commit()
    return db


class TestFindProjectIdByRepoName(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()

    def tearDown(self):
        self.db.close()

    def _create_project(self, project_id: str, repo_name: str):
        """直接写入一个带 repository.repoName 的项目记录。"""
        create_collaboration_project(
            self.db,
            {
                "id": project_id,
                "title": f"Test {project_id}",
                "teamName": "TestTeam",
                "leaderId": "teacher",
                "members": ["alice"],
                "repoName": repo_name,
            },
            actor="teacher",
        )
        # 补充 repository.repoName 字段（create 可能不写入 repository 块）
        from app.repositories.json_store import JsonStore
        from app.services.team_git_service import MODULE, PROJECT
        store = JsonStore(self.db)
        project = store.get_payload(MODULE, PROJECT, project_id)
        if project:
            project.setdefault("repository", {})["repoName"] = repo_name
            store.upsert(MODULE, PROJECT, project_id, project, owner_id="teacher", status="active")

    def test_find_by_exact_repo_name(self):
        """按精确 repoName 反查应返回对应的 project_id。"""
        self._create_project("huffman-team", "huffman-coding")
        found = find_project_id_by_repo_name(self.db, "huffman-coding")
        self.assertEqual(found, "huffman-team")

    def test_find_by_full_name_with_org(self):
        """full_name 为 campus/repo 格式时，取最后一段匹配。"""
        self._create_project("sort-team", "bubble-sort")
        found = find_project_id_by_repo_name(self.db, "campus/bubble-sort")
        self.assertEqual(found, "sort-team")

    def test_find_by_project_id(self):
        """repoName 不存在时，用 project id 也应能找到。"""
        self._create_project("my-project-id", "anything-else")
        found = find_project_id_by_repo_name(self.db, "my-project-id")
        self.assertIsNotNone(found)

    def test_not_found_returns_none(self):
        """找不到时返回 None。"""
        self._create_project("some-project", "some-repo")
        found = find_project_id_by_repo_name(self.db, "totally-different-repo-xyz")
        self.assertIsNone(found)

    def test_case_insensitive(self):
        """匹配应该忽略大小写。"""
        self._create_project("huffman-team2", "Huffman-Coding-Upper")
        found = find_project_id_by_repo_name(self.db, "huffman-coding-upper")
        self.assertEqual(found, "huffman-team2")


class TestResolveTeamProjectId(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()

    def tearDown(self):
        self.db.close()

    def _create_project(self, project_id: str, repo_name: str):
        create_collaboration_project(
            self.db,
            {
                "id": project_id,
                "title": f"Test {project_id}",
                "teamName": "ResolveTeam",
                "leaderId": "teacher",
                "members": ["bob"],
                "repoName": repo_name,
            },
            actor="teacher",
        )
        from app.repositories.json_store import JsonStore
        from app.services.team_git_service import MODULE, PROJECT
        store = JsonStore(self.db)
        project = store.get_payload(MODULE, PROJECT, project_id)
        if project:
            project.setdefault("repository", {})["repoName"] = repo_name
            store.upsert(MODULE, PROJECT, project_id, project, owner_id="teacher", status="active")

    def test_valid_project_id_returns_same(self):
        """有效 project_id 直接命中，不走反查。"""
        self._create_project("known-project", "known-repo")
        result = resolve_team_project_id(self.db, "known-project", {})
        self.assertEqual(result, "known-project")

    def test_invalid_project_id_fallback_by_repo_name(self):
        """错误 project_id + payload.repository.name 正确 → 反查成功。"""
        self._create_project("real-project", "real-repo")
        payload = {"repository": {"name": "real-repo", "full_name": "campus/real-repo"}}
        result = resolve_team_project_id(self.db, "wrong-id-xyz", payload)
        self.assertEqual(result, "real-project")

    def test_invalid_project_id_fallback_by_full_name(self):
        """错误 project_id + payload.repository.full_name 包含正确 repo → 反查成功。"""
        self._create_project("full-name-project", "full-name-repo")
        payload = {"repository": {"name": "other-name", "full_name": "campus/full-name-repo"}}
        result = resolve_team_project_id(self.db, "bad-id", payload)
        self.assertEqual(result, "full-name-project")

    def test_both_fail_raises_file_not_found(self):
        """project_id 无效 + payload 也匹配不上 → FileNotFoundError。"""
        self._create_project("existing-project", "existing-repo")
        payload = {"repository": {"name": "nonexistent-repo"}}
        with self.assertRaises(FileNotFoundError) as ctx:
            resolve_team_project_id(self.db, "bad-id", payload)
        self.assertIn("team project not found", str(ctx.exception))

    def test_empty_payload_raises_file_not_found(self):
        """project_id 无效 + 空 payload → FileNotFoundError。"""
        with self.assertRaises(FileNotFoundError):
            resolve_team_project_id(self.db, "bad-id", {})


    def test_unknown_project_id_is_not_created_by_failed_webhook_resolution(self):
        before = self.db.query(DomainRecord).count()
        payload = {"repository": {"name": "missing-repo", "full_name": "campus/missing-repo"}}

        with self.assertRaises(FileNotFoundError):
            resolve_team_project_id(self.db, "legacy-missing-project", payload)

        after = self.db.query(DomainRecord).count()
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
