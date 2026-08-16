import asyncio
import os
import unittest
from io import BytesIO

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers

from app.api.endpoints.user_center import UserInfoUpdate, update_user_info, upload_avatar
from app.models.user_account import UserAccount


class UserCenterEndpointTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self.username = "user_center_test"
        self.avatar_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app",
            "static",
            "avatars",
            f"{self.username}.png",
        )
        if os.path.exists(self.avatar_path):
            os.remove(self.avatar_path)

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.avatar_path):
            os.remove(self.avatar_path)

    def test_update_user_info_persists_to_user_accounts(self):
        self.db.add(UserAccount(username=self.username, role="student", password_hash=""))
        self.db.commit()

        response = asyncio.run(
            update_user_info(
                UserInfoUpdate(
                    username=self.username,
                    real_name="  张三  ",
                    student_id=" 20260001 ",
                    class_name=" 计科一班 ",
                ),
                self.db,
            )
        )

        account = self.db.query(UserAccount).filter_by(username=self.username).one()
        self.assertEqual(account.real_name, "张三")
        self.assertEqual(account.student_id, "20260001")
        self.assertEqual(account.class_name, "计科一班")
        self.assertEqual(response["user"]["real_name"], "张三")
        self.assertEqual(response["user"]["student_id"], "20260001")
        self.assertEqual(response["user"]["class_name"], "计科一班")

    def test_upload_avatar_persists_path_and_returns_syncable_user(self):
        upload = UploadFile(
            filename="avatar.png",
            file=BytesIO(b"\x89PNG\r\n\x1a\nsmall-test-image"),
            headers=Headers({"content-type": "image/png"}),
        )

        response = asyncio.run(upload_avatar(username=self.username, file=upload, db=self.db))

        account = self.db.query(UserAccount).filter_by(username=self.username).one()
        self.assertEqual(account.avatar_path, f"{self.username}.png")
        self.assertTrue(os.path.exists(self.avatar_path))
        self.assertEqual(response["avatar_url"], f"/static/avatars/{self.username}.png")
        self.assertEqual(response["user"]["avatar_url"], f"/static/avatars/{self.username}.png")


if __name__ == "__main__":
    unittest.main()
