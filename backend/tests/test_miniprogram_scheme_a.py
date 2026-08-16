import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")


class MiniprogramResponseHelperTest(unittest.TestCase):
    def test_api_response_uses_scheme_a_code_zero(self):
        from app.core.miniprogram_response import api_response

        self.assertEqual(api_response({"ok": True}), {"code": 0, "message": "ok", "data": {"ok": True}})

    def test_client_header_detection_is_explicit(self):
        from app.core.miniprogram_response import is_miniprogram_client

        self.assertTrue(is_miniprogram_client("miniprogram"))
        self.assertTrue(is_miniprogram_client("wechat-miniprogram"))
        self.assertFalse(is_miniprogram_client(None))
        self.assertFalse(is_miniprogram_client("pc"))

    def test_isoformat_z_normalizes_datetime(self):
        from app.core.miniprogram_response import isoformat_z

        self.assertEqual(
            isoformat_z(datetime(2026, 7, 8, 10, 30, tzinfo=timezone.utc)),
            "2026-07-08T10:30:00Z",
        )

    def test_page_items_uses_cursor_after_last_item(self):
        from app.core.miniprogram_response import page_items

        items = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        page = page_items(items, cursor="a", limit=1)

        self.assertEqual(page["items"], [{"id": "b"}])
        self.assertEqual(page["nextCursor"], "b")


from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount
from app.models.domain_record import DomainRecord
from app.repositories.json_store import JsonStore


class MiniprogramAuthCompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        db = self.SessionLocal()
        db.add(
            UserAccount(
                username="24001020106",
                role="student",
                password_hash=get_password_hash("123456"),
                real_name="寮犲崕",
                student_id="24001020106",
                class_name="璁＄2301",
            )
        )
        db.add(StudentProfile(user_id="24001020106", knowledge=72, pace=65, cognitive="娓愯繘鐞嗚В鍨?"))
        db.commit()
        db.close()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=self.engine)

    def test_pc_login_shape_is_unchanged_without_miniprogram_header(self):
        response = self.client.post(
            "/api/student/login",
            json={"username": "24001020106", "password": "123456", "role": "student"},
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertIn("token", body["data"])

    def test_miniprogram_login_uses_code_zero_with_header(self):
        response = self.client.post(
            "/api/student/login",
            headers={"X-Gezhi-Client": "miniprogram"},
            json={"username": "24001020106", "password": "123456", "role": "student"},
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["message"], "ok")
        self.assertEqual(body["data"]["user"]["real_name"], "寮犲崕")
        self.assertIn("token", body["data"])


class MiniprogramProfileEndpointTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        db = self.SessionLocal()
        db.add(UserAccount(username="24001020106", role="student", password_hash="", real_name="寮犲崕", student_id="24001020106", class_name="璁＄2301"))
        db.add(StudentProfile(user_id="24001020106", knowledge=72, pace=65, cognitive="娓愯繘鐞嗚В鍨?", goal="鎺屾彙鏍稿績鏁版嵁缁撴瀯涓庣畻娉?"))
        db.commit()
        db.close()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=self.engine)

    def test_profile_detail_is_wrapped_for_miniprogram_only(self):
        pc = self.client.get("/api/profile/24001020106")
        mp = self.client.get("/api/profile/24001020106", headers={"X-Gezhi-Client": "miniprogram"})

        self.assertIn("user_id", pc.json())
        self.assertEqual(mp.json()["code"], 0)
        self.assertEqual(mp.json()["data"]["behavior"]["knowledge"], 72)

    def test_profile_summary_trends_and_knowledge_map(self):
        headers = {"X-Gezhi-Client": "miniprogram"}

        summary = self.client.get("/api/profile/summary?user_id=24001020106", headers=headers).json()["data"]
        trends = self.client.get("/api/profile/trends?user_id=24001020106&range=7d", headers=headers).json()["data"]
        knowledge_map = self.client.get("/api/profile/knowledge-map?user_id=24001020106", headers=headers).json()["data"]

        self.assertEqual(summary["userId"], "24001020106")
        self.assertEqual(summary["knowledgeScore"], 72)
        self.assertEqual(len(trends["knowledge"]), 7)
        self.assertEqual(knowledge_map["id"], "root")
        self.assertIn("children", knowledge_map)


class MiniprogramJournalEndpointTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=self.engine)

    def test_create_list_and_day_journal_events(self):
        headers = {"X-Gezhi-Client": "miniprogram"}
        created = self.client.post(
            "/api/journal/events",
            headers=headers,
            json={
                "userId": "24001020106",
                "type": "chat",
                "title": "AI Q&A",
                "summary": "Binary tree traversal",
                "relatedIds": ["101"],
                "tags": ["data-structures"],
                "scoreDelta": 2,
            },
        ).json()["data"]

        listed = self.client.get(
            "/api/journal/events?user_id=24001020106&limit=20&type=chat",
            headers=headers,
        ).json()["data"]
        by_day = self.client.get(
            f"/api/journal/events/day?user_id=24001020106&date={created['createdAt'][:10]}&cursor=&limit=20",
            headers=headers,
        ).json()

        self.assertEqual(created["type"], "chat")
        self.assertIsNotNone(datetime.fromisoformat(created["createdAt"].replace("Z", "+00:00")))
        self.assertEqual(listed["items"][0]["id"], created["id"])
        self.assertEqual(by_day["code"], 0)
        self.assertEqual(by_day["message"], "ok")
        self.assertIn("items", by_day["data"])
        self.assertIn("nextCursor", by_day["data"])
        self.assertEqual(by_day["data"]["items"][0]["id"], created["id"])
        self.assertEqual(by_day["data"]["nextCursor"], None)


class MiniprogramKnowledgeAliasTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=self.engine)

    def test_upload_alias_returns_scheme_a_response(self):
        with patch(
            "app.api.endpoints.user_knowledge.upload_document_to_repository",
            return_value={"id": "doc_1", "status": "parsing", "filename": "tree.pdf"},
        ):
            response = self.client.post(
                "/api/user/knowledge/upload",
                headers={"X-Gezhi-Client": "miniprogram"},
                data={"user_id": "24001020106", "repository_id": "repo_1"},
                files={"file": ("tree.pdf", b"tree", "application/pdf")},
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["message"], "ok")
        self.assertEqual(body["data"]["id"], "doc_1")

    def test_existing_documents_endpoint_returns_scheme_a_response(self):
        with patch(
            "app.api.endpoints.user_knowledge.upload_document_to_repository",
            return_value={"id": "doc_2", "status": "parsing", "filename": "river.pdf"},
        ):
            response = self.client.post(
                "/api/user/knowledge/documents",
                headers={"X-Gezhi-Client": "miniprogram"},
                data={"user_id": "24001020106", "repository_id": "repo_1"},
                files={"file": ("river.pdf", b"river", "application/pdf")},
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body, {"code": 0, "message": "ok", "data": {"id": "doc_2", "status": "parsing", "filename": "river.pdf"}})


class MiniprogramEvaluatorEndpointTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=self.engine)

    def test_create_mistake_from_quiz(self):
        response = self.client.post(
            "/api/exams/mistakes",
            headers={"X-Gezhi-Client": "miniprogram"},
            json={
                "userId": "24001020106",
                "question": "Binary tree preorder traversal order?",
                "answer": "root-left-right",
                "source": "quiz",
                "quizId": "quiz_001",
            },
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["message"], "ok")
        self.assertEqual(body["data"]["studentId"], "24001020106")
        self.assertFalse(body["data"]["mastered"])

    def test_evaluator_attempt_lifecycle(self):
        headers = {"X-Gezhi-Client": "miniprogram"}
        quizzes = self.client.get("/api/evaluator/quizzes?limit=20", headers=headers).json()["data"]
        quiz_id = quizzes["items"][0]["id"]
        attempt = self.client.post(
            "/api/evaluator/attempts",
            headers=headers,
            json={"userId": "24001020106", "quizId": quiz_id},
        ).json()["data"]
        detail = self.client.get(f"/api/evaluator/attempts/{attempt['id']}", headers=headers).json()["data"]
        submitted = self.client.post(
            f"/api/evaluator/attempts/{attempt['id']}/submit",
            headers=headers,
            json={"answers": {"q_001": "A", "q_002": True}},
        ).json()["data"]
        result = self.client.get(f"/api/evaluator/attempts/{attempt['id']}/result", headers=headers).json()["data"]

        self.assertGreaterEqual(len(quizzes["items"]), 1)
        self.assertIn("nextCursor", quizzes)
        self.assertEqual(detail["status"], "in_progress")
        self.assertNotIn("correctAnswer", detail["questions"][0])
        self.assertEqual(submitted["status"], "submitted")
        self.assertEqual(result["attemptId"], attempt["id"])
        self.assertEqual(result["score"], 100)
        self.assertIn("questions", result)


class MiniprogramExistingEndpointWrapperTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=self.engine)

    def test_forum_posts_pc_shape_and_miniprogram_shape(self):
        pc = self.client.get("/api/forum/posts").json()
        mp = self.client.get("/api/forum/posts", headers={"X-Gezhi-Client": "miniprogram"}).json()

        self.assertEqual(pc["code"], 200)
        self.assertEqual(mp["code"], 0)
        self.assertEqual(mp["message"], "ok")
        self.assertIn("items", mp["data"])
        self.assertIn("nextCursor", mp["data"])

    def test_chat_history_miniprogram_shape(self):
        mp = self.client.get(
            "/api/chat/history?session_id=24001020106&agent_mode=tutor&limit=50",
            headers={"X-Gezhi-Client": "miniprogram"},
        ).json()

        self.assertEqual(mp["code"], 0)
        self.assertEqual(mp["message"], "ok")
        self.assertIn("items", mp["data"])
        self.assertIn("nextCursor", mp["data"])

    def test_analytics_interactions_pc_shape_and_miniprogram_shape(self):
        db = self.SessionLocal()
        JsonStore(db).upsert(
            "analytics",
            "interaction",
            "interaction_1",
            {"id": "interaction_1", "title": "Review task", "status": "running"},
            status="running",
        )
        db.close()

        pc = self.client.get("/api/analytics/interactions").json()
        mp = self.client.get("/api/analytics/interactions", headers={"X-Gezhi-Client": "miniprogram"}).json()

        self.assertEqual(pc["code"], 200)
        self.assertEqual(mp["code"], 0)
        self.assertEqual(mp["message"], "ok")
        self.assertEqual(mp["data"]["items"][0]["id"], "interaction_1")
        self.assertIn("nextCursor", mp["data"])

    def test_exam_mistake_existing_endpoints_miniprogram_shape(self):
        headers = {"X-Gezhi-Client": "miniprogram"}
        created = self.client.post(
            "/api/exams/mistakes",
            headers=headers,
            json={
                "userId": "24001020106",
                "question": "Stack pop order?",
                "answer": "LIFO",
                "correctAnswer": "LIFO",
            },
        ).json()["data"]

        pc_list = self.client.get("/api/exams/student/24001020106/mistakes").json()
        mp_list = self.client.get("/api/exams/student/24001020106/mistakes", headers=headers).json()
        patched = self.client.patch(
            f"/api/exams/mistakes/{created['id']}",
            headers=headers,
            json={"mastered": True},
        ).json()
        with patch("app.api.endpoints.exams.build_chat_model", side_effect=RuntimeError("skip model")):
            analysis = self.client.post(
                f"/api/exams/mistakes/{created['id']}/ai-analysis",
                headers=headers,
                json={"model": "unit-test"},
            ).json()

        self.assertEqual(pc_list["code"], 200)
        self.assertEqual(mp_list["code"], 0)
        self.assertEqual(mp_list["message"], "ok")
        self.assertGreaterEqual(mp_list["data"]["summary"]["total"], 1)
        self.assertEqual(patched["code"], 0)
        self.assertTrue(patched["data"]["mastered"])
        self.assertEqual(analysis["code"], 0)
        self.assertEqual(analysis["data"]["mistakeId"], created["id"])
