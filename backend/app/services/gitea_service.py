import base64
import re
import secrets
import string
from typing import Any
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException

from app.core.config import settings

STALE_GITEA_URL_MARKERS = (
    "git.gezhi.local",
    "git.gezhisystem.com",
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
)


def _random_password(length: int = 28) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def normalize_repo_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-._")
    return slug or "project"


def is_stale_gitea_url(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return bool(text) and any(marker in text for marker in STALE_GITEA_URL_MARKERS)


def _normalize_public_base_url(value: str | None = None) -> str:
    return (value or settings.GITEA_PUBLIC_BASE_URL or "https://gezhisystem.com/gitea").strip().rstrip("/")


def _host_from_url(value: str) -> str:
    parsed = urlparse(value)
    return parsed.hostname or re.sub(r"^https?://", "", value).split("/", 1)[0].split(":", 1)[0]


def build_repository_urls(
    *,
    owner: str,
    repo: str,
    branch: str = "main",
    public_base_url: str | None = None,
    ssh_domain: str | None = None,
    ssh_port: int | None = None,
    ssh_user: str | None = None,
) -> dict[str, str]:
    repo_owner = str(owner or settings.GITEA_ORG or "campus").strip().strip("/") or "campus"
    repo_name = normalize_repo_slug(repo)
    default_branch = str(branch or "main").strip() or "main"
    public_base = _normalize_public_base_url(public_base_url)
    host = str(ssh_domain or settings.GITEA_SSH_DOMAIN or _host_from_url(public_base) or "gezhisystem.com").strip()
    port = int(ssh_port if ssh_port is not None else settings.GITEA_SSH_PORT or 22)
    user = str(ssh_user or settings.GITEA_SSH_USER or "git").strip() or "git"
    port_part = f":{port}" if port else ""
    html_url = f"{public_base}/{repo_owner}/{repo_name}"
    return {
        "giteaOwner": repo_owner,
        "giteaRepo": repo_name,
        "htmlUrl": html_url,
        "cloneUrl": f"{html_url}.git",
        "sshUrl": f"ssh://{user}@{host}{port_part}/{repo_owner}/{repo_name}.git",
        "defaultBranch": default_branch,
        "archiveUrl": f"{html_url}/archive/{default_branch}.zip",
    }


class GiteaService:
    def __init__(
        self,
        *,
        enabled: bool | None = None,
        base_url: str | None = None,
        public_base_url: str | None = None,
        ssh_domain: str | None = None,
        ssh_port: int | None = None,
        ssh_user: str | None = None,
        token: str | None = None,
        org: str | None = None,
    ):
        self.enabled = settings.GITEA_ENABLED if enabled is None else enabled
        self.base_url = (base_url or settings.GITEA_BASE_URL).rstrip("/")
        self.public_base_url = _normalize_public_base_url(public_base_url)
        self.ssh_domain = str(ssh_domain or settings.GITEA_SSH_DOMAIN or _host_from_url(self.public_base_url)).strip()
        self.ssh_port = int(ssh_port if ssh_port is not None else settings.GITEA_SSH_PORT or 22)
        self.ssh_user = str(ssh_user or settings.GITEA_SSH_USER or "git").strip() or "git"
        self.token = token if token is not None else settings.GITEA_API_TOKEN
        self.org = org if org is not None else settings.GITEA_ORG

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def _reset_user_password(self, username: str) -> str:
        password = _random_password()
        response = requests.patch(
            f"{self.base_url}/api/v1/admin/users/{username}",
            json={
                "password": password,
                "must_change_password": False,
                "login_name": username,
            },
            headers=self._headers(),
            timeout=15,
        )
        response.raise_for_status()
        return password

    def _user_basic_auth(self, username: str) -> requests.auth.HTTPBasicAuth:
        password = self._reset_user_password(username)
        return requests.auth.HTTPBasicAuth(username, password)

    def list_user_tokens(
        self,
        username: str,
        *,
        auth: requests.auth.HTTPBasicAuth | None = None,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not self.token:
            return []
        basic_auth = auth or self._user_basic_auth(username)
        response = requests.get(
            f"{self.base_url}/api/v1/users/{username}/tokens",
            auth=basic_auth,
            timeout=15,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    def delete_user_token_by_name(
        self,
        username: str,
        token_name: str,
        *,
        auth: requests.auth.HTTPBasicAuth | None = None,
    ) -> bool:
        if not self.enabled or not self.token:
            return True
        basic_auth = auth or self._user_basic_auth(username)
        for item in self.list_user_tokens(username, auth=basic_auth):
            if str(item.get("name") or "") == token_name:
                token_id = item.get("id")
                if token_id is None:
                    continue
                response = requests.delete(
                    f"{self.base_url}/api/v1/users/{username}/tokens/{token_id}",
                    auth=basic_auth,
                    timeout=15,
                )
                if response.status_code in (200, 204, 404):
                    return True
                response.raise_for_status()
        return True

    def _mock_repository(self, name: str) -> dict[str, str]:
        owner = self.org or "campus"
        return self.repository_urls(owner=owner, repo=name, branch="main")

    def repository_urls(self, *, owner: str, repo: str, branch: str = "main") -> dict[str, str]:
        return build_repository_urls(
            owner=owner,
            repo=repo,
            branch=branch,
            public_base_url=self.public_base_url,
            ssh_domain=self.ssh_domain,
            ssh_port=self.ssh_port,
            ssh_user=self.ssh_user,
        )

    def _repository_payload(self, data: dict[str, Any], fallback_name: str) -> dict[str, Any]:
        owner = (data.get("owner") or {}).get("login") or self.org or ""
        repo = data.get("name") or fallback_name
        branch = data.get("default_branch") or "main"
        return self.repository_urls(owner=owner, repo=repo, branch=branch)

    def get_repository(self, *, owner: str, repo: str) -> dict[str, Any] | None:
        repo_name = normalize_repo_slug(repo)
        if not self.enabled or not self.token:
            return self._mock_repository(repo_name)
        response = requests.get(
            f"{self.base_url}/api/v1/repos/{owner}/{repo_name}",
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json() if response.content else {}
        if not isinstance(data, dict):
            return None
        return self._repository_payload(data, repo_name)

    def create_repository(
        self,
        *,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
    ) -> dict[str, Any]:
        repo_name = normalize_repo_slug(name)
        if not self.enabled or not self.token:
            return self._mock_repository(repo_name)

        path = f"/api/v1/orgs/{self.org}/repos" if self.org else "/api/v1/user/repos"
        response = requests.post(
            f"{self.base_url}{path}",
            json={
                "name": repo_name,
                "description": description or "",
                "private": private,
                "auto_init": auto_init,
                "default_branch": "main",
            },
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code in (409, 422):
            existing = self.get_repository(owner=self.org or "campus", repo=repo_name)
            if existing:
                return existing
        response.raise_for_status()
        data = response.json()
        return self._repository_payload(data if isinstance(data, dict) else {}, repo_name)

    def get_readme(self, *, owner: str, repo: str, branch: str = "main") -> str:
        if not self.enabled or not self.token:
            return ""

        for filename in ("README.md", "readme.md", "README"):
            response = requests.get(
                f"{self.base_url}/api/v1/repos/{owner}/{repo}/contents/{filename}",
                params={"ref": branch},
                headers=self._headers(),
                timeout=15,
            )
            if response.status_code == 404:
                continue
            response.raise_for_status()
            data = response.json()
            content = data.get("content") or ""
            if data.get("encoding") == "base64" and content:
                return base64.b64decode(content).decode("utf-8", errors="replace")
            return content
        return ""

    def _normalize_repo_path(self, path: str | None) -> str:
        value = str(path or "").strip().strip("/")
        return value

    def _normalize_content_entry(self, item: dict[str, Any]) -> dict[str, Any]:
        entry_type = str(item.get("type") or "file")
        return {
            "name": str(item.get("name") or ""),
            "path": str(item.get("path") or item.get("name") or ""),
            "type": "dir" if entry_type == "dir" else "file",
            "sha": str(item.get("sha") or ""),
            "size": int(item.get("size") or 0),
        }

    def list_contents(
        self,
        *,
        owner: str,
        repo: str,
        path: str = "",
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        if not self.enabled or not self.token:
            return []
        repo_path = self._normalize_repo_path(path)
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/contents"
        if repo_path:
            url = f"{url}/{repo_path}"
        response = requests.get(
            url,
            params={"ref": branch},
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            if repo_path:
                raise FileNotFoundError(repo_path)
            raise FileNotFoundError(f"{owner}/{repo}")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return [self._normalize_content_entry(payload)]
        if isinstance(payload, list):
            entries = [self._normalize_content_entry(item) for item in payload if isinstance(item, dict)]
            entries.sort(key=lambda item: (0 if item["type"] == "dir" else 1, item["name"].lower()))
            return entries
        return []

    def get_file_content(
        self,
        *,
        owner: str,
        repo: str,
        path: str,
        branch: str = "main",
        max_bytes: int = 512_000,
    ) -> dict[str, Any]:
        repo_path = self._normalize_repo_path(path)
        if not repo_path:
            raise ValueError("file path is required")
        if not self.enabled or not self.token:
            return {
                "path": repo_path,
                "name": repo_path.rsplit("/", 1)[-1],
                "encoding": "text",
                "content": "",
                "size": 0,
                "previewable": False,
            }
        response = requests.get(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/contents/{repo_path}",
            params={"ref": branch},
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            raise FileNotFoundError(repo_path)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get("type") == "dir":
            raise ValueError("path is not a file")
        size = int(data.get("size") or 0)
        encoding = str(data.get("encoding") or "")
        raw_content = str(data.get("content") or "")
        previewable = encoding == "base64" and size <= max_bytes
        content = ""
        if previewable and raw_content:
            try:
                content = base64.b64decode(raw_content).decode("utf-8")
            except UnicodeDecodeError:
                previewable = False
                content = ""
        return {
            "path": str(data.get("path") or repo_path),
            "name": str(data.get("name") or repo_path.rsplit("/", 1)[-1]),
            "encoding": "text" if previewable else encoding or "binary",
            "content": content,
            "size": size,
            "previewable": previewable,
        }

    def get_languages(self, *, owner: str, repo: str) -> dict[str, float]:
        if not self.enabled or not self.token:
            return {}
        response = requests.get(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/languages",
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return {str(name): float(value) for name, value in payload.items()}

    def get_archive_url(self, *, owner: str, repo: str, branch: str = "main") -> str:
        return self.repository_urls(owner=owner, repo=repo, branch=branch)["archiveUrl"]

    def delete_repository(self, *, owner: str, repo: str) -> bool:
        if not self.enabled or not self.token:
            return True

        response = requests.delete(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}",
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code in (200, 202, 204, 404):
            return True
        response.raise_for_status()
        return True

    def _webhook_url(self, *, project_id: str, module: str = "team_git") -> str:
        if module == "code_repository":
            webhook_path = f"/api/code-repositories/{project_id}/webhooks/gitea"
        else:
            webhook_path = f"/api/team-git/projects/{project_id}/webhooks/gitea"
        return f"{settings.GITEA_PUBLIC_BACKEND_URL.rstrip('/')}{webhook_path}"

    def ensure_webhook(self, *, owner: str, repo: str, project_id: str, module: str = "team_git") -> dict[str, Any]:
        webhook_url = self._webhook_url(project_id=project_id, module=module)
        events = ["push", "pull_request"]
        if not self.enabled or not self.token:
            return {"configured": True, "url": webhook_url, "events": events, "mock": True}

        path = f"/api/v1/repos/{owner}/{repo}/hooks"
        try:
            list_response = requests.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
                timeout=10,
            )
            if list_response.status_code == 200:
                hooks = list_response.json()
                if isinstance(hooks, list):
                    for hook in hooks:
                        if not isinstance(hook, dict):
                            continue
                        config = hook.get("config") if isinstance(hook.get("config"), dict) else {}
                        if str(config.get("url") or "") == webhook_url:
                            return {
                                "configured": bool(hook.get("active", True)),
                                "url": webhook_url,
                                "events": hook.get("events") or events,
                                "id": hook.get("id"),
                            }
            elif list_response.status_code != 404:
                list_response.raise_for_status()

            response = requests.post(
                f"{self.base_url}{path}",
                json={
                    "type": "gitea",
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "secret": settings.GITEA_WEBHOOK_SECRET,
                    },
                    "events": events,
                    "active": True,
                },
                headers=self._headers(),
                timeout=10,
            )
            if response.status_code == 422:
                return {"configured": True, "url": webhook_url, "events": events, "alreadyExists": True}
            response.raise_for_status()
            data = response.json() if response.content else {}
            return {
                "configured": True,
                "url": webhook_url,
                "events": events,
                "id": data.get("id") if isinstance(data, dict) else None,
            }
        except Exception as exc:
            return {"configured": False, "url": webhook_url, "events": events, "error": str(exc)}

    def create_webhook(self, *, owner: str, repo: str, project_id: str, module: str = "team_git") -> bool:
        """
        向 Gitea 自动注册本项目的 Webhook 回调地址
        """
        if not self.enabled or not self.token:
            return True

        if module == "code_repository":
            webhook_path = f"/api/code-repositories/{project_id}/webhooks/gitea"
        else:
            webhook_path = f"/api/team-git/projects/{project_id}/webhooks/gitea"
        webhook_url = f"{settings.GITEA_PUBLIC_BACKEND_URL.rstrip('/')}{webhook_path}"
        path = f"/api/v1/repos/{owner}/{repo}/hooks"
        
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json={
                    "type": "gitea",
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "secret": settings.GITEA_WEBHOOK_SECRET
                    },
                    "events": ["push", "pull_request"],
                    "active": True
                },
                headers=self._headers(),
                timeout=10
            )
            # 若 Gitea Webhook 已存在，返回 422，我们允许已存在情况
            if response.status_code == 422:
                return True
            response.raise_for_status()
            return True
        except Exception:
            # Gitea API 失败 fallback
            return False

    def get_user(self, username: str) -> dict[str, Any] | None:
        if not self.enabled or not self.token:
            return None
        response = requests.get(
            f"{self.base_url}/api/v1/users/{username}",
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def create_user(
        self,
        *,
        username: str,
        email: str,
        full_name: str = "",
        password: str,
        must_change_password: bool = False,
        visibility: str = "private",
    ) -> dict[str, Any]:
        if not self.enabled or not self.token:
            return {"id": None, "login": username, "username": username, "email": email, "full_name": full_name}
        existing = self.get_user(username)
        if existing:
            return existing
        response = requests.post(
            f"{self.base_url}/api/v1/admin/users",
            json={
                "username": username,
                "email": email,
                "full_name": full_name or username,
                "password": password,
                "must_change_password": must_change_password,
                "visibility": visibility,
                "send_notify": False,
                "source_id": 0,
            },
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 422:
            existing = self.get_user(username)
            if existing:
                return existing
        response.raise_for_status()
        return response.json()

    def _resolve_org_team_id(self) -> int | None:
        response = requests.get(
            f"{self.base_url}/api/v1/orgs/{self.org}/teams",
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        teams = payload if isinstance(payload, list) else []
        preferred_names = ("members", "writers", "students", "developers")
        for preferred in preferred_names:
            for team in teams:
                if str(team.get("name") or "").lower() == preferred:
                    team_id = team.get("id")
                    if team_id is not None:
                        return int(team_id)
        for team in teams:
            if str(team.get("name") or "").lower() != "owners":
                team_id = team.get("id")
                if team_id is not None:
                    return int(team_id)
        create_response = requests.post(
            f"{self.base_url}/api/v1/orgs/{self.org}/teams",
            headers=self._headers(),
            json={
                "name": "Members",
                "description": "Campus learning system members",
                "permission": "write",
                "includes_all_repositories": True,
                "units": ["repo.code", "repo.issues", "repo.pulls", "repo.releases", "repo.wiki"],
            },
            timeout=15,
        )
        if create_response.status_code == 201:
            created = create_response.json() or {}
            team_id = created.get("id")
            return int(team_id) if team_id is not None else None
        if create_response.status_code == 422:
            for team in teams:
                if str(team.get("name") or "").lower() == "members":
                    team_id = team.get("id")
                    if team_id is not None:
                        return int(team_id)
        return None

    def ensure_org_membership(self, username: str, role: str = "member") -> bool:
        if not self.enabled or not self.token or not self.org:
            return True
        check = requests.get(
            f"{self.base_url}/api/v1/orgs/{self.org}/members/{username}",
            headers=self._headers(),
            timeout=15,
        )
        if check.status_code == 200:
            return True
        team_id = self._resolve_org_team_id()
        if team_id is None:
            return True
        response = requests.put(
            f"{self.base_url}/api/v1/teams/{team_id}/members/{username}",
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code in (204, 422):
            return True
        return True

    def add_repository_collaborator(self, *, owner: str, repo: str, username: str, permission: str = "write") -> bool:
        if not self.enabled or not self.token:
            return True
        response = requests.put(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/collaborators/{username}",
            json={"permission": permission},
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code in (204, 422):
            return True
        response.raise_for_status()
        return True

    def create_user_token(self, username: str, token_name: str = "campus-learning-system") -> str:
        if not self.enabled or not self.token:
            return f"mock-gitea-token-{username}-{token_name}"
        basic_auth = self._user_basic_auth(username)
        self.delete_user_token_by_name(username, token_name, auth=basic_auth)
        response = requests.post(
            f"{self.base_url}/api/v1/users/{username}/tokens",
            json={"name": token_name, "scopes": ["all"]},
            auth=basic_auth,
            timeout=15,
        )
        if response.status_code == 422:
            self.delete_user_token_by_name(username, token_name, auth=basic_auth)
            response = requests.post(
                f"{self.base_url}/api/v1/users/{username}/tokens",
                json={"name": token_name, "scopes": ["all"]},
                auth=basic_auth,
                timeout=15,
            )
        response.raise_for_status()
        data = response.json()
        return str(data.get("sha1") or data.get("token") or "")

    def get_commit_diff(self, *, owner: str, repo: str, sha: str) -> str:
        """
        获取 Commit Diff，如果超过 4000 个字符则进行截断
        """
        if not self.enabled or not self.token:
            return "Mock Commit Diff: code change detected."
            
        path = f"/api/v1/repos/{owner}/{repo}/commits/{sha}.diff"
        try:
            response = requests.get(
                f"{self.base_url}{path}",
                headers={"Authorization": f"token {self.token}"},
                timeout=10
            )
            if response.status_code == 404:
                return "Commit diff not found."
            response.raise_for_status()
            diff_text = response.text
            
            # 对超长 Diff 进行截断处理 (防止 AI Token 溢出)
            MAX_DIFF_LEN = 4000
            if len(diff_text) > MAX_DIFF_LEN:
                diff_text = diff_text[:MAX_DIFF_LEN] + "\n\n... [Diff over limit, truncated by system]"
            return diff_text
        except Exception as e:
            # API 失败 fallback
            return f"Error retrieving commit diff: {str(e)}"

    def ping(self) -> dict[str, Any]:
        """Connectivity check for deploy health endpoints."""
        if not self.enabled:
            return {"ok": False, "enabled": False, "message": "Gitea 未启用（GITEA_ENABLED=false）"}
        if not self.token:
            return {"ok": False, "enabled": True, "message": "缺少 GITEA_API_TOKEN"}
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/version",
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json() if response.content else {}
            return {
                "ok": True,
                "enabled": True,
                "baseUrl": self.base_url,
                "version": str((data or {}).get("version") or ""),
                "message": "Gitea 连通正常",
            }
        except RequestException as exc:
            return {"ok": False, "enabled": True, "baseUrl": self.base_url, "message": f"Gitea 连通失败：{exc}"}

    def list_pull_requests(self, *, owner: str, repo: str, state: str = "all") -> list[dict[str, Any]]:
        if not self.enabled or not self.token:
            return []
        response = requests.get(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls",
            params={"state": state},
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []
        results: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            user = item.get("user") if isinstance(item.get("user"), dict) else {}
            head = item.get("head") if isinstance(item.get("head"), dict) else {}
            base = item.get("base") if isinstance(item.get("base"), dict) else {}
            merged = bool(item.get("merged"))
            closed = str(item.get("state") or "").lower() == "closed" and not merged
            status = "merged" if merged else ("closed" if closed else "open")
            results.append(
                {
                    "number": int(item.get("number") or 0),
                    "title": str(item.get("title") or f"Pull Request #{item.get('number') or ''}"),
                    "state": str(item.get("state") or status),
                    "status": status,
                    "merged": merged,
                    "creator": str(user.get("login") or user.get("username") or ""),
                    "sourceBranch": str(head.get("ref") or ""),
                    "targetBranch": str(base.get("ref") or ""),
                    "url": str(item.get("html_url") or item.get("url") or ""),
                    "body": str(item.get("body") or ""),
                    "updatedAt": str(item.get("updated_at") or item.get("created_at") or ""),
                    "createdAt": str(item.get("created_at") or ""),
                }
            )
        return results

    def list_branches(self, *, owner: str, repo: str) -> list[dict[str, Any]]:
        if not self.enabled or not self.token:
            return []
        response = requests.get(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/branches",
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []
        branches: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            commit = item.get("commit") if isinstance(item.get("commit"), dict) else {}
            branches.append(
                {
                    "name": name,
                    "commitSha": str(commit.get("id") or commit.get("sha") or ""),
                    "protected": bool(item.get("protected")),
                }
            )
        return branches

    def merge_pull_request(
        self,
        *,
        owner: str,
        repo: str,
        index: int,
        merge_message: str = "",
        merge_style: str = "merge",
    ) -> dict[str, Any]:
        if not self.enabled or not self.token:
            raise RuntimeError("Gitea 未启用或缺少 API Token，无法合并 Pull Request")
        response = requests.post(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{int(index)}/merge",
            json={
                "Do": merge_style,
                "MergeMessageField": merge_message or f"Merge pull request #{index}",
                "delete_branch_after_merge": False,
            },
            headers=self._headers(),
            timeout=20,
        )
        if response.status_code == 405:
            # Already merged / not mergeable — inspect current PR
            current = self.list_pull_requests(owner=owner, repo=repo, state="all")
            pr = next((item for item in current if int(item.get("number") or 0) == int(index)), None)
            if pr and pr.get("merged"):
                return {"merged": True, "alreadyMerged": True, "number": int(index)}
            raise RuntimeError(f"Gitea PR #{index} 无法合并：{response.text[:300]}")
        if response.status_code == 404:
            raise FileNotFoundError(f"Gitea PR #{index} 不存在")
        response.raise_for_status()
        data = response.json() if response.content else {}
        return {"merged": True, "alreadyMerged": False, "number": int(index), "raw": data if isinstance(data, dict) else {}}

    def list_commits(
        self,
        *,
        owner: str,
        repo: str,
        sha: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not self.token:
            return []
        params: dict[str, Any] = {"limit": max(1, min(int(limit or 30), 50))}
        if sha:
            params["sha"] = sha
        response = requests.get(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/commits",
            params=params,
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []
        results: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            commit = item.get("commit") if isinstance(item.get("commit"), dict) else {}
            author_obj = commit.get("author") if isinstance(commit.get("author"), dict) else {}
            committer_obj = commit.get("committer") if isinstance(commit.get("committer"), dict) else {}
            user = item.get("author") if isinstance(item.get("author"), dict) else {}
            results.append(
                {
                    "sha": str(item.get("sha") or item.get("id") or ""),
                    "message": str(commit.get("message") or item.get("message") or "").strip().split("\n")[0],
                    "authorName": str(author_obj.get("name") or user.get("login") or user.get("username") or ""),
                    "authorEmail": str(author_obj.get("email") or ""),
                    "authorLogin": str(user.get("login") or user.get("username") or ""),
                    "committerName": str(committer_obj.get("name") or ""),
                    "time": str(author_obj.get("date") or committer_obj.get("date") or item.get("created") or ""),
                    "url": str(item.get("html_url") or item.get("url") or ""),
                }
            )
        return results

    def list_issues(self, *, owner: str, repo: str, state: str = "open") -> list[dict[str, Any]]:
        if not self.enabled or not self.token:
            return []
        response = requests.get(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/issues",
            params={"state": state, "type": "issues"},
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []
        results: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            # Gitea may still return PRs in issues endpoint; skip pull requests
            if item.get("pull_request"):
                continue
            assignees = item.get("assignees") if isinstance(item.get("assignees"), list) else []
            assignee_logins = [
                str(a.get("login") or a.get("username") or "")
                for a in assignees
                if isinstance(a, dict)
            ]
            primary = item.get("assignee") if isinstance(item.get("assignee"), dict) else {}
            if primary.get("login") or primary.get("username"):
                login = str(primary.get("login") or primary.get("username"))
                if login and login not in assignee_logins:
                    assignee_logins.insert(0, login)
            results.append(
                {
                    "number": int(item.get("number") or 0),
                    "title": str(item.get("title") or ""),
                    "body": str(item.get("body") or ""),
                    "state": str(item.get("state") or "open"),
                    "assignees": [login for login in assignee_logins if login],
                    "url": str(item.get("html_url") or item.get("url") or ""),
                    "updatedAt": str(item.get("updated_at") or ""),
                }
            )
        return results

    def create_issue(
        self,
        *,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled or not self.token:
            raise RuntimeError("Gitea 未启用或缺少 API Token，无法创建 Issue")
        payload: dict[str, Any] = {"title": title, "body": body or ""}
        cleaned = [str(name).strip() for name in (assignees or []) if str(name or "").strip()]
        if cleaned:
            payload["assignees"] = cleaned
        response = requests.post(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/issues",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
        if not isinstance(data, dict):
            raise RuntimeError("Gitea 创建 Issue 返回异常")
        return {
            "number": int(data.get("number") or 0),
            "title": str(data.get("title") or title),
            "body": str(data.get("body") or body or ""),
            "url": str(data.get("html_url") or data.get("url") or ""),
            "state": str(data.get("state") or "open"),
        }

    def edit_issue(
        self,
        *,
        owner: str,
        repo: str,
        index: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled or not self.token:
            raise RuntimeError("Gitea 未启用或缺少 API Token，无法更新 Issue")
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if assignees is not None:
            payload["assignees"] = [str(name).strip() for name in assignees if str(name or "").strip()]
        response = requests.patch(
            f"{self.base_url}/api/v1/repos/{owner}/{repo}/issues/{int(index)}",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        if response.status_code == 404:
            raise FileNotFoundError(f"Gitea Issue #{index} 不存在")
        response.raise_for_status()
        data = response.json() if response.content else {}
        return data if isinstance(data, dict) else {"number": int(index)}
