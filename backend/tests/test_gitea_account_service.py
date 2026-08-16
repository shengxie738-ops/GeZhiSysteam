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

from app.models.gitea_account_binding import GiteaAccountBinding
from app.models.user_account import UserAccount
from app.services.gitea_service import GiteaService
from app.services.gitea_account_service import (
    GiteaTokenError,
    RepoPermission,
    create_or_rotate_gitea_token,
    ensure_gitea_account_for_user,
    ensure_repository_collaborators,
    get_gitea_binding_summary,
    gitea_email_for_account,
    gitea_username_for_account,
    match_campus_user_from_gitea_event,
)


class GiteaAccountBindingModelTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        GiteaAccountBinding.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_binding_persists_required_mapping_fields(self):
        db = self.SessionLocal()
        try:
            db.add(
                GiteaAccountBinding(
                    campus_user_id="20260001",
                    role="student",
                    student_id="20260001",
                    teacher_id="",
                    class_name="计科2601",
                    gitea_user_id=101,
                    gitea_username="stu_20260001",
                    gitea_email="20260001@gezhi.local",
                    token_last_four="abcd",
                    sync_status="synced",
                    sync_error="",
                )
            )
            db.commit()
            item = db.query(GiteaAccountBinding).filter_by(campus_user_id="20260001").one()
            self.assertEqual(item.gitea_username, "stu_20260001")
            self.assertEqual(item.student_id, "20260001")
            self.assertEqual(item.gitea_user_id, 101)
            self.assertEqual(item.sync_status, "synced")
        finally:
            db.close()


class GiteaServiceMockModeTest(unittest.TestCase):
    def test_repository_urls_use_configured_gitea_proxy_and_ssh_port(self):
        service = GiteaService(
            enabled=False,
            token="",
            org="campus",
            public_base_url="https://gezhisystem.com/gitea",
            ssh_domain="gezhisystem.com",
            ssh_port=2222,
        )

        repo = service.create_repository(name="Mini Vue Reactive Runtime", private=False, auto_init=True)

        self.assertEqual(repo["giteaOwner"], "campus")
        self.assertEqual(repo["giteaRepo"], "mini-vue-reactive-runtime")
        self.assertEqual(repo["htmlUrl"], "https://gezhisystem.com/gitea/campus/mini-vue-reactive-runtime")
        self.assertEqual(repo["cloneUrl"], "https://gezhisystem.com/gitea/campus/mini-vue-reactive-runtime.git")
        self.assertEqual(repo["sshUrl"], "ssh://git@gezhisystem.com:2222/campus/mini-vue-reactive-runtime.git")

    def test_create_user_returns_mock_payload_when_disabled(self):
        service = GiteaService(enabled=False, token="", org="campus")
        user = service.create_user(
            username="stu_20260001",
            email="20260001@gezhi.local",
            full_name="张三",
            password="generated-password",
        )
        self.assertEqual(user["login"], "stu_20260001")
        self.assertEqual(user["email"], "20260001@gezhi.local")
        self.assertIsNone(user["id"])

    def test_mock_token_is_deterministic_shape(self):
        service = GiteaService(enabled=False, token="", org="campus")
        token = service.create_user_token("stu_20260001", "campus-learning-system")
        self.assertTrue(token.startswith("mock-gitea-token-stu_20260001-"))

    def test_create_user_token_uses_basic_auth_for_target_user(self):
        service = GiteaService(enabled=True, base_url="http://gitea.test", token="admin-token", org="campus")
        captured: dict = {}

        class FakeResponse:
            status_code = 201

            @staticmethod
            def json():
                return {"sha1": "abc123token", "token_last_eight": "23token"}

            def raise_for_status(self):
                return None

        def fake_patch(url, json=None, headers=None, timeout=None):
            captured["patch_url"] = url
            return FakeResponse()

        def fake_post(url, json=None, headers=None, auth=None, timeout=None):
            captured["url"] = url
            captured["auth"] = auth
            captured["json"] = json
            return FakeResponse()

        def fake_get(url, headers=None, auth=None, timeout=None):
            class ListResponse:
                status_code = 200

                @staticmethod
                def json():
                    return []

                def raise_for_status(self):
                    return None

            return ListResponse()

        import app.services.gitea_service as gitea_module

        original_post = gitea_module.requests.post
        original_get = gitea_module.requests.get
        original_patch = gitea_module.requests.patch
        try:
            gitea_module.requests.patch = fake_patch
            gitea_module.requests.post = fake_post
            gitea_module.requests.get = fake_get
            token = service.create_user_token("stu_20260001", "campus-learning-system")
            self.assertEqual(token, "abc123token")
            self.assertEqual(getattr(captured["auth"], "username", None), "stu_20260001")
            self.assertIn("/api/v1/users/stu_20260001/tokens", captured["url"])
        finally:
            gitea_module.requests.post = original_post
            gitea_module.requests.get = original_get
            gitea_module.requests.patch = original_patch

    def test_create_repository_adopts_existing_org_repo(self):
        service = GiteaService(
            enabled=True,
            base_url="http://gitea.test",
            public_base_url="http://localhost:3000",
            token="admin-token",
            org="campus",
        )
        calls: list[tuple[str, str]] = []

        class ConflictResponse:
            status_code = 409
            text = "repository already exists"
            content = b"repository already exists"

            def raise_for_status(self):
                from requests import HTTPError

                raise HTTPError("409 repository already exists")

        class RepoResponse:
            status_code = 200
            content = b"{}"

            @staticmethod
            def json():
                return {
                    "name": "team-real-loop",
                    "default_branch": "main",
                    "owner": {"login": "campus"},
                }

            def raise_for_status(self):
                return None

        def fake_post(url, json=None, headers=None, timeout=None):
            calls.append(("post", url))
            return ConflictResponse()

        def fake_get(url, headers=None, auth=None, timeout=None, params=None):
            calls.append(("get", url))
            return RepoResponse()

        import app.services.gitea_service as gitea_module

        original_post = gitea_module.requests.post
        original_get = gitea_module.requests.get
        try:
            gitea_module.requests.post = fake_post
            gitea_module.requests.get = fake_get
            repo = service.create_repository(name="team-real-loop", private=True, auto_init=True)

            self.assertEqual(repo["giteaOwner"], "campus")
            self.assertEqual(repo["giteaRepo"], "team-real-loop")
            self.assertEqual(repo["cloneUrl"], "http://localhost:3000/campus/team-real-loop.git")
            self.assertIn(("get", "http://gitea.test/api/v1/repos/campus/team-real-loop"), calls)
        finally:
            gitea_module.requests.post = original_post
            gitea_module.requests.get = original_get


class FakeCampusGitea:
    def create_user(self, *, username, email, full_name="", password="", must_change_password=False, visibility="private"):
        self.users[username] = {"id": len(self.users) + 1, "login": username, "email": email, "full_name": full_name}
        return self.users[username]

    def ensure_org_membership(self, username, role="member"):
        self.members.append({"username": username, "role": role})
        return True

    def add_repository_collaborator(self, *, owner, repo, username, permission="write"):
        self.collaborators.append({"owner": owner, "repo": repo, "username": username, "permission": permission})
        return True

    def create_user_token(self, username, token_name="campus-learning-system"):
        self.delete_user_token_by_name(username, token_name)
        token = f"token-for-{username}"
        self.tokens.append({"username": username, "token_name": token_name})
        return token

    def delete_user_token_by_name(self, username, token_name="campus-learning-system"):
        self.tokens = [item for item in self.tokens if not (item["username"] == username and item["token_name"] == token_name)]

    def __init__(self):
        self.users = {}
        self.members = []
        self.collaborators = []
        self.tokens = []


class GiteaAccountServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        GiteaAccountBinding.__table__.create(bind=self.engine)
        UserAccount.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_student_username_uses_stu_student_id(self):
        account = UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001")
        self.assertEqual(gitea_username_for_account(account), "stu_20260001")
        self.assertEqual(gitea_email_for_account(account), "20260001@gezhi.local")

    def test_teacher_username_uses_tea_teacher_id(self):
        account = UserAccount(username="teacher_chen", role="teacher", real_name="陈老师", teacher_id="T2026")
        self.assertEqual(gitea_username_for_account(account), "tea_T2026")
        self.assertEqual(gitea_email_for_account(account), "teacher_T2026@gezhi.local")

    def test_ensure_gitea_account_creates_binding_and_org_member(self):
        db = self.SessionLocal()
        gitea = FakeCampusGitea()
        try:
            account = UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001", class_name="计科2601")
            db.add(account)
            db.commit()
            identity = ensure_gitea_account_for_user(db, account, gitea=gitea)
            self.assertEqual(identity.gitea_username, "stu_20260001")
            self.assertEqual(identity.gitea_user_id, 1)
            self.assertEqual(identity.sync_status, "synced")
            self.assertEqual(gitea.members, [{"username": "stu_20260001", "role": "member"}])
        finally:
            db.close()

    def test_rotate_token_returns_plain_once_and_stores_last_four(self):
        db = self.SessionLocal()
        gitea = FakeCampusGitea()
        try:
            account = UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001")
            db.add(account)
            db.commit()
            result = create_or_rotate_gitea_token(db, account, gitea=gitea)
            self.assertEqual(result.gitea_username, "stu_20260001")
            self.assertEqual(result.token, "token-for-stu_20260001")
            self.assertEqual(result.token_last_four, "0001")
        finally:
            db.close()

    def test_ensure_repository_collaborators_adds_permissions(self):
        db = self.SessionLocal()
        gitea = FakeCampusGitea()
        try:
            leader = UserAccount(username="20260001", role="student", real_name="队长", student_id="20260001")
            member = UserAccount(username="20260002", role="student", real_name="队员", student_id="20260002")
            teacher = UserAccount(username="teacher_chen", role="teacher", real_name="陈老师", teacher_id="T2026")
            db.add_all([leader, member, teacher])
            db.commit()
            ensure_repository_collaborators(
                db,
                "campus",
                "team-demo",
                [
                    RepoPermission("20260001", "admin", "leader"),
                    RepoPermission("20260002", "write", "member"),
                    RepoPermission("teacher_chen", "admin", "teacher"),
                ],
                gitea=gitea,
            )
            self.assertEqual(
                gitea.collaborators,
                [
                    {"owner": "campus", "repo": "team-demo", "username": "stu_20260001", "permission": "admin"},
                    {"owner": "campus", "repo": "team-demo", "username": "stu_20260002", "permission": "write"},
                    {"owner": "campus", "repo": "team-demo", "username": "tea_T2026", "permission": "admin"},
                ],
            )
        finally:
            db.close()

    def test_match_webhook_sender_by_gitea_username(self):
        db = self.SessionLocal()
        gitea = FakeCampusGitea()
        try:
            account = UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001")
            db.add(account)
            db.commit()
            ensure_gitea_account_for_user(db, account, gitea=gitea)
            match = match_campus_user_from_gitea_event(db, sender_username="stu_20260001", commit_author={})
            self.assertEqual(match["campusUserId"], "20260001")
            self.assertEqual(match["displayName"], "张三")
            self.assertEqual(match["matchSource"], "gitea_username")
        finally:
            db.close()

    def test_get_gitea_binding_summary_does_not_call_gitea_api(self):
        db = self.SessionLocal()
        try:
            account = UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001")
            db.add(account)
            db.commit()
            summary = get_gitea_binding_summary(db, account)
            self.assertEqual(summary["username"], "stu_20260001")
            self.assertEqual(summary["email"], "20260001@gezhi.local")
            self.assertEqual(summary["syncStatus"], "pending")
            self.assertEqual(summary["tokenLastFour"], "")
        finally:
            db.close()

    def test_ensure_skips_gitea_api_when_already_synced(self):
        class FailingGitea:
            def create_user(self, **kwargs):
                raise AssertionError("should not call create_user when already synced")

            def ensure_org_membership(self, *args, **kwargs):
                raise AssertionError("should not call ensure_org_membership when already synced")

        db = self.SessionLocal()
        try:
            account = UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001")
            db.add(account)
            db.add(
                GiteaAccountBinding(
                    campus_user_id="20260001",
                    role="student",
                    student_id="20260001",
                    gitea_user_id=99,
                    gitea_username="stu_20260001",
                    gitea_email="20260001@gezhi.local",
                    sync_status="synced",
                )
            )
            db.commit()
            identity = ensure_gitea_account_for_user(db, account, gitea=FailingGitea())
            self.assertEqual(identity.sync_status, "synced")
            self.assertEqual(identity.gitea_user_id, 99)
        finally:
            db.close()

    def test_teacher_gezhi_email_does_not_match_student_id(self):
        db = self.SessionLocal()
        try:
            db.add(UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001"))
            db.add(UserAccount(username="teacher_chen", role="teacher", real_name="陈老师", teacher_id="T2026"))
            db.commit()
            match = match_campus_user_from_gitea_event(
                db,
                sender_username="",
                commit_author={"email": "teacher_T2026@gezhi.local", "name": "陈老师"},
            )
            self.assertEqual(match["campusUserId"], "teacher_chen")
            self.assertEqual(match["matchSource"], "teacher_email")
        finally:
            db.close()

    def test_create_or_rotate_token_raises_gitea_token_error(self):
        class BrokenGitea(FakeCampusGitea):
            def create_user_token(self, username, token_name="campus-learning-system"):
                raise RuntimeError("gitea token api failed")

        db = self.SessionLocal()
        gitea = BrokenGitea()
        try:
            account = UserAccount(username="20260001", role="student", real_name="张三", student_id="20260001")
            db.add(account)
            db.commit()
            with self.assertRaises(GiteaTokenError):
                create_or_rotate_gitea_token(db, account, gitea=gitea)
        finally:
            db.close()
