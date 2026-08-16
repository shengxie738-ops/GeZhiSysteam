import asyncio
import gc
import unittest
import warnings

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.api.endpoints.learning_diagnosis as endpoint_module
import app.schemas.learning_diagnosis as schema_module
from app.core.security import create_access_token
from app.models.domain_record import DomainRecord
from app.schemas.learning_diagnosis import CreateDiagnosisSessionRequest
from app.services.code_sandbox import CodeSandbox


class LearningDiagnosisRunPreviewTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=engine)
        self.db = sessionmaker(bind=engine)()
        self.authorization = f"Bearer {create_access_token('student-1', 'student')}"

    def tearDown(self):
        self.db.close()

    def test_run_preview_executes_without_creating_evidence(self):
        self.assertTrue(hasattr(schema_module, "RunTaskRequest"), "RunTaskRequest should exist")
        self.assertTrue(hasattr(endpoint_module, "run_diagnosis_task"), "run_diagnosis_task should exist")

        created = asyncio.run(endpoint_module.create_diagnosis_session(
            CreateDiagnosisSessionRequest(student_id="student-1", course="数据结构"),
            self.authorization,
            self.db,
        ))
        session_id = created["data"]["session"]["id"]
        coding_task = next(
            task for task in created["data"]["path"]["tasks"]
            if task["task_type"] == "CODING_PRACTICE"
        )
        request = schema_module.RunTaskRequest(
            student_id="student-1",
            session_id=session_id,
            code="print(input())",
            language="python",
        )

        result = asyncio.run(endpoint_module.run_diagnosis_task(
            coding_task["task_id"], request, self.db, self.authorization
        ))
        latest = asyncio.run(endpoint_module.get_latest_diagnosis_session(
            "student-1", self.db, self.authorization
        ))

        self.assertEqual(result["data"]["status"], "PASSED")
        self.assertEqual(result["data"]["test_summary"], {"total": 3, "passed": 3, "failed": 0})
        self.assertEqual(latest["data"]["evidence"], [])
        self.assertEqual(latest["data"]["snapshot"]["version"], created["data"]["snapshot"]["version"])

    def test_code_sandbox_closes_subprocess_pipes(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            result = CodeSandbox().run(
                "print(input())",
                "python",
                [{"input": ["normal"], "expected": "normal"}],
            )
            gc.collect()

        unclosed_pipes = [
            str(item.message) for item in caught
            if issubclass(item.category, ResourceWarning) and "unclosed file" in str(item.message)
        ]
        self.assertEqual(result["passed"], 1)
        self.assertEqual(unclosed_pipes, [])


if __name__ == "__main__":
    unittest.main()
