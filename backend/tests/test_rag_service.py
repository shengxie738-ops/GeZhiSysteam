import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost/api/v1")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.services.rag_service import (
    build_document_metadata,
    build_repository_metadata_condition,
    classify_supported_file,
    guess_cross_languages,
    map_ragflow_run_to_status,
    retrieve_from_datasets,
    upload_and_run_document,
)
from app.services import rag_service


def response(payload, status_code=200):
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = payload
    mock.text = str(payload)
    return mock


class RagServiceTest(unittest.TestCase):
    def test_classify_supported_file_only_accepts_pdf_with_presentation_deepdoc(self):
        profile = classify_supported_file("paper.pdf")
        self.assertEqual(profile["chunk_method"], "presentation")
        self.assertEqual(profile["parser_config"]["layout_recognize"], "DeepDOC")
        self.assertEqual(profile["file_type"], "pdf")

        with self.assertRaises(ValueError):
            classify_supported_file("slides.pptx")

    def test_upload_updates_metadata_and_parser_before_parse(self):
        upload_payload = {"code": 0, "data": [{"id": "doc_1"}]}
        ok_payload = {"code": 0}
        with patch(
            "app.services.rag_service.requests.post",
            side_effect=[response(upload_payload), response(ok_payload)],
        ) as post:
            with patch("app.services.rag_service.requests.put", return_value=response(ok_payload)) as put:
                doc_id = upload_and_run_document(
                    "ds_1",
                    b"deck",
                    "lesson.pdf",
                    metadata={"repository_id": "repo_1"},
                    parser={
                        "chunk_method": "presentation",
                        "parser_config": {"layout_recognize": "DeepDOC", "raptor": {"use_raptor": False}},
                    },
                )

        self.assertEqual(doc_id, "doc_1")
        expected_base_url = rag_service.settings.RAGFLOW_BASE_URL.rstrip("/")
        self.assertEqual(put.call_args.args[0], f"{expected_base_url}/datasets/ds_1/documents/doc_1")
        self.assertEqual(put.call_args.kwargs["json"]["meta_fields"]["repository_id"], "repo_1")
        self.assertEqual(put.call_args.kwargs["json"]["chunk_method"], "presentation")
        self.assertEqual(put.call_args.kwargs["json"]["parser_config"]["layout_recognize"], "DeepDOC")
        self.assertEqual(post.call_args_list[1].args[0], f"{expected_base_url}/datasets/ds_1/chunks")

    def test_retrieve_includes_cross_language_and_repository_filter(self):
        condition = build_repository_metadata_condition("repo_1")
        with patch(
            "app.services.rag_service.requests.post",
            return_value=response({"code": 0, "data": {"chunks": [{"content": "x"}]}}),
        ) as post:
            chunks = retrieve_from_datasets(
                ["ds_1"],
                "什么是 object detection",
                top_k_per_dataset=2,
                cross_languages=["English"],
                metadata_condition=condition,
            )

        self.assertEqual(chunks, [{"content": "x"}])
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["cross_languages"], ["English"])
        self.assertEqual(payload["metadata_condition"], condition)
        self.assertEqual(payload["keyword"], True)

    def test_status_and_language_helpers(self):
        self.assertEqual(map_ragflow_run_to_status("DONE"), "parsed")
        self.assertEqual(map_ragflow_run_to_status("FAIL"), "failed")
        self.assertEqual(map_ragflow_run_to_status("RUNNING"), "parsing")
        self.assertEqual(map_ragflow_run_to_status("UNSTART"), "queued")
        self.assertEqual(map_ragflow_run_to_status("CANCEL"), "cancelled")

        self.assertEqual(guess_cross_languages("什么是二叉树"), ["English"])
        self.assertEqual(guess_cross_languages("explain 二叉树 traversal"), ["Chinese", "English"])
        self.assertEqual(guess_cross_languages("explain graph traversal"), ["Chinese"])

        metadata = build_document_metadata("alice", "repo_1", "paper.pdf")
        self.assertEqual(metadata["user_id"], "alice")
        self.assertEqual(metadata["repository_id"], "repo_1")
        self.assertEqual(metadata["file_type"], "pdf")


if __name__ == "__main__":
    unittest.main()
