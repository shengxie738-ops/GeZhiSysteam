from __future__ import annotations

import copy
import re
from typing import Any

import requests

from app.core.config import settings


REQUEST_TIMEOUT_SECONDS = 30

PDF_EXTENSIONS = {"pdf"}

SUPPORTED_KNOWLEDGE_EXTENSIONS = PDF_EXTENSIONS

PDF_PRESENTATION_PARSER_CONFIG = {
    "layout_recognize": "DeepDOC",
    "raptor": {"use_raptor": False},
}


def _get_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.RAGFLOW_API_KEY}"}


def _json_headers() -> dict[str, str]:
    return {**_get_headers(), "Content-Type": "application/json"}


def _raise_ragflow_error(prefix: str, resp: requests.Response) -> None:
    try:
        body: Any = resp.json()
    except Exception:
        body = resp.text
    raise RuntimeError(f"{prefix}: status={resp.status_code}, body={body}")


def _base_url() -> str:
    return settings.RAGFLOW_BASE_URL.rstrip("/")


def _get_extension(filename: str) -> str:
    name = (filename or "").strip()
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def classify_supported_file(filename: str) -> dict[str, Any]:
    """Return RAGFlow parser settings for a supported knowledge-base file."""
    extension = _get_extension(filename)
    if extension not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
        supported = ", ".join(f".{ext}" for ext in sorted(SUPPORTED_KNOWLEDGE_EXTENSIONS))
        actual = f".{extension}" if extension else "<none>"
        raise ValueError(f"unsupported file type: {actual}. Supported file types: {supported}")

    return {
        "extension": extension,
        "file_type": "pdf",
        "chunk_method": "presentation",
        "parser_config": copy.deepcopy(PDF_PRESENTATION_PARSER_CONFIG),
    }


def build_document_metadata(user_id: str, repository_id: str, filename: str) -> dict[str, str]:
    profile = classify_supported_file(filename)
    return {
        "source": "student_private",
        "user_id": (user_id or "").strip(),
        "repository_id": (repository_id or "").strip(),
        "file_type": profile["file_type"],
        "extension": profile["extension"],
        "filename": filename or "",
    }


def build_repository_metadata_condition(repository_id: str | None) -> dict[str, Any] | None:
    repo_id = (repository_id or "").strip()
    if not repo_id:
        return None
    return {
        "logic": "and",
        "conditions": [
            {
                "name": "repository_id",
                "comparison_operator": "is",
                "value": repo_id,
            }
        ],
    }


def guess_cross_languages(query: str) -> list[str]:
    text = query or ""
    has_cjk = bool(re.search(r"[\u3400-\u9fff]", text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    if has_cjk and has_latin:
        return ["Chinese", "English"]
    if has_cjk:
        return ["English"]
    if has_latin:
        return ["Chinese"]
    return []


def map_ragflow_run_to_status(run: str | int | None) -> str:
    normalized = str(run or "").strip().upper()
    mapping = {
        "0": "queued",
        "UNSTART": "queued",
        "1": "parsing",
        "RUNNING": "parsing",
        "2": "cancelled",
        "CANCEL": "cancelled",
        "3": "parsed",
        "DONE": "parsed",
        "4": "failed",
        "FAIL": "failed",
    }
    return mapping.get(normalized, "parsing")


def create_user_dataset(user_id: str) -> str:
    """Create one private RAGFlow dataset for a student."""
    url = f"{_base_url()}/datasets"
    payload = {"name": f"user_private_{user_id}"}
    resp = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to create dataset: {resp.text}")

    res_json = resp.json()
    if res_json.get("code") != 0:
        raise RuntimeError(f"RAGFlow error creating dataset: {res_json.get('message')}")

    return res_json["data"]["id"]


def update_document_config(
    dataset_id: str,
    document_id: str,
    *,
    metadata: dict[str, Any] | None = None,
    parser: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {}
    if metadata:
        payload["meta_fields"] = metadata
    if parser:
        payload["chunk_method"] = parser["chunk_method"]
        payload["parser_config"] = parser.get("parser_config", {})
    if not payload:
        return

    url = f"{_base_url()}/datasets/{dataset_id}/documents/{document_id}"
    resp = requests.put(url, json=payload, headers=_json_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    if resp.status_code != 200:
        _raise_ragflow_error("Failed to update document config", resp)
    res_json = resp.json()
    if res_json.get("code") != 0:
        raise RuntimeError(f"RAGFlow error updating document config: {res_json.get('message')}")


def upload_and_run_document(
    dataset_id: str,
    file_bytes: bytes,
    filename: str,
    *,
    metadata: dict[str, Any] | None = None,
    parser: dict[str, Any] | None = None,
) -> str:
    """Upload a document to RAGFlow, configure metadata/parser, then start parsing."""
    headers = _get_headers()

    upload_url = f"{_base_url()}/datasets/{dataset_id}/documents"
    files = {"file": (filename, file_bytes, "application/octet-stream")}
    upload_resp = requests.post(
        upload_url,
        files=files,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if upload_resp.status_code != 200:
        raise RuntimeError(f"Failed to upload document: {upload_resp.text}")

    upload_json = upload_resp.json()
    if upload_json.get("code") != 0:
        raise RuntimeError(f"RAGFlow error uploading document: {upload_json.get('message')}")

    docs = upload_json.get("data", [])
    if isinstance(docs, list) and docs:
        doc_id = docs[0].get("id")
    elif isinstance(docs, dict):
        doc_id = docs.get("id")
    else:
        raise RuntimeError(f"Could not extract doc_id from upload response: {upload_json}")
    if not doc_id:
        raise RuntimeError(f"RAGFlow upload response did not include document id: {upload_json}")

    update_document_config(dataset_id, doc_id, metadata=metadata, parser=parser)

    parse_url = f"{_base_url()}/datasets/{dataset_id}/chunks"
    parse_resp = requests.post(
        parse_url,
        json={"document_ids": [doc_id]},
        headers=_json_headers(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if parse_resp.status_code in {404, 405}:
        legacy_parse_url = f"{_base_url()}/datasets/{dataset_id}/documents/parse"
        parse_resp = requests.post(
            legacy_parse_url,
            json={"document_ids": [doc_id]},
            headers=_json_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    if parse_resp.status_code != 200 or parse_resp.json().get("code") != 0:
        raise RuntimeError(f"Failed to start document parsing: status={parse_resp.status_code}, body={parse_resp.text}")

    return doc_id


def list_dataset_documents(dataset_id: str, *, document_id: str | None = None, page_size: int = 100) -> list[dict[str, Any]]:
    if not dataset_id:
        return []
    params: dict[str, Any] = {"page": 1, "page_size": page_size}
    if document_id:
        params["id"] = document_id

    url = f"{_base_url()}/datasets/{dataset_id}/documents"
    resp = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    if resp.status_code != 200:
        _raise_ragflow_error("Failed to list documents", resp)
    res_json = resp.json()
    if res_json.get("code") != 0:
        raise RuntimeError(f"RAGFlow error listing documents: {res_json.get('message')}")
    data = res_json.get("data", {})
    if isinstance(data, dict):
        return data.get("docs", []) or []
    if isinstance(data, list):
        return data
    return []


def delete_document_from_dataset(dataset_id: str, document_id: str) -> None:
    """Delete one document from the user's single RAGFlow dataset."""
    if not dataset_id or not document_id:
        raise RuntimeError("dataset_id and document_id are required")

    url = f"{_base_url()}/datasets/{dataset_id}/documents"
    resp = requests.delete(
        url,
        json={"ids": [document_id]},
        headers=_json_headers(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if resp.status_code != 200:
        _raise_ragflow_error("Failed to delete document", resp)

    res_json = resp.json()
    if res_json.get("code") != 0:
        raise RuntimeError(f"RAGFlow error deleting document: {res_json.get('message')}")


def retrieve_from_datasets(
    dataset_ids: list,
    query: str,
    top_k_per_dataset: int = 4,
    *,
    cross_languages: list[str] | None = None,
    metadata_condition: dict[str, Any] | None = None,
) -> list:
    """
    Retrieve chunks from one or more RAGFlow datasets and merge the results.
    """
    if not dataset_ids:
        return []

    valid_dataset_ids = [ds_id for ds_id in dataset_ids if ds_id]
    if not valid_dataset_ids:
        return []

    languages = guess_cross_languages(query) if cross_languages is None else cross_languages
    payload: dict[str, Any] = {
        "dataset_ids": valid_dataset_ids,
        "question": query,
        "similarity_threshold": 0.2,
        "vector_similarity_weight": 0.3,
        "top_k": top_k_per_dataset * len(valid_dataset_ids),
        "keyword": True,
    }
    if languages:
        payload["cross_languages"] = languages
    if metadata_condition:
        payload["metadata_condition"] = metadata_condition

    try:
        resp = requests.post(f"{_base_url()}/retrieval", json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            print(f"[RAG] Retrieval failed: HTTP {resp.status_code} - {resp.text}")
            return []

        res_json = resp.json()
        if res_json.get("code") != 0:
            print(f"[RAG] Retrieval API error: {res_json.get('message')}")
            return []

        return res_json.get("data", {}).get("chunks", [])
    except Exception as e:
        print(f"[RAG] Exception during multi-dataset retrieval: {e}")
        return []


def get_public_dataset_ids() -> list:
    """Read public knowledge-base dataset IDs from environment variables."""
    raw = settings.RAGFLOW_PUBLIC_DATASET_IDS
    return [ds_id.strip() for ds_id in raw.split(",") if ds_id.strip()]


def get_course_datasets() -> list[dict[str, str]]:
    """Return course knowledge-base list with name and id for frontend selector."""
    import json
    raw = settings.RAGFLOW_COURSE_DATASETS
    if not raw:
        return []
    try:
        datasets = json.loads(raw)
        return [{"name": ds.get("name", ""), "id": ds.get("id", "")} for ds in datasets if ds.get("id")]
    except (json.JSONDecodeError, TypeError):
        return []
