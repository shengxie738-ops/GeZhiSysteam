"""为演示账号 23001020119（谢渝）注入"能力协同六维图谱"真实后端数据。

数据全部写入 MySQL（domain_records / student_profiles / user_accounts），
与前端真实 API（/analytics/students/me 同源 _compute_radar_values）保持一致：
  1. 作业提交：13 个 daily Checkpoint 全部完成 + milestone + capstone，带三智能体诊断分
  2. 考试成绩：期中 / 闭卷 / 上机三场真实考试记录
  3. 错题本：旧错题补复习记录标记已掌握，仅保留 1 条近期新错
  4. 学术论坛：补充 7 帖 + 2 回复，凑成 8 帖 4 回（活跃度 100）
  5. 学生画像：知识基础 / 学习步调提升为优秀学生水平
幂等：全部使用固定 record_key upsert，可重复执行。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore

TARGET_USER_ID = "23001020119"
TARGET_REAL_NAME = "谢渝"
TARGET_CLASS_NAME = "23006"
CHINA_TZ = timezone(timedelta(hours=8))


def _ts(month: int, day: int, hour: int, minute: int) -> str:
    return datetime(2026, month, day, hour, minute, tzinfo=CHINA_TZ).isoformat()


# ---------------------------------------------------------------------------
# 1. 作业提交（13 daily + 1 milestone + 1 capstone）
#    grade: 14A + 1B(attention milestone 推导扣分)，诊断分均值 alina≈89 / ninja≈90 / profx≈87
# ---------------------------------------------------------------------------

def _diag(alina: int, ninja: int, profx: int, a: str, n: str, p: str, at: str) -> dict[str, Any]:
    return {
        "scores": {"alina": alina, "codeninja": ninja, "profx": profx},
        "alinaMsg": a,
        "codeninjaMsg": n,
        "profxMsg": p,
        "generatedAt": at,
        "source": "ai",
    }


HOMEWORK_SUBMISSIONS: list[dict[str, Any]] = [
    {
        "homeworkId": "demo-hw-se-pr-review",
        "submittedAt": _ts(6, 23, 21, 14),
        "grade": "A",
        "answers": {
            "q1": "验收清单：1) GET /api/repositories 返回字段与契约一致；2) 分页参数越界时返回空列表而非 500；3) 未认证请求返回 401；4) 单元测试覆盖 service 层分支；5) PR 描述包含变更范围与自测结果。",
            "q2": "补充了 repository service 的单元测试：空仓库列表、按 star 排序稳定性、下架项目过滤三个分支，使用 mock 数据隔离数据库。",
        },
        "file": "23001020119-demo-hw-se-pr-review.zip",
        "teacherComment": "验收清单把契约、鉴权、分页边界都列到了，PR 描述规范度是全班示范级。单元测试再补一个并发收藏的分支会更完整。",
        "scores": (88, 90, 86),
        "msgs": (
            "Alina诊断：目标拆解清晰，先契约后实现再自测的顺序值得保持。",
            "CodeNinja诊断：单测覆盖了主要分支，mock 边界干净；并发场景用例可以再补一组。",
            "Prof. X诊断：验收清单结构完整，把『变更范围』『自测结果』写进 PR 规范的理解到位。",
        ),
    },
    {
        "homeworkId": "demo-hw-co-cache",
        "submittedAt": _ts(6, 25, 20, 41),
        "grade": "A",
        "answers": {
            "q1": "冲突缺失",
            "q2": "按 32 位地址、直接映射、cache 共 64 行、块大小 16B 计算：offset 4 位，index 6 位，tag 取高 22 位。例：0x0000C120 → index 0x12(18)，tag 0x00030。",
        },
        "file": "23001020119-demo-hw-co-cache.zip",
        "teacherComment": "tag/index/offset 位拆解过程完整，二进制到十六进制的换算没有跳步。下次可以再标注一下映射后的命中组号。",
        "scores": (87, 89, 85),
        "msgs": (
            "Alina诊断：复习节奏稳定，作业在截止前一天完成，时间规划合理。",
            "CodeNinja诊断：位运算拆解逻辑正确，建议封装成可复用函数避免重复计算。",
            "Prof. X诊断：对地址三段划分的原理表述准确，可直接映射与组相联的对比再展开一句更好。",
        ),
    },
    {
        "homeworkId": "demo-hw-ai-attention",
        "submittedAt": _ts(6, 27, 16, 2),
        "grade": "B",
        "answers": {
            "q1": "避免 Softmax 过饱和",
            "q2": "设序列长度 n、嵌入维度 d_model、头数 h，则 Q∈R^{n×d_k}，K∈R^{n×d_k}（d_k=d_model/h），QK^T∈R^{n×n}；除以 sqrt(d_k) 后与 V（R^{n×d_v}）相乘，输出回到 R^{n×d_v}。",
        },
        "file": "23001020119-demo-hw-ai-attention.zip",
        "teacherComment": "维度推导第一步正确，但 QK^T 与 V 相乘的方向在草稿里写反了一次，订正时把每个矩阵的行列标出来再乘。缩放因子的直觉解释加分。",
        "scores": (84, 85, 81),
        "msgs": (
            "Alina诊断： milestone 作业完成度略有延迟，建议把推导类作业提前两天启动。",
            "CodeNinja诊断：矩阵维度标注习惯好，但乘法方向需再仔细，建议手推一遍再落笔。",
            "Prof. X诊断：对缩放因子防止点积过大导致梯度消失的理解正确，推导链路中间有跳步。",
        ),
    },
    {
        "homeworkId": "demo-hw-fe-reactive",
        "submittedAt": _ts(6, 29, 21, 33),
        "grade": "A",
        "answers": {
            "q1": "修复 getter this 指向",
            "q2": "track；trigger",
            "q3": "function reactive(obj) {\n  return new Proxy(obj, {\n    get(target, key, receiver) {\n      track(target, key);\n      return Reflect.get(target, key, receiver);\n    },\n    set(target, key, value, receiver) {\n      const old = target[key];\n      const ok = Reflect.set(target, key, value, receiver);\n      if (ok && old !== value) trigger(target, key);\n      return ok;\n    }\n  });\n}",
        },
        "file": "23001020119-demo-hw-fe-reactive.zip",
        "teacherComment": "最小 reactive 实现里保留了 receiver 和旧值判断，这两个细节大多数同学都漏了。依赖收集用 WeakMap 嵌套可以再优化。",
        "scores": (89, 91, 87),
        "msgs": (
            "Alina诊断：作业按时完成，前端专题的学习曲线把握平稳。",
            "CodeNinja诊断：Proxy + Reflect 组合使用规范，新旧值比较避免了无谓触发，代码质量高。",
            "Prof. X诊断：对 track/trigger 时机的解释准确，effect 嵌套场景的表述可以再补充。",
        ),
    },
    {
        "homeworkId": "demo-hw-db-index-join",
        "submittedAt": _ts(7, 1, 19, 52),
        "grade": "A",
        "answers": {
            "q1": "叶子节点",
            "q2": "覆盖索引把查询需要的字段全部放进索引叶子节点，扫描索引即可返回结果，不需要再按主键回聚簇索引取整行，因此减少回表。",
            "q3": "SELECT s.student_id, s.name, sc.score\nFROM scores sc\nJOIN students s ON s.student_id = sc.student_id\nWHERE sc.course_id = 'DS'\nORDER BY sc.score DESC\nLIMIT 10;",
        },
        "file": "23001020119-demo-hw-db-index-join.zip",
        "teacherComment": "覆盖索引解释抓住了『免回表』的本质，Top-N 查询里 ORDER BY + LIMIT 与索引序的配合如果能点出就更好。",
        "scores": (88, 90, 88),
        "msgs": (
            "Alina诊断：数据库专题连续两次作业质量稳定，可进入索引优化进阶内容。",
            "CodeNinja诊断：SQL 书写规范，JOIN 顺序合理；建议对 course_id 建复合索引并说明原因。",
            "Prof. X诊断：回表机制的因果链描述完整，B+ 树叶子链表与范围扫描的联系表述到位。",
        ),
    },
    {
        "homeworkId": "demo-hw-ds-linked-stack",
        "submittedAt": _ts(7, 3, 20, 18),
        "grade": "A",
        "answers": {
            "q1": "避免节点丢失",
            "q2": "栈",
            "q3": "ListNode reverseList(ListNode head) {\n    ListNode prev = null, curr = head;\n    while (curr != null) {\n        ListNode next = curr.next;\n        curr.next = prev;\n        prev = curr;\n        curr = next;\n    }\n    return prev;\n}",
        },
        "file": "23001020119-demo-hw-ds-linked-stack.zip",
        "teacherComment": "迭代反转的三指针推进写得很干净，先存 next 再改指向的顺序完全正确。建议再补一个递归版对比空间开销。",
        "scores": (90, 92, 89),
        "msgs": (
            "Alina诊断：链表专题的目标推进顺利，错误率明显低于上一章节。",
            "CodeNinja诊断：边界处理（空表、单节点）完整，变量命名清晰，无冗余操作。",
            "Prof. X诊断：对指针修改顺序与节点丢失因果的表述准确，递归调用栈的联系理解到位。",
        ),
    },
    {
        "homeworkId": "hw-1783166758091-1aa25a4a",
        "submittedAt": _ts(7, 5, 19, 26),
        "grade": "A",
        "answers": {},
        "file": "23001020119-hw-binary-tree.zip",
        "teacherComment": "二叉树作业提交完整，四种遍历的迭代实现都过了用例。层序遍历里用 size 标记每层节点数的技巧掌握得不错。",
        "scores": (91, 90, 88),
        "msgs": (
            "Alina诊断：周末前完成作业，学习节奏稳定。",
            "CodeNinja诊断：遍历实现均通过全部用例，队列与栈的使用选择合理。",
            "Prof. X诊断：遍历序列与树结构的对应关系理解扎实。",
        ),
    },
    {
        "homeworkId": "target-teacher-su-hw-ds-stack-queue",
        "submittedAt": _ts(7, 14, 19, 8),
        "grade": "A",
        "answers": {"q1": "后进先出", "q2": "先进先出（FIFO）"},
        "file": "23001020119-target-teacher-su-hw-ds-stack-queue.zip",
        "teacherComment": "概念题全对。备注里补充的循环队列判满条件说明看得出课后有延伸阅读。",
        "scores": (89, 90, 87),
        "msgs": (
            "Alina诊断：随堂练习完成迅速，基础概念巩固良好。",
            "CodeNinja诊断：作答简洁准确，无多余表述。",
            "Prof. X诊断：栈与队列的访问规则表述规范。",
        ),
    },
    {
        "homeworkId": "target-teacher-su-hw-db-index",
        "submittedAt": _ts(7, 15, 20, 22),
        "grade": "A",
        "answers": {"q1": "叶子节点", "q2": "覆盖索引"},
        "file": "23001020119-target-teacher-su-hw-db-index.zip",
        "teacherComment": "全对。结合上次作业的覆盖索引解释，这块知识已经形成闭环。",
        "scores": (90, 91, 89),
        "msgs": (
            "Alina诊断：数据库索引专题持续保持高正确率。",
            "CodeNinja诊断：概念转译准确，能结合实例说明。",
            "Prof. X诊断：对 B+ 树结构与索引命中路径的理解稳定。",
        ),
    },
    {
        "homeworkId": "target-teacher-su-hw-python-basic",
        "submittedAt": _ts(7, 16, 21, 47),
        "grade": "A",
        "answers": {"q1": "dict", "q2": "方括号 []"},
        "file": "23001020119-target-teacher-su-hw-python-basic.zip",
        "teacherComment": "基础扎实。dict 按键查找 O(1) 的原因（哈希表）在答案里主动做了说明，很好。",
        "scores": (91, 93, 90),
        "msgs": (
            "Alina诊断：Python 基础练习正确率 100%。",
            "CodeNinja诊断：作答准确，主动补充底层实现原理的说明。",
            "Prof. X诊断：对哈希查找复杂度的理解到位。",
        ),
    },
    {
        "homeworkId": "target-teacher-su-hw-network-http",
        "submittedAt": _ts(7, 17, 19, 31),
        "grade": "A",
        "answers": {"q1": "资源未找到", "q2": "POST"},
        "file": "23001020119-target-teacher-su-hw-network-http.zip",
        "teacherComment": "全对。对 401 与 404 的区别在自测记录里做了区分说明。",
        "scores": (88, 89, 86),
        "msgs": (
            "Alina诊断：网络专题练习按时完成。",
            "CodeNinja诊断：状态码语义理解准确。",
            "Prof. X诊断：REST 语义与请求方法的对应关系表述正确。",
        ),
    },
    {
        "homeworkId": "target-teacher-su-hw-ai-attention",
        "submittedAt": _ts(7, 18, 20, 55),
        "grade": "A",
        "answers": {"q1": "避免 Softmax 过饱和", "q2": "QKV"},
        "file": "23001020119-target-teacher-su-hw-ai-attention.zip",
        "teacherComment": "相比 milestone 作业，这次缩放因子的推导已经完全理顺，能看到明显进步。",
        "scores": (87, 88, 85),
        "msgs": (
            "Alina诊断：对上一次 milestone 薄弱点完成了针对性补强。",
            "CodeNinja诊断：概念选择正确，公式推导复查通过。",
            "Prof. X诊断：QKV 各自的作用表述清楚，softmax 饱和问题理解到位。",
        ),
    },
    {
        "homeworkId": "target-teacher-su-hw-software-test",
        "submittedAt": _ts(7, 19, 21, 19),
        "grade": "A",
        "answers": {"q1": "验证最小功能单元行为", "q2": "风险点"},
        "file": "23001020119-target-teacher-su-hw-software-test.zip",
        "teacherComment": "结合团队项目 PR 写的自测说明很规范，把『变更范围/自测结果/风险点』三段式用起来了。",
        "scores": (90, 92, 88),
        "msgs": (
            "Alina诊断：工程实践专题与团队协作经验形成了联动。",
            "CodeNinja诊断：对最小功能单元边界的把握准确，测试粒度设计合理。",
            "Prof. X诊断：单元测试目标的表述无歧义，PR 规范理解完整。",
        ),
    },
    {
        "homeworkId": "target-teacher-su-hw-os-process",
        "submittedAt": _ts(7, 20, 19, 44),
        "grade": "A",
        "answers": {"q1": "地址空间", "q2": "信号量"},
        "file": "23001020119-target-teacher-su-hw-os-process.zip",
        "teacherComment": "全对。线程共享地址空间带来的同步问题，答案里举了计数器竞态的例子，理解深入。",
        "scores": (88, 89, 87),
        "msgs": (
            "Alina诊断：操作系统概念题正确率保持高位。",
            "CodeNinja诊断：竞态举例恰当，体现了工程直觉。",
            "Prof. X诊断：互斥锁与信号量的适用差异表述清楚。",
        ),
    },
    {
        "homeworkId": "target-teacher-su-hw-frontend-vue",
        "submittedAt": _ts(7, 21, 20, 37),
        "grade": "A",
        "answers": {"q1": "Proxy", "q2": "trigger"},
        "file": "23001020119-target-teacher-su-hw-frontend-vue.zip",
        "teacherComment": "与此前 reactive 手写实现呼应，Proxy 拦截与依赖收集已经完全掌握。",
        "scores": (89, 91, 88),
        "msgs": (
            "Alina诊断：前端响应式专题完成闭环，可进入组件化内容。",
            "CodeNinja诊断：track/trigger 概念转译准确无误。",
            "Prof. X诊断：对 Vue 3 响应式演进（defineProperty → Proxy）的动因理解到位。",
        ),
    },
]


def _seed_homework_submissions(store: JsonStore) -> int:
    for item in HOMEWORK_SUBMISSIONS:
        homework = store.get_payload("homework", "homework", item["homeworkId"]) or {}
        submission_id = f"{item['homeworkId']}:{TARGET_USER_ID}"
        alina, ninja, profx = item["scores"]
        payload = {
            "id": submission_id,
            "studentId": TARGET_USER_ID,
            "studentName": TARGET_REAL_NAME,
            "className": TARGET_CLASS_NAME,
            "homeworkId": item["homeworkId"],
            "homeworkTitle": homework.get("title", ""),
            "submittedAt": item["submittedAt"],
            "answers": item["answers"],
            "file": item["file"],
            "status": "graded",
            "grade": item["grade"],
            "teacherComment": item["teacherComment"],
            "diagnosis": _diag(alina, ninja, profx, *item["msgs"], at=item["submittedAt"]),
            "classInsight": "本次作业共性问题已经同步到错题本和教师学情决策台。",
            "questionResults": {key: True for key in item["answers"]},
            "gradedAt": item["submittedAt"],
        }
        store.upsert("homework", "submission", submission_id, payload, owner_id=TARGET_USER_ID, status="graded")
    return len(HOMEWORK_SUBMISSIONS)


# ---------------------------------------------------------------------------
# 2. 考试 attempts（真实考试：期中 / 数据库闭卷 / 上机）
# ---------------------------------------------------------------------------

EXAM_ATTEMPTS: list[dict[str, Any]] = [
    {
        "id": "demo-exam-ds-midterm:23001020119",
        "examId": "demo-exam-ds-midterm",
        "examTitle": "数据结构期中综合考试",
        "objectiveScore": 42,
        "maxObjectiveScore": 50,
        "programmingScore": 88,
        "totalScore": 86,
        "submittedAt": _ts(7, 5, 19, 42),
        "durationMinutes": 96,
        "summary": "客观题扣分集中在哈希冲突处理与 KMP next 数组两题；编程题链表反转与二叉树层序全过，Dijkstra 堆优化第 4 个用例超时后重写通过。",
    },
    {
        "id": "demo-exam-db-closed:23001020119",
        "examId": "demo-exam-db-closed",
        "examTitle": "数据库系统原理闭卷测验",
        "objectiveScore": 45,
        "maxObjectiveScore": 50,
        "totalScore": 90,
        "submittedAt": _ts(7, 8, 15, 36),
        "durationMinutes": 78,
        "summary": "范式判断与事务隔离级别全对，扣分点集中在可串行化调度的冲突边判定。",
    },
    {
        "id": "demo-exam-code-practical:23001020119",
        "examId": "demo-exam-code-practical",
        "examTitle": "计算机程序设计上机考试",
        "programmingScore": 92,
        "totalScore": 92,
        "submittedAt": _ts(8, 12, 20, 24),
        "durationMinutes": 141,
        "summary": "四道编程题通过三道半：滑动窗口最大值用单调队列 O(n) 解法拿到性能分，最后一题并查集只过 7/10 用例。",
    },
]


def _seed_exam_attempts(store: JsonStore) -> int:
    for item in EXAM_ATTEMPTS:
        payload = {
            **item,
            "studentId": TARGET_USER_ID,
            "studentName": TARGET_REAL_NAME,
            "className": TARGET_CLASS_NAME,
            "status": "graded",
        }
        store.upsert("exams", "attempt", item["id"], payload, owner_id=TARGET_USER_ID, status="graded")
    return len(EXAM_ATTEMPTS)


# ---------------------------------------------------------------------------
# 3. 错题本：旧错题补复习记录 → 已掌握；保留 1 条近期新错（wrongCount=1）
# ---------------------------------------------------------------------------

def _seed_mistake_mastery(store: JsonStore) -> dict[str, int]:
    mastered_updates = {
        "target-23001020119-mistake-01": (_ts(7, 14, 20, 12), 3),
        "target-23001020119-mistake-03": (_ts(7, 16, 21, 5), 2),
        "target-23001020119-mistake-04": (_ts(7, 18, 19, 48), 2),
        "target-23001020119-mistake-05": (_ts(7, 21, 20, 33), 3),
        "target-23001020119-mistake-07": (_ts(7, 24, 21, 9), 2),
    }
    mastered = 0
    for mistake_id, (mastered_at, review_count) in mastered_updates.items():
        payload = store.get_payload("exams", "mistake", mistake_id, owner_id=TARGET_USER_ID)
        if not payload:
            continue
        payload["mastered"] = True
        payload["masteredAt"] = mastered_at
        payload["reviewCount"] = review_count
        payload["updatedAt"] = mastered_at
        analysis = payload.get("aiAnalysis")
        if isinstance(analysis, dict):
            review_log = analysis.get("reviewLog")
            if not isinstance(review_log, list):
                review_log = []
            if not any(mastered_at[:10] in str(item) for item in review_log):
                review_log.append(
                    f"学生于 {mastered_at[:10]} 完成订正并二次通过同类题，确认掌握（复习 {review_count} 轮）。"
                )
            analysis["reviewLog"] = review_log
            analysis["masteredAt"] = mastered_at
            payload["aiAnalysis"] = analysis
        store.upsert("exams", "mistake", mistake_id, payload, owner_id=TARGET_USER_ID, status="active")
        mastered += 1

    # 最新一条错题（7/13 团队 PR 自测描述）保留为"待复习"的新错题
    fresh_id = "target-23001020119-mistake-08"
    payload = store.get_payload("exams", "mistake", fresh_id, owner_id=TARGET_USER_ID)
    if payload:
        payload["wrongCount"] = 1
        payload["updatedAt"] = _ts(8, 13, 19, 40)
        store.upsert("exams", "mistake", fresh_id, payload, owner_id=TARGET_USER_ID, status="active")
    return {"mastered": mastered, "keptFresh": 1}


# ---------------------------------------------------------------------------
# 4. 学术论坛：7 帖 + 在同学帖下 2 条回复（连同已有 1 帖 2 回复 → 8 帖 4 回 = 100）
# ---------------------------------------------------------------------------

def _reply(author: str, username: str, content: str, at: str, likes: int, reply_id: str) -> dict[str, Any]:
    return {
        "id": reply_id,
        "author": author,
        "authorUsername": username,
        "avatar": f"/static/avatars/{username}.jpg",
        "isAi": False,
        "content": content,
        "createdAt": at,
        "likes": likes,
    }


FORUM_POSTS: list[dict[str, Any]] = [
    {
        "id": "target-23001020119-forum-post-01",
        "title": "「整理」单链表反转的三种写法，各自的坑都在这了",
        "category": "share",
        "categoryLabel": "经验分享",
        "tags": ["数据结构", "链表"],
        "createdAt": _ts(6, 28, 21, 6),
        "likes": 34,
        "views": 286,
        "content": "作业写完顺手整理的，三种反转写法对比：\n\n1. 迭代三指针：prev/curr/next，注意先存 next 再改指向，否则链就断了；\n2. 头插法：拿原节点依次插到哑结点后面，最不容易错；\n3. 递归：reverseList(head.next) 之后再接回去，注意 head.next.next = head 和 head.next = null 这两步的顺序。\n\n我自己踩过的坑：迭代法最后 return 的是 prev 不是 curr（curr 已经是 null 了）。递归版在 10^5 节点会爆栈，OJ 上老老实实用迭代。\n\n有错误欢迎指出，一起补全。",
        "replies": [
            _reply("肖楚墨", "23001020126", "头插法确实最稳，我期中就是用头插法一遍过的。递归爆栈那个点提醒得好，addBottom_ 上真的会踩。", _ts(6, 28, 21, 48), 8, "target-23001020119-forum-post-01-reply-01"),
            _reply("林暮白", "23001020127", "补充一个：反转区间链表（LeetCode 92）可以用「头插法 + 计数」直接扩展，思路完全一致。", _ts(6, 29, 9, 15), 11, "target-23001020119-forum-post-01-reply-02"),
        ],
    },
    {
        "id": "target-23001020119-forum-post-02",
        "title": "求确认：循环队列判满到底用 (rear+1)%N==front 还是维护 size 变量？",
        "category": "qna",
        "categoryLabel": "课程答疑",
        "tags": ["数据结构", "队列"],
        "createdAt": _ts(7, 2, 20, 14),
        "likes": 21,
        "views": 173,
        "content": "写循环队列的时候发现两种判满思路：\n\nA. 牺牲一个格子：(rear+1)%capacity == front 时判满，front == rear 判空。好处是不用额外变量，坏处是容量少一格，而且判空和判满条件长得有点像，容易写混。\n\nB. 维护 size：入队 size+1，出队 size-1，size==capacity 判满，size==0 判空。直观但要多维护一个状态。\n\n我手写的时候 A 方案过了 OJ，但总感觉 B 更不容易错。大家的习惯是哪种？考试手写推荐哪个？",
        "replies": [
            _reply("江辰", "23001020122", "考试推荐 A，书上定义就是它，判空判满各一句话写清楚就行。工程里我用 B，可读性值回票价。", _ts(7, 2, 20, 57), 9, "target-23001020119-forum-post-02-reply-01"),
        ],
    },
    {
        "id": "target-23001020119-forum-post-03",
        "title": "「笔记」把 B+ 树范围查询和回表次数画成一张图之后全通了",
        "category": "share",
        "categoryLabel": "经验分享",
        "tags": ["数据库", "索引"],
        "createdAt": _ts(7, 6, 19, 38),
        "likes": 42,
        "views": 351,
        "content": "之前一直背「B+ 树叶子节点串链表」，但做题还是懵。昨天把一次范围查询完整画了出来：\n\n1. 从根向下定位起始 key 所在叶子（这一步只走 log_N 次）；\n2. 沿叶子链表向右扫到终点 key；\n3. 如果是非覆盖索引，扫到的每个主键还要回聚簇索引取整行——回表次数 = 命中行数。\n\n所以「为什么尽量用覆盖索引」的答案就变成：把第 3 步整个删掉。\n\n画完图之后老师留的 index/offset 那类计算题也顺了，因为终于知道每个字段在树上「住哪一层」。分享给同样背了就忘的同学。",
        "replies": [
            _reply("顾清寒", "23001020120", "第 3 步的公式化太准了，我上次面试就被问「回表次数怎么估」，答的就是命中行数。", _ts(7, 6, 20, 22), 13, "target-23001020119-forum-post-03-reply-01"),
            _reply("沈砚之", "23001020125", "求这张图的原件，想打印了贴工位上（", _ts(7, 7, 10, 41), 6, "target-23001020119-forum-post-03-reply-02"),
        ],
    },
    {
        "id": "target-23001020119-forum-post-04",
        "title": "Python 切片浅拷贝踩坑实录：改一个格子，坏了一整张表",
        "category": "share",
        "categoryLabel": "经验分享",
        "tags": ["Python", "踩坑"],
        "createdAt": _ts(7, 11, 22, 3),
        "likes": 28,
        "views": 218,
        "content": "写动态规划初始化的时候顺手写了：\n\ndp = [[0] * n] * m\n\n结果每次更新 dp[i][j]，整列都变了。排查了半小时才反应过来：* m 复制的是同一个内层列表的引用，改一个就是改所有。\n\n正确姿势是列表推导：\n\ndp = [[0] * n for _ in range(m)]\n\n顺手复习了结论：切片 / * 复制都是浅拷贝，嵌套结构要 copy.deepcopy 或者逐层推导。以前在书上看到这行字没感觉，自己踩一次就终身难忘了。",
        "replies": [
            _reply("陆子昂", "23001020123", "经典坑，我也踩过。再加一个：tuple 里放 list 的话 tuple 不可变也救不了里面的 list。", _ts(7, 11, 22, 40), 7, "target-23001020119-forum-post-04-reply-01"),
        ],
    },
    {
        "id": "target-23001020119-forum-post-05",
        "title": "求助：单调栈解接雨水，栈里到底存下标还是存高度？",
        "category": "qna",
        "categoryLabel": "课程答疑",
        "tags": ["算法", "单调栈"],
        "createdAt": _ts(7, 17, 21, 26),
        "likes": 15,
        "views": 156,
        "content": "两种写法都见过：\n\n- 存下标：height[st[-1]] 取高度，算宽度直接用 i - st[-1] - 1；\n- 存高度：宽度要额外记，容易乱。\n\n我自己写存下标版能过，但看题解里弹栈后一层层「横向接水」的图，总感觉对「为什么弹栈时结算的是那一层的水」理解还是虚的。有没有同学能用一句话把这个结算时机讲透？",
        "replies": [
            _reply("谢临风", "23001020124", "一句话：弹栈结算的是「当前条右侧第一个更高者到达之前，被弹出柱子顶部那一层」的水。每次弹栈只算一层，所以横向一层层填。", _ts(7, 17, 22, 2), 12, "target-23001020119-forum-post-05-reply-01"),
        ],
    },
    {
        "id": "target-23001020119-forum-post-06",
        "title": "「复盘」期中考后我把 Dijkstra 堆优化整理成了模板，附三个易错点",
        "category": "share",
        "categoryLabel": "经验分享",
        "tags": ["算法", "最短路"],
        "createdAt": _ts(7, 24, 20, 49),
        "likes": 37,
        "views": 308,
        "content": "期中 Dijkstra 堆优化第 4 个用例超时，重写时把易错点全记下来了：\n\n1. 懒删除：弹出堆顶时如果 d[u] < dist[u] 直接 continue，别在堆里真删；\n2. 初始化：dist[s]=0 要在 push 之前，push (0, s)；\n3. 判断成环/重边：邻接表存有向边别存反，无向图两个方向都要 add。\n\n模板（Python heapq）我贴在自己仓库 notes/dijkstra.py 里了，稀疏图 O((V+E)logV) 稳过 10^5 规模。\n\n顺便：错题本里那条「为什么能避免 O(n^2) 扫描」我现在的理解是——堆替我们完成了「找未确定点中 dist 最小」这件事，每个点只出堆一次。求锤。",
        "replies": [
            _reply("肖楚墨", "23001020126", "第 1 点懒删除是精髓，我第一次写就想在堆里删元素，当场表演原地消失。", _ts(7, 24, 21, 18), 10, "target-23001020119-forum-post-06-reply-01"),
            _reply("林暮白", "23001020127", "补一句：稠密图直接邻接矩阵 + O(n^2) 朴素版反而更快，别无脑堆优化。", _ts(7, 25, 8, 44), 14, "target-23001020119-forum-post-06-reply-02"),
        ],
    },
    {
        "id": "target-23001020119-forum-post-07",
        "title": "组队：九月底校赛（程序设计）有没有缺队友的，求带/互带",
        "category": "discussion",
        "categoryLabel": "学习讨论",
        "tags": ["竞赛", "组队"],
        "createdAt": _ts(8, 10, 19, 52),
        "likes": 19,
        "views": 142,
        "content": "如题，九月下旬的校级程序设计竞赛想找队友组队（三人队）。\n\n自我介绍：数据结构基础还行，图论和 DP 比较熟，去年蓝桥杯省三（惭愧，目标是今年冲省二）。每周能保证 2-3 次 CF div3/div4 连训，周末可以线下刷题。\n\n希望找一个数学/思维强的 + 一个代码手速稳的，风格互补。有意向的评论区或者私信都行，训练地点图书馆三楼或实验室都 OK。",
        "replies": [
            _reply("陆子昂", "23001020123", "数学位 +1，组合博弈和数论在练，周六下午图书馆可以面谈。", _ts(8, 10, 20, 31), 5, "target-23001020119-forum-post-07-reply-01"),
        ],
    },
]

# 谢渝在同学已有帖下的回复（追加到对应帖的 replies 数组）
FORUM_REPLIES_BY_TARGET: list[dict[str, str]] = [
    {
        "post_id": "forum-showcase-post-01",
        "content": "补充一个内存页角度：叶子链表让范围扫描变成「顺序读」，对磁盘和 CPU 缓存都友好；没有链表的话每个 key 都要从根走一遍，随机 I/O 会翻好几倍。楼主说的「减少随机 I/O」直觉是对的。",
        "createdAt": _ts(7, 6, 20, 44),
        "reply_id": "forum-showcase-post-01-reply-xieyu",
    },
    {
        "post_id": "forum-showcase-post-02",
        "content": "我的记法是顺着隔离级别加锁范围递增来记：读已提交只锁「行读那一瞬间」，可重复读锁「行的一生」，串行化锁「整个范围」。RR 挡不挡幻读要看实现，InnoDB 靠间隙锁在当前读下能挡，快照读下靠 MVCC 视觉上不存在幻影——考试答「RR 下幻读基本被防止，但极端混用当前读会出现」比较稳。",
        "createdAt": _ts(7, 11, 21, 37),
        "reply_id": "forum-showcase-post-02-reply-xieyu",
    },
]


def _seed_forum(store: JsonStore) -> dict[str, int]:
    for post in FORUM_POSTS:
        payload = {
            "id": post["id"],
            "title": post["title"],
            "author": TARGET_REAL_NAME,
            "authorUsername": TARGET_USER_ID,
            "avatar": f"/static/avatars/{TARGET_USER_ID}.jpg",
            "category": post["category"],
            "categoryLabel": post["categoryLabel"],
            "tags": post["tags"],
            "likes": post["likes"],
            "isLiked": False,
            "views": post["views"],
            "createdAt": post["createdAt"],
            "replies": post["replies"],
            "isPinned": False,
            "content": post["content"],
        }
        store.upsert("forum", "post", post["id"], payload, owner_id="", status="active")
    added_replies = 0
    for item in FORUM_REPLIES_BY_TARGET:
        payload = store.get_payload("forum", "post", item["post_id"])
        if not payload:
            continue
        replies = list(payload.get("replies") or [])
        if any(reply.get("id") == item["reply_id"] for reply in replies):
            continue
        replies.append(
            _reply(
                TARGET_REAL_NAME,
                TARGET_USER_ID,
                item["content"],
                item["createdAt"],
                9,
                item["reply_id"],
            )
        )
        payload["replies"] = replies
        payload["views"] = int(payload.get("views") or 0) + 5
        store.upsert("forum", "post", item["post_id"], payload, owner_id="", status="active")
        added_replies += 1
    return {"posts": len(FORUM_POSTS), "repliesAdded": added_replies}


# ---------------------------------------------------------------------------
# 5. 学生画像 + 账号信息
# ---------------------------------------------------------------------------

PROFILE_FIELDS = {
    "knowledge": 86,
    "cognitive": "目标驱动型，先搭整体框架再深入细节，偏好直接提问",
    "pace": 88,
    "error_pattern": "偶发失误集中在循环队列判满条件、矩阵乘法方向与 PR 自测描述完整性，订正后同类错误基本不再犯",
    "goal": "系统啃完数据结构与算法专题，期末冲刺专业前 5%，备战九月校赛与明年蓝桥杯省二",
    "background": "计算机科学与技术",
}


def _seed_profile_and_account(db: Session) -> dict[str, Any]:
    account = db.query(UserAccount).filter(UserAccount.username == TARGET_USER_ID).first()
    if account:
        account.real_name = TARGET_REAL_NAME
        account.class_name = TARGET_CLASS_NAME
        if not account.avatar_path:
            account.avatar_path = f"{TARGET_USER_ID}.jpg"
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == TARGET_USER_ID).first()
    if not profile:
        profile = StudentProfile(user_id=TARGET_USER_ID)
        db.add(profile)
    for key, value in PROFILE_FIELDS.items():
        setattr(profile, key, value)
    db.commit()
    return {"profile": PROFILE_FIELDS, "className": TARGET_CLASS_NAME}


def seed_target_user_sixdim_data(db: Session) -> dict[str, Any]:
    """幂等注入六维图谱数据，返回各数据源写入摘要。"""
    store = JsonStore(db)
    summary = {
        "targetUser": TARGET_USER_ID,
        "homeworkSubmissions": _seed_homework_submissions(store),
        "examAttempts": _seed_exam_attempts(store),
        "mistakeMastery": _seed_mistake_mastery(store),
        "forum": _seed_forum(store),
        "profile": _seed_profile_and_account(db),
    }
    return summary
