from copy import deepcopy
import re
import threading
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.gitea_account_binding import GiteaAccountBinding
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore
from app.services.gitea_account_service import RepoPermission, ensure_repository_collaborators, match_campus_user_from_gitea_event
from app.services.gitea_service import GiteaService, is_stale_gitea_url, normalize_repo_slug
from app.utils.datetime import format_chinese_datetime
from app.services.git_workflow_rules import evaluate_git_workflow


MODULE = "team_collaboration_git"
PROJECT = "project"
_SYNC_LOCKS: dict[str, threading.Lock] = {}
_SYNC_LOCKS_GUARD = threading.Lock()

# Gitea 系统账号 / 管理员账号黑名单：这些账号产生的提交不计入学生成员进度
_GITEA_SYSTEM_LOGINS: frozenset[str] = frozenset({
    "campus-admin", "campus-admin-gitea", "campus-admin-web",
    "gitea-actions", "gitea", "teacher", "admin",
    "git", "root", "system", "bot", "ci",
})
_REAL_GITEA_ROW_SOURCES: frozenset[str] = frozenset({"gitea", "gitea_webhook"})


def _normalize_gitea_login(login: str | None) -> str:
    value = str(login or "").strip().lower()
    value = re.sub(r"\s*\(.*$", "", value).strip()
    value = value.replace("_", "-")
    value = re.sub(r"[^a-z0-9.-]+", "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-.")


def _is_gitea_system_login(login: str) -> bool:
    """判断是否为 Gitea 系统/管理账号，忽略大小写。"""
    normalized = _normalize_gitea_login(login)
    if not normalized:
        return False
    if normalized in _GITEA_SYSTEM_LOGINS:
        return True
    return any(normalized.startswith(f"{prefix}-") for prefix in _GITEA_SYSTEM_LOGINS)


def _is_real_gitea_row(item: dict[str, Any]) -> bool:
    return str((item or {}).get("source") or "").strip() in _REAL_GITEA_ROW_SOURCES


def _is_gitea_system_commit(commit: dict[str, Any]) -> bool:
    candidates = [
        commit.get("authorLogin"),
        commit.get("authorName"),
        commit.get("committerName"),
    ]
    email = str(commit.get("authorEmail") or "").strip()
    if "@" in email:
        candidates.append(email.split("@", 1)[0])
    author = commit.get("author") if isinstance(commit.get("author"), dict) else {}
    candidates.extend([author.get("username"), author.get("name")])
    author_email = str(author.get("email") or "").strip()
    if "@" in author_email:
        candidates.append(author_email.split("@", 1)[0])
    return any(_is_gitea_system_login(str(candidate or "")) for candidate in candidates)

MOCK_CLASS_STUDENTS = [
    {"username": "zhanghua", "name": "张华", "studentId": "20230001", "className": "计科 2301", "source": "mock"},
    {"username": "liming", "name": "李明", "studentId": "20230002", "className": "计科 2301", "source": "mock"},
    {"username": "wanglei", "name": "王磊", "studentId": "20230003", "className": "计科 2301", "source": "mock"},
    {"username": "zhaolei", "name": "赵雷", "studentId": "20230004", "className": "计科 2301", "source": "mock"},
    {"username": "chensisi", "name": "陈思思", "studentId": "20230005", "className": "计科 2301", "source": "mock"},
]


def _store(db: Session) -> JsonStore:
    return JsonStore(db)


def _now_label() -> str:
    return format_chinese_datetime()


def _repo_urls(repo_name: str, owner: str = "campus") -> dict[str, str]:
    return GiteaService().repository_urls(owner=owner, repo=repo_name, branch="main")


def _refresh_repository_urls(project: dict[str, Any]) -> bool:
    repo = project.setdefault("repository", {})
    owner = str(repo.get("giteaOwner") or "campus").strip() or "campus"
    repo_name = normalize_repo_slug(str(repo.get("giteaRepo") or repo.get("repoName") or project.get("id") or "team-repository"))
    branch = str(repo.get("defaultBranch") or "main").strip() or "main"

    gitea_svc = GiteaService()
    try:
        gitea_repo = gitea_svc.get_repository(owner=owner, repo=repo_name)
        if gitea_repo and gitea_repo.get("default_branch"):
            actual_branch = str(gitea_repo["default_branch"]).strip()
            if actual_branch and actual_branch != branch:
                branch = actual_branch
                repo["defaultBranch"] = branch
                changed = True
            else:
                changed = False
        else:
            changed = False
    except Exception:
        changed = False

    urls = gitea_svc.repository_urls(owner=owner, repo=repo_name, branch=branch)
    for key in ("htmlUrl", "cloneUrl", "sshUrl", "archiveUrl"):
        if not repo.get(key) or is_stale_gitea_url(repo.get(key)):
            repo[key] = urls[key]
            changed = True
    if repo.get("giteaOwner") != owner:
        repo["giteaOwner"] = owner
        changed = True
    if repo.get("giteaRepo") != repo_name:
        repo["giteaRepo"] = repo_name
        changed = True
    if repo.get("repoName") != repo_name:
        repo["repoName"] = repo_name
        changed = True
    if repo.get("defaultBranch") != branch:
        repo["defaultBranch"] = branch
        changed = True

    home = project.get("repositoryHome")
    if isinstance(home, dict):
        for key in ("cloneUrl", "sshUrl"):
            if home.get(key) != repo.get(key):
                home[key] = repo.get(key)
                changed = True
        if home.get("repoName") != repo_name:
            home["repoName"] = repo_name
            changed = True
        if home.get("namespace") != owner:
            home["namespace"] = owner
            changed = True
        if home.get("defaultBranch") != branch:
            home["defaultBranch"] = branch
            changed = True
    return changed


def _actor_name(actor: dict[str, Any] | str | None, fallback: str = "") -> str:
    if isinstance(actor, dict):
        return str(actor.get("username") or actor.get("name") or actor.get("realName") or fallback)
    if actor:
        return str(actor)
    return fallback


def _actor_role(actor: dict[str, Any] | str | None) -> str:
    if isinstance(actor, dict):
        return str(actor.get("role") or "student")
    return "student"


def _actor_class(actor: dict[str, Any] | str | None) -> str:
    if isinstance(actor, dict):
        return str(actor.get("className") or actor.get("class_name") or "")
    return ""


def _actor_identifiers(actor: dict[str, Any] | str | None, fallback: str = "") -> set[str]:
    if isinstance(actor, dict):
        values = {
            actor.get("username"),
            actor.get("name"),
            actor.get("realName"),
            actor.get("real_name"),
            actor.get("studentId"),
            actor.get("student_id"),
            fallback,
        }
    else:
        values = {actor, fallback}
    return {str(value).replace(" (你)", "").strip() for value in values if str(value or "").strip()}


def _project_member_names(project: dict[str, Any]) -> set[str]:
    names = {str(item.get("name") or "").replace(" (你)", "").strip() for item in project.get("memberProgress") or []}
    names.update(str(item.get("id") or "").strip() for item in project.get("memberProgress") or [])
    leader = str(project.get("project", {}).get("leaderId") or "").strip()
    created_by = str(project.get("project", {}).get("createdBy") or "").strip()
    if leader:
        names.add(leader)
    if created_by:
        names.add(created_by)
    return {name for name in names if name}


def _project_visible_to_actor(project: dict[str, Any], actor: dict[str, Any] | str | None, *, fallback_viewer: str = "") -> bool:
    if not actor:
        return True
    if _actor_role(actor) == "teacher":
        actor_class = _actor_class(actor)
        project_info = project.get("project") or {}
        project_class = str(project_info.get("className") or project_info.get("class_name") or "")
        if project_class:
            return bool(actor_class) and actor_class == project_class
        return True
    return bool(_actor_identifiers(actor, fallback_viewer) & _project_member_names(project))


def _project_leader_identifiers(project: dict[str, Any]) -> set[str]:
    project_info = project.get("project") or {}
    leaders = {
        project_info.get("leaderId"),
        project_info.get("createdBy"),
    }
    for member in project.get("memberProgress") or []:
        role = str(member.get("role") or "").lower()
        if "队长" in role or "leader" in role or "captain" in role:
            leaders.update(
                {
                    member.get("id"),
                    member.get("name"),
                    member.get("username"),
                    member.get("studentId"),
                    member.get("student_id"),
                }
            )
    return {str(value).replace(" (你)", "").strip() for value in leaders if str(value or "").strip()}


def _project_can_be_deleted_by(project: dict[str, Any], actor: dict[str, Any] | str | None) -> bool:
    if _actor_role(actor) == "teacher":
        return True
    return bool(_actor_identifiers(actor) & _project_leader_identifiers(project))


def _actor_is_teacher_like(actor: dict[str, Any] | str | None) -> bool:
    if _actor_role(actor) == "teacher":
        return True
    # Tests and legacy callers often pass a plain teacher username instead of
    # the resolved actor dict. Keep that path working while endpoint callers
    # still use the explicit role from the JWT-resolved account.
    name = _actor_name(actor).strip().lower()
    return name.startswith("teacher") or name in {"admin", "campus-admin"}


def _project_can_review_pull_requests(project: dict[str, Any], actor: dict[str, Any] | str | None) -> bool:
    if _actor_is_teacher_like(actor):
        return True
    return bool(_actor_identifiers(actor) & _project_leader_identifiers(project))


def _language_stats_for_project(project: dict[str, Any]) -> list[dict[str, Any]]:
    text = f"{project.get('project', {}).get('title', '')} {project.get('project', {}).get('course', '')}"
    if "Vue" in text or "前端" in text:
        return [
            {"name": "Vue", "percent": 42, "color": "#41b883"},
            {"name": "TypeScript", "percent": 35, "color": "#3178c6"},
            {"name": "Python", "percent": 23, "color": "#3572A5"},
        ]
    return [
        {"name": "Python", "percent": 46, "color": "#3572A5"},
        {"name": "JavaScript", "percent": 28, "color": "#f1e05a"},
        {"name": "Markdown", "percent": 26, "color": "#083fa1"},
    ]


def _default_repository_files(project: dict[str, Any]) -> list[dict[str, Any]]:
    updated_at = project.get("updatedAt") or _now_label()
    return [
        {"name": "backend", "type": "dir", "lastCommit": "feat: 完成后端核心接口", "updatedAt": updated_at},
        {"name": "frontend", "type": "dir", "lastCommit": "feat: 完成仓库主页界面", "updatedAt": updated_at},
        {"name": "docs", "type": "dir", "lastCommit": "docs: 补充项目说明与类图", "updatedAt": updated_at},
        {"name": "README.md", "type": "file", "lastCommit": "docs: 初始化项目 README", "updatedAt": updated_at},
        {"name": "class-diagram.md", "type": "file", "lastCommit": "docs: 添加类图说明", "updatedAt": updated_at},
    ]


def _default_repository_home(project: dict[str, Any]) -> dict[str, Any]:
    project_info = project.get("project") or {}
    repo = project.get("repository") or {}
    repo_name = repo.get("repoName") or project.get("id") or "team-repository"
    description = project_info.get("description") or "团队尚未补充项目介绍。"
    title = project_info.get("title") or repo_name
    return {
        "namespace": repo.get("giteaOwner") or "campus",
        "repoName": repo_name,
        "visibility": "private",
        "course": project_info.get("course") or "编程团队实训",
        "about": description,
        "readme": f"# {title}\n\n{description}\n\n## 团队协作说明\n\n本仓库用于团队协作实训演示，当前 clone 地址为演示数据。",
        "classDiagram": "Controller -> Service -> Repository -> DomainRecord",
        "teacherComment": "",
        "revisionSuggestions": "",
        "teacherFeedbackUpdatedAt": "",
        "teacherFeedbackUpdatedBy": "",
        "cloneUrlMockOnly": True,
        "defaultBranch": repo.get("defaultBranch") or "main",
        "cloneUrl": repo.get("cloneUrl") or "",
        "sshUrl": repo.get("sshUrl") or "",
        "updatedAt": project.get("updatedAt") or _now_label(),
        "languageStats": _language_stats_for_project(project),
        "files": _default_repository_files(project),
    }


def _ensure_repository_home(project: dict[str, Any]) -> bool:
    changed = _refresh_repository_urls(project)
    existing = project.get("repositoryHome")
    default_home = _default_repository_home(project)
    if not isinstance(existing, dict):
        project["repositoryHome"] = default_home
        return True
    for key, value in default_home.items():
        if key not in existing:
            existing[key] = value
            changed = True
    repo = project.get("repository") or {}
    for key in ("repoName", "cloneUrl", "sshUrl", "defaultBranch"):
        source_value = repo.get(key)
        if source_value and existing.get(key) != source_value:
            existing[key] = source_value
            changed = True
    return changed


def _default_repo(repo_name: str = "huffman-coding-team", *, status: str = "collaborating") -> dict[str, Any]:
    urls = _repo_urls(repo_name)
    return {
        "repoName": repo_name,
        **urls,
        "defaultBranch": "main",
        "taskBranch": "feature/huffman-compress",
        "status": status,
        "statusLabel": _status_label(status),
        "webhookConfigured": False,
        "lastSyncedAt": _now_label(),
    }


def _workflow_steps(repo: dict[str, Any], member: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    repo_name = repo.get("repoName") or "huffman-coding-team"
    task_branch = repo.get("taskBranch") or "feature/huffman-compress"
    default_branch = repo.get("defaultBranch") or "main"
    fallback_urls = _repo_urls(repo_name, repo.get("giteaOwner") or "campus")
    clone_url = repo.get("cloneUrl") or fallback_urls["cloneUrl"]
    html_url = (repo.get("htmlUrl") or fallback_urls["htmlUrl"]).rstrip("/")
    clone_done = member and member.get("cloneStatus") == "done"
    push_done = member and member.get("pushStatus") in {"detected", "done"}
    pr_open = member and member.get("prStatus") in {"open", "merged"}
    merged = member and member.get("mergeStatus") == "merged"
    return [
        {
            "id": "clone",
            "title": "拉取代码",
            "description": "复制仓库地址，在本地终端完成项目初始化。",
            "command": f"git clone {clone_url}",
            "status": "done" if clone_done else "current",
            "statusLabel": "已拉取" if clone_done else "待确认",
            "nextHint": "拉取后点击“我已完成拉取”。",
        },
        {
            "id": "branch",
            "title": "创建功能分支",
            "description": "进入项目目录，为当前任务建立独立分支。",
            "command": f"cd {repo_name}\ngit checkout -b {task_branch}",
            "status": "done" if push_done or pr_open or merged else ("current" if clone_done else "locked"),
            "statusLabel": "已准备" if clone_done else "等待 clone",
            "nextHint": "分支创建后即可提交代码。",
        },
        {
            "id": "commit",
            "title": "提交代码",
            "description": "把本地改动提交到任务分支，commit message 要说明实现内容。",
            "command": 'git add .\ngit commit -m "feat: 完成哈夫曼压缩核心逻辑"',
            "status": "done" if push_done or pr_open or merged else ("current" if clone_done else "locked"),
            "statusLabel": "已提交" if push_done else "待提交",
            "nextHint": "提交后推送到 Gitea。",
        },
        {
            "id": "push",
            "title": "推送代码",
            "description": "推送任务分支，系统后续通过 Gitea Webhook 检测 push。",
            "command": f"git push -u origin {task_branch}",
            "status": "done" if push_done or pr_open or merged else ("current" if clone_done else "locked"),
            "statusLabel": "已检测" if push_done else "等待系统检测",
            "nextHint": "push 后刷新状态，等待系统检测。",
        },
        {
            "id": "pull_request",
            "title": "发起 Pull Request",
            "description": "进入 Gitea 原生 PR 页面，把任务分支合并到主分支。",
            "command": f"{html_url}/pulls/new?head={task_branch}&base={default_branch}",
            "status": "done" if pr_open or merged else ("current" if push_done else "locked"),
            "statusLabel": "PR 已创建" if pr_open else "PR 待创建",
            "nextHint": "创建 PR 后等待老师或队长审核。",
        },
        {
            "id": "merge",
            "title": "等待审核合并",
            "description": "老师或队长在 Gitea 审核并合并后，页面同步任务完成状态。",
            "command": f"git pull origin {default_branch}",
            "status": "done" if merged else ("current" if pr_open else "locked"),
            "statusLabel": "已合并" if merged else "等待审核",
            "nextHint": "合并后团队进度与得分会自动更新。",
        },
    ]


def _default_project(project_id: str = "huffman-coding-team") -> dict[str, Any]:
    repo = _default_repo(project_id)
    project = {
        "id": project_id,
        "project": {
            "id": project_id,
            "title": "哈夫曼压缩与解压引擎",
            "course": "数据结构与算法",
            "teamName": "极客先锋队",
            "description": "基于哈夫曼树完成文本压缩、解压、CLI 集成与测试用例集跑通。",
            "leaderId": "张华",
            "createdBy": "张华",
            "className": "",
        },
        "repository": repo,
        "memberProgress": [
            {
                "id": "liming",
                "name": "李明",
                "role": "学生",
                "task": "编写文本二进制流压缩与解压引擎",
                "branch": "feature/huffman-compress",
                "cloneStatus": "done",
                "commitCount": 3,
                "pushStatus": "detected",
                "prStatus": "needs_pr",
                "mergeStatus": "pending",
                "statusLabel": "PR 待创建",
                "lastCommitAt": "15:31",
                "score": 82,
                "contribution": 28,
                "progress": 58,
            },
            {
                "id": "zhanghua",
                "name": "张华",
                "role": "队长",
                "task": "哈夫曼树节点结构与建树算法设计",
                "branch": "feature/huffman-tree",
                "cloneStatus": "done",
                "commitCount": 5,
                "pushStatus": "detected",
                "prStatus": "open",
                "mergeStatus": "pending",
                "statusLabel": "PR 待审核",
                "lastCommitAt": "15:26",
                "score": 90,
                "contribution": 32,
                "progress": 74,
            },
            {
                "id": "wanglei",
                "name": "王磊",
                "role": "学生",
                "task": "哈夫曼二进制编码生成与字典构建",
                "branch": "feature/code-map",
                "cloneStatus": "done",
                "commitCount": 4,
                "pushStatus": "detected",
                "prStatus": "merged",
                "mergeStatus": "merged",
                "statusLabel": "已完成",
                "lastCommitAt": "15:18",
                "score": 94,
                "contribution": 35,
                "progress": 100,
            },
            {
                "id": "alina",
                "name": "Alina AI",
                "role": "AI 协作体",
                "task": "集成 CLI 命令行系统与测试用例集跑通",
                "branch": "feature/cli-tests",
                "cloneStatus": "pending",
                "commitCount": 0,
                "pushStatus": "pending",
                "prStatus": "not_created",
                "mergeStatus": "pending",
                "statusLabel": "未开始",
                "lastCommitAt": "-",
                "score": 0,
                "contribution": 5,
                "progress": 8,
            },
        ],
        "pullRequests": [
            {
                "id": "pr-2",
                "number": 2,
                "title": "feat: 完成哈夫曼树建树模块",
                "creator": "张华",
                "sourceBranch": "feature/huffman-tree",
                "targetBranch": "main",
                "status": "open",
                "statusLabel": "PR 待审核",
                "createdAt": "15:23",
                "updatedAt": "15:28",
                "url": f"{repo['htmlUrl']}/pulls/2",
            },
            {
                "id": "pr-1",
                "number": 1,
                "title": "feat: 编码字典构建逻辑",
                "creator": "王磊",
                "sourceBranch": "feature/code-map",
                "targetBranch": "main",
                "status": "merged",
                "statusLabel": "已合并",
                "createdAt": "15:04",
                "updatedAt": "15:18",
                "url": f"{repo['htmlUrl']}/pulls/1",
            },
            {
                "id": "pr-0",
                "number": 0,
                "title": "docs: 初始实验说明草稿",
                "creator": "Alina AI",
                "sourceBranch": "feature/cli-tests",
                "targetBranch": "main",
                "status": "closed",
                "statusLabel": "已关闭",
                "createdAt": "14:48",
                "updatedAt": "14:52",
                "url": f"{repo['htmlUrl']}/pulls/0",
            },
        ],
        "recentCommits": [
            {"id": "c-1", "author": "李明", "branch": "feature/huffman-compress", "message": "feat: 完成哈夫曼压缩核心逻辑", "time": "15:31"},
            {"id": "c-2", "author": "张华", "branch": "feature/huffman-tree", "message": "test: 补充建树边界用例", "time": "15:26"},
            {"id": "c-3", "author": "王磊", "branch": "feature/code-map", "message": "fix: 修复单字符编码边界", "time": "15:16"},
        ],
        "gitEvents": [
            {"id": "e-1", "type": "push", "actor": "李明", "text": "李明 推送了 feature/huffman-compress 分支", "time": "15:31"},
            {"id": "e-2", "type": "pull_request", "actor": "张华", "text": "张华 创建了 Pull Request #2", "time": "15:23"},
            {"id": "e-3", "type": "merge", "actor": "老师", "text": "老师合并了 feature/code-map -> main", "time": "15:18"},
            {"id": "e-4", "type": "commit", "actor": "系统", "text": "系统检测到 2 次新提交", "time": "15:16"},
        ],
        "chatMessages": [
            {"id": 1, "sender": "张华", "content": "我这边的建树算法逻辑已经跑通了。", "time": "15:21"},
            {"id": 2, "sender": "王磊", "content": "我的递归字典构建代码在深度比较大时报错了，可能是边界条件没写对。", "time": "15:25"},
        ],
        "updatedAt": _now_label(),
    }
    _ensure_repository_home(project)
    return project


def _status_label(status: str) -> str:
    return {
        "not_created": "未创建",
        "created": "已创建",
        "waiting_upload": "等待上传",
        "collaborating": "协作中",
        "completed": "已完成",
    }.get(status, status or "未知")


def _member_key(member: dict[str, Any]) -> str:
    return str(member.get("name") or "").replace(" (你)", "").strip()


def _member_matches(member: dict[str, Any], user_id: str) -> bool:
    key = str(user_id or "").replace(" (你)", "").strip()
    if not key:
        return False
    identifiers = {
        _member_key(member),
        str(member.get("id") or "").strip(),
        str(member.get("studentId") or "").strip(),
        str(member.get("student_id") or "").strip(),
        str(member.get("username") or "").strip(),
    }
    return key in {item for item in identifiers if item}


def _member_lookup_from_match(match: dict[str, Any], fallback: str = "") -> str:
    campus_id = str(match.get("campusUserId") or "").strip()
    if campus_id:
        return campus_id
    if match.get("matchSource") != "unmatched":
        return str(match.get("displayName") or fallback).strip()
    return str(fallback or "").strip()


def _find_member(project: dict[str, Any], user_id: str) -> dict[str, Any]:
    key = str(user_id or "").replace(" (你)", "").strip()
    for member in project.get("memberProgress") or []:
        if _member_matches(member, key):
            return member
    member = {
        "id": normalize_repo_slug(key or "member"),
        "name": key or "匿名成员",
        "role": "学生",
        "task": project.get("project", {}).get("title") or "团队协作任务",
        "branch": project.get("repository", {}).get("taskBranch") or "feature/task",
        "cloneStatus": "pending",
        "commitCount": 0,
        "pushStatus": "pending",
        "prStatus": "not_created",
        "mergeStatus": "pending",
        "statusLabel": "未开始",
        "lastCommitAt": "-",
        "score": 0,
        "contribution": 0,
        "progress": 0,
    }
    project.setdefault("memberProgress", []).append(member)
    return member


def _make_member(name: str, *, role: str = "学生", task: str = "待分配协作任务", branch: str = "") -> dict[str, Any]:
    member_name = str(name or "匿名成员").strip()
    return {
        "id": normalize_repo_slug(member_name),
        "name": member_name,
        "role": role,
        "task": task,
        "branch": branch or f"feature/{normalize_repo_slug(member_name)}",
        "cloneStatus": "pending",
        "commitCount": 0,
        "pushStatus": "pending",
        "prStatus": "not_created",
        "mergeStatus": "pending",
        "statusLabel": "未开始",
        "lastCommitAt": "-",
        "score": 0,
        "contribution": 0,
        "progress": 0,
        "reminderCount": 0,
        "lastReminderAt": "",
    }


def _append_event(project: dict[str, Any], event_type: str, actor: str, text: str) -> None:
    events = project.setdefault("gitEvents", [])
    events.insert(
        0,
        {
            "id": f"event-{len(events) + 1}-{normalize_repo_slug(actor or event_type)}",
            "type": event_type,
            "actor": actor or "系统",
            "text": text,
            "time": _now_label(),
        },
    )
    del events[20:]


def _append_unique_event(project: dict[str, Any], event_type: str, actor: str, text: str, dedupe_key: str) -> None:
    events = project.setdefault("gitEvents", [])
    if dedupe_key and any(item.get("dedupeKey") == dedupe_key for item in events):
        return
    _append_event(project, event_type, actor, text)
    if events:
        events[0]["dedupeKey"] = dedupe_key


def _sender_username(payload: dict[str, Any]) -> str:
    sender = payload.get("sender") or payload.get("pusher") or payload.get("actor") or ""
    if isinstance(sender, dict):
        return str(sender.get("username") or sender.get("login") or sender.get("name") or "")
    return str(sender or "")


def _branch_from_ref(ref: str | None) -> str:
    value = str(ref or "")
    if value.startswith("refs/heads/"):
        return value.removeprefix("refs/heads/")
    return value


def _account_display_name(account: UserAccount | None, fallback: str) -> str:
    if account:
        return account.real_name or account.username
    return fallback


def _match_student_by_username(db: Session, username: str | None, fallback: str = "") -> str:
    candidate = str(username or "").strip()
    if candidate:
        account = (
            db.query(UserAccount)
            .filter(or_(UserAccount.username == candidate, UserAccount.real_name == candidate))
            .first()
        )
        if account:
            return _account_display_name(account, candidate)
    return fallback or candidate


def _match_student_for_commit(db: Session, commit: dict[str, Any], fallback_username: str) -> str:
    author = commit.get("author") if isinstance(commit.get("author"), dict) else {}
    email = str(author.get("email") or "").strip()
    match = re.match(r"^([^@\s]+)@gezhi\.local$", email, flags=re.IGNORECASE)
    if match:
        account = db.query(UserAccount).filter(UserAccount.student_id == match.group(1)).first()
        if account:
            return _account_display_name(account, match.group(1))
    for candidate in (author.get("username"), author.get("name"), fallback_username):
        display = _match_student_by_username(db, str(candidate or ""), "")
        if display:
            return display
    fallback = str(author.get("name") or fallback_username or "unknown").strip()
    return f"{fallback} (未绑定 Gitea 用户)"


def _commit_sha(commit: dict[str, Any]) -> str:
    return str(commit.get("id") or commit.get("sha") or "").strip()


def _commit_message(commit: dict[str, Any]) -> str:
    return str(commit.get("message") or "Detected Git push").strip()


def _coach_queue_entry(commit: dict[str, Any], branch: str, author: str) -> dict[str, Any]:
    sha = _commit_sha(commit)
    return {
        "id": f"coach-{sha[:12] or normalize_repo_slug(author)}",
        "sha": sha,
        "author": author,
        "branch": branch,
        "status": "queued",
        "summary": "AI Git coach feedback queued.",
        "createdAt": _now_label(),
    }


def _upsert_coach_feedback(project: dict[str, Any], entry: dict[str, Any]) -> None:
    feedback = project.setdefault("aiGitCoachFeedback", [])
    sha = entry.get("sha")
    existing = next((item for item in feedback if sha and item.get("sha") == sha), None)
    if existing:
        existing.update(entry)
    else:
        feedback.insert(0, entry)
    del feedback[20:]


def _member_git_activity_score(member: dict[str, Any]) -> int:
    commits = int(member.get("commitCount") or 0)
    prs = int(member.get("prCount") or 0)
    merged = int(member.get("mergedPrCount") or 0)
    push_bonus = 1 if member.get("pushStatus") in {"detected", "done"} and commits == 0 else 0
    return max(0, commits + prs * 2 + merged * 3 + push_bonus)


def _apply_auto_contribution(project: dict[str, Any]) -> None:
    members = project.get("memberProgress") or []
    manual_contribution_exists = any(
        int(member.get("contribution") or 0) > 0
        and member.get("contributionSource") != "gitea_auto"
        for member in members
    )

    scored: list[tuple[int, dict[str, Any], int]] = []
    for index, member in enumerate(members):
        score = _member_git_activity_score(member)
        member["gitActivityScore"] = score
        if _is_gitea_system_login(str(member.get("name") or member.get("id") or "")):
            continue
        scored.append((index, member, score))

    total_score = sum(score for _index, _member, score in scored)
    if manual_contribution_exists or total_score <= 0:
        return

    exact = [(index, member, score, score * 100 / total_score) for index, member, score in scored]
    assigned: dict[int, int] = {
        index: int(percent)
        for index, _member, _score, percent in exact
    }
    remainder = 100 - sum(assigned.values())
    for index, _member, _score, _percent in sorted(
        exact,
        key=lambda item: (item[3] - int(item[3]), item[2], -item[0]),
        reverse=True,
    )[:remainder]:
        assigned[index] += 1

    for index, member, _score in scored:
        member["contribution"] = assigned.get(index, 0)
        member["contributionSource"] = "gitea_auto"


def _team_summary(project: dict[str, Any]) -> dict[str, Any]:
    _apply_auto_contribution(project)
    members = project.get("memberProgress") or []
    completed = [item for item in members if item.get("mergeStatus") == "merged"]
    pushed = [item for item in members if item.get("pushStatus") in {"detected", "done"}]
    open_pr = [item for item in project.get("pullRequests") or [] if item.get("status") == "open"]
    average = round(sum(int(item.get("progress") or 0) for item in members) / max(len(members), 1))
    contribution_ranking = sorted(
        [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "role": item.get("role"),
                "task": item.get("task"),
                "studentId": item.get("studentId") or item.get("student_id") or item.get("id"),
                "progress": int(item.get("progress") or 0),
                "commitCount": int(item.get("commitCount") or 0),
                "prCount": int(item.get("prCount") or 0),
                "mergedPrCount": int(item.get("mergedPrCount") or 0),
                "contribution": int(item.get("contribution") or 0),
                "contributionSource": item.get("contributionSource") or "",
                "gitActivityScore": int(item.get("gitActivityScore") or 0),
                "score": int(item.get("score") or 0),
                "source": item.get("source") or (project.get("repository") or {}).get("prSource") or "local",
            }
            for item in members
        ],
        key=lambda item: (item["contribution"], item["score"], item["commitCount"]),
        reverse=True,
    )
    return {
        "totalMembers": len(members),
        "completedMembers": len(completed),
        "pushedMembers": len(pushed),
        "openPullRequests": len(open_pr),
        "averageProgress": average,
        "pendingMembers": len([item for item in members if item.get("mergeStatus") != "merged"]),
        "unsubmittedMembers": len([item for item in members if item.get("pushStatus") not in {"detected", "done"}]),
        "reminderCount": len(project.get("reminders") or []),
        "contributionRanking": contribution_ranking,
    }


def _current_user_progress(project: dict[str, Any], viewer: str | None) -> dict[str, Any]:
    member = _find_member(project, viewer or "李明")
    if member.get("mergeStatus") == "merged":
        next_hint = "任务已完成，等待教师汇总评分。"
    elif member.get("prStatus") == "open":
        next_hint = "等待老师或队长审核 PR。"
    elif member.get("pushStatus") in {"detected", "done"}:
        next_hint = "系统已检测到 push，请前往 Gitea 创建 Pull Request。"
    elif member.get("cloneStatus") == "done":
        next_hint = "完成提交并推送后，等待系统检测 push 事件。"
    else:
        next_hint = "先复制 clone 命令并在本地拉取仓库。"
    return {
        "userId": viewer or member.get("name"),
        "member": member,
        "nextHint": next_hint,
        "score": member.get("score") or 0,
    }


def _enrich(project: dict[str, Any], viewer: str | None = None) -> dict[str, Any]:
    result = deepcopy(project)
    # 清理因 Gitea 同步而误写入的系统账号幽灵成员
    enrolled_names: set[str] = set()
    for enrolled in (result.get("project", {}).get("members") or []):
        if isinstance(enrolled, dict):
            enrolled_names.update(
                str(enrolled.get(key) or "").strip()
                for key in ("id", "memberId", "studentId", "username", "name")
                if str(enrolled.get(key) or "").strip()
            )
        else:
            value = str(enrolled or "").strip()
            if value:
                enrolled_names.add(value)
    def _is_system_phantom(m: dict[str, Any]) -> bool:
        name = str(m.get("name") or "").strip()
        member_id = str(m.get("id") or "").strip()
        return _is_gitea_system_login(name) or _is_gitea_system_login(member_id)

    def _is_phantom(m: dict[str, Any]) -> bool:
        name = str(m.get("name") or "").strip()
        if not name or name in enrolled_names:
            return False
        # 含"未绑定 Gitea 用户"标记字符串（如 "campus-admin (未绑定 Gitea 用户)"）
        if "未绑定 Gitea 用户" in name:
            return True
        name_lower = name.lower()
        # 匹配已知系统账号前缀（含变体形式）
        if _is_system_phantom(m):
            return True
        # 纯 ASCII 英文用户名（无汉字）
        return bool(re.match(r'^[A-Za-z0-9_\-]+$', name))

    if enrolled_names:
        result["memberProgress"] = [m for m in (result.get("memberProgress") or []) if not _is_phantom(m)]
    else:
        result["memberProgress"] = [m for m in (result.get("memberProgress") or []) if not _is_system_phantom(m)]
    _ensure_repository_home(result)
    if not _repository_has_live_gitea_sync(result):
        _ensure_pull_requests_from_member_progress(result)
    member = _find_member(result, viewer or "李明")
    result["repository"]["statusLabel"] = _status_label(result["repository"].get("status") or "")
    result["workflowSteps"] = _workflow_steps(result["repository"], member)
    result["currentUserProgress"] = _current_user_progress(result, viewer)
    result["teamSummary"] = _team_summary(result)
    return result


def _resolve_member_display_names(db: Session, project: dict[str, Any]) -> None:
    """将 memberProgress 中的 username/学号 替换为真实姓名，并填充 leaderName。"""
    info = project.get("project") or {}
    leader_id = str(info.get("leaderId") or "").strip()
    if leader_id:
        info["leaderName"] = _match_student_by_username(db, leader_id, leader_id)
    for member in project.get("memberProgress") or []:
        raw_name = str(member.get("name") or "").strip()
        if raw_name:
            member["name"] = _match_student_by_username(db, raw_name, raw_name)


def _load_project(db: Session, project_id: str) -> dict[str, Any]:
    store = _store(db)
    existing = store.get_payload(MODULE, PROJECT, project_id)
    if existing:
        changed = _ensure_repository_home(existing)
        if not _repository_has_live_gitea_sync(existing):
            changed = _ensure_pull_requests_from_member_progress(existing) or changed
        _resolve_member_display_names(db, existing)
        if changed:
            return store.upsert(
                MODULE,
                PROJECT,
                project_id,
                existing,
                owner_id=_project_owner_id(existing),
                status=existing.get("status") or "active",
            )
        return existing
    if project_id != "huffman-coding-team":
        raise FileNotFoundError(f"team project not found: {project_id}")
    project = _default_project(project_id)
    _ensure_repository_home(project)
    _resolve_member_display_names(db, project)
    return store.upsert(MODULE, PROJECT, project_id, project, owner_id=_project_owner_id(project), status="active")


def _save_project(db: Session, project: dict[str, Any]) -> dict[str, Any]:
    project["updatedAt"] = _now_label()
    _ensure_repository_home(project)
    if not _repository_has_live_gitea_sync(project):
        _ensure_pull_requests_from_member_progress(project)
    return _store(db).upsert(MODULE, PROJECT, project["id"], project, owner_id=_project_owner_id(project), status="active")


def _project_owner_id(project: dict[str, Any]) -> str:
    project_info = project.get("project") or {}
    return str(
        project.get("ownerId")
        or project_info.get("createdBy")
        or project_info.get("leaderId")
        or ""
    )


def _project_id_from_payload(payload: dict[str, Any]) -> str:
    explicit = payload.get("id") or payload.get("projectId") or payload.get("slug")
    if explicit:
        return normalize_repo_slug(str(explicit))
    return normalize_repo_slug(f"{payload.get('teamName') or ''}-{payload.get('title') or 'project'}")


def _default_task_for_member(tasks: list[dict[str, Any]], member_name: str, project_title: str) -> tuple[str, str]:
    for task in tasks:
        assignee = task.get("memberId") or task.get("member") or task.get("assignee") or task.get("name")
        if str(assignee or "").strip() == member_name:
            return (
                str(task.get("task") or task.get("title") or project_title or "待分配协作任务"),
                str(task.get("branch") or f"feature/{normalize_repo_slug(member_name)}"),
            )
    return project_title or "待分配协作任务", f"feature/{normalize_repo_slug(member_name)}"


def list_collaboration_projects(
    db: Session,
    *,
    viewer: str | None = None,
    actor: dict[str, Any] | str | None = None,
    scope: str = "all",
) -> list[dict[str, Any]]:
    projects = _store(db).list_payloads(MODULE, PROJECT, status="active")
    if not projects:
        projects = [_load_project(db, "huffman-coding-team")]
    visible = [project for project in projects if _project_visible_to_actor(project, actor, fallback_viewer=viewer or "")]
    return [_enrich(project, _actor_name(actor, viewer or "李明")) for project in visible]


def delete_collaboration_project(
    db: Session,
    project_id: str,
    *,
    actor: dict[str, Any] | str | None,
) -> dict[str, Any]:
    project = _store(db).get_payload(MODULE, PROJECT, project_id)
    if not project:
        raise FileNotFoundError("team collaboration project not found")
    if actor is not None and not _project_visible_to_actor(project, actor):
        raise PermissionError("project is not visible to current user")
    if not _project_can_be_deleted_by(project, actor):
        raise PermissionError("only team leaders can delete team repositories")
    deleted = _store(db).delete(MODULE, PROJECT, project_id)
    return {"id": project_id, "deleted": deleted}


def create_collaboration_project(db: Session, payload: dict[str, Any], *, actor: str | dict[str, Any]) -> dict[str, Any]:
    data = payload or {}
    actor_name = _actor_name(actor, "队长")
    project_id = _project_id_from_payload(data)
    title = str(data.get("title") or data.get("projectTitle") or project_id)
    team_name = str(data.get("teamName") or f"{actor_name or '队长'}的小组")
    leader_id = str(data.get("leaderId") or actor_name).strip()
    course = str(data.get("course") or "编程团队实训")
    description = str(data.get("description") or "队长尚未补充项目介绍。")
    class_name = str(data.get("className") or data.get("class_name") or _actor_class(actor))
    raw_members = data.get("members") or []
    if isinstance(raw_members, str):
        raw_members = [item.strip() for item in raw_members.replace("，", ",").split(",") if item.strip()]
    member_names = []
    for item in raw_members:
        if isinstance(item, dict):
            member_names.append(str(item.get("memberId") or item.get("name") or "").strip())
        else:
            member_names.append(str(item).strip())
    member_names = [name for name in member_names if name]
    if leader_id and leader_id not in member_names:
        member_names.insert(0, leader_id)
    if not member_names:
        member_names = [actor_name or "队长"]

    tasks = [task for task in (data.get("tasks") or []) if isinstance(task, dict)]
    members = []
    for name in member_names:
        task, branch = _default_task_for_member(tasks, name, title)
        members.append(_make_member(name, role="队长" if name == leader_id else "学生", task=task, branch=branch))

    repo_name = normalize_repo_slug(data.get("repoName") or project_id)
    project = {
        "id": project_id,
        "project": {
            "id": project_id,
            "title": title,
            "course": course,
            "teamName": team_name,
            "description": description,
            "leaderId": leader_id,
            "teacherId": data.get("teacherId") or "",
            "className": class_name,
            "status": "active",
            "createdBy": actor_name,
            "createdAt": _now_label(),
        },
        "repository": {
            **_default_repo(repo_name, status="not_created"),
            "taskBranch": members[0].get("branch") or "feature/task",
        },
        "memberProgress": members,
        "pullRequests": [],
        "recentCommits": [],
        "gitEvents": [],
        "chatMessages": [
            {
                "id": 1,
                "sender": actor or "队长",
                "content": f"团队项目「{title}」已创建，请各成员按照任务分支推进。",
                "time": _now_label(),
            }
        ],
        "reminders": [],
        "teacherEvaluation": {"summary": "", "auditor": "", "updatedAt": ""},
        "updatedAt": _now_label(),
    }
    _ensure_repository_home(project)
    _append_event(project, "project_created", actor_name, f"{actor_name or '队长'} 创建了团队协作项目 {title}")
    saved = _save_project(db, project)
    return _enrich(saved, actor_name)


def update_collaboration_project(db: Session, project_id: str, payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    project = _load_project(db, project_id)
    project_info = project.setdefault("project", {})
    for field in ("title", "course", "teamName", "description", "teacherId"):
        if field in (payload or {}):
            project_info[field] = payload[field]
    _append_event(project, "project_updated", actor, f"{actor or '队长'} 更新了项目资料")
    saved = _save_project(db, project)
    return _enrich(saved, actor)


def _sync_lock_for(project_id: str) -> threading.Lock:
    with _SYNC_LOCKS_GUARD:
        lock = _SYNC_LOCKS.get(project_id)
        if lock is None:
            lock = threading.Lock()
            _SYNC_LOCKS[project_id] = lock
        return lock


def _resolve_member_gitea_username(db: Session, member: dict[str, Any]) -> str:
    candidates = [
        str(member.get("username") or "").strip(),
        str(member.get("id") or "").strip(),
        str(member.get("name") or "").strip(),
        str(member.get("studentId") or member.get("student_id") or "").strip(),
    ]
    candidates = [item for item in candidates if item]
    if not candidates:
        return ""
    account = (
        db.query(UserAccount)
        .filter(
            or_(
                UserAccount.username.in_(candidates),
                UserAccount.real_name.in_(candidates),
                UserAccount.student_id.in_(candidates),
            )
        )
        .first()
    )
    if not account:
        return ""
    binding = db.query(GiteaAccountBinding).filter(GiteaAccountBinding.campus_user_id == account.username).first()
    if binding and binding.gitea_username:
        return str(binding.gitea_username)
    return str(account.username or "")


def _find_member_for_gitea_match(project: dict[str, Any], match: dict[str, Any], fallback: str = "") -> dict[str, Any]:
    existing = _find_existing_member_for_gitea_match(project, match, fallback)
    if existing is not None:
        return existing
    display = str(match.get("displayName") or "").strip()
    campus = str(match.get("campusUserId") or "").strip()
    student_id = str(match.get("studentId") or "").strip()
    gitea_username = str(match.get("giteaUsername") or "").strip()
    return _find_member(project, campus or student_id or display or gitea_username or fallback)


def _find_existing_member_for_gitea_match(project: dict[str, Any], match: dict[str, Any], fallback: str = "") -> dict[str, Any] | None:
    display = str(match.get("displayName") or "").strip()
    campus = str(match.get("campusUserId") or "").strip()
    student_id = str(match.get("studentId") or "").strip()
    gitea_username = str(match.get("giteaUsername") or "").strip()
    for key in (campus, student_id, display, gitea_username, str(fallback or "").strip()):
        if not key:
            continue
        for member in project.get("memberProgress") or []:
            if _member_matches(member, key):
                return member
    return None


def _pr_status_label(status: str) -> str:
    mapping = {
        "open": "待审核",
        "merged": "已合并",
        "closed": "已关闭",
    }
    return mapping.get(status, status or "未知")


def _member_pull_request_status(member: dict[str, Any]) -> str:
    pr_status = str(member.get("prStatus") or "").strip()
    if pr_status == "merged" or member.get("mergeStatus") == "merged":
        return "merged"
    if pr_status == "open":
        return "open"
    return ""


def _student_pr_title(member: dict[str, Any], status: str) -> str:
    task = str(member.get("task") or "").strip()
    if len(task) > 24:
        task = f"{task[:24]}..."
    if status == "merged":
        return f"feat: 完成{task or '任务分支'}并通过集成"
    return f"feat: 提交{task or '任务分支'}实现"


def _mark_gitea_sync_state(
    project: dict[str, Any],
    *,
    status: str,
    pr_source: str | None = None,
    webhook_status: str | None = None,
    fallback_reason: str = "",
    error: str = "",
) -> None:
    repo = project.setdefault("repository", {})
    repo["giteaSyncStatus"] = status
    if pr_source:
        repo["prSource"] = pr_source
    if webhook_status:
        repo["webhookStatus"] = webhook_status
    repo["demoFallbackReason"] = fallback_reason
    repo["lastSyncError"] = error
    repo["syncError"] = error


def _repository_has_live_gitea_sync(project: dict[str, Any]) -> bool:
    repo = project.get("repository") or {}
    return (
        str(repo.get("giteaSyncStatus") or "") == "synced"
        and str(repo.get("prSource") or "") in {"gitea", "gitea_empty"}
    )


def _ensure_pull_requests_from_member_progress(project: dict[str, Any]) -> bool:
    """Backfill PR rows when member progress already shows PR states.

    Some demo/training datasets only have member-level Git progress. The teacher
    audit panel and team cards read pullRequests, so keep that collection
    consistent with memberProgress instead of showing an empty PR state.
    """
    if _repository_has_live_gitea_sync(project):
        return False

    if any(_is_real_gitea_row(item) for item in (project.get("pullRequests") or [])):
        return False

    repo = project.get("repository") or {}
    html_url = str(repo.get("htmlUrl") or "").rstrip("/")
    prs = project.setdefault("pullRequests", [])
    changed = False
    max_number = max([int(item.get("number") or 0) for item in prs] or [0])

    def _same_member_pr(pr: dict[str, Any], member: dict[str, Any]) -> bool:
        creator = str(pr.get("creator") or "").strip()
        return bool(creator and creator == str(member.get("name") or "").strip())

    for member in project.get("memberProgress") or []:
        status = _member_pull_request_status(member)
        if not status:
            continue
        existing = next((item for item in prs if _same_member_pr(item, member)), None)
        if existing:
            # Existing PR rows are the source of truth for review/merge state.
            # Member progress is only used to create missing rows.
            continue

        max_number += 1
        created_at = member.get("lastCommitAt")
        if not created_at or str(created_at) == "-":
            created_at = project.get("updatedAt") or _now_label()
        pr = {
            "id": f"pr-{max_number}",
            "number": max_number,
            "title": _student_pr_title(member, status),
            "creator": member.get("name") or member.get("id") or "学生成员",
            "sourceBranch": member.get("branch") or repo.get("taskBranch") or "feature/task",
            "targetBranch": repo.get("defaultBranch") or "main",
            "status": status,
            "statusLabel": "已合并" if status == "merged" else "PR 待审核",
            "leaderReviewStatus": "recommended",
            "leaderReviewer": project.get("project", {}).get("leaderId") or "",
            "teacherReviewStatus": "approved" if status == "merged" else "pending",
            "teacherReviewer": "teacher_chen" if status == "merged" else "",
            "reviewComment": (
                "教师已确认合并，功能演示和测试记录基本完整。"
                if status == "merged"
                else "队长已完成初审，建议教师重点查看异常路径测试和 README 运行说明。"
            ),
            "createdAt": created_at,
            "updatedAt": project.get("updatedAt") or _now_label(),
            "url": f"{html_url}/pulls/{max_number}" if html_url else "",
            "source": "member_progress_backfill",
        }
        prs.append(pr)
        changed = True

    if changed:
        prs.sort(key=lambda item: int(item.get("number") or 0), reverse=True)
    return changed


def _apply_gitea_prs_to_project(db: Session, project: dict[str, Any], prs: list[dict[str, Any]]) -> None:
    if not prs:
        project["pullRequests"] = []
        _mark_gitea_sync_state(project, status="synced", pr_source="gitea_empty")
        return

    member_refs: dict[str, dict[str, Any]] = {}
    pr_counts: dict[str, int] = {}
    merged_counts: dict[str, int] = {}
    existing = {
        int(item.get("number") or 0): item
        for item in (project.get("pullRequests") or [])
        if int(item.get("number") or 0) and _is_real_gitea_row(item)
    }
    merged_list: list[dict[str, Any]] = []
    for pr in prs:
        number = int(pr.get("number") or 0)
        if not number:
            continue
        creator_login = str(pr.get("creator") or "")
        # 跳过系统账号创建的 PR
        if _is_gitea_system_login(creator_login):
            continue
        match = match_campus_user_from_gitea_event(db, sender_username=creator_login, commit_author={})
        creator = match.get("displayName") or creator_login
        status = str(pr.get("status") or "open")
        prev = existing.get(number) or {}
        row = {
            **prev,
            "id": prev.get("id") or f"pr-{number}",
            "number": number,
            "title": pr.get("title") or prev.get("title") or f"Pull Request #{number}",
            "status": status,
            "statusLabel": prev.get("statusLabel") if status == prev.get("status") else _pr_status_label(status),
            "creator": creator,
            "sourceBranch": pr.get("sourceBranch") or prev.get("sourceBranch") or "",
            "targetBranch": pr.get("targetBranch") or prev.get("targetBranch") or "main",
            "url": pr.get("url") or prev.get("url") or "",
            "updatedAt": pr.get("updatedAt") or prev.get("updatedAt") or _now_label(),
            "createdAt": pr.get("createdAt") or prev.get("createdAt") or _now_label(),
            "source": "gitea",
        }
        member = _find_existing_member_for_gitea_match(project, match, creator_login)
        if member:
            member_key = str(member.get("id") or member.get("studentId") or member.get("name") or creator_login)
            member_refs[member_key] = member
            pr_counts[member_key] = pr_counts.get(member_key, 0) + 1
            if status == "merged":
                merged_counts[member_key] = merged_counts.get(member_key, 0) + 1
        if status == "merged":
            row["statusLabel"] = prev.get("statusLabel") if prev.get("status") == "merged" else "已合并"
            row["teacherReviewStatus"] = prev.get("teacherReviewStatus") or "approved"
        elif status == "open":
            row["statusLabel"] = prev.get("statusLabel") or "待审核"
            if member:
                member["prStatus"] = "open"
                member["pushStatus"] = "detected"
                member["statusLabel"] = "PR 待审核"
                member["progress"] = max(int(member.get("progress") or 0), 74)
        merged_list.append(row)
    merged_list.sort(key=lambda item: int(item.get("number") or 0), reverse=True)
    project["pullRequests"] = merged_list
    _mark_gitea_sync_state(project, status="synced", pr_source="gitea" if merged_list else "gitea_empty")

    for pr in merged_list:
        if pr.get("status") != "merged":
            continue
        member = _find_existing_member_for_gitea_match(
            project,
            {"displayName": pr.get("creator"), "campusUserId": ""},
            str(pr.get("creator") or ""),
        )
        if not member:
            continue
        member["prStatus"] = "merged"
        member["mergeStatus"] = "merged"
        member["statusLabel"] = "已完成"
        member["progress"] = 100
    for member_key, member in member_refs.items():
        member["prCount"] = pr_counts.get(member_key, 0)
        member["mergedPrCount"] = merged_counts.get(member_key, 0)
        member["source"] = "gitea"

def _apply_gitea_commits_to_project(
    db: Session,
    project: dict[str, Any],
    commits: list[dict[str, Any]],
    *,
    branch: str | None = None,
) -> None:
    recent = project.setdefault("recentCommits", [])
    if commits:
        recent[:] = [item for item in recent if str(item.get("sha") or "").strip()]
    existing_shas = {str(item.get("sha") or item.get("id") or "") for item in recent}
    repo = project.get("repository") or {}
    branch_name = str(branch or repo.get("defaultBranch") or "main")
    for commit in commits:
        sha = str(commit.get("sha") or "")
        if not sha or sha in existing_shas:
            continue
        author_login = str(commit.get("authorLogin") or "")
        # 跳过 Gitea 系统账号的提交，不将其写入成员进度
        if _is_gitea_system_login(author_login) or _is_gitea_system_commit(commit):
            continue
        match = match_campus_user_from_gitea_event(
            db,
            sender_username=author_login,
            commit_author={"name": commit.get("authorName"), "email": commit.get("authorEmail")},
        )
        if _is_gitea_system_login(str(match.get("displayName") or "")):
            continue
        author = match.get("displayName") or commit.get("authorName") or commit.get("authorLogin") or "未知"
        recent.insert(
            0,
            {
                "id": f"commit-{sha[:8]}",
                "sha": sha,
                "author": author,
                "branch": branch_name,
                "message": commit.get("message") or "commit",
                "time": commit.get("time") or _now_label(),
                "url": commit.get("url") or "",
                "source": "gitea",
            },
        )
        existing_shas.add(sha)
        member = _find_existing_member_for_gitea_match(project, match, str(author))
        if not member:
            continue
        member["source"] = "gitea"
        member["pushStatus"] = "detected"
        member["cloneStatus"] = "done"
        if member.get("prStatus") in {None, "", "not_created", "needs_pr"}:
            member["prStatus"] = "needs_pr"
            member["statusLabel"] = "PR 待创建"
        member["commitCount"] = int(member.get("commitCount") or 0) + 1
        member["lastCommitAt"] = commit.get("time") or _now_label()
        member["progress"] = max(int(member.get("progress") or 0), 58)
    del recent[30:]


def _apply_gitea_issues_to_project(db: Session, project: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    by_number = {int(item.get("number") or 0): item for item in issues if int(item.get("number") or 0)}
    for member in project.get("memberProgress") or []:
        issue_no = int(member.get("giteaIssueNumber") or 0)
        if issue_no and issue_no in by_number:
            issue = by_number[issue_no]
            title = str(issue.get("title") or "").strip()
            if title:
                member["task"] = title
            body = str(issue.get("body") or "")
            branch_match = re.search(r"分支[：:]\s*(\S+)", body)
            if branch_match:
                member["branch"] = branch_match.group(1)
            continue
        gitea_user = _resolve_member_gitea_username(db, member)
        if not gitea_user:
            continue
        for issue in issues:
            assignees = [str(a).lower() for a in (issue.get("assignees") or [])]
            if gitea_user.lower() not in assignees:
                continue
            member["giteaIssueNumber"] = int(issue.get("number") or 0)
            if issue.get("title"):
                member["task"] = str(issue.get("title"))
            break


def _candidate_gitea_sync_branches(project: dict[str, Any], prs: list[dict[str, Any]], default_branch: str) -> list[str]:
    repo = project.get("repository") or {}
    branches: list[str] = []

    def add(value: Any) -> None:
        branch = str(value or "").strip()
        if branch and branch not in branches:
            branches.append(branch)

    add(default_branch or repo.get("defaultBranch") or "main")
    add(repo.get("taskBranch"))
    for member in project.get("memberProgress") or []:
        add(member.get("branch"))
    for pr in prs:
        add(pr.get("sourceBranch"))
        add(pr.get("targetBranch"))
    for pr in project.get("pullRequests") or []:
        add(pr.get("sourceBranch"))
        add(pr.get("targetBranch"))

    max_branches = max(1, int(getattr(settings, "GITEA_SYNC_MAX_BRANCHES", 20) or 20))
    return branches[:max_branches]


def sync_project_from_gitea(
    db: Session,
    project_id: str,
    *,
    actor: dict[str, Any] | str | None = None,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    lock = _sync_lock_for(project_id)
    if not lock.acquire(blocking=False):
        project = _load_project(db, project_id)
        if actor is not None and not _project_visible_to_actor(project, actor):
            raise PermissionError("project is not visible to current user")
        return _enrich(project, _actor_name(actor, "系统"))

    try:
        project = _load_project(db, project_id)
        if actor is not None and not _project_visible_to_actor(project, actor):
            raise PermissionError("project is not visible to current user")

        gitea_svc = gitea or GiteaService()
        owner, repo, branch = _gitea_repo_target(project)
        repo_meta = project.setdefault("repository", {})

        if not gitea_svc.enabled or not gitea_svc.token:
            _mark_gitea_sync_state(
                project,
                status="disabled",
                pr_source="demo_fallback",
                fallback_reason="Gitea 未启用或缺少 API Token，已显示演示数据",
                error="Gitea 未启用或缺少 API Token",
            )
            repo_meta["lastSyncedAt"] = _now_label()
            _save_project(db, project)
            raise RuntimeError(repo_meta["syncError"])

        if not owner or not repo:
            _mark_gitea_sync_state(
                project,
                status="unbound",
                pr_source="demo_fallback",
                fallback_reason="项目尚未绑定 Gitea 仓库，已显示演示数据",
                error="项目尚未绑定 Gitea 仓库",
            )
            repo_meta["lastSyncedAt"] = _now_label()
            _save_project(db, project)
            raise RuntimeError(repo_meta["syncError"])

        try:
            prs = gitea_svc.list_pull_requests(owner=owner, repo=repo, state="all")
            issues = gitea_svc.list_issues(owner=owner, repo=repo, state="open")
            _apply_gitea_prs_to_project(db, project, prs)
            for branch_name in _candidate_gitea_sync_branches(project, prs, branch or repo_meta.get("defaultBranch") or "main"):
                commits = gitea_svc.list_commits(owner=owner, repo=repo, sha=branch_name, limit=30)
                _apply_gitea_commits_to_project(db, project, commits, branch=branch_name)
            _apply_gitea_issues_to_project(db, project, issues)
            _mark_gitea_sync_state(
                project,
                status="synced",
                pr_source=repo_meta.get("prSource") or ("gitea" if project.get("pullRequests") else "gitea_empty"),
                webhook_status="configured" if repo_meta.get("webhookConfigured") else repo_meta.get("webhookStatus") or "",
            )
            repo_meta["lastSyncedAt"] = _now_label()
            repo_meta["syncError"] = ""
            _append_event(project, "gitea_synced", _actor_name(actor, "系统"), f"{_actor_name(actor, '系统')} 从 Gitea 同步了 PR/提交/任务")
            saved = _save_project(db, project)
            return _enrich(saved, _actor_name(actor, "系统"))
        except Exception as exc:
            _mark_gitea_sync_state(
                project,
                status="error",
                pr_source="demo_fallback",
                fallback_reason="Gitea 同步异常，已显示演示数据",
                error=str(exc),
            )
            repo_meta["lastSyncedAt"] = _now_label()
            _save_project(db, project)
            raise RuntimeError(f"Gitea 同步失败：{exc}") from exc
    finally:
        lock.release()


def check_gitea_health(*, gitea: GiteaService | None = None) -> dict[str, Any]:
    return (gitea or GiteaService()).ping()


def assign_member_task(
    db: Session,
    project_id: str,
    member_id: str,
    payload: dict[str, Any],
    *,
    actor: str,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    project = _load_project(db, project_id)
    member = _find_member(project, member_id)
    task = str((payload or {}).get("task") or (payload or {}).get("title") or member.get("task") or "")
    branch = str((payload or {}).get("branch") or member.get("branch") or f"feature/{normalize_repo_slug(member.get('name') or member_id)}")
    owner, repo, _default_branch = _gitea_repo_target(project)
    gitea_svc = gitea or GiteaService()

    issue_number = int(member.get("giteaIssueNumber") or 0)
    issue_body = f"负责人：{member.get('name') or member_id}\n分支：{branch}\n分配人：{actor or '系统'}"
    repo_status = str((project.get("repository") or {}).get("status") or "")
    repo_ready = bool(owner and repo and repo_status not in {"", "not_created"})

    if gitea_svc.enabled and gitea_svc.token and repo_ready:
        assignees: list[str] = []
        gitea_user = _resolve_member_gitea_username(db, member)
        if gitea_user:
            assignees.append(gitea_user)
        try:
            if issue_number:
                gitea_svc.edit_issue(
                    owner=owner,
                    repo=repo,
                    index=issue_number,
                    title=task or f"{member.get('name')} 的协作任务",
                    body=issue_body,
                    assignees=assignees or None,
                )
            else:
                created = gitea_svc.create_issue(
                    owner=owner,
                    repo=repo,
                    title=task or f"{member.get('name')} 的协作任务",
                    body=issue_body,
                    assignees=assignees or None,
                )
                issue_number = int(created.get("number") or 0)
        except Exception as exc:
            raise RuntimeError(f"同步 Gitea Issue 失败：{exc}") from exc
    elif gitea_svc.enabled and not gitea_svc.token:
        raise RuntimeError("无法同步任务到 Gitea：缺少 API Token")
    # 仓库尚未创建时允许先落本地任务，创建仓库后再次分配会补建 Issue

    member.update(
        {
            "task": task,
            "branch": branch,
            "statusLabel": "已分配",
            "progress": max(int(member.get("progress") or 0), 10),
            "giteaIssueNumber": issue_number or member.get("giteaIssueNumber") or 0,
        }
    )
    if project.get("repository") and _member_matches(member, project.get("project", {}).get("leaderId") or ""):
        project["repository"]["taskBranch"] = branch
    _append_event(project, "task_assigned", actor, f"{actor or '队长'} 将「{task}」分配给 {member.get('name')}")
    saved = _save_project(db, project)
    return _enrich(saved, actor)


def remind_unsubmitted_members(db: Session, project_id: str, payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    project = _load_project(db, project_id)
    data = payload or {}
    target_ids = data.get("memberIds") or data.get("members") or []
    if isinstance(target_ids, str):
        target_ids = [item.strip() for item in target_ids.replace("，", ",").split(",") if item.strip()]
    message = str(data.get("message") or "请尽快完成本地提交、push 并创建 Pull Request。")
    if target_ids:
        targets = [_find_member(project, str(member_id)) for member_id in target_ids]
    else:
        targets = [
            member
            for member in project.get("memberProgress") or []
            if member.get("pushStatus") not in {"detected", "done"} or member.get("prStatus") in {"not_created", "needs_pr"}
        ]

    reminders = project.setdefault("reminders", [])
    for member in targets:
        member["reminderCount"] = int(member.get("reminderCount") or 0) + 1
        member["lastReminderAt"] = _now_label()
        reminders.insert(
            0,
            {
                "id": f"reminder-{len(reminders) + 1}",
                "memberId": member.get("id"),
                "memberName": member.get("name"),
                "message": message,
                "actor": actor,
                "createdAt": _now_label(),
                "status": "sent",
            },
        )
        project.setdefault("chatMessages", []).append(
            {
                "id": len(project.get("chatMessages") or []) + 1,
                "sender": actor or "队长",
                "content": f"@{member.get('name')} {message}",
                "time": _now_label(),
            }
        )
    _append_event(project, "member_reminded", actor, f"{actor or '队长'} 提醒了 {len(targets)} 位未提交成员")
    saved = _save_project(db, project)
    return _enrich(saved, actor)


def get_collaboration_project(
    db: Session,
    project_id: str,
    *,
    viewer: str | None = None,
    actor: dict[str, Any] | str | None = None,
    sync: bool = False,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    if sync:
        return sync_project_from_gitea(db, project_id, actor=actor, gitea=gitea)
    project = _load_project(db, project_id)
    if actor is not None and not _project_visible_to_actor(project, actor, fallback_viewer=viewer or ""):
        raise PermissionError("project is not visible to current user")
    return _enrich(project, _actor_name(actor, viewer or "李明"))


def get_repository_home(
    db: Session,
    project_id: str,
    *,
    actor: dict[str, Any] | str | None = None,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    project = _load_project(db, project_id)
    if actor is not None and not _project_visible_to_actor(project, actor):
        raise PermissionError("repository home is not visible to current user")
    _ensure_repository_home(project)
    saved = _save_project(db, project)
    home = deepcopy(saved.get("repositoryHome") or {})

    # 实时从 Gitea 拉取 README 和类图，覆盖 mock 默认值
    gitea_svc = gitea or GiteaService()
    owner, repo, branch = _gitea_repo_target(saved)
    if gitea_svc.enabled:
        real_readme = gitea_svc.get_readme(owner=owner, repo=repo, branch=branch)
        if real_readme:
            home["readme"] = real_readme

        # 尝试读取约定类图文件，找不到回退存储值
        for diagram_path in ("class-diagram.md", "docs/class-diagram.md", "class-diagram.txt"):
            try:
                blob = gitea_svc.get_file_content(
                    owner=owner, repo=repo, path=diagram_path, branch=branch
                )
                if blob.get("content"):
                    home["classDiagram"] = blob["content"]
                    break
            except (FileNotFoundError, ValueError):
                continue

    home["project"] = saved.get("project") or {}
    home["repository"] = saved.get("repository") or {}
    home["memberProgress"] = saved.get("memberProgress") or []
    home["pullRequests"] = saved.get("pullRequests") or []
    home["teamSummary"] = _team_summary(saved)
    return home


def _require_visible_project(db: Session, project_id: str, *, actor: dict[str, Any] | str | None = None) -> dict[str, Any]:
    project = _load_project(db, project_id)
    if actor is not None and not _project_visible_to_actor(project, actor):
        raise PermissionError("repository is not visible to current user")
    return project


def _gitea_repo_target(project: dict[str, Any]) -> tuple[str, str, str]:
    repo = project.get("repository") or {}
    return (
        str(repo.get("giteaOwner") or "campus"),
        str(repo.get("giteaRepo") or repo.get("repoName") or project.get("id") or ""),
        str(repo.get("defaultBranch") or "main"),
    )


def get_team_repository_tree(
    db: Session,
    project_id: str,
    *,
    path: str = "",
    ref: str | None = None,
    actor: dict[str, Any] | str | None = None,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    project = _require_visible_project(db, project_id, actor=actor)
    owner, repo, branch = _gitea_repo_target(project)
    branch = ref or branch
    entries = (gitea or GiteaService()).list_contents(owner=owner, repo=repo, path=path, branch=branch)
    normalized_path = str(path or "").strip().strip("/")
    return {
        "projectId": project_id,
        "path": normalized_path,
        "ref": branch,
        "entries": entries,
    }


def list_team_branches(
    db: Session,
    project_id: str,
    *,
    actor: dict[str, Any] | str | None = None,
    gitea: GiteaService | None = None,
) -> list[dict[str, Any]]:
    project = _require_visible_project(db, project_id, actor=actor)
    owner, repo, default_branch = _gitea_repo_target(project)
    branches = (gitea or GiteaService()).list_branches(owner=owner, repo=repo)
    for b in branches:
        b["default"] = b.get("name") == default_branch
    return branches


def get_team_repository_blob(
    db: Session,
    project_id: str,
    *,
    path: str,
    ref: str | None = None,
    actor: dict[str, Any] | str | None = None,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    project = _require_visible_project(db, project_id, actor=actor)
    owner, repo, branch = _gitea_repo_target(project)
    branch = ref or branch
    blob = (gitea or GiteaService()).get_file_content(owner=owner, repo=repo, path=path, branch=branch)
    return {
        "projectId": project_id,
        "ref": branch,
        **blob,
    }


def get_team_repository_languages(
    db: Session,
    project_id: str,
    *,
    actor: dict[str, Any] | str | None = None,
    gitea: GiteaService | None = None,
) -> list[dict[str, Any]]:
    project = _require_visible_project(db, project_id, actor=actor)
    owner, repo, _branch = _gitea_repo_target(project)
    stats = (gitea or GiteaService()).get_languages(owner=owner, repo=repo)
    total = sum(stats.values()) or 1.0
    return [
        {
            "name": name,
            "bytes": value,
            "percent": round(value / total * 100, 1),
        }
        for name, value in sorted(stats.items(), key=lambda item: item[1], reverse=True)
    ]


def update_repository_feedback(
    db: Session,
    project_id: str,
    payload: dict[str, Any],
    *,
    actor: dict[str, Any] | str | None,
) -> dict[str, Any]:
    if _actor_role(actor) != "teacher":
        raise PermissionError("only teachers can update repository feedback")
    project = _load_project(db, project_id)
    if not _project_visible_to_actor(project, actor):
        raise PermissionError("repository home is not visible to current teacher")
    _ensure_repository_home(project)
    home = project["repositoryHome"]
    home["teacherComment"] = str((payload or {}).get("teacherComment") or "")
    home["revisionSuggestions"] = str((payload or {}).get("revisionSuggestions") or "")
    home["teacherFeedbackUpdatedAt"] = _now_label()
    home["teacherFeedbackUpdatedBy"] = _actor_name(actor, "teacher")
    _append_event(project, "repository_feedback_updated", _actor_name(actor, "teacher"), "教师更新了仓库主页评语与修改建议")
    saved = _save_project(db, project)
    return saved["repositoryHome"]


def search_team_members(
    db: Session,
    keyword: str,
    *,
    actor: dict[str, Any] | str | None = None,
    course: str = "",
    class_name: str = "",
) -> list[dict[str, Any]]:
    query_text = str(keyword or "").strip()
    if not query_text:
        return []

    like_text = f"%{query_text}%"
    query = db.query(UserAccount).filter(UserAccount.role == "student")
    accounts = (
        query.filter(
            or_(
                UserAccount.student_id.like(like_text),
                UserAccount.username.like(like_text),
                UserAccount.real_name.like(like_text),
            )
        )
        .limit(8)
        .all()
    )
    if accounts:
        return [
            {
                "username": item.username,
                "name": item.real_name or item.username,
                "studentId": item.student_id or "",
                "className": item.class_name or "",
                "source": "user",
            }
            for item in accounts
        ]

    lowered = query_text.lower()
    return [
        item
        for item in MOCK_CLASS_STUDENTS
        if (not target_class or item["className"] == target_class)
        and (query_text in item["studentId"] or query_text in item["name"] or lowered in item["username"])
    ][:8]


def backfill_repository_home_records(db: Session) -> int:
    store = _store(db)
    changed_count = 0
    for project in store.list_payloads(MODULE, PROJECT):
        if _ensure_repository_home(project):
            store.upsert(
                MODULE,
                PROJECT,
                project["id"],
                project,
                owner_id=project.get("project", {}).get("createdBy") or "",
                status=project.get("project", {}).get("status") or "active",
            )
            changed_count += 1
    return changed_count


def backfill_training_pull_request_records(db: Session) -> int:
    store = _store(db)
    changed_count = 0
    for project in store.list_payloads(MODULE, PROJECT, status="active"):
        if _ensure_pull_requests_from_member_progress(project):
            _save_project(db, project)
            changed_count += 1
    return changed_count


def _team_repo_permissions(project: dict[str, Any]) -> list[RepoPermission]:
    project_info = project.get("project") or {}
    permissions: list[RepoPermission] = []
    leader_id = str(project_info.get("leaderId") or project_info.get("createdBy") or "").strip()
    if leader_id:
        permissions.append(RepoPermission(leader_id, "admin", "leader"))
    teacher_id = str(project_info.get("teacherId") or project_info.get("teacher") or "").strip()
    if teacher_id:
        permissions.append(RepoPermission(teacher_id, "admin", "teacher"))
    for member in project.get("memberProgress") or []:
        member_id = str(member.get("id") or member.get("memberId") or member.get("studentId") or member.get("username") or member.get("name") or "").strip()
        if not member_id or member_id == leader_id:
            continue
        role = str(member.get("role") or "").lower()
        permission = "admin" if "队长" in role or "leader" in role or "captain" in role else "write"
        permissions.append(RepoPermission(member_id, permission, "team_member"))
    deduped: dict[str, RepoPermission] = {}
    rank = {"read": 1, "write": 2, "admin": 3}
    for item in permissions:
        existing = deduped.get(item.campus_user_id)
        if not existing or rank[item.permission] > rank[existing.permission]:
            deduped[item.campus_user_id] = item
    return list(deduped.values())


def create_project_repository(
    db: Session,
    project_id: str,
    *,
    actor: str,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    project = _load_project(db, project_id)
    project_title = project.get("project", {}).get("title") or project_id
    repo_name = project.get("repository", {}).get("repoName") or normalize_repo_slug(project_title)
    gitea_client = gitea or GiteaService()
    repo = gitea_client.create_repository(
        name=repo_name,
        description=f"{project_title} - 团队协作实训仓库",
        private=True,
        auto_init=True,
    )
    webhook_result: dict[str, Any] = {"configured": True}
    ensure_webhook = getattr(gitea_client, "ensure_webhook", None)
    if callable(ensure_webhook):
        raw_webhook = ensure_webhook(
            owner=repo.get("giteaOwner") or "campus",
            repo=repo.get("giteaRepo") or repo_name,
            project_id=project_id,
        )
        webhook_result = raw_webhook if isinstance(raw_webhook, dict) else {"configured": bool(raw_webhook)}
    else:
        create_webhook = getattr(gitea_client, "create_webhook", None)
        if callable(create_webhook):
            webhook_result = {
                "configured": bool(
                    create_webhook(
                        owner=repo.get("giteaOwner") or "campus",
                        repo=repo.get("giteaRepo") or repo_name,
                        project_id=project_id,
                    )
                )
            }
    webhook_configured = bool(webhook_result.get("configured"))
    project["repository"].update(
        {
            "repoName": repo.get("giteaRepo") or repo_name,
            "giteaOwner": repo.get("giteaOwner") or "campus",
            "htmlUrl": repo.get("htmlUrl") or project["repository"].get("htmlUrl"),
            "cloneUrl": repo.get("cloneUrl") or project["repository"].get("cloneUrl"),
            "sshUrl": repo.get("sshUrl") or project["repository"].get("sshUrl"),
            "defaultBranch": repo.get("defaultBranch") or "main",
            "status": "created",
            "webhookConfigured": webhook_configured,
            "webhookUrl": webhook_result.get("url") or "",
            "webhookEvents": webhook_result.get("events") or ["push", "pull_request"],
            "webhookError": webhook_result.get("error") or "",
            "lastSyncedAt": _now_label(),
        }
    )
    permission_sync = ensure_repository_collaborators(
        db,
        project["repository"].get("giteaOwner") or "campus",
        project["repository"].get("repoName") or project_id,
        _team_repo_permissions(project),
        gitea=gitea_client,
    )
    project["repository"]["giteaCollaborators"] = permission_sync
    _ensure_repository_home(project)
    project["repositoryHome"]["cloneUrlMockOnly"] = not webhook_configured
    _append_event(project, "repository_created", actor, f"{actor or '老师'} 创建了 Gitea 仓库 {project['repository']['repoName']}")
    saved = _save_project(db, project)
    return _enrich(saved, actor)


def bind_project_repository(db: Session, project_id: str, payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    project = _load_project(db, project_id)
    repo_name = payload.get("repoName") or project["repository"].get("repoName") or project_id
    default_urls = _repo_urls(repo_name, payload.get("giteaOwner") or "campus")
    html_url = payload.get("htmlUrl") or default_urls["htmlUrl"]
    project["repository"].update(
        {
            "repoName": repo_name,
            "giteaOwner": payload.get("giteaOwner") or "campus",
            "htmlUrl": html_url,
            "cloneUrl": payload.get("cloneUrl") or default_urls["cloneUrl"],
            "sshUrl": payload.get("sshUrl") or default_urls["sshUrl"],
            "defaultBranch": payload.get("defaultBranch") or "main",
            "taskBranch": payload.get("taskBranch") or project["repository"].get("taskBranch"),
            "status": "created",
            "webhookConfigured": bool(payload.get("webhookConfigured", False)),
            "lastSyncedAt": _now_label(),
        }
    )
    _append_event(project, "repository_bound", actor, f"{actor or '老师'} 绑定了已有仓库 {repo_name}")
    saved = _save_project(db, project)
    return _enrich(saved, actor)


def confirm_clone(db: Session, project_id: str, *, user_id: str) -> dict[str, Any]:
    project = _load_project(db, project_id)
    member = _find_member(project, user_id)
    member.update({"cloneStatus": "done", "statusLabel": "已拉取", "progress": max(int(member.get("progress") or 0), 35)})
    _append_event(project, "clone_confirmed", user_id, f"{user_id} 已确认完成 clone 拉取")
    saved = _save_project(db, project)
    return _enrich(saved, user_id)


def _upsert_pr(project: dict[str, Any], pr_payload: dict[str, Any]) -> None:
    number = int(pr_payload.get("number") or 0)
    prs = project.setdefault("pullRequests", [])
    existing = next((item for item in prs if int(item.get("number") or 0) == number), None)
    if existing:
        existing.update(pr_payload)
    else:
        prs.insert(0, {"id": f"pr-{number}", **pr_payload})


def _legacy_apply_gitea_webhook(db: Session, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    project = _load_project(db, project_id)
    event_type = payload.get("type") or payload.get("hook_name") or "unknown"
    sender = payload.get("sender") or payload.get("actor") or "系统"
    repo = project.get("repository") or {}
    if event_type == "push":
        member = _find_member(project, sender)
        member["pushStatus"] = "detected"
        member["prStatus"] = "needs_pr"
        member["statusLabel"] = "PR 待创建"
        member["commitCount"] = int(member.get("commitCount") or 0) + int(payload.get("commitCount") or 1)
        member["lastCommitAt"] = _now_label()
        member["progress"] = max(int(member.get("progress") or 0), 58)
        commit_message = payload.get("commitMessage") or "检测到新的 Git push"
        project.setdefault("recentCommits", []).insert(
            0,
            {
                "id": f"commit-{len(project.get('recentCommits') or []) + 1}",
                "author": sender,
                "branch": payload.get("branch") or member.get("branch") or repo.get("taskBranch"),
                "message": commit_message,
                "time": _now_label(),
            },
        )
        _append_event(project, "push", sender, f"{sender} 推送了 {payload.get('branch') or member.get('branch')} 分支")
    elif event_type == "pull_request" and payload.get("action") == "opened":
        member = _find_member(project, sender)
        member["prStatus"] = "open"
        member["statusLabel"] = "PR 待审核"
        member["progress"] = max(int(member.get("progress") or 0), 74)
        number = int(payload.get("number") or len(project.get("pullRequests") or []) + 1)
        _upsert_pr(
            project,
            {
                "number": number,
                "title": payload.get("title") or f"{sender} 的协作提交",
                "creator": sender,
                "sourceBranch": payload.get("sourceBranch") or member.get("branch"),
                "targetBranch": payload.get("targetBranch") or repo.get("defaultBranch") or "main",
                "status": "open",
                "statusLabel": "PR 待审核",
                "leaderReviewStatus": "pending",
                "leaderReviewer": "",
                "teacherReviewStatus": "pending",
                "teacherReviewer": "",
                "reviewComment": "",
                "createdAt": _now_label(),
                "updatedAt": _now_label(),
                "url": payload.get("url") or f"{repo.get('htmlUrl', '').rstrip('/')}/pulls/{number}",
            },
        )
        _append_event(project, "pull_request", sender, f"{sender} 创建了 Pull Request #{number}")
    elif event_type == "pull_request" and payload.get("action") == "merged":
        creator = payload.get("creator") or sender
        member = _find_member(project, creator)
        member["prStatus"] = "merged"
        member["mergeStatus"] = "merged"
        member["statusLabel"] = "已完成"
        member["score"] = max(int(member.get("score") or 0), 96)
        member["progress"] = 100
        number = int(payload.get("number") or 0)
        if number:
            _upsert_pr(project, {"number": number, "status": "merged", "statusLabel": "已合并", "updatedAt": _now_label()})
        _append_event(project, "merge", sender, f"{sender} 合并了 {member.get('branch')} -> {repo.get('defaultBranch') or 'main'}")
    saved = _save_project(db, project)
    return _enrich(saved, sender)


def apply_gitea_webhook(db: Session, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    project = _load_project(db, project_id)
    event_type = payload.get("hook_name") or payload.get("type") or "unknown"
    sender = _sender_username(payload) or "system"
    repo = project.get("repository") or {}

    if event_type == "push":
        branch = payload.get("branch") or _branch_from_ref(payload.get("ref")) or repo.get("taskBranch")
        commits = payload.get("commits") if isinstance(payload.get("commits"), list) else []
        recent_commits = project.setdefault("recentCommits", [])
        if commits:
            recent_commits[:] = [item for item in recent_commits if str(item.get("sha") or "").strip()]
        existing_shas = {item.get("sha") for item in recent_commits if item.get("sha")}
        member_counts: dict[str, int] = {}
        member_refs: dict[str, dict[str, Any]] = {}
        inserted_shas: list[str] = []

        for commit in commits:
            if not isinstance(commit, dict):
                continue
            sha = _commit_sha(commit)
            if sha and sha in existing_shas:
                continue
            if _is_gitea_system_commit(commit):
                continue
            match = match_campus_user_from_gitea_event(
                db,
                sender_username=sender,
                commit_author=commit.get("author") if isinstance(commit.get("author"), dict) else {},
            )
            if _is_gitea_system_login(str(match.get("displayName") or "")):
                continue
            author = match["displayName"]
            member = _find_existing_member_for_gitea_match(project, match, sender)
            recent_commits.insert(
                0,
                {
                    "id": f"commit-{sha[:12] or len(recent_commits) + 1}",
                    "sha": sha,
                    "author": author,
                    "branch": branch,
                    "message": _commit_message(commit),
                    "time": _now_label(),
                    "source": "gitea_webhook",
                },
            )
            if sha:
                existing_shas.add(sha)
                inserted_shas.append(sha)
            if member:
                member_key = str(member.get("id") or member.get("studentId") or member.get("name") or sender)
                member_refs[member_key] = member
                member_counts[member_key] = member_counts.get(member_key, 0) + 1
            _upsert_coach_feedback(project, _coach_queue_entry(commit, branch, author))

        if not commits and not _is_gitea_system_login(sender):
            author = _match_student_by_username(db, sender, sender)
            member = _find_existing_member_for_gitea_match(project, {"displayName": author}, sender)
            if member:
                member_key = str(member.get("id") or member.get("studentId") or member.get("name") or sender)
                member_refs[member_key] = member
                member_counts[member_key] = int(payload.get("commitCount") or 1)
            recent_commits.insert(
                0,
                {
                    "id": f"commit-{len(recent_commits) + 1}",
                    "author": author,
                    "branch": branch,
                    "message": payload.get("commitMessage") or "Detected Git push",
                    "time": _now_label(),
                },
            )

        for member_key, count in member_counts.items():
            member = member_refs[member_key]
            member["source"] = "gitea"
            member["pushStatus"] = "detected"
            member["prStatus"] = "needs_pr"
            member["statusLabel"] = "PR pending"
            member["commitCount"] = int(member.get("commitCount") or 0) + count
            member["lastCommitAt"] = _now_label()
            member["progress"] = max(int(member.get("progress") or 0), 58)

        if member_counts:
            dedupe = inserted_shas[0] if inserted_shas else f"push:{sender}:{branch}:{_now_label()}"
            _append_unique_event(project, "push", sender, f"{sender} pushed {branch}", dedupe)
        del recent_commits[20:]

    elif str(event_type).startswith("pull_request"):
        pr = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else {}
        action = str(payload.get("action") or "").lower()
        number = int(pr.get("number") or payload.get("number") or 0)
        pr_user = pr.get("user") if isinstance(pr.get("user"), dict) else {}
        creator_login = payload.get("creator") or pr_user.get("login") or pr_user.get("username") or sender
        if _is_gitea_system_login(str(creator_login or sender)):
            saved = _save_project(db, project)
            return _enrich(saved, sender)
        match = match_campus_user_from_gitea_event(db, sender_username=str(creator_login or sender), commit_author={})
        creator = match["displayName"]
        member = _find_existing_member_for_gitea_match(project, match, str(creator_login or sender))
        head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
        base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
        source_branch = payload.get("sourceBranch") or head.get("ref") or (member.get("branch") if member else "") or repo.get("taskBranch") or ""
        target_branch = payload.get("targetBranch") or base.get("ref") or repo.get("defaultBranch") or "main"
        merged = action == "merged" or bool(pr.get("merged"))
        closed = action == "closed" and not merged
        status = "merged" if merged else ("closed" if closed else "open")

        if member and status == "merged":
            member["prStatus"] = "merged"
            member["mergeStatus"] = "merged"
            member["statusLabel"] = "Merged"
            member["progress"] = 100
        elif member and status == "open":
            member["prStatus"] = "open"
            member["statusLabel"] = "PR pending review"
            member["progress"] = max(int(member.get("progress") or 0), 74)
        elif member:
            member["prStatus"] = "closed"
            member["statusLabel"] = "PR closed"

        if number:
            _upsert_pr(
                project,
                {
                    "number": number,
                    "title": pr.get("title") or payload.get("title") or f"Pull Request #{number}",
                    "creator": creator,
                    "sourceBranch": source_branch,
                    "targetBranch": target_branch,
                    "status": status,
                    "statusLabel": "Merged" if status == "merged" else ("Closed" if status == "closed" else "PR pending review"),
                    "leaderReviewStatus": "pending",
                    "leaderReviewer": "",
                    "teacherReviewStatus": "pending",
                    "teacherReviewer": "",
                    "reviewComment": "",
                    "createdAt": _now_label(),
                    "updatedAt": _now_label(),
                    "url": pr.get("html_url") or payload.get("url") or f"{repo.get('htmlUrl', '').rstrip('/')}/pulls/{number}",
                    "source": "gitea_webhook",
                },
            )
            related_prs = [
                item
                for item in project.get("pullRequests") or []
                if str(item.get("creator") or "") == str(creator)
            ]
            if member:
                member["prCount"] = max(int(member.get("prCount") or 0), len(related_prs), 1)
                member["mergedPrCount"] = max(
                    int(member.get("mergedPrCount") or 0),
                    sum(1 for item in related_prs if item.get("status") == "merged"),
                )
                member["source"] = "gitea"
            _mark_gitea_sync_state(
                project,
                status="synced",
                pr_source="gitea",
                webhook_status=repo.get("webhookStatus") or "configured",
            )
            event_kind = "merge" if status == "merged" else "pull_request"
            _append_unique_event(project, event_kind, sender, f"{sender} updated Pull Request #{number}", f"pr:{number}:{status}:{action}")

    # Task 4: 规则校验，写入 lastWorkflowRuleResult
    if event_type == "push" or str(event_type).startswith("pull_request"):
        try:
            matched_sender = match_campus_user_from_gitea_event(db, sender_username=sender, commit_author={})
            workflow_event_type = "pull_request" if str(event_type).startswith("pull_request") else event_type
            rule_result = evaluate_git_workflow(
                event_type=workflow_event_type,
                payload=payload,
                project=project,
                matched_member=matched_sender,
                author_match_source=matched_sender.get("source") or "unmatched",
            )
            project["lastWorkflowRuleResult"] = rule_result
            # 若有 error 级别违规，更新成员 statusLabel 附加提示（不回退进度）
            has_error = any(v.get("severity") == "error" for v in rule_result.get("violations") or [])
            if has_error and event_type == "push":
                branch_push = payload.get("branch") or _branch_from_ref(payload.get("ref")) or ""
                for commit in (payload.get("commits") or []):
                    if not isinstance(commit, dict):
                        continue
                    c_match = match_campus_user_from_gitea_event(
                        db,
                        sender_username=sender,
                        commit_author=commit.get("author") if isinstance(commit.get("author"), dict) else {},
                    )
                    c_author_lookup = _member_lookup_from_match(c_match, sender)
                    if c_author_lookup:
                        member = _find_member(project, c_author_lookup)
                        current_label = str(member.get("statusLabel") or "")
                        if "修正" not in current_label:
                            member["statusLabel"] = f"{current_label}·分支需修正" if current_label else "推送已检测·分支需修正"
        except Exception as _rule_exc:
            import logging as _log
            _log.getLogger(__name__).warning("apply_gitea_webhook: 规则校验失败: %s", _rule_exc)

    saved = _save_project(db, project)
    return _enrich(saved, sender)


def find_project_id_by_repo_name(db: Session, repo_name: str) -> str | None:
    """在 MODULE=team_collaboration_git 的 active payloads 中匹配
    repository.repoName / repository.giteaRepo / id（忽略大小写）。
    full_name 形如 campus/foo 时取最后一段。
    """
    if not repo_name:
        return None
    # 标准化：取 full_name 最后一段，转小写
    normalized = repo_name.strip().lower().split("/")[-1]
    projects = _store(db).list_payloads(MODULE, PROJECT, status="active")
    for project in projects:
        pid = str(project.get("id") or "").lower()
        repo = project.get("repository") or {}
        repo_name_field = str(repo.get("repoName") or "").lower()
        gitea_repo_field = str(repo.get("giteaRepo") or "").lower()
        if normalized in (pid, repo_name_field, gitea_repo_field):
            return str(project.get("id") or "")
        # 还尝试 split 后的最后段对比
        for field_val in (repo_name_field, gitea_repo_field):
            if field_val and normalized == field_val.split("/")[-1]:
                return str(project.get("id") or "")
    return None


def resolve_team_project_id(db: Session, project_id: str, payload: dict) -> str:
    """优先按 project_id 定位项目；若无效则从 payload.repository 反查 repoName。
    两边均失败时 raise FileNotFoundError。
    """
    # 1) 直接按 project_id 加载
    existing = _store(db).get_payload(MODULE, PROJECT, project_id)
    if existing:
        return project_id

    # 2) 从 payload 提取仓库名，尝试反查
    repo_payload = payload.get("repository") or {}
    candidates = [
        repo_payload.get("name"),
        repo_payload.get("full_name"),
        repo_payload.get("repo"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        found_id = find_project_id_by_repo_name(db, str(candidate))
        if found_id:
            return found_id

    raise FileNotFoundError(f"team project not found for webhook (project_id={project_id!r})")


def enqueue_git_coach_feedback(project_id: str, payload: dict[str, Any]) -> None:
    """后台异步任务：调用 git_coach_service 生成真实 AI Git 教练反馈。
    LLM 失败时自动 fallback，不抛出异常，不阻塞 Webhook 响应。
    """
    db = SessionLocal()
    try:
        from app.services.git_coach_service import generate_commit_coach_feedback
        generate_commit_coach_feedback(db, project_id, payload=payload)
    except Exception as exc:
        # 最外层兜底：绝不让后台任务把进程打崩
        import logging
        logging.getLogger(__name__).error(
            "enqueue_git_coach_feedback: 未预期异常 project_id=%s: %s", project_id, exc
        )
    finally:
        db.close()


def _find_pr(project: dict[str, Any], pr_number: int) -> dict[str, Any]:
    for pr in project.get("pullRequests") or []:
        if int(pr.get("number") or 0) == int(pr_number or 0):
            return pr
    repo = project.get("repository") or {}
    pr = {
        "id": f"pr-{pr_number}",
        "number": int(pr_number or len(project.get("pullRequests") or []) + 1),
        "title": f"Pull Request #{pr_number}",
        "creator": "",
        "sourceBranch": repo.get("taskBranch") or "feature/task",
        "targetBranch": repo.get("defaultBranch") or "main",
        "status": "open",
        "statusLabel": "PR 待审核",
        "leaderReviewStatus": "pending",
        "leaderReviewer": "",
        "teacherReviewStatus": "pending",
        "teacherReviewer": "",
        "reviewComment": "",
        "createdAt": _now_label(),
        "updatedAt": _now_label(),
        "url": f"{str(repo.get('htmlUrl') or '').rstrip('/')}/pulls/{pr_number}",
    }
    project.setdefault("pullRequests", []).insert(0, pr)
    return pr


def review_pull_request(
    db: Session,
    project_id: str,
    pr_number: int,
    payload: dict[str, Any],
    *,
    actor: dict[str, Any] | str,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    project = _load_project(db, project_id)
    data = payload or {}
    action = str(data.get("action") or "recommend_merge")
    comment = str(data.get("comment") or "")
    actor_display = _actor_name(actor, "reviewer")
    review_actions = {
        "leader_approve",
        "recommend_merge",
        "request_changes",
        "leader_reject",
        "teacher_reject",
        "reject",
    }
    merge_actions = {"teacher_approve", "teacher_merge", "merge", "leader_merge", "approve_merge"}
    if action in review_actions | merge_actions and not _project_can_review_pull_requests(project, actor):
        raise PermissionError("only team leaders or teachers can review pull requests")
    pr = _find_pr(project, int(pr_number))
    now = _now_label()

    if action in {"leader_approve", "recommend_merge"}:
        pr["leaderReviewStatus"] = "recommended"
        pr["leaderReviewer"] = actor_display
        pr["leaderReviewedAt"] = now
        pr["statusLabel"] = "队长建议合并"
        pr["reviewComment"] = comment
        event_type = "pr_recommended"
        event_text = f"{actor_display} 初审 PR #{pr_number} 并建议合并"
    elif action in {"request_changes", "leader_reject"}:
        pr["leaderReviewStatus"] = "changes_requested"
        pr["leaderReviewer"] = actor_display
        pr["leaderReviewedAt"] = now
        pr["statusLabel"] = "队长要求修改"
        pr["reviewComment"] = comment
        event_type = "pr_changes_requested"
        event_text = f"{actor_display} 要求 PR #{pr_number} 修改后再提交"
    elif action in merge_actions:
        owner, repo, _branch = _gitea_repo_target(project)
        gitea_svc = gitea or GiteaService()
        if not gitea_svc.enabled or not gitea_svc.token or not owner or not repo:
            raise RuntimeError("无法合并 PR：Gitea 未配置或仓库未绑定")
        try:
            gitea_svc.merge_pull_request(
                owner=owner,
                repo=repo,
                index=int(pr_number),
                merge_message=comment or f"Merge PR #{pr_number}",
            )
        except Exception as exc:
            merged_after_error = False
            try:
                current_prs = gitea_svc.list_pull_requests(owner=owner, repo=repo, state="all")
                current_pr = next(
                    (item for item in current_prs if int(item.get("number") or 0) == int(pr_number)),
                    None,
                )
                merged_after_error = bool(current_pr and current_pr.get("status") == "merged")
            except Exception:
                merged_after_error = False
            if not merged_after_error:
                raise RuntimeError(f"Gitea 合并 PR #{pr_number} 失败：{exc}") from exc
        if _actor_is_teacher_like(actor) or action in {"teacher_approve", "teacher_merge"}:
            pr["teacherReviewStatus"] = "approved"
            pr["teacherReviewer"] = actor_display
            pr["teacherReviewedAt"] = now
        if action in {"leader_merge", "approve_merge"} or bool(
            _actor_identifiers(actor) & _project_leader_identifiers(project)
        ):
            pr["leaderReviewStatus"] = "approved"
            pr["leaderReviewer"] = actor_display
            pr["leaderReviewedAt"] = now
        pr["status"] = "merged"
        pr["statusLabel"] = "已合并"
        pr["reviewComment"] = comment
        creator = pr.get("creator") or data.get("creator") or actor_display
        member = _find_member(project, creator)
        member["prStatus"] = "merged"
        member["mergeStatus"] = "merged"
        member["statusLabel"] = "已完成"
        member["progress"] = 100
        member["score"] = max(int(member.get("score") or 0), int(data.get("score") or 96))
        project["repository"]["status"] = "completed" if all(
            item.get("mergeStatus") == "merged" for item in project.get("memberProgress") or []
        ) else project.get("repository", {}).get("status") or "collaborating"
        event_type = "pr_merged"
        event_text = f"{actor_display} 审核并合并 PR #{pr_number}"
    elif action in {"teacher_reject", "reject"}:
        pr["teacherReviewStatus"] = "rejected"
        pr["teacherReviewer"] = actor_display
        pr["teacherReviewedAt"] = now
        pr["status"] = "open"
        pr["statusLabel"] = "教师要求修改"
        pr["reviewComment"] = comment
        event_type = "pr_teacher_rejected"
        event_text = f"{actor_display} 驳回 PR #{pr_number}，要求继续修改"
    else:
        pr["reviewComment"] = comment
        event_type = "pr_reviewed"
        event_text = f"{actor_display} 更新了 PR #{pr_number} 审核意见"

    pr["updatedAt"] = now
    _append_event(project, event_type, actor_display, event_text)
    saved = _save_project(db, project)
    return _enrich(saved, actor_display)


def evaluate_team_contribution(db: Session, project_id: str, payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    project = _load_project(db, project_id)
    data = payload or {}
    for item in data.get("scores") or []:
        member = _find_member(project, str(item.get("memberId") or item.get("name") or ""))
        if "score" in item:
            member["score"] = int(item.get("score") or 0)
        if "contribution" in item:
            member["contribution"] = int(item.get("contribution") or 0)
            member["contributionSource"] = "teacher"
        if "comment" in item:
            member["teacherComment"] = str(item.get("comment") or "")
    project["teacherEvaluation"] = {
        "summary": str(data.get("summary") or ""),
        "auditor": actor,
        "updatedAt": _now_label(),
    }
    _append_event(project, "contribution_evaluated", actor, f"{actor} 评价了团队贡献度")
    saved = _save_project(db, project)
    return _enrich(saved, actor)


def refresh_project_status(
    db: Session,
    project_id: str,
    *,
    stage: str = "detected",
    actor: str = "系统",
    actor_info: dict[str, Any] | str | None = None,
    gitea: GiteaService | None = None,
    allow_demo_stage: bool = False,
) -> dict[str, Any]:
    """Force sync from Gitea. Demo stage simulation only when allow_demo_stage=True."""
    if not allow_demo_stage:
        return sync_project_from_gitea(db, project_id, actor=actor_info or actor, gitea=gitea)

    project = _load_project(db, project_id)
    if stage == "merged":
        member = _find_member(project, "李明")
        member["cloneStatus"] = "done"
        member["pushStatus"] = "detected"
        member["prStatus"] = "merged"
        member["mergeStatus"] = "merged"
        member["statusLabel"] = "已完成"
        member["score"] = max(int(member.get("score") or 0), 96)
        member["progress"] = 100
        project["repository"]["status"] = "completed"
    elif stage == "pr":
        member = _find_member(project, "李明")
        member["pushStatus"] = "detected"
        member["prStatus"] = "open"
        member["statusLabel"] = "PR 待审核"
        member["progress"] = max(int(member.get("progress") or 0), 74)
    elif stage == "push":
        member = _find_member(project, "李明")
        member["pushStatus"] = "detected"
        member["prStatus"] = "needs_pr"
        member["statusLabel"] = "PR 待创建"
        member["progress"] = max(int(member.get("progress") or 0), 58)
    project["repository"]["lastSyncedAt"] = _now_label()
    _append_event(project, "status_refreshed", actor, f"{actor} 刷新了团队 Git 协作状态")
    saved = _save_project(db, project)
    return _enrich(saved, actor)
