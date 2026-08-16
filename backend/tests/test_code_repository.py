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

from app.core.database import Base
from app.models.domain_record import DomainRecord
from app.models.gitea_account_binding import GiteaAccountBinding
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore
from app.services.code_repository_service import (
    apply_code_repository_gitea_webhook,
    audit_repository_report,
    create_repository_report,
    get_repository_blob,
    get_repository_detail,
    get_repository_languages,
    get_repository_tree,
    get_user_repository_profile,
    list_repositories,
    publish_repository,
    toggle_repository_favorite,
    toggle_repository_star,
)


class FakeGiteaService:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.webhooks = []
        self.users = {}
        self.members = []
        self.collaborators = []
        self.contents = {}
        self.files = {}
        self.languages = {}

    def create_repository(self, *, name, description="", private=False, auto_init=True):
        self.created.append({"name": name, "description": description, "private": private, "auto_init": auto_init})
        return {
            "giteaOwner": "campus",
            "giteaRepo": name,
            "htmlUrl": f"https://git.example.edu/campus/{name}",
            "cloneUrl": f"https://git.example.edu/campus/{name}.git",
            "sshUrl": f"git@git.example.edu:campus/{name}.git",
            "defaultBranch": "main",
            "archiveUrl": f"https://git.example.edu/campus/{name}/archive/main.zip",
        }

    def get_readme(self, *, owner, repo, branch="main"):
        return f"# {repo}\n\nREADME from Gitea"

    def get_archive_url(self, *, owner, repo, branch="main"):
        return f"https://git.example.edu/{owner}/{repo}/archive/{branch}.zip"

    def delete_repository(self, *, owner, repo):
        self.deleted.append({"owner": owner, "repo": repo})
        return True

    def create_user(self, *, username, email, full_name="", password="", must_change_password=False, visibility="private"):
        self.users[username] = {"id": len(self.users) + 1, "login": username, "email": email, "full_name": full_name}
        return self.users[username]

    def ensure_org_membership(self, username, role="member"):
        self.members.append({"username": username, "role": role})
        return True

    def add_repository_collaborator(self, *, owner, repo, username, permission="write"):
        self.collaborators.append({"owner": owner, "repo": repo, "username": username, "permission": permission})
        return True

    def create_webhook(self, *, owner, repo, project_id, module="team_git"):
        self.webhooks.append({"owner": owner, "repo": repo, "project_id": project_id, "module": module})
        return True

    def list_contents(self, *, owner, repo, path="", branch="main"):
        key = f"{owner}/{repo}:{path or ''}"
        if key not in self.contents:
            raise FileNotFoundError(path or f"{owner}/{repo}")
        return self.contents[key]

    def get_file_content(self, *, owner, repo, path, branch="main"):
        key = f"{owner}/{repo}:{path}"
        if key not in self.files:
            raise FileNotFoundError(path)
        return self.files[key]

    def get_languages(self, *, owner, repo):
        key = f"{owner}/{repo}"
        return self.languages.get(key, {})


class CodeRepositoryServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=self.engine)
        UserAccount.__table__.create(bind=self.engine)
        GiteaAccountBinding.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_list_and_detail_rewrite_legacy_local_clone_urls(self):
        db = self.SessionLocal()
        try:
            legacy = {
                "id": "vue-reactive-runtime",
                "title": "Mini Vue Reactive Runtime",
                "slug": "vue-reactive-runtime",
                "description": "Reactive runtime lab",
                "author": "alice",
                "avatar": "",
                "language": "TypeScript",
                "course": "Frontend",
                "tags": [],
                "collaborators": [],
                "visibility": "public",
                "status": "active",
                "recommendScore": 0,
                "readme": "",
                "readmeSyncedAt": "",
                "createdAt": "2026-07-14T00:00:00Z",
                "updatedAt": "2026-07-14T00:00:00Z",
                "webhookConfigured": True,
                "giteaSyncStatus": "connected",
                "lastSyncedAt": "2026-07-14T00:00:00Z",
                "recentCommits": [],
                "pullRequests": [],
                "gitEvents": [],
                "aiGitCoachFeedback": [],
                "giteaCollaborators": [],
                "giteaOwner": "campus",
                "giteaRepo": "vue-reactive-runtime",
                "htmlUrl": "https://git.gezhi.local/campus/vue-reactive-runtime",
                "cloneUrl": "https://git.gezhi.local/campus/vue-reactive-runtime.git",
                "sshUrl": "git@git.gezhi.local:campus/vue-reactive-runtime.git",
                "defaultBranch": "main",
                "archiveUrl": "http://127.0.0.1:3000/campus/vue-reactive-runtime/archive/main.zip",
            }
            JsonStore(db).upsert("code_repository", "project", legacy["id"], legacy, owner_id="alice", status="active")

            listed = list_repositories(db)
            detail = get_repository_detail(db, legacy["id"], gitea=FakeGiteaService())

            for item in (listed[0], detail):
                self.assertEqual(item["htmlUrl"], "https://gezhisystem.com/gitea/campus/vue-reactive-runtime")
                self.assertEqual(item["cloneUrl"], "https://gezhisystem.com/gitea/campus/vue-reactive-runtime.git")
                self.assertEqual(item["sshUrl"], "ssh://git@gezhisystem.com:2222/campus/vue-reactive-runtime.git")
                self.assertNotIn("git.gezhi.local", item["cloneUrl"])
                self.assertNotIn("127.0.0.1", item["archiveUrl"])
        finally:
            db.close()

    def test_publish_repository_syncs_author_as_gitea_collaborator(self):
        from app.models.user_account import hash_password

        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            db.add(UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001", password_hash=hash_password("123456")))
            db.commit()
            project = publish_repository(
                db,
                {"title": "学生代码仓库", "slug": "student-code-lab", "description": "个人代码实验"},
                current_user="20260001",
                gitea=gitea,
            )
            self.assertEqual(project["author"], "20260001")
            self.assertIn({"owner": "campus", "repo": "student-code-lab", "username": "stu_20260001", "permission": "admin"}, gitea.collaborators)
        finally:
            db.close()

    def test_publish_repository_creates_gitea_mapping_and_lists_project(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {
                    "title": "算法可视化实验室",
                    "slug": " Algo Lab ",
                    "description": "图算法和排序算法的交互式演示",
                    "language": "Vue",
                    "course": "数据结构",
                    "tags": ["算法", "可视化"],
                },
                current_user="alice",
                gitea=gitea,
            )

            self.assertEqual(project["author"], "alice")
            self.assertEqual(project["slug"], "algo-lab")
            self.assertEqual(project["cloneUrl"], "https://git.example.edu/campus/algo-lab.git")
            self.assertTrue(project["webhookConfigured"])
            self.assertEqual(project["giteaSyncStatus"], "connected")
            self.assertEqual(project["recentCommits"], [])
            self.assertEqual(project["pullRequests"], [])
            self.assertEqual(gitea.created[0]["name"], "algo-lab")
            self.assertEqual(gitea.webhooks[0], {"owner": "campus", "repo": "algo-lab", "project_id": "algo-lab", "module": "code_repository"})

            projects = list_repositories(db, viewer="bob")
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0]["title"], "算法可视化实验室")
            self.assertEqual(projects[0]["starCount"], 0)
            self.assertFalse(projects[0]["isStarred"])
        finally:
            db.close()

    def test_gitea_push_webhook_deduplicates_commit_sha_for_code_repository(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {"title": "Webhook Lab", "slug": "webhook-lab", "description": "Webhook sync"},
                current_user="alice",
                gitea=gitea,
            )
            payload = {
                "hook_name": "push",
                "ref": "refs/heads/feature/demo",
                "pusher": {"username": "alice"},
                "commits": [
                    {
                        "id": "abcdef0123456789abcdef0123456789abcdef01",
                        "message": "feat: add webhook demo",
                        "author": {"name": "Alice", "email": "alice@example.edu", "username": "alice"},
                    }
                ],
            }

            first = apply_code_repository_gitea_webhook(db, project["id"], payload)
            second = apply_code_repository_gitea_webhook(db, project["id"], payload)

            commits = [item for item in second["recentCommits"] if item.get("sha") == "abcdef0123456789abcdef0123456789abcdef01"]
            self.assertEqual(len(commits), 1)
            self.assertEqual(commits[0]["branch"], "feature/demo")
            self.assertEqual(commits[0]["author"], "Alice (未绑定 Gitea 用户)")
            self.assertEqual(first["giteaSyncStatus"], "synced")
            self.assertEqual(len(second["aiGitCoachFeedback"]), 1)
        finally:
            db.close()

    def test_gitea_pull_request_webhook_upserts_by_number_for_code_repository(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {"title": "PR Lab", "slug": "pr-lab", "description": "PR sync"},
                current_user="alice",
                gitea=gitea,
            )
            opened = {
                "hook_name": "pull_request",
                "action": "opened",
                "sender": {"username": "alice"},
                "pull_request": {
                    "number": 9,
                    "title": "feat: open pr",
                    "html_url": "https://git.example.edu/campus/pr-lab/pulls/9",
                    "merged": False,
                    "user": {"login": "alice"},
                    "head": {"ref": "feature/demo"},
                    "base": {"ref": "main"},
                },
            }
            synchronized = {
                **opened,
                "action": "synchronized",
                "pull_request": {**opened["pull_request"], "title": "feat: update pr"},
            }
            merged = {
                **opened,
                "action": "closed",
                "pull_request": {**opened["pull_request"], "merged": True},
            }

            apply_code_repository_gitea_webhook(db, project["id"], opened)
            updated = apply_code_repository_gitea_webhook(db, project["id"], synchronized)
            closed = apply_code_repository_gitea_webhook(db, project["id"], merged)

            prs = [item for item in updated["pullRequests"] if item.get("number") == 9]
            self.assertEqual(len(prs), 1)
            self.assertEqual(prs[0]["title"], "feat: update pr")
            merged_pr = next(item for item in closed["pullRequests"] if item.get("number") == 9)
            self.assertEqual(merged_pr["status"], "merged")
            self.assertEqual(closed["giteaSyncStatus"], "synced")
        finally:
            db.close()

    def test_detail_reads_readme_and_star_favorite_are_user_scoped(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {"title": "Mini Compiler", "slug": "mini-compiler", "description": "编译原理课程项目"},
                current_user="alice",
                gitea=gitea,
            )

            star_state = toggle_repository_star(db, project["id"], "bob")
            favorite_state = toggle_repository_favorite(db, project["id"], "bob")
            detail = get_repository_detail(db, project["id"], viewer="bob", gitea=gitea)

            self.assertTrue(star_state["isStarred"])
            self.assertEqual(star_state["starCount"], 1)
            self.assertTrue(favorite_state["isFavorited"])
            self.assertEqual(favorite_state["favoriteCount"], 1)
            self.assertIn("README from Gitea", detail["readme"])
            self.assertTrue(detail["isStarred"])
            self.assertTrue(detail["isFavorited"])
        finally:
            db.close()

    def test_report_audit_removes_project_and_updates_profile_groups(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {"title": "违规测试仓库", "slug": "bad-project", "description": "需要被审核"},
                current_user="alice",
                gitea=gitea,
            )
            toggle_repository_star(db, project["id"], "bob")
            toggle_repository_favorite(db, project["id"], "bob")

            profile = get_user_repository_profile(db, "bob")
            self.assertEqual([item["id"] for item in profile["starredProjects"]], [project["id"]])
            self.assertEqual([item["id"] for item in profile["favoriteProjects"]], [project["id"]])

            report = create_repository_report(
                db,
                project["id"],
                {"reason": "违规内容", "description": "README 中包含不当内容"},
                reporter="bob",
            )
            result = audit_repository_report(
                db,
                report["id"],
                {"action": "approve_delete", "note": "确认违规"},
                teacher_id="teacher-a",
                gitea=gitea,
            )
            removed_detail = get_repository_detail(db, project["id"], viewer="bob", gitea=gitea)

            self.assertEqual(result["status"], "approved")
            self.assertEqual(removed_detail["status"], "removed")
            self.assertEqual(gitea.deleted, [{"owner": "campus", "repo": "bad-project"}])
        finally:
            db.close()

    def test_get_repository_tree_returns_gitea_directory_entries(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {"title": "心理健康项目", "slug": "mental-health", "description": "demo"},
                current_user="alice",
                gitea=gitea,
            )
            gitea.contents["campus/mental-health:"] = [
                {"name": "README.md", "path": "README.md", "type": "file", "sha": "abc", "size": 120},
                {"name": "frontend", "path": "frontend", "type": "dir", "sha": "def", "size": 0},
            ]
            gitea.contents["campus/mental-health:frontend"] = [
                {"name": "package.json", "path": "frontend/package.json", "type": "file", "sha": "ghi", "size": 88},
            ]

            root = get_repository_tree(db, project["id"], path="", gitea=gitea)
            nested = get_repository_tree(db, project["id"], path="frontend", gitea=gitea)

            self.assertEqual(root["path"], "")
            self.assertEqual(len(root["entries"]), 2)
            self.assertEqual(root["entries"][0]["name"], "README.md")
            self.assertEqual(nested["path"], "frontend")
            self.assertEqual(nested["entries"][0]["path"], "frontend/package.json")
        finally:
            db.close()

    def test_get_repository_tree_raises_when_directory_missing(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {"title": "心理健康项目", "slug": "mental-health", "description": "demo"},
                current_user="alice",
                gitea=gitea,
            )
            with self.assertRaises(FileNotFoundError):
                get_repository_tree(db, project["id"], path="missing-dir", gitea=gitea)
        finally:
            db.close()

    def test_get_repository_blob_returns_text_preview(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {"title": "心理健康项目", "slug": "mental-health", "description": "demo"},
                current_user="alice",
                gitea=gitea,
            )
            gitea.files["campus/mental-health:README.md"] = {
                "path": "README.md",
                "name": "README.md",
                "encoding": "text",
                "content": "# Hello\n",
                "size": 8,
                "previewable": True,
            }

            blob = get_repository_blob(db, project["id"], path="README.md", gitea=gitea)

            self.assertEqual(blob["path"], "README.md")
            self.assertTrue(blob["previewable"])
            self.assertIn("Hello", blob["content"])
        finally:
            db.close()

    def test_get_repository_languages_returns_percentages(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            project = publish_repository(
                db,
                {"title": "心理健康项目", "slug": "mental-health", "description": "demo"},
                current_user="alice",
                gitea=gitea,
            )
            gitea.languages["campus/mental-health"] = {"Vue": 45.0, "Java": 35.0, "Python": 20.0}

            result = get_repository_languages(db, project["id"], gitea=gitea)

            self.assertEqual(result[0]["name"], "Vue")
            self.assertEqual(result[0]["percent"], 45.0)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
