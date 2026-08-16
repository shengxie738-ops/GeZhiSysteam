from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount, hash_password
from app.repositories.json_store import JsonStore


TARGET_USER_ID = "23001020119"
TARGET_REAL_NAME = "谢渝"
TARGET_CLASS_NAME = "23006"
TARGET_PREFIX = f"target-{TARGET_USER_ID}"


@dataclass(frozen=True)
class DemoPerson:
    username: str
    real_name: str
    student_id: str
    class_name: str
    avatar_path: str


from app.models.user_account import UserAccount, hash_password
from app.services.gitea_account_service import ensure_gitea_account_for_user


def _sync_seed_gitea_accounts(db: Session, accounts: list[UserAccount]) -> dict:
    summary = {"synced": 0, "mock": 0, "failed": 0}
    for account in accounts:
        try:
            identity = ensure_gitea_account_for_user(db, account)
            if identity.sync_status == "synced":
                summary["synced"] += 1
            elif identity.sync_status == "mock":
                summary["mock"] += 1
            else:
                summary["failed"] += 1
        except Exception:
            summary["failed"] += 1
    return summary


def seed_target_user_demo_data(
    db: Session,
    *,
    data_root: str | Path = r"D:\软件杯测试数据注入",
    static_root: str | Path | None = None,
    anchor_now: datetime | None = None,
    reset_target: bool = False,
) -> dict[str, Any]:
    """Seed realistic demonstration data for the user shown in the UI screenshots."""
    now = anchor_now or datetime.now(timezone.utc)
    data_path = Path(data_root)
    if static_root is None:
        static_root = Path(__file__).resolve().parents[1] / "static"
    static_path = Path(static_root)
    static_path.mkdir(parents=True, exist_ok=True)

    if reset_target:
        _delete_target_records(db)

    names = _read_names(data_path / "学生姓名.txt")
    avatar_files = sorted((data_path / "头像").glob("*.jpg"), key=lambda item: _natural_key(item.name))
    people = _ensure_accounts(db, names, avatar_files, static_path / "avatars")
    repos = _personal_repositories(people[0], now, static_path)
    mistakes = _mistakes(people[0], now)
    teams = _team_repositories(people, now, static_path)

    store = JsonStore(db)
    for repo in repos:
        relations = repo.pop("_relations", [])
        store.upsert("code_repository", "project", repo["id"], repo, owner_id=TARGET_USER_ID, status="active")
        for relation in relations:
            store.upsert("code_repository", relation["type"], relation["id"], relation, owner_id=relation["userId"], status="active")
    for mistake in mistakes:
        store.upsert("exams", "mistake", mistake["id"], mistake, owner_id=TARGET_USER_ID, status="active")
    for team in teams:
        store.upsert(
            "team_collaboration_git",
            "project",
            team["id"],
            team,
            owner_id=team.get("ownerId") or TARGET_USER_ID,
            status="active",
        )

    created_accounts = [person for person in people if isinstance(person, UserAccount)]
    if not created_accounts:
        usernames = [person.username for person in people] + ["teacher_wu"]
        created_accounts = db.query(UserAccount).filter(UserAccount.username.in_(usernames)).all()
    return {
        "targetUser": TARGET_USER_ID,
        "personalRepositories": len(repos),
        "teamRepositories": len(teams),
        "mistakes": len(mistakes),
        "staticRoot": str(static_path),
        "gitea_accounts": _sync_seed_gitea_accounts(db, created_accounts),
    }


def _delete_target_records(db: Session) -> None:
    rows = (
        db.query(DomainRecord)
        .filter(
            DomainRecord.record_key.like(f"{TARGET_PREFIX}%")
            | (DomainRecord.owner_id == TARGET_USER_ID)
        )
        .all()
    )
    for row in rows:
        db.delete(row)
    db.commit()


def _read_names(path: Path) -> list[str]:
    if not path.exists():
        return ["江景珩", "陆知屿", "沈砚辞", "苏晚晴", "温知予", "夏清禾"]
    names: list[str] = []
    pattern = re.compile(r"^\s*\d+\.\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            names.append(match.group(1))
    return names or ["江景珩", "陆知屿", "沈砚辞", "苏晚晴", "温知予", "夏清禾"]


def _natural_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]


def _ensure_accounts(db: Session, names: list[str], avatar_files: list[Path], avatar_dir: Path) -> list[DemoPerson]:
    avatar_dir.mkdir(parents=True, exist_ok=True)
    members = [TARGET_REAL_NAME] + [name for name in names if name != TARGET_REAL_NAME][:6]
    people: list[DemoPerson] = []
    for index, real_name in enumerate(members):
        username = TARGET_USER_ID if index == 0 else f"23001020{130 + index:03d}"
        student_id = username
        avatar_name = f"{username}.jpg"
        if avatar_files:
            source = avatar_files[index % len(avatar_files)]
            shutil.copyfile(source, avatar_dir / avatar_name)
        elif not (avatar_dir / avatar_name).exists():
            (avatar_dir / avatar_name).write_bytes(b"")
        account = db.query(UserAccount).filter(UserAccount.username == username).first()
        if not account:
            account = UserAccount(username=username, role="student", password_hash=hash_password("Demo@2026"))
            db.add(account)
        account.role = "student"
        account.real_name = real_name
        account.student_id = student_id
        account.class_name = TARGET_CLASS_NAME
        account.avatar_path = avatar_name
        people.append(DemoPerson(username, real_name, student_id, TARGET_CLASS_NAME, avatar_name))

    teacher = db.query(UserAccount).filter(UserAccount.username == "teacher_wu").first()
    if not teacher:
        teacher = UserAccount(username="teacher_wu", role="teacher", password_hash=hash_password("Teacher@2026"))
        db.add(teacher)
    teacher.role = "teacher"
    teacher.real_name = "吴嘉宁"
    teacher.teacher_id = "T2026018"
    teacher.class_name = TARGET_CLASS_NAME
    db.commit()
    return people


def _ts(now: datetime, days: int, hour: int, minute: int) -> str:
    value = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if days:
        value = value.replace(day=max(1, value.day - days))
    return value.isoformat()


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return text or "course-project"


def _personal_repositories(owner: DemoPerson, now: datetime, static_root: Path) -> list[dict[str, Any]]:
    specs = [
        {
            "id": f"{TARGET_PREFIX}-repo-graph-path-lab",
            "title": "图最短路径可视化实验",
            "language": "Python",
            "course": "数据结构与算法",
            "tags": ["图算法", "Dijkstra", "课程实验"],
            "description": "把课堂上的邻接表、优先队列和最短路径松弛过程整理成可运行的小实验，方便复盘图章节错题。",
            "files": {
                "README.md": "# 图最短路径可视化实验\n\n运行 `python app/main.py` 查看示例输出。\n",
                "app/main.py": "from graph import shortest_path\n\nedges = {'A': [('B', 4), ('C', 2)], 'C': [('B', 1), ('D', 7)], 'B': [('D', 3)]}\nprint(shortest_path(edges, 'A', 'D'))\n",
                "app/graph.py": "import heapq\n\ndef shortest_path(edges, start, target):\n    heap = [(0, start, [start])]\n    seen = set()\n    while heap:\n        cost, node, path = heapq.heappop(heap)\n        if node == target:\n            return {'distance': cost, 'path': path}\n        if node in seen:\n            continue\n        seen.add(node)\n        for nxt, weight in edges.get(node, []):\n            heapq.heappush(heap, (cost + weight, nxt, path + [nxt]))\n    return {'distance': -1, 'path': []}\n",
                "tests/test_graph.py": "from app.graph import shortest_path\n\ndef test_shortest_path():\n    assert shortest_path({'A': [('B', 2)]}, 'A', 'B')['distance'] == 2\n",
            },
        },
        {
            "id": f"{TARGET_PREFIX}-repo-mistake-dashboard",
            "title": "课程错题复盘看板",
            "language": "TypeScript",
            "course": "软件工程综合实训",
            "tags": ["错题本", "可视化", "前端工程"],
            "description": "把作业和考试错题按知识点聚合，生成一页式复盘看板，重点展示最近一周重复出错的概念。",
            "files": {
                "README.md": "# 课程错题复盘看板\n\n运行 `npm install && npm run dev` 查看示例页面。\n",
                "package.json": json.dumps({"scripts": {"dev": "vite", "test": "vitest"}, "dependencies": {"@vitejs/plugin-react": "latest"}}, ensure_ascii=False, indent=2),
                "src/app.ts": "import { summarizeMistakes } from './mistakes';\n\nconst rows = summarizeMistakes([\n  { tag: 'B+树', count: 3 },\n  { tag: '递归边界', count: 2 }\n]);\nconsole.log(rows);\n",
                "src/mistakes.ts": "export type Mistake = { tag: string; count: number };\n\nexport function summarizeMistakes(items: Mistake[]) {\n  return items.sort((a, b) => b.count - a.count).map(item => ({ ...item, level: item.count >= 3 ? 'high' : 'medium' }));\n}\n",
                "tests/mistakes.test.ts": "import { summarizeMistakes } from '../src/mistakes';\n\nit('marks repeated mistakes as high risk', () => {\n  expect(summarizeMistakes([{ tag: 'SQL', count: 3 }])[0].level).toBe('high');\n});\n",
            },
        },
        {
            "id": f"{TARGET_PREFIX}-repo-lab-booking-api",
            "title": "实验室预约管理 API",
            "language": "Java",
            "course": "数据库系统原理",
            "tags": ["Spring", "MySQL", "事务"],
            "description": "围绕实验室预约冲突检测、事务提交和教师审核流程写的课程后端练习，保留了数据库设计说明。",
            "files": {
                "README.md": "# 实验室预约管理 API\n\n运行 `mvn test` 验证预约冲突检测逻辑。\n",
                "pom.xml": "<project><modelVersion>4.0.0</modelVersion><groupId>edu.demo</groupId><artifactId>lab-booking-api</artifactId><version>1.0.0</version></project>\n",
                "src/main/java/edu/demo/Application.java": "package edu.demo;\n\npublic class Application {\n  public static void main(String[] args) {\n    System.out.println(\"Lab booking API demo\");\n  }\n}\n",
                "src/main/java/edu/demo/BookingService.java": "package edu.demo;\n\npublic class BookingService {\n  public boolean canBook(int existingEnd, int newStart) {\n    return existingEnd <= newStart;\n  }\n}\n",
                "src/test/java/edu/demo/BookingServiceTest.java": "package edu.demo;\n\nclass BookingServiceTest {\n  void rejectsOverlap() {\n    assert !new BookingService().canBook(10, 9);\n  }\n}\n",
            },
        },
    ]

    repos: list[dict[str, Any]] = []
    for index, spec in enumerate(specs):
        archive_url = _write_archive(static_root, spec["id"], spec["files"])
        source_files = [{"path": path, "language": _language_for_path(path), "content": content} for path, content in spec["files"].items()]
        repo = {
            "id": spec["id"],
            "title": spec["title"],
            "slug": spec["id"].replace(f"{TARGET_PREFIX}-repo-", ""),
            "description": spec["description"],
            "author": owner.username,
            "authorName": owner.real_name,
            "avatar": f"/static/avatars/{owner.avatar_path}",
            "language": spec["language"],
            "course": spec["course"],
            "tags": spec["tags"],
            "collaborators": [],
            "visibility": "public",
            "status": "active",
            "recommendScore": 88 - index * 3,
            "giteaOwner": "campus",
            "giteaRepo": spec["id"].replace(f"{TARGET_PREFIX}-repo-", ""),
            "htmlUrl": f"https://gezhisystem.com/gitea/campus/{spec['id'].replace(f'{TARGET_PREFIX}-repo-', '')}",
            "cloneUrl": f"https://gezhisystem.com/gitea/campus/{spec['id'].replace(f'{TARGET_PREFIX}-repo-', '')}.git",
            "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/{spec['id'].replace(f'{TARGET_PREFIX}-repo-', '')}.git",
            "defaultBranch": "main",
            "archiveUrl": archive_url,
            "downloadUrl": archive_url,
            "readme": _repo_readme(spec["title"], spec["description"], spec["language"], spec["course"], spec["tags"], source_files),
            "classDiagram": _repo_class_diagram(spec["title"]),
            "fileTree": [{"name": path, "type": "file", "lastCommit": "feat: 补齐课程项目文件"} for path in spec["files"]],
            "sourceFiles": source_files,
            "createdAt": _ts(now, 9 - index, 9 + index, 20),
            "updatedAt": _ts(now, index, 15 + index, 10),
            "_relations": [
                {"id": f"{spec['id']}:23001020131", "type": "star", "projectId": spec["id"], "userId": "23001020131", "active": True, "status": "active", "updatedAt": _ts(now, index, 16, 0)},
                {"id": f"{spec['id']}:23001020132", "type": "favorite", "projectId": spec["id"], "userId": "23001020132", "active": True, "status": "active", "updatedAt": _ts(now, index, 16, 5)},
            ],
        }
        repos.append(repo)
    return repos


def _repo_readme(title: str, description: str, language: str, course: str, tags: list[str], source_files: list[dict[str, str]]) -> str:
    file_list = "\n".join(f"- `{item['path']}`：{_file_note(item['path'])}" for item in source_files)
    return f"""# {title}

## 项目介绍

{description}

这个仓库按大学课程作业的标准整理：README 能说明背景，核心代码可以直接运行，测试文件能复现至少一个课堂知识点。

## 技术栈

- 主语言：{language}
- 关联课程：{course}
- 关键词：{", ".join(tags)}

## 项目文件

{file_list}

## 运行方式

下载仓库 zip 后解压，按 README 中的命令运行。演示环境中的下载地址已经同步到 `archiveUrl` 字段。

## 复盘记录

谢渝在整理该仓库时把错题本里的易错点写进代码注释，便于答辩时说明“课程知识 -> 项目实现 -> 测试验证”的闭环。
"""


def _repo_class_diagram(title: str) -> str:
    class_name = re.sub(r"[^A-Za-z0-9]", "", title) or "CourseProject"
    return f"classDiagram\n    class {class_name}App\n    class CourseService\n    class DemoRepository\n    {class_name}App --> CourseService\n    CourseService --> DemoRepository"


def _file_note(path: str) -> str:
    if path.endswith("README.md"):
        return "项目介绍、运行方式和课程复盘"
    if "test" in path.lower():
        return "课程知识点的最小验证用例"
    if path.endswith((".py", ".ts", ".java")):
        return "核心逻辑代码"
    return "项目配置文件"


def _language_for_path(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "Python",
        ".ts": "TypeScript",
        ".java": "Java",
        ".md": "Markdown",
        ".json": "JSON",
        ".xml": "XML",
    }.get(suffix, "Text")


def _write_archive(static_root: Path, repo_id: str, files: dict[str, str]) -> str:
    archive_dir = static_root / "demo_repositories"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{repo_id}.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(f"{repo_id}/{path}", content)
    return f"/static/demo_repositories/{repo_id}.zip"


def _mistakes(student: DemoPerson, now: datetime) -> list[dict[str, Any]]:
    specs = [
        ("B+树索引范围查询为什么不一定走主键？", "数据库系统原理", "选择题", "误把聚簇索引和二级索引的回表过程混在一起。", ["B+树", "索引", "回表"], "homework", 3),
        ("非递归中序遍历栈为空时的循环条件", "数据结构与算法", "编程题", "只判断当前节点，没有同时判断辅助栈，导致右子树漏访问。", ["二叉树", "栈", "遍历"], "exam", 2),
        ("哈希冲突拉链法平均查找长度", "数据结构与算法", "计算题", "把装填因子直接当成比较次数，没有区分成功和失败查找。", ["哈希表", "复杂度"], "homework", 2),
        ("动态规划状态转移的初始化边界", "算法设计", "编程题", "先写转移方程但没有定义 dp[0] 的含义，样例能过但边界错。", ["动态规划", "边界条件"], "exam", 4),
        ("GROUP BY 后 SELECT 字段是否合法", "数据库系统原理", "选择题", "忽略了非聚合字段必须出现在分组条件中。", ["SQL", "GROUP BY"], "homework", 1),
        ("C++ 指针数组与数组指针辨析", "计算机程序设计", "填空题", "只看星号位置，没有结合括号优先级读声明。", ["指针", "数组"], "exam", 3),
        ("HTTP 状态码 401 与 403 的接口语义", "Web 开发基础", "简答题", "把未登录和无权限统一写成权限不足，导致前端跳转逻辑不清楚。", ["HTTP", "权限"], "homework", 2),
        ("PR 只测成功路径的评审问题", "软件工程综合实训", "实践题", "单元测试只覆盖 200，缺少 403、空 README 和无仓库记录三种路径。", ["PR", "单元测试", "异常路径"], "homework", 2),
    ]
    result = []
    for index, (title, subject, qtype, reason, tags, source_type, wrong_count) in enumerate(specs, start=1):
        mistake_id = f"{TARGET_PREFIX}-mistake-{index:02d}"
        source_id = f"{TARGET_PREFIX}-{source_type}-{index:02d}"
        last_wrong_at = _ts(now, 8 - min(index, 7), 19, 10 + index)
        result.append(
            {
                "id": mistake_id,
                "studentId": student.username,
                "studentName": student.real_name,
                "className": student.class_name,
                "examId": source_id,
                "examTitle": "课程作业错题订正" if source_type == "homework" else "阶段测验错题回放",
                "subject": subject,
                "questionId": f"q-{index:02d}",
                "questionType": qtype,
                "questionTitle": title,
                "studentAnswer": _student_wrong_answer(tags[0]),
                "correctAnswer": _correct_answer(tags[0]),
                "errorReason": reason,
                "knowledgeTags": tags,
                "wrongCount": wrong_count,
                "lastWrongAt": last_wrong_at,
                "mastered": index in {5},
                "aiAnalysis": {
                    "diagnosis": f"主要问题集中在「{tags[0]}」的判断条件和适用场景。",
                    "concept": f"复盘时先写出 {tags[0]} 的定义，再用一个最小例子验证。",
                    "practice": "完成 2 道同类题，把错误原因写成一句可以复用的检查清单。",
                    "path": ["回看原题", "补概念卡片", "同类迁移", "隔天复测"],
                },
                "source": {
                    "type": source_type,
                    "homeworkId": source_id if source_type == "homework" else "",
                    "examId": source_id if source_type == "exam" else "",
                    "title": "课程作业错题订正" if source_type == "homework" else "阶段测验错题回放",
                },
                "updatedAt": last_wrong_at,
            }
        )
    return result


def _student_wrong_answer(topic: str) -> str:
    return {
        "B+树": "范围查询直接走主键索引，不需要回表。",
        "二叉树": "while node: 只要当前节点为空就结束。",
        "哈希表": "平均查找长度等于装填因子。",
        "动态规划": "dp[i] = max(dp[i-1], dp[i-2] + a[i])，初始化省略。",
    }.get(topic, "按直觉写了答案，没有列出判断条件。")


def _correct_answer(topic: str) -> str:
    return {
        "B+树": "二级索引命中后可能需要回表；是否走索引还取决于选择度和优化器估算。",
        "二叉树": "循环条件应同时考虑当前节点和辅助栈：while cur or stack。",
        "哈希表": "成功/失败查找的平均长度公式不同，需结合冲突处理方式计算。",
        "动态规划": "先定义状态含义和初始值，再写转移方程。",
    }.get(topic, "先写概念定义，再根据题目条件选择对应方法。")


def _team_repositories(people: list[DemoPerson], now: datetime, static_root: Path) -> list[dict[str, Any]]:
    specs = [
        {
            "id": f"{TARGET_PREFIX}-team-oj-review",
            "title": "课程 OJ 判题与错题回流平台",
            "course": "编程团队实训",
            "teamName": "栈帧小组",
            "description": "面向程序设计课的判题、提交记录分析和错题本回流系统，支持公开样例、隐藏用例和教师端复盘。",
            "members": people[:4],
            "progress": [92, 78, 66, 54],
            "contribution": [36, 27, 22, 15],
            "files": {
                "README.md": "# 课程 OJ 判题与错题回流平台\n\n团队实训仓库，包含判题服务、提交分析和错题回流。\n",
                "backend/judge.py": "def judge(answer, expected):\n    return {'accepted': answer.strip() == expected.strip()}\n",
                "backend/mistake_sync.py": "def build_mistake(student_id, problem_id):\n    return {'studentId': student_id, 'questionId': problem_id, 'source': {'type': 'homework'}}\n",
                "frontend/app.ts": "export const title = 'OJ Review Platform';\n",
                "tests/test_judge.py": "from backend.judge import judge\n\ndef test_judge_accepts_exact_output():\n    assert judge('42', '42')['accepted']\n",
            },
        },
        {
            "id": f"{TARGET_PREFIX}-team-rag-course",
            "title": "课程论坛语义检索与 RAG 助教",
            "course": "人工智能技术基础",
            "teamName": "向量检索队",
            "description": "把论坛高质量问答、课程 PDF 和错题分析接入轻量检索，帮助学生在提问前找到已有解法。",
            "members": [people[0], *people[4:7]],
            "progress": [86, 72, 61, 39],
            "contribution": [33, 26, 24, 17],
            "files": {
                "README.md": "# 课程论坛语义检索与 RAG 助教\n\n团队实训仓库，沉淀检索、引用来源和教师建议。\n",
                "retrieval/chunk.py": "def chunk(text, size=180):\n    return [text[i:i+size] for i in range(0, len(text), size)]\n",
                "retrieval/search.py": "def search(query, docs):\n    return [doc for doc in docs if query in doc]\n",
                "web/app.ts": "export function renderAnswer(answer: string) { return `引用来源：${answer}`; }\n",
                "tests/test_chunk.py": "from retrieval.chunk import chunk\n\ndef test_chunk_splits_text():\n    assert chunk('abcdef', 2) == ['ab', 'cd', 'ef']\n",
            },
        },
    ]
    teams = []
    for team_index, spec in enumerate(specs):
        archive_url = _write_archive(static_root, spec["id"], spec["files"])
        members = spec["members"]
        html_url = f"https://gezhisystem.com/gitea/campus/{spec['id'].replace(f'{TARGET_PREFIX}-team-', '')}"
        member_progress = []
        for index, member in enumerate(members):
            progress = spec["progress"][index]
            member_progress.append(
                {
                    "id": member.username,
                    "name": member.real_name,
                    "avatar": f"/static/avatars/{member.avatar_path}",
                    "role": "队长" if index == 0 else "队员",
                    "task": _team_task(spec["title"], index),
                    "branch": f"feature/{_slug(member.real_name)}-{index + 1}",
                    "cloneStatus": "done" if progress >= 35 else "pending",
                    "commitCount": 5 - index + team_index,
                    "pushStatus": "detected" if progress >= 55 else "pending",
                    "prStatus": "merged" if progress >= 85 else ("open" if progress >= 65 else ("needs_pr" if progress >= 55 else "not_created")),
                    "mergeStatus": "merged" if progress >= 85 else "pending",
                    "statusLabel": "已合并" if progress >= 85 else ("PR 待审核" if progress >= 65 else "PR 待创建"),
                    "lastCommitAt": _ts(now, index, 14 + index, 8),
                    "score": 95 - index * 6 if progress >= 60 else 0,
                    "contribution": spec["contribution"][index],
                    "progress": progress,
                    "teacherComment": _teacher_member_comment(progress),
                }
            )
        teams.append(
            {
                "id": spec["id"],
                "status": "active",
                "ownerId": TARGET_USER_ID,
                "project": {
                    "id": spec["id"],
                    "title": spec["title"],
                    "course": spec["course"],
                    "teamName": spec["teamName"],
                    "description": spec["description"],
                    "leaderId": TARGET_USER_ID,
                    "createdBy": TARGET_USER_ID,
                    "teacherId": "teacher_wu",
                    "className": TARGET_CLASS_NAME,
                    "status": "active",
                    "createdAt": _ts(now, 7, 10 + team_index, 0),
                },
                "repository": {
                    "repoName": spec["id"].replace(f"{TARGET_PREFIX}-team-", ""),
                    "giteaOwner": "campus",
                    "htmlUrl": html_url,
                    "cloneUrl": f"{html_url}.git",
                    "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/{spec['id'].replace(f'{TARGET_PREFIX}-team-', '')}.git",
                    "defaultBranch": "main",
                    "taskBranch": "feature/team-start",
                    "status": "collaborating",
                    "statusLabel": "协作中",
                    "webhookConfigured": True,
                    "lastSyncedAt": _ts(now, 0, 17, 10 + team_index),
                },
                "memberProgress": member_progress,
                "pullRequests": _team_prs(members, html_url, now),
                "recentCommits": _team_commits(members, now, team_index),
                "gitEvents": _team_events(members, now, team_index),
                "chatMessages": _team_chat(members, now, team_index),
                "teacherEvaluation": {
                    "summary": "团队提交节奏比较稳定，谢渝承担了接口契约和最终集成，其他成员有明确分支和 PR 记录。",
                    "auditor": "teacher_wu",
                    "updatedAt": _ts(now, 0, 18, 20),
                },
                "repositoryHome": {
                    "namespace": "campus",
                    "repoName": spec["id"].replace(f"{TARGET_PREFIX}-team-", ""),
                    "visibility": "private",
                    "course": spec["course"],
                    "about": spec["description"],
                    "readme": _team_readme(spec["title"], spec["description"], members),
                    "classDiagram": "classDiagram\n    class ApiController\n    class ProjectService\n    class DomainRecordStore\n    ApiController --> ProjectService\n    ProjectService --> DomainRecordStore",
                    "teacherComment": "项目选题贴合课程要求，仓库主页能看到任务拆分、提交记录和错题/检索闭环，适合答辩演示。",
                    "revisionSuggestions": "建议把异常路径测试截图补进 docs，并在 README 顶部增加一张系统流程图。",
                    "teacherFeedbackUpdatedAt": _ts(now, 0, 18, 20),
                    "teacherFeedbackUpdatedBy": "吴嘉宁",
                    "cloneUrlMockOnly": True,
                    "defaultBranch": "main",
                    "cloneUrl": f"{html_url}.git",
                    "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/{spec['id'].replace(f'{TARGET_PREFIX}-team-', '')}.git",
                    "archiveUrl": archive_url,
                    "downloadUrl": archive_url,
                    "updatedAt": _ts(now, 0, 17, 30),
                    "languageStats": [{"name": "Python", "percent": 45}, {"name": "TypeScript", "percent": 35}, {"name": "Markdown", "percent": 20}],
                    "files": [{"name": path, "type": "file", "lastCommit": "feat: 完成团队实训文件"} for path in spec["files"]],
                    "sourceFiles": [{"path": path, "language": _language_for_path(path), "content": content} for path, content in spec["files"].items()],
                },
                "updatedAt": _ts(now, 0, 17, 35),
            }
        )
    return teams


def _team_task(title: str, index: int) -> str:
    tasks = [
        f"{title} 的接口契约、README 和最终集成",
        "后端服务、数据模型和接口联调",
        "前端页面状态、异常提示和演示脚本",
        "测试用例、CI 记录和教师反馈整理",
    ]
    return tasks[index % len(tasks)]


def _teacher_member_comment(progress: int) -> str:
    if progress >= 85:
        return "贡献度高，能把任务拆成可 review 的提交，适合负责合并前检查。"
    if progress >= 65:
        return "主线功能已经跑通，PR 描述需要补充自测截图。"
    if progress >= 50:
        return "有有效提交，但异常路径和边界用例还要补。"
    return "需要队长协助缩小任务范围，先交付最小可运行版本。"


def _team_prs(members: list[DemoPerson], html_url: str, now: datetime) -> list[dict[str, Any]]:
    return [
        {
            "id": "pr-3",
            "number": 3,
            "title": "feat: 接入教师建议与演示数据看板",
            "creator": members[0].real_name,
            "sourceBranch": "feature/repository-feedback",
            "targetBranch": "main",
            "status": "open",
            "statusLabel": "PR 待审核",
            "leaderReviewStatus": "recommended",
            "leaderReviewer": members[0].real_name,
            "teacherReviewStatus": "pending",
            "reviewComment": "自测通过，建议重点看空数据兜底和 README 展示。",
            "createdAt": _ts(now, 1, 16, 10),
            "updatedAt": _ts(now, 0, 11, 40),
            "url": f"{html_url}/pulls/3",
        },
        {
            "id": "pr-2",
            "number": 2,
            "title": "test: 补充错题回流和检索引用用例",
            "creator": members[1].real_name,
            "sourceBranch": "feature/tests",
            "targetBranch": "main",
            "status": "merged",
            "statusLabel": "已合并",
            "leaderReviewStatus": "recommended",
            "teacherReviewStatus": "approved",
            "reviewComment": "测试覆盖能支撑课堂演示。",
            "createdAt": _ts(now, 3, 20, 15),
            "updatedAt": _ts(now, 2, 9, 25),
            "url": f"{html_url}/pulls/2",
        },
    ]


def _team_commits(members: list[DemoPerson], now: datetime, team_index: int) -> list[dict[str, Any]]:
    messages = [
        "docs: 补充项目介绍和运行截图",
        "feat: 完成核心服务接口",
        "test: 增加异常路径回归用例",
        "fix: 修复空数据时页面统计为 NaN",
        "feat: 接入教师建议字段",
        "refactor: 拆分数据适配层",
    ]
    return [
        {
            "id": f"commit-{team_index}-{index}",
            "author": members[index % len(members)].real_name,
            "branch": f"feature/{index + 1}",
            "message": message,
            "time": _ts(now, max(0, 5 - index), 10 + index, 12),
        }
        for index, message in enumerate(messages)
    ]


def _team_events(members: list[DemoPerson], now: datetime, team_index: int) -> list[dict[str, Any]]:
    return [
        {"id": f"event-{team_index}-1", "type": "push", "actor": members[1].real_name, "text": f"{members[1].real_name} 推送了测试分支", "time": _ts(now, 2, 20, 20)},
        {"id": f"event-{team_index}-2", "type": "pull_request", "actor": members[0].real_name, "text": f"{members[0].real_name} 创建 Pull Request #3", "time": _ts(now, 1, 16, 10)},
        {"id": f"event-{team_index}-3", "type": "review", "actor": "吴嘉宁", "text": "教师要求补充异常路径说明", "time": _ts(now, 1, 18, 20)},
        {"id": f"event-{team_index}-4", "type": "merge", "actor": "吴嘉宁", "text": "教师合并 Pull Request #2", "time": _ts(now, 2, 9, 25)},
        {"id": f"event-{team_index}-5", "type": "commit", "actor": members[2 % len(members)].real_name, "text": "系统检测到新的课程项目提交", "time": _ts(now, 0, 15, 35)},
    ]


def _team_chat(members: list[DemoPerson], now: datetime, team_index: int) -> list[dict[str, Any]]:
    return [
        {"id": 1, "sender": members[0].real_name, "content": "我把 README 的演示路径补上了，大家确认一下自己的模块说明。", "time": _ts(now, 1, 19, 0)},
        {"id": 2, "sender": members[1].real_name, "content": "后端接口已经返回真实数据，剩下空列表兜底我今晚补。", "time": _ts(now, 1, 19, 18)},
        {"id": 3, "sender": "吴嘉宁", "content": "答辩时重点讲清楚数据从课程任务进入错题/仓库的闭环。", "time": _ts(now, 0, 10 + team_index, 45)},
    ]


def _team_readme(title: str, description: str, members: list[DemoPerson]) -> str:
    member_lines = "\n".join(f"- {member.real_name}（{member.student_id}）" for member in members)
    return f"""# {title}

{description}

## 团队成员

{member_lines}

## 协作方式

每个成员使用 `feature/{{module}}-{{name}}` 分支提交，队长先做 PR 初审，教师再确认合并。仓库保留测试记录、教师建议和答辩说明。
"""
