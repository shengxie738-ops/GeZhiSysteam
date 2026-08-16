from app.services.learning_diagnosis import knowledge_retriever


def test_auto_retriever_uses_loaded_settings_when_process_env_is_empty(monkeypatch):
    monkeypatch.delenv("RAGFLOW_BASE_URL", raising=False)
    monkeypatch.delenv("RAGFLOW_API_KEY", raising=False)
    monkeypatch.delenv("RAGFLOW_DATASET_ID", raising=False)
    monkeypatch.setattr(knowledge_retriever.settings, "RAGFLOW_BASE_URL", "https://ragflow.example/api/v1")
    monkeypatch.setattr(knowledge_retriever.settings, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(knowledge_retriever.settings, "RAGFLOW_DATASET_ID", "dataset-default")
    monkeypatch.setattr(knowledge_retriever, "get_course_datasets", lambda: [])
    monkeypatch.setattr(knowledge_retriever, "get_public_dataset_ids", lambda: [])

    retriever = knowledge_retriever.select_knowledge_retriever("auto")

    assert isinstance(retriever, knowledge_retriever.RagFlowKnowledgeRetriever)
    assert retriever.base_url == "https://ragflow.example/api/v1"
    assert retriever.api_key == "test-key"
    assert retriever.dataset_ids == ["dataset-default"]
