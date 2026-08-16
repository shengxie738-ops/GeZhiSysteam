import sys
import os
import random
import time
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from app.core.database import SessionLocal
from app.models.user_account import UserAccount
from app.repositories.json_store import JsonStore

CHINA_TZ = timezone(timedelta(hours=8))

# Data to generate
FORUM_TOPICS = [
    # 课程答疑
    {
        "title": "红黑树的插入旋转到底怎么记？",
        "content": "数据结构课上老师讲了红黑树插入时的各种旋转情况（左旋、右旋、变色）。自己看的时候感觉总是记混，特别是叔叔节点是红色还是黑色的时候。有没有什么好记的口诀或者图解方法？大家在手写红黑树的时候一般怎么确保不错？",
        "category": "qna",
        "tags": ["数据结构", "红黑树", "二叉树"],
        "comments": [
            "我也在这个地方卡了很久，后来发现先记住2-3-4树的等价关系，再对应到红黑树的变色和旋转上，就顺畅多了。",
            "其实不用死记，画图！遇到叔叔是红色，就把祖父、父、叔叔变色，祖父变红继续向上；遇到黑色才需要旋转。只要记住这一个最核心的条件就能推出来。",
            "推荐看下《算法》第4版里的左倾红黑树（LLRB），规则比标准红黑树少很多，代码写起来也更短。考试的时候如果没硬性规定，可以写 LLRB。",
            "我昨天刚写完红黑树的实现，建议准备几个固定的测试用例，每次插入后打印一下前中后序，断点跟踪一下就能看懂树形变化了。",
            "感觉最难的不是插入，而是删除！删除的各种借节点操作才是真的绕晕了……不过期末考试一般最多考到插入吧？"
        ]
    },
    {
        "title": "计组里的Cache直接映射和全相联在代码性能上有直观体现吗？",
        "content": "最近在复习计组的 Cache 映射机制。直接映射会容易发生冲突，全相联硬件成本高。但在我们平时写 C++ 或 Java 的时候，能通过代码直接感受到 Cache 命中的差异吗？有没有什么经典的代码例子可以让我跑一下体会体会？",
        "category": "qna",
        "tags": ["计算机组成原理", "Cache", "性能优化"],
        "comments": [
            "最经典的例子就是二维数组的遍历！先按行遍历（`a[i][j]`）和先按列遍历（`a[j][i]`），你跑个大矩阵看看时间，按列遍历慢得怀疑人生，就是因为 Cache miss 严重。",
            "确实，除了二维数组，还有个经典的例子是数据结构的内存对齐（Struct padding），如果你的结构体刚好卡在 Cache line 的边界上，也会导致额外的加载。游戏开发经常优化这个。",
            "C++ 里面你可以自己用 `#pragma pack` 修改结构体大小，然后对比下循环处理它的时间。很多高性能并发库甚至会用 padding 专门避免伪共享（False Sharing），这都是直接跟 Cache 打交道。",
            "Java 的话，可以看看 LMAX Disruptor 这个框架的代码，里面为了避免伪共享，塞了好多没有任何作用的 long 类型变量，把关键数据隔开，保证它们不在同一个 Cache line。",
            "直接映射带来的问题就是“冲突缺失”。如果你两个数组刚好映射到相同的 Cache 组，交替访问它们的时候，哪怕 Cache 是空的也会一直相互挤走，性能极差。这也是为什么很多时候建议不要把数组大小设为 2 的幂次。"
        ]
    },
    {
        "title": "Transformer模型里，Q K V 为什么不能用同一个矩阵？",
        "content": "这学期的 AI 课在讲 Attention 机制。公式 $Attention(Q, K, V) = softmax(\\frac{QK^T}{\\sqrt{d_k}})V$ 看起来挺直观。但是为什么 Q、K、V 需要通过三个不同的权重矩阵 $W_q, W_k, W_v$ 从输入 X 里映射出来呢？如果直接用 X 替代 Q K V，不是能省下大量参数吗？",
        "category": "qna",
        "tags": ["人工智能", "深度学习", "Transformer"],
        "comments": [
            "如果直接用 X 乘 X^T，算出来的就是个对称矩阵。也就是说，A 对 B 的注意力和 B 对 A 的注意力强制变成一样的了。但语言里“猫”和“吃”的关系显然是不对称的。",
            "不同的权重矩阵让输入有了不同的语义空间。Q 就像是“我们在找什么”，K 是“我们有什么特征”，V 是“如果我们被选中了，提供什么信息”。强制它们一样的话，模型的表达能力就弱爆了。",
            "其实早期有些自注意力机制是共用权重矩阵的（比如 Q和K用同一个），但效果确实不如分开好。分开能够让模型通过线性变换学习到不同位置之间复杂的非对称依赖关系。",
            "顺便提一下，如果你只用一个矩阵，那就变成类似传统自相关函数的东西了，缺少了深度学习那种把输入投影到高维语义特征空间的能力。",
            "不仅不能用同一个，在多头注意力（Multi-head Attention）里，还要切分成好几组不同的 QKV，就是为了让模型从多个不同的视角去提取特征，防止单一视角不够丰富。"
        ]
    },
    # 竞赛交流
    {
        "title": "[蓝桥杯] 动态规划状态转移方程推不出来怎么办？",
        "content": "每次做蓝桥杯的题，只要一碰到中等难度的 DP（比如树形DP或者状压DP），我的脑子就完全卡壳。要么是状态定义得不对导致推不出方程，要么是漏掉了某些情况。大家都是怎么培养 DP 题的直觉的？刷多少题才能有手感？",
        "category": "competition",
        "tags": ["蓝桥杯", "算法竞赛", "动态规划"],
        "comments": [
            "其实 DP 最难的就是第一步——如何定义 dp[i][j]。我的经验是：题目问什么，状态就先试着定义成什么。如果发现转移不下去，再加一个维度（比如以什么结尾，或者选了多少个）。",
            "建议把经典的背包模型（01背包、完全背包、多重背包）和最长上升子序列（LIS）、最长公共子序列（LCS）彻底吃透。大部分中等题都是这几个模型的变种。",
            "状压 DP 刚开始学的时候确实觉得非人类。你可以先把 N<=20 这个数据范围刻在DNA里，看到这种数据范围，就算不知道怎么转，也要强行往状压上想。先把状态的二进制操作（与、或、移位）写熟练。",
            "我的方法是记忆化搜索！有时候正向推递推式很难，那就写个从后往前的 DFS，然后加个 memo 数组缓存一下结果。很多时候能拿大头分数，甚至能通过 100%。",
            "我也比较推荐记忆化搜索，蓝桥杯不像 ACM 卡常数卡得那么死，很多 DP 题写记忆化搜索思维量小很多，只要不爆栈就行。"
        ]
    },
    {
        "title": "软件杯后端组：SpringBoot微服务鉴权怎么做比较优雅？",
        "content": "我们组在准备今年的中国软件杯大赛，后端打算拆几个微服务。现在卡在用户鉴权这块了。是在每个服务里都写一套拦截器解析 JWT，还是在网关（Gateway）层统一下发解析好的用户信息？有做过的大佬能分享一下生产环境或者比赛拿高分的常规方案吗？",
        "category": "competition",
        "tags": ["软件杯", "SpringBoot", "微服务", "鉴权"],
        "comments": [
            "比赛的话，强烈建议在 Gateway 层做统一鉴权。网关解析 JWT 验证签名和过期时间，然后把 User ID 放在 HTTP Header 里透传给下游服务，这样下游就不用管 Token 的事情了，代码极其干净。",
            "补充楼上的，这种叫『网关鉴权，下游认头』。不过如果你们内部服务之间有互调，记得在 Feign Client 里面把 Header 传递下去，不然内部调用会丢失用户信息。",
            "如果是复杂的权限控制（RBAC，比如谁能访问什么接口），建议网关只校验登录状态，具体的接口权限控制（如 @PreAuthorize）还是放在具体的服务模块里做，因为路由太细网关不好维护。",
            "我们去年的项目就是用的 Gateway + JWT。顺便提醒一下，JWT 最好做一下黑名单机制（利用 Redis），不然用户退出登录或者修改密码后，旧的 Token 还能用，评委答辩的时候很喜欢揪这种安全漏洞。",
            "如果是为了拿奖，也可以考虑接入现成的认证中心，比如使用 Spring Authorization Server 或者整合 OAuth2，虽然对小项目偏重，但在架构图上画出来非常能唬人，加分项！"
        ]
    },
    {
        "title": "这周日的CCCC天梯赛，大家有什么拿分策略分享吗？",
        "content": "第一次参加中国大学生程序设计天梯赛，队伍里有大一新生也有大三的。看了一下往年真题，题量有点大，而且是按个人分数加总算团队分的。想问问参加过的学长学姐，在比赛的时候应该怎么分配时间？有什么避坑的经验吗？",
        "category": "competition",
        "tags": ["CCCC", "天梯赛", "竞赛经验"],
        "comments": [
            "天梯赛的核心是『保送大局』！千万别一开始就死磕 L3 的难题。前两小时，全员冲 L1 和 L2 的简单题，保证能拿的分全拿到手，别因为语法错误或者小粗心丢分。",
            "对，L1 虽然简单，但特别容易因为边界条件扣几分，天梯赛的判题机有时候挺刁钻的。建议提交前多造几组包括 0、负数、极大值的极端测试用例。",
            "大一大二的学弟学妹可以专注于把 L1 全满分，L2 挑自己会的数据结构做。大三的大手子负责突破 L3。比赛的时候千万不要几个人同时盯着一道自己不会的题发呆。",
            "特别提醒：一定要看清楚题目的输入输出格式！！有很多同学算法写对了，结果因为多了一个空格、或者换行不对，一直拿不到全部分数。天梯赛格式错不给分的。",
            "最后半小时如果某道题还是差几分，可以尝试面向测试用例编程，写几个 if-else 猜一下边界，有时候能蹭到几分，毕竟团队赛一分也是爱！"
        ]
    },
    # 经验分享
    {
        "title": "从Vue2到Vue3的组合式API，分享一点学习痛点",
        "content": "最近在把大二写的一个后台管理系统从 Vue2 迁移到 Vue3。一开始用 Composition API (setup) 简直痛苦，感觉原来在 data, methods, computed 里写得好好的，现在全揉在一起，代码变得像一锅粥。后来看了官网的逻辑复用（Composables），才突然开窍。大家有没有类似的经历？你们是怎么过渡的？",
        "category": "experience",
        "tags": ["Vue3", "前端开发", "项目经验"],
        "comments": [
            "一开始确实觉得乱，因为 Vue2 是按『选项类型』分类代码的，而 Vue3 是让你按『业务逻辑』分类。刚开始写 setup 容易把所有的 ref 和 function 堆在一个大文件里，这叫“意大利面条代码”。",
            "强烈建议把独立的逻辑抽成 `useUser.js`, `useTable.js` 这种 hooks。在 Vue 文件里只负责引入和绑定模板。一旦这么写，你会发现代码复用简直爽飞了，根本不想回 Vue2 的 mixins。",
            "其实最难受的是 ref 和 reactive 混用的心智负担。天天在纠结写 `.value`。后来的最佳实践就是：基础类型一律 `ref`，复杂的表单对象用 `reactive`。",
            "VueUse 这个库一定要用！里面封装了超级多好用的组合式函数，比如点击外部、本地存储、防抖节流等等。看 VueUse 的源码是学习 Composition API 最快的方法。",
            "我也是这样过来的。我的建议是搭配 TypeScript 一起写 Vue3，有了类型的约束，你写 composables 的时候输入输出极其清晰，比纯 JS 瞎猜爽太多了。"
        ]
    },
    {
        "title": "项目里碰到数据库死锁(Deadlock)的排查经验",
        "content": "前几天我们的抢课系统测试的时候，突然狂报 MySQL Deadlock 异常。排查了两天，终于发现是因为两个事务更新数据的顺序不一致导致的。整理了一点经验：1. 尽量按相同的主键顺序去锁定数据；2. 大事务拆小；3. 如果只是更新热点数据，可以尝试在 SQL 层面做计算，不把数据读出来再写回去。大家遇到过类似的并发坑吗？",
        "category": "experience",
        "tags": ["数据库", "死锁", "并发编程"],
        "comments": [
            "经典问题了。只要涉及到 A转账给B，B同时转账给A 这种逻辑，不注意加锁顺序必死锁。我们一般的做法是按主键大小排序，先锁 ID 小的，再锁 ID 大的，直接从根本上破除循环等待。",
            "你提到的“SQL 层面做计算”很好用。比如 `UPDATE inventory SET stock = stock - 1 WHERE id = 1 AND stock > 0`。这样就利用了数据库自身的行锁，不需要先 SELECT FOR UPDATE 再写回了。",
            "不过抢课或者秒杀系统，最好还是把高并发写请求拦在缓存层，用 Redis 的 Lua 脚本先扣库存，异步再落库 MySQL。不然再怎么优化，MySQL 的行锁竞争也会把 QPS 拖死。",
            "排查死锁的时候，可以通过 `SHOW ENGINE INNODB STATUS;` 去看最近一次死锁的日志。里面清楚写了哪个事务持有什么锁、在等什么锁，分析那个日志比盲猜好多了。",
            "我以前遇到死锁是因为用到了 MySQL 的间隙锁（Gap Lock）。非唯一索引上的更新或者删除，如果条件是一个范围，会锁住一大片区域。这个坑很多人都踩过，强烈建议复习一下 Next-Key Lock。"
        ]
    },
    {
        "title": "学习数据结构的小技巧：用动图和断点！",
        "content": "作为一个曾经在链表和二叉树上挣扎了半个学期的人，给大家分享个有效方法。不要死盯代码！不要死盯代码！代码是静止的，数据结构是动态的。推荐大家去搜 VisuAlgo 这个网站，所有的算法都有动画演示。另外，自己写代码的时候，务必学会 IDE 的单步调试（Debug），看着指针一层层改变，比你拿纸笔画清楚一万倍。",
        "category": "experience",
        "tags": ["数据结构", "学习方法", "编程技巧"],
        "comments": [
            "VisuAlgo 必须强推！当时学 AVL 树旋转的时候，脑子里根本转不过弯，看动画看了五遍，终于悟了。后来连着手写代码也觉得没那么难了。",
            "IDE 调试确实重要。很多人大二了还只会用 `printf` 或者 `console.log`，一到递归就完蛋了，打印出来的东西根本看不出调用栈在哪层。学会看 Call Stack 简直是程序员必备神技。",
            "如果是刷力扣，推荐大家用一下 LeetCode 的树形可视化插件，或者本地自己写个能把层序遍历数组直接打印成树状结构的辅助函数，调试的时候非常直观。",
            "除了调试，我也推荐“橡皮鸭调试法”。对着一个玩具鸭子或者室友，把你写的链表插入逻辑一句一句解释出来。很多时候刚解释到一半，自己就发现 `curr.next` 提前被覆盖了。",
            "其实用纸笔画也挺重要的，特别是期末考试只能手写代码的时候。不过结合着 Debug 验证自己画的结果，效果最好。现在的很多新手确实缺乏基础的 Debug 训练。"
        ]
    },
    # 日常闲聊
    {
        "title": "大家一般去哪里找好的实习内推机会啊？",
        "content": "大三下了，最近投了一堆海投简历，大部分都石沉大海或者笔试完就没消息了。听学长说找实习最好走内推，但是自己又不认识什么已经毕业在互联网大厂的学长学姐。大家平时都是通过什么渠道找靠谱的内推机会的？脉脉上找靠谱吗？",
        "category": "chat",
        "tags": ["实习", "求职", "日常闲聊"],
        "comments": [
            "牛客网上发内推贴的很多！很多大厂员工为了赚内推奖金，会在牛客的讨论区里发帖子。只要你简历不是很差，他们一般都很乐意帮你推，你可以在上面多看看。",
            "不要忽视学校自己的就业群和 BBS。其实很多校招团队会优先联系学校的辅导员或者老师。你可以直接去问你们系的辅导员，看看最近有没有企业定向来要人的。",
            "脉脉上找也可以，但前提是你的 Profile 要写得好看，而且发消息的时候直接附上精简版的简历和成绩。大厂人都很忙，别发一句“你好”等半天。",
            "最靠谱的还是同门师兄师姐的直推，特别是一个实验室出来的。如果你在实验室干过，老板一般都会帮忙介绍以前毕业的学生，可以直接推到对方部门里，免筛选。",
            "其实多参加点比赛（蓝桥杯、互联网+之类）也行。有些比赛的赞助商在颁奖的时候直接就把优秀的选手拉群发 Offer 了。技术过硬的话机会很多。"
        ]
    },
    {
        "title": "期末复习周，二食堂阿姨打菜的手抖得越来越厉害了",
        "content": "简直绷不住，最近为了复习天天泡图书馆，饭点去二食堂买那个红烧肉。本来想补补脑子，结果阿姨一勺子下去，颠了两下，硬生生把三块肉给颠回锅里了，最后就剩两块加一堆土豆。大家都这样吗？一食堂会不会好一点？",
        "category": "chat",
        "tags": ["吐槽", "大学生活", "日常闲聊"],
        "comments": [
            "真实！二食堂那个阿姨是传说中的帕金森颠勺法。我上次打糖醋排骨，硬是给抖成糖醋骨头，肉全回去了。",
            "一食堂的二楼自选菜还不错，自己夹，想吃多少拿多少，不用看阿姨的脸色。不过去晚了就只剩冷饭了，建议 11:30 准时冲。",
            "期末复习本来就费脑子，我建议直接点外卖到宿舍楼下。虽然贵一点，但至少保证碳水和蛋白质够。每天在南门拿外卖的人能排成长龙。",
            "告诉你们个诀窍，去打饭的时候要一直面带微笑喊阿姨好，并且眼睛直勾勾盯着勺子。阿姨一般会不好意思抖太多，亲测有效！",
            "食堂的土豆不好吃吗！红烧肉的灵魂其实就是吸满汤汁的土豆！不过复习周大家确实都挺辛苦的，实在不行周末出去学校旁边的小吃街搓一顿烧烤犒劳一下自己。"
        ]
    }
]

def _parse_student_names(path):
    if not os.path.exists(path):
        return []
    names = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            import re
            match = re.match(r"^\d+[\.、]\s*(.+?)\s*$", line)
            if match:
                names.append(match.group(1))
    return names

def _avatar_files(path):
    if not os.path.exists(path):
        return []
    import re
    files = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    def sort_key(name):
        match = re.search(r"\((\d+)\)", name)
        return (int(match.group(1)) if match else 9999, name)
    return sorted(files, key=sort_key)

def main():
    db = SessionLocal()
    try:
        store = JsonStore(db)
        
        # 1. 从测试数据注入文件夹获取真实用户池
        data_root = r"D:\软件杯测试数据注入"
        names = _parse_student_names(os.path.join(data_root, "学生姓名.txt"))
        avatar_files = _avatar_files(os.path.join(data_root, "头像"))
        
        if not names:
            print("没有找到测试学生姓名数据。")
            return
            
        user_pool = []
        for index, name in enumerate(names, start=1):
            student_id = f"202300{index:02d}"
            avatar_ext = os.path.splitext(avatar_files[index - 1])[1].lower() if index - 1 < len(avatar_files) else ".jpg"
            avatar_path = f"{student_id}{avatar_ext}"
            
            user_pool.append({
                "username": student_id,
                "real_name": name,
                "avatar": f"/static/avatars/{avatar_path}",
                "role": "student"
            })
            
        print(f"成功加载 {len(user_pool)} 个真实用户，开始生成帖子数据...")
        
        now = datetime.now(CHINA_TZ)
        
        for idx, topic in enumerate(FORUM_TOPICS):
            # 时间控制：过去14天，早上8点到晚上23:30之间
            days_ago = random.randint(0, 14)
            hour = random.randint(8, 23)
            minute = random.randint(0, 59)
            if hour == 23 and minute > 30:
                minute = 30
            
            created_dt = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            author = random.choice(user_pool)
            post_id = f"gen-post-{int(time.time()*1000)}-{idx}"
            
            # 选择评论者（与作者不同）
            available_commenters = [u for u in user_pool if u["username"] != author["username"]]
            if len(available_commenters) < 5:
                # 兼容用户较少的环境
                commenters = available_commenters * 2
            else:
                commenters = random.sample(available_commenters, 5)
            
            replies = []
            reply_dt = created_dt
            
            for i, comment_text in enumerate(topic["comments"]):
                # 每条评论之间随机间隔15到120分钟
                reply_dt += timedelta(minutes=random.randint(15, 120))
                if reply_dt > now:
                    reply_dt = now
                    
                commenter = commenters[i % len(commenters)]
                
                is_ai = False
                if "Prof. X" in commenter["real_name"] or "AI" in commenter["real_name"]:
                    is_ai = True
                
                replies.append({
                    "id": f"{post_id}-reply-{i+1}",
                    "author": commenter["real_name"],
                    "authorUsername": commenter["username"],
                    "avatar": commenter["avatar"],
                    "isAi": is_ai,
                    "content": comment_text,
                    "createdAt": reply_dt.isoformat(),
                    "likes": random.randint(0, 20)
                })
                
            likes = random.randint(10, 60)
            views = likes * random.randint(5, 15)
            
            category_label_map = {
                "qna": "课程答疑",
                "experience": "经验分享",
                "competition": "竞赛交流",
                "chat": "日常闲聊"
            }
            
            post_payload = {
                "id": post_id,
                "title": topic["title"],
                "content": topic["content"],
                "author": author["real_name"],
                "authorUsername": author["username"],
                "avatar": author["avatar"],
                "category": topic["category"],
                "categoryLabel": category_label_map.get(topic["category"], "课程答疑"),
                "tags": topic["tags"],
                "likes": likes,
                "isLiked": False,
                "views": views,
                "createdAt": created_dt.isoformat(),
                "replies": replies,
                "isPinned": False
            }
            
            store.upsert(
                module="forum",
                record_type="post",
                record_key=post_id,
                payload=post_payload
            )
            print(f"[生成完成] 分类:{category_label_map.get(topic['category'])} | 标题: {topic['title']} | 作者: {author['real_name']} | 评论数: {len(replies)}")
            
        print("所有论坛数据生成并写入数据库完成！")

    finally:
        db.close()

if __name__ == "__main__":
    main()
