import os
import hmac
import hashlib
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

from app.api.endpoints.team_git import resolve_team_git_actor, verify_gitea_signature
from app.core.security import create_access_token
from app.models.user_account import UserAccount, hash_password


class TeamGitApiSecurityTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_actor_comes_from_token_not_viewer_query(self):
        db = self.SessionLocal()
        try:
            db.add(
                UserAccount(
                    username="student-a",
                    role="student",
                    real_name="学生A",
                    student_id="20230001",
                    class_name="计科 2301",
                    password_hash=hash_password("123456"),
                )
            )
            db.commit()
            token = create_access_token("student-a", "student")

            actor = resolve_team_git_actor(f"Bearer {token}", db, fallback_username="viewer-teacher")

            self.assertEqual(actor["username"], "student-a")
            self.assertEqual(actor["role"], "student")
            self.assertEqual(actor["className"], "计科 2301")
        finally:
            db.close()

    def test_gitea_webhook_signature_requires_matching_hmac_sha256(self):
        body = b'{"hook_name":"push","commits":[]}'
        secret = "local-webhook-secret"
        valid = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        self.assertTrue(verify_gitea_signature(body, secret, valid))
        self.assertFalse(verify_gitea_signature(body, secret, "bad-signature"))
        self.assertFalse(verify_gitea_signature(body, "", valid))
        self.assertFalse(verify_gitea_signature(body, secret, ""))


if __name__ == "__main__":
    unittest.main()
