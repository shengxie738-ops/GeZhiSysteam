"""Import 仓库数据A projects into academic code repository + Gitea."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.core.config import settings
from app.core.database import SessionLocal
from app.repositories.json_store import JsonStore
from app.services.gitea_service import GiteaService, normalize_repo_slug
from app.utils.datetime import utc_now_iso

MODULE = "code_repository"
PROJECT = "project"
DATA_ROOT = Path(r"D:\软件杯代码仓库数据\仓库数据A")

GITIGNORE_LINES = [
    "__pycache__/",
    "*.pyc",
    ".pytest_cache/",
    "node_modules/",
    "target/",
    "venv/",
    ".venv/",
    ".env",
    ".idea/",
    ".vscode/",
    "*.log",
    ".DS_Store",
]

STUDENTS = [
    "江景珩",
    "陆知屿",
    "沈砚辞",
    "顾星辞",
    "苏沐辰",
    "温景然",
    "傅斯年",
    "萧亦辰",
    "季云舟",
    "贺临川",
    "许清和",
    "宋柏屹",
    "程砚舟",
    "秦屿川",
    "裴书尧",
]

BATCH_PROJECTS: list[dict[str, str]] = [
    {"folder": "仓库1", "slug": "smart-dormitory-system", "title": "智慧宿舍管理系统", "language": "Java", "course": "物联网应用"},
    {"folder": "仓库2", "slug": "ai-emotion-companion", "title": "AI情绪陪伴助手", "language": "Java", "course": "软件工程"},
    {"folder": "仓库3", "slug": "ai-medication-reminder", "title": "AI用药提醒系统", "language": "Java", "course": "医疗健康信息化"},
    {"folder": "仓库4", "slug": "ai-green-life-assistant", "title": "AI绿色生活助手", "language": "Java", "course": "软件工程"},
    {"folder": "仓库6", "slug": "ai-campus-life-assistant", "title": "AI校园生活助手", "language": "Java", "course": "软件工程"},
    {"folder": "仓库7", "slug": "ai-family-life-manager", "title": "AI家庭智慧生活管家", "language": "Java", "course": "软件工程"},
    {"folder": "仓库8", "slug": "ai-smart-campus-platform", "title": "AI智慧校园平台", "language": "JavaScript", "course": "Web开发"},
    {"folder": "仓库9", "slug": "ai-student-portfolio-hub", "title": "AI学生作品集中心", "language": "Python", "course": "软件工程"},
    {"folder": "仓库10", "slug": "huffman-coding-team", "title": "哈夫曼压缩与解压引擎", "language": "Python", "course": "数据结构"},
    {"folder": "AI项目仓库1", "slug": "student-grade-prediction-ai", "title": "学生成绩预测AI", "language": "Python", "course": "机器学习"},
    {"folder": "AI项目仓库2", "slug": "handwritten-digit-recognition-ai", "title": "手写数字识别AI", "language": "Python", "course": "深度学习"},
    {"folder": "AI项目仓库3", "slug": "course-review-sentiment-analysis", "title": "课程评价情感分析", "language": "Python", "course": "自然语言处理"},
    {"folder": "AI项目仓库4", "slug": "learning-resource-recommendation-ai", "title": "学习资源推荐AI", "language": "Python", "course": "推荐系统"},
    {"folder": "AI项目仓库5", "slug": "classroom-attention-detection-ai", "title": "课堂注意力检测AI", "language": "Python", "course": "计算机视觉"},
    {"folder": "AI项目仓库6", "slug": "course-knowledge-graph-ai", "title": "课程知识图谱AI", "language": "Python", "course": "知识工程"},
]

LANG_BY_EXT = {
    ".py": "Python",
    ".java": "Java",
    ".vue": "Vue",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".cpp": "C++",
    ".go": "Go",
}


def _read_students() -> list[str]:
    path = DATA_ROOT / "学生姓名.txt"
    if not path.is_file():
        return STUDENTS[:15]
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\d+\.\s*(.+)", line.strip())
        if match:
            names.append(match.group(1).strip())
    return names[:15] if len(names) >= 15 else STUDENTS[:15]


def _resolve_source(folder: str) -> Path | None:
    root = DATA_ROOT / folder
    if not root.is_dir():
        return None
    entries = list(root.iterdir())
    subdirs = [item for item in entries if item.is_dir()]
    files = [item for item in entries if item.is_file()]
    if folder == "仓库8":
        return root
    if len(subdirs) == 1 and not files:
        return subdirs[0]
    if subdirs or files:
        return root
    return None


def _source_has_content(source: Path) -> bool:
    if not source or not source.is_dir():
        return False
    for path in source.rglob("*"):
        if path.is_file() and path.name != ".gitkeep":
            return True
    return False


def _read_title_description(source: Path, fallback_title: str) -> tuple[str, str]:
    readme = source / "README.md"
    title = fallback_title
    description = fallback_title
    if readme.is_file():
        lines = [line.strip() for line in readme.read_text(encoding="utf-8", errors="ignore").splitlines()]
        if lines:
            title = lines[0].lstrip("# ").strip() or fallback_title
        for line in lines[1:]:
            if line and not line.startswith("#"):
                description = line
                break
    return title, description


def _detect_language(source: Path, fallback: str) -> str:
    counts: Counter[str] = Counter()
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in LANG_BY_EXT:
            counts[LANG_BY_EXT[ext]] += 1
    if counts:
        return counts.most_common(1)[0][0]
    return fallback


def _generate_publish_times(count: int, *, seed: int = 20260708) -> list[datetime]:
    rng = random.Random(seed)
    now = datetime.now(timezone(timedelta(hours=8)))
    start = now - timedelta(days=30)
    slots: set[tuple[int, int, int, int, int]] = set()
    results: list[datetime] = []
    tz = timezone(timedelta(hours=8))
    while len(results) < count:
        day_offset = rng.randint(0, 29)
        hour = rng.randint(9, 17)
        minute = rng.choice([3, 7, 11, 14, 18, 22, 26, 31, 36, 41, 47, 52, 58])
        day = start + timedelta(days=day_offset)
        key = (day.year, day.month, day.day, hour, minute)
        if key in slots:
            continue
        slots.add(key)
        results.append(datetime(day.year, day.month, day.day, hour, minute, 0, tzinfo=tz))
    results.sort()
    return results


def _to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_env(commit_dt: datetime) -> dict[str, str]:
    stamp = commit_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    stamp = f"{stamp[:-2]}:{stamp[-2:]}"
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = stamp
    env["GIT_COMMITTER_DATE"] = stamp
    return env


def _run_git(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")


def _clone_url(owner: str, repo: str) -> str:
    token = settings.GITEA_API_TOKEN
    base = settings.GITEA_BASE_URL.rstrip("/")
    if token:
        return f"{base.replace('://', f'://oauth2:{token}@')}/{owner}/{repo}.git"
    return f"{base}/{owner}/{repo}.git"


def _push_source_to_gitea(
    *,
    source: Path,
    owner: str,
    repo: str,
    branch: str,
    author_name: str,
    commit_dt: datetime,
) -> str:
    with tempfile.TemporaryDirectory(prefix="repo-a-import-") as tmp:
        work = Path(tmp)
        shutil.copytree(source, work, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
        gitignore = work / ".gitignore"
        existing = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines() if gitignore.is_file() else []
        merged = sorted(set(line.strip() for line in [*existing, *GITIGNORE_LINES] if line.strip()))
        gitignore.write_text("\n".join(merged) + "\n", encoding="utf-8")

        env = _git_env(commit_dt)
        _run_git(["init", "-b", branch], cwd=work)
        _run_git(["config", "user.name", author_name], cwd=work)
        _run_git(["config", "user.email", f"{normalize_repo_slug(author_name)}@gezhi.local"], cwd=work)
        _run_git(["add", "-A"], cwd=work)
        _run_git(["commit", "-m", f"feat: initial import for {repo}"], cwd=work, env=env)
        _run_git(["remote", "add", "origin", _clone_url(owner, repo)], cwd=work)
        _run_git(["push", "-u", "origin", branch, "--force"], cwd=work)
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(work), text=True).strip()
        return sha


def _slug_exists(store: JsonStore, slug: str) -> bool:
    return store.get_payload(MODULE, PROJECT, slug) is not None


def _delete_existing(store: JsonStore, gitea: GiteaService, slug: str) -> None:
    project = store.get_payload(MODULE, PROJECT, slug)
    if project:
        owner = project.get("giteaOwner") or settings.GITEA_ORG or "campus"
        repo = project.get("giteaRepo") or slug
        try:
            gitea.delete_repository(owner=owner, repo=repo)
        except Exception:
            pass
        record = store.get_record(MODULE, PROJECT, slug)
        if record:
            store.db.delete(record)
            store.db.commit()


def import_one(
    db,
    *,
    spec: dict[str, str],
    author_name: str,
    publish_at: datetime,
    gitea: GiteaService,
    force: bool = False,
) -> dict[str, Any]:
    store = JsonStore(db)
    slug = normalize_repo_slug(spec["slug"])
    source = _resolve_source(spec["folder"])
    if source is None or not _source_has_content(source):
        return {"slug": slug, "status": "skipped", "reason": "empty source folder", "folder": spec["folder"]}

    if _slug_exists(store, slug):
        if not force:
            return {"slug": slug, "status": "skipped", "reason": "already exists"}
        _delete_existing(store, gitea, slug)

    title, description = _read_title_description(source, spec["title"])
    language = _detect_language(source, spec["language"])
    repo_meta = gitea.create_repository(name=slug, description=description, private=False, auto_init=False)
    owner = repo_meta.get("giteaOwner") or settings.GITEA_ORG or "campus"
    branch = repo_meta.get("defaultBranch") or "main"

    webhook_configured = False
    create_webhook = getattr(gitea, "create_webhook", None)
    if callable(create_webhook):
        webhook_configured = bool(create_webhook(owner=owner, repo=slug, project_id=slug, module="code_repository"))

    commit_sha = _push_source_to_gitea(
        source=source,
        owner=owner,
        repo=slug,
        branch=branch,
        author_name=author_name,
        commit_dt=publish_at,
    )
    created_iso = _to_iso(publish_at)
    project = {
        "id": slug,
        "title": title,
        "slug": slug,
        "description": description,
        "author": author_name,
        "authorName": author_name,
        "avatar": "",
        "language": language,
        "course": spec["course"],
        "tags": [spec["course"], language, "仓库A"],
        "collaborators": [],
        "visibility": "public",
        "status": "active",
        "recommendScore": 0,
        "readme": "",
        "readmeSyncedAt": created_iso,
        "createdAt": created_iso,
        "updatedAt": created_iso,
        "webhookConfigured": webhook_configured,
        "giteaSyncStatus": "synced",
        "lastSyncedAt": created_iso,
        "recentCommits": [
            {
                "id": f"commit-{commit_sha[:12]}",
                "sha": commit_sha,
                "author": author_name,
                "branch": branch,
                "message": f"feat: initial import for {slug}",
                "time": created_iso,
            }
        ],
        "pullRequests": [],
        "gitEvents": [
            {
                "id": f"event-{commit_sha[:12]}",
                "type": "push",
                "actor": author_name,
                "summary": f"{author_name} pushed {branch}",
                "time": created_iso,
            }
        ],
        "aiGitCoachFeedback": [],
        "giteaCollaborators": [],
        **repo_meta,
    }
    store.upsert(MODULE, PROJECT, slug, project, owner_id=author_name, status="active")
    return {
        "slug": slug,
        "status": "imported",
        "author": author_name,
        "createdAt": created_iso,
        "cloneUrl": repo_meta.get("cloneUrl"),
        "commit": commit_sha,
        "folder": spec["folder"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import 仓库数据A into code repository + Gitea")
    parser.add_argument("--force", action="store_true", help="Replace existing projects with same slug")
    parser.add_argument("--dry-run", action="store_true", help="Validate sources only")
    parser.add_argument("--only", default="", help="Comma-separated slugs to import")
    args = parser.parse_args()

    if not settings.GITEA_ENABLED or not settings.GITEA_API_TOKEN:
        print("GITEA_ENABLED and GITEA_API_TOKEN must be configured.", file=sys.stderr)
        return 1

    students = _read_students()
    publish_times = _generate_publish_times(len(BATCH_PROJECTS))
    only = {item.strip() for item in args.only.split(",") if item.strip()}

    preview: list[dict[str, Any]] = []
    for index, spec in enumerate(BATCH_PROJECTS):
        source = _resolve_source(spec["folder"])
        preview.append(
            {
                "folder": spec["folder"],
                "slug": spec["slug"],
                "author": students[index],
                "publishAt": publish_times[index].isoformat(),
                "hasContent": _source_has_content(source) if source else False,
                "source": str(source) if source else None,
            }
        )

    if args.dry_run:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    db = SessionLocal()
    gitea = GiteaService()
    results: list[dict[str, Any]] = []
    try:
        for index, spec in enumerate(BATCH_PROJECTS):
            if only and spec["slug"] not in only:
                continue
            try:
                result = import_one(
                    db,
                    spec=spec,
                    author_name=students[index],
                    publish_at=publish_times[index],
                    gitea=gitea,
                    force=args.force,
                )
            except Exception as exc:
                result = {"slug": spec["slug"], "status": "failed", "error": str(exc), "folder": spec["folder"]}
            results.append(result)
            print(json.dumps(result, ensure_ascii=False))
        print(json.dumps({"summary": results}, ensure_ascii=False, indent=2))
        failed = [item for item in results if item.get("status") == "failed"]
        skipped_empty = [item for item in results if item.get("status") == "skipped" and item.get("reason") == "empty source folder"]
        return 1 if failed else 0 if not skipped_empty else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
