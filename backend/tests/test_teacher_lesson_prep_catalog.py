from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.schemas.teacher_lesson_prep import CoursewareResource, DocumentChunk
from app.services.teacher_lesson_prep.courseware_catalog import (
    DEFAULT_COURSE_DIRECTORIES,
    CoursewareCatalog,
)
from app.services.teacher_lesson_prep.document_retriever import DocumentRetriever


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_COURSE_NAMES = {
    "AI_technology": "人工智能技术",
    "Computer_ Organization": "计算机组成原理",
    "Database _Technology": "数据库系统原理",
    "computer_programming": "计算机程序设计",
    "data_structure": "数据结构",
}


@pytest.fixture(scope="module")
def catalog() -> CoursewareCatalog:
    return CoursewareCatalog(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def resources(catalog: CoursewareCatalog) -> list[CoursewareResource]:
    return catalog.scan()


def test_default_catalog_scans_only_the_five_allowed_course_directories(
    resources: list[CoursewareResource],
) -> None:
    assert DEFAULT_COURSE_DIRECTORIES == tuple(EXPECTED_COURSE_NAMES)
    assert {resource.course for resource in resources} == set(EXPECTED_COURSE_NAMES.values())
    for resource in resources:
        raw_course = resource.frontend_url.strip("/").split("/", 1)[0]
        assert resource.course == EXPECTED_COURSE_NAMES[raw_course]


def test_catalog_reports_the_expected_resource_totals_and_index_states(
    catalog: CoursewareCatalog,
    resources: list[CoursewareResource],
) -> None:
    summary = catalog.summarize(resources)

    assert summary.total == 97
    assert summary.pdf == 58
    assert summary.slides == 39
    assert summary.ppt == 38
    assert summary.pptx == 1

    legacy_ppt = [resource for resource in resources if resource.extension == ".ppt"]
    assert legacy_ppt
    assert all(resource.index_status == "UNSUPPORTED_LEGACY_PPT" for resource in legacy_ppt)
    assert all(resource.searchable is False for resource in legacy_ppt)


def test_resource_ids_are_stable_and_derived_from_normalized_frontend_paths(
    catalog: CoursewareCatalog,
    resources: list[CoursewareResource],
) -> None:
    rescanned = catalog.scan()

    assert [resource.id for resource in resources] == [resource.id for resource in rescanned]
    assert len({resource.id for resource in resources}) == len(resources)

    first = resources[0]
    normalized_path = first.frontend_url.lstrip("/").casefold()
    expected = hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()[:24]
    assert first.id == f"courseware-{expected}"


def test_catalog_rejects_paths_outside_the_allowed_course_directories(
    catalog: CoursewareCatalog,
) -> None:
    with pytest.raises(ValueError, match="allowed course directories"):
        catalog.resolve_frontend_path("../backend/requirements.txt")

    with pytest.raises(ValueError, match="allowed course directories"):
        catalog.resolve_frontend_path("AI_technology/../../backend/requirements.txt")

    with pytest.raises(ValueError, match="allowed course directories"):
        catalog.resolve_frontend_path("not_a_course/file.pdf")


def test_catalog_refreshes_when_courseware_changes() -> None:
    catalog = CoursewareCatalog(REPOSITORY_ROOT)
    first = catalog.list_resources()
    sample = REPOSITORY_ROOT / "frontend" / "data_structure" / "temporary-refresh-test.pdf"
    sample.write_bytes(b"%PDF-1.4\n%%EOF")
    try:
        second = catalog.list_resources()
        assert second.summary.total == first.summary.total + 1
    finally:
        sample.unlink(missing_ok=True)


def test_catalog_refreshes_when_extractor_dependency_becomes_available(monkeypatch) -> None:
    import app.services.teacher_lesson_prep.courseware_catalog as catalog_module

    real_find_spec = catalog_module.importlib.util.find_spec
    pypdf_available = False

    def fake_find_spec(name: str):
        if name == "pypdf":
            return object() if pypdf_available else None
        return real_find_spec(name)

    monkeypatch.setattr(catalog_module.importlib.util, "find_spec", fake_find_spec)
    catalog = CoursewareCatalog(REPOSITORY_ROOT)

    unavailable = catalog.list_resources()
    unavailable_pdf = next(
        item
        for item in unavailable.resources
        if item.frontend_url == "/AI_technology/16-Making_Simple_Decisions.pdf"
    )
    assert unavailable_pdf.index_status == "PYPDF_UNAVAILABLE"
    assert unavailable_pdf.searchable is False

    pypdf_available = True
    refreshed = catalog.list_resources()
    refreshed_pdf = next(
        item
        for item in refreshed.resources
        if item.frontend_url == "/AI_technology/16-Making_Simple_Decisions.pdf"
    )
    assert refreshed_pdf.index_status == "NOT_INDEXED"
    assert refreshed_pdf.searchable is True


def test_pdf_extraction_builds_page_chunks_and_returns_page_citations(
    catalog: CoursewareCatalog,
    resources: list[CoursewareResource],
) -> None:
    resource = next(
        item
        for item in resources
        if item.frontend_url == "/AI_technology/16-Making_Simple_Decisions.pdf"
    )
    retriever = DocumentRetriever(catalog)

    indexed = retriever.index_resource(resource.id)
    result = retriever.search("utility functions", resource_ids=[resource.id], limit=3)

    assert indexed.status == "INDEXED"
    assert indexed.chunks
    assert indexed.chunks[0].page >= 1
    assert [chunk.page for chunk in indexed.chunks] == sorted(chunk.page for chunk in indexed.chunks)
    assert all(chunk.resource_id == resource.id for chunk in indexed.chunks)
    assert result.matches
    assert result.matches[0].resource_id == resource.id
    assert result.matches[0].page >= 1
    assert "utility" in result.matches[0].excerpt.casefold()


def test_lightweight_ranking_supports_chinese_and_english_queries(
    catalog: CoursewareCatalog,
) -> None:
    retriever = DocumentRetriever(catalog)
    chunks = [
        DocumentChunk(
            resource_id="courseware-a",
            page=1,
            text="线性表是具有相同数据类型的有限序列，可使用顺序存储。",
        ),
        DocumentChunk(
            resource_id="courseware-b",
            page=2,
            text="A linked list stores elements in nodes connected by links.",
        ),
        DocumentChunk(
            resource_id="courseware-c",
            page=3,
            text="Database transactions preserve consistency and isolation.",
        ),
    ]

    chinese = retriever.rank_chunks("线性表 顺序存储", chunks, limit=2)
    english = retriever.rank_chunks("linked list nodes", chunks, limit=2)

    assert chinese[0].resource_id == "courseware-a"
    assert english[0].resource_id == "courseware-b"
    assert chinese[0].score > 0
    assert english[0].score > 0


def test_pptx_dependency_or_legacy_ppt_failures_are_explicit(
    catalog: CoursewareCatalog,
    resources: list[CoursewareResource],
) -> None:
    retriever = DocumentRetriever(catalog)
    legacy = next(resource for resource in resources if resource.extension == ".ppt")
    legacy_result = retriever.index_resource(legacy.id)

    assert legacy_result.status == "UNSUPPORTED_LEGACY_PPT"
    assert legacy_result.chunks == []
    assert "legacy .ppt" in legacy_result.message

    pptx = next(resource for resource in resources if resource.extension == ".pptx")
    pptx_result = retriever.index_resource(pptx.id)
    assert pptx_result.status in {"INDEXED", "PYTHON_PPTX_UNAVAILABLE"}
    if pptx_result.status == "PYTHON_PPTX_UNAVAILABLE":
        assert pptx_result.chunks == []
        assert "python-pptx" in pptx_result.message
