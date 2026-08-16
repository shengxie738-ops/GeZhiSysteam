from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.domain_record import DomainRecord
from app.models.user_account import UserAccount


FORUM_SHOWCASE_PREFIX = "forum-showcase"
CHINA_TZ = timezone(timedelta(hours=8))
DEFAULT_CLASS_NAME = "计科 2301"


@dataclass(frozen=True)
class ForumClassmateAccount:
    real_name: str
    student_id: str
    password: str


@dataclass(frozen=True)
class ForumUser:
    username: str
    real_name: str
    student_id: str
    avatar: str


POST_SPECS: list[dict[str, Any]] = [
    {
        "category": "qna",
        "title": "数据架构课的 B+ 树范围查询，到底为什么要串叶子节点？",
        "content": "复习数据架构的时候卡住了：B+ 树内部节点只放索引，叶子节点才挂数据，这个我能理解。但老师一直强调叶子节点之间要用链表串起来。我的理解是范围查询先定位到起点叶子，然后一路 next 扫过去，不用反复回到根节点。那如果落到磁盘页上，是不是还能减少随机 I/O？有没有同学用一句人话讲讲。",
        "tags": ["数据架构", "B+树", "索引"],
        "days_ago": 34,
        "hour": 9,
        "comments": [
            "对，就是为了范围查询顺扫。你可以把它理解成目录先定位页码，然后按页往后翻，比每查一个值都重新翻目录省事太多。",
            "我们老师说面试里讲 B+ 树，最好把“范围查询友好”和“磁盘页高度低”这两个点一起说，听起来就比较完整。",
            "楼主这个理解没问题。补一句：数据库里叶子页顺序读通常比随机读舒服，所以这个设计很现实，不只是书上好看。",
        ],
    },
    {
        "category": "qna",
        "title": "数据架构里的事务隔离级别，总是和锁混在一起，怎么记？",
        "content": "脏读、不可重复读、幻读我背得出来，但一做题就开始乱。尤其是可重复读到底挡不挡幻读，不同数据库实现还不一样。有没有人能用“读一行”和“读一个范围”的角度讲讲？感觉这样比死记四个级别靠谱。",
        "tags": ["数据架构", "事务", "隔离级别"],
        "days_ago": 33,
        "hour": 14,
        "comments": [
            "我自己的记法：不可重复读看同一行前后变没变，幻读看同一个范围里有没有多出来的行。范围这个词抓住就清楚很多。",
            "MySQL InnoDB 的可重复读靠 MVCC 和 next-key lock 处理很多幻读场景，考试如果没限定数据库，最好按标准定义回答。",
            "可以画时间线。T1 查一次，T2 改或插，T1 再查一次，看结果有没有变，基本就能判断是哪类问题。",
        ],
    },
    {
        "category": "qna",
        "title": "计算机程序设计课：递归函数到底怎么确定出口不漏？",
        "content": "写递归题最怕两件事：出口写少了栈爆，出口写多了结果少算。像二叉树路径、全排列、组合这些题，我看题解都觉得顺，一自己写就会漏掉回溯。大家写递归前会先画调用树吗，还是直接从函数语义开始定参数？求一个不玄学的方法。",
        "tags": ["计算机程序设计", "递归", "回溯"],
        "days_ago": 32,
        "hour": 10,
        "comments": [
            "先写函数语义很有用，比如 dfs(i, path) 表示“从 i 开始补全 path”。语义清楚了，出口一般就是 i 到头或者 path 满足条件。",
            "回溯题我固定三步：做选择、递归、撤销选择。撤销那一步千万别靠记忆，直接写成模板最稳。",
            "画调用树适合调试，不一定每题都画完整，但至少把前两层展开一下，能发现参数有没有往正确方向变化。",
        ],
    },
    {
        "category": "qna",
        "title": "C 语言指针数组和数组指针，我又绕晕了",
        "content": "程序设计课复习到指针，`int *p[3]` 和 `int (*p)[3]` 每次都要盯半天。前者是装 3 个 int 指针的数组，后者是指向含 3 个 int 的数组的指针，对吧？但一放到函数参数里就更乱了。有没有顺口一点的判断方法。",
        "tags": ["计算机程序设计", "C语言", "指针"],
        "days_ago": 30,
        "hour": 16,
        "comments": [
            "看谁先和变量名结合。`[]` 优先级高，所以 `*p[3]` 先是数组，再看元素是指针；括号把 `*p` 绑住后就是指针。",
            "函数传二维数组时 `int (*p)[3]` 很常见，因为你传进去的是一行一行的地址，列数必须知道。",
            "我建议把声明拆成中文读一遍：p 是什么，p 指向什么，里面的元素是什么。读顺了就不容易错。",
        ],
    },
    {
        "category": "qna",
        "title": "人工智能课的 A* 启发函数，为什么不能高估？",
        "content": "A* 里面 admissible heuristic 说不能高估真实代价，这样才能保证最优。我的直觉是高估会把真正的好路提前压下去，但写实验报告总觉得解释不够硬。曼哈顿距离在四方向网格里为什么安全？如果地图有传送门或者泥地代价，启发函数是不是就要重设？",
        "tags": ["人工智能", "A*", "搜索算法"],
        "days_ago": 29,
        "hour": 11,
        "comments": [
            "不能高估的核心是：f=g+h 如果把某条实际最优路径估贵了，队列可能先扩展别的路径，最优性证明就断了。",
            "四方向网格每走一步最多让曼哈顿距离减 1，所以它不会比真实步数大。有障碍也只是绕路，更不会让它高估。",
            "有传送门就要小心了，曼哈顿可能比真实代价大，因为传送能突然变近。泥地则看最小单步代价怎么定义。",
        ],
    },
    {
        "category": "qna",
        "title": "Transformer 里的 Q、K、V 能不能共用一个矩阵？",
        "content": "人工智能课讲 attention，公式看着挺直观，但 Q/K/V 三套线性变换让我一直有点纠结。既然都是从同一个输入 X 来的，为啥不直接共用一个投影省参数？是不是因为查询、匹配、输出信息本来就是三种不同角色？求大佬用不太论文腔的方式讲讲。",
        "tags": ["人工智能", "Transformer", "注意力机制"],
        "days_ago": 27,
        "hour": 15,
        "comments": [
            "可以这么理解：Q 是“我想找啥”，K 是“我有什么标签”，V 是“我被选中后交出啥内容”。三者硬绑一起表达能力会变弱。",
            "共用也不是完全不能跑，但模型少了自由度。尤其是不同 token 之间的关系不一定对称，分开投影更灵活。",
            "多头注意力也是类似思路，让不同头去看不同子空间。省参数可以做，但通常要拿效果换。",
        ],
    },
    {
        "category": "qna",
        "title": "机器学习里训练集 loss 降了，验证集反而抖，是过拟合吗？",
        "content": "机器学习课程实验做分类，训练 loss 一路往下，验证集 accuracy 有时候涨有时候掉。老师说可能是学习率、数据划分、过拟合都有关。我现在不知道该先调学习率，还是先加正则/dropout。大家做课程实验一般怎么排查，别一上来就玄学调参。",
        "tags": ["机器学习", "调参", "过拟合"],
        "days_ago": 26,
        "hour": 13,
        "comments": [
            "先固定随机种子和数据划分，不然你每次跑出来都不一样，根本没法判断是哪一步生效。",
            "训练 loss 稳降但验证指标变差，确实要怀疑过拟合。可以先看训练/验证曲线差距，再决定加正则还是早停。",
            "学习率过大通常 loss 也会抖。你这个如果训练很顺、验证乱跳，优先检查数据量、类别分布和验证集是否太小。",
        ],
    },
    {
        "category": "qna",
        "title": "机器学习课程的 SVM 核函数，什么时候该从线性换 RBF？",
        "content": "这周实验要对比 SVM，不知道核函数怎么选。线性核快、好解释，但遇到非线性边界就不够；RBF 好像效果更强但参数 C 和 gamma 又多。课程报告里如果只说“调参后 RBF 更好”是不是太水了？有没有比较像样的分析角度。",
        "tags": ["机器学习", "SVM", "核函数"],
        "days_ago": 25,
        "hour": 17,
        "comments": [
            "可以先画 PCA 或 t-SNE 的二维分布看看大概形状，线性分不开再考虑 RBF。报告里别只贴分数，讲数据分布更有说服力。",
            "RBF 的 gamma 太大容易把每个点都记住，太小又接近线性。用网格搜索加交叉验证，比手调靠谱。",
            "如果特征维度很高、样本不多，线性核经常就够了。课程实验重点是比较过程，不是硬追最高分。",
        ],
    },
    {
        "category": "competition",
        "title": "蓝桥杯备赛：DP 题状态想不出来，怎么练才不是瞎刷？",
        "content": "蓝桥杯全国大学生软件和信息技术大赛的真题刷到 DP 就卡。模拟和枚举还能硬做，遇到背包变形、区间 DP、数位 DP，样例看懂但状态定义不出来。大家是按题型专题刷，还是先系统补经典模型？蹲一个靠谱训练顺序。",
        "tags": ["蓝桥杯", "动态规划", "备赛"],
        "days_ago": 24,
        "hour": 9,
        "comments": [
            "先把 01 背包、完全背包、LIS/LCS 这些基础模型写到闭眼能出，再刷变形题。别一开始就上状压。",
            "蓝桥杯很多题可以先写记忆化搜索，状态从递归参数里长出来，比直接推表格舒服。",
            "复盘比数量重要。每道 DP 都写一句“状态表示什么”，写不出来就说明没真懂。",
        ],
    },
    {
        "category": "competition",
        "title": "CCPC 组队训练，一个人卡题的时候另外两个人干啥最有效？",
        "content": "准备中国大学生程序设计竞赛（CCPC）校内选拔，三个人一台机的节奏还没磨合好。经常一个人在写，另外两个人围观，结果大家一起焦虑。老队伍一般怎么分工？是读题、造样例、盯边界同步进行，还是按算法方向分工更好？",
        "tags": ["CCPC", "程序设计竞赛", "组队训练"],
        "days_ago": 23,
        "hour": 14,
        "comments": [
            "别三个人盯一份代码。一个写，另一个手造样例和看边界，第三个读下一题，这样机器时间才不亏。",
            "我们队会设止损时间，20 分钟没思路就换人讲题。卡住不说最伤节奏。",
            "方向分工可以有，但基础题大家都得会。比赛前 1 小时通常拼的是谁更稳，不是分工多细。",
        ],
    },
    {
        "category": "competition",
        "title": "中国大学生计算机设计大赛，作品文档到底要写多细？",
        "content": "看了中国大学生计算机设计大赛官网的作品方向，感觉不只是能跑 demo，还得把需求、创新点、技术路线、测试结果讲清楚。我们组现在功能做得还行，但文档像课程作业。参加过的同学说说，答辩前文档应该细到接口和数据库表吗？",
        "tags": ["计算机设计大赛", "作品文档", "答辩"],
        "days_ago": 22,
        "hour": 10,
        "comments": [
            "建议核心接口和数据表要有，但别堆满。评委更想看到你为什么这么设计，以及数据闭环是否完整。",
            "文档里一定要放测试截图和真实操作流程。只有功能列表的话，很像临时拼出来的。",
            "创新点别写虚的。比如“引入 RAG 提升课程资料检索准确率”，后面最好跟对比指标或案例。",
        ],
    },
    {
        "category": "competition",
        "title": "全国大学生计算机应用能力与数字素养大赛，选择题怎么复习？",
        "content": "同学说的 IT 计算机素质应用赛，我查了一下更像“全国大学生计算机应用能力与数字素养大赛/全国IT技能大赛”这条线，题型偏信息素养、办公软件、数据分析、AI 基础。有人考过吗？这种比赛是刷题库更有效，还是先把概念系统过一遍？",
        "tags": ["数字素养", "IT技能大赛", "计算机应用能力"],
        "days_ago": 21,
        "hour": 16,
        "comments": [
            "这类题很多是概念和操作细节，先过一遍知识点框架，再刷题库查漏比较稳。",
            "如果有办公软件操作题，光背概念不够，最好自己开 WPS 或 Excel 跟着做几遍。",
            "注意题干里的“最适合”“不正确”这种字眼，我上次模拟错了一半都是没看清。",
        ],
    },
    {
        "category": "competition",
        "title": "计算机系统能力大赛 CPU 赛道，零基础能不能先看单周期？",
        "content": "看到全国大学生计算机系统能力大赛 CPU 设计赛（龙芯杯）的资料，感觉很硬核。我们计组刚学到流水线，Verilog 也只写过小模块。想问问如果暑假想入门，是不是先把单周期 CPU 跑通，再看五级流水和冒险处理？有没有推荐的学习路线。",
        "tags": ["计算机系统能力大赛", "CPU设计", "计组"],
        "days_ago": 20,
        "hour": 13,
        "comments": [
            "先单周期没问题。能把取指、译码、执行、访存、写回这条链跑通，再看流水线会少很多黑盒感。",
            "Verilog 一定要配仿真波形看，不然你以为信号对了，其实时序已经飞了。",
            "冒险处理先从 load-use 和 forwarding 开始，别一上来就追完整异常和中断。",
        ],
    },
    {
        "category": "competition",
        "title": "比赛项目加 RAG 模块，怎么避免答非所问？",
        "content": "我们做课程助手，向量库接上以后发现一个问题：用户问“B+ 树范围查询”，检索有时混进红黑树或普通二叉搜索树资料，回答就跑偏。现在纠结 query rewrite、metadata filter、rerank 哪个先做。工程比赛里评委如果现场追问，怎么讲这块比较扎实？",
        "tags": ["竞赛项目", "RAG", "向量检索"],
        "days_ago": 19,
        "hour": 18,
        "comments": [
            "先做 metadata filter，课程、章节、知识点这些过滤条件能立刻减少跑偏，比纯靠向量相似度稳。",
            "rerank 也建议加，尤其是 topK 里混了相近概念时，二次排序能救很多。",
            "答辩时讲闭环：检索命中、引用片段、低置信度拒答、人工反馈更新。别只说用了大模型。",
        ],
    },
    {
        "category": "competition",
        "title": "蓝桥杯填空题用 Python 暴力，怎么避免精度坑？",
        "content": "蓝桥杯填空题很多可以本地写脚本跑答案，但浮点、日期、大整数这些地方很容易翻车。比如概率题直接 float，最后差一点；日期枚举又容易漏闰年。大家赛前会准备哪些 Python 小模板？我目前只整理了日期、质数筛、组合数、Decimal。",
        "tags": ["蓝桥杯", "Python", "填空题"],
        "days_ago": 18,
        "hour": 11,
        "comments": [
            "日期题直接用 datetime，别自己手写每月天数，除非题目限制不能用库。",
            "浮点能不用就不用，概率很多可以用分数 Fraction 或者把式子化简后再算。",
            "暴力脚本也要写断言，比如小范围手算几个样例，别跑出一个数字就直接交。",
        ],
    },
    {
        "category": "experience",
        "title": "数据架构课程经验：索引不是越多越好，先看执行计划",
        "content": "课程项目有个排行榜接口，数据一多就慢。刚开始想当然给所有查询字段都加索引，结果写入变慢还没解决核心问题。后来用 EXPLAIN 看，发现 WHERE + ORDER BY 没走到合适的联合索引。调整成 `(course_id, score)` 后才明显改善。索引顺序真的不是装饰品。",
        "tags": ["课程经验", "数据架构", "MySQL"],
        "days_ago": 17,
        "hour": 9,
        "comments": [
            "这个太真实了。联合索引顺序错了，表面上有索引，实际还是扫得很痛苦。",
            "写报告时把 EXPLAIN 前后对比贴出来，比单纯说“优化了索引”有说服力。",
            "还要注意覆盖索引，有时候少查几个字段就能省回表，接口速度差很多。",
        ],
    },
    {
        "category": "experience",
        "title": "程序设计刷题经验：链表题别硬扛头节点特判",
        "content": "最近集中刷链表，发现自己出错最多的不是反转逻辑，而是空链表、单节点、删除头节点这些边界。后来统一加 dummy head，所有删除和插入都从 prev/curr 两个指针开始，代码一下稳了很多。尤其删除倒数第 N 个节点，dummy 真的能少一堆 if。",
        "tags": ["课程经验", "链表", "刷题"],
        "days_ago": 16,
        "hour": 15,
        "comments": [
            "dummy head 是链表题救命工具，尤其是可能改头节点的题，不用每次单独判断 head。",
            "再补一个：快慢指针先让 fast 走 N+1 步，prev 停在待删节点前面，和 dummy 配起来很顺。",
            "我之前就是忘了处理单节点，线上测试直接挂。现在链表题默认先写边界。",
        ],
    },
    {
        "category": "experience",
        "title": "人工智能实验调参，千万别一次改三个变量",
        "content": "做分类实验时我一开始同时改学习率、batch size、dropout，准确率波动很大，完全不知道谁生效。后来固定随机种子，每次只改一个变量，并记录训练曲线和验证集指标，才看出来学习率过大导致 loss 抖。机器学习实验最重要的可能不是调得多，而是可复现。",
        "tags": ["课程经验", "人工智能", "实验记录"],
        "days_ago": 15,
        "hour": 10,
        "comments": [
            "同意。调参不记录等于没调，过两天自己都不知道为什么这个版本最好。",
            "建议表格里加上数据划分、随机种子、epoch、best checkpoint，不然后面复现实验很麻烦。",
            "课程报告里放曲线比只放最终 accuracy 好，老师能看到你是真的分析过。",
        ],
    },
    {
        "category": "experience",
        "title": "参赛经验：答辩 demo 最好准备一条固定剧本",
        "content": "之前参加项目赛，现场最怕临时想点哪里。后来我们把 demo 流程写成剧本：登录、导入数据、触发分析、查看论坛讨论、导出报告，每一步谁讲、谁点、异常怎么兜底都排练。现场虽然紧张，但至少不会在页面里乱翻。这个准备比多做两个小功能更值。",
        "tags": ["参赛经验", "答辩", "Demo"],
        "days_ago": 14,
        "hour": 16,
        "comments": [
            "剧本真的很有用，尤其是多人答辩，不提前分工就会抢话或者冷场。",
            "建议再准备一个离线兜底视频，现场网络和服务器都不一定听话。",
            "演示数据也要提前造好，空系统看起来很像半成品，评委很难感知价值。",
        ],
    },
    {
        "category": "experience",
        "title": "找工作经验：项目别只写技术栈，要写你解决了什么问题",
        "content": "最近改简历发现，以前写“SpringBoot + Vue + MySQL + Redis”太像模板了。后来改成“把论坛帖子和评论持久化到统一 domain_records，支持部署后保留演示数据”，面试官反而更愿意追问。感觉项目经历最好写问题、动作、结果，不然一堆技术名词看不出含金量。",
        "tags": ["找工作经验", "简历", "项目经历"],
        "days_ago": 12,
        "hour": 11,
        "comments": [
            "STAR 法则挺适合项目描述：背景、任务、行动、结果。技术栈放后面就行。",
            "结果最好量化，比如接口从多少 ms 降到多少，数据量多少，覆盖了哪些异常。",
            "面试官最爱问“这个是你做的吗”，所以简历上写的点一定要能展开讲实现细节。",
        ],
    },
    {
        "category": "experience",
        "title": "大学抢课经验：别只盯热门老师，也看看时间冲突成本",
        "content": "抢课的时候大家都冲热门老师，但我踩过坑：课是抢到了，结果和实验、社团、比赛训练挤在一起，一学期都在赶场。现在我会先排时间块，再看老师和考核方式。能稳定去上课，比抢一个传说中给分高但时间爆炸的课更现实。",
        "tags": ["大学抢课", "课程经验", "时间安排"],
        "days_ago": 11,
        "hour": 13,
        "comments": [
            "还要看校区距离。十分钟跨校区这种安排，天气一差就想放弃。",
            "我会提前列 A/B/C 三套方案，第一志愿没了就立刻切，不然犹豫几秒全没。",
            "考核方式也重要，有的课平时作业多，期末周会和专业课撞得很难受。",
        ],
    },
    {
        "category": "experience",
        "title": "团队项目经验：接口契约先写清楚，联调少吵一半",
        "content": "这周和前端联调作业模块，刚开始大家在群里口头约字段名，结果 `studentName`、`student_name`、`name` 三套混着来。后来我们写了接口契约，明确请求体、响应体、错误码、空数据返回，再配一个 Postman 集合，效率直接提升。别等联调炸了才补文档。",
        "tags": ["项目经验", "接口契约", "团队协作"],
        "days_ago": 9,
        "hour": 17,
        "comments": [
            "接口文档最少要有字段含义和示例值，不然大家都按自己的理解写。",
            "错误码也别省。成功路径谁都会写，联调最耗时间的是异常返回不统一。",
            "Postman 集合可以跟着代码一起版本管理，后面回归测试也方便。",
        ],
    },
    {
        "category": "chat",
        "title": "图书馆三楼靠窗位置是不是默认被考研同学承包了？",
        "content": "最近想找个安静地方看数据架构，发现三楼靠窗上午十点前就满了，桌上全是厚书和水杯。二楼讨论区又有点吵。大家平时复习专业课都在哪儿？有没有既能插电又不太吵的位置推荐，蹲一个校园生存攻略。",
        "tags": ["日常闲聊", "自习地点", "复习"],
        "days_ago": 8,
        "hour": 10,
        "comments": [
            "三楼靠窗真的难抢，可以试试四楼西侧，插座少一点但人也少。",
            "空教室其实不错，尤其下午没课的楼层，背书和写代码都舒服。",
            "我一般早上八点半前到，不然只能接受随机座位了。",
        ],
    },
    {
        "category": "chat",
        "title": "期末周项目验收和考试撞车，大家怎么排优先级？",
        "content": "软件工程项目验收和机器学习考试挤在同一周，感觉每天都在切上下文。上午改接口，下午看 SVM，晚上还要改 PPT。最怕项目突然冒 bug，把复习节奏打碎。大家有没有比较现实的时间安排方法，别太鸡血那种。",
        "tags": ["日常闲聊", "期末周", "时间管理"],
        "days_ago": 7,
        "hour": 18,
        "comments": [
            "项目先冻结需求，只修 bug 不加功能。不然期末周加新东西很容易把自己拖死。",
            "我会把上午留给最难的复习，下午处理项目杂事，晚上只做轻量复盘。",
            "PPT 可以提前定模板和讲稿，别最后一天还在纠结动画。",
        ],
    },
    {
        "category": "chat",
        "title": "有没有人想组暑假算法打卡小队？每天 1-2 题那种",
        "content": "暑假不想完全躺平，准备每天刷 1-2 道算法题，从数组、链表、栈队列开始，再到树、图、动态规划。一个人坚持很难，想找几个人互相监督，每天在论坛发题号和一句复盘。目标不是卷排名，就是保持手感。有人一起吗？",
        "tags": ["日常闲聊", "算法打卡", "暑假计划"],
        "days_ago": 6,
        "hour": 20,
        "comments": [
            "算我一个，但建议规则简单点，题号加一句错因就够了，太复杂容易坚持不下去。",
            "可以每周固定一次复盘，把大家都错的题型整理出来，比单纯打卡更有用。",
            "先从 easy/medium 混合开始吧，上来全 hard 很快就劝退。",
        ],
    },
    {
        "category": "chat",
        "title": "机房空调是不是只有两档：不开和北极模式",
        "content": "今天下午在机房写程序设计作业，刚进去热，过半小时冻得鼠标都不想碰。带外套像夸张，不带又真的顶不住。有没有同学也觉得机房温度很玄学？写代码写到一半手冷，debug 都慢半拍。",
        "tags": ["日常闲聊", "机房", "写代码"],
        "days_ago": 5,
        "hour": 15,
        "comments": [
            "太真实了，我书包里常年放一件薄外套，夏天进机房比冬天还需要。",
            "坐远离出风口的位置会好点，不然一直被吹真的影响敲键盘。",
            "建议机房门口贴个“请自备外套”，大家少走弯路。",
        ],
    },
    {
        "category": "chat",
        "title": "课程群里问问题，怎么描述才不会被学长要求“贴代码”？",
        "content": "每次程序设计作业出 bug，想在群里问，但又怕描述不清。后来发现只发“为什么错”基本没人能答，贴最小代码、输入输出、期望结果和报错信息，回复会快很多。大家还有什么提问模板吗？我想整理一下贴到论坛置顶。",
        "tags": ["日常闲聊", "提问方式", "程序设计"],
        "days_ago": 3,
        "hour": 12,
        "comments": [
            "最小复现很重要，别把一整个项目丢出来让别人猜。能 20 行说明问题最好。",
            "再加上你已经尝试过什么，不然别人会重复建议你做过的事。",
            "标题也别写“救命”，写清楚模块和现象，比如“链表删除头节点后空指针”。",
        ],
    },
    {
        "category": "chat",
        "title": "今天有人去听人工智能讲座吗，感觉大模型部分讲得挺接地气",
        "content": "下午的讲座本来以为会很广告，结果讲到 prompt、RAG、智能体边界时还挺实用。尤其是说不要把大模型当数据库，要让它基于检索材料回答，这点和我们课程项目刚好对上。有没有同学也去了？后面问答环节我提前走了，错过了啥。",
        "tags": ["日常闲聊", "人工智能", "讲座"],
        "days_ago": 1,
        "hour": 14,
        "comments": [
            "问答里有人问幻觉问题，老师说重点是引用来源和低置信度拒答，不要强行编。",
            "还提到评测集要自己做，不能只靠主观感觉判断回答好不好。",
            "我记了一句：AI 功能上线前先想清楚失败时怎么兜底，挺适合写进项目文档。",
        ],
    },
]


CATEGORY_LABELS = {
    "qna": "课程答疑",
    "competition": "竞赛交流",
    "experience": "经验分享",
    "chat": "日常闲聊",
}


def parse_forum_classmate_accounts(path: str | Path) -> list[ForumClassmateAccount]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"演示账号文件不存在: {source}")

    pattern = re.compile(
        r"^\s*(?P<name>[^，,。.\s]+)\s*[，,]\s*学号\s*[:：]\s*(?P<student_id>\d+)\s*[。.\s]*密码\s*[:：]\s*(?P<password>[^\s，,。]+)"
    )
    accounts: list[ForumClassmateAccount] = []
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = pattern.match(line)
        if not match:
            raise ValueError(f"无法解析演示账号行: {line}")
        accounts.append(
            ForumClassmateAccount(
                real_name=match.group("name").strip(),
                student_id=match.group("student_id").strip(),
                password=match.group("password").strip(),
            )
        )
    if not accounts:
        raise ValueError(f"演示账号文件没有解析到账号: {source}")
    return accounts


def seed_academic_forum_showcase_data(
    db: Session,
    *,
    accounts_file: str | Path = r"D:\演示账号的同学文件\演示账号的同学用户.txt",
    anchor_now: datetime | None = None,
    reset_forum_showcase: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    now = _normalize_now(anchor_now)
    accounts = parse_forum_classmate_accounts(accounts_file)
    users = _forum_users(accounts)
    posts = _build_posts(users, now)
    hot_topics = _build_hot_topics(posts)

    summary = {
        "accounts": len(accounts),
        "forumPosts": len(posts),
        "comments": sum(len(post["replies"]) for post in posts),
        "hotTopics": len(hot_topics),
        "firstPostAt": posts[0]["createdAt"] if posts else "",
        "lastPostAt": posts[-1]["createdAt"] if posts else "",
    }
    if dry_run:
        return summary

    if reset_forum_showcase:
        _reset_forum_showcase_records(db)

    for account in accounts:
        _upsert_user_account(db, account)
    for post in posts:
        _upsert_domain_payload(
            db,
            module="forum",
            record_type="post",
            record_key=post["id"],
            payload=post,
            owner_id=post["authorUsername"],
            role="student",
            status="published",
            created_at=datetime.fromisoformat(post["createdAt"]).replace(tzinfo=None),
        )
    for topic in hot_topics:
        _upsert_domain_payload(
            db,
            module="forum",
            record_type="hot_topic",
            record_key=topic["id"],
            payload=topic,
            owner_id="",
            role="",
            status="active",
            created_at=now.replace(tzinfo=None),
        )
    db.commit()
    return summary


def _normalize_now(anchor_now: datetime | None) -> datetime:
    now = anchor_now or datetime.now(CHINA_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CHINA_TZ)
    return now.astimezone(CHINA_TZ)


def _forum_users(accounts: list[ForumClassmateAccount]) -> list[ForumUser]:
    return [
        ForumUser(
            username=account.student_id,
            real_name=account.real_name,
            student_id=account.student_id,
            avatar=f"/static/avatars/{account.student_id}.jpg",
        )
        for account in accounts
    ]


def _upsert_user_account(db: Session, account: ForumClassmateAccount) -> None:
    existing = db.query(UserAccount).filter(UserAccount.username == account.student_id).first()
    if not existing:
        existing = UserAccount(username=account.student_id)
        db.add(existing)
    existing.role = "student"
    existing.real_name = account.real_name
    existing.student_id = account.student_id
    existing.class_name = "人工智能 2304" if account.student_id.startswith("230040") else DEFAULT_CLASS_NAME
    existing.teacher_id = ""
    existing.avatar_path = existing.avatar_path or f"{account.student_id}.jpg"
    if not verify_password(account.password, existing.password_hash or ""):
        existing.password_hash = get_password_hash(account.password)


def _reset_forum_showcase_records(db: Session) -> None:
    records = (
        db.query(DomainRecord)
        .filter(
            DomainRecord.module == "forum",
            DomainRecord.record_key.like(f"{FORUM_SHOWCASE_PREFIX}%"),
        )
        .all()
    )
    for record in records:
        db.delete(record)
    db.commit()


def _build_posts(users: list[ForumUser], now: datetime) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for index, spec in enumerate(POST_SPECS, start=1):
        author = users[(index - 1) % len(users)]
        created_at = _post_time(now, int(spec["days_ago"]), int(spec["hour"]), index)
        post_id = f"{FORUM_SHOWCASE_PREFIX}-post-{index:02d}"
        posts.append(
            {
                "id": post_id,
                "title": spec["title"],
                "content": spec["content"],
                "author": author.real_name,
                "authorUsername": author.username,
                "avatar": author.avatar,
                "category": spec["category"],
                "categoryLabel": CATEGORY_LABELS[spec["category"]],
                "tags": spec["tags"],
                "likes": 12 + (index * 7) % 58,
                "isLiked": False,
                "views": 96 + (index * 43) % 780,
                "createdAt": created_at.isoformat(),
                "replies": _build_replies(post_id, author, users, spec["comments"], created_at, index),
                "isPinned": False,
            }
        )
    posts.sort(key=lambda post: post["createdAt"], reverse=True)
    return posts


def _post_time(now: datetime, days_ago: int, hour: int, index: int) -> datetime:
    minute = (index * 11 + days_ago * 3) % 50 + 5
    created = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if created > now:
        created = (now - timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return created


def _build_replies(
    post_id: str,
    author: ForumUser,
    users: list[ForumUser],
    comments: list[str],
    post_time: datetime,
    post_index: int,
) -> list[dict[str, Any]]:
    candidates = [user for user in users if user.username != author.username]
    replies: list[dict[str, Any]] = []
    for reply_index, content in enumerate(comments[:3], start=1):
        commenter = candidates[(post_index + reply_index * 4) % len(candidates)]
        reply_time = post_time + timedelta(hours=reply_index * 2, minutes=7 + reply_index * 9)
        if reply_time.hour > 21 or reply_time.hour < 8:
            reply_time = (post_time + timedelta(days=1)).replace(
                hour=8 + reply_index,
                minute=(post_index * 7 + reply_index * 13) % 50 + 5,
                second=0,
                microsecond=0,
            )
        replies.append(
            {
                "id": f"{post_id}-reply-{reply_index:02d}",
                "author": commenter.real_name,
                "authorUsername": commenter.username,
                "avatar": commenter.avatar,
                "isAi": False,
                "content": content,
                "createdAt": reply_time.isoformat(),
                "likes": 2 + (post_index * reply_index * 3) % 18,
            }
        )
    return replies


def _build_hot_topics(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for post in posts:
        for tag in post.get("tags") or []:
            counts[str(tag)] += 1
    topics = []
    for index, (tag, count) in enumerate(counts.most_common(12), start=1):
        topics.append(
            {
                "id": f"{FORUM_SHOWCASE_PREFIX}-topic-{index:02d}",
                "tag": tag,
                "count": 16 + count * 4 + index,
            }
        )
    return topics


def _upsert_domain_payload(
    db: Session,
    *,
    module: str,
    record_type: str,
    record_key: str,
    payload: dict[str, Any],
    owner_id: str,
    role: str,
    status: str,
    created_at: datetime,
) -> None:
    record = (
        db.query(DomainRecord)
        .filter(
            DomainRecord.module == module,
            DomainRecord.record_type == record_type,
            DomainRecord.record_key == record_key,
        )
        .order_by(DomainRecord.id.desc())
        .first()
    )
    if not record:
        record = DomainRecord(module=module, record_type=record_type, record_key=record_key)
        db.add(record)
    record.owner_id = owner_id
    record.role = role
    record.status = status
    record.payload = json.dumps(payload, ensure_ascii=False, default=str)
    record.created_at = created_at
    record.updated_at = created_at
