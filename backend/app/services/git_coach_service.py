"""
git_coach_service.py — AI Git 教练服务（团队协作实训）

职责：
1. build_coach_prompt  — 构建系统/用户提示词，要求 LLM 输出 JSON
2. parse_coach_json    — 从 LLM 输出中提取 JSON
3. render_fallback_feedback — 无 LLM 时用规则 violations 生成 fallback 反馈
4. generate_commit_coach_feedback — 主入口：取 diff、调 LLM、写回数据库

对外接口：
    generate_commit_coach_feedback(db, project_id, *, payload, gitea=None) -> dict
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.git_workflow_rules import evaluate_git_workflow
from app.services.gitea_service import GiteaService
from app.services.model_registry import build_chat_model

logger = logging.getLogger(__name__)

# ── Prompt 构建 ────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
你是一所高校「Git 协作实训」课程的 AI 教练。
你的任务是对学生的 Git 操作进行规范性点评，帮助学生掌握团队协作中的 Git 最佳实践。

【评价原则】
1. 只评价 Git 流程与提交规范（分支命名、commit message、PR 流程等），不评价业务代码的算法正确性。
2. 必须明确指出学生做错的点（对应规则 violations）。
3. 给出可执行的修改步骤（如：切分支、改 commit message、开 PR 到 main 等）。
4. 语言亲切、鼓励为主，同时清晰指出问题。
5. 面向本科生，用中文表达，术语可用英文但要加解释。

【输出格式】
必须输出严格 JSON，不要 Markdown 围栏（```）外的任何废话，格式如下：
{
  "summary": "一句话总评（30字以内）",
  "mistakes": ["具体错误1", "具体错误2"],
  "suggestions": ["可执行建议1", "可执行建议2"]
}
"""


def build_coach_prompt(
    *,
    rules: dict[str, Any],
    commit_meta: dict[str, Any],
    diff_text: str,
    project: dict[str, Any],
) -> tuple[str, str]:
    """返回 (system_prompt, user_prompt)。"""
    violations = rules.get("violations") or []
    score = rules.get("score", 100)
    branch = commit_meta.get("branch") or "未知分支"
    sha_short = str(commit_meta.get("sha") or "")[:8]
    author = commit_meta.get("author") or "未知作者"
    message = commit_meta.get("message") or ""
    project_title = (project.get("project") or {}).get("title") or project.get("id") or "未命名项目"

    violation_text = ""
    if violations:
        violation_text = "\n".join(
            f"- [{v['severity'].upper()}] {v['code']}: {v['message']}" for v in violations
        )
    else:
        violation_text = "（无规则违规）"

    # diff 截断到 3500 字符，保留最后的省略提示
    diff_display = diff_text
    if len(diff_display) > 3500:
        diff_display = diff_display[:3500] + "\n\n... [Diff 过长，已截断]"

    user_prompt = f"""【项目】{project_title}
【作者】{author}
【分支】{branch}
【Commit】{sha_short} — {message}
【规则评分】{score}/100

【规则诊断】
{violation_text}

【代码变更（Diff）】
{diff_display}

请根据以上信息，用中文对该学生的 Git 操作进行点评，指出错误和改进建议。
严格输出 JSON，不要其他文字。"""

    return _SYSTEM_PROMPT, user_prompt


# ── JSON 解析 ──────────────────────────────────────────────────────

def parse_coach_json(text: str) -> dict[str, Any]:
    """从 LLM 输出提取 JSON；失败则 raise ValueError。"""
    if not text:
        raise ValueError("LLM 返回空响应")
    # 尝试直接解析
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict) and "summary" in data:
            return data
    except json.JSONDecodeError:
        pass
    # 从 Markdown 围栏提取
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and "summary" in data:
                return data
        except json.JSONDecodeError:
            pass
    # 从文本中提取第一个完整 JSON 对象
    match2 = re.search(r"\{[^{}]*\"summary\"[^{}]*\}", text, re.DOTALL)
    if match2:
        try:
            data = json.loads(match2.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    raise ValueError(f"无法从 LLM 输出中解析 JSON: {text[:200]!r}")


# ── Fallback 反馈 ──────────────────────────────────────────────────

def render_fallback_feedback(rules: dict[str, Any], *, reason: str = "") -> dict[str, Any]:
    """无 LLM 时，用 violations 生成 mistakes/suggestions/summary。status=fallback。"""
    violations = rules.get("violations") or []
    score = rules.get("score", 100)
    mistakes: list[str] = []
    suggestions: list[str] = []
    for v in violations:
        mistakes.append(v.get("message") or v.get("code") or "未知错误")
        if v.get("hint"):
            suggestions.append(v["hint"])

    if not mistakes:
        summary = f"规则检查通过（得分 {score}/100），AI 教练暂时离线。"
    else:
        summary = f"发现 {len(violations)} 个规范问题（得分 {score}/100），请参阅下方建议。"

    return {
        "status": "fallback",
        "summary": summary,
        "mistakes": mistakes or ["暂无具体问题（AI 教练离线）"],
        "suggestions": suggestions or ["请保持良好的 Git 使用习惯"],
        "fallbackReason": reason or "AI 教练暂时不可用，显示规则诊断",
    }


# ── 主入口 ─────────────────────────────────────────────────────────

def generate_commit_coach_feedback(
    db: Session,
    project_id: str,
    *,
    payload: dict[str, Any],
    gitea: GiteaService | None = None,
) -> dict[str, Any]:
    """
    主入口：对 payload 中的 commits 逐条生成 AI Git 教练反馈，写回数据库。

    PR 事件（无 commits）也会生成一条 sha="" 的反馈条目。
    LLM 失败时自动 fallback（status=fallback），不抛出异常。

    返回更新后的 aiGitCoachFeedback 列表。
    """
    # 延迟导入，避免循环依赖
    from app.services.team_git_service import (
        MODULE, PROJECT, _load_project, _save_project,
        _upsert_coach_feedback, _branch_from_ref,
        _commit_sha, _commit_message,
    )
    from app.services.gitea_account_service import match_campus_user_from_gitea_event
    from app.core.config import settings
    from langchain_core.messages import SystemMessage, HumanMessage

    try:
        project = _load_project(db, project_id)
    except Exception as exc:
        logger.error("git_coach: 加载项目失败 project_id=%s: %s", project_id, exc)
        return {}

    gitea_svc = gitea or GiteaService()
    repo = project.get("repository") or {}
    owner = str(repo.get("giteaOwner") or "campus")
    repo_name = str(repo.get("repoName") or repo.get("giteaRepo") or project_id)
    event_type = str(payload.get("hook_name") or payload.get("type") or ("pull_request" if "pull_request" in payload else "push"))
    ref = str(payload.get("ref") or "")
    branch = _branch_from_ref(ref)
    sender = str(payload.get("pusher", {}).get("name") or payload.get("sender", {}).get("login") or "unknown")
    commits = payload.get("commits") if isinstance(payload.get("commits"), list) else []

    # LLM 实例（复用；失败时置 None）
    try:
        llm = build_chat_model(settings.LLM_MODEL_DEFAULT, temperature=0.2)
    except Exception as exc:
        logger.warning("git_coach: 构建 LLM 失败: %s", exc)
        llm = None

    processed_shas: set[str] = set()

    def _process_commit(commit: dict[str, Any]) -> None:
        sha = _commit_sha(commit)
        if sha and sha in processed_shas:
            return  # 去重
        if sha:
            processed_shas.add(sha)

        # 1. 匹配作者
        match = match_campus_user_from_gitea_event(
            db,
            sender_username=sender,
            commit_author=commit.get("author") if isinstance(commit.get("author"), dict) else {},
        )
        author = match.get("displayName") or sender
        source = match.get("source") or "unmatched"

        # 2. 规则校验
        rules = evaluate_git_workflow(
            event_type=event_type,
            payload=payload,
            project=project,
            matched_member=match,
            author_match_source=source,
        )

        # 3. 获取 diff
        diff_text = ""
        if sha:
            try:
                diff_text = gitea_svc.get_commit_diff(owner=owner, repo=repo_name, sha=sha)
            except Exception as exc:
                logger.warning("git_coach: 取 diff 失败 sha=%s: %s", sha, exc)
                diff_text = ""

        # 4. 构建 prompt
        commit_meta = {
            "sha": sha,
            "branch": branch,
            "author": author,
            "message": _commit_message(commit),
        }
        system_p, user_p = build_coach_prompt(
            rules=rules,
            commit_meta=commit_meta,
            diff_text=diff_text,
            project=project,
        )

        # 5. 调用 LLM
        feedback_data: dict[str, Any]
        if llm is None:
            feedback_data = render_fallback_feedback(rules, reason="LLM 初始化失败")
        else:
            try:
                resp = llm.invoke([SystemMessage(content=system_p), HumanMessage(content=user_p)])
                text = getattr(resp, "content", None) or str(resp)
                parsed = parse_coach_json(text)
                feedback_data = {
                    "status": "ready",
                    "summary": str(parsed.get("summary") or ""),
                    "mistakes": list(parsed.get("mistakes") or []),
                    "suggestions": list(parsed.get("suggestions") or []),
                    "model": settings.LLM_MODEL_DEFAULT,
                }
            except Exception as exc:
                logger.warning("git_coach: LLM 调用/解析失败 sha=%s: %s", sha, exc)
                feedback_data = render_fallback_feedback(rules, reason=str(exc))

        # 6. 组装条目
        rule_violations = [
            {"code": v["code"], "message": v["message"]}
            for v in (rules.get("violations") or [])
        ]
        entry: dict[str, Any] = {
            "id": f"coach-{sha[:12]}" if sha else f"coach-pr-{uuid.uuid4().hex[:8]}",
            "sha": sha,
            "author": author,
            "branch": branch,
            "eventType": event_type,
            "ruleViolations": rule_violations,
            "ruleScore": rules.get("score", 100),
            "createdAt": _now_label(),
            "updatedAt": _now_label(),
        }
        entry.update(feedback_data)

        _upsert_coach_feedback(project, entry)

    # 处理 commits
    if commits:
        for commit in commits:
            if isinstance(commit, dict):
                _process_commit(commit)
    else:
        # PR 事件或无 commits：生成基于规则的一条反馈
        pr = payload.get("pull_request") or {}
        pr_number = pr.get("number") or "?"
        pr_branch = str((pr.get("head") or {}).get("label") or pr.get("head_branch") or branch)

        rules = evaluate_git_workflow(
            event_type=event_type,
            payload=payload,
            project=project,
        )
        feedback_data = render_fallback_feedback(rules, reason="PR 事件，无具体 commit diff")
        feedback_data["status"] = "fallback" if rules.get("violations") else "ready"
        if not rules.get("violations"):
            feedback_data["summary"] = f"PR #{pr_number} 规则检查通过（{rules.get('score', 100)}/100）"
            feedback_data["mistakes"] = []
            feedback_data["suggestions"] = ["继续保持良好的 PR 流程 🎉"]

        entry = {
            "id": f"coach-pr-{pr_number}",
            "sha": "",
            "author": sender,
            "branch": pr_branch,
            "eventType": event_type,
            "ruleViolations": [
                {"code": v["code"], "message": v["message"]} for v in (rules.get("violations") or [])
            ],
            "ruleScore": rules.get("score", 100),
            "createdAt": _now_label(),
            "updatedAt": _now_label(),
        }
        entry.update(feedback_data)
        _upsert_coach_feedback(project, entry)

    # 7. 保存
    try:
        _save_project(db, project)
    except Exception as exc:
        logger.error("git_coach: 保存项目失败 project_id=%s: %s", project_id, exc)

    return {"aiGitCoachFeedback": project.get("aiGitCoachFeedback") or []}


def _now_label() -> str:
    from app.utils.datetime import format_chinese_datetime
    return format_chinese_datetime()
