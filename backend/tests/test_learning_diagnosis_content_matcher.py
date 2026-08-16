import unittest
import os
from datetime import datetime, timezone

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost/api/v1")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test-agent")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test-chat")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test-dataset")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost/v1")

from app.services.learning_diagnosis.content_matcher import ContentMatcher
from app.services.learning_diagnosis.contracts import GoalVersion
from app.models.domain_record import DomainRecord
from app.models.ranked_question import RankedQuestion
from app.repositories.json_store import JsonStore
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class LearningDiagnosisContentMatcherTest(unittest.TestCase):
    def setUp(self):
        self.goal = GoalVersion(
            goal_version_id="goal-1",
            session_id="session-1",
            student_id="student-1",
            raw_goal_text="两周内掌握二叉树遍历并能编程实现",
            course_name="数据结构",
            created_at=datetime.now(timezone.utc),
            parsed_success_criteria={
                "knowledge_points": [
                    {"id": "tree_traversal", "name": "二叉树遍历"},
                    {"id": "tree_recursion", "name": "递归实现"},
                ]
            },
        )

    def test_structured_tags_have_priority_and_unrelated_is_ignored(self):
        catalog = [
            {"content_type": "EXAM", "content_id": "q-1", "source_module": "exams", "title": "二叉树遍历", "knowledgeTags": ["tree_traversal"]},
            {"content_type": "HOMEWORK", "content_id": "h-1", "source_module": "homework", "title": "数据库事务", "knowledgeTags": ["transaction"]},
        ]
        result = ContentMatcher(catalog=catalog).match_goal(self.goal)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].content_id, "q-1")
        self.assertEqual(result[0].match_method, "STRUCTURED_TAG")
        self.assertGreaterEqual(result[0].relevance_score, 0.8)

    def test_text_keyword_matching_is_used_when_tags_are_missing(self):
        catalog = [{"content_type": "COURSEWARE", "content_id": "c-1", "source_module": "course", "title": "二叉树遍历基础", "description": "递归和非递归实现"}]
        result = ContentMatcher(catalog=catalog).match_goal(self.goal)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].match_method, "TEXT_KEYWORD")
        self.assertIn("tree_traversal", result[0].knowledge_point_ids)

    def test_duplicate_association_is_idempotent_and_rebuilds(self):
        catalog = [{"content_type": "CODING", "content_id": "code-1", "source_module": "coding", "title": "二叉树遍历练习"}]
        matcher = ContentMatcher(catalog=catalog)
        first = matcher.match_goal(self.goal)
        second = matcher.match_goal(self.goal)
        self.assertEqual(first[0].association_id, second[0].association_id)
        rebuilt = matcher.rebuild_for_goal(self.goal)
        self.assertEqual(rebuilt[0].association_id, first[0].association_id)
        self.assertEqual(matcher.list_for_goal(self.goal.goal_version_id, self.goal.student_id)[0].content_id, "code-1")

    def test_association_keeps_read_only_content_snapshot_for_task_resolution(self):
        catalog = [{
            "content_type": "HOMEWORK",
            "content_id": "hw-1-q-2",
            "source_module": "homework",
            "title": "实现二叉树前序遍历",
            "description": "返回节点访问顺序",
            "type": "programming",
            "starterCode": "def preorder(root):\n    pass\n",
            "publicCases": [{"input": [[1, 2, 3]], "expected": [1, 2, 3]}],
            "knowledgeTags": ["tree_traversal"],
        }]
        association = ContentMatcher(catalog=catalog).match_goal(self.goal)[0]
        self.assertEqual(association.content_snapshot["title"], "实现二叉树前序遍历")
        self.assertEqual(association.content_snapshot["starterCode"], "def preorder(root):\n    pass\n")
        self.assertNotIn("studentAnswer", association.content_snapshot)

    def test_database_catalog_expands_homework_questions_and_ranked_question_rows(self):
        engine = create_engine("sqlite:///:memory:")
        DomainRecord.__table__.create(bind=engine)
        RankedQuestion.__table__.create(bind=engine)
        db = sessionmaker(bind=engine)()
        try:
            JsonStore(db).upsert("homework", "homework", "hw-1", {
                "id": "hw-1",
                "title": "树遍历作业",
                "questions": [{
                    "id": "q-2", "type": "programming", "title": "实现二叉树前序遍历",
                    "desc": "返回访问顺序", "starterCode": "def preorder(root):\n    pass\n",
                    "knowledgeTags": ["tree_traversal"],
                }],
            })
            db.add(RankedQuestion(
                question_id="rank-tree-1", title="二叉树遍历竞赛题", difficulty="easy", min_tier="bronze",
                category="数据结构", knowledge_tags='["tree_traversal"]', description="输出前序遍历",
                input_format="树节点", output_format="访问顺序", examples='[{"input":[1],"output":[1]}]',
                constraints="节点数不超过100", hint="使用递归",
            ))
            db.commit()
            matches = ContentMatcher(db=db).match_goal(self.goal)
            by_id = {item.content_id: item for item in matches}
            self.assertIn("hw-1:q-2", by_id)
            self.assertEqual(by_id["hw-1:q-2"].content_snapshot["starterCode"], "def preorder(root):\n    pass\n")
            self.assertIn("rank-tree-1", by_id)
            self.assertEqual(by_id["rank-tree-1"].content_type, "RANKED")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
