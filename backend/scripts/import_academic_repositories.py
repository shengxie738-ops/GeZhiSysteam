from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.domain_record import DomainRecord
from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore
from app.services.gitea_account_service import (
    RepoPermission,
    create_or_rotate_gitea_token,
    ensure_gitea_account_for_user,
    ensure_repository_collaborators,
)
from app.services.gitea_service import GiteaService


ROOT = Path(r"D:\学术空间代码仓库")
ACCOUNT_FILE = Path(r"D:\演示账号的同学文件\演示账号的同学用户.txt")
WORK_ROOT = Path(r"D:\gezhisystem\.tmp_academic_repo_import")


@dataclass(frozen=True)
class Student:
    name: str
    student_id: str
    password: str


@dataclass(frozen=True)
class ProjectPlan:
    folder: str
    slug: str
    commit_at_local: str
    student_index: int


PROJECTS: list[ProjectPlan] = [
    ProjectPlan("个人信用积分与消费行为分析系统", "personal-credit-score-analysis", "2026-06-18T09:18:00+08:00", 0),
    ProjectPlan("个人学习打卡与成就系统", "personal-study-checkin-achievement", "2026-06-20T10:24:00+08:00", 1),
    ProjectPlan("公共停车场智能引导与预约系统", "smart-parking-guidance-booking", "2026-06-23T14:12:00+08:00", 2),
    ProjectPlan("城市交通流量预测与智能信号调度系统", "urban-traffic-flow-signal", "2026-06-25T15:36:00+08:00", 3),
    ProjectPlan("基于区块链的电子病历共享与隐私保护平台", "blockchain-emr-sharing-privacy", "2026-06-28T11:08:00+08:00", 4),
    ProjectPlan("大学生社团协作管理系统", "student-club-collaboration", "2026-07-01T13:45:00+08:00", 5),
    ProjectPlan("智慧校园失物招领平台", "campus-lost-found", "2026-07-04T09:52:00+08:00", 6),
    ProjectPlan("校园学习资料共享中心", "campus-learning-resource-share", "2026-07-07T16:10:00+08:00", 7),
    ProjectPlan("校园活动报名与电子签到系统", "campus-event-signin", "2026-07-10T10:33:00+08:00", 0),
    ProjectPlan("社区活动报名与志愿服务记录平台", "community-volunteer-service", "2026-07-13T15:18:00+08:00", 1),
]


def parse_students() -> list[Student]:
    text = ACCOUNT_FILE.read_text(encoding="utf-8")
    students: list[Student] = []
    pattern = re.compile(r"^\s*(?P<name>.+?)\s*[，,]\s*学号：\s*(?P<sid>\d+).*?密码：\s*(?P<pwd>\S+)", re.M)
    for match in pattern.finditer(text):
        students.append(
            Student(
                name=re.sub(r"\s+", "", match.group("name")),
                student_id=match.group("sid").strip(),
                password=match.group("pwd").strip(),
            )
        )
    if len(students) < 1:
        raise RuntimeError(f"No student accounts parsed from {ACCOUNT_FILE}")
    return students


def run(cmd: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> str:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=merged_env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        command = " ".join(cmd[:2]) if cmd else ""
        raise RuntimeError(f"{command} failed in {cwd}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result.stdout.strip()


def ensure_student_account(db, student: Student) -> UserAccount:
    account = db.query(UserAccount).filter(UserAccount.username == student.student_id).first()
    if not account:
        account = UserAccount(
            username=student.student_id,
            role="student",
            phone="",
            real_name=student.name,
            student_id=student.student_id,
            teacher_id="",
            class_name="计科 2301",
            password_hash=get_password_hash(student.password),
        )
        db.add(account)
    else:
        account.role = "student"
        account.real_name = student.name
        account.student_id = student.student_id
        account.class_name = account.class_name or "计科 2301"
        if not account.password_hash:
            account.password_hash = get_password_hash(student.password)
    if not db.query(StudentProfile).filter(StudentProfile.user_id == student.student_id).first():
        db.add(StudentProfile(user_id=student.student_id))
    db.commit()
    db.refresh(account)
    return account


def copy_project(source: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        source,
        dest,
        ignore=shutil.ignore_patterns(".git", ".idea", ".vscode"),
    )


def discover_classes(project_dir: Path) -> list[str]:
    classes: list[str] = []
    for file in project_dir.rglob("*"):
        if file.suffix not in {".py", ".java"}:
            continue
        if "__pycache__" in file.parts:
            continue
        text = file.read_text(encoding="utf-8", errors="ignore")
        if file.suffix == ".py":
            classes.extend(re.findall(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.M))
        else:
            classes.extend(re.findall(r"\b(?:class|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)", text))
    unique: list[str] = []
    for item in classes:
        if item not in unique:
            unique.append(item)
    return unique[:8] or ["ApiController", "BusinessService", "Repository", "Entity"]


def class_diagram_mermaid(classes: list[str]) -> str:
    lines = ["classDiagram"]
    for item in classes:
        lines.append(f"    class {item}")
    if len(classes) >= 2:
        lines.append(f"    {classes[0]} --> {classes[1]}")
    if len(classes) >= 3:
        lines.append(f"    {classes[1]} --> {classes[2]}")
    if len(classes) >= 4:
        for item in classes[3:]:
            lines.append(f"    {classes[1]} ..> {item}")
    return "\n".join(lines)


def write_class_diagram_svg(project_dir: Path, title: str, classes: list[str]) -> None:
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    width = 920
    height = 170 + len(classes) * 64
    service = classes[1] if len(classes) > 1 else classes[0]
    boxes: list[str] = []
    arrows: list[str] = []
    for index, name in enumerate(classes):
        x = 80 + (index % 3) * 280
        y = 90 + (index // 3) * 150
        boxes.append(
            f'<rect x="{x}" y="{y}" width="220" height="92" rx="8" fill="#f8fafc" stroke="#2563eb" stroke-width="2"/>'
            f'<text x="{x + 110}" y="{y + 34}" text-anchor="middle" font-size="17" font-weight="700" fill="#0f172a">{html.escape(name)}</text>'
            f'<line x1="{x}" y1="{y + 48}" x2="{x + 220}" y2="{y + 48}" stroke="#bfdbfe"/>'
            f'<text x="{x + 16}" y="{y + 72}" font-size="13" fill="#475569">+ handle()</text>'
        )
        if index > 0:
            prev_x = 80 + ((index - 1) % 3) * 280 + 220
            prev_y = 90 + ((index - 1) // 3) * 150 + 46
            arrows.append(
                f'<path d="M {prev_x} {prev_y} L {x} {y + 46}" fill="none" stroke="#64748b" stroke-width="1.8" marker-end="url(#arrow)"/>'
            )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#64748b"/>
    </marker>
  </defs>
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="40" y="44" font-size="24" font-weight="700" fill="#111827">{html.escape(title)} 核心类图</text>
  <text x="40" y="70" font-size="14" fill="#64748b">Controller, Service, Repository 与核心实体之间的主要依赖关系</text>
  {''.join(arrows)}
  {''.join(boxes)}
  <text x="40" y="{height - 34}" font-size="13" fill="#64748b">核心服务节点：{html.escape(service)}</text>
</svg>
'''
    (docs_dir / "class-diagram.svg").write_text(svg, encoding="utf-8", newline="\n")


def ensure_readme(project_dir: Path, title: str, classes: list[str]) -> tuple[str, str]:
    readme = project_dir / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
    else:
        text = f"# {title}\n\n课程项目代码仓库。\n"
    if not text.lstrip().startswith("#"):
        text = f"# {title}\n\n{text}"
    mermaid = class_diagram_mermaid(classes)
    if "docs/class-diagram.svg" not in text:
        text = text.rstrip() + "\n\n## 渲染类图\n\n![核心类图](docs/class-diagram.svg)\n"
    if "classDiagram" not in text:
        text += "\n\n```mermaid\n" + mermaid + "\n```\n"
    readme.write_text(text, encoding="utf-8", newline="\n")
    return text, mermaid


def infer_language(project_dir: Path) -> str:
    suffixes = {file.suffix.lower() for file in project_dir.rglob("*") if file.is_file()}
    if ".java" in suffixes:
        return "Java"
    if ".py" in suffixes:
        return "Python"
    if ".js" in suffixes:
        return "JavaScript"
    return "Other"


def description_from_readme(readme: str, title: str) -> str:
    for paragraph in re.split(r"\n\s*\n", readme):
        paragraph = paragraph.strip()
        if not paragraph or paragraph.startswith("#") or paragraph.startswith("```") or paragraph.startswith("!"):
            continue
        cleaned = re.sub(r"\s+", " ", paragraph)
        return cleaned[:280]
    return f"{title}课程项目代码仓库，包含前端页面、后端服务、接口文档、测试用例和类图说明。"


def file_tree(project_dir: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for item in sorted(project_dir.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if item.name == ".git":
            continue
        entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file", "lastCommit": "feat: initial import"})
    return entries[:20]


def git_date_env(commit_at_local: str) -> dict[str, str]:
    value = commit_at_local.replace("T", " ")
    return {"GIT_AUTHOR_DATE": value, "GIT_COMMITTER_DATE": value}


def commit_iso_utc(commit_at_local: str) -> str:
    return datetime.fromisoformat(commit_at_local).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def auth_env(username: str, token: str) -> dict[str, str]:
    credential = base64.b64encode(f"{username}:{token}".encode("utf-8")).decode("ascii")
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.http://127.0.0.1:3000/.extraHeader",
        "GIT_CONFIG_VALUE_0": f"Authorization: Basic {credential}",
    }


def import_project(db, gitea: GiteaService, plan: ProjectPlan, student: Student) -> dict[str, Any]:
    source = ROOT / plan.folder
    if not source.exists():
        raise FileNotFoundError(source)
    work_dir = WORK_ROOT / plan.slug
    copy_project(source, work_dir)

    account = ensure_student_account(db, student)
    identity = ensure_gitea_account_for_user(db, account, gitea=gitea, force_sync=True)
    token_result = create_or_rotate_gitea_token(db, account, gitea=gitea)

    classes = discover_classes(work_dir)
    write_class_diagram_svg(work_dir, plan.folder, classes)
    readme, mermaid = ensure_readme(work_dir, plan.folder, classes)
    language = infer_language(work_dir)
    description = description_from_readme(readme, plan.folder)

    repo = gitea.create_repository(name=plan.slug, description=description, private=False, auto_init=True)
    owner = repo.get("giteaOwner") or "campus"
    repo_name = repo.get("giteaRepo") or plan.slug
    webhook_configured = gitea.create_webhook(owner=owner, repo=repo_name, project_id=plan.slug, module="code_repository")
    permissions = ensure_repository_collaborators(
        db,
        owner,
        repo_name,
        [RepoPermission(student.student_id, "admin", "repository_author")],
        gitea=gitea,
    )

    run(["git", "init", "-b", "main"], work_dir)
    run(["git", "config", "user.name", student.name], work_dir)
    run(["git", "config", "user.email", f"{student.student_id}@gezhi.local"], work_dir)
    run(["git", "config", "core.quotepath", "false"], work_dir)
    run(["git", "add", "-A"], work_dir)
    run(["git", "commit", "-m", f"feat: initial import for {plan.slug}"], work_dir, env=git_date_env(plan.commit_at_local))
    sha = run(["git", "rev-parse", "HEAD"], work_dir)
    remote_url = f"http://127.0.0.1:3000/{owner}/{repo_name}.git"
    run(["git", "remote", "add", "origin", remote_url], work_dir)
    push_env = auth_env(identity.gitea_username, token_result.token)
    run(["git", "push", "--force", "origin", "main"], work_dir, env=push_env)

    commit_time = commit_iso_utc(plan.commit_at_local)
    store = JsonStore(db)
    for record in db.query(DomainRecord).filter(
        DomainRecord.module == "code_repository",
        DomainRecord.record_type == "project",
        DomainRecord.record_key == plan.slug,
    ):
        db.delete(record)
    db.commit()
    payload = {
        "id": plan.slug,
        "title": plan.folder,
        "slug": plan.slug,
        "description": description,
        "author": student.name,
        "authorId": student.student_id,
        "authorName": student.name,
        "avatar": f"/static/avatars/{student.student_id}.jpg",
        "language": language,
        "course": "软件工程课程设计",
        "tags": ["学术空间", "课程项目", language],
        "collaborators": [],
        "visibility": "public",
        "status": "active",
        "recommendScore": 80 + (plan.student_index % 8),
        "readme": readme,
        "readmeSyncedAt": commit_time,
        "createdAt": commit_time,
        "updatedAt": commit_time,
        "webhookConfigured": bool(webhook_configured),
        "giteaSyncStatus": "synced",
        "lastSyncedAt": commit_time,
        "recentCommits": [
            {
                "id": f"commit-{sha[:12]}",
                "sha": sha,
                "author": student.name,
                "branch": "main",
                "message": f"feat: initial import for {plan.slug}",
                "time": commit_time,
            }
        ],
        "pullRequests": [],
        "gitEvents": [
            {
                "id": f"event-{sha[:12]}",
                "type": "push",
                "actor": student.name,
                "text": f"{student.name} pushed main",
                "summary": f"{student.name} pushed main",
                "time": commit_time,
            }
        ],
        "aiGitCoachFeedback": [],
        "giteaCollaborators": permissions,
        "classDiagram": mermaid,
        "fileTree": file_tree(work_dir),
        **repo,
    }
    store.upsert("code_repository", "project", plan.slug, payload, owner_id=student.student_id, status="active")
    return {
        "slug": plan.slug,
        "title": plan.folder,
        "student": f"{student.name}({student.student_id})",
        "gitea_user": identity.gitea_username,
        "sha": sha,
        "commit_time": commit_time,
        "html_url": repo.get("htmlUrl"),
    }


def main() -> None:
    students = parse_students()
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    WORK_ROOT.mkdir(parents=True)
    db = SessionLocal()
    gitea = GiteaService()
    try:
        results = []
        for plan in PROJECTS:
            student = students[plan.student_index % len(students)]
            results.append(import_project(db, gitea, plan, student))
        print(json.dumps(results, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
