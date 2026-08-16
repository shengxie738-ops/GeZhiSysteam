"""
git_workflow_rules.py — 纯函数 Git 工作流规则校验器
不访问网络，便于单测。

规则码（见指导书 4.3）：
    PUSH_TO_DEFAULT_BRANCH     push 到 main/master（非 merge 场景）  error
    BRANCH_NAME_INVALID        分支名不包含 feature/feat/fix/docs/test/hotfix  warn
    COMMIT_MESSAGE_TOO_SHORT   message 去空白 < 8 字符  warn
    COMMIT_MESSAGE_EMPTY       message 为空  error
    AUTHOR_UNMATCHED           作者未绑定 / unmatched  warn
    PR_BASE_NOT_DEFAULT        PR base 不是 defaultBranch  warn
    PR_HEAD_NAME_INVALID       PR head 分支命名不合规  warn
    MEMBER_NOT_IN_TEAM         作者不在 memberProgress（新建了匿名成员）  warn
"""

from __future__ import annotations

import re
from typing import Any

# 合规分支前缀
_VALID_BRANCH_PREFIXES = ("feature", "feat", "fix", "docs", "test", "hotfix")
# 默认分支名集合
_DEFAULT_BRANCHES = {"main", "master"}

# 严重等级对应扣分
_DEDUCT = {"error": 20, "warn": 10}


def _branch_name_valid(branch: str) -> bool:
    """检查分支名是否以合规前缀开头（不区分大小写）。"""
    b = branch.strip().lower()
    return any(b == p or b.startswith(f"{p}/") or b.startswith(f"{p}-") for p in _VALID_BRANCH_PREFIXES)


def _commit_message_check(message: str) -> str | None:
    """返回违规码或 None（无违规）。"""
    stripped = (message or "").strip()
    if not stripped:
        return "COMMIT_MESSAGE_EMPTY"
    if len(stripped) < 8:
        return "COMMIT_MESSAGE_TOO_SHORT"
    return None


def _is_merge_commit(message: str) -> bool:
    """Merge commit 通常不算「直接 push main」违规。"""
    return bool(re.match(r"^(merge|Merge)\b", (message or "").strip()))


def _member_in_team(author: str, project: dict[str, Any]) -> bool:
    """检查 author 是否在 memberProgress 已有成员中（含 id/name 比对）。"""
    members = project.get("memberProgress") or []
    for m in members:
        name = str(m.get("name") or "").strip()
        mid = str(m.get("id") or "").strip()
        if author and author.strip() in (name, mid):
            return True
    return False


def evaluate_git_workflow(
    *,
    event_type: str,
    payload: dict[str, Any],
    project: dict[str, Any],
    matched_member: dict[str, Any] | None = None,
    author_match_source: str = "",
) -> dict[str, Any]:
    """返回 workflowRuleResult（见指导书 4.1）。

    Parameters
    ----------
    event_type:
        "push" 或 "pull_request"
    payload:
        Gitea Webhook payload dict
    project:
        DomainRecord payload（含 repository / memberProgress 等字段）
    matched_member:
        match_campus_user_from_gitea_event 返回值（可选）；
        None 时默认 source=unmatched
    author_match_source:
        "matched" / "unmatched" / "" 三种值
    """
    from app.utils.datetime import format_chinese_datetime

    passed: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    repo = project.get("repository") or {}
    default_branch = str(repo.get("defaultBranch") or "main")

    def _add_violation(code: str, severity: str, message: str, hint: str, evidence: dict | None = None):
        violations.append({
            "code": code,
            "severity": severity,
            "message": message,
            "hint": hint,
            "evidence": evidence or {},
        })

    def _add_passed(code: str, message: str):
        passed.append({"code": code, "message": message})

    # ── push 事件校验 ────────────────────────────────────────────
    if event_type == "push":
        ref = str(payload.get("ref") or "")
        branch = ref.replace("refs/heads/", "").strip() if ref.startswith("refs/heads/") else ref.split("/")[-1]
        commits = payload.get("commits") or []

        # 规则: PUSH_TO_DEFAULT_BRANCH
        if branch.lower() in _DEFAULT_BRANCHES:
            # 检查是否全是 merge commit
            all_merge = commits and all(_is_merge_commit(c.get("message") or "") for c in commits if isinstance(c, dict))
            if not all_merge:
                _add_violation(
                    "PUSH_TO_DEFAULT_BRANCH",
                    "error",
                    f"直接向 {branch} 分支推送代码（非 Merge commit），违反协作规范",
                    f"请先创建 feature/xxx 等功能分支，完成后通过 Pull Request 合并到 {default_branch}",
                    {"branch": branch},
                )
            else:
                _add_passed("PUSH_TO_DEFAULT_BRANCH", f"Merge commit 推送到 {branch}，符合规范")
        else:
            # 规则: BRANCH_NAME_INVALID
            if _branch_name_valid(branch):
                _add_passed("BRANCH_NAME_INVALID", f"分支名 {branch} 符合 feature/fix/docs/test 约定")
            else:
                _add_violation(
                    "BRANCH_NAME_INVALID",
                    "warn",
                    f"分支名 {branch!r} 不符合 feature/feat/fix/docs/test/hotfix 约定",
                    "请使用 feature/xxx 或 fix/xxx 命名后再推送",
                    {"branch": branch},
                )

        # 规则: commit message 相关
        for commit in commits:
            if not isinstance(commit, dict):
                continue
            msg = str(commit.get("message") or "").strip()
            sha_short = str(commit.get("id") or "")[:8]
            code = _commit_message_check(msg)
            if code == "COMMIT_MESSAGE_EMPTY":
                _add_violation(
                    "COMMIT_MESSAGE_EMPTY",
                    "error",
                    f"commit {sha_short} 提交说明为空",
                    "每次提交必须有清晰的说明，例如 'fix: 修复哈夫曼树边界条件'",
                    {"sha": sha_short, "message": msg},
                )
            elif code == "COMMIT_MESSAGE_TOO_SHORT":
                _add_violation(
                    "COMMIT_MESSAGE_TOO_SHORT",
                    "warn",
                    f"commit {sha_short} 提交说明过短（{len(msg)} 字符），看不出改动目的",
                    "提交说明至少 8 个字符，用动词开头描述本次改动",
                    {"sha": sha_short, "message": msg, "length": len(msg)},
                )
            else:
                _add_passed("COMMIT_HAS_MESSAGE", f"commit {sha_short} 提交说明非空且足够清晰")

        # 规则: AUTHOR_UNMATCHED
        source = author_match_source or (
            str((matched_member or {}).get("source") or "") if matched_member else "unmatched"
        )
        if source in ("unmatched", "") and not matched_member:
            _add_violation(
                "AUTHOR_UNMATCHED",
                "warn",
                "提交作者未能匹配到校园用户，可能未绑定 Gitea 账号",
                "请在「个人设置 → Gitea 账号绑定」完成账号关联",
                {"source": source},
            )
        else:
            _add_passed("AUTHOR_UNMATCHED", "提交作者已成功匹配到校园用户")

        # 规则: MEMBER_NOT_IN_TEAM
        author_name = str((matched_member or {}).get("displayName") or "")
        if author_name and not _member_in_team(author_name, project):
            _add_violation(
                "MEMBER_NOT_IN_TEAM",
                "warn",
                f"作者 {author_name!r} 不在团队成员列表，已自动创建匿名成员",
                "请确认提交者已加入该团队项目，或由队长在团队页面手动添加成员",
                {"author": author_name},
            )

    # ── pull_request 事件校验 ─────────────────────────────────────
    elif event_type == "pull_request":
        pr = payload.get("pull_request") or {}
        head_branch = str((pr.get("head") or {}).get("label") or pr.get("head_branch") or "")
        base_branch = str((pr.get("base") or {}).get("label") or pr.get("base_branch") or "")

        # 规则: PR_BASE_NOT_DEFAULT
        base_name = base_branch.split(":")[-1] if ":" in base_branch else base_branch
        if base_name and base_name != default_branch:
            _add_violation(
                "PR_BASE_NOT_DEFAULT",
                "warn",
                f"PR 目标分支是 {base_name!r}，应合并到 {default_branch}",
                f"创建 PR 时请将 base 分支选为 {default_branch}",
                {"base": base_name, "defaultBranch": default_branch},
            )
        elif base_name:
            _add_passed("PR_BASE_NOT_DEFAULT", f"PR base 分支正确指向 {default_branch}")

        # 规则: PR_HEAD_NAME_INVALID
        head_name = head_branch.split(":")[-1] if ":" in head_branch else head_branch
        if head_name and not _branch_name_valid(head_name):
            _add_violation(
                "PR_HEAD_NAME_INVALID",
                "warn",
                f"PR 来源分支 {head_name!r} 命名不规范",
                "来源分支应使用 feature/xxx、fix/xxx 等命名",
                {"head": head_name},
            )
        elif head_name:
            _add_passed("PR_HEAD_NAME_INVALID", f"PR head 分支 {head_name!r} 命名规范")

    # ── 计算得分 ──────────────────────────────────────────────────
    deduct = sum(_DEDUCT.get(v["severity"], 0) for v in violations)
    score = max(0, 100 - deduct)

    return {
        "eventType": event_type,
        "evaluatedAt": format_chinese_datetime(),
        "score": score,
        "passed": passed,
        "violations": violations,
    }
