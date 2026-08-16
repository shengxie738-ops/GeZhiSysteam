import unittest

from app.services.learning_diagnosis.path_planner import LearningPathPlanner
from app.services.learning_diagnosis.knowledge_graph import KnowledgeGraph


class LearningDiagnosisPathTest(unittest.TestCase):
    def test_prerequisites_are_sorted_before_target(self):
        graph = KnowledgeGraph()
        ordered = graph.resolve_prerequisites(["linked_list_delete"])
        self.assertLess(ordered.index("linked_list_boundary"), ordered.index("linked_list_delete"))

    def test_initial_path_has_four_learning_stages(self):
        path = LearningPathPlanner().plan(
            assessments={"linked_list_boundary": {"state": "unstable", "mastery_score": 58}},
            goal={"course": "数据结构", "weeks_remaining": 4, "weekly_minutes": 180},
            previous_path=None,
        )
        self.assertEqual(path.path_version, 1)
        self.assertEqual([task.task_type for task in path.tasks], ["KNOWLEDGE_REVIEW", "GUIDED_PRACTICE", "CODING_PRACTICE", "INDEPENDENT_RETEST"])

    def test_second_failure_splits_task_and_third_failure_adds_remediation(self):
        planner = LearningPathPlanner()
        first = planner.plan({"linked_list_boundary": {"state": "unstable", "mastery_score": 58}}, {"weeks_remaining": 4, "weekly_minutes": 180}, None)
        second = planner.plan({"linked_list_boundary": {"state": "unstable", "mastery_score": 50}}, {"weeks_remaining": 4, "weekly_minutes": 180}, first, failure_count=2)
        self.assertEqual(second.path_version, 2)
        self.assertTrue(any(task.parent_task_id for task in second.tasks))
        third = planner.plan({"linked_list_boundary": {"state": "unstable", "mastery_score": 42}}, {"weeks_remaining": 4, "weekly_minutes": 180}, second, failure_count=3)
        self.assertEqual(third.path_version, 3)
        self.assertTrue(any(task.return_task_id for task in third.tasks))

    def test_path_version_keeps_previous_version_and_change_reason(self):
        planner = LearningPathPlanner()
        first = planner.plan({"linked_list_boundary": {"state": "unstable", "mastery_score": 58}}, {"weeks_remaining": 4, "weekly_minutes": 180}, None)
        second = planner.plan({"linked_list_boundary": {"state": "learning", "mastery_score": 72}}, {"weeks_remaining": 4, "weekly_minutes": 180}, first, trigger_type="REMEDIATION_COMPLETED")
        self.assertEqual(second.previous_version, 1)
        self.assertIn("BOUNDARY_CASES_IMPROVED", second.change_reason_codes)


if __name__ == "__main__":
    unittest.main()
