import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.json_store import JsonStore, make_record_key
from app.services.gitea_account_service import RepoPermission, ensure_repository_collaborators, match_campus_user_from_gitea_event
from app.services.gitea_service import GiteaService, is_stale_gitea_url, normalize_repo_slug
from app.utils.datetime import utc_now_iso


MODULE = "code_repository"
PROJECT = "project"
STAR = "star"
FAVORITE = "favorite"
REPORT = "report"


def _store(db: Session) -> JsonStore:
    return JsonStore(db)


def _unique_slug(store: JsonStore, requested: str, title: str) -> str:
    base = normalize_repo_slug(requested or title)
    existing = {item.get("slug") for item in store.list_payloads(MODULE, PROJECT)}
    if base not in existing:
        return base
    return f"{base}-{uuid.uuid4().hex[:6]}"


def _relation_key(project_id: str, user_id: str) -> str:
    return f"{project_id}:{user_id}"


def _project_owner_id(project: dict[str, Any]) -> str:
    return str(project.get("authorId") or project.get("ownerId") or project.get("author") or "")


def _active_projects(store: JsonStore) -> list[dict[str, Any]]:
    return [item for item in store.list_payloads(MODULE, PROJECT) if item.get("status", "active") != "deleted"]


def _project_counts(store: JsonStore, project_id: str) -> tuple[int, int]:
    stars = [item for item in store.list_payloads(MODULE, STAR) if item.get("projectId") == project_id and item.get("active")]
    favorites = [item for item in store.list_payloads(MODULE, FAVORITE) if item.get("projectId") == project_id and item.get("active")]
    return len(stars), len(favorites)


def _viewer_flags(store: JsonStore, project_id: str, viewer: str | None) -> tuple[bool, bool]:
    if not viewer:
        return False, False
    star = store.get_payload(MODULE, STAR, _relation_key(project_id, viewer))
    favorite = store.get_payload(MODULE, FAVORITE, _relation_key(project_id, viewer))
    return bool(star and star.get("active")), bool(favorite and favorite.get("active"))


def _enrich_project(store: JsonStore, project: dict[str, Any], viewer: str | None = None) -> dict[str, Any]:
    if _refresh_project_git_urls(project):
        store.upsert(MODULE, PROJECT, project["id"], project, owner_id=_project_owner_id(project), status=project.get("status") or "active")
    star_count, favorite_count = _project_counts(store, project["id"])
    is_starred, is_favorited = _viewer_flags(store, project["id"], viewer)
    enriched = dict(project)
    enriched.update(
        {
            "starCount": star_count,
            "favoriteCount": favorite_count,
            "isStarred": is_starred,
            "isFavorited": is_favorited,
        }
    )
    return enriched


def _refresh_project_git_urls(project: dict[str, Any]) -> bool:
    owner = str(project.get("giteaOwner") or "campus").strip() or "campus"
    repo = normalize_repo_slug(str(project.get("giteaRepo") or project.get("slug") or project.get("id") or "project"))
    branch = str(project.get("defaultBranch") or "main").strip() or "main"
    urls = GiteaService().repository_urls(owner=owner, repo=repo, branch=branch)
    changed = False
    for key in ("htmlUrl", "cloneUrl", "sshUrl", "archiveUrl"):
        if not project.get(key) or is_stale_gitea_url(project.get(key)):
            project[key] = urls[key]
            changed = True
    if project.get("giteaOwner") != owner:
        project["giteaOwner"] = owner
        changed = True
    if project.get("giteaRepo") != repo:
        project["giteaRepo"] = repo
        changed = True
    if project.get("defaultBranch") != branch:
        project["defaultBranch"] = branch
        changed = True
    return changed


def _branch_from_ref(ref: str | None) -> str:
    value = str(ref or "")
    if value.startswith("refs/heads/"):
        return value.removeprefix("refs/heads/")
    return value


def _sender_username(payload: dict[str, Any]) -> str:
    sender = payload.get("sender") or payload.get("pusher") or payload.get("actor") or ""
    if isinstance(sender, dict):
        return str(sender.get("username") or sender.get("login") or sender.get("name") or "")
    return str(sender or "")


def _commit_sha(commit: dict[str, Any]) -> str:
    return str(commit.get("id") or commit.get("sha") or "").strip()


def _commit_author(commit: dict[str, Any], fallback: str) -> str:
    author = commit.get("author") if isinstance(commit.get("author"), dict) else {}
    return str(author.get("name") or author.get("username") or fallback or "unknown")


def _commit_message(commit: dict[str, Any]) -> str:
    return str(commit.get("message") or "Detected Git push").strip()


def _upsert_pr(project: dict[str, Any], pr_payload: dict[str, Any]) -> None:
    number = int(pr_payload.get("number") or 0)
    prs = project.setdefault("pullRequests", [])
    existing = next((item for item in prs if int(item.get("number") or 0) == number), None)
    if existing:
        existing.update(pr_payload)
    else:
        prs.insert(0, {"id": f"pr-{number}", **pr_payload})


def _append_git_event(project: dict[str, Any], event_type: str, actor: str, text: str, dedupe_key: str) -> None:
    events = project.setdefault("gitEvents", [])
    if dedupe_key and any(item.get("dedupeKey") == dedupe_key for item in events):
        return
    events.insert(
        0,
        {
            "id": f"event-{len(events) + 1}-{normalize_repo_slug(actor or event_type)}",
            "type": event_type,
            "actor": actor or "system",
            "text": text,
            "dedupeKey": dedupe_key,
            "time": utc_now_iso(),
        },
    )
    del events[20:]


def _queue_git_coach_feedback(project: dict[str, Any], commit: dict[str, Any], branch: str, author: str) -> None:
    sha = _commit_sha(commit)
    feedback = project.setdefault("aiGitCoachFeedback", [])
    existing = next((item for item in feedback if sha and item.get("sha") == sha), None)
    payload = {
        "id": f"coach-{sha[:12] or normalize_repo_slug(author)}",
        "sha": sha,
        "author": author,
        "branch": branch,
        "status": "fallback",
        "summary": "AI Git coach is offline; rule diagnosis: commit received and branch naming is acceptable.",
        "createdAt": utc_now_iso(),
    }
    if existing:
        existing.update(payload)
    else:
        feedback.insert(0, payload)
    del feedback[20:]


def publish_repository(
    db: Session,
    payload: dict[str, Any],
    *,
    current_user: str,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    store = _store(db)
    title = str(payload.get("title") or "").strip() or "未命名项目"
    description = str(payload.get("description") or "").strip()
    slug = _unique_slug(store, str(payload.get("slug") or ""), title)
    gitea_client = gitea or GiteaService()
    repo = gitea_client.create_repository(
        name=slug,
        description=description,
        private=bool(payload.get("private", False)),
        auto_init=True,
    )
    create_webhook = getattr(gitea_client, "create_webhook", None)
    webhook_configured = True
    if callable(create_webhook):
        webhook_configured = bool(
            create_webhook(
                owner=repo.get("giteaOwner") or "campus",
                repo=repo.get("giteaRepo") or slug,
                project_id=slug,
                module="code_repository",
            )
        )
    permissions = [RepoPermission(current_user, "admin", "repository_author")]
    for collaborator in payload.get("collaborators") or []:
        collaborator_id = str(collaborator.get("username") if isinstance(collaborator, dict) else collaborator).strip()
        if collaborator_id and collaborator_id != current_user:
            permissions.append(RepoPermission(collaborator_id, "write", "repository_collaborator"))
    permission_sync = ensure_repository_collaborators(
        db,
        repo.get("giteaOwner") or "campus",
        repo.get("giteaRepo") or slug,
        permissions,
        gitea=gitea_client,
    )
    now = utc_now_iso()
    project = {
        "id": slug,
        "title": title,
        "slug": slug,
        "description": description,
        "author": current_user or "anonymous",
        "avatar": payload.get("avatar") or "",
        "language": payload.get("language") or "Other",
        "course": payload.get("course") or "",
        "tags": payload.get("tags") or [],
        "collaborators": payload.get("collaborators") or [],
        "visibility": "private" if payload.get("private") else "public",
        "status": "active",
        "recommendScore": int(payload.get("recommendScore") or 0),
        "readme": payload.get("readme") or "",
        "readmeSyncedAt": "",
        "createdAt": now,
        "updatedAt": now,
        "webhookConfigured": webhook_configured,
        "giteaSyncStatus": "connected" if webhook_configured else "fallback",
        "lastSyncedAt": now,
        "recentCommits": [],
        "pullRequests": [],
        "gitEvents": [],
        "aiGitCoachFeedback": [],
        "giteaCollaborators": permission_sync,
        **repo,
    }
    saved = store.upsert(MODULE, PROJECT, project["id"], project, owner_id=current_user or "", status="active")
    return _enrich_project(store, saved, current_user)


def apply_code_repository_gitea_webhook(db: Session, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    store = _store(db)
    project = store.get_payload(MODULE, PROJECT, project_id)
    if not project:
        raise ValueError("repository not found")
    event_type = payload.get("hook_name") or payload.get("type") or "unknown"
    sender = _sender_username(payload) or "system"
    now = utc_now_iso()

    if event_type == "push":
        branch = payload.get("branch") or _branch_from_ref(payload.get("ref")) or project.get("defaultBranch") or "main"
        commits = payload.get("commits") if isinstance(payload.get("commits"), list) else []
        recent = project.setdefault("recentCommits", [])
        existing_shas = {item.get("sha") for item in recent if item.get("sha")}
        inserted = []
        for commit in commits:
            if not isinstance(commit, dict):
                continue
            sha = _commit_sha(commit)
            if sha and sha in existing_shas:
                continue
            match = match_campus_user_from_gitea_event(
                db,
                sender_username=sender,
                commit_author=commit.get("author") if isinstance(commit.get("author"), dict) else {},
            )
            author = match["displayName"]
            recent.insert(
                0,
                {
                    "id": f"commit-{sha[:12] or len(recent) + 1}",
                    "sha": sha,
                    "author": author,
                    "branch": branch,
                    "message": _commit_message(commit),
                    "time": now,
                },
            )
            if sha:
                existing_shas.add(sha)
                inserted.append(sha)
            _queue_git_coach_feedback(project, commit, branch, author)
        if inserted:
            _append_git_event(project, "push", sender, f"{sender} pushed {branch}", inserted[0])
        project["giteaSyncStatus"] = "synced"
        project["lastSyncedAt"] = now
        project["updatedAt"] = now
        del recent[20:]

    elif event_type == "pull_request":
        pr = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else {}
        action = str(payload.get("action") or "").lower()
        number = int(pr.get("number") or payload.get("number") or 0)
        pr_user = pr.get("user") if isinstance(pr.get("user"), dict) else {}
        creator_login = str(pr_user.get("login") or pr_user.get("username") or payload.get("creator") or sender)
        creator = match_campus_user_from_gitea_event(db, sender_username=creator_login, commit_author={})["displayName"]
        head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
        base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
        merged = action == "merged" or bool(pr.get("merged"))
        closed = action == "closed" and not merged
        status = "merged" if merged else ("closed" if closed else "open")
        if number:
            _upsert_pr(
                project,
                {
                    "number": number,
                    "title": pr.get("title") or payload.get("title") or f"Pull Request #{number}",
                    "creator": creator,
                    "sourceBranch": payload.get("sourceBranch") or head.get("ref") or "",
                    "targetBranch": payload.get("targetBranch") or base.get("ref") or project.get("defaultBranch") or "main",
                    "status": status,
                    "statusLabel": "Merged" if status == "merged" else ("Closed" if status == "closed" else "PR pending review"),
                    "url": pr.get("html_url") or payload.get("url") or f"{str(project.get('htmlUrl') or '').rstrip('/')}/pulls/{number}",
                    "updatedAt": now,
                },
            )
            _append_git_event(project, "merge" if status == "merged" else "pull_request", sender, f"{sender} updated Pull Request #{number}", f"pr:{number}:{status}:{action}")
        project["giteaSyncStatus"] = "synced"
        project["lastSyncedAt"] = now
        project["updatedAt"] = now

    saved = store.upsert(MODULE, PROJECT, project["id"], project, owner_id=_project_owner_id(project), status=project.get("status") or "active")
    return _enrich_project(store, saved)


def enqueue_code_repository_git_coach_feedback(project_id: str, payload: dict[str, Any]) -> None:
    return None


def list_repositories(
    db: Session,
    *,
    viewer: str | None = None,
    query: str = "",
    language: str = "",
    tag: str = "",
    sort: str = "latest",
) -> list[dict[str, Any]]:
    store = _store(db)
    result = [_enrich_project(store, project, viewer) for project in _active_projects(store)]
    result = [item for item in result if item.get("status") == "active"]
    if query:
        keyword = query.lower()
        result = [
            item
            for item in result
            if keyword in (item.get("title") or "").lower()
            or keyword in (item.get("description") or "").lower()
            or keyword in " ".join(item.get("tags") or []).lower()
        ]
    if language:
        result = [item for item in result if (item.get("language") or "").lower() == language.lower()]
    if tag:
        result = [item for item in result if tag in (item.get("tags") or [])]
    if sort == "stars":
        result.sort(key=lambda item: (item.get("starCount") or 0, item.get("createdAt") or ""), reverse=True)
    elif sort == "favorites":
        result.sort(key=lambda item: (item.get("favoriteCount") or 0, item.get("createdAt") or ""), reverse=True)
    elif sort == "relevant":
        result.sort(
            key=lambda item: (
                (item.get("recommendScore") or 0)
                + (item.get("favoriteCount") or 0) * 5
                + (item.get("starCount") or 0) * 2,
                item.get("createdAt") or "",
            ),
            reverse=True,
        )
    elif sort == "recommended":
        result.sort(key=lambda item: (item.get("recommendScore") or 0, item.get("starCount") or 0), reverse=True)
    else:
        result.sort(key=lambda item: item.get("createdAt") or "", reverse=True)
    return result


def get_repository_detail(
    db: Session,
    project_id: str,
    *,
    viewer: str | None = None,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    store = _store(db)
    project = store.get_payload(MODULE, PROJECT, project_id)
    if not project:
        raise ValueError("repository not found")
    if project.get("status") == "active":
        try:
            readme = (gitea or GiteaService()).get_readme(
                owner=project.get("giteaOwner") or "",
                repo=project.get("giteaRepo") or project.get("slug") or "",
                branch=project.get("defaultBranch") or "main",
            )
            if readme:
                project["readme"] = readme
                project["readmeSyncedAt"] = utc_now_iso()
                store.upsert(MODULE, PROJECT, project["id"], project, owner_id=_project_owner_id(project), status=project.get("status") or "active")
        except Exception:
            project["readmeError"] = "README 尚未同步"
    return _enrich_project(store, project, viewer)


def _toggle_relation(db: Session, record_type: str, project_id: str, user_id: str) -> dict[str, Any]:
    store = _store(db)
    project = store.get_payload(MODULE, PROJECT, project_id)
    if not project:
        raise ValueError("repository not found")
    key = _relation_key(project_id, user_id)
    existing = store.get_payload(MODULE, record_type, key)
    active = not bool(existing and existing.get("active"))
    payload = {
        "id": key,
        "projectId": project_id,
        "userId": user_id,
        "active": active,
        "updatedAt": utc_now_iso(),
    }
    store.upsert(MODULE, record_type, key, payload, owner_id=user_id, status="active" if active else "inactive")
    enriched = _enrich_project(store, project, user_id)
    return {
        "projectId": project_id,
        "starCount": enriched["starCount"],
        "favoriteCount": enriched["favoriteCount"],
        "isStarred": enriched["isStarred"],
        "isFavorited": enriched["isFavorited"],
    }


def toggle_repository_star(db: Session, project_id: str, user_id: str) -> dict[str, Any]:
    return _toggle_relation(db, STAR, project_id, user_id)


def toggle_repository_favorite(db: Session, project_id: str, user_id: str) -> dict[str, Any]:
    return _toggle_relation(db, FAVORITE, project_id, user_id)


def create_repository_report(
    db: Session,
    project_id: str,
    payload: dict[str, Any],
    *,
    reporter: str,
) -> dict[str, Any]:
    store = _store(db)
    project = store.get_payload(MODULE, PROJECT, project_id)
    if not project:
        raise ValueError("repository not found")
    report_id = make_record_key("repo-report")
    report = {
        "id": report_id,
        "projectId": project_id,
        "projectTitle": project.get("title") or "",
        "projectAuthor": project.get("author") or "",
        "reporter": reporter or "anonymous",
        "reason": payload.get("reason") or "违规内容",
        "description": payload.get("description") or "",
        "status": "pending",
        "createdAt": utc_now_iso(),
        "auditedAt": "",
        "auditor": "",
        "note": "",
    }
    return store.upsert(MODULE, REPORT, report_id, report, owner_id=reporter or "", status="pending")


def list_repository_reports(db: Session, *, status: str | None = None) -> list[dict[str, Any]]:
    reports = _store(db).list_payloads(MODULE, REPORT, status=status)
    return sorted(reports, key=lambda item: item.get("createdAt") or "", reverse=True)


def audit_repository_report(
    db: Session,
    report_id: str,
    payload: dict[str, Any],
    *,
    teacher_id: str,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    store = _store(db)
    report = store.get_payload(MODULE, REPORT, report_id)
    if not report:
        raise ValueError("report not found")
    project = store.get_payload(MODULE, PROJECT, report.get("projectId") or "")
    action = payload.get("action") or "reject"
    report["auditedAt"] = utc_now_iso()
    report["auditor"] = teacher_id or ""
    report["note"] = payload.get("note") or ""
    if action == "approve_delete":
        report["status"] = "approved"
        if project:
            project["status"] = "removed"
            project["removedAt"] = utc_now_iso()
            project["removedBy"] = teacher_id or ""
            project["removeReason"] = report["note"] or report.get("reason") or "违规项目"
            (gitea or GiteaService()).delete_repository(
                owner=project.get("giteaOwner") or "",
                repo=project.get("giteaRepo") or project.get("slug") or "",
            )
            store.upsert(MODULE, PROJECT, project["id"], project, owner_id=_project_owner_id(project), status="removed")
    else:
        report["status"] = "rejected"
    return store.upsert(MODULE, REPORT, report_id, report, owner_id=report.get("reporter") or "", status=report["status"])


def delete_repository_project(
    db: Session,
    project_id: str,
    *,
    teacher_id: str,
    reason: str = "教师审核删除",
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    store = _store(db)
    project = store.get_payload(MODULE, PROJECT, project_id)
    if not project:
        raise ValueError("repository not found")
    project["status"] = "removed"
    project["removedAt"] = utc_now_iso()
    project["removedBy"] = teacher_id or ""
    project["removeReason"] = reason
    (gitea or GiteaService()).delete_repository(
        owner=project.get("giteaOwner") or "",
        repo=project.get("giteaRepo") or project.get("slug") or "",
    )
    return store.upsert(MODULE, PROJECT, project_id, project, owner_id=_project_owner_id(project), status="removed")


def get_user_repository_profile(db: Session, user_id: str) -> dict[str, Any]:
    store = _store(db)
    projects = [_enrich_project(store, project, user_id) for project in _active_projects(store)]
    own = [
        item
        for item in projects
        if _project_owner_id(item) == user_id
    ]
    starred_ids = {
        item.get("projectId")
        for item in store.list_payloads(MODULE, STAR, owner_id=user_id)
        if item.get("active")
    }
    favorite_ids = {
        item.get("projectId")
        for item in store.list_payloads(MODULE, FAVORITE, owner_id=user_id)
        if item.get("active")
    }
    return {
        "userId": user_id,
        "ownProjects": [item for item in projects if item in own and item.get("status") == "active"],
        "collaboratingProjects": [item for item in projects if user_id in (item.get("collaborators") or []) and item.get("status") == "active"],
        "starredProjects": [item for item in projects if item.get("id") in starred_ids and item.get("status") == "active"],
        "favoriteProjects": [item for item in projects if item.get("id") in favorite_ids and item.get("status") == "active"],
    }


def get_repository_archive(db: Session, project_id: str, *, gitea: GiteaService | None = None) -> dict[str, str]:
    project = _store(db).get_payload(MODULE, PROJECT, project_id)
    if not project:
        raise ValueError("repository not found")
    branch = project.get("defaultBranch") or "main"
    url = (gitea or GiteaService()).get_archive_url(
        owner=project.get("giteaOwner") or "",
        repo=project.get("giteaRepo") or project.get("slug") or "",
        branch=branch,
    )
    return {"downloadUrl": url, "archiveUrl": url, "branch": branch}


def _require_repository(db: Session, project_id: str) -> dict[str, Any]:
    project = _store(db).get_payload(MODULE, PROJECT, project_id)
    if not project:
        raise ValueError("repository not found")
    return project


def _gitea_repo_target(project: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(project.get("giteaOwner") or ""),
        str(project.get("giteaRepo") or project.get("slug") or ""),
        str(project.get("defaultBranch") or "main"),
    )


def get_repository_tree(
    db: Session,
    project_id: str,
    *,
    path: str = "",
    ref: str | None = None,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    project = _require_repository(db, project_id)
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


def get_repository_blob(
    db: Session,
    project_id: str,
    *,
    path: str,
    ref: str | None = None,
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    project = _require_repository(db, project_id)
    owner, repo, branch = _gitea_repo_target(project)
    branch = ref or branch
    blob = (gitea or GiteaService()).get_file_content(owner=owner, repo=repo, path=path, branch=branch)
    return {
        "projectId": project_id,
        "ref": branch,
        **blob,
    }


def get_repository_languages(
    db: Session,
    project_id: str,
    *,
    gitea: GiteaService | None = None,
) -> list[dict[str, Any]]:
    project = _require_repository(db, project_id)
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
