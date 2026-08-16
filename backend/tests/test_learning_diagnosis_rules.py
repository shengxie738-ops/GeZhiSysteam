import unittest

from app.services.learning_diagnosis.contracts import EvidenceRecord, Provenance
from app.services.learning_diagnosis.mastery_evaluator import MasteryEvaluator
from app.services.learning_diagnosis.rule_engine import RuleEngine


def evidence(source, result, kp="linked_list_boundary", **kwargs):
    return EvidenceRecord(
        evidence_id=f"{source}-{result.get('status', result.get('score', 'x'))}",
        student_id="student-1",
        source_type=source,
        knowledge_point_ids=[kp],
        result=result,
        observed_at="2026-08-09T00:00:00Z",
        provenance=Provenance(source=source.lower(), reliability=0.9),
        **kwargs,
    )


class LearningDiagnosisRulesTest(unittest.TestCase):
    def test_scores_multiple_sources_and_keeps_git_score_null_when_disabled(self):
        result = RuleEngine().assess(
            [
                evidence("ASSIGNMENT", {"score": 70}),
                evidence("EXAM_WRONG", {"score": 50, "failed_cases": ["EMPTY_LIST"]}),
                evidence("SANDBOX", {"status": "TEST_FAILED", "test_summary": {"total": 6, "passed": 4, "failed": 2}}),
            ],
            ["linked_list_boundary"],
            include_git_evidence=False,
        )["linked_list_boundary"]
        self.assertGreater(result["mastery_score"], 0)
        self.assertIsNone(result["practice_score"])
        self.assertIn("EMPTY_LIST_FAILED", result["reason_codes"])

    def test_sandbox_error_does_not_lower_score(self):
        result = RuleEngine().assess([evidence("SANDBOX", {"status": "SANDBOX_ERROR"})], ["linked_list_boundary"], False)["linked_list_boundary"]
        self.assertEqual(result["evidence_count"], 0)
        self.assertEqual(result["state"], "insufficient_data")

    def test_git_practice_score_stays_separate_when_mastery_has_no_evidence(self):
        result = RuleEngine().assess(
            [evidence("GIT", {"practice_score": 76, "uncertainty": True}, include_git_evidence=True)],
            ["linked_list_boundary"],
            include_git_evidence=True,
        )["linked_list_boundary"]
        self.assertIsNone(result["mastery_score"])
        self.assertEqual(result["practice_score"], 76.0)
        self.assertEqual(result["state"], "learning")

    def test_hint_level_reduces_current_evidence_weight(self):
        evaluator = MasteryEvaluator()
        self.assertGreater(evaluator.independence_weight(1), evaluator.independence_weight(4))
        self.assertEqual(evaluator.independence_weight(5), 0.0)

    def test_guided_success_cannot_mark_mastered(self):
        result = MasteryEvaluator().evaluate(
            {"correct": True, "independent_retest_passed": False, "coverage": {"NORMAL", "BOUNDARY", "EXCEPTION"}, "highest_hint_level": 3},
            85,
        )
        self.assertNotEqual(result["state"], "mastered")

    def test_mastered_requires_multi_boundary_independent_retest(self):
        result = MasteryEvaluator().evaluate(
            {"correct": True, "independent_retest_passed": True, "coverage": {"NORMAL", "BOUNDARY", "EXCEPTION"}, "highest_hint_level": 1},
            90,
        )
        self.assertEqual(result["state"], "mastered")

    def test_rule_engine_uses_hint_weight_and_independent_retest_coverage(self):
        records = [
            evidence("SANDBOX", {"status": "PASSED", "test_summary": {"total": 3, "passed": 3}, "task_type": "CODING_PRACTICE", "hint_level": 1}),
            evidence("INDEPENDENT_RETEST", {"status": "PASSED", "test_summary": {"total": 3, "passed": 3}, "task_type": "INDEPENDENT_RETEST", "hint_level": 1, "coverage": ["NORMAL", "BOUNDARY", "EXCEPTION"]}),
        ]
        result = RuleEngine().assess(records, ["linked_list_boundary"], False)["linked_list_boundary"]
        self.assertTrue(result["independent_retest_passed"])
        self.assertEqual(set(result["independent_retest_coverage"]), {"NORMAL", "BOUNDARY", "EXCEPTION"})
        self.assertEqual(result["highest_hint_level"], 1)
        self.assertEqual(result["state"], "mastered")


if __name__ == "__main__":
    unittest.main()
