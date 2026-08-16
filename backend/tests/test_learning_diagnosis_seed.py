import asyncio
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.seed_learning_diagnosis_demo import GOAL, seed_student


class SeedLearningDiagnosisDemoTest(unittest.TestCase):
    def test_seed_script_does_not_import_or_call_mock_evidence_provider(self):
        source = Path(__file__).resolve().parents[1].joinpath("scripts", "seed_learning_diagnosis_demo.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)]
        self.assertNotIn("MockEvidenceProvider", names)

    def test_seed_student_provides_idempotent_existing_system_evidence(self):
        class FakeStore:
            def __init__(self):
                self.paths = []

            def list_sessions(self, student_id):
                return []

            def list_paths(self, student_id, session_id):
                return self.paths

        class FakeWorkflow:
            def __init__(self):
                self.store = FakeStore()
                self.received_goal = None

            async def create_session(self, student_id, goal):
                self.received_goal = goal
                result = {
                    "session": {"id": "session-1", "student_id": student_id},
                    "snapshot": {"assessments": []},
                    "path": {"tasks": [{"content_payload": {"knowledge_point_ids": ["linked_list_boundary"]}}]},
                }
                result["path"]["path_version"] = 1
                self.store.paths.append(result["path"])
                return result

            async def refresh_session(self, session_id, student_id, trigger):
                path = {"path_version": len(self.store.paths) + 1, "tasks": [{"content_payload": {"prompt": "demo"}}]}
                self.store.paths.append(path)
                return {"session": {"id": session_id, "student_id": student_id}, "snapshot": {"version": path["path_version"]}, "path": path}

        workflow = FakeWorkflow()
        result = asyncio.run(seed_student(workflow, "demo-student"))
        self.assertTrue(result["created"])
        evidence = workflow.received_goal["existing_evidence"]
        self.assertEqual(len(evidence), 3)
        self.assertTrue(all(item["evidence_id"].startswith("demo-") for item in evidence))
        self.assertTrue(all(item["source_type"] in {"ASSIGNMENT", "EXAM_WRONG", "RANKED_RESULT"} for item in evidence))
        self.assertEqual(len({item["evidence_id"] for item in evidence}), 3)
        self.assertTrue(workflow.received_goal["goal_text"])
        self.assertEqual(result["path"]["path_version"], 4)

    def test_seed_student_is_idempotent_when_session_exists(self):
        class FakeStore:
            def __init__(self):
                self.paths = [{"path_version": 1, "tasks": [{"content_payload": {"prompt": "demo"}}]}]

            def list_sessions(self, student_id):
                return [{"id": "session-existing", "created_at": "2026-08-10T00:00:00+00:00", "student_id": student_id, "existing_evidence": [{"evidence_id": "demo-existing"}], "current_knowledge_points": [{"id": "linked_list_boundary"}, {"id": "linked_list_delete"}]}]

            def list_snapshots(self, student_id, session_id):
                return [{"version": 1, "evidence_refs": ["demo-existing"]}]

            def list_paths(self, student_id, session_id):
                return self.paths

        class FakeWorkflow:
            def __init__(self):
                self.store = FakeStore()
                self.refresh_triggers = []

            async def create_session(self, student_id, goal):
                raise AssertionError("existing demo session must not be recreated")

            async def refresh_session(self, session_id, student_id, trigger):
                self.refresh_triggers.append(trigger)
                path = {"path_version": len(self.store.paths) + 1, "tasks": [{"content_payload": {"prompt": "demo"}}]}
                self.store.paths.append(path)
                return {"session": {"id": session_id, "student_id": student_id}, "snapshot": {"version": path["path_version"]}, "path": path}

        workflow = FakeWorkflow()
        result = asyncio.run(seed_student(workflow, "demo-student"))
        self.assertFalse(result["created"])
        self.assertEqual(result["session"]["id"], "session-existing")
        self.assertEqual(result["path"]["path_version"], 4)
        self.assertEqual([item["failure_count"] for item in workflow.refresh_triggers], [2, 3, 0])

    def test_seed_student_archives_stale_mock_session_and_creates_clean_session(self):
        class FakeStore:
            def __init__(self):
                self.patches = []
                self.paths = []

            def list_sessions(self, student_id):
                return [{"id": "session-old", "created_at": "2026-08-09T00:00:00+00:00", "student_id": student_id}]

            def list_snapshots(self, student_id, session_id):
                return [{"version": 1, "evidence_refs": ["mock-exam-old"]}]

            def list_paths(self, student_id, session_id):
                if session_id == "session-old":
                    return [{"path_version": 1, "tasks": [{"task_id": "legacy", "title": "old"}]}]
                return self.paths

            def update_session(self, session_id, student_id, patch):
                self.patches.append((session_id, student_id, patch))
                return {"id": session_id, "status": patch["status"]}

        class FakeWorkflow:
            def __init__(self):
                self.store = FakeStore()
                self.received_goal = None

            async def create_session(self, student_id, goal):
                self.received_goal = goal
                result = {"session": {"id": "session-new", "student_id": student_id}, "snapshot": {}, "path": {"path_version": 1, "tasks": []}}
                self.store.paths.append(result["path"])
                return result

            async def refresh_session(self, session_id, student_id, trigger):
                path = {"path_version": len(self.store.paths) + 1, "tasks": []}
                self.store.paths.append(path)
                return {"session": {"id": session_id, "student_id": student_id}, "snapshot": {"version": path["path_version"]}, "path": path}

        workflow = FakeWorkflow()
        result = asyncio.run(seed_student(workflow, "demo-student"))
        self.assertTrue(result["created"])
        self.assertEqual(result["session"]["id"], "session-new")
        self.assertEqual(workflow.store.patches[0][2]["status"], "ARCHIVED")

    def test_seed_student_repairs_valid_session_without_path_history(self):
        class FakeStore:
            def __init__(self):
                self.paths = []

            def list_sessions(self, student_id):
                return [{"id": "session-empty", "created_at": "2026-08-11T00:00:00+00:00", "student_id": student_id, "existing_evidence": [{"evidence_id": "demo-existing"}], "current_knowledge_points": [{"id": "linked_list_boundary"}, {"id": "linked_list_delete"}]}]

            def list_snapshots(self, student_id, session_id):
                return []

            def list_paths(self, student_id, session_id):
                return self.paths

        class FakeWorkflow:
            def __init__(self):
                self.store = FakeStore()

            async def create_session(self, student_id, goal):
                raise AssertionError("valid session should be repaired in place")

            async def refresh_session(self, session_id, student_id, trigger):
                path = {"path_version": len(self.store.paths) + 1, "tasks": []}
                self.store.paths.append(path)
                return {"session": {"id": session_id, "student_id": student_id}, "snapshot": {"version": path["path_version"]}, "path": path}

        result = asyncio.run(seed_student(FakeWorkflow(), "demo-student"))
        self.assertFalse(result["created"])
        self.assertEqual(result["path"]["path_version"], 4)


if __name__ == "__main__":
    unittest.main()
