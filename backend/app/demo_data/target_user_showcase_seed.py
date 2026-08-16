from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore


TARGET_USER_ID = "23001020119"
TARGET_REAL_NAME = "谢渝"
TARGET_CLASS_NAME = "23006"
TARGET_PREFIX = f"target-{TARGET_USER_ID}-showcase"
CHINA_TZ = timezone(timedelta(hours=8))
README_PREVIEW_LIMIT = 6000
SOURCE_PREVIEW_FILE_LIMIT = 8
SOURCE_PREVIEW_CHAR_LIMIT = 1400


@dataclass(frozen=True)
class ClassmateAccount:
    real_name: str
    student_id: str
    password: str


@dataclass(frozen=True)
class DemoMember:
    username: str
    real_name: str
    student_id: str
    avatar_path: str
    class_name: str = TARGET_CLASS_NAME


def parse_classmate_accounts(path: str | Path) -> list[ClassmateAccount]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"演示账号同学文件不存在: {source}")
    pattern = re.compile(
        r"^\s*(?P<name>[^，,。]+?)\s*[，,]\s*学号\s*[:：]\s*(?P<student_id>\d+)\s*[。.]?\s*密码\s*[:：]\s*(?P<password>[^\s，,。]+)"
    )
    accounts: list[ClassmateAccount] = []
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = pattern.match(line)
        if not match:
            raise ValueError(f"无法解析同学账号行: {line}")
        accounts.append(
            ClassmateAccount(
                real_name=match.group("name").strip(),
                student_id=match.group("student_id").strip(),
                password=match.group("password").strip(),
            )
        )
    if not accounts:
        raise ValueError(f"同学账号文件没有解析到账号: {source}")
    return accounts


def seed_target_user_showcase_data(
    db: Session,
    *,
    classmates_root: str | Path = r"D:\演示账号的同学文件",
    team_repo_root: str | Path = r"D:\团队仓库数据",
    static_root: str | Path | None = None,
    anchor_now: datetime | None = None,
    reset_target: bool = False,
) -> dict[str, Any]:
    now = _normalize_now(anchor_now)
    classmates_path = Path(classmates_root)
    team_repo_path = Path(team_repo_root)
    if static_root is None:
        static_root = Path(__file__).resolve().parents[1] / "static"
    static_path = Path(static_root)
    static_path.mkdir(parents=True, exist_ok=True)

    classmates = parse_classmate_accounts(classmates_path / "演示账号的同学用户.txt")
    avatar_files = _avatar_files(classmates_path / "同学头像")
    repo_sources = _resolve_team_sources(team_repo_path)
    preserved_code_repositories = _target_code_repository_count(db)

    if reset_target:
        _reset_target_showcase_records(db)

    target = _ensure_target_account(db)
    members = _ensure_classmate_accounts(db, classmates, avatar_files, static_path / "avatars")
    teacher = _ensure_teacher_account(db)

    teams = _team_projects(
        target=_member_from_account(target),
        classmates=members,
        teacher=teacher,
        repo_sources=repo_sources,
        static_root=static_path,
        now=now,
    )
    mistakes = _exam_mistakes(target, now)
    attempts = _exam_attempts(target, now)
    ranked = _ranked_payloads(target, members, now)

    store = JsonStore(db)
    for team in teams:
        store.upsert("team_collaboration_git", "project", team["id"], team, owner_id=TARGET_USER_ID, status="active")
    for mistake in mistakes:
        store.upsert("exams", "mistake", mistake["id"], mistake, owner_id=TARGET_USER_ID, status="active")
    for attempt in attempts:
        store.upsert("exams", "attempt", attempt["id"], attempt, owner_id=TARGET_USER_ID, status="graded")
    for record_type, payloads in ranked.items():
        for payload in payloads:
            store.upsert("ranked", record_type, payload["id"], payload, owner_id=TARGET_USER_ID, status="active")

    return {
        "targetUser": TARGET_USER_ID,
        "classmates": len(classmates),
        "classmateAvatarsCopied": min(len(classmates), len(avatar_files)),
        "teamProjects": len(teams),
        "mistakes": len(mistakes),
        "examAttempts": len(attempts),
        "rankedRecords": sum(len(items) for items in ranked.values()),
        "preservedCodeRepositories": preserved_code_repositories,
        "staticRoot": str(static_path),
    }


def _normalize_now(anchor_now: datetime | None) -> datetime:
    now = anchor_now or datetime.now(CHINA_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CHINA_TZ)
    return now.astimezone(CHINA_TZ)


def _avatar_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    files = [item for item in path.iterdir() if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]

    def sort_key(item: Path) -> tuple[int, str]:
        match = re.search(r"\((\d+)\)", item.name)
        return (int(match.group(1)) if match else 9999, item.name)

    return sorted(files, key=sort_key)


def _target_code_repository_count(db: Session) -> int:
    return (
        db.query(DomainRecord)
        .filter(
            DomainRecord.module == "code_repository",
            DomainRecord.record_type == "project",
            DomainRecord.owner_id == TARGET_USER_ID,
        )
        .count()
    )


def _reset_target_showcase_records(db: Session) -> None:
    records = (
        db.query(DomainRecord)
        .filter(
            DomainRecord.module.in_(["team_collaboration_git", "exams", "ranked"]),
            (
                (DomainRecord.owner_id == TARGET_USER_ID)
                | (DomainRecord.record_key.like(f"{TARGET_PREFIX}%"))
                | (DomainRecord.record_key.like(f"target-{TARGET_USER_ID}-team-%"))
                | (DomainRecord.record_key.like(f"target-{TARGET_USER_ID}-mistake-%"))
            ),
        )
        .all()
    )
    for record in records:
        db.delete(record)
    db.commit()


def _ensure_target_account(db: Session) -> UserAccount:
    account = db.query(UserAccount).filter(UserAccount.username == TARGET_USER_ID).first()
    if not account:
        account = UserAccount(username=TARGET_USER_ID, avatar_path=f"{TARGET_USER_ID}.jpg")
        db.add(account)
    account.role = "student"
    account.real_name = TARGET_REAL_NAME
    account.student_id = TARGET_USER_ID
    account.class_name = TARGET_CLASS_NAME
    account.teacher_id = ""
    if not verify_password("123456", account.password_hash or ""):
        account.password_hash = get_password_hash("123456")
    if not account.avatar_path:
        account.avatar_path = f"{TARGET_USER_ID}.jpg"
    db.commit()
    db.refresh(account)
    return account


def _ensure_classmate_accounts(
    db: Session,
    classmates: list[ClassmateAccount],
    avatar_files: list[Path],
    avatar_dir: Path,
) -> list[DemoMember]:
    avatar_dir.mkdir(parents=True, exist_ok=True)
    members: list[DemoMember] = []
    for index, classmate in enumerate(classmates):
        source_avatar = avatar_files[index] if index < len(avatar_files) else None
        avatar_ext = source_avatar.suffix.lower() if source_avatar else ".jpg"
        avatar_name = f"{classmate.student_id}{avatar_ext}"
        if source_avatar:
            shutil.copyfile(source_avatar, avatar_dir / avatar_name)

        account = db.query(UserAccount).filter(UserAccount.username == classmate.student_id).first()
        if not account:
            account = UserAccount(username=classmate.student_id)
            db.add(account)
        account.role = "student"
        account.real_name = classmate.real_name
        account.student_id = classmate.student_id
        account.class_name = TARGET_CLASS_NAME
        account.teacher_id = ""
        account.avatar_path = avatar_name
        account.password_hash = get_password_hash(classmate.password)
        members.append(DemoMember(classmate.student_id, classmate.real_name, classmate.student_id, avatar_name))
    db.commit()
    return members


def _ensure_teacher_account(db: Session) -> DemoMember:
    account = db.query(UserAccount).filter(UserAccount.username == "teacher_wu").first()
    if not account:
        account = UserAccount(username="teacher_wu")
        db.add(account)
    account.role = "teacher"
    account.real_name = "吴彦章"
    account.teacher_id = "T2026018"
    account.student_id = ""
    account.class_name = TARGET_CLASS_NAME
    if not verify_password("123456", account.password_hash or ""):
        account.password_hash = get_password_hash("123456")
    db.commit()
    return DemoMember(account.username, account.real_name, account.teacher_id, account.avatar_path or "")


def _member_from_account(account: UserAccount) -> DemoMember:
    return DemoMember(account.username, account.real_name, account.student_id or account.username, account.avatar_path or f"{account.username}.jpg", account.class_name or TARGET_CLASS_NAME)


def _resolve_team_sources(root: Path) -> dict[str, Path]:
    oj_base = root / "OJ Review"
    oj_source = oj_base / "oj-review" if (oj_base / "oj-review").exists() else oj_base
    rag_source = root / "RAG Course"
    sources = {"oj": oj_source, "rag": rag_source}
    missing = [str(path) for path in sources.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"团队仓库目录不存在: {', '.join(missing)}")
    return sources


def _team_projects(
    *,
    target: DemoMember,
    classmates: list[DemoMember],
    teacher: DemoMember,
    repo_sources: dict[str, Path],
    static_root: Path,
    now: datetime,
) -> list[dict[str, Any]]:
    specs = [
        {
            "id": f"{TARGET_PREFIX}-team-oj-review",
            "title": "课程 OJ 判题与错题回流平台",
            "course": "软件工程综合实训",
            "teamName": "栈帧实验室",
            "repoName": "oj-review",
            "description": "面向程序设计课的在线评测、提交分析、错题回流和教师复盘系统。",
            "source": repo_sources["oj"],
            "members": [target, *classmates[:4]],
            "progress": [94, 86, 78, 69, 58],
            "contribution": [32, 21, 18, 16, 13],
            "languageStats": [{"name": "Java", "percent": 44}, {"name": "Vue", "percent": 30}, {"name": "Python", "percent": 18}, {"name": "Markdown", "percent": 8}],
        },
        {
            "id": f"{TARGET_PREFIX}-team-rag-course",
            "title": "课程论坛语义检索与 RAG 助教",
            "course": "人工智能技术基础",
            "teamName": "向量检索小队",
            "repoName": "rag-course",
            "description": "把课程资料、论坛问答和错题复盘接入检索增强生成，帮助学生形成可追溯学习路径。",
            "source": repo_sources["rag"],
            "members": [target, *classmates[4:]],
            "progress": [91, 83, 72, 64, 51],
            "contribution": [30, 23, 19, 16, 12],
            "languageStats": [{"name": "Python", "percent": 38}, {"name": "Java", "percent": 28}, {"name": "TypeScript", "percent": 24}, {"name": "Markdown", "percent": 10}],
        },
    ]
    projects: list[dict[str, Any]] = []
    for team_index, spec in enumerate(specs):
        html_url = f"https://gezhisystem.com/gitea/campus/{spec['repoName']}"
        archive_url = _write_repo_archive(static_root, spec["id"], spec["source"])
        source_files = _source_previews(spec["source"])
        readme = _read_readme(spec["source"], spec["title"], spec["description"])
        members = spec["members"]
        member_progress = []
        for index, member in enumerate(members):
            progress = spec["progress"][index % len(spec["progress"])]
            contribution = spec["contribution"][index % len(spec["contribution"])]
            last_commit_hour = 14 + (index % 8)
            last_commit_minute = (8 + index * 5) % 60
            member_progress.append(
                {
                    "id": member.username,
                    "name": member.real_name,
                    "avatar": f"/static/avatars/{member.avatar_path}" if member.avatar_path else "/static/avatars/default.png",
                    "role": "队长" if index == 0 else "队员",
                    "task": _team_task(spec["title"], index),
                    "branch": f"feature/{_slug(member.real_name)}-{index + 1}",
                    "cloneStatus": "done",
                    "commitCount": max(1, 9 - index + team_index),
                    "pushStatus": "detected",
                    "prStatus": "merged" if progress >= 86 else ("open" if progress >= 64 else "needs_pr"),
                    "mergeStatus": "merged" if progress >= 86 else "pending",
                    "statusLabel": "已合并" if progress >= 86 else ("PR 待审核" if progress >= 64 else "PR 待完善"),
                    "lastCommitAt": _ts(now, max(0, 5 - index), last_commit_hour, last_commit_minute),
                    "score": max(60, 96 - index * 4),
                    "contribution": contribution,
                    "progress": progress,
                    "teacherComment": _teacher_member_comment(progress),
                }
            )
        projects.append(
            {
                "id": spec["id"],
                "status": "active",
                "project": {
                    "id": spec["id"],
                    "title": spec["title"],
                    "course": spec["course"],
                    "teamName": spec["teamName"],
                    "description": spec["description"],
                    "leaderId": target.username,
                    "createdBy": target.username,
                    "teacherId": teacher.username,
                    "className": TARGET_CLASS_NAME,
                    "status": "active",
                    "createdAt": _ts(now, 12 - team_index, 9, 20),
                },
                "repository": {
                    "repoName": spec["repoName"],
                    "giteaOwner": "campus",
                    "htmlUrl": html_url,
                    "cloneUrl": f"{html_url}.git",
                    "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/{spec['repoName']}.git",
                    "defaultBranch": "main",
                    "taskBranch": "feature/showcase-polish",
                    "status": "collaborating",
                    "statusLabel": "协作中",
                    "webhookConfigured": True,
                    "webhookStatus": "configured",
                    "webhookEvents": ["push", "pull_request"],
                    "lastSyncedAt": _ts(now, 0, 16, 10 + team_index),
                },
                "memberProgress": member_progress,
                "pullRequests": _team_prs(members, html_url, now, team_index),
                "recentCommits": _team_commits(members, now, team_index),
                "gitEvents": _team_events(members, now, team_index),
                "aiGitCoachFeedback": _team_coach_feedback(members, now, team_index),
                "chatMessages": _team_chat(members, now, team_index),
                "teacherEvaluation": {
                    "summary": "团队提交节奏稳定，队长能把项目目标、接口契约和演示路径串起来，成员分工记录完整。",
                    "auditor": teacher.username,
                    "updatedAt": _ts(now, 0, 17, 30),
                },
                "repositoryHome": {
                    "namespace": "campus",
                    "repoName": spec["repoName"],
                    "visibility": "private",
                    "course": spec["course"],
                    "about": spec["description"],
                    "readme": readme,
                    "classDiagram": _class_diagram(spec["title"]),
                    "teacherComment": "仓库结构完整，README 能独立说明系统目标、运行方式和核心模块，适合比赛现场从协作记录切入演示。",
                    "revisionSuggestions": "建议演示前把最近一次 CI 结果截图补进 docs，并在 PR 描述中明确每个成员负责的测试范围。",
                    "teacherFeedbackUpdatedAt": _ts(now, 0, 17, 30),
                    "teacherFeedbackUpdatedBy": teacher.real_name,
                    "cloneUrlMockOnly": True,
                    "defaultBranch": "main",
                    "cloneUrl": f"{html_url}.git",
                    "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/{spec['repoName']}.git",
                    "archiveUrl": archive_url,
                    "downloadUrl": archive_url,
                    "updatedAt": _ts(now, 0, 17, 35),
                    "languageStats": spec["languageStats"],
                    "files": _file_tree(spec["source"]),
                    "sourceFiles": source_files,
                    "memberContribution": [{"name": item["name"], "contribution": item["contribution"], "commitCount": item["commitCount"]} for item in member_progress],
                },
                "updatedAt": _ts(now, 0, 17, 35),
            }
        )
    return projects


def _write_repo_archive(static_root: Path, repo_id: str, source: Path) -> str:
    archive_dir = static_root / "demo_repositories"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{repo_id}.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source.rglob("*"):
            if path.is_file() and _include_repo_file(path):
                archive.write(path, f"{repo_id}/{path.relative_to(source).as_posix()}")
    return f"/static/demo_repositories/{repo_id}.zip"


def _include_repo_file(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    if parts & {".git", "node_modules", "target", "dist", "build", "__pycache__", ".venv", "venv"}:
        return False
    return path.stat().st_size <= 512_000


def _source_previews(source: Path) -> list[dict[str, str]]:
    previews: list[dict[str, str]] = []
    suffixes = {".md", ".py", ".java", ".ts", ".js", ".vue", ".yml", ".yaml", ".sql", ".xml", ".json"}
    for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
        if len(previews) >= SOURCE_PREVIEW_FILE_LIMIT:
            break
        if not path.is_file() or path.suffix.lower() not in suffixes or not _include_repo_file(path):
            continue
        relative = path.relative_to(source).as_posix()
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        previews.append({"path": relative, "language": _language_for_path(path), "content": _trim_text(content, SOURCE_PREVIEW_CHAR_LIMIT)})
    return previews


def _file_tree(source: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(source.iterdir(), key=lambda item: item.name.lower()):
        if path.name.lower() in {"node_modules", "target", ".git", "dist", "build"}:
            continue
        items.append({"name": path.name, "type": "dir" if path.is_dir() else "file", "lastCommit": "docs: 同步真实团队仓库文件"})
    return items[:30]


def _read_readme(source: Path, title: str, description: str) -> str:
    readme_path = source / "README.md"
    if readme_path.exists():
        return _trim_text(readme_path.read_text(encoding="utf-8", errors="replace"), README_PREVIEW_LIMIT)
    return f"# {title}\n\n{description}\n\n## 演示说明\n\n本仓库来自团队协作源码目录，已同步为演示用归档和源码预览。"


def _trim_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}\n\n...（内容已裁剪，完整项目请下载仓库归档查看）"


def _language_for_path(path: Path) -> str:
    return {
        ".md": "Markdown",
        ".py": "Python",
        ".java": "Java",
        ".ts": "TypeScript",
        ".js": "JavaScript",
        ".vue": "Vue",
        ".yml": "YAML",
        ".yaml": "YAML",
        ".sql": "SQL",
        ".xml": "XML",
        ".json": "JSON",
    }.get(path.suffix.lower(), "Text")


def _exam_mistakes(target: UserAccount, now: datetime) -> list[dict[str, Any]]:
    specs = [
        ("Dijkstra 堆优化为什么能避免 O(n^2) 扫描", "数据结构与算法", "编程题", ["最短路", "优先队列", "图算法"], "第一次实现仍按邻接矩阵找最小 dist，稀疏图下无法通过大数据。", "先写出每条边最多入堆一次的复杂度，再补充 visited 判重。"),
        ("B+ 树覆盖索引和回表的判断边界", "数据库系统原理", "选择题", ["B+树", "覆盖索引", "SQL优化"], "只看 WHERE 字段是否命中索引，忽略 SELECT 字段是否都在二级索引里。", "用一条 SQL 标注查询字段、过滤字段、排序字段，逐项判断是否覆盖。"),
        ("OJ 隐藏用例下的输出比较器设计", "软件工程综合实训", "实践题", ["在线评测", "边界用例", "测试"], "比较输出时没有统一处理末尾空白，导致正确代码在隐藏样例中误判。", "把 trim、行尾空格和浮点误差拆成三个比较策略测试。"),
        ("RAG 引用来源为什么不能只返回生成答案", "人工智能技术基础", "简答题", ["RAG", "引用溯源", "检索"], "答案可读性较好，但没有返回 chunkId 和课程资料来源，无法复核。", "生成答案时同步输出 sourceId、标题、页码或段落位置。"),
        ("JWT 过期和刷新令牌的职责拆分", "Web 开发基础", "简答题", ["JWT", "权限", "接口安全"], "把 access token 和 refresh token 设置成相同有效期，演示时无法解释安全收益。", "用短 access token 加长 refresh token，并记录刷新接口的异常路径。"),
        ("事务隔离级别下的不可重复读复现", "数据库系统原理", "实验题", ["事务", "隔离级别", "并发"], "只写了理论结论，没有用两个会话复现读写顺序。", "用 session A/B 表格列出 begin、select、update、commit 的顺序。"),
        ("Vue 列表 key 使用 index 导致状态错位", "前端工程实践", "调试题", ["Vue", "key", "状态保持"], "拖拽排序后组件内部状态和数据项错位，原因是 key 不稳定。", "key 使用业务 id，并补一个删除中间项的交互测试。"),
        ("团队 PR 只描述实现未描述自测结果", "软件工程综合实训", "实践题", ["Git", "Pull Request", "协作"], "PR 描述只有功能点，没有写测试命令、截图和风险边界。", "PR 模板固定包含变更范围、自测命令、影响页面和待确认问题。"),
    ]
    mistakes = []
    for index, (title, subject, question_type, tags, reason, practice) in enumerate(specs, start=1):
        last_wrong_at = _ts(now, max(0, 9 - index), 19, 8 + index)
        mistakes.append(
            {
                "id": f"{TARGET_PREFIX}-mistake-{index:02d}",
                "studentId": TARGET_USER_ID,
                "studentName": target.real_name or TARGET_REAL_NAME,
                "className": TARGET_CLASS_NAME,
                "examId": f"{TARGET_PREFIX}-exam-review",
                "examTitle": "课程项目综合复盘测验",
                "subject": subject,
                "questionId": f"showcase-q-{index:02d}",
                "questionType": question_type,
                "questionTitle": title,
                "studentAnswer": "按课堂模板完成了主流程，但边界条件说明不完整。",
                "correctAnswer": practice,
                "errorReason": reason,
                "knowledgeTags": tags,
                "wrongCount": 2 + (index % 3),
                "lastWrongAt": last_wrong_at,
                "mastered": index in {2, 6},
                "aiAnalysis": {
                    "diagnosis": f"主要问题集中在「{tags[0]}」的适用边界和演示表达。",
                    "concept": f"复盘时先定义 {tags[0]} 的判断条件，再给出一个最小反例。",
                    "practice": practice,
                    "path": ["重看原题", "补边界清单", "完成同类题", "写入项目 README"],
                },
                "source": {"type": "exam" if index % 2 == 0 else "homework", "title": "课程项目综合复盘测验"},
                "updatedAt": last_wrong_at,
            }
        )
    return mistakes


def _exam_attempts(target: UserAccount, now: datetime) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{TARGET_PREFIX}-attempt-final-review",
            "studentId": TARGET_USER_ID,
            "studentName": target.real_name or TARGET_REAL_NAME,
            "examId": f"{TARGET_PREFIX}-exam-review",
            "examTitle": "课程项目综合复盘测验",
            "score": 94,
            "status": "graded",
            "submittedAt": _ts(now, 1, 20, 18),
            "durationMinutes": 47,
            "summary": "整体掌握较好，主要扣分集中在 RAG 引用溯源和 PR 自测描述。",
        }
    ]


def _ranked_payloads(target: UserAccount, classmates: list[DemoMember], now: datetime) -> dict[str, list[dict[str, Any]]]:
    profile = {
        "id": TARGET_USER_ID,
        "studentId": TARGET_USER_ID,
        "name": target.real_name or TARGET_REAL_NAME,
        "className": TARGET_CLASS_NAME,
        "tier": "钻石段位",
        "tierCode": "diamond",
        "score": 4180,
        "nextTier": "王者段位",
        "nextTierNeed": 1020,
        "streak": 7,
        "progress": 82,
        "badge": "./assets/ranked/badge-gold.png",
        "updatedAt": _ts(now, 0, 18, 40),
    }
    daily = {
        "id": f"{TARGET_PREFIX}-daily",
        "studentId": TARGET_USER_ID,
        "title": "完成 2 道图算法和 1 道数据库索引题",
        "tag": "冲刺训练 · 图算法 / B+ 树",
        "reward": 220,
        "progress": 2,
        "total": 3,
        "date": now.strftime("%Y-%m-%d"),
    }
    seasons = [
        {"id": f"{TARGET_PREFIX}-season-2026-spring", "studentId": TARGET_USER_ID, "title": "2026 春季学期", "status": "进行中", "dateRange": "2026-02-24 ~ 2026-07-20", "score": 4180, "tier": "钻石段位", "progress": 92, "winRate": "81%", "highestStreak": 9, "peakTier": "钻石", "schoolRank": "#3"},
        {"id": f"{TARGET_PREFIX}-season-2025-autumn", "studentId": TARGET_USER_ID, "title": "2025 秋季学期", "status": "已结束", "dateRange": "2025-09-01 ~ 2026-01-18", "score": 2760, "tier": "铂金段位", "progress": 100, "winRate": "74%", "highestStreak": 6, "peakTier": "铂金", "schoolRank": "#11"},
    ]
    matches = [
        {"id": f"{TARGET_PREFIX}-match-01", "studentId": TARGET_USER_ID, "title": "堆优化 Dijkstra", "type": "编程题", "result": "win", "scoreDelta": 231, "duration": "18分42秒", "createdAt": _ts(now, 1, 21, 5), "status": "settled", "questionId": "ranked-graph-dijkstra"},
        {"id": f"{TARGET_PREFIX}-match-02", "studentId": TARGET_USER_ID, "title": "覆盖索引判断", "type": "选择题", "result": "win", "scoreDelta": 168, "duration": "06分18秒", "createdAt": _ts(now, 2, 20, 12), "status": "settled", "questionId": "ranked-db-covering-index"},
        {"id": f"{TARGET_PREFIX}-match-03", "studentId": TARGET_USER_ID, "title": "RAG 引用片段排序", "type": "算法题", "result": "loss", "scoreDelta": -72, "duration": "23分09秒", "createdAt": _ts(now, 3, 19, 44), "status": "settled", "questionId": "ranked-rag-citation-rank"},
    ]
    mistake_specs = [
        (
            "rag-citation-rank",
            "RAG 引用片段排序",
            "算法题",
            "RAG / 排序 / 引用溯源",
            2,
            3,
            "排序权重设计不稳定",
            "召回分和新鲜度权重没有归一化，导致短文档被过度靠前。",
            "期末周复盘时把 BM25、向量相似度、资料时间三个分数统一缩放到 0~1，再写 3 组排序用例。",
        ),
        (
            "transaction-isolation",
            "事务隔离级别复现",
            "实验题",
            "MySQL / 隔离级别",
            1,
            5,
            "复现实验步骤不完整",
            "没有分清 session A 和 session B 的提交顺序，导致不可重复读现象解释不清。",
            "用两列时间线重写实验记录，把 begin、select、update、commit 的顺序逐行标出来。",
        ),
        (
            "dijkstra-heap",
            "堆优化 Dijkstra 超时",
            "编程题",
            "图算法 / 优先队列",
            3,
            6,
            "复杂度估计偏乐观",
            "仍按邻接矩阵每轮扫描最小 dist，稀疏图大样例直接 TLE。",
            "周末刷题时重写邻接表版本，并在 README 里写清 O((n+m)logn) 的来源。",
        ),
        (
            "dp-boundary",
            "动态规划初始化边界",
            "编程题",
            "动态规划 / 边界条件",
            2,
            7,
            "状态定义没有先固定",
            "先写转移方程再补初值，空数组和只有一个元素的样例全部漏掉。",
            "先写 dp[i] 含义，再列 n=0、n=1、n=2 三个最小样例，最后写代码。",
        ),
        (
            "bplus-covering-index",
            "覆盖索引判断",
            "选择题",
            "数据库 / B+树 / SQL优化",
            2,
            8,
            "只看 WHERE 没看 SELECT",
            "误以为 WHERE 命中二级索引就一定不回表，忽略查询字段不在索引里。",
            "把 SELECT、WHERE、ORDER BY 字段分别圈出来，判断每个字段是否都在联合索引中。",
        ),
        (
            "hash-collision",
            "哈希冲突平均查找长度",
            "计算题",
            "数据结构 / 哈希表",
            4,
            9,
            "公式套用不分场景",
            "把成功查找和失败查找的平均长度混在一起，拉链法和开放定址法也没区分。",
            "整理一页速记卡：拉链法、线性探测、成功查找、失败查找各写一个例题。",
        ),
        (
            "vue-key-state",
            "Vue 列表 key 导致状态错位",
            "调试题",
            "Vue / 组件状态 / key",
            1,
            10,
            "用 index 当稳定身份",
            "删除中间项后，输入框状态跟着位置走，导致错题标签显示到另一个题目上。",
            "把 key 改成业务 id，并补一个删除第二项后状态仍跟随原数据的前端测试。",
        ),
        (
            "jwt-refresh",
            "JWT 刷新令牌职责",
            "简答题",
            "Web安全 / JWT / 权限",
            2,
            11,
            "token 生命周期设计混乱",
            "access token 和 refresh token 设置成同样过期时间，无法解释刷新机制价值。",
            "画一张登录、过期、刷新、退出的时序图，明确短 token 和长 token 的职责。",
        ),
        (
            "pr-test-proof",
            "PR 描述缺少自测证明",
            "工程题",
            "Git / PR / 团队协作",
            1,
            12,
            "只写实现不写验证",
            "PR 里只有“完成接口联调”，没有测试命令、截图和失败路径说明。",
            "套用固定 PR 模板：改了什么、怎么测的、影响哪些页面、还有什么风险。",
        ),
        (
            "cache-lru",
            "LRU 缓存淘汰顺序",
            "编程题",
            "操作系统 / 缓存 / 链表",
            3,
            13,
            "访问后没有刷新热度",
            "get 命中缓存后没有把节点移动到队尾，导致最近访问的数据被提前淘汰。",
            "用双向链表加哈希表重写模板，手算 capacity=2 的 put/get 序列再提交。",
        ),
    ]
    mistakes = [
        {
            "id": f"{TARGET_PREFIX}-ranked-mistake-{slug}",
            "studentId": TARGET_USER_ID,
            "title": title,
            "type": mistake_type,
            "knowledge": knowledge,
            "wrongCount": wrong_count,
            "lastWrongAt": _ts(now, days_ago, 18 + (index % 4), 10 + index),
            "status": "review",
            "risk": risk,
            "errorPhenomenon": phenomenon,
            "note": note,
        }
        for index, (slug, title, mistake_type, knowledge, wrong_count, days_ago, risk, phenomenon, note) in enumerate(mistake_specs, start=1)
    ]
    leaderboard_items = [
        {"rank": 1, "name": classmates[0].real_name if classmates else "顾清寒", "className": TARGET_CLASS_NAME, "tier": "diamond", "streak": 8, "score": 4310, "studentId": classmates[0].student_id if classmates else "23001020120"},
        {"rank": 2, "name": target.real_name or TARGET_REAL_NAME, "className": TARGET_CLASS_NAME, "tier": "diamond", "streak": 7, "score": 4180, "studentId": TARGET_USER_ID, "isCurrent": True},
        {"rank": 3, "name": classmates[1].real_name if len(classmates) > 1 else "段奕寒", "className": TARGET_CLASS_NAME, "tier": "platinum", "streak": 4, "score": 3670, "studentId": classmates[1].student_id if len(classmates) > 1 else "23001020121"},
    ]
    return {
        "profile": [profile],
        "daily_challenge": [daily],
        "season": seasons,
        "match": matches,
        "mistake": mistakes,
        "leaderboard": [{"id": "default", "items": leaderboard_items}],
    }


def _team_task(title: str, index: int) -> str:
    tasks = [
        f"{title} 的接口契约、README 和最终集成",
        "后端服务、数据库模型和权限校验",
        "前端页面状态、错误提示和演示脚本",
        "测试用例、CI 记录和 PR 自测说明",
        "课程资料整理、引用来源和复盘文档",
    ]
    return tasks[index % len(tasks)]


def _teacher_member_comment(progress: int) -> str:
    if progress >= 90:
        return "贡献度高，能把任务拆成可审核提交，适合负责最终演示串联。"
    if progress >= 78:
        return "主线功能完成较扎实，建议继续补充异常路径测试。"
    if progress >= 64:
        return "已有清晰提交记录，PR 描述还可以增加自测截图。"
    return "基础模块已推进，下一步需要把边界用例和 README 补齐。"


def _team_prs(members: list[DemoMember], html_url: str, now: datetime, team_index: int) -> list[dict[str, Any]]:
    topic = "判题接口" if team_index == 0 else "检索链路"
    reviewer_note = "异常路径和教师复盘截图" if team_index == 0 else "引用来源和向量召回日志"
    return [
        {"id": f"pr-{team_index}-4", "number": 4, "title": f"test: real loop verification 23001020119 {topic} 202607141732", "creator": members[0].real_name, "sourceBranch": "feature/23001020119-real-loop-202607141732", "targetBranch": "main", "status": "open", "statusLabel": "待审核", "leaderReviewStatus": "recommended", "leaderReviewer": members[0].real_name, "teacherReviewStatus": "pending", "reviewComment": f"本地测试通过，建议老师重点看{reviewer_note}。", "createdAt": _ts(now, 0, 17, 22 + team_index), "updatedAt": _ts(now, 0, 17, 50 + team_index), "url": f"{html_url}/pulls/4", "source": "gitea_webhook"},
        {"id": f"pr-{team_index}-3", "number": 3, "title": "feat: connect teacher feedback and repository home showcase", "creator": members[1].real_name, "sourceBranch": "feature/showcase-feedback", "targetBranch": "main", "status": "open", "statusLabel": "待审核", "leaderReviewStatus": "changes_requested", "leaderReviewer": members[0].real_name, "teacherReviewStatus": "pending", "reviewComment": "队长要求补充自测命令、截图路径和回滚风险说明。", "createdAt": _ts(now, 0, 15, 48 + team_index), "updatedAt": _ts(now, 0, 16, 36 + team_index), "url": f"{html_url}/pulls/3", "source": "gitea"},
        {"id": f"pr-{team_index}-2", "number": 2, "title": "test: add edge cases and regression suite", "creator": members[2].real_name, "sourceBranch": "feature/regression-tests", "targetBranch": "main", "status": "merged", "statusLabel": "已合并", "leaderReviewStatus": "recommended", "leaderReviewer": members[0].real_name, "teacherReviewStatus": "approved", "teacherReviewer": "teacher_wu", "reviewComment": "测试覆盖能支撑课堂演示，已合并到 main。", "createdAt": _ts(now, 0, 13, 42 + team_index), "updatedAt": _ts(now, 0, 14, 18 + team_index), "url": f"{html_url}/pulls/2", "source": "gitea_webhook"},
        {"id": f"pr-{team_index}-1", "number": 1, "title": "docs: initialize architecture and demo script", "creator": members[3].real_name, "sourceBranch": "feature/project-docs", "targetBranch": "main", "status": "merged", "statusLabel": "已合并", "leaderReviewStatus": "recommended", "leaderReviewer": members[0].real_name, "teacherReviewStatus": "approved", "teacherReviewer": "teacher_wu", "reviewComment": "文档结构清楚，已补充比赛演示路线。", "createdAt": _ts(now, 0, 10, 20 + team_index), "updatedAt": _ts(now, 0, 11, 8 + team_index), "url": f"{html_url}/pulls/1", "source": "gitea"},
    ]


def _team_commits(members: list[DemoMember], now: datetime, team_index: int) -> list[dict[str, Any]]:
    messages = [
        "test: real loop verification and screenshot evidence",
        "fix: stabilize empty-state fallback before demo",
        "feat: connect webhook payload to team progress panel",
        "docs: update README with runbook and rollback notes",
        "test: add edge cases for classroom demo data",
        "refactor: split repository adapter from page state",
        "feat: expose teacher feedback in repository home",
        "chore: align branch names with PR checklist",
    ]
    return [
        {
            "id": f"commit-{team_index}-{index}",
            "sha": f"{team_index + 1}{index:02d}0cafe23001020119{index}",
            "author": members[index % len(members)].real_name,
            "branch": f"feature/230010201{19 + (index % len(members))}-demo-{index + 1}",
            "message": message,
            "time": _ts(now, 0, 10 + index, 6 + team_index),
            "source": "gitea_webhook" if index < 4 else "gitea",
        }
        for index, message in enumerate(messages)
    ]


def _team_events(members: list[DemoMember], now: datetime, team_index: int) -> list[dict[str, Any]]:
    repo_name = "oj-review" if team_index == 0 else "rag-course"
    return [
        {"id": f"event-{team_index}-10", "type": "gitea_synced", "actor": "23001020119", "text": f"Gitea 实时同步 {repo_name} 的 PR、commit 和 webhook 状态", "time": _ts(now, 0, 18, 2 + team_index), "source": "gitea"},
        {"id": f"event-{team_index}-9", "type": "pr_changes_requested", "actor": members[0].real_name, "text": f"{members[0].real_name} 要求 PR #3 补充截图路径和自测命令", "time": _ts(now, 0, 17, 58 + team_index), "source": "leader_review"},
        {"id": f"event-{team_index}-8", "type": "pull_request", "actor": members[0].real_name, "text": f"Webhook 捕获 {members[0].real_name} 创建 Pull Request #4", "time": _ts(now, 0, 17, 50 + team_index), "source": "gitea_webhook"},
        {"id": f"event-{team_index}-7", "type": "push", "actor": members[0].real_name, "text": f"Webhook 捕获 {members[0].real_name} 推送 feature/23001020119-real-loop-202607141732", "time": _ts(now, 0, 17, 32 + team_index), "source": "gitea_webhook"},
        {"id": f"event-{team_index}-6", "type": "gitea_synced", "actor": "23001020119", "text": f"Gitea 同步 {repo_name} 分支与语言统计", "time": _ts(now, 0, 16, 42 + team_index), "source": "gitea"},
        {"id": f"event-{team_index}-5", "type": "pull_request", "actor": members[1].real_name, "text": f"{members[1].real_name} 创建 Pull Request #3，等待队长复核", "time": _ts(now, 0, 16, 36 + team_index), "source": "gitea"},
        {"id": f"event-{team_index}-4", "type": "push", "actor": members[1].real_name, "text": f"Webhook 捕获 {members[1].real_name} 推送演示反馈分支", "time": _ts(now, 0, 15, 48 + team_index), "source": "gitea_webhook"},
        {"id": f"event-{team_index}-3", "type": "merge", "actor": "teacher_wu", "text": "教师合并 PR #2，并确认异常路径测试记录", "time": _ts(now, 0, 14, 18 + team_index), "source": "gitea"},
        {"id": f"event-{team_index}-2", "type": "pull_request", "actor": members[2].real_name, "text": f"Webhook 捕获 {members[2].real_name} 更新 Pull Request #2", "time": _ts(now, 0, 13, 52 + team_index), "source": "gitea_webhook"},
        {"id": f"event-{team_index}-1", "type": "repository_created", "actor": members[0].real_name, "text": f"{members[0].real_name} 创建团队仓库并初始化 main 分支", "time": _ts(now, 0, 9, 30 + team_index), "source": "system"},
    ]


def _team_coach_feedback(members: list[DemoMember], now: datetime, team_index: int) -> list[dict[str, Any]]:
    repo_topic = "OJ 判题回流" if team_index == 0 else "课程 RAG 检索"
    branches = [
        "feature/23001020119-real-loop-202607141732",
        "feature/showcase-feedback",
        "feature/regression-tests",
        "feature/project-docs",
        "feature/webhook-progress-sync",
        "feature/demo-runbook-polish",
    ]
    summaries = [
        f"{repo_topic} 的真实闭环分支命名规范，commit 信息能对应 PR 目标。",
        "PR 描述覆盖了变更范围，但还需要把自测命令和截图路径放到顶部。",
        "异常路径测试补得较完整，可以支撑老师现场抽查。",
        "README 已能独立说明运行步骤，建议补一张最终流程截图。",
        "Webhook 动态能推动成员进度，但需要避免重复同步事件刷屏。",
        "演示 runbook 已经清楚，最后确认回滚步骤和数据重置命令。",
    ]
    feedback = []
    for index, summary in enumerate(summaries):
        author = members[index % len(members)].real_name
        created_at = _ts(now, 0, 17 - index, 24 + team_index)
        feedback.append(
            {
                "id": f"coach-{team_index}-{index + 1}",
                "sha": f"{team_index + 1}{index:02d}9a7b23001020119",
                "status": "ready" if index < 5 else "fallback",
                "branch": branches[index],
                "author": author,
                "summary": summary,
                "mistakes": [
                    "PR 描述中的验证命令需要和实际提交保持一致。",
                    "截图或日志证据要能对应到本次分支，而不是复用旧记录。",
                ][: 1 + (index % 2)],
                "suggestions": [
                    "在 PR 顶部写清楚变更范围、自测命令、影响页面和待确认问题。",
                    "将 Webhook 同步时间、commit SHA、PR 编号写入演示备注，便于老师追问时定位。",
                    "合并前再运行一次最小回归脚本，确认 main 分支可直接演示。",
                ][: 2 + (index % 2)],
                "createdAt": created_at,
                "updatedAt": created_at,
            }
        )
    return feedback


def _team_chat(members: list[DemoMember], now: datetime, team_index: int) -> list[dict[str, Any]]:
    return [
        {"id": 1, "sender": members[0].real_name, "content": "我把演示路线写进 README 了，大家按模块补一下自测命令。", "time": _ts(now, 2, 20, 10)},
        {"id": 2, "sender": members[1].real_name, "content": "后端异常路径已经补测试，PR 里放了执行结果。", "time": _ts(now, 1, 10, 35)},
        {"id": 3, "sender": members[-1].real_name, "content": "我负责把课程知识点和代码文件对应关系整理到 docs。", "time": _ts(now, 0, 15, 20)},
    ]


def _class_diagram(title: str) -> str:
    class_name = re.sub(r"[^A-Za-z0-9]", "", title) or "ShowcaseProject"
    return f"classDiagram\n    class {class_name}Controller\n    class CollaborationService\n    class RepositoryHomeAdapter\n    class TeacherReview\n    {class_name}Controller --> CollaborationService\n    CollaborationService --> RepositoryHomeAdapter\n    TeacherReview --> CollaborationService"


def _slug(value: str) -> str:
    return value.encode("utf-8").hex()[:10]


def _ts(now: datetime, days: int, hour: int, minute: int) -> str:
    return (now - timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()
