#!/usr/bin/env python
"""
将 7 个团队仓库注入 Gitea 和数据库：
1. 在 Gitea 创建仓库
2. 用 git 推送本地代码
3. 为学生创建 Gitea 账号
4. 随机组队并写入 team_collaboration_git 记录
5. 添加学生协作者到仓库
"""

from __future__ import annotations

import os
import sys
import subprocess
import random
import json
import re
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import requests
from app.core.database import SessionLocal
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore
from app.services.gitea_service import GiteaService, normalize_repo_slug
from app.services.gitea_account_service import (
    ensure_gitea_account_for_user,
    ensure_repository_collaborators,
    RepoPermission,
)
from app.utils.datetime import format_chinese_datetime

# ── 配置 ──────────────────────────────────────────────
GITEA_BASE_URL = "http://127.0.0.1:3000"
GITEA_TOKEN = "5ec8ff0a1e13d677b8cca4ca02c20c111f900008"
GITEA_ORG = "campus"
REPO_DATA_ROOT = Path(r"D:\软件杯代码仓库数据\团队仓库")
CHINA_TZ = timezone(timedelta(hours=8))
MODULE = "team_collaboration_git"
PROJECT = "project"
random.seed(20260709)

# ── 7 个仓库配置 ──────────────────────────────────────
REPOS = [
    {
        "folder": "仓库11",
        "name": "smart-health-guardian",
        "title": "智慧健康守护系统",
        "course": "软件工程综合实训",
        "team_name": "健康码农小队",
        "description": "面向校园健康管理场景，实现运动记录追踪、睡眠质量分析和健康风险预警，提供可视化健康报告和个性化建议。",
    },
    {
        "folder": "仓库12",
        "name": "ai-learning-companion",
        "title": "AI学习陪伴系统",
        "course": "人工智能技术基础",
        "team_name": "智学工坊",
        "description": "基于RAG的智能学习助手，支持错题本管理、学习计划生成和个性化答疑，帮助学生高效复盘知识点。",
    },
    {
        "folder": "仓库13",
        "name": "student-score-warning-system",
        "title": "学生成绩预警系统",
        "course": "数据库系统原理课程设计",
        "team_name": "学情雷达站",
        "description": "面向教师端的成绩监控与预警平台，自动分析作业和考试成绩趋势，识别学业困难学生并生成干预建议。",
    },
    {
        "folder": "仓库14",
        "name": "campus-secondhand-market",
        "title": "校园二手交易市场",
        "course": "Web应用开发实训",
        "team_name": "闲置流转局",
        "description": "校园闲置物品交易平台，支持商品发布、搜索、下单和订单管理，保障校内交易安全便捷。",
    },
    {
        "folder": "仓库15",
        "name": "student-learning-behavior-analysis",
        "title": "学生学习行为分析系统",
        "course": "数据分析与可视化",
        "team_name": "行为解码者",
        "description": "采集学生学习行为数据，构建学习画像，识别风险学生并生成个性化干预报告，辅助教师精准施教。",
    },
    {
        "folder": "仓库16",
        "name": "smart-lab-reservation-system",
        "title": "智慧实验室预约系统",
        "course": "软件工程综合实训",
        "team_name": "实验室管家",
        "description": "面向高校实验室的预约管理系统，支持设备管理、冲突检测、审批流程和报修工单，提升实验室使用效率。",
    },
    {
        "folder": "仓库17",
        "name": "campus-activity-volunteer-system",
        "title": "校园活动志愿者管理系统",
        "course": "Web应用开发实训",
        "team_name": "志愿星火",
        "description": "校园志愿活动管理平台，涵盖活动发布、报名签到、志愿时长统计和电子证书生成，打通志愿服务全流程。",
    },
]

# ── 任务模板 ──────────────────────────────────────────
TASK_TEMPLATES = [
    # leader
    [
        "项目架构设计、接口契约定义和 README 编写，负责团队协调和 PR 审核",
        "整体架构搭建、数据库 ER 图设计和技术选型，统筹团队开发进度",
        "系统架构设计、接口文档输出和团队任务拆分，把控代码质量",
    ],
    # backend
    [
        "后端 API 开发、数据模型设计和接口联调",
        "后端核心业务逻辑实现、数据库交互和单元测试编写",
        "后端服务层开发、异常处理和接口性能优化",
    ],
    # frontend
    [
        "前端页面开发、交互逻辑实现和状态管理",
        "前端组件封装、页面路由和数据可视化展示",
        "前端 UI 实现、表单校验和响应式适配",
    ],
    # test / docs
    [
        "测试用例编写、CI 配置和演示文档整理",
        "数据库脚本编写、测试数据准备和部署文档",
        "集成测试、接口文档完善和演示脚本准备",
    ],
    # extra
    [
        "数据采集模块开发和数据清洗脚本",
        "安全模块开发和权限控制实现",
        "性能优化、代码审查和文档校对",
    ],
]


# ── 工具函数 ──────────────────────────────────────────
def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"token {GITEA_TOKEN}",
    }


def _ts(days_ago: int, hour: int, minute: int = 0) -> str:
    now = datetime.now(CHINA_TZ)
    return (now - timedelta(days=days_ago)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    ).isoformat()


def _now_label() -> str:
    return format_chinese_datetime()


def _slug(value: str) -> str:
    return normalize_repo_slug(value)


# ── Step 1: 创建 Gitea 仓库 ───────────────────────────
def create_gitea_repo(repo_info: dict) -> dict:
    name = repo_info["name"]
    desc = repo_info["description"]
    print(f"  [Gitea] 创建仓库 {name} ...")

    # 检查是否已存在
    r = requests.get(
        f"{GITEA_BASE_URL}/api/v1/repos/{GITEA_ORG}/{name}",
        headers=_headers(),
        timeout=15,
    )
    if r.status_code == 200:
        print(f"  [Gitea] 仓库 {name} 已存在，跳过创建")
        data = r.json()
        return {
            "giteaOwner": GITEA_ORG,
            "giteaRepo": name,
            "htmlUrl": data.get("html_url", f"{GITEA_BASE_URL}/{GITEA_ORG}/{name}"),
            "cloneUrl": data.get("clone_url", f"{GITEA_BASE_URL}/{GITEA_ORG}/{name}.git"),
            "sshUrl": data.get("ssh_url", ""),
            "defaultBranch": data.get("default_branch", "main"),
        }

    # 创建仓库 (auto_init=False 避免初始 commit 冲突)
    r = requests.post(
        f"{GITEA_BASE_URL}/api/v1/orgs/{GITEA_ORG}/repos",
        json={
            "name": name,
            "description": desc,
            "private": False,
            "auto_init": False,
            "default_branch": "main",
        },
        headers=_headers(),
        timeout=15,
    )
    if r.status_code not in (201, 409):
        r.raise_for_status()
    data = r.json()
    print(f"  [Gitea] 仓库 {name} 创建成功 (id={data.get('id')})")
    return {
        "giteaOwner": GITEA_ORG,
        "giteaRepo": name,
        "htmlUrl": data.get("html_url", f"{GITEA_BASE_URL}/{GITEA_ORG}/{name}"),
        "cloneUrl": data.get("clone_url", f"{GITEA_BASE_URL}/{GITEA_ORG}/{name}.git"),
        "sshUrl": data.get("ssh_url", ""),
        "defaultBranch": "main",
    }


# ── Step 2: 用 git 推送代码 ──────────────────────────
def push_code_to_gitea(repo_info: dict) -> bool:
    name = repo_info["name"]
    folder = repo_info["folder"]
    local_path = REPO_DATA_ROOT / folder / name
    print(f"  [Git] 推送 {folder}/{name} → Gitea ...")

    if not local_path.exists():
        print(f"  [Git] 警告: 本地目录不存在 {local_path}")
        return False

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + list(args),
            cwd=str(local_path),
            capture_output=True,
            text=True,
            env=env,
        )

    # 清理 .git / __pycache__ / .pytest_cache
    git_dir = local_path / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir, ignore_errors=True)

    for pattern in ("__pycache__", ".pytest_cache", "*.pyc"):
        for p in local_path.rglob(pattern):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.is_file():
                p.unlink(missing_ok=True)

    # 确保 .gitignore 存在且包含常见忽略项
    gitignore = local_path / ".gitignore"
    ignore_lines = {"__pycache__/", "*.pyc", ".pytest_cache/", "*.db", ".env"}
    existing = set()
    if gitignore.exists():
        existing = set(gitignore.read_text(encoding="utf-8").splitlines())
    missing = ignore_lines - existing
    if missing:
        with open(gitignore, "a", encoding="utf-8") as f:
            if existing and list(existing)[-1] != "":
                f.write("\n")
            f.write("\n".join(sorted(missing)) + "\n")

    # git init → add → commit → push
    result = git("init", "-b", "main")
    if result.returncode != 0:
        # 旧版 git 不支持 -b
        git("init")
        git("checkout", "-b", "main")

    git("config", "user.name", "campus-admin")
    git("config", "user.email", "admin@gezhi.local")

    add_result = git("add", "-A")
    if add_result.returncode != 0:
        print(f"  [Git] git add 失败: {add_result.stderr}")
        return False

    commit_result = git("commit", "-m", f"feat: 初始化 {repo_info['title']} 项目")
    if commit_result.returncode != 0:
        print(f"  [Git] git commit 失败: {commit_result.stderr}")
        return False

    remote_url = f"{GITEA_BASE_URL.replace('http://', 'http://')}/{GITEA_ORG}/{name}.git"
    # 使用 token 认证
    auth_url = remote_url.replace(
        "http://", f"http://{GITEA_TOKEN}@"
    )

    git("remote", "remove", "origin")
    git("remote", "add", "origin", auth_url)

    push_result = git("push", "-u", "origin", "main", "--force")
    if push_result.returncode != 0:
        print(f"  [Git] git push 失败: {push_result.stderr[:300]}")
        return False

    print(f"  [Git] {name} 推送成功")
    return True


# ── Step 3: 创建 webhook ─────────────────────────────
def create_webhook(repo_name: str) -> bool:
    webhook_url = f"http://host.docker.internal:8516/api/team-git/projects/{repo_name}/webhooks/gitea"
    try:
        r = requests.post(
            f"{GITEA_BASE_URL}/api/v1/repos/{GITEA_ORG}/{repo_name}/hooks",
            json={
                "type": "gitea",
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": "a330253add23cd58a62744db6a9755439c05b356a9c774f03bf7787a47bffd12",
                },
                "events": ["push", "pull_request"],
                "active": True,
            },
            headers=_headers(),
            timeout=10,
        )
        if r.status_code in (201, 422):
            return True
        return False
    except Exception:
        return False


# ── Step 4: 获取学生并创建 Gitea 账号 ─────────────────
def get_students(db) -> list[UserAccount]:
    students = (
        db.query(UserAccount)
        .filter(UserAccount.role == "student")
        .filter(UserAccount.student_id.like("2023%"))
        .order_by(UserAccount.student_id)
        .all()
    )
    print(f"  [DB] 找到 {len(students)} 名学生")
    return students


def ensure_gitea_accounts(db, students: list[UserAccount]) -> None:
    gitea = GiteaService()
    print(f"  [Gitea] 为 {len(students)} 名学生创建 Gitea 账号 ...")
    synced = 0
    for i, student in enumerate(students):
        try:
            identity = ensure_gitea_account_for_user(db, student, gitea=gitea)
            if identity.sync_status == "synced":
                synced += 1
        except Exception as e:
            print(f"    学生 {student.username} Gitea 账号创建失败: {e}")
    print(f"  [Gitea] Gitea 账号同步完成: {synced}/{len(students)} synced")


# ── Step 5: 随机组队 ─────────────────────────────────
def form_teams(students: list[UserAccount]) -> list[list[UserAccount]]:
    shuffled = list(students)
    random.shuffle(shuffled)

    # 7 个团队: 3 个 5 人 + 4 个 4 人 = 31
    sizes = [5, 4, 5, 4, 4, 5, 4]
    teams = []
    idx = 0
    for size in sizes:
        team = shuffled[idx : idx + size]
        teams.append(team)
        idx += size
    return teams


# ── Step 6: 生成团队项目数据 ─────────────────────────
def _member_progress(members: list[UserAccount], team_index: int) -> list[dict]:
    progress_patterns = [
        # [progress, contribution, score, status]
        [85, 30, 92, "leader_merged"],
        [72, 25, 85, "pr_open"],
        [60, 22, 78, "pushed"],
        [45, 15, 0, "cloned"],
        [30, 8, 0, "pending"],
    ]
    mp = []
    for i, student in enumerate(members):
        pattern = progress_patterns[i % len(progress_patterns)]
        progress = pattern[0] + random.randint(-5, 5)
        progress = max(15, min(100, progress))
        contribution = pattern[1] + random.randint(-3, 3)
        score = pattern[2] if pattern[2] > 0 else 0
        status_key = pattern[3]

        if status_key == "leader_merged":
            clone_status = "done"
            push_status = "detected"
            pr_status = "merged"
            merge_status = "merged"
            status_label = "已完成"
            commit_count = 6 + random.randint(0, 4)
        elif status_key == "pr_open":
            clone_status = "done"
            push_status = "detected"
            pr_status = "open"
            merge_status = "pending"
            status_label = "PR 待审核"
            commit_count = 4 + random.randint(0, 3)
        elif status_key == "pushed":
            clone_status = "done"
            push_status = "detected"
            pr_status = "needs_pr"
            merge_status = "pending"
            status_label = "PR 待创建"
            commit_count = 2 + random.randint(0, 2)
        elif status_key == "cloned":
            clone_status = "done"
            push_status = "pending"
            pr_status = "not_created"
            merge_status = "pending"
            status_label = "未提交"
            commit_count = 1
        else:
            clone_status = "pending"
            push_status = "pending"
            pr_status = "not_created"
            merge_status = "pending"
            status_label = "未开始"
            commit_count = 0

        role = "队长" if i == 0 else "学生"
        task_idx = min(i, len(TASK_TEMPLATES) - 1)
        task = random.choice(TASK_TEMPLATES[task_idx])
        branch = f"feature/{_slug(student.real_name)}-{i + 1}"

        mp.append({
            "id": student.username,
            "name": student.real_name,
            "role": role,
            "task": task,
            "branch": branch,
            "cloneStatus": clone_status,
            "commitCount": commit_count,
            "pushStatus": push_status,
            "prStatus": pr_status,
            "mergeStatus": merge_status,
            "statusLabel": status_label,
            "lastCommitAt": _ts(max(0, 5 - i), 10 + i, 15 + i * 4) if commit_count > 0 else "-",
            "score": score,
            "contribution": contribution,
            "progress": progress,
            "reminderCount": 0,
            "lastReminderAt": "",
        })
    return mp


def _pull_requests(members: list[UserAccount], html_url: str, team_index: int) -> list[dict]:
    prs = []
    pr_configs = [
        {
            "number": 1,
            "title": "docs: 初始化项目结构与 README",
            "status": "merged",
            "statusLabel": "已合并",
            "leaderReview": "recommended",
            "teacherReview": "approved",
            "days_ago": 6,
        },
        {
            "number": 2,
            "title": "feat: 完成后端核心接口与数据模型",
            "status": "merged",
            "statusLabel": "已合并",
            "leaderReview": "recommended",
            "teacherReview": "approved",
            "days_ago": 4,
        },
        {
            "number": 3,
            "title": "feat: 前端页面开发与交互实现",
            "status": "open",
            "statusLabel": "PR 待审核",
            "leaderReview": "recommended",
            "teacherReview": "pending",
            "days_ago": 2,
        },
    ]
    for i, cfg in enumerate(pr_configs):
        creator = members[min(i, len(members) - 1)]
        prs.append({
            "id": f"pr-{cfg['number']}",
            "number": cfg["number"],
            "title": cfg["title"],
            "creator": creator.real_name,
            "sourceBranch": f"feature/{_slug(creator.real_name)}-{i + 1}",
            "targetBranch": "main",
            "status": cfg["status"],
            "statusLabel": cfg["statusLabel"],
            "leaderReviewStatus": cfg["leaderReview"],
            "leaderReviewer": members[0].real_name if cfg["leaderReview"] != "pending" else "",
            "teacherReviewStatus": cfg["teacherReview"],
            "teacherReviewer": "teacher_chen" if cfg["teacherReview"] == "approved" else "",
            "reviewComment": "代码结构清晰，测试覆盖到位。" if cfg["status"] == "merged" else "请补充异常路径测试用例。",
            "createdAt": _ts(cfg["days_ago"], 14, 20),
            "updatedAt": _ts(max(0, cfg["days_ago"] - 1), 16, 5),
            "url": f"{html_url}/pulls/{cfg['number']}",
        })
    return prs


def _recent_commits(members: list[UserAccount], team_index: int) -> list[dict]:
    messages = [
        "docs: 补充项目 README 和接口契约",
        "feat: 完成后端核心接口开发",
        "test: 增加单元测试和边界用例",
        "fix: 修复数据模型关联问题",
        "feat: 接入前端页面和交互逻辑",
        "refactor: 优化服务层代码结构",
    ]
    commits = []
    for i, msg in enumerate(messages):
        author = members[i % len(members)]
        commits.append({
            "id": f"team-{team_index}-commit-{i}",
            "author": author.real_name,
            "branch": f"feature/{_slug(author.real_name)}-{i + 1}",
            "message": msg,
            "time": _ts(max(0, 6 - i), 9 + i, 18 + i * 3),
        })
    return commits


def _git_events(members: list[UserAccount], team_index: int) -> list[dict]:
    leader = members[0]
    second = members[1] if len(members) > 1 else members[0]
    events = [
        {"id": f"evt-{team_index}-1", "type": "project_created", "actor": leader.real_name, "text": f"{leader.real_name} 创建了团队协作项目", "time": _ts(8, 9, 0)},
        {"id": f"evt-{team_index}-2", "type": "push", "actor": second.real_name, "text": f"{second.real_name} 推送了 feature 分支", "time": _ts(5, 14, 30)},
        {"id": f"evt-{team_index}-3", "type": "pull_request", "actor": leader.real_name, "text": f"{leader.real_name} 创建了 Pull Request #1", "time": _ts(6, 14, 20)},
        {"id": f"evt-{team_index}-4", "type": "merge", "actor": "teacher_chen", "text": "teacher_chen 合并了 PR #1", "time": _ts(5, 16, 10)},
        {"id": f"evt-{team_index}-5", "type": "push", "actor": members[min(2, len(members)-1)].real_name, "text": f"{members[min(2, len(members)-1)].real_name} 推送了 feature 分支", "time": _ts(2, 10, 45)},
    ]
    return events


def _chat_messages(members: list[UserAccount], team_index: int) -> list[dict]:
    leader = members[0]
    m2 = members[1] if len(members) > 1 else members[0]
    m3 = members[2] if len(members) > 2 else members[0]
    return [
        {"id": 1, "sender": leader.real_name, "content": "大家好，项目已经建好了，先把环境跑起来看看 README。", "time": _ts(8, 9, 15)},
        {"id": 2, "sender": m2.real_name, "content": "收到，我先跑一下后端接口，有报错再群里同步。", "time": _ts(8, 10, 30)},
        {"id": 3, "sender": m3.real_name, "content": "前端页面我这边先搭框架，有空帮忙看下接口字段对不对。", "time": _ts(7, 14, 20)},
        {"id": 4, "sender": leader.real_name, "content": "PR 模板和分支规范我写到 README 里了，提交前看一眼。", "time": _ts(6, 9, 45)},
    ]


def _repository_home(repo_info: dict, html_url: str, member_progress: list[dict], team_index: int) -> dict:
    name = repo_info["name"]
    return {
        "namespace": GITEA_ORG,
        "repoName": name,
        "visibility": "private",
        "course": repo_info["course"],
        "about": repo_info["description"],
        "readme": f"# {repo_info['title']}\n\n{repo_info['description']}\n\n## 当前进展\n\n- 队长负责接口契约和 README\n- 成员按功能分支提交 PR\n- 教师评语已同步到仓库主页\n\n## 本周风险\n\n测试覆盖和类图说明还需要继续补齐。",
        "classDiagram": "classDiagram\n    class Controller\n    class Service\n    class Repository\n    class Model\n    Controller --> Service\n    Service --> Repository\n    Repository --> Model",
        "teacherComment": "项目推进节奏真实，有持续 commit 和 PR 审核记录。下一轮重点看异常路径测试和演示脚本是否能独立运行。",
        "revisionSuggestions": "1. README 补充一键启动命令和截图。\n2. 类图中标清 Controller、Service、Repository 的职责。\n3. PR 描述里增加自测结果，不只写实现内容。",
        "teacherFeedbackUpdatedAt": _ts(1, 16, 20),
        "teacherFeedbackUpdatedBy": "teacher_chen",
        "cloneUrlMockOnly": False,
        "defaultBranch": "main",
        "cloneUrl": f"{html_url}.git",
        "sshUrl": f"ssh://git@gezhisystem.com:2222/{GITEA_ORG}/{name}.git",
        "updatedAt": _ts(1, 16, 20),
        "languageStats": [
            {"name": "Python", "percent": 46, "color": "#3572A5"},
            {"name": "JavaScript", "percent": 28, "color": "#f1e05a"},
            {"name": "Vue", "percent": 18, "color": "#41b883"},
            {"name": "Markdown", "percent": 8, "color": "#083fa1"},
        ],
        "files": [
            {"name": "backend", "type": "dir", "lastCommit": "feat: 完成后端核心接口", "updatedAt": _ts(3, 15, 25)},
            {"name": "frontend", "type": "dir", "lastCommit": "feat: 接入前端页面", "updatedAt": _ts(2, 11, 40)},
            {"name": "docs", "type": "dir", "lastCommit": "docs: 补充项目说明", "updatedAt": _ts(1, 16, 5)},
            {"name": "tests", "type": "dir", "lastCommit": "test: 增加回归用例", "updatedAt": _ts(4, 10, 40)},
            {"name": "README.md", "type": "file", "lastCommit": "docs: 更新运行步骤", "updatedAt": _ts(1, 16, 5)},
        ],
        "memberContribution": [
            {"name": m["name"], "contribution": m["contribution"], "commitCount": m["commitCount"]}
            for m in member_progress
        ],
    }


def create_team_project(
    db,
    repo_info: dict,
    team_members: list[UserAccount],
    gitea_repo: dict,
) -> dict:
    store = JsonStore(db)
    project_id = repo_info["name"]
    html_url = gitea_repo["htmlUrl"]
    clone_url = gitea_repo["cloneUrl"]
    ssh_url = gitea_repo["sshUrl"]

    leader = team_members[0]
    mp = _member_progress(team_members, 0)
    prs = _pull_requests(team_members, html_url, 0)
    commits = _recent_commits(team_members, 0)
    events = _git_events(team_members, 0)
    chat = _chat_messages(team_members, 0)

    # 判断仓库整体状态
    all_merged = all(m["mergeStatus"] == "merged" for m in mp)
    any_pushed = any(m["pushStatus"] == "detected" for m in mp)
    repo_status = "completed" if all_merged else ("collaborating" if any_pushed else "created")
    repo_status_label = {
        "completed": "已完成",
        "collaborating": "协作中",
        "created": "已创建",
    }.get(repo_status, "协作中")

    project = {
        "id": project_id,
        "status": "active",
        "project": {
            "id": project_id,
            "title": repo_info["title"],
            "course": repo_info["course"],
            "teamName": repo_info["team_name"],
            "description": repo_info["description"],
            "leaderId": leader.real_name,
            "createdBy": leader.username,
            "teacherId": "teacher_chen",
            "className": leader.class_name or "计科 2301",
            "status": "active",
            "createdAt": _ts(8, 9, 0),
        },
        "repository": {
            "repoName": repo_info["name"],
            "giteaOwner": GITEA_ORG,
            "htmlUrl": html_url,
            "cloneUrl": clone_url,
            "sshUrl": ssh_url,
            "defaultBranch": "main",
            "taskBranch": mp[0]["branch"] if mp else "feature/team-start",
            "status": repo_status,
            "statusLabel": repo_status_label,
            "webhookConfigured": True,
            "lastSyncedAt": _ts(0, 10, 20),
        },
        "memberProgress": mp,
        "pullRequests": prs,
        "recentCommits": commits,
        "gitEvents": events,
        "chatMessages": chat,
        "reminders": [],
        "teacherEvaluation": {
            "summary": "团队协作过程有持续提交记录，贡献度差异合理。下一阶段重点检查测试覆盖和 README 可复现性。",
            "auditor": "teacher_chen",
            "updatedAt": _ts(1, 16, 20),
        },
        "repositoryHome": _repository_home(repo_info, html_url, mp, 0),
        "updatedAt": _ts(0, 11, 30),
        "ownerId": leader.username,
    }

    saved = store.upsert(
        MODULE,
        PROJECT,
        project_id,
        project,
        owner_id=leader.username,
        role="demo_realistic_seed",
        status="active",
    )
    print(f"  [DB] 团队项目 {project_id} 已写入 (team={repo_info['team_name']}, members={len(team_members)})")
    return saved


# ── Step 7: 添加协作者 ───────────────────────────────
def add_collaborators(db, repo_info: dict, team_members: list[UserAccount]) -> None:
    repo_name = repo_info["name"]
    permissions = []
    for i, member in enumerate(team_members):
        perm = "admin" if i == 0 else "write"
        permissions.append(RepoPermission(member.username, perm, "leader" if i == 0 else "team_member"))
    # 添加教师
    permissions.append(RepoPermission("teacher_chen", "admin", "teacher"))

    result = ensure_repository_collaborators(
        db, GITEA_ORG, repo_name, permissions, gitea=GiteaService()
    )
    synced = sum(1 for r in result if r.get("status") == "synced")
    print(f"  [Gitea] {repo_name} 协作者同步: {synced}/{len(permissions)} synced")


# ── 主流程 ────────────────────────────────────────────
def main() -> int:
    print("=" * 60)
    print("开始注入 7 个团队仓库到 Gitea 和数据库")
    print("=" * 60)

    # Step 1+2: 创建 Gitea 仓库并推送代码
    print("\n[Step 1+2] 创建 Gitea 仓库并推送代码")
    gitea_repos = {}
    for repo_info in REPOS:
        print(f"\n--- {repo_info['name']} ---")
        gitea_repo = create_gitea_repo(repo_info)
        push_code_to_gitea(repo_info)
        create_webhook(repo_info["name"])
        gitea_repos[repo_info["name"]] = gitea_repo

    # Step 3: 获取学生并创建 Gitea 账号
    print("\n[Step 3] 创建学生 Gitea 账号")
    db = SessionLocal()
    try:
        students = get_students(db)
        if len(students) < 31:
            print(f"  警告: 期望 31 名学生，实际 {len(students)} 名")
        ensure_gitea_accounts(db, students)

        # Step 4: 随机组队
        print("\n[Step 4] 随机组队")
        teams = form_teams(students)
        for i, (repo_info, team) in enumerate(zip(REPOS, teams)):
            names = [s.real_name for s in team]
            print(f"  团队 {i+1} ({repo_info['team_name']}): {', '.join(names)}")

        # Step 5: 创建团队项目记录
        print("\n[Step 5] 写入团队项目数据到数据库")
        for repo_info, team in zip(REPOS, teams):
            gitea_repo = gitea_repos[repo_info["name"]]
            create_team_project(db, repo_info, team, gitea_repo)

        # Step 6: 添加协作者
        print("\n[Step 6] 添加学生协作者到 Gitea 仓库")
        for repo_info, team in zip(REPOS, teams):
            add_collaborators(db, repo_info, team)

        print("\n" + "=" * 60)
        print("注入完成！")
        print("=" * 60)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
