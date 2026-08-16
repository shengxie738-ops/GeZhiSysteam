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

from app.core.security import create_access_token
from app.models.gitea_account_binding import GiteaAccountBinding
from app.models.user_account import UserAccount, hash_password
from app.api.endpoints.gitea_accounts import resolve_account_from_authorization, get_gitea_me_payload


class GiteaAccountsApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        GiteaAccountBinding.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_resolve_account_from_bearer_token(self):
        db = self.SessionLocal()
        try:
            db.add(UserAccount(username="20260001", role="student", student_id="20260001", real_name="张三", password_hash=hash_password("123456")))
            db.commit()
            token = create_access_token("20260001", "student")
            account = resolve_account_from_authorization(db, f"Bearer {token}")
            self.assertEqual(account.username, "20260001")
        finally:
            db.close()

    def test_get_gitea_me_payload_returns_git_config(self):
        db = self.SessionLocal()
        try:
            account = UserAccount(username="20260001", role="student", student_id="20260001", real_name="张三", password_hash=hash_password("123456"))
            db.add(account)
            db.commit()
            payload = get_gitea_me_payload(db, account)
            self.assertEqual(payload["giteaUsername"], "stu_20260001")
            self.assertIn('git config user.name "20260001"', payload["gitConfigCommands"][0])
            self.assertIn('git config user.email "20260001@gezhi.local"', payload["gitConfigCommands"][1])
        finally:
            db.close()
