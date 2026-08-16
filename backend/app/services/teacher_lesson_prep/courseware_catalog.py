from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path, PurePosixPath
from typing import Iterable

from app.schemas.teacher_lesson_prep import (
    CoursewareCatalogResult,
    CoursewareResource,
    CoursewareSummary,
)


DEFAULT_COURSE_DIRECTORIES = (
    "AI_technology",
    "Computer_ Organization",
    "Database _Technology",
    "computer_programming",
    "data_structure",
)
COURSE_DISPLAY_NAMES = {
    "AI_technology": "人工智能技术",
    "Computer_ Organization": "计算机组成原理",
    "Database _Technology": "数据库系统原理",
    "computer_programming": "计算机程序设计",
    "data_structure": "数据结构",
}
SUPPORTED_EXTENSIONS = frozenset({".pdf", ".ppt", ".pptx"})


class CoursewareCatalog:
    def __init__(
        self,
        repository_root: str | Path,
        course_directories: Iterable[str] = DEFAULT_COURSE_DIRECTORIES,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.frontend_root = (self.repository_root / "frontend").resolve()
        self.course_directories = tuple(course_directories)
        if self.course_directories != DEFAULT_COURSE_DIRECTORIES:
            raise ValueError("course directories must match the five allowed course directories")
        if set(COURSE_DISPLAY_NAMES) != set(DEFAULT_COURSE_DIRECTORIES):
            raise ValueError("course display names must cover the five allowed course directories")
        self._resource_cache: dict[str, CoursewareResource] | None = None
        self._catalog_signature: tuple[tuple[str, int, int], ...] | None = None
        self._dependency_signature: tuple[bool, bool] | None = None

    def scan(self, *, refresh: bool = False) -> list[CoursewareResource]:
        signature = self._build_signature()
        dependency_signature = self._build_dependency_signature()
        if (
            self._resource_cache is not None
            and not refresh
            and signature == self._catalog_signature
            and dependency_signature == self._dependency_signature
        ):
            return [resource.model_copy(deep=True) for resource in self._resource_cache.values()]

        resources: list[CoursewareResource] = []
        for course in self.course_directories:
            course_root = (self.frontend_root / course).resolve()
            if not course_root.is_dir() or not course_root.is_relative_to(self.frontend_root):
                continue
            paths = sorted(
                (
                    path
                    for path in course_root.rglob("*")
                    if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
                ),
                key=lambda path: path.relative_to(self.frontend_root).as_posix().casefold(),
            )
            for path in paths:
                resolved = path.resolve()
                if not resolved.is_relative_to(course_root):
                    continue
                resources.append(self._build_resource(course, resolved))

        resources.sort(key=lambda item: item.frontend_url.casefold())
        self._resource_cache = {resource.id: resource for resource in resources}
        self._catalog_signature = signature
        self._dependency_signature = dependency_signature
        return [resource.model_copy(deep=True) for resource in resources]

    def list_resources(self, *, refresh: bool = False) -> CoursewareCatalogResult:
        resources = self.scan(refresh=refresh)
        return CoursewareCatalogResult(summary=self.summarize(resources), resources=resources)

    def summarize(self, resources: Iterable[CoursewareResource] | None = None) -> CoursewareSummary:
        resource_list = list(resources) if resources is not None else self.scan()
        pdf = sum(resource.extension == ".pdf" for resource in resource_list)
        ppt = sum(resource.extension == ".ppt" for resource in resource_list)
        pptx = sum(resource.extension == ".pptx" for resource in resource_list)
        return CoursewareSummary(
            total=len(resource_list),
            pdf=pdf,
            slides=ppt + pptx,
            ppt=ppt,
            pptx=pptx,
            searchable=sum(resource.searchable for resource in resource_list),
        )

    def get_resource(self, resource_id: str) -> CoursewareResource:
        self.scan()
        assert self._resource_cache is not None
        resource = self._resource_cache.get(resource_id)
        if resource is None:
            raise ValueError(f"unknown courseware resource: {resource_id}")
        return resource.model_copy(deep=True)

    def resolve_resource_path(self, resource_id: str) -> Path:
        return self.resolve_frontend_path(self.get_resource(resource_id).frontend_url)

    def resolve_frontend_path(self, relative_path: str | Path) -> Path:
        raw_path = str(relative_path).replace("\\", "/").lstrip("/")
        parsed = PurePosixPath(raw_path)
        if parsed.is_absolute() or not parsed.parts or ".." in parsed.parts:
            raise ValueError("path must stay within the five allowed course directories")
        course = parsed.parts[0]
        if course not in self.course_directories:
            raise ValueError("path must stay within the five allowed course directories")

        course_root = (self.frontend_root / course).resolve()
        candidate = (self.frontend_root / Path(*parsed.parts)).resolve()
        if not candidate.is_relative_to(course_root):
            raise ValueError("path must stay within the five allowed course directories")
        return candidate

    def _build_resource(self, course: str, path: Path) -> CoursewareResource:
        relative_path = path.relative_to(self.frontend_root).as_posix()
        frontend_url = f"/{relative_path}"
        extension = path.suffix.casefold()
        status, searchable = self._initial_index_state(extension)
        normalized_path = relative_path.casefold()
        digest = hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()[:24]
        return CoursewareResource(
            id=f"courseware-{digest}",
            course=COURSE_DISPLAY_NAMES[course],
            name=path.name,
            filename=path.name,
            extension=extension,
            size_bytes=path.stat().st_size,
            frontend_url=frontend_url,
            index_status=status,
            searchable=searchable,
        )

    def _build_signature(self) -> tuple[tuple[str, int, int], ...]:
        values = []
        for course in self.course_directories:
            course_root = (self.frontend_root / course).resolve()
            if not course_root.is_dir() or not course_root.is_relative_to(self.frontend_root):
                continue
            for path in course_root.rglob("*"):
                if not path.is_file() or path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
                    continue
                resolved = path.resolve()
                if not resolved.is_relative_to(course_root):
                    continue
                stat = resolved.stat()
                values.append((resolved.relative_to(self.frontend_root).as_posix().casefold(), stat.st_mtime_ns, stat.st_size))
        return tuple(sorted(values))

    @staticmethod
    def _build_dependency_signature() -> tuple[bool, bool]:
        return (
            importlib.util.find_spec("pypdf") is not None,
            importlib.util.find_spec("pptx") is not None,
        )

    @staticmethod
    def _initial_index_state(extension: str) -> tuple[str, bool]:
        if extension == ".ppt":
            return "UNSUPPORTED_LEGACY_PPT", False
        if extension == ".pptx" and importlib.util.find_spec("pptx") is None:
            return "PYTHON_PPTX_UNAVAILABLE", False
        if extension == ".pdf" and importlib.util.find_spec("pypdf") is None:
            return "PYPDF_UNAVAILABLE", False
        return "NOT_INDEXED", True
