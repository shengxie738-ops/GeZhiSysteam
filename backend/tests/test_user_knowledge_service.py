import os
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
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user_knowledge import UserKnowledgeDocument, UserKnowledgeRepository
from app.models.user_rag import UserRagMapping
from app.services.user_knowledge_service import (
    create_repository,
    delete_repository,
    delete_repository_document,
    list_user_knowledge,
    upload_document_to_repository,
)


class UserKnowledgeServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_upload_uses_one_ragflow_dataset_and_local_repository_classification(self):
        repo = create_repository(self.db, "alice", "A仓库")

        with patch("app.services.user_knowledge_service.create_user_dataset", return_value="ds_alice") as create_dataset:
            with patch("app.services.user_knowledge_service.upload_and_run_document", return_value="doc_1") as upload:
                document = upload_document_to_repository(
                    self.db,
                    user_id="alice",
                    repository_id=repo["id"],
                    file_bytes=b"stack queue tree",
                    filename="data-structure.pdf",
                    file_size=16,
                )

        create_dataset.assert_called_once_with("alice")
        upload.assert_called_once()
        self.assertEqual(upload.call_args.args[:3], ("ds_alice", b"stack queue tree", "data-structure.pdf"))
        self.assertEqual(upload.call_args.kwargs["metadata"]["user_id"], "alice")
        self.assertEqual(upload.call_args.kwargs["metadata"]["repository_id"], repo["id"])
        self.assertEqual(upload.call_args.kwargs["metadata"]["file_type"], "pdf")
        self.assertEqual(upload.call_args.kwargs["parser"]["chunk_method"], "presentation")
        self.assertEqual(upload.call_args.kwargs["parser"]["parser_config"]["layout_recognize"], "DeepDOC")
        self.assertEqual(document["repository_id"], repo["id"])
        self.assertEqual(document["dataset_id"], "ds_alice")
        self.assertEqual(document["rag_document_id"], "doc_1")

        second_repo = create_repository(self.db, "alice", "B仓库")
        with patch("app.services.user_knowledge_service.create_user_dataset", return_value="should_not_create") as create_dataset:
            with patch("app.services.user_knowledge_service.upload_and_run_document", return_value="doc_2") as upload:
                second_doc = upload_document_to_repository(
                    self.db,
                    user_id="alice",
                    repository_id=second_repo["id"],
                    file_bytes=b"graph notes",
                    filename="graph.pdf",
                    file_size=11,
                )

        create_dataset.assert_not_called()
        upload.assert_called_once()
        self.assertEqual(upload.call_args.args[:3], ("ds_alice", b"graph notes", "graph.pdf"))
        self.assertEqual(second_doc["dataset_id"], "ds_alice")
        self.assertEqual(self.db.query(UserRagMapping).filter_by(user_id="alice").count(), 1)

    def test_upload_rejects_unsupported_file_extension_before_ragflow_call(self):
        repo = create_repository(self.db, "alice", "A仓库")

        with patch("app.services.user_knowledge_service.create_user_dataset") as create_dataset:
            with patch("app.services.user_knowledge_service.upload_and_run_document") as upload:
                with self.assertRaises(ValueError) as ctx:
                    upload_document_to_repository(
                        self.db,
                        user_id="alice",
                        repository_id=repo["id"],
                        file_bytes=b"bad",
                        filename="notes.txt",
                        file_size=3,
                    )

        self.assertIn("unsupported file type", str(ctx.exception))
        create_dataset.assert_not_called()
        upload.assert_not_called()

    def test_list_user_knowledge_groups_documents_by_repository(self):
        repo = create_repository(self.db, "alice", "数据结构")
        with patch("app.services.user_knowledge_service.create_user_dataset", return_value="ds_alice"):
            with patch("app.services.user_knowledge_service.upload_and_run_document", return_value="doc_1"):
                upload_document_to_repository(
                    self.db,
                    user_id="alice",
                    repository_id=repo["id"],
                    file_bytes=b"tree",
                    filename="tree.pdf",
                    file_size=4,
                )

        payload = list_user_knowledge(self.db, "alice")

        self.assertEqual(payload["dataset_id"], "ds_alice")
        self.assertEqual(len(payload["repositories"]), 1)
        self.assertEqual(payload["repositories"][0]["name"], "数据结构")
        self.assertEqual(payload["repositories"][0]["document_count"], 1)
        self.assertEqual(payload["repositories"][0]["documents"][0]["filename"], "tree.pdf")

    def test_list_user_knowledge_can_sync_ragflow_parse_status(self):
        repo = create_repository(self.db, "alice", "A仓库")
        self.db.add(UserRagMapping(user_id="alice", dataset_id="ds_alice"))
        self.db.add(
            UserKnowledgeDocument(
                id="local_doc",
                user_id="alice",
                repository_id=repo["id"],
                dataset_id="ds_alice",
                rag_document_id="rag_doc",
                filename="tree.pdf",
                file_size=10,
                status="parsing",
            )
        )
        self.db.commit()

        with patch("app.services.user_knowledge_service.list_dataset_documents", return_value=[{"id": "rag_doc", "run": "DONE"}]):
            payload = list_user_knowledge(self.db, "alice", sync_remote=True)

        self.assertEqual(payload["repositories"][0]["documents"][0]["status"], "parsed")

    def test_delete_document_syncs_ragflow_before_removing_local_record(self):
        repo = create_repository(self.db, "alice", "A仓库")
        self.db.add(UserRagMapping(user_id="alice", dataset_id="ds_alice"))
        self.db.add(
            UserKnowledgeDocument(
                id="local_doc",
                user_id="alice",
                repository_id=repo["id"],
                dataset_id="ds_alice",
                rag_document_id="rag_doc",
                filename="delete-me.pdf",
                file_size=10,
                status="parsed",
            )
        )
        self.db.commit()

        with patch("app.services.user_knowledge_service.delete_document_from_dataset") as delete_remote:
            deleted = delete_repository_document(self.db, user_id="alice", document_id="local_doc")

        delete_remote.assert_called_once_with("ds_alice", "rag_doc")
        self.assertEqual(deleted["id"], "local_doc")
        self.assertIsNone(self.db.query(UserKnowledgeDocument).filter_by(id="local_doc").first())

    def test_delete_keeps_local_record_when_ragflow_delete_fails(self):
        repo = create_repository(self.db, "alice", "A仓库")
        self.db.add(
            UserKnowledgeDocument(
                id="local_doc",
                user_id="alice",
                repository_id=repo["id"],
                dataset_id="ds_alice",
                rag_document_id="rag_doc",
                filename="keep-me.pdf",
                file_size=10,
                status="parsed",
            )
        )
        self.db.commit()

        with patch("app.services.user_knowledge_service.delete_document_from_dataset", side_effect=RuntimeError("RAGFlow down")):
            with self.assertRaises(RuntimeError):
                delete_repository_document(self.db, user_id="alice", document_id="local_doc")

        self.assertIsNotNone(self.db.query(UserKnowledgeDocument).filter_by(id="local_doc").first())

    def test_delete_repository_syncs_all_ragflow_documents_before_removing_local_records(self):
        repo = create_repository(self.db, "alice", "A仓库")
        other_repo = create_repository(self.db, "alice", "B仓库")
        self.db.add_all(
            [
                UserKnowledgeDocument(
                    id="local_doc_1",
                    user_id="alice",
                    repository_id=repo["id"],
                    dataset_id="ds_alice",
                    rag_document_id="rag_doc_1",
                    filename="one.pdf",
                    file_size=10,
                    status="parsed",
                ),
                UserKnowledgeDocument(
                    id="local_doc_2",
                    user_id="alice",
                    repository_id=repo["id"],
                    dataset_id="ds_alice",
                    rag_document_id="rag_doc_2",
                    filename="two.pdf",
                    file_size=20,
                    status="parsed",
                ),
                UserKnowledgeDocument(
                    id="other_doc",
                    user_id="alice",
                    repository_id=other_repo["id"],
                    dataset_id="ds_alice",
                    rag_document_id="rag_doc_other",
                    filename="keep.pdf",
                    file_size=30,
                    status="parsed",
                ),
            ]
        )
        self.db.commit()

        with patch("app.services.user_knowledge_service.delete_document_from_dataset") as delete_remote:
            deleted = delete_repository(self.db, user_id="alice", repository_id=repo["id"])

        self.assertEqual(deleted["id"], repo["id"])
        self.assertEqual(deleted["document_count"], 2)
        delete_remote.assert_any_call("ds_alice", "rag_doc_1")
        delete_remote.assert_any_call("ds_alice", "rag_doc_2")
        self.assertEqual(delete_remote.call_count, 2)
        self.assertIsNone(self.db.query(UserKnowledgeRepository).filter_by(id=repo["id"]).first())
        self.assertEqual(self.db.query(UserKnowledgeDocument).filter_by(repository_id=repo["id"]).count(), 0)
        self.assertIsNotNone(self.db.query(UserKnowledgeRepository).filter_by(id=other_repo["id"]).first())
        self.assertIsNotNone(self.db.query(UserKnowledgeDocument).filter_by(id="other_doc").first())

    def test_delete_repository_keeps_local_records_when_ragflow_delete_fails(self):
        repo = create_repository(self.db, "alice", "A仓库")
        self.db.add(
            UserKnowledgeDocument(
                id="local_doc",
                user_id="alice",
                repository_id=repo["id"],
                dataset_id="ds_alice",
                rag_document_id="rag_doc",
                filename="keep.pdf",
                file_size=10,
                status="parsed",
            )
        )
        self.db.commit()

        with patch("app.services.user_knowledge_service.delete_document_from_dataset", side_effect=RuntimeError("RAGFlow down")):
            with self.assertRaises(RuntimeError):
                delete_repository(self.db, user_id="alice", repository_id=repo["id"])

        self.assertIsNotNone(self.db.query(UserKnowledgeRepository).filter_by(id=repo["id"]).first())
        self.assertIsNotNone(self.db.query(UserKnowledgeDocument).filter_by(id="local_doc").first())


if __name__ == "__main__":
    unittest.main()
