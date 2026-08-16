from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount, hash_password
from app.repositories.json_store import JsonStore


TARGET_USER_ID = "23001020119"
TARGET_REAL_NAME = "谢渝"
TARGET_CLASS_NAME = "23006"
TARGET_PREFIX = f"target-{TARGET_USER_ID}"


def seed_target_user_mistake_data(
    db: Session,
    *,
    anchor_now: datetime | None = None,
    password: str = "123456",
) -> dict[str, Any]:
    """Upsert curated mistake-book records for the target demo student."""
    now = anchor_now or datetime.now(timezone.utc)
    _ensure_target_account(db, password=password)
    _delete_stale_showcase_mistakes(db)

    store = JsonStore(db)
    mistakes = _mistakes(now)
    for mistake in mistakes:
        store.upsert("exams", "mistake", mistake["id"], mistake, owner_id=TARGET_USER_ID, status="active")

    return {
        "targetUser": TARGET_USER_ID,
        "mistakes": len(mistakes),
        "recordKeys": [item["id"] for item in mistakes],
    }


def _delete_stale_showcase_mistakes(db: Session) -> None:
    rows = (
        db.query(DomainRecord)
        .filter(
            DomainRecord.module == "exams",
            DomainRecord.record_type == "mistake",
            DomainRecord.owner_id == TARGET_USER_ID,
            DomainRecord.record_key.like(f"{TARGET_PREFIX}-showcase-mistake-%"),
        )
        .all()
    )
    for row in rows:
        db.delete(row)
    if rows:
        db.commit()


def _ensure_target_account(db: Session, *, password: str) -> UserAccount:
    account = db.query(UserAccount).filter(UserAccount.username == TARGET_USER_ID).first()
    if not account:
        account = UserAccount(username=TARGET_USER_ID, role="student")
        db.add(account)
    account.role = "student"
    account.real_name = TARGET_REAL_NAME
    account.student_id = TARGET_USER_ID
    account.class_name = TARGET_CLASS_NAME
    account.password_hash = hash_password(password)
    if not account.avatar_path:
        account.avatar_path = f"{TARGET_USER_ID}.jpg"
    db.commit()
    db.refresh(account)
    return account


def _ts(now: datetime, days_ago: int, hour: int, minute: int) -> str:
    value = now - timedelta(days=days_ago)
    value = value.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return value.isoformat()


def _analysis(tags: list[str], diagnosis: str, concept: str, practice: str) -> dict[str, Any]:
    return {
        "diagnosis": diagnosis,
        "concept": concept,
        "practice": practice,
        "path": ["重看原题", "对比错误答案", "补边界清单", "完成同类题", "写入项目复盘"],
        "source": "seeded",
        "agentId": "agent_mistake_analyst",
        "agentName": "错题分析师",
        "knowledgeTags": tags,
    }


def _mistakes(now: datetime) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = [
        {
            "title": "Dijkstra 堆优化为什么能避免 O(n^2) 扫描",
            "subject": "数据结构与算法",
            "type": "编程题",
            "tags": ["最短路", "优先队列", "图算法"],
            "studentAnswer": "把所有边都先放进优先队列，每轮弹出距离最小的点后直接松弛；因为堆顶总是最小值，所以不需要 visited 判重，复杂度大约是 O(E)。",
            "correctAnswer": "用邻接表存边，只把当前点的出边松弛结果入堆；每次弹出堆顶最小 dist，并用 visited 或 dist 判重过滤过期记录。这样不用每轮扫描全部未确定顶点，复杂度通常为 O((V+E)logV)。",
            "reason": "答案抓住了优先队列能取最小值，但误以为所有边一次入堆且不需要判重，遗漏了过期堆记录和邻接表按需松弛。",
            "wrongCount": 3,
            "mastered": False,
            "diagnosis": "你的答案接近正确思路，但把“按出边松弛后入堆”说成“所有边先入堆”，并漏掉 visited/dist 判重，这是堆优化 Dijkstra 最常见的边界错误。",
            "concept": "堆优化不是减少边的数量，而是避免用 O(V) 扫描找当前最小 dist；堆中可能有同一节点的旧距离，必须弹出时过滤。",
            "practice": "重写一次伪代码，专门标出 heappush 的时机和跳过过期记录的条件，再用稀疏图与含重复松弛的样例验证。",
        },
        {
            "title": "B+ 树覆盖索引和回表的判断边界",
            "subject": "数据库系统原理",
            "type": "选择题",
            "tags": ["B+树", "覆盖索引", "SQL优化"],
            "studentAnswer": "只要 WHERE 条件命中了联合索引，就可以认为走覆盖索引，不需要回表；ORDER BY 字段是否在索引里影响不大。",
            "correctAnswer": "覆盖索引要求查询所需字段都能从二级索引叶子节点取得，既要看 WHERE，也要看 SELECT、ORDER BY、GROUP BY 字段；若还要读取索引外字段，就需要回表。",
            "reason": "把“命中索引”误判为“覆盖索引”，没有检查 SELECT 字段和排序/分组字段是否都在同一个索引中。",
            "wrongCount": 4,
            "mastered": True,
            "diagnosis": "你已经知道 WHERE 会影响索引选择，但把索引过滤和覆盖索引混在了一起，导致回表判断过于乐观。",
            "concept": "覆盖索引关注的是“本次查询需要的列是否全部在索引中”，不是“过滤条件是否使用了索引”。",
            "practice": "给 3 条 SQL 分别圈出 SELECT、WHERE、ORDER BY 字段，再判断是否都能从同一二级索引拿到。",
        },
        {
            "title": "OJ 隐藏用例下的输出比较器设计",
            "subject": "软件工程综合实训",
            "type": "实践题",
            "tags": ["在线评测", "边界用例", "测试"],
            "studentAnswer": "比较器直接 trim 整个输出字符串后做相等判断即可，隐藏用例如果失败多半是学生算法逻辑问题。",
            "correctAnswer": "输出比较器要按题目类型选择策略：精确匹配、忽略行尾空格、忽略多余空行、浮点误差比较等；隐藏用例失败时需要记录期望输出、实际输出和差异位置。",
            "reason": "把所有题目统一成一次 trim，忽略了逐行空白、浮点误差和差异定位，导致正确程序也可能被误判。",
            "wrongCount": 2,
            "mastered": False,
            "diagnosis": "你的答案有基本的空白处理意识，但处理粒度太粗，容易把合法格式差异和真实错误混在一起。",
            "concept": "OJ 比较器是测试策略的一部分，不同题型的判定标准不同；隐藏用例更需要可解释的差异报告。",
            "practice": "补 4 个比较器测试：行尾空格、多余空行、浮点误差 1e-6、真实输出不一致。",
        },
        {
            "title": "RAG 引用来源为什么不能只返回生成答案",
            "subject": "人工智能技术基础",
            "type": "简答题",
            "tags": ["RAG", "引用来源", "检索"],
            "studentAnswer": "只要模型回答内容准确，前端展示最终答案就够了；来源可以放在日志里，不一定要返回给用户。",
            "correctAnswer": "RAG 应同时返回生成答案与可追溯来源，如 sourceId、标题、页码、段落或 chunkId，方便用户核验、教师复盘和发现检索偏差。",
            "reason": "忽略了 RAG 的可追溯性要求，把内部日志和面向用户的证据链混为一谈。",
            "wrongCount": 2,
            "mastered": False,
            "diagnosis": "你的答案重视可读性，但没有体现 RAG 相比普通生成式回答的核心价值：答案必须能追溯到检索证据。",
            "concept": "RAG 的质量不仅看答案文本，还看检索命中、引用片段和生成内容之间是否一致。",
            "practice": "为一次课程问答设计返回 JSON，至少包含 answer、sources、chunkId、page、score 五个字段。",
        },
        {
            "title": "JWT 过期和刷新令牌的职责拆分",
            "subject": "Web 开发基础",
            "type": "简答题",
            "tags": ["JWT", "权限", "接口安全"],
            "studentAnswer": "access token 和 refresh token 都设置成 7 天有效，前端发现 401 后重新登录即可，刷新接口可以省略。",
            "correctAnswer": "access token 应较短有效期，用于访问接口；refresh token 有较长有效期，只用于换取新的 access token，并应支持撤销、轮换和异常处理。",
            "reason": "把两个令牌的职责和风险等级等同处理，导致演示时无法说明短令牌降低泄露风险、刷新令牌维持会话的安全收益。",
            "wrongCount": 3,
            "mastered": False,
            "diagnosis": "你的方案能跑通登录，但牺牲了令牌分层设计的安全意义，特别是 refresh token 不应和 access token 一样到处使用。",
            "concept": "短 access token 控制接口访问风险，长 refresh token 负责会话续期，两者使用场景和存储策略不同。",
            "practice": "画出 access 过期后的 401 -> refresh -> retry 流程，并补充 refresh 失败时的退出登录路径。",
        },
        {
            "title": "事务隔离级别下的不可重复读复现",
            "subject": "数据库系统原理",
            "type": "实验题",
            "tags": ["事务", "隔离级别", "并发"],
            "studentAnswer": "不可重复读就是同一条 SELECT 前后结果不同，所以把隔离级别设成 READ COMMITTED 后执行两次 SELECT 就能复现。",
            "correctAnswer": "需要两个并发会话配合：会话 A 开启事务并第一次读，会话 B 修改同一行并提交，会话 A 再读同一行；在 READ COMMITTED 下可复现，在 REPEATABLE READ 下通常不会。",
            "reason": "知道现象定义，但缺少会话 A/B 的操作顺序，导致实验步骤不能稳定复现并对比隔离级别。",
            "wrongCount": 2,
            "mastered": True,
            "diagnosis": "你记住了不可重复读的表现，但实验答案缺少并发事务时间线，无法证明隔离级别的差异。",
            "concept": "隔离级别问题必须说明事务边界、两个会话的读写顺序以及提交时机。",
            "practice": "用表格写 session A/B 的 begin、select、update、commit、select 顺序，并分别在两个隔离级别下记录结果。",
        },
        {
            "title": "Vue 列表 key 使用 index 导致状态错位",
            "subject": "前端工程实践",
            "type": "调试题",
            "tags": ["Vue", "key", "状态保持"],
            "studentAnswer": "index 作为 key 一般没问题，拖拽排序后状态错位可以在 watch 里重新同步列表数据解决。",
            "correctAnswer": "列表项会新增、删除、排序时不能用 index 作为 key，应使用稳定业务 id；否则组件复用会把输入框、选中态等内部状态带到错误的数据项上。",
            "reason": "把状态错位当成数据同步问题，没有定位到虚拟 DOM diff 复用组件实例的根因。",
            "wrongCount": 4,
            "mastered": False,
            "diagnosis": "你的修复方向会增加额外同步逻辑，但根因是 key 不稳定，排序后同一个 index 已经代表另一条业务数据。",
            "concept": "key 是组件身份标识，不是循环序号；业务 id 才能在重排后保持组件状态和数据项绑定。",
            "practice": "写一个删除中间项的最小复现，比较 :key='index' 与 :key='item.id' 时输入框状态的差异。",
        },
        {
            "title": "团队 PR 只描述实现未描述自测结果",
            "subject": "软件工程综合实训",
            "type": "实践题",
            "tags": ["Git", "Pull Request", "协作"],
            "studentAnswer": "PR 说明写清楚新增了哪些接口和页面即可，自测命令可以等老师问到时再补充在评论区。",
            "correctAnswer": "PR 描述应固定包含变更范围、自测命令、关键截图或接口结果、影响页面、风险边界和待确认问题，便于队长与教师快速 review。",
            "reason": "把 PR 当成提交说明，忽略了它是团队协作和质量审查入口，缺少可验证证据。",
            "wrongCount": 2,
            "mastered": False,
            "diagnosis": "你的 PR 能说明做了什么，但不能让 reviewer 快速判断是否验证过、影响哪里、风险在哪里。",
            "concept": "高质量 PR 描述是审查协议，既写实现，也写验证证据和边界。",
            "practice": "按模板重写一个 PR：变更范围、自测命令、截图/接口返回、风险、待确认项各至少一条。",
        },
    ]

    result: list[dict[str, Any]] = []
    for index, spec in enumerate(specs, start=1):
        last_wrong_at = _ts(now, max(0, 9 - index), 19, 8 + index)
        result.append(
            {
                "id": f"{TARGET_PREFIX}-mistake-{index:02d}",
                "studentId": TARGET_USER_ID,
                "studentName": TARGET_REAL_NAME,
                "className": TARGET_CLASS_NAME,
                "examId": f"{TARGET_PREFIX}-exam-review",
                "examTitle": "课程项目综合复盘测验",
                "subject": spec["subject"],
                "questionId": f"showcase-q-{index:02d}",
                "questionType": spec["type"],
                "questionTitle": spec["title"],
                "studentAnswer": spec["studentAnswer"],
                "correctAnswer": spec["correctAnswer"],
                "errorReason": spec["reason"],
                "knowledgeTags": spec["tags"],
                "wrongCount": spec["wrongCount"],
                "lastWrongAt": last_wrong_at,
                "mastered": spec["mastered"],
                "aiAnalysis": _analysis(spec["tags"], spec["diagnosis"], spec["concept"], spec["practice"]),
                "source": {
                    "type": "exam" if index % 2 == 0 else "homework",
                    "title": "课程项目综合复盘测验",
                },
                "createdAt": last_wrong_at,
                "updatedAt": last_wrong_at,
            }
        )
    return result
