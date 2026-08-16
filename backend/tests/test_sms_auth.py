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
os.environ.setdefault("SMS_MOCK_ENABLED", "true")
os.environ.setdefault("SMS_SEND_COOLDOWN_SECONDS", "60")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.sms_verification_code import SmsVerificationCode
from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount
from app.core.security import get_password_hash
from app.core.config import settings
from app.api.endpoints.auth import MobileLoginRequest, RegisterRequest, _mobile_login, _register
from app.services.sms_service import send_sms_code, verify_sms_code


def _unwrap_response(response):
    """Unwrap a FastAPI JSONResponse to a plain dict for direct unit-test assertions.

    `auth_fail()` returns a ``JSONResponse`` (status 401) so that FastAPI endpoints
    can propagate the correct HTTP status code.  When the service function is called
    directly in a unit test (without a real HTTP client) the return value is the raw
    ``JSONResponse`` object, which is *not* subscriptable.  This helper normalises
    both cases so tests can do ``response["success"]`` regardless.
    """
    from fastapi.responses import JSONResponse
    import json
    if isinstance(response, JSONResponse):
        return json.loads(response.body)
    return response


class SmsServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        SmsVerificationCode.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        # Force mock mode so tests never call real Aliyun SMS API,
        # even when the production .env has SMS_MOCK_ENABLED=false.
        # (The settings singleton may have been loaded by an earlier test module.)
        self._orig_mock = settings.SMS_MOCK_ENABLED
        settings.SMS_MOCK_ENABLED = True

    def tearDown(self):
        settings.SMS_MOCK_ENABLED = self._orig_mock
        self.db.close()

    def test_send_sms_code_creates_database_record(self):
        ok, message, payload = send_sms_code(self.db, "13800138000", "register")

        self.assertTrue(ok, message)
        self.assertEqual(payload["mock"], True)
        self.assertRegex(payload["debug_code"], r"^\d{6}$")
        record = self.db.query(SmsVerificationCode).filter_by(phone="13800138000").one()
        self.assertEqual(record.purpose, "register")
        self.assertNotEqual(record.code_hash, payload["debug_code"])

    def test_sms_code_cannot_be_reused_after_successful_verify(self):
        ok, message, payload = send_sms_code(self.db, "13800138000", "register")
        self.assertTrue(ok, message)

        first_ok, first_message = verify_sms_code(self.db, "13800138000", "register", payload["debug_code"])
        second_ok, second_message = verify_sms_code(self.db, "13800138000", "register", payload["debug_code"])

        self.assertTrue(first_ok, first_message)
        self.assertFalse(second_ok)
        self.assertEqual(second_message, "验证码不存在或已失效")

    def test_sms_code_rejects_invalid_code_and_counts_attempt(self):
        ok, message, _ = send_sms_code(self.db, "13800138000", "login")
        self.assertTrue(ok, message)

        verified, verify_message = verify_sms_code(self.db, "13800138000", "login", "000000")

        self.assertFalse(verified)
        self.assertEqual(verify_message, "验证码错误")
        record = self.db.query(SmsVerificationCode).filter_by(phone="13800138000").one()
        self.assertEqual(record.attempts, 1)

    def test_send_sms_code_rejects_recent_duplicate_send(self):
        first_ok, first_message, _ = send_sms_code(self.db, "13800138000", "login")
        second_ok, second_message, _ = send_sms_code(self.db, "13800138000", "login")

        self.assertTrue(first_ok, first_message)
        self.assertFalse(second_ok)
        self.assertIn("请稍后再获取验证码", second_message)


class SmsAuthEndpointTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        UserAccount.__table__.create(bind=self.engine)
        StudentProfile.__table__.create(bind=self.engine)
        SmsVerificationCode.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        # Force mock mode for the same reason as SmsServiceTest.setUp.
        self._orig_mock = settings.SMS_MOCK_ENABLED
        settings.SMS_MOCK_ENABLED = True

    def tearDown(self):
        settings.SMS_MOCK_ENABLED = self._orig_mock
        self.db.close()

    def test_student_register_requires_sms_code(self):
        request = RegisterRequest(
            role="student",
            real_name="张三",
            student_id="20260001",
            class_name="计科一班",
            password="secret123",
            confirm_password="secret123",
            phone="13800138000",
        )

        response = _unwrap_response(_register(self.db, request, "student"))

        self.assertFalse(response["success"])
        self.assertEqual(response["message"], "请先完成手机号验证")

    def test_student_register_uses_student_id_as_username_after_sms_verify(self):
        _, _, payload = send_sms_code(self.db, "13800138000", "register")
        request = RegisterRequest(
            role="student",
            real_name="张三",
            student_id="20260001",
            class_name="计科一班",
            password="secret123",
            confirm_password="secret123",
            phone="13800138000",
            sms_code=payload["debug_code"],
        )

        response = _register(self.db, request, "student")

        self.assertTrue(response["success"])
        account = self.db.query(UserAccount).filter_by(username="20260001").one()
        self.assertEqual(account.student_id, "20260001")
        self.assertEqual(account.real_name, "张三")
        self.assertEqual(account.class_name, "计科一班")

    def test_mobile_login_returns_token_for_verified_student_phone(self):
        self.db.add(
            UserAccount(
                username="20260001",
                role="student",
                password_hash=get_password_hash("secret123"),
                phone="13800138000",
                real_name="张三",
                student_id="20260001",
                class_name="计科一班",
            )
        )
        self.db.commit()
        _, _, payload = send_sms_code(self.db, "13800138000", "login")

        response = _mobile_login(
            self.db,
            MobileLoginRequest(phone="13800138000", sms_code=payload["debug_code"], role="student"),
            "student",
        )

        self.assertTrue(response["success"])
        self.assertIn("token", response["data"])
        self.assertEqual(response["data"]["user"]["username"], "20260001")


if __name__ == "__main__":
    unittest.main()
