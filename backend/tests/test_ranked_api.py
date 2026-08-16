import asyncio
import concurrent.futures
import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from sqlalchemy import create_engine
from sqlalchemy.orm import Query, sessionmaker

from app.api.endpoints.ranked import (
    MatchStartPayload,
    RankedMatchSubmitPayload,
    _build_ranked_dashboard_data,
    get_match_history,
    get_ranked_dashboard,
    get_ranked_mistakes,
    get_ranked_seasons,
    delete_ranked_mistake,
    start_ranked_match,
    submit_ranked_match,
)
from app.models.domain_record import DomainRecord
from app.models.ranked_question import RankedQuestion
from app.repositories.json_store import JsonStore


class RankedApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=self.engine)
        RankedQuestion.__table__.create(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_dashboard_seeds_and_reuses_database_records(self):
        db = self.SessionLocal()
        try:
            first = _build_ranked_dashboard_data("student-1", db)
            store = JsonStore(db)
            stored_profile = store.get_payload("ranked", "profile", "student-1")
            stored_profile["score"] = 2222
            store.upsert("ranked", "profile", "student-1", stored_profile, owner_id="student-1", status="active")

            second = _build_ranked_dashboard_data("student-1", db)

            self.assertEqual(first["player"]["studentId"], "student-1")
            self.assertEqual(second["player"]["score"], 2222)
            self.assertGreaterEqual(len(second["leaderboard"]), 1)
            self.assertGreaterEqual(len(second["rules"]), 1)
            self.assertGreaterEqual(len(second["tierLadder"]), 1)
        finally:
            db.close()

    def test_dashboard_endpoint_allows_public_positional_db_call(self):
        db = self.SessionLocal()
        try:
            response = asyncio.run(get_ranked_dashboard("student-1", db))

            self.assertEqual(response["status"], "success")
            self.assertEqual(response["data"]["player"]["studentId"], "student-1")
        finally:
            db.close()

    def test_start_match_persists_history_record(self):
        db = self.SessionLocal()
        try:
            response = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]
            history = asyncio.run(get_match_history("student-1", db))["data"]

            self.assertEqual(response["studentId"], "student-1")
            self.assertTrue(response["id"].startswith("ranked-match-"))
            self.assertTrue(any(item["id"] == response["id"] for item in history))
        finally:
            db.close()

    def test_mistakes_and_seasons_seed_for_student(self):
        db = self.SessionLocal()
        try:
            mistakes = asyncio.run(get_ranked_mistakes("student-1", db))["data"]
            seasons = asyncio.run(get_ranked_seasons("student-1", db))["data"]

            self.assertGreaterEqual(len(mistakes), 1)
            self.assertEqual(mistakes[0]["studentId"], "student-1")
            self.assertGreaterEqual(len(seasons), 1)
            self.assertEqual(seasons[0]["studentId"], "student-1")
        finally:
            db.close()

    def test_failed_match_submission_creates_ranked_mistake_and_updates_profile(self):
        db = self.SessionLocal()
        try:
            store = JsonStore(db)
            store.upsert(
                "ranked",
                "profile",
                "student-1",
                {
                    "studentId": "student-1",
                    "name": "Student One",
                    "tierCode": "gold",
                    "tier": "榛勯噾娈典綅",
                    "score": 1980,
                    "streak": 5,
                    "progress": 68,
                },
                owner_id="student-1",
                status="active",
            )
            match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]

            response = asyncio.run(
                submit_ranked_match(
                    match["id"],
                    RankedMatchSubmitPayload(
                        userId="student-1",
                        result="loss",
                        code="function solve(){ return 0; }",
                        durationSeconds=125,
                        passedCount=1,
                        totalCount=2,
                        testResults=[
                            {"label": "case 1", "status": "passed", "expected": 1, "actual": 1},
                            {"label": "case 2", "status": "failed", "expected": 2, "actual": 0, "error": "wrong answer"},
                        ],
                    ),
                    db,
                )
            )["data"]

            self.assertEqual(response["match"]["status"], "settled")
            self.assertEqual(response["match"]["result"], "loss")
            self.assertLess(response["match"]["scoreDelta"], 0)
            self.assertEqual(response["profile"]["score"], 1980 + response["match"]["scoreDelta"])
            self.assertEqual(response["profile"]["streak"], 0)
            self.assertIsNotNone(response["mistake"])
            self.assertEqual(response["mistake"]["studentId"], "student-1")
            self.assertEqual(response["mistake"]["questionId"], match["questionId"])
            self.assertEqual(response["mistake"]["wrongCount"], 1)
            self.assertIn("case 2", response["mistake"]["errorPhenomenon"])

            mistakes = asyncio.run(get_ranked_mistakes("student-1", db))["data"]
            self.assertTrue(any(item["id"] == response["mistake"]["id"] for item in mistakes))
        finally:
            db.close()

    def test_duplicate_failed_match_submission_returns_existing_settlement(self):
        db = self.SessionLocal()
        try:
            match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]
            payload = RankedMatchSubmitPayload(
                userId="student-1",
                result="loss",
                code="function solve(){ return 0; }",
                durationSeconds=80,
                passedCount=0,
                totalCount=1,
                testResults=[{"label": "case retry", "status": "failed", "expected": 1, "actual": 0}],
            )

            first_response = asyncio.run(submit_ranked_match(match["id"], payload, db))["data"]
            second_response = asyncio.run(submit_ranked_match(match["id"], payload, db))["data"]

            self.assertEqual(second_response["match"], first_response["match"])
            self.assertEqual(second_response["profile"]["score"], first_response["profile"]["score"])
            self.assertEqual(second_response["mistake"]["id"], first_response["mistake"]["id"])
            self.assertEqual(second_response["mistake"]["wrongCount"], first_response["mistake"]["wrongCount"])
        finally:
            db.close()

    def test_match_submission_locks_match_row_before_settlement(self):
        db = self.SessionLocal()
        lock_calls = []
        original_with_for_update = Query.with_for_update
        try:
            match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]
            payload = RankedMatchSubmitPayload(
                userId="student-1",
                result="win",
                code="function solve(){ return 1; }",
                durationSeconds=70,
                passedCount=1,
                totalCount=1,
                testResults=[{"label": "case lock", "status": "passed"}],
            )

            def tracking_with_for_update(query, *args, **kwargs):
                lock_calls.append(kwargs)
                return original_with_for_update(query, *args, **kwargs)

            with patch.object(Query, "with_for_update", new=tracking_with_for_update):
                asyncio.run(submit_ranked_match(match["id"], payload, db))

            self.assertGreaterEqual(len(lock_calls), 1)
        finally:
            db.close()

    def test_match_submission_does_not_use_jsonstore_upsert_for_settlement(self):
        db = self.SessionLocal()
        try:
            match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]
            payload = RankedMatchSubmitPayload(
                userId="student-1",
                result="loss",
                code="function solve(){ return 0; }",
                durationSeconds=80,
                passedCount=0,
                totalCount=1,
                testResults=[{"label": "case atomic", "status": "failed", "expected": 1, "actual": 0}],
            )

            with patch.object(JsonStore, "upsert", side_effect=AssertionError("JsonStore.upsert commits per record")):
                response = asyncio.run(submit_ranked_match(match["id"], payload, db))["data"]

            self.assertEqual(response["match"]["status"], "settled")
            self.assertIsNotNone(response["mistake"])
        finally:
            db.close()

    def test_partial_seed_match_submission_stays_atomic(self):
        db = self.SessionLocal()
        try:
            match = {
                "id": "ranked-match-partial-seed",
                "studentId": "student-legacy",
                "title": "Legacy seeded question",
                "type": "programming question",
                "result": "matched",
                "scoreDelta": 0,
                "duration": "00:00",
                "createdAt": "2026-07-13 00:00:00",
                "status": "pending",
                "questionId": "legacy-question-1",
                "question": {
                    "questionId": "legacy-question-1",
                    "title": "Legacy seeded question",
                    "category": "graph",
                    "knowledgeTags": ["DFS"],
                    "scoreReward": 50,
                    "scorePenalty": 20,
                },
            }
            db.add(
                DomainRecord(
                    module="ranked",
                    record_type="match",
                    record_key=match["id"],
                    owner_id="student-legacy",
                    status="active",
                    payload=json.dumps(match),
                )
            )
            db.commit()
            payload = RankedMatchSubmitPayload(
                userId="student-legacy",
                result="loss",
                code="function solve(){ return 0; }",
                durationSeconds=80,
                passedCount=0,
                totalCount=1,
                testResults=[{"label": "case partial", "status": "failed", "expected": 1, "actual": 0}],
            )

            with patch.object(JsonStore, "upsert", side_effect=AssertionError("JsonStore.upsert called during submit")):
                with patch.object(db, "commit", wraps=db.commit) as commit:
                    response = asyncio.run(submit_ranked_match(match["id"], payload, db))["data"]

            profile = JsonStore(db).get_payload("ranked", "profile", "student-legacy", owner_id="student-legacy")
            mistake = JsonStore(db).get_payload(
                "ranked",
                "mistake",
                "ranked-mistake:student-legacy:legacy-question-1",
                owner_id="student-legacy",
            )

            self.assertEqual(commit.call_count, 1)
            self.assertEqual(response["match"]["status"], "settled")
            self.assertEqual(profile["score"], 1960)
            self.assertEqual(mistake["wrongCount"], 1)
        finally:
            db.close()

    def test_match_submission_commits_settlement_once(self):
        db = self.SessionLocal()
        try:
            match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]
            payload = RankedMatchSubmitPayload(
                userId="student-1",
                result="loss",
                code="function solve(){ return 0; }",
                durationSeconds=80,
                passedCount=0,
                totalCount=1,
                testResults=[{"label": "case commit", "status": "failed", "expected": 1, "actual": 0}],
            )

            with patch.object(db, "commit", wraps=db.commit) as commit:
                response = asyncio.run(submit_ranked_match(match["id"], payload, db))["data"]

            self.assertEqual(response["match"]["status"], "settled")
            self.assertEqual(commit.call_count, 1)
        finally:
            db.close()

    def test_concurrent_duplicate_submission_settles_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "ranked-concurrency.db")
            engine = create_engine(
                f"sqlite:///{database_path}",
                connect_args={"check_same_thread": False},
            )
            DomainRecord.__table__.create(bind=engine)
            RankedQuestion.__table__.create(bind=engine)
            session_local = sessionmaker(bind=engine)
            setup_db = session_local()
            try:
                store = JsonStore(setup_db)
                store.upsert(
                    "ranked",
                    "profile",
                    "student-1",
                    {
                        "studentId": "student-1",
                        "tierCode": "gold",
                        "tier": "gold",
                        "score": 1980,
                        "streak": 5,
                        "progress": 68,
                    },
                    owner_id="student-1",
                    status="active",
                )
                match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), setup_db))["data"]
            finally:
                setup_db.close()

            payload = RankedMatchSubmitPayload(
                userId="student-1",
                result="loss",
                code="function solve(){ return 0; }",
                durationSeconds=80,
                passedCount=0,
                totalCount=1,
                testResults=[{"label": "case retry", "status": "failed", "expected": 1, "actual": 0}],
            )
            requests_ready = threading.Barrier(2)
            match_writes_ready = threading.Barrier(2)
            match_writes_released = threading.Event()
            profile_updated = threading.Event()
            state_guard = threading.Lock()
            profile_reads = 0
            original_get_payload = JsonStore.get_payload
            original_upsert = JsonStore.upsert

            def coordinated_get_payload(store, module, record_type, record_key, owner_id=None):
                nonlocal profile_reads
                if (
                    match_writes_released.is_set()
                    and module == "ranked"
                    and record_type == "profile"
                    and record_key == "student-1"
                ):
                    with state_guard:
                        profile_reads += 1
                        wait_for_first_profile_update = profile_reads == 2
                    if wait_for_first_profile_update:
                        profile_updated.wait(timeout=1)
                return original_get_payload(store, module, record_type, record_key, owner_id)

            def coordinated_upsert(store, module, record_type, record_key, record, **kwargs):
                if module == "ranked" and record_type == "match" and record.get("status") == "settled":
                    try:
                        match_writes_ready.wait(timeout=1)
                    except threading.BrokenBarrierError:
                        pass
                    match_writes_released.set()
                stored = original_upsert(store, module, record_type, record_key, record, **kwargs)
                if module == "ranked" and record_type == "profile" and record_key == "student-1":
                    profile_updated.set()
                return stored

            def submit_in_own_session():
                db = session_local()
                try:
                    requests_ready.wait(timeout=2)
                    return asyncio.run(submit_ranked_match(match["id"], payload, db))["data"]
                finally:
                    db.close()

            with patch.object(JsonStore, "get_payload", new=coordinated_get_payload), patch.object(
                JsonStore, "upsert", new=coordinated_upsert
            ):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    responses = list(executor.map(lambda _: submit_in_own_session(), range(2)))

            check_db = session_local()
            try:
                settled_match = JsonStore(check_db).get_payload("ranked", "match", match["id"], owner_id="student-1")
                profile = JsonStore(check_db).get_payload("ranked", "profile", "student-1")
                mistake_id = f"ranked-mistake:student-1:{match['questionId']}"
                mistake = JsonStore(check_db).get_payload("ranked", "mistake", mistake_id, owner_id="student-1")

                self.assertEqual(settled_match["status"], "settled")
                self.assertEqual(profile["score"], 1980 + settled_match["scoreDelta"])
                self.assertEqual(mistake["wrongCount"], 1)
                self.assertEqual(responses[0]["match"], responses[1]["match"])
            finally:
                check_db.close()
                engine.dispose()

    def test_repeated_failed_match_submission_increments_ranked_mistake(self):
        db = self.SessionLocal()
        try:
            first_match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]
            question = first_match["question"]
            second_match = dict(first_match)
            second_match["id"] = "ranked-match-repeat"
            second_match["status"] = "pending"
            JsonStore(db).upsert("ranked", "match", second_match["id"], second_match, owner_id="student-1", status="active")

            payload = RankedMatchSubmitPayload(
                userId="student-1",
                result="loss",
                code="function solve(){ return 0; }",
                durationSeconds=80,
                passedCount=0,
                totalCount=1,
                testResults=[{"label": "case repeat", "status": "failed", "expected": 1, "actual": 0}],
            )
            first_response = asyncio.run(submit_ranked_match(first_match["id"], payload, db))["data"]
            second_response = asyncio.run(submit_ranked_match(second_match["id"], payload, db))["data"]

            self.assertEqual(first_response["mistake"]["questionId"], question["questionId"])
            self.assertEqual(second_response["mistake"]["id"], first_response["mistake"]["id"])
            self.assertEqual(second_response["mistake"]["wrongCount"], 2)
        finally:
            db.close()

    def test_successful_match_submission_updates_profile_without_mistake(self):
        db = self.SessionLocal()
        try:
            store = JsonStore(db)
            store.upsert(
                "ranked",
                "profile",
                "student-1",
                {
                    "studentId": "student-1",
                    "name": "Student One",
                    "tierCode": "gold",
                    "tier": "榛勯噾娈典綅",
                    "score": 1980,
                    "streak": 2,
                    "progress": 68,
                },
                owner_id="student-1",
                status="active",
            )
            match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]

            response = asyncio.run(
                submit_ranked_match(
                    match["id"],
                    RankedMatchSubmitPayload(
                        userId="student-1",
                        result="win",
                        code="function solve(){ return 1; }",
                        durationSeconds=61,
                        passedCount=2,
                        totalCount=2,
                        testResults=[
                            {"label": "case 1", "status": "passed"},
                            {"label": "case 2", "status": "passed"},
                        ],
                    ),
                    db,
                )
            )["data"]

            self.assertEqual(response["match"]["result"], "win")
            self.assertGreater(response["match"]["scoreDelta"], 0)
            self.assertEqual(response["profile"]["streak"], 3)
            self.assertIsNone(response["mistake"])
        finally:
            db.close()

    def test_cheat_loss_creates_mistake_with_reason(self):
        db = self.SessionLocal()
        try:
            match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]
            response = asyncio.run(
                submit_ranked_match(
                    match["id"],
                    RankedMatchSubmitPayload(
                        userId="student-1",
                        result="cheat_lose",
                        code="function solve(){}",
                        durationSeconds=10,
                        passedCount=0,
                        totalCount=2,
                        testResults=[],
                        cheatReason="fullscreen-exit",
                    ),
                    db,
                )
            )["data"]

            self.assertEqual(response["match"]["result"], "cheat_lose")
            self.assertIsNotNone(response["mistake"])
            self.assertIn("fullscreen-exit", response["mistake"]["errorPhenomenon"])
        finally:
            db.close()

    def test_soft_delete_ranked_mistake_hides_from_active_listing(self):
        db = self.SessionLocal()
        try:
            match = asyncio.run(start_ranked_match(MatchStartPayload(userId="student-1"), db))["data"]
            response = asyncio.run(
                submit_ranked_match(
                    match["id"],
                    RankedMatchSubmitPayload(
                        userId="student-1",
                        result="loss",
                        code="function solve(){ return 0; }",
                        durationSeconds=40,
                        passedCount=0,
                        totalCount=1,
                        testResults=[{"label": "case delete", "status": "failed"}],
                    ),
                    db,
                )
            )["data"]
            mistake_id = response["mistake"]["id"]

            deleted = asyncio.run(delete_ranked_mistake(mistake_id, userId="student-1", db=db))["data"]
            active = asyncio.run(get_ranked_mistakes("student-1", db))["data"]
            stored = JsonStore(db).get_payload("ranked", "mistake", mistake_id)

            self.assertEqual(deleted["status"], "deleted")
            self.assertTrue(deleted["deletedAt"])
            self.assertFalse(any(item["id"] == mistake_id for item in active))
            self.assertEqual(stored["status"], "deleted")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
