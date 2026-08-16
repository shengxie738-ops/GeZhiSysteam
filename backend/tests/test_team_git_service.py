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
from app.models.gitea_account_binding import GiteaAccountBinding
from app.models.user_account import UserAccount, hash_password
from app.repositories.json_store import JsonStore
from app.services.team_git_service import (
    apply_gitea_webhook,
    assign_member_task,
    backfill_training_pull_request_records,
    backfill_repository_home_records,
    confirm_clone,
    create_collaboration_project,
    create_project_repository,
    evaluate_team_contribution,
    get_collaboration_project,
    get_repository_home,
    get_team_repository_blob,
    get_team_repository_languages,
    get_team_repository_tree,
    list_collaboration_projects,
    remind_unsubmitted_members,
    review_pull_request,
    refresh_project_status,
    search_team_members,
    sync_project_from_gitea,
    update_repository_feedback,
)


class FakeGiteaService:
    def __init__(self):
        self.enabled = True
        self.token = "fake-token"
        self.created = []
        self.users = {}
        self.members = []
        self.collaborators = []
        self.contents = {}
        self.files = {}
        self.languages = {}
        self.readmes = {}
        self.pull_requests = []
        self.commits = []
        self.branch_commits = {}
        self.branches = []
        self.commit_calls = []
        self.issues = []
        self.created_issues = []
        self.merged_prs = []
        self.merge_should_fail = False
        self.merge_raises_after_success = False
        self.webhooks = []

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

    def create_webhook(self, *, owner, repo, project_id, module="team_git"):
        return True

    def ensure_webhook(self, *, owner, repo, project_id, module="team_git"):
        url = f"http://host.docker.internal:8516/api/team-git/projects/{project_id}/webhooks/gitea"
        payload = {"configured": True, "url": url, "events": ["push", "pull_request"]}
        self.webhooks.append({"owner": owner, "repo": repo, "project_id": project_id, **payload})
        return payload

    def create_user(self, *, username, email, full_name="", password="", must_change_password=False, visibility="private"):
        self.users[username] = {"id": len(self.users) + 1, "login": username, "email": email, "full_name": full_name}
        return self.users[username]

    def ensure_org_membership(self, username, role="member"):
        self.members.append({"username": username, "role": role})
        return True

    def add_repository_collaborator(self, *, owner, repo, username, permission="write"):
        self.collaborators.append({"owner": owner, "repo": repo, "username": username, "permission": permission})
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

    def get_readme(self, *, owner, repo, branch="main"):
        key = f"{owner}/{repo}"
        return self.readmes.get(key, "")

    def get_languages(self, *, owner, repo):
        key = f"{owner}/{repo}"
        return self.languages.get(key, {})

    def ping(self):
        return {"ok": True, "enabled": True, "message": "ok", "version": "fake"}

    def list_pull_requests(self, *, owner, repo, state="all"):
        return list(self.pull_requests)

    def list_branches(self, *, owner, repo):
        if self.branches:
            return list(self.branches)
        names = list(self.branch_commits.keys())
        return [{"name": name} for name in names]

    def list_commits(self, *, owner, repo, sha=None, limit=30):
        self.commit_calls.append(sha)
        if sha and sha in self.branch_commits:
            return list(self.branch_commits[sha])[:limit]
        return list(self.commits)[:limit]

    def list_issues(self, *, owner, repo, state="open"):
        return [item for item in self.issues if state == "all" or item.get("state", "open") == state]

    def create_issue(self, *, owner, repo, title, body="", assignees=None):
        number = len(self.created_issues) + 100
        issue = {
            "number": number,
            "title": title,
            "body": body,
            "url": f"https://git.example.edu/campus/{repo}/issues/{number}",
            "state": "open",
            "assignees": list(assignees or []),
        }
        self.created_issues.append(issue)
        self.issues.append(issue)
        return issue

    def edit_issue(self, *, owner, repo, index, title=None, body=None, state=None, assignees=None):
        for issue in self.issues:
            if int(issue.get("number") or 0) == int(index):
                if title is not None:
                    issue["title"] = title
                if body is not None:
                    issue["body"] = body
                if state is not None:
                    issue["state"] = state
                if assignees is not None:
                    issue["assignees"] = list(assignees)
                return issue
        raise FileNotFoundError(f"issue {index}")

    def merge_pull_request(self, *, owner, repo, index, merge_message="", merge_style="merge"):
        if self.merge_should_fail:
            raise RuntimeError("merge blocked")
        self.merged_prs.append({"owner": owner, "repo": repo, "index": int(index), "message": merge_message})
        for pr in self.pull_requests:
            if int(pr.get("number") or 0) == int(index):
                pr["status"] = "merged"
                pr["merged"] = True
                pr["state"] = "closed"
        if self.merge_raises_after_success:
            raise RuntimeError("read timeout")
        return {"merged": True, "alreadyMerged": False, "number": int(index)}


class TeamGitServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=self.engine)
        UserAccount.__table__.create(bind=self.engine)
        GiteaAccountBinding.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_default_project_contains_complete_git_workflow_mock(self):
        db = self.SessionLocal()
        try:
            detail = get_collaboration_project(db, "huffman-coding-team", viewer="李明")

            self.assertEqual(detail["project"]["title"], "哈夫曼压缩与解压引擎")
            self.assertEqual(detail["repository"]["repoName"], "huffman-coding-team")
            self.assertEqual(detail["repository"]["defaultBranch"], "main")
            self.assertEqual(len(detail["workflowSteps"]), 6)
            self.assertTrue(all(step["command"] for step in detail["workflowSteps"]))
            self.assertEqual([member["name"] for member in detail["memberProgress"]], ["李明", "张华", "王磊", "Alina AI"])
            self.assertIn("push", {event["type"] for event in detail["gitEvents"]})
            self.assertIn("merged", {item["status"] for item in detail["pullRequests"]})
        finally:
            db.close()

    def test_repository_home_rewrites_legacy_local_clone_urls(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "id": "rag-course",
                    "title": "RAG Course",
                    "teamName": "Vector Team",
                    "leaderId": "leader",
                    "members": ["leader", "member-a"],
                    "repoName": "rag-course",
                    "className": "CS2601",
                },
                actor="leader",
            )
            created["repository"].update(
                {
                    "giteaOwner": "campus",
                    "repoName": "rag-course",
                    "htmlUrl": "https://git.gezhi.local/campus/rag-course",
                    "cloneUrl": "https://git.gezhi.local/campus/rag-course.git",
                    "sshUrl": "git@git.gezhi.local:campus/rag-course.git",
                    "defaultBranch": "main",
                }
            )
            created["repositoryHome"] = {
                "repoName": "rag-course",
                "cloneUrl": "https://git.gezhi.local/campus/rag-course.git",
                "sshUrl": "git@git.gezhi.local:campus/rag-course.git",
                "defaultBranch": "main",
                "cloneUrlMockOnly": False,
            }
            JsonStore(db).upsert(
                "team_collaboration_git",
                "project",
                created["id"],
                created,
                owner_id="leader",
                status="active",
            )

            teacher = {"username": "teacher", "role": "teacher", "className": "CS2601"}
            detail = get_collaboration_project(db, created["id"], actor=teacher)
            home = get_repository_home(db, created["id"], actor=teacher, gitea=gitea)

            self.assertEqual(detail["repository"]["htmlUrl"], "https://gezhisystem.com/gitea/campus/rag-course")
            self.assertEqual(detail["repository"]["cloneUrl"], "https://gezhisystem.com/gitea/campus/rag-course.git")
            self.assertEqual(detail["repository"]["sshUrl"], "ssh://git@gezhisystem.com:2222/campus/rag-course.git")
            self.assertEqual(home["cloneUrl"], "https://gezhisystem.com/gitea/campus/rag-course.git")
            self.assertEqual(home["sshUrl"], "ssh://git@gezhisystem.com:2222/campus/rag-course.git")
            self.assertIn("git clone https://gezhisystem.com/gitea/campus/rag-course.git", detail["workflowSteps"][0]["command"])
            self.assertNotIn("git.gezhi.local", str(detail))
            self.assertNotIn("localhost", str(home))
        finally:
            db.close()

    def test_create_team_repository_syncs_leader_member_and_teacher_gitea_permissions(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            db.add_all(
                [
                    UserAccount(username="20260001", role="student", real_name="队长", student_id="20260001", password_hash=hash_password("123456")),
                    UserAccount(username="20260002", role="student", real_name="队员", student_id="20260002", password_hash=hash_password("123456")),
                    UserAccount(username="teacher_chen", role="teacher", real_name="陈老师", teacher_id="T2026", password_hash=hash_password("123456")),
                ]
            )
            db.commit()
            project = create_collaboration_project(
                db,
                {
                    "title": "权限同步实验",
                    "course": "软件工程",
                    "teamName": "A队",
                    "description": "测试 Gitea 权限",
                    "leaderId": "20260001",
                    "members": [{"memberId": "20260002", "name": "队员"}],
                    "teacherId": "teacher_chen",
                    "className": "计科2601",
                },
                actor={"username": "20260001", "role": "student", "studentId": "20260001"},
            )
            result = create_project_repository(db, project["id"], actor="20260001", gitea=gitea)
            self.assertEqual(result["repository"]["status"], "created")
            self.assertIn({"owner": "campus", "repo": project["id"], "username": "stu_20260001", "permission": "admin"}, gitea.collaborators)
            self.assertIn({"owner": "campus", "repo": project["id"], "username": "stu_20260002", "permission": "write"}, gitea.collaborators)
            self.assertIn({"owner": "campus", "repo": project["id"], "username": "tea_T2026", "permission": "admin"}, gitea.collaborators)
        finally:
            db.close()

    def test_create_repository_updates_project_without_touching_code_repository_module(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            result = create_project_repository(db, "huffman-coding-team", actor="teacher-a", gitea=gitea)

            self.assertEqual(result["repository"]["status"], "created")
            self.assertEqual(result["repository"]["cloneUrl"], "https://git.example.edu/campus/huffman-coding-team.git")
            self.assertFalse(result["repositoryHome"]["cloneUrlMockOnly"])
            self.assertTrue(result["repository"]["webhookConfigured"])
            self.assertEqual(
                result["repository"]["webhookUrl"],
                "http://host.docker.internal:8516/api/team-git/projects/huffman-coding-team/webhooks/gitea",
            )
            self.assertEqual(gitea.created[0]["name"], "huffman-coding-team")

            detail = get_collaboration_project(db, "huffman-coding-team", viewer="teacher-a")
            self.assertEqual(detail["repository"]["htmlUrl"], "https://git.example.edu/campus/huffman-coding-team")
            self.assertTrue(any(event["type"] == "repository_created" for event in detail["gitEvents"]))
        finally:
            db.close()

    def test_missing_pull_request_rows_are_backfilled_from_member_progress(self):
        db = self.SessionLocal()
        try:
            created = create_collaboration_project(
                db,
                {
                    "id": "student-score-warning-system",
                    "title": "学生成绩预警系统",
                    "course": "数据库系统原理课程设计",
                    "teamName": "学情雷达站",
                    "description": "面向教师端的成绩监控与预警平台。",
                    "leaderId": "夏清禾",
                    "members": ["夏清禾", "沈砚辞", "贺临川", "苏沐辰"],
                    "repoName": "student-score-warning-system",
                    "className": "计科 2301",
                },
                actor="夏清禾",
            )
            for index, member in enumerate(created["memberProgress"]):
                member["cloneStatus"] = "done"
                member["pushStatus"] = "detected"
                member["commitCount"] = 6 - index
                member["progress"] = 82 - index * 8
                if member["name"] == "沈砚辞":
                    member["prStatus"] = "open"
                    member["statusLabel"] = "PR 待审核"
                elif member["name"] == "贺临川":
                    member["prStatus"] = "merged"
                    member["mergeStatus"] = "merged"
                    member["statusLabel"] = "已完成"
                    member["progress"] = 100
                else:
                    member["prStatus"] = "needs_pr"
                    member["statusLabel"] = "PR 待创建"
            created["pullRequests"] = []
            JsonStore(db).upsert(
                "team_collaboration_git",
                "project",
                created["id"],
                created,
                owner_id=created.get("ownerId") or "夏清禾",
                status="active",
            )

            detail = get_collaboration_project(db, created["id"], actor={"username": "teacher-a", "role": "teacher", "className": "计科 2301"})
            persisted = JsonStore(db).get_payload("team_collaboration_git", "project", created["id"])

            self.assertEqual(detail["teamSummary"]["openPullRequests"], 1)
            self.assertEqual(len(detail["pullRequests"]), 2)
            self.assertTrue(any(pr["creator"] == "沈砚辞" and pr["status"] == "open" for pr in detail["pullRequests"]))
            self.assertTrue(any(pr["creator"] == "贺临川" and pr["status"] == "merged" for pr in detail["pullRequests"]))
            self.assertEqual(len(persisted["pullRequests"]), 2)
        finally:
            db.close()

    def test_empty_gitea_pr_sync_keeps_backfilled_training_pull_requests(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "id": "ai-learning-companion",
                    "title": "AI学习陪伴系统",
                    "course": "人工智能技术基础",
                    "teamName": "智学工坊",
                    "leaderId": "林舟",
                    "members": ["林舟", "周予安", "陈知夏"],
                    "repoName": "ai-learning-companion",
                    "className": "计科 2301",
                },
                actor="林舟",
            )
            for member in created["memberProgress"]:
                member["cloneStatus"] = "done"
                member["pushStatus"] = "detected"
                member["commitCount"] = 3
                member["prStatus"] = "open" if member["name"] == "周予安" else "needs_pr"
                member["statusLabel"] = "PR 待审核" if member["name"] == "周予安" else "PR 待创建"
                member["progress"] = 74 if member["name"] == "周予安" else 58
            created["repository"]["status"] = "collaborating"
            created["pullRequests"] = []
            JsonStore(db).upsert(
                "team_collaboration_git",
                "project",
                created["id"],
                created,
                owner_id=created.get("ownerId") or "林舟",
                status="active",
            )

            synced = sync_project_from_gitea(
                db,
                created["id"],
                actor={"username": "teacher-a", "role": "teacher", "className": "计科 2301"},
                gitea=gitea,
            )

            self.assertEqual(synced["pullRequests"], [])
            self.assertEqual(synced["teamSummary"]["openPullRequests"], 0)
            self.assertEqual(synced["repository"]["prSource"], "gitea_empty")
        finally:
            db.close()

    def test_live_gitea_empty_pr_sync_does_not_backfill_member_progress_prs(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "id": "live-empty-pr-project",
                    "title": "Live Empty PR Project",
                    "teamName": "Live Empty Team",
                    "members": ["队长", "队员A"],
                    "leaderId": "队长",
                    "repoName": "live-empty-pr-project",
                    "className": "CS2601",
                },
                actor="队长",
            )
            create_project_repository(db, created["id"], actor="队长", gitea=gitea)
            created = get_collaboration_project(db, created["id"], actor="队长")
            for member in created["memberProgress"]:
                member["cloneStatus"] = "done"
                member["pushStatus"] = "detected"
                member["commitCount"] = 2
                member["prStatus"] = "open"
                member["statusLabel"] = "PR 待审核"
            created["pullRequests"] = []
            JsonStore(db).upsert(
                "team_collaboration_git",
                "project",
                created["id"],
                created,
                owner_id=created.get("ownerId") or "队长",
                status="active",
            )

            gitea.pull_requests = []
            synced = sync_project_from_gitea(db, created["id"], actor="队长", gitea=gitea)

            self.assertEqual(synced["pullRequests"], [])
            self.assertEqual(synced["teamSummary"]["openPullRequests"], 0)
            self.assertEqual(synced["repository"]["giteaSyncStatus"], "synced")
            self.assertEqual(synced["repository"]["prSource"], "gitea_empty")
            self.assertEqual(synced["repository"].get("demoFallbackReason") or "", "")
        finally:
            db.close()

    def test_disabled_gitea_marks_demo_fallback_metadata(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        gitea.enabled = False
        try:
            created = create_collaboration_project(
                db,
                {
                    "id": "disabled-gitea-fallback",
                    "title": "Disabled Gitea Fallback",
                    "teamName": "Fallback Team",
                    "members": ["队长", "队员A"],
                    "leaderId": "队长",
                    "repoName": "disabled-gitea-fallback",
                    "className": "CS2601",
                },
                actor="队长",
            )
            for member in created["memberProgress"]:
                member["pushStatus"] = "detected"
                member["prStatus"] = "open"
                member["statusLabel"] = "PR 待审核"
            created["pullRequests"] = []
            JsonStore(db).upsert(
                "team_collaboration_git",
                "project",
                created["id"],
                created,
                owner_id="队长",
                status="active",
            )

            with self.assertRaises(RuntimeError):
                sync_project_from_gitea(db, created["id"], actor="队长", gitea=gitea)

            persisted = get_collaboration_project(db, created["id"], actor="队长")
            self.assertEqual(persisted["repository"]["giteaSyncStatus"], "disabled")
            self.assertEqual(persisted["repository"]["prSource"], "demo_fallback")
            self.assertIn("Gitea", persisted["repository"]["demoFallbackReason"])
            self.assertGreaterEqual(len(persisted["pullRequests"]), 1)
        finally:
            db.close()

    def test_team_summary_contribution_ranking_preserves_git_activity_counts(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            db.add(
                UserAccount(
                    username="23001020120",
                    role="student",
                    real_name="顾清寒",
                    student_id="23001020120",
                    class_name="23006",
                    password_hash=hash_password("123456"),
                )
            )
            db.add(
                GiteaAccountBinding(
                    campus_user_id="23001020120",
                    gitea_username="stu_23001020120",
                    gitea_email="23001020120@gezhi.local",
                    role="student",
                    student_id="23001020120",
                    class_name="23006",
                    sync_status="synced",
                )
            )
            db.commit()
            created = create_collaboration_project(
                db,
                {
                    "id": "contribution-real-counts",
                    "title": "Contribution Real Counts",
                    "teamName": "Contribution Team",
                    "members": [{"memberId": "23001020120", "name": "顾清寒"}],
                    "leaderId": "23001020120",
                    "repoName": "contribution-real-counts",
                    "className": "23006",
                },
                actor="23001020120",
            )
            create_project_repository(db, created["id"], actor="23001020120", gitea=gitea)
            gitea.pull_requests = [
                {
                    "number": 7,
                    "title": "feat: real pr",
                    "status": "open",
                    "creator": "stu_23001020120",
                    "sourceBranch": "feature/real",
                    "targetBranch": "main",
                }
            ]
            gitea.commits = [
                {
                    "sha": "countsha001",
                    "message": "feat: first real commit",
                    "authorName": "顾清寒",
                    "authorEmail": "23001020120@gezhi.local",
                    "authorLogin": "stu_23001020120",
                    "time": "2026-07-14T09:00:00Z",
                }
            ]

            synced = sync_project_from_gitea(db, created["id"], actor="23001020120", gitea=gitea)
            ranking = synced["teamSummary"]["contributionRanking"]
            member = next(item for item in ranking if item["studentId"] == "23001020120" or item["name"] == "顾清寒")

            self.assertEqual(member["commitCount"], 1)
            self.assertEqual(member["prCount"], 1)
            self.assertEqual(member["source"], "gitea")
            self.assertIn("role", member)
            self.assertIn("task", member)
        finally:
            db.close()

    def test_pull_request_webhook_switches_live_empty_project_to_gitea_source(self):
        db = self.SessionLocal()
        try:
            db.add(
                UserAccount(
                    username="23001020124",
                    role="student",
                    real_name="学生24",
                    student_id="23001020124",
                    class_name="23006",
                    password_hash=hash_password("123456"),
                )
            )
            db.add(
                GiteaAccountBinding(
                    campus_user_id="23001020124",
                    gitea_username="stu_23001020124",
                    gitea_email="23001020124@gezhi.local",
                    role="student",
                    student_id="23001020124",
                    class_name="23006",
                    sync_status="synced",
                )
            )
            db.commit()
            created = create_collaboration_project(
                db,
                {
                    "id": "webhook-empty-to-live-pr",
                    "title": "Webhook Empty To Live PR",
                    "teamName": "Webhook Team",
                    "members": ["23001020124"],
                    "leaderId": "23001020124",
                    "repoName": "webhook-empty-to-live-pr",
                    "className": "23006",
                },
                actor="23001020124",
            )
            created["repository"]["giteaSyncStatus"] = "synced"
            created["repository"]["prSource"] = "gitea_empty"
            created["repository"]["webhookStatus"] = "configured"
            created["pullRequests"] = []
            JsonStore(db).upsert(
                "team_collaboration_git",
                "project",
                created["id"],
                created,
                owner_id="23001020124",
                status="active",
            )

            apply_gitea_webhook(
                db,
                created["id"],
                {
                    "hook_name": "pull_request",
                    "action": "opened",
                    "sender": "stu_23001020124",
                    "number": 1,
                    "repository": {
                        "name": "webhook-empty-to-live-pr",
                        "full_name": "campus/webhook-empty-to-live-pr",
                    },
                    "pull_request": {
                        "number": 1,
                        "title": "test: real webhook pr",
                        "user": {"login": "stu_23001020124"},
                        "head": {"ref": "feature/real-webhook"},
                        "base": {"ref": "main"},
                        "merged": False,
                    },
                },
            )

            detail = get_collaboration_project(db, created["id"], actor="23001020124")
            self.assertEqual(detail["repository"]["prSource"], "gitea")
            self.assertEqual(len(detail["pullRequests"]), 1)
            self.assertEqual(detail["pullRequests"][0]["number"], 1)
            self.assertEqual(detail["pullRequests"][0]["source"], "gitea_webhook")
            member = detail["memberProgress"][0]
            self.assertEqual(member["prCount"], 1)
            self.assertEqual(member["source"], "gitea")
        finally:
            db.close()

    def test_sync_filters_system_gitea_accounts_from_members_commits_and_summary(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            db.add(
                UserAccount(
                    username="23010000001",
                    role="student",
                    real_name="Student Alpha",
                    student_id="23010000001",
                    class_name="CS2601",
                    password_hash=hash_password("123456"),
                )
            )
            db.add(
                GiteaAccountBinding(
                    campus_user_id="23010000001",
                    gitea_username="stu_23010000001",
                    gitea_email="23010000001@gezhi.local",
                    role="student",
                    student_id="23010000001",
                    class_name="CS2601",
                    sync_status="synced",
                )
            )
            db.commit()

            created = create_collaboration_project(
                db,
                {
                    "id": "system-account-filter",
                    "title": "System Account Filter",
                    "teamName": "Filter Team",
                    "members": ["23010000001"],
                    "leaderId": "23010000001",
                    "repoName": "system-account-filter",
                    "className": "CS2601",
                },
                actor="23010000001",
            )
            create_project_repository(db, created["id"], actor="23010000001", gitea=gitea)
            gitea.commits = [
                {
                    "sha": "system001",
                    "message": "Merge branch main",
                    "authorName": "campus_admin",
                    "authorEmail": "campus_admin@gezhi.local",
                    "authorLogin": "campus_admin",
                    "time": "2026-07-14T09:00:00Z",
                },
                {
                    "sha": "student001",
                    "message": "feat: student work",
                    "authorName": "Student Alpha",
                    "authorEmail": "23010000001@gezhi.local",
                    "authorLogin": "stu_23010000001",
                    "time": "2026-07-14T09:05:00Z",
                },
            ]

            synced = sync_project_from_gitea(db, created["id"], actor="23010000001", gitea=gitea)

            names = [str(item.get("name") or "") for item in synced["memberProgress"]]
            ranking_names = [str(item.get("name") or "") for item in synced["teamSummary"]["contributionRanking"]]
            commit_authors = [str(item.get("author") or "") for item in synced["recentCommits"]]
            self.assertEqual(len(synced["memberProgress"]), 1)
            self.assertTrue(all("campus_admin" not in name.lower() for name in names + ranking_names + commit_authors))
            member = synced["memberProgress"][0]
            self.assertEqual(member["pushStatus"], "detected")
            self.assertEqual(member["commitCount"], 1)
        finally:
            db.close()

    def test_sync_does_not_add_non_team_gitea_authors_as_members(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            for username, real_name in (
                ("23010000101", "Team Leader"),
                ("23010000199", "Other Student"),
            ):
                db.add(
                    UserAccount(
                        username=username,
                        role="student",
                        real_name=real_name,
                        student_id=username,
                        class_name="CS2601",
                        password_hash=hash_password("123456"),
                    )
                )
            db.add(
                GiteaAccountBinding(
                    campus_user_id="23010000101",
                    gitea_username="stu_23010000101",
                    gitea_email="23010000101@gezhi.local",
                    role="student",
                    student_id="23010000101",
                    class_name="CS2601",
                    sync_status="synced",
                )
            )
            db.add(
                GiteaAccountBinding(
                    campus_user_id="23010000199",
                    gitea_username="stu_23010000199",
                    gitea_email="23010000199@gezhi.local",
                    role="student",
                    student_id="23010000199",
                    class_name="CS2601",
                    sync_status="synced",
                )
            )
            db.commit()

            created = create_collaboration_project(
                db,
                {
                    "id": "non-team-author-filter",
                    "title": "Non Team Author Filter",
                    "teamName": "Filter Team",
                    "members": ["23010000101"],
                    "leaderId": "23010000101",
                    "repoName": "non-team-author-filter",
                    "className": "CS2601",
                },
                actor="23010000101",
            )
            create_project_repository(db, created["id"], actor="23010000101", gitea=gitea)
            gitea.commits = [
                {
                    "sha": "leader001",
                    "message": "feat: leader work",
                    "authorName": "Team Leader",
                    "authorEmail": "23010000101@gezhi.local",
                    "authorLogin": "stu_23010000101",
                    "time": "2026-07-14T09:00:00Z",
                },
                {
                    "sha": "other001",
                    "message": "feat: unrelated student work",
                    "authorName": "Other Student",
                    "authorEmail": "23010000199@gezhi.local",
                    "authorLogin": "stu_23010000199",
                    "time": "2026-07-14T09:05:00Z",
                },
                {
                    "sha": "unbound001",
                    "message": "feat: unbound author work",
                    "authorName": "Gezhi System Bot",
                    "authorEmail": "bot@gezhi.local",
                    "authorLogin": "gezhi-system-bot",
                    "time": "2026-07-14T09:10:00Z",
                },
            ]

            synced = sync_project_from_gitea(db, created["id"], actor="23010000101", gitea=gitea)

            names = [str(item.get("name") or "") for item in synced["memberProgress"]]
            ranking_names = [str(item.get("name") or "") for item in synced["teamSummary"]["contributionRanking"]]
            self.assertEqual(names, ["23010000101"])
            self.assertEqual(ranking_names, ["23010000101"])
            self.assertTrue(any(item.get("sha") == "other001" for item in synced["recentCommits"]))
            self.assertFalse(any("Other Student" in name for name in names + ranking_names))
            self.assertFalse(any("Gezhi System Bot" in name for name in names + ranking_names))
        finally:
            db.close()

    def test_existing_system_gitea_members_are_hidden_even_without_enrolled_member_list(self):
        db = self.SessionLocal()
        try:
            created = create_collaboration_project(
                db,
                {
                    "id": "existing-system-member-filter",
                    "title": "Existing System Member Filter",
                    "teamName": "Filter Team",
                    "members": ["23010000901"],
                    "leaderId": "23010000901",
                    "repoName": "existing-system-member-filter",
                    "className": "CS2601",
                },
                actor="23010000901",
            )
            created["memberProgress"].append(
                {
                    "id": "campus_admin-gitea",
                    "name": "campus_admin (unbound Gitea user)",
                    "role": "student",
                    "task": "Existing System Member Filter",
                    "branch": "main",
                    "cloneStatus": "done",
                    "commitCount": 2,
                    "pushStatus": "detected",
                    "prStatus": "needs_pr",
                    "mergeStatus": "pending",
                    "statusLabel": "PR pending",
                    "lastCommitAt": "2026-07-14T09:00:00Z",
                    "score": 0,
                    "contribution": 0,
                    "progress": 58,
                    "source": "gitea",
                }
            )
            JsonStore(db).upsert(
                "team_collaboration_git",
                "project",
                created["id"],
                created,
                owner_id="23010000901",
                status="active",
            )

            detail = get_collaboration_project(db, created["id"], actor="23010000901")

            names = [str(item.get("name") or "") for item in detail["memberProgress"]]
            ranking_names = [str(item.get("name") or "") for item in detail["teamSummary"]["contributionRanking"]]
            self.assertEqual(names, ["23010000901"])
            self.assertTrue(all("campus_admin" not in name.lower() for name in names + ranking_names))
            self.assertEqual(detail["teamSummary"]["totalMembers"], 1)
        finally:
            db.close()

    def test_sync_reads_member_feature_branch_commits_without_pull_request(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            db.add(
                UserAccount(
                    username="23010000002",
                    role="student",
                    real_name="Student Beta",
                    student_id="23010000002",
                    class_name="CS2601",
                    password_hash=hash_password("123456"),
                )
            )
            db.add(
                GiteaAccountBinding(
                    campus_user_id="23010000002",
                    gitea_username="stu_23010000002",
                    gitea_email="23010000002@gezhi.local",
                    role="student",
                    student_id="23010000002",
                    class_name="CS2601",
                    sync_status="synced",
                )
            )
            db.commit()

            created = create_collaboration_project(
                db,
                {
                    "id": "feature-branch-sync",
                    "title": "Feature Branch Sync",
                    "teamName": "Branch Team",
                    "members": ["23010000002"],
                    "leaderId": "23010000002",
                    "repoName": "feature-branch-sync",
                    "className": "CS2601",
                    "tasks": [
                        {
                            "memberId": "23010000002",
                            "task": "Implement branch-only change",
                            "branch": "feature/beta-task",
                        }
                    ],
                },
                actor="23010000002",
            )
            create_project_repository(db, created["id"], actor="23010000002", gitea=gitea)
            gitea.commits = []
            gitea.branch_commits = {
                "feature/beta-task": [
                    {
                        "sha": "beta001",
                        "message": "feat: beta branch work",
                        "authorName": "Student Beta",
                        "authorEmail": "23010000002@gezhi.local",
                        "authorLogin": "stu_23010000002",
                        "time": "2026-07-14T10:00:00Z",
                    }
                ]
            }

            synced = sync_project_from_gitea(db, created["id"], actor="23010000002", gitea=gitea)

            member = synced["memberProgress"][0]
            self.assertIn("feature/beta-task", gitea.commit_calls)
            self.assertEqual(member["pushStatus"], "detected")
            self.assertEqual(member["commitCount"], 1)
            self.assertTrue(any(item.get("branch") == "feature/beta-task" for item in synced["recentCommits"]))
        finally:
            db.close()

    def test_team_summary_auto_contribution_uses_real_git_activity_when_teacher_has_not_scored(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            for suffix, name in (("03", "Student Gamma"), ("04", "Student Delta")):
                student_id = f"230100000{suffix}"
                db.add(
                    UserAccount(
                        username=student_id,
                        role="student",
                        real_name=name,
                        student_id=student_id,
                        class_name="CS2601",
                        password_hash=hash_password("123456"),
                    )
                )
                db.add(
                    GiteaAccountBinding(
                        campus_user_id=student_id,
                        gitea_username=f"stu_{student_id}",
                        gitea_email=f"{student_id}@gezhi.local",
                        role="student",
                        student_id=student_id,
                        class_name="CS2601",
                        sync_status="synced",
                    )
                )
            db.commit()

            created = create_collaboration_project(
                db,
                {
                    "id": "auto-contribution-sync",
                    "title": "Auto Contribution Sync",
                    "teamName": "Contribution Team",
                    "members": ["23010000003", "23010000004"],
                    "leaderId": "23010000003",
                    "repoName": "auto-contribution-sync",
                    "className": "CS2601",
                },
                actor="23010000003",
            )
            create_project_repository(db, created["id"], actor="23010000003", gitea=gitea)
            gitea.pull_requests = [
                {
                    "number": 3,
                    "title": "feat: gamma merged",
                    "status": "merged",
                    "creator": "stu_23010000003",
                    "sourceBranch": "feature/gamma",
                    "targetBranch": "main",
                }
            ]
            gitea.commits = [
                {
                    "sha": "gamma001",
                    "message": "feat: gamma work",
                    "authorName": "Student Gamma",
                    "authorEmail": "23010000003@gezhi.local",
                    "authorLogin": "stu_23010000003",
                    "time": "2026-07-14T10:00:00Z",
                },
                {
                    "sha": "delta001",
                    "message": "feat: delta work",
                    "authorName": "Student Delta",
                    "authorEmail": "23010000004@gezhi.local",
                    "authorLogin": "stu_23010000004",
                    "time": "2026-07-14T10:05:00Z",
                },
            ]

            synced = sync_project_from_gitea(db, created["id"], actor="23010000003", gitea=gitea)
            ranking = synced["teamSummary"]["contributionRanking"]
            contributions = {item["studentId"]: item["contribution"] for item in ranking}

            self.assertEqual(contributions["23010000003"] + contributions["23010000004"], 100)
            self.assertGreater(contributions["23010000003"], contributions["23010000004"])
            self.assertTrue(all(item.get("contributionSource") == "gitea_auto" for item in ranking))
        finally:
            db.close()

    def test_real_gitea_sync_replaces_seed_prs_and_demo_commits(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            db.add(
                UserAccount(
                    username="23001020119",
                    role="student",
                    real_name="Student One",
                    student_id="23001020119",
                    class_name="CS2601",
                    password_hash=hash_password("123456"),
                )
            )
            db.add(
                GiteaAccountBinding(
                    campus_user_id="23001020119",
                    gitea_username="stu_23001020119",
                    gitea_email="23001020119@gezhi.local",
                    role="student",
                    student_id="23001020119",
                    class_name="CS2601",
                    sync_status="synced",
                )
            )
            db.commit()

            created = create_collaboration_project(
                db,
                {
                    "id": "real-gitea-only",
                    "title": "Real Gitea Project",
                    "teamName": "Real Team",
                    "members": ["23001020119"],
                    "leaderId": "23001020119",
                    "repoName": "real-gitea-only",
                    "className": "CS2601",
                },
                actor="23001020119",
            )
            created["repository"]["status"] = "created"
            created["pullRequests"] = [
                {"number": 1, "title": "demo pr should be replaced", "creator": "Demo", "status": "open"},
                {"number": 2, "title": "demo backfill should disappear", "creator": "Demo", "status": "open"},
            ]
            created["recentCommits"] = [
                {"id": "demo-commit", "author": "Demo", "branch": "feature/demo", "message": "demo commit without sha"}
            ]
            JsonStore(db).upsert(
                "team_collaboration_git",
                "project",
                created["id"],
                created,
                owner_id="23001020119",
                status="active",
            )

            gitea.pull_requests = [
                {
                    "number": 1,
                    "title": "feat: real gitea pr",
                    "status": "open",
                    "creator": "stu_23001020119",
                    "sourceBranch": "feature/real-e2e",
                    "targetBranch": "main",
                    "url": "http://localhost:3000/campus/real-gitea-only/pulls/1",
                    "updatedAt": "2026-07-13T10:00:00Z",
                    "createdAt": "2026-07-13T09:00:00Z",
                }
            ]
            gitea.commits = [
                {
                    "sha": "abc123def456",
                    "message": "feat: real commit",
                    "authorName": "Student One",
                    "authorEmail": "23001020119@gezhi.local",
                    "authorLogin": "stu_23001020119",
                    "time": "2026-07-13T09:30:00Z",
                    "url": "http://localhost:3000/campus/real-gitea-only/commit/abc123def456",
                }
            ]

            synced = sync_project_from_gitea(db, created["id"], gitea=gitea)

            self.assertEqual(len(synced["pullRequests"]), 1)
            self.assertEqual(synced["pullRequests"][0]["title"], "feat: real gitea pr")
            self.assertEqual(synced["pullRequests"][0]["source"], "gitea")
            self.assertEqual({item["number"] for item in synced["pullRequests"]}, {1})
            self.assertTrue(all(item.get("sha") for item in synced["recentCommits"]))
            self.assertTrue(any(item.get("sha") == "abc123def456" and item.get("source") == "gitea" for item in synced["recentCommits"]))
        finally:
            db.close()

    def test_training_pull_request_backfill_updates_all_active_projects(self):
        db = self.SessionLocal()
        try:
            created = create_collaboration_project(
                db,
                {
                    "id": "campus-secondhand-market",
                    "title": "校园二手交易市场",
                    "teamName": "闲置流转局",
                    "leaderId": "周叙白",
                    "members": ["周叙白", "许安然"],
                    "repoName": "campus-secondhand-market",
                },
                actor="周叙白",
            )
            for member in created["memberProgress"]:
                if member["name"] == "许安然":
                    member["cloneStatus"] = "done"
                    member["pushStatus"] = "detected"
                    member["prStatus"] = "open"
                    member["statusLabel"] = "PR 待审核"
                    member["progress"] = 76
                    member["commitCount"] = 4
            created["pullRequests"] = []
            JsonStore(db).upsert("team_collaboration_git", "project", created["id"], created, owner_id="周叙白", status="active")

            changed = backfill_training_pull_request_records(db)
            persisted = JsonStore(db).get_payload("team_collaboration_git", "project", created["id"])

            self.assertEqual(changed, 1)
            self.assertEqual(len(persisted["pullRequests"]), 1)
            self.assertEqual(persisted["pullRequests"][0]["creator"], "许安然")
        finally:
            db.close()

    def test_confirm_clone_and_webhook_advance_member_progress(self):
        db = self.SessionLocal()
        try:
            clone_result = confirm_clone(db, "huffman-coding-team", user_id="赵雷")
            zhaolei = next(member for member in clone_result["memberProgress"] if member["name"] == "赵雷")
            self.assertEqual(zhaolei["cloneStatus"], "done")
            self.assertEqual(clone_result["currentUserProgress"]["nextHint"], "完成提交并推送后，等待系统检测 push 事件。")

            push_result = apply_gitea_webhook(
                db,
                "huffman-coding-team",
                {
                    "type": "push",
                    "sender": "李明",
                    "branch": "feature/huffman-compress",
                    "commitMessage": "feat: 完成哈夫曼压缩核心逻辑",
                    "commitCount": 2,
                },
            )
            liming = next(member for member in push_result["memberProgress"] if member["name"] == "李明")
            self.assertEqual(liming["pushStatus"], "detected")
            self.assertEqual(liming["prStatus"], "needs_pr")

            pr_result = apply_gitea_webhook(
                db,
                "huffman-coding-team",
                {
                    "type": "pull_request",
                    "action": "opened",
                    "sender": "李明",
                    "number": 7,
                    "title": "feat: 哈夫曼压缩核心逻辑",
                    "sourceBranch": "feature/huffman-compress",
                    "targetBranch": "main",
                    "url": "https://git.example.edu/campus/huffman-coding-team/pulls/7",
                },
            )
            self.assertTrue(any(pr["number"] == 7 and pr["status"] == "open" for pr in pr_result["pullRequests"]))

            merge_result = apply_gitea_webhook(
                db,
                "huffman-coding-team",
                {
                    "type": "pull_request",
                    "action": "merged",
                    "sender": "teacher-a",
                    "creator": "李明",
                    "number": 7,
                },
            )
            liming = next(member for member in merge_result["memberProgress"] if member["name"] == "李明")
            self.assertEqual(liming["mergeStatus"], "merged")
            self.assertEqual(liming["score"], 82)
        finally:
            db.close()

    def test_gitea_push_payload_maps_student_and_deduplicates_commit_sha(self):
        db = self.SessionLocal()
        try:
            db.add(
                UserAccount(
                    username="liming",
                    role="student",
                    real_name="李明",
                    student_id="20230002",
                    class_name="计科 2301",
                    password_hash=hash_password("123456"),
                )
            )
            db.commit()
            payload = {
                "hook_name": "push",
                "ref": "refs/heads/feature/huffman-compress",
                "pusher": {"username": "liming"},
                "repository": {"name": "huffman-coding-team", "owner": {"username": "campus"}},
                "commits": [
                    {
                        "id": "0123456789abcdef0123456789abcdef01234567",
                        "message": "feat: implement compression flow",
                        "author": {"name": "Li Ming", "email": "20230002@gezhi.local", "username": "liming"},
                        "timestamp": "2026-07-07T14:20:00+08:00",
                    }
                ],
            }

            first = apply_gitea_webhook(db, "huffman-coding-team", payload)
            second = apply_gitea_webhook(db, "huffman-coding-team", payload)

            commits = [
                item
                for item in second["recentCommits"]
                if item.get("sha") == "0123456789abcdef0123456789abcdef01234567"
            ]
            self.assertEqual(len(commits), 1)
            self.assertEqual(commits[0]["author"], "李明")
            self.assertEqual(commits[0]["branch"], "feature/huffman-compress")
            member = next(item for item in first["memberProgress"] if item["name"] == "李明")
            self.assertEqual(member["pushStatus"], "detected")
            self.assertEqual(member["commitCount"], 4)
        finally:
            db.close()

    def test_gitea_pull_request_upserts_by_number_and_merge_does_not_score(self):
        db = self.SessionLocal()
        try:
            db.add(
                UserAccount(
                    username="liming",
                    role="student",
                    real_name="李明",
                    student_id="20230002",
                    class_name="计科 2301",
                    password_hash=hash_password("123456"),
                )
            )
            db.commit()
            opened = {
                "hook_name": "pull_request",
                "action": "opened",
                "sender": {"username": "liming"},
                "pull_request": {
                    "number": 17,
                    "title": "feat: implement compression flow",
                    "html_url": "http://localhost:3000/campus/huffman-coding-team/pulls/17",
                    "merged": False,
                    "user": {"login": "liming"},
                    "head": {"ref": "feature/huffman-compress"},
                    "base": {"ref": "main"},
                },
            }
            updated = {
                **opened,
                "hook_name": "pull_request_sync",
                "action": "synchronized",
                "pull_request": {**opened["pull_request"], "title": "feat: refine compression flow"},
            }
            merged = {
                **opened,
                "action": "closed",
                "pull_request": {**opened["pull_request"], "merged": True},
            }

            apply_gitea_webhook(db, "huffman-coding-team", opened)
            after_update = apply_gitea_webhook(db, "huffman-coding-team", updated)
            after_merge = apply_gitea_webhook(db, "huffman-coding-team", merged)

            prs = [item for item in after_update["pullRequests"] if item.get("number") == 17]
            self.assertEqual(len(prs), 1)
            self.assertEqual(prs[0]["title"], "feat: refine compression flow")
            self.assertEqual(prs[0]["source"], "gitea_webhook")
            merged_pr = next(item for item in after_merge["pullRequests"] if item.get("number") == 17)
            self.assertEqual(merged_pr["status"], "merged")
            member = next(item for item in after_merge["memberProgress"] if item["name"] == "李明")
            self.assertEqual(member["mergeStatus"], "merged")
            self.assertEqual(member["score"], 82)
        finally:
            db.close()

    def test_refresh_project_status_can_drive_demo_state_switches(self):
        db = self.SessionLocal()
        try:
            result = refresh_project_status(
                db,
                "huffman-coding-team",
                stage="merged",
                actor="teacher-a",
                allow_demo_stage=True,
            )
            self.assertEqual(result["repository"]["status"], "completed")
            self.assertEqual(result["teamSummary"]["completedMembers"], 2)
            self.assertTrue(any(event["type"] == "status_refreshed" for event in result["gitEvents"]))
        finally:
            db.close()

    def test_captain_can_create_project_and_assign_member_tasks(self):
        db = self.SessionLocal()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "校园算法协作平台",
                    "course": "软件工程综合实训",
                    "teamName": "极客先锋队",
                    "description": "参考 GitHub flow 完成多人分支开发、PR 审核与合并。",
                    "leaderId": "张华",
                    "members": ["张华", "李明", "王磊"],
                    "tasks": [
                        {"memberId": "李明", "task": "实现登录鉴权模块", "branch": "feature/auth-flow"},
                        {"memberId": "王磊", "task": "补充端到端测试", "branch": "feature/e2e-tests"},
                    ],
                },
                actor="张华",
            )

            self.assertEqual(created["project"]["leaderId"], "张华")
            self.assertEqual(created["repository"]["status"], "not_created")
            self.assertEqual(created["project"]["description"], "参考 GitHub flow 完成多人分支开发、PR 审核与合并。")
            liming = next(member for member in created["memberProgress"] if member["name"] == "李明")
            self.assertEqual(liming["task"], "实现登录鉴权模块")
            self.assertEqual(liming["branch"], "feature/auth-flow")

            updated = assign_member_task(
                db,
                created["id"],
                "王磊",
                {"task": "负责 Pull Request 回归测试", "branch": "feature/pr-regression"},
                actor="张华",
            )
            wanglei = next(member for member in updated["memberProgress"] if member["name"] == "王磊")
            self.assertEqual(wanglei["task"], "负责 Pull Request 回归测试")
            self.assertEqual(wanglei["branch"], "feature/pr-regression")
            self.assertTrue(any(event["type"] == "task_assigned" for event in updated["gitEvents"]))
        finally:
            db.close()

    def test_captain_reminds_unsubmitted_members_and_recommends_pr_merge(self):
        db = self.SessionLocal()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "PR 协作演练",
                    "teamName": "Merge Rangers",
                    "description": "练习未提交提醒与队长初审。",
                    "leaderId": "队长",
                    "members": ["队长", "成员A"],
                },
                actor="队长",
            )

            reminded = remind_unsubmitted_members(
                db,
                created["id"],
                {"memberIds": ["成员A"], "message": "今晚 22:00 前请完成 push 并创建 PR。"},
                actor="队长",
            )
            member = next(item for item in reminded["memberProgress"] if item["name"] == "成员A")
            self.assertEqual(member["reminderCount"], 1)
            self.assertEqual(reminded["reminders"][0]["message"], "今晚 22:00 前请完成 push 并创建 PR。")

            pr_opened = apply_gitea_webhook(
                db,
                created["id"],
                {
                    "type": "pull_request",
                    "action": "opened",
                    "sender": "成员A",
                    "number": 12,
                    "title": "feat: 完成协作模块",
                    "sourceBranch": "feature/member-a",
                    "targetBranch": "main",
                },
            )
            self.assertTrue(any(pr["number"] == 12 for pr in pr_opened["pullRequests"]))

            reviewed = review_pull_request(
                db,
                created["id"],
                12,
                {"action": "recommend_merge", "comment": "本地测试通过，建议教师合并。"},
                actor="队长",
            )
            pr = next(item for item in reviewed["pullRequests"] if item["number"] == 12)
            self.assertEqual(pr["leaderReviewStatus"], "recommended")
            self.assertEqual(pr["statusLabel"], "队长建议合并")
            self.assertEqual(pr["leaderReviewer"], "队长")
        finally:
            db.close()

    def test_teacher_can_list_projects_audit_pr_and_evaluate_contribution(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "教师端管理演练",
                    "teamName": "Admin Flow",
                    "description": "教师管理员统一审核 PR 和贡献度。",
                    "leaderId": "赵队",
                    "members": ["赵队", "李明"],
                    "repoName": "admin-flow",
                    "className": "计科 2301",
                },
                actor="赵队",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            apply_gitea_webhook(
                db,
                created["id"],
                {
                    "type": "pull_request",
                    "action": "opened",
                    "sender": "李明",
                    "number": 3,
                    "title": "feat: 提交核心实现",
                    "sourceBranch": "feature/core",
                    "targetBranch": "main",
                },
            )
            gitea.pull_requests = [{"number": 3, "status": "open", "merged": False, "state": "open"}]
            review_pull_request(
                db,
                created["id"],
                3,
                {"action": "recommend_merge", "comment": "队长初审通过。"},
                actor="赵队",
                gitea=gitea,
            )

            projects = list_collaboration_projects(db, viewer="teacher-a")
            self.assertTrue(any(item["id"] == created["id"] for item in projects))

            audited = review_pull_request(
                db,
                created["id"],
                3,
                {"action": "teacher_approve", "comment": "管理员审核通过。"},
                actor="teacher-a",
                gitea=gitea,
            )
            pr = next(item for item in audited["pullRequests"] if item["number"] == 3)
            self.assertEqual(pr["teacherReviewStatus"], "approved")
            self.assertEqual(pr["status"], "merged")
            self.assertEqual(len(gitea.merged_prs), 1)

            evaluated = evaluate_team_contribution(
                db,
                created["id"],
                {
                    "scores": [
                        {"memberId": "赵队", "score": 92, "contribution": 45, "comment": "组织协调清晰"},
                        {"memberId": "李明", "score": 96, "contribution": 55, "comment": "核心代码质量高"},
                    ],
                    "summary": "团队完成度高，PR 流程闭环清晰。",
                },
                actor="teacher-a",
            )
            self.assertEqual(evaluated["teacherEvaluation"]["summary"], "团队完成度高，PR 流程闭环清晰。")
            ranking = evaluated["teamSummary"]["contributionRanking"]
            self.assertEqual(ranking[0]["name"], "李明")
            self.assertEqual(ranking[0]["contribution"], 55)
        finally:
            db.close()

    def test_created_project_has_repository_home_and_mock_clone_warning(self):
        db = self.SessionLocal()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "仓库主页演示",
                    "course": "软件工程综合实训",
                    "teamName": "Repo Home Team",
                    "description": "系统内仓库主页演示。",
                    "members": ["张华", "李明"],
                },
                actor="张华",
            )

            home = get_repository_home(
                db,
                created["id"],
                actor={"username": "李明", "role": "student", "className": "计科 2301"},
            )

            self.assertEqual(home["repoName"], created["repository"]["repoName"])
            self.assertTrue(home["cloneUrlMockOnly"])
            self.assertIn("files", home)
            self.assertIn("teacherFeedbackUpdatedAt", home)
            self.assertIn("teacherFeedbackUpdatedBy", home)
        finally:
            db.close()

    def test_teacher_feedback_records_updated_by_and_updated_at(self):
        db = self.SessionLocal()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "教师反馈演示",
                    "course": "数据结构",
                    "teamName": "Feedback Team",
                    "description": "教师反馈需要同步给学生。",
                    "members": ["张华", "李明"],
                    "className": "计科 2301",
                },
                actor="张华",
            )

            updated = update_repository_feedback(
                db,
                created["id"],
                {"teacherComment": "结构清晰。", "revisionSuggestions": "补充单元测试。"},
                actor={"username": "teacher-a", "role": "teacher", "className": "计科 2301"},
            )

            self.assertEqual(updated["teacherComment"], "结构清晰。")
            self.assertEqual(updated["revisionSuggestions"], "补充单元测试。")
            self.assertEqual(updated["teacherFeedbackUpdatedBy"], "teacher-a")
            self.assertTrue(updated["teacherFeedbackUpdatedAt"])
        finally:
            db.close()

    def test_student_scope_filters_to_joined_projects_even_if_viewer_claims_teacher(self):
        db = self.SessionLocal()
        try:
            mine = create_collaboration_project(
                db,
                {"title": "我的项目", "teamName": "Mine", "members": ["李明"], "course": "数据结构"},
                actor="李明",
            )
            create_collaboration_project(
                db,
                {"title": "其他项目", "teamName": "Other", "members": ["王磊"], "course": "数据结构"},
                actor="王磊",
            )

            projects = list_collaboration_projects(
                db,
                actor={"username": "李明", "role": "student", "className": "计科 2301"},
                scope="my",
                viewer="teacher",
            )

            self.assertEqual([item["id"] for item in projects], [mine["id"]])
        finally:
            db.close()

    def test_member_search_prefers_same_class_real_users_then_mock_fallback(self):
        db = self.SessionLocal()
        try:
            db.add(
                UserAccount(
                    username="liming",
                    role="student",
                    real_name="李明",
                    student_id="20230001",
                    class_name="计科 2301",
                    password_hash=hash_password("123456"),
                )
            )
            db.add(
                UserAccount(
                    username="other",
                    role="student",
                    real_name="外班同学",
                    student_id="20239999",
                    class_name="计科 2302",
                    password_hash=hash_password("123456"),
                )
            )
            db.commit()

            real_results = search_team_members(
                db,
                "20230001",
                actor={"username": "teacher-a", "role": "teacher", "className": "计科 2301"},
                class_name="计科 2301",
            )
            self.assertEqual(real_results[0]["studentId"], "20230001")
            self.assertEqual(real_results[0]["className"], "计科 2301")

            mock_results = search_team_members(
                db,
                "20230004",
                actor={"username": "teacher-a", "role": "teacher", "className": "计科 2301"},
                class_name="计科 2301",
            )
            self.assertTrue(mock_results)
            self.assertTrue(all(item["source"] == "mock" for item in mock_results))
        finally:
            db.close()

    def test_backfill_repository_home_updates_existing_records(self):
        db = self.SessionLocal()
        try:
            created = create_collaboration_project(
                db,
                {"title": "旧数据", "teamName": "Legacy", "members": ["李明"], "course": "软件工程"},
                actor="李明",
            )
            with self.engine.begin() as conn:
                conn.execute(
                    DomainRecord.__table__.update()
                    .where(DomainRecord.record_key == created["id"])
                    .values(
                        payload=(
                            '{"id":"%s","project":{"title":"旧数据","course":"软件工程","teamName":"Legacy",'
                            '"description":"旧数据"},"repository":{"repoName":"legacy",'
                            '"cloneUrl":"https://git.gezhi.local/campus/legacy.git","status":"created"},'
                            '"memberProgress":[{"name":"李明"}],"pullRequests":[],"recentCommits":[],"gitEvents":[]}'
                        )
                        % created["id"]
                    )
                )

            changed = backfill_repository_home_records(db)
            home = get_repository_home(
                db,
                created["id"],
                actor={"username": "李明", "role": "student", "className": "计科 2301"},
            )

            self.assertGreaterEqual(changed, 1)
            self.assertEqual(home["repoName"], "legacy")
            self.assertTrue(home["cloneUrlMockOnly"])
        finally:
            db.close()

    def test_get_team_repository_tree_returns_gitea_directory_entries(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        actor = {"username": "李明", "role": "student", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {"title": "团队文件浏览", "teamName": "Team A", "members": ["李明"], "repoName": "team-files"},
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            gitea.contents["campus/team-files:"] = [
                {"name": "README.md", "path": "README.md", "type": "file", "sha": "abc", "size": 120},
                {"name": "src", "path": "src", "type": "dir", "sha": "def", "size": 0},
            ]
            gitea.contents["campus/team-files:src"] = [
                {"name": "main.py", "path": "src/main.py", "type": "file", "sha": "ghi", "size": 88},
            ]

            root = get_team_repository_tree(db, created["id"], path="", actor=actor, gitea=gitea)
            nested = get_team_repository_tree(db, created["id"], path="src", actor=actor, gitea=gitea)

            self.assertEqual(root["path"], "")
            self.assertEqual(len(root["entries"]), 2)
            self.assertEqual(nested["entries"][0]["path"], "src/main.py")
        finally:
            db.close()

    def test_get_team_repository_blob_returns_text_preview(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        actor = {"username": "李明", "role": "student", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {"title": "团队文件预览", "teamName": "Team B", "members": ["李明"], "repoName": "team-preview"},
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            gitea.files["campus/team-preview:README.md"] = {
                "path": "README.md",
                "name": "README.md",
                "encoding": "text",
                "content": "# Team README\n",
                "size": 16,
                "previewable": True,
            }

            blob = get_team_repository_blob(db, created["id"], path="README.md", actor=actor, gitea=gitea)

            self.assertEqual(blob["path"], "README.md")
            self.assertTrue(blob["previewable"])
            self.assertIn("Team README", blob["content"])
        finally:
            db.close()

    def test_get_team_repository_languages_returns_percentages(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        actor = {"username": "李明", "role": "student", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {"title": "团队语言统计", "teamName": "Team C", "members": ["李明"], "repoName": "team-lang"},
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            gitea.languages["campus/team-lang"] = {"Python": 60.0, "Markdown": 40.0}

            result = get_team_repository_languages(db, created["id"], actor=actor, gitea=gitea)

            self.assertEqual(result[0]["name"], "Python")
            self.assertEqual(result[0]["percent"], 60.0)
        finally:
            db.close()

    def test_get_repository_home_with_real_readme_from_gitea(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        actor = {"username": "teacher-a", "role": "teacher", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {"title": "真实 README 演示", "teamName": "Readme Team", "members": ["李明"], "repoName": "team-readme", "className": "计科 2301"},
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            gitea.readmes["campus/team-readme"] = "# 真实 README\n\n来自 Gitea 的内容。"

            home = get_repository_home(db, created["id"], actor=actor, gitea=gitea)

            self.assertIn("真实 README", home["readme"])
            self.assertIn("来自 Gitea", home["readme"])
        finally:
            db.close()

    def test_get_repository_home_readme_fallback_when_gitea_disabled(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        gitea.enabled = False
        actor = {"username": "teacher-a", "role": "teacher", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {"title": "Fallback 演示", "teamName": "Fallback Team", "members": ["李明"], "repoName": "team-fallback", "className": "计科 2301"},
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)

            home = get_repository_home(db, created["id"], actor=actor, gitea=gitea)

            # Gitea 未启用时应回退到存储的 mock 值
            self.assertTrue(home["readme"])
            self.assertNotIn("来自 Gitea", home["readme"])
        finally:
            db.close()

    def test_get_repository_home_class_diagram_from_gitea_file(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        actor = {"username": "teacher-a", "role": "teacher", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {"title": "类图文件演示", "teamName": "Diagram Team", "members": ["李明"], "repoName": "team-diagram", "className": "计科 2301"},
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            gitea.files["campus/team-diagram:class-diagram.md"] = {
                "path": "class-diagram.md",
                "name": "class-diagram.md",
                "encoding": "text",
                "content": "User -> Order -> Product",
                "size": 24,
                "previewable": True,
            }

            home = get_repository_home(db, created["id"], actor=actor, gitea=gitea)

            self.assertEqual(home["classDiagram"], "User -> Order -> Product")
        finally:
            db.close()

    def test_get_repository_home_class_diagram_fallback_to_stored(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        actor = {"username": "teacher-a", "role": "teacher", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {"title": "类图回退演示", "teamName": "Diagram Fallback", "members": ["李明"], "repoName": "team-diagram-fb", "className": "计科 2301"},
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            # 不设置任何类图文件，应回退到存储值

            home = get_repository_home(db, created["id"], actor=actor, gitea=gitea)

            # 存储的默认类图
            self.assertTrue(home["classDiagram"])
            self.assertNotEqual(home["classDiagram"], "User -> Order -> Product")
        finally:
            db.close()

    def test_get_repository_home_clone_url_mock_only_flag(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        actor = {"username": "teacher-a", "role": "teacher", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {"title": "Clone 地址演示", "teamName": "Clone Team", "members": ["李明"], "repoName": "team-clone", "className": "计科 2301"},
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)

            home = get_repository_home(db, created["id"], actor=actor, gitea=gitea)

            # 仓库创建后有真实 cloneUrl，cloneUrlMockOnly 应为 False
            self.assertFalse(home["cloneUrlMockOnly"])
            self.assertTrue(home["cloneUrl"])
        finally:
            db.close()

    def test_sync_project_from_gitea_upserts_prs_commits_and_issues(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        actor = {"username": "teacher-a", "role": "teacher", "className": "计科 2301"}
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "同步对账项目",
                    "teamName": "Sync Team",
                    "members": ["李明", "王磊"],
                    "leaderId": "李明",
                    "repoName": "team-sync",
                    "className": "计科 2301",
                },
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            gitea.pull_requests = [
                {
                    "number": 9,
                    "title": "feat: sync pr",
                    "status": "open",
                    "creator": "liming",
                    "sourceBranch": "feature/sync",
                    "targetBranch": "main",
                    "url": "https://git.example.edu/campus/team-sync/pulls/9",
                    "updatedAt": "2026-07-10T10:00:00Z",
                    "createdAt": "2026-07-10T09:00:00Z",
                }
            ]
            gitea.commits = [
                {
                    "sha": "abc123def",
                    "message": "push for sync",
                    "authorName": "李明",
                    "authorEmail": "liming@example.com",
                    "authorLogin": "liming",
                    "time": "2026-07-10T08:00:00Z",
                    "url": "",
                }
            ]
            gitea.issues = [
                {
                    "number": 3,
                    "title": "实现压缩模块",
                    "body": "负责人：李明\n分支：feature/compress",
                    "state": "open",
                    "assignees": ["liming"],
                }
            ]
            db.add(
                UserAccount(
                    username="liming",
                    password_hash=hash_password("x"),
                    role="student",
                    real_name="李明",
                    student_id="20230002",
                    class_name="计科 2301",
                )
            )
            db.add(
                GiteaAccountBinding(
                    campus_user_id="liming",
                    gitea_username="liming",
                    gitea_email="liming@example.com",
                    role="student",
                    student_id="20230002",
                    class_name="计科 2301",
                    sync_status="active",
                )
            )
            db.commit()

            synced = sync_project_from_gitea(db, created["id"], actor=actor, gitea=gitea)
            self.assertEqual(len(synced["pullRequests"]), 1)
            self.assertEqual(synced["pullRequests"][0]["number"], 9)
            self.assertTrue(any(item.get("sha") == "abc123def" for item in synced["recentCommits"]))
            liming = next(item for item in synced["memberProgress"] if item["name"] == "李明")
            self.assertEqual(liming["prStatus"], "open")
            self.assertEqual(liming["pushStatus"], "detected")
            self.assertEqual(liming["task"], "实现压缩模块")
            self.assertEqual(int(liming.get("giteaIssueNumber") or 0), 3)
            self.assertTrue(synced["repository"].get("lastSyncedAt"))
            self.assertFalse(synced["repository"].get("syncError"))
        finally:
            db.close()

    def test_assign_member_task_creates_gitea_issue_before_save(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "任务 Issue 项目",
                    "teamName": "Issue Team",
                    "members": ["李明"],
                    "leaderId": "李明",
                    "repoName": "team-issue",
                    "className": "计科 2301",
                },
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            result = assign_member_task(
                db,
                created["id"],
                "李明",
                {"task": "完成 Huffman 编码", "branch": "feature/huffman"},
                actor="teacher-a",
                gitea=gitea,
            )
            liming = next(item for item in result["memberProgress"] if item["name"] == "李明")
            self.assertEqual(liming["task"], "完成 Huffman 编码")
            self.assertGreater(int(liming.get("giteaIssueNumber") or 0), 0)
            self.assertEqual(len(gitea.created_issues), 1)
            self.assertEqual(gitea.created_issues[0]["title"], "完成 Huffman 编码")
        finally:
            db.close()

    def test_teacher_merge_calls_gitea_before_local_status(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "Merge 项目",
                    "teamName": "Merge Team",
                    "members": ["李明"],
                    "leaderId": "李明",
                    "repoName": "team-merge",
                    "className": "计科 2301",
                },
                actor="李明",
            )
            create_project_repository(db, created["id"], actor="teacher-a", gitea=gitea)
            apply_gitea_webhook(
                db,
                created["id"],
                {
                    "hook_name": "pull_request",
                    "action": "opened",
                    "number": 5,
                    "sender": "liming",
                    "pull_request": {
                        "number": 5,
                        "title": "feat: merge me",
                        "user": {"login": "liming"},
                        "head": {"ref": "feature/x"},
                        "base": {"ref": "main"},
                        "merged": False,
                    },
                },
            )
            gitea.pull_requests = [{"number": 5, "status": "open", "merged": False, "state": "open"}]
            merged = review_pull_request(
                db,
                created["id"],
                5,
                {"action": "teacher_approve", "comment": "LGTM"},
                actor="teacher-a",
                gitea=gitea,
            )
            self.assertEqual(len(gitea.merged_prs), 1)
            pr = next(item for item in merged["pullRequests"] if item["number"] == 5)
            self.assertEqual(pr["status"], "merged")

            gitea.merge_should_fail = True
            apply_gitea_webhook(
                db,
                created["id"],
                {
                    "hook_name": "pull_request",
                    "action": "opened",
                    "number": 6,
                    "sender": "liming",
                    "pull_request": {
                        "number": 6,
                        "title": "feat: fail merge",
                        "user": {"login": "liming"},
                        "head": {"ref": "feature/y"},
                        "base": {"ref": "main"},
                        "merged": False,
                    },
                },
            )
            with self.assertRaises(RuntimeError):
                review_pull_request(
                    db,
                    created["id"],
                    6,
                    {"action": "teacher_approve", "comment": "should fail"},
                    actor="teacher-a",
                    gitea=gitea,
                )
            after = get_collaboration_project(db, created["id"], actor="李明")
            pr6 = next(item for item in after["pullRequests"] if item["number"] == 6)
            self.assertNotEqual(pr6.get("status"), "merged")
        finally:
            db.close()

    def test_leader_merge_calls_gitea_and_updates_local_state(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "队长合并项目",
                    "teamName": "Leader Merge Team",
                    "members": ["队长", "成员A"],
                    "leaderId": "队长",
                    "repoName": "leader-merge",
                    "className": "计科 2301",
                },
                actor="队长",
            )
            create_project_repository(db, created["id"], actor="队长", gitea=gitea)
            apply_gitea_webhook(
                db,
                created["id"],
                {
                    "hook_name": "pull_request",
                    "action": "opened",
                    "number": 9,
                    "sender": "member-a",
                    "pull_request": {
                        "number": 9,
                        "title": "feat: member implementation",
                        "user": {"login": "member-a"},
                        "head": {"ref": "feature/member-a"},
                        "base": {"ref": "main"},
                        "merged": False,
                    },
                },
            )
            gitea.pull_requests = [{"number": 9, "status": "open", "merged": False, "state": "open"}]

            merged = review_pull_request(
                db,
                created["id"],
                9,
                {"action": "approve_merge", "comment": "队长审核通过。"},
                actor="队长",
                gitea=gitea,
            )

            self.assertEqual(len(gitea.merged_prs), 1)
            self.assertEqual(gitea.merged_prs[0]["index"], 9)
            pr = next(item for item in merged["pullRequests"] if item["number"] == 9)
            self.assertEqual(pr["status"], "merged")
            self.assertEqual(pr["leaderReviewStatus"], "approved")
            self.assertEqual(pr["leaderReviewer"], "队长")
            self.assertEqual(pr["reviewComment"], "队长审核通过。")
        finally:
            db.close()

    def test_regular_member_cannot_merge_pull_request(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "成员越权合并项目",
                    "teamName": "No Merge Team",
                    "members": ["队长", "成员A"],
                    "leaderId": "队长",
                    "repoName": "member-no-merge",
                    "className": "计科 2301",
                },
                actor="队长",
            )
            create_project_repository(db, created["id"], actor="队长", gitea=gitea)
            apply_gitea_webhook(
                db,
                created["id"],
                {
                    "type": "pull_request",
                    "action": "opened",
                    "sender": "成员A",
                    "number": 10,
                    "title": "feat: protected branch update",
                    "sourceBranch": "feature/member-a",
                    "targetBranch": "main",
                },
            )

            with self.assertRaises(PermissionError):
                review_pull_request(
                    db,
                    created["id"],
                    10,
                    {"action": "approve_merge", "comment": "我自己合并。"},
                    actor="成员A",
                    gitea=gitea,
                )

            self.assertEqual(gitea.merged_prs, [])
            after = get_collaboration_project(db, created["id"], actor="队长")
            pr = next(item for item in after["pullRequests"] if item["number"] == 10)
            self.assertEqual(pr["status"], "open")
        finally:
            db.close()

    def test_merge_timeout_after_gitea_success_is_treated_as_merged(self):
        db = self.SessionLocal()
        gitea = FakeGiteaService()
        try:
            created = create_collaboration_project(
                db,
                {
                    "title": "超时回查合并项目",
                    "teamName": "Timeout Merge Team",
                    "members": ["队长", "成员A"],
                    "leaderId": "队长",
                    "repoName": "timeout-merge",
                    "className": "计科 2301",
                },
                actor="队长",
            )
            create_project_repository(db, created["id"], actor="队长", gitea=gitea)
            apply_gitea_webhook(
                db,
                created["id"],
                {
                    "type": "pull_request",
                    "action": "opened",
                    "sender": "成员A",
                    "number": 11,
                    "title": "feat: timeout merged branch",
                    "sourceBranch": "feature/member-a",
                    "targetBranch": "main",
                },
            )
            gitea.pull_requests = [{"number": 11, "status": "open", "merged": False, "state": "open"}]
            gitea.merge_raises_after_success = True

            merged = review_pull_request(
                db,
                created["id"],
                11,
                {"action": "approve_merge", "comment": "Gitea 已合并但响应超时。"},
                actor="队长",
                gitea=gitea,
            )

            pr = next(item for item in merged["pullRequests"] if item["number"] == 11)
            self.assertEqual(pr["status"], "merged")
            self.assertEqual(pr["leaderReviewStatus"], "approved")
            self.assertEqual(pr["reviewComment"], "Gitea 已合并但响应超时。")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
