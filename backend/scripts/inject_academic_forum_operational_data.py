import json
import os
import random
import re
import shutil
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymysql


DATA_DIR_NAME = "\u8f6f\u4ef6\u676f\u6d4b\u8bd5\u6570\u636e\u6ce8\u5165"
NAMES_FILE_NAME = "\u5b66\u751f\u59d3\u540d.txt"
AVATAR_DIR_NAME = "\u5934\u50cf"
TZ = timezone(timedelta(hours=8))
BASE_DATE = datetime(2026, 7, 5, 18, 30, tzinfo=TZ)
RANDOM = random.Random(20260705)


CATEGORY_LABELS = {
    "qna": "课程答疑",
    "competition": "竞赛交流",
    "experience": "经验分享",
    "chat": "日常闲聊",
}


POST_SPECS = [
    {
        "category": "qna",
        "title": "B+ 树范围查询为什么一定要把叶子节点串起来？",
        "content": "复习数据库和数据结构交叉内容时有点卡住：B+ 树内部节点只放索引，叶子节点放数据指针，这个我能理解。但很多资料都强调叶子节点之间要用链表连接。我的理解是范围查询时先定位到起点叶子，然后顺着链表扫，不用反复回到根节点。这个理解对吗？如果是磁盘页存储，链表顺序扫描是不是还能减少随机 I/O？",
        "tags": ["数据结构", "B+树", "数据库索引"],
        "seed_day": 29,
        "hour": 10,
    },
    {
        "category": "qna",
        "title": "红黑树插入修复里叔叔节点为红色时到底在维护什么？",
        "content": "红黑树插入的三种情况我能背，但到手写代码时经常不知道为什么要把父节点和叔叔节点染黑、祖父节点染红。是不是本质上在把局部的红色冲突往上推，同时保持每条路径黑高不变？有没有同学能用 2-3-4 树的视角解释一下，感觉那样可能更好记。",
        "tags": ["红黑树", "数据结构", "算法"],
        "seed_day": 28,
        "hour": 16,
    },
    {
        "category": "qna",
        "title": "计组 Cache 写回法和写直达法在题目里怎么区分脏位变化？",
        "content": "计算机组成原理做 Cache 题时，写命中之后到底要不要立刻访问主存，我总是容易混。写直达是 Cache 和主存同时更新，写回法只改 Cache 并置 dirty bit，替换时再写回。可是遇到写分配和非写分配一起出现时就乱了。大家有没有一套稳定的判断流程？",
        "tags": ["计算机组成原理", "Cache", "脏位"],
        "seed_day": 27,
        "hour": 14,
    },
    {
        "category": "qna",
        "title": "流水线数据冒险里 forwarding 和 stall 的边界怎么判断？",
        "content": "计组流水线那章，RAW 冒险里有些题说可以通过 forwarding 解决，有些又必须插入气泡。我现在的判断是：如果生产结果在下一条指令 EX 阶段前已经可用，就能旁路；load-use 因为数据到 MEM 末尾才出来，所以紧跟的下一条必须停一个周期。这个说法有没有漏洞？",
        "tags": ["计组", "流水线", "数据冒险"],
        "seed_day": 26,
        "hour": 19,
    },
    {
        "category": "qna",
        "title": "Transformer 里多头注意力为什么不是简单把维度复制几份？",
        "content": "人工智能课讲到 Multi-Head Attention，我以前以为多个头就是把同一个 QKV 算几遍。后来发现每个头都有独立的线性投影，关注的子空间可能不同。想问下在实际项目里，多头数是不是越多越好？如果 head_dim 太小，会不会反而学不到足够的信息？",
        "tags": ["人工智能", "Transformer", "注意力机制"],
        "seed_day": 25,
        "hour": 11,
    },
    {
        "category": "qna",
        "title": "A* 搜索的启发函数为什么必须不能高估？",
        "content": "AI 课的路径搜索实验里，老师说 admissible heuristic 不能高估真实代价，这样 A* 才能保证最优。我大概能理解为不要过早排除最优路径，但写实验报告时解释不够清楚。曼哈顿距离用于四方向网格为什么是安全的？如果地图里有传送门或者不同地形代价，是不是就要重新设计启发函数？",
        "tags": ["人工智能", "A*", "搜索算法"],
        "seed_day": 23,
        "hour": 15,
    },
    {
        "category": "competition",
        "title": "蓝桥杯省赛 DP 题总是想不到状态，怎么训练比较有效？",
        "content": "刷蓝桥杯真题时，感觉模拟和枚举还能靠细心做出来，DP 题经常连状态都定义不出来。尤其是带限制条件的序列问题，样例看懂了但推不出转移。大家备赛时是按题型刷，还是先系统学背包、区间、数位这些模板？有没有推荐的训练顺序？",
        "tags": ["蓝桥杯", "动态规划", "备赛"],
        "seed_day": 22,
        "hour": 20,
    },
    {
        "category": "competition",
        "title": "CCCC 天梯赛 L2 题如何在 30 分钟内稳定拿分？",
        "content": "上次模拟赛 L1 做完还挺顺，到了 L2 就开始卡时间。L2 有些题不难，但输入输出细节和边界条件很磨人。我现在想把目标定成 L2 稳定拿 2-3 题，不追求全 AK。大家比赛时会先读完所有 L2 再选题，还是按顺序硬刚？",
        "tags": ["CCCC", "天梯赛", "比赛策略"],
        "seed_day": 21,
        "hour": 18,
    },
    {
        "category": "competition",
        "title": "中国软件杯项目里 RAG 模块怎么避免答非所问？",
        "content": "我们组软件杯做的是课程智能助手，接了向量库之后发现一个问题：用户问“B+ 树范围查询”，检索出来有时候混进红黑树或者普通二叉搜索树的资料，回答就跑偏。现在想在 query rewrite、metadata filter 和 rerank 之间做取舍。有没有同学做过类似项目，工程上怎么比较稳？",
        "tags": ["中国软件杯", "RAG", "向量检索"],
        "seed_day": 20,
        "hour": 13,
    },
    {
        "category": "competition",
        "title": "比赛项目从 Flask 换 FastAPI，接口文档和类型校验确实省事吗？",
        "content": "团队项目最开始用 Flask 写原型，路由简单但请求体校验全靠自己判断。最近准备换 FastAPI，看中的是 Pydantic 和自动 OpenAPI 文档。不过担心迁移成本，尤其是权限中间件和异常返回格式。做过比赛后端的同学，FastAPI 在演示和联调阶段体验怎么样？",
        "tags": ["后端框架", "FastAPI", "项目联调"],
        "seed_day": 18,
        "hour": 17,
    },
    {
        "category": "competition",
        "title": "ACM 队内训练时，图论题该先补最短路还是并查集？",
        "content": "我们三个人准备暑假组队刷区域赛基础题，图论这一块分工还没定。我个人会 Dijkstra 和 Floyd，但对最小生成树、强连通分量不熟。队友建议先把并查集、拓扑排序、最短路这些高频内容打牢。大家觉得图论训练怎么排优先级更合理？",
        "tags": ["ACM", "图论", "组队训练"],
        "seed_day": 17,
        "hour": 9,
    },
    {
        "category": "competition",
        "title": "比赛展示时前端可视化要做到什么程度才不显得花架子？",
        "content": "软件杯答辩准备阶段，老师说我们的功能能跑，但展示页面缺少“系统已经运营过”的感觉。我们想加学习路径图、错题趋势、论坛热议这些可视化。问题是时间有限，怕做太多动效反而不稳。大家答辩时更看重真实数据闭环，还是页面冲击力？",
        "tags": ["软件杯", "前端可视化", "答辩"],
        "seed_day": 16,
        "hour": 15,
    },
    {
        "category": "experience",
        "title": "链表题最容易错的不是指针，而是边界条件",
        "content": "最近集中刷链表，发现自己出错最多的不是反转逻辑，而是空链表、单节点、头节点被删这些边界。后来统一加 dummy head，所有删除和插入都从 prev/curr 两个指针开始，代码一下稳定很多。尤其是删除倒数第 N 个节点，dummy 真的能少掉一堆 if。",
        "tags": ["链表", "刷题经验", "边界条件"],
        "seed_day": 15,
        "hour": 12,
    },
    {
        "category": "experience",
        "title": "项目接口联调时，先写契约文档比口头约定靠谱太多",
        "content": "这周和前端联调作业管理模块，刚开始大家在群里说字段名，结果 `studentName`、`student_name`、`name` 三套混着出现。后来我们把接口契约写成 Markdown，明确请求体、响应体、错误码和状态枚举，再配一个 Postman 集合，联调效率直接提高。比赛项目真不建议边写边猜字段。",
        "tags": ["项目经验", "接口契约", "前后端联调"],
        "seed_day": 14,
        "hour": 10,
    },
    {
        "category": "experience",
        "title": "调递归题时先画调用树，比盯着代码有效",
        "content": "递归回溯题我以前总是靠脑补，越想越乱。后来改成先画调用树，把参数、选择列表和撤销操作写在每一层，尤其是全排列、组合总和这种题，错误基本都能定位到“没有 pop 回去”或者“剪枝条件写早了”。这个方法虽然慢，但对理解很有帮助。",
        "tags": ["递归", "回溯", "调试方法"],
        "seed_day": 13,
        "hour": 19,
    },
    {
        "category": "experience",
        "title": "MySQL 慢查询不是只加索引，先看执行计划",
        "content": "我们课程项目有个排行榜接口，数据一多就慢。刚开始想当然给所有查询字段都加索引，结果写入变慢还没解决核心问题。后来用 EXPLAIN 看，发现 ORDER BY + WHERE 没走到合适的联合索引。调整成 `(course_id, score)` 后才明显改善。索引不是越多越好，顺序也很关键。",
        "tags": ["MySQL", "慢查询", "项目优化"],
        "seed_day": 12,
        "hour": 16,
    },
    {
        "category": "experience",
        "title": "把错题按知识点归档，比单纯收藏题目更有用",
        "content": "期末复习数据结构时，我把错题分成“树旋转”“哈希冲突”“图遍历”“复杂度分析”几类，每类只保留代表题和自己的错因。这样复盘时不会被题量淹没。尤其是复杂度分析，很多题表面不一样，底层都是循环次数和递归式。",
        "tags": ["学习方法", "错题复盘", "数据结构"],
        "seed_day": 11,
        "hour": 11,
    },
    {
        "category": "experience",
        "title": "AI 实验调参别一次改三个变量，否则根本不知道谁生效",
        "content": "做分类实验时我一开始同时改学习率、batch size 和 dropout，准确率波动很大，完全判断不出原因。后来每次只改一个变量，并且固定随机种子，记录训练曲线和验证集指标，才看出学习率过大导致 loss 抖动。感觉机器学习实验最重要的是可复现。",
        "tags": ["人工智能", "实验记录", "调参"],
        "seed_day": 10,
        "hour": 14,
    },
    {
        "category": "qna",
        "title": "哈希表开放寻址删除元素为什么不能直接置空？",
        "content": "数据结构课讲开放寻址法，插入和查找我都懂，但删除时老师说不能直接把槽位置空，要标记 deleted。是不是因为后面的元素可能是因为冲突才探测到更远位置，如果中间断开，查找会提前停止？那 deleted 标记太多以后，查找性能是不是会下降，需要重建表吗？",
        "tags": ["哈希表", "开放寻址", "数据结构"],
        "seed_day": 9,
        "hour": 20,
    },
    {
        "category": "competition",
        "title": "蓝桥杯填空题用 Python 暴力，怎样避免精度和时间坑？",
        "content": "蓝桥杯填空题很多可以本地写脚本暴力出答案，但我踩过浮点精度和运行时间的坑。比如日期枚举、组合计数还好，遇到大数或者概率就容易不稳。大家比赛前会准备哪些 Python 小模板？我现在只整理了日期、质数筛、组合数和高精度 Decimal。",
        "tags": ["蓝桥杯", "Python", "填空题"],
        "seed_day": 8,
        "hour": 13,
    },
    {
        "category": "chat",
        "title": "图书馆三楼靠窗位置是不是默认被考研同学承包了？",
        "content": "最近想找个安静地方看计组，发现三楼靠窗位置每天上午十点前就满了，桌上全是厚厚的书和水杯。二楼讨论区又有点吵。大家平时复习专业课都在哪儿？有没有既能插电又不太吵的位置推荐？",
        "tags": ["校园生活", "复习", "自习地点"],
        "seed_day": 7,
        "hour": 10,
    },
    {
        "category": "chat",
        "title": "期末周写项目和复习考试撞车，大家怎么排优先级？",
        "content": "软件工程项目验收和数据结构期末挤在同一周，感觉每天都在切上下文。上午写接口，下午背红黑树，晚上还要改 PPT。现在最大问题是项目一有 bug 就会打断复习节奏。大家有没有比较现实的时间安排方法？",
        "tags": ["期末周", "项目验收", "时间管理"],
        "seed_day": 6,
        "hour": 18,
    },
    {
        "category": "chat",
        "title": "有没有人想组一个暑假算法打卡小队？",
        "content": "暑假不想完全躺平，准备每天刷 1-2 道算法题，从数组、链表、栈队列开始，再到树、图、动态规划。一个人坚持很难，想找几个人互相监督，每天在论坛发一下题号和一句复盘。目标不是卷排名，就是保持手感。",
        "tags": ["算法打卡", "暑假计划", "组队"],
        "seed_day": 5,
        "hour": 21,
    },
    {
        "category": "experience",
        "title": "用 Git 分支开发时，提交信息写清楚真的能救命",
        "content": "团队项目最近合并分支，发现有些 commit 叫 `fix`、`update`、`改一下`，根本看不出改了什么。后来统一成 `feat: 添加作业提交接口`、`fix: 修复空文件上传校验` 这种格式，回滚和 code review 都轻松很多。比赛项目时间越紧，越需要这些小规范。",
        "tags": ["Git", "团队协作", "项目规范"],
        "seed_day": 4,
        "hour": 15,
    },
    {
        "category": "qna",
        "title": "进程调度题里的响应时间和周转时间总算混，怎么记？",
        "content": "操作系统虽然不是这次论坛重点课，但复习计组时顺手看了 OS，发现调度算法题很容易把响应时间、等待时间、周转时间混起来。我的记法是：响应时间看第一次被 CPU 服务，周转时间看完成时间减到达时间，等待时间看就绪队列里等了多久。这个记法够用吗？",
        "tags": ["操作系统", "调度算法", "复习"],
        "seed_day": 3,
        "hour": 9,
    },
    {
        "category": "competition",
        "title": "软件杯答辩问到安全性，学生项目怎么回答比较扎实？",
        "content": "老师模拟答辩时问我们：如果有人伪造请求删除别人的帖子怎么办？我们现在只有简单登录态，还没做细粒度权限。准备补充 JWT 校验、接口级权限、操作日志和后端二次校验。大家比赛答辩被问到安全性时，一般会从哪些角度回答？",
        "tags": ["软件杯", "系统安全", "答辩准备"],
        "seed_day": 2,
        "hour": 16,
    },
]


COMMENT_BANK = {
    "qna": [
        "我一般先把概念翻译成“数据什么时候可用、谁依赖谁”。题目里只要抓住这个关系，很多细节就不会散。",
        "这个问题可以配合一张小图来看，尤其是把每一步状态变化写出来，比直接背结论稳很多。",
        "老师上课提过类似思路：先判断约束条件，再看它破坏了哪条性质，最后选择最小修改恢复性质。",
        "建议你把一两个典型题完整推一遍，不要只看答案。推导过程里容易暴露真正没理解的点。",
        "如果是考试题，最好把关键词写清楚，比如命中、替换、黑高、启发函数这些，阅卷老师看逻辑会更明确。",
        "我之前也卡在这里，后来发现不是公式难，是场景没分清。先区分读/写、命中/不命中、是否替换，会清楚很多。",
    ],
    "competition": [
        "比赛里不要追求一开始就写最优解，先写一个能过小数据的版本，很多时候能帮你确认状态和边界。",
        "我们队训练时会给每题设置止损时间，超过 25 分钟没思路就换人讲题，避免三个人同时坐牢。",
        "工程比赛更看重闭环，评委问的时候能说清楚数据来源、处理过程和异常兜底，比单纯炫技术更有说服力。",
        "建议把 demo 流程写成脚本，每一步谁点击、谁讲、异常怎么处理都排练一遍，现场少很多事故。",
        "算法竞赛这块我觉得题后复盘比刷题数量重要，同一类错三次就要整理模板和反例。",
        "框架选择别只看新不新，比赛最怕现场跑不起来。能稳定部署、接口清楚、日志能查，才是最实用的。",
    ],
    "experience": [
        "这个经验很真实。很多 bug 不是算法不会，而是没有把输入边界和状态变化写清楚。",
        "我现在也会保留一份问题记录：现象、原因、解决办法、下次怎么预防。复盘多了以后排错速度会明显变快。",
        "团队项目里规范看起来麻烦，但等到多人并行和临近验收时，就会发现它是在节省沟通成本。",
        "建议把这个整理成 checklist，之后写同类代码前先过一遍，能少踩很多重复坑。",
        "我补充一点：不要只看最终结果，过程指标也要记录。比如 SQL 的执行计划、训练曲线、接口耗时都很有用。",
        "这种方法适合长期坚持，短期看慢，但期末或者答辩前复盘时会非常省时间。",
    ],
    "chat": [
        "我一般把上午留给需要脑子的内容，下午处理项目杂事，晚上做一点复盘，不然一天都在切任务很累。",
        "可以试试预约靠近墙边的位置，插电方便一点。实在找不到位置的话，空教室其实也挺适合背专业课。",
        "组队打卡可以，但建议规则简单一点，每天题号加一句错因就够了，太复杂容易坚持不下去。",
        "期末周最怕临时加需求，项目这边最好先冻结功能，只修 bug，不然复习节奏会被打碎。",
        "我觉得保持稳定比突然爆肝重要。每天固定两个时间段学习，比熬到半夜效率高很多。",
        "可以把论坛当成轻量复盘区，今天踩的坑写一句，后面别人搜到也能少走弯路。",
    ],
}


def connect():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", "root"),
        database=os.getenv("DB_NAME", "Software_Cup"),
        charset="utf8mb4",
        autocommit=False,
    )


def find_injection_dir() -> Path:
    target_name = DATA_DIR_NAME
    for item in Path("D:/").iterdir():
        if item.name == target_name:
            return item
    raise FileNotFoundError(f"Injection directory not found: D:/{target_name}")


def parse_student_names(data_dir: Path) -> list[str]:
    text = (data_dir / NAMES_FILE_NAME).read_text(encoding="utf-8")
    names: list[str] = []
    for line in text.splitlines():
        match = re.match(r"\s*\d+\.\s*(\S+)", line)
        if match:
            names.append(match.group(1).strip())
    return names


def avatar_files(data_dir: Path) -> list[Path]:
    avatar_dir = data_dir / AVATAR_DIR_NAME
    files = [p for p in avatar_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]

    def sort_key(path: Path):
        match = re.search(r"\((\d+)\)", path.name)
        return (int(match.group(1)) if match else 9999, path.name)

    return sorted(files, key=sort_key)


def ensure_static_avatars(data_dir: Path, users: list[dict]) -> None:
    files = avatar_files(data_dir)
    static_dir = Path(__file__).resolve().parents[1] / "app" / "static" / "avatars"
    static_dir.mkdir(parents=True, exist_ok=True)
    for index, user in enumerate(users):
        target = static_dir / user["avatar_path"]
        if target.exists() or index >= len(files):
            continue
        shutil.copyfile(files[index], target)


def load_users(cur) -> list[dict]:
    cur.execute(
        """
        SELECT username, real_name, student_id, class_name, avatar_path
        FROM user_accounts
        WHERE role='student'
        ORDER BY username
        """
    )
    users = []
    static_dir = Path(__file__).resolve().parents[1] / "app" / "static" / "avatars"
    for username, real_name, student_id, class_name, avatar_path in cur.fetchall():
        username = str(username or "").strip()
        real_name = str(real_name or "").strip()
        avatar_path = str(avatar_path or "").strip()
        if not re.fullmatch(r"202300\d{2}", username):
            continue
        if not real_name or "?" in real_name or not avatar_path:
            continue
        if not (static_dir / avatar_path).exists():
            continue
        users.append(
            {
                "username": username,
                "real_name": real_name,
                "student_id": str(student_id or username).strip() or username,
                "class_name": str(class_name or "").strip(),
                "avatar_path": avatar_path,
                "avatar": f"/static/avatars/{avatar_path}",
            }
        )
    if len(users) < 10:
        raise RuntimeError(f"Not enough valid forum users: {len(users)}")
    return users


def load_existing_posts(cur) -> tuple[set[tuple[str, str]], set[str]]:
    cur.execute("SELECT record_key, payload FROM domain_records WHERE module='forum' AND record_type='post'")
    signatures: set[tuple[str, str]] = set()
    keys: set[str] = set()
    for record_key, payload in cur.fetchall():
        keys.add(record_key)
        try:
            data = json.loads(payload or "{}")
        except json.JSONDecodeError:
            continue
        signatures.add(((data.get("title") or "").strip(), (data.get("content") or "").strip()))
    return signatures, keys


def pick_time(seed_day: int, hour: int, minute_offset: int = 0) -> datetime:
    minute = (seed_day * 7 + minute_offset * 11) % 50 + 5
    return (BASE_DATE - timedelta(days=seed_day)).replace(hour=hour, minute=minute, second=0, microsecond=0)


def iso(dt: datetime) -> str:
    return dt.isoformat()


def make_replies(post_id: str, author: dict, category: str, post_time: datetime, users: list[dict]) -> list[dict]:
    candidates = [u for u in users if u["username"] != author["username"]]
    commenters = RANDOM.sample(candidates, 5)
    snippets = RANDOM.sample(COMMENT_BANK[category], 5)
    replies = []
    for index, (commenter, content) in enumerate(zip(commenters, snippets), start=1):
        reply_time = post_time + timedelta(hours=2 + index * RANDOM.randint(2, 5), minutes=RANDOM.randint(6, 54))
        if reply_time.hour >= 23 or reply_time.hour < 8:
            reply_time = (reply_time + timedelta(days=1)).replace(hour=9 + index, minute=RANDOM.randint(8, 49))
        replies.append(
            {
                "id": f"{post_id}-reply-{index}",
                "author": commenter["real_name"],
                "authorUsername": commenter["username"],
                "avatar": commenter["avatar"],
                "isAi": False,
                "content": content,
                "createdAt": iso(reply_time),
                "likes": RANDOM.randint(2, 19),
            }
        )
    return replies


def build_posts(users: list[dict], existing_signatures: set[tuple[str, str]], existing_keys: set[str]) -> list[dict]:
    posts = []
    for index, spec in enumerate(POST_SPECS, start=1):
        signature = (spec["title"].strip(), spec["content"].strip())
        if signature in existing_signatures:
            continue
        author = users[(index * 5 + spec["seed_day"]) % len(users)]
        post_time = pick_time(spec["seed_day"], spec["hour"], index)
        post_id = f"ops-post-{post_time.strftime('%Y%m%d')}-{index:02d}-{uuid.uuid4().hex[:6]}"
        while post_id in existing_keys:
            post_id = f"ops-post-{post_time.strftime('%Y%m%d')}-{index:02d}-{uuid.uuid4().hex[:6]}"
        replies = make_replies(post_id, author, spec["category"], post_time, users)
        post = {
            "id": post_id,
            "title": spec["title"],
            "content": spec["content"],
            "author": author["real_name"],
            "authorUsername": author["username"],
            "avatar": author["avatar"],
            "category": spec["category"],
            "categoryLabel": CATEGORY_LABELS[spec["category"]],
            "tags": spec["tags"],
            "likes": RANDOM.randint(12, 73),
            "isLiked": False,
            "views": RANDOM.randint(96, 920),
            "createdAt": iso(post_time),
            "replies": replies,
            "isPinned": False,
        }
        posts.append({"record_key": post_id, "owner_id": author["username"], "created_at": post_time, "payload": post})
    return posts


def upsert_hot_topics(cur, posts: list[dict]) -> None:
    tag_counts = Counter()
    for item in posts:
        for tag in item["payload"].get("tags") or []:
            tag_counts[tag] += 1
    for tag, count in tag_counts.most_common(12):
        payload = {"id": tag, "tag": tag, "count": 12 + count * 4}
        cur.execute(
            "DELETE FROM domain_records WHERE module='forum' AND record_type='hot_topic' AND record_key=%s",
            (tag,),
        )
        cur.execute(
            """
            INSERT INTO domain_records (module, record_type, record_key, owner_id, role, status, payload, created_at, updated_at)
            VALUES ('forum', 'hot_topic', %s, '', '', 'active', %s, NOW(), NOW())
            """,
            (tag, json.dumps(payload, ensure_ascii=False)),
        )


def insert_posts(cur, posts: list[dict]) -> None:
    for item in posts:
        payload = json.dumps(item["payload"], ensure_ascii=False)
        naive_time = item["created_at"].replace(tzinfo=None)
        cur.execute(
            """
            INSERT INTO domain_records (module, record_type, record_key, owner_id, role, status, payload, created_at, updated_at)
            VALUES ('forum', 'post', %s, %s, 'student', 'published', %s, %s, %s)
            """,
            (item["record_key"], item["owner_id"], payload, naive_time, naive_time),
        )


def main() -> None:
    data_dir = find_injection_dir()
    names = parse_student_names(data_dir)
    avatars = avatar_files(data_dir)
    if len(names) < 31 or len(avatars) < 31:
        raise RuntimeError(f"Injection assets incomplete: names={len(names)}, avatars={len(avatars)}")

    conn = connect()
    try:
        cur = conn.cursor()
        users = load_users(cur)
        ensure_static_avatars(data_dir, users)
        existing_signatures, existing_keys = load_existing_posts(cur)
        posts = build_posts(users, existing_signatures, existing_keys)
        if len(posts) < 20:
            cur.execute("SELECT COUNT(*) FROM domain_records WHERE module='forum' AND record_type='post' AND record_key LIKE 'ops-post-%'")
            existing_ops_posts = int(cur.fetchone()[0])
            if existing_ops_posts >= 20 and not posts:
                print(
                    json.dumps(
                        {
                            "inserted_posts": 0,
                            "existing_ops_posts": existing_ops_posts,
                            "valid_users": len(users),
                            "names": len(names),
                            "avatars": len(avatars),
                            "status": "already_seeded",
                        },
                        ensure_ascii=False,
                    )
                )
                return
            raise RuntimeError(f"Need at least 20 new non-duplicate posts, got {len(posts)}")
        insert_posts(cur, posts)
        upsert_hot_topics(cur, posts)
        conn.commit()
        print(json.dumps({"inserted_posts": len(posts), "valid_users": len(users), "names": len(names), "avatars": len(avatars)}, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
