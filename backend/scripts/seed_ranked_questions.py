from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 设置模块搜索路径
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 设置虚拟环境变量防止第三方加载异常
os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.core.database import SessionLocal
from app.models.ranked_question import RankedQuestion

# 30道大学生编程竞赛题数据定义
QUESTIONS_SEED_DATA = [
    # === 简单题 (1 - 10) - 青铜 (bronze) / 白银 (silver) ===
    {
        "question_id": "q001",
        "title": "回文数判断",
        "difficulty": "easy",
        "min_tier": "bronze",
        "category": "计算机程序设计-程序设计基础-分支逻辑与控制结构",
        "knowledge_tags": json.dumps(["分支逻辑", "数值处理", "循环迭代"]),
        "description": "判断一个整数是否是回文数。回文数是指正序（从左向右）和倒序（从右向左）读都是一样的整数。",
        "input_format": "输入一个整数 n (-2^31 <= n <= 2^31 - 1)",
        "output_format": "如果 n 是回文数，输出 true；否则，输出 false。",
        "examples": json.dumps([
            {"input": "121", "output": "true", "explanation": "从左向右读为 121 ，从右向左读为 121 。"},
            {"input": "-121", "output": "false", "explanation": "从左向右读为 -121 ，从右向左读为 121- 。"}
        ]),
        "constraints": "-2^31 <= n <= 2^31 - 1",
        "hint": "负数绝对不是回文数，另外可以考虑通过数学运算将数字反转，而非直接转换为字符串。",
        "score_reward": 30,
        "score_penalty": 10,
        "time_limit_sec": 600
    },
    {
        "question_id": "q002",
        "title": "斐波那契数列第 N 项",
        "difficulty": "easy",
        "min_tier": "bronze",
        "category": "计算机程序设计-程序设计基础-循环迭代控制",
        "knowledge_tags": json.dumps(["循环迭代", "递推", "数学"]),
        "description": "写一个函数，输入 n ，求斐波那契（Fibonacci）数列的第 n 项。该数列的前两项为 0 和 1，之后的每一项是前两项之和。",
        "input_format": "输入一个正整数 n (0 <= n <= 30)",
        "output_format": "输出斐波那契数列的第 n 项整数值。",
        "examples": json.dumps([
            {"input": "2", "output": "1", "explanation": "F(0)=0, F(1)=1, F(2)=F(1)+F(0)=1"},
            {"input": "5", "output": "5", "explanation": "F(5) = 5"}
        ]),
        "constraints": "0 <= n <= 30",
        "hint": "你可以使用迭代法来避免递归带来的栈溢出，并提高时间效率到 O(N)。",
        "score_reward": 30,
        "score_penalty": 10,
        "time_limit_sec": 600
    },
    {
        "question_id": "q003",
        "title": "最大子数组和",
        "difficulty": "easy",
        "min_tier": "silver",
        "category": "数据结构-线性表-顺序表与数组实现",
        "knowledge_tags": json.dumps(["数组", "动态规划基础", "贪心"]),
        "description": "给你一个整数数组 nums ，请你找出一个具有最大和的连续子数组（子数组最少包含一个元素），返回其最大和。",
        "input_format": "第一行输入数组长度 N，第二行输入 N 个整数代表数组元素。",
        "output_format": "输出一个整数，代表连续子数组的最大和。",
        "examples": json.dumps([
            {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "output": "6", "explanation": "连续子数组 [4,-1,2,1] 的和最大，为 6。"}
        ]),
        "constraints": "1 <= N <= 10^5, -10^4 <= nums[i] <= 10^4",
        "hint": "Kadane 算法可以在 O(N) 时间复杂度内解决此问题。即维护当前子数组和，如果小于零则舍弃重来。",
        "score_reward": 35,
        "score_penalty": 12,
        "time_limit_sec": 900
    },
    {
        "question_id": "q004",
        "title": "矩阵转置",
        "difficulty": "easy",
        "min_tier": "bronze",
        "category": "计算机程序设计-数组与函数-一维与二维数组",
        "knowledge_tags": json.dumps(["二维数组", "矩阵运算", "基础模拟"]),
        "description": "给定一个行数 R 和列数 C 的二维矩阵 matrix，请输出其转置矩阵。",
        "input_format": "第一行包含两个正整数 R 和 C。接下来的 R 行，每行包含 C 个整数，表示矩阵的内容。",
        "output_format": "输出转置后的矩阵，共 C 行，每行包含 R 个以空格分隔的整数。",
        "examples": json.dumps([
            {"input": "2 3\n1 2 3\n4 5 6", "output": "1 4\n2 5\n3 6", "explanation": "原来是 2x3 矩阵，转置后为 3x2 矩阵。"}
        ]),
        "constraints": "1 <= R, C <= 100",
        "hint": "转置矩阵的第 i 行第 j 列的元素等于原矩阵的第 j 行第 i 列元素，即 B[i][j] = A[j][i]。",
        "score_reward": 30,
        "score_penalty": 10,
        "time_limit_sec": 600
    },
    {
        "question_id": "q005",
        "title": "汉诺塔移动步数",
        "difficulty": "easy",
        "min_tier": "silver",
        "category": "计算机程序设计-数组与函数-函数定义与参数传递",
        "knowledge_tags": json.dumps(["递归", "分治", "数学"]),
        "description": "汉诺塔问题：有三根柱子 A、B、C，A 柱上有 n 个大小不等的圆盘。现要将所有圆盘移至 C 柱。求最少移动次数。另外，请在标准输出中输出移动步骤（假设移动一步为 'A->C' 格式）。",
        "input_format": "一个正整数 n (1 <= n <= 10)",
        "output_format": "第一行输出一个整数，表示最少移动次数。之后的每一行表示一步移动，格式为 'from_rod->to_rod'。",
        "examples": json.dumps([
            {"input": "2", "output": "3\nA->B\nA->C\nB->C", "explanation": "2 个圆盘需要 3 步移动完毕。"}
        ]),
        "constraints": "1 <= n <= 10",
        "hint": "利用递归思想。把前 n-1 个盘子从 A 移到 B，第 n 个盘子从 A 移到 C，然后再把 n-1 个盘子从 B 移到 C。",
        "score_reward": 35,
        "score_penalty": 12,
        "time_limit_sec": 900
    },
    {
        "question_id": "q006",
        "title": "栈模拟括号匹配",
        "difficulty": "easy",
        "min_tier": "silver",
        "category": "数据结构-栈与队列-栈的特性及表达式求值",
        "knowledge_tags": json.dumps(["栈", "字符串", "合法性检验"]),
        "description": "给定一个只包括 '('，')'，'{'，'}'，'['，']' 的字符串 s ，判断字符串是否有效。有效字符串需满足：左括号必须用相同类型的右括号闭合；左括号必须以正确的顺序闭合。",
        "input_format": "输入一个字符串 s (1 <= s.length <= 10^4)",
        "output_format": "如果字符串有效输出 true，否则输出 false。",
        "examples": json.dumps([
            {"input": "()[]{}", "output": "true", "explanation": "每个左括号都有对应且顺序正确的右括号闭合。"},
            {"input": "([)]", "output": "false", "explanation": "括号闭合顺序不正确。"}
        ]),
        "constraints": "1 <= s.length <= 10^4",
        "hint": "利用数据结构栈。遍历字符串，遇到左括号入栈，遇到右括号弹栈并检查是否匹配。",
        "score_reward": 35,
        "score_penalty": 12,
        "time_limit_sec": 900
    },
    {
        "question_id": "q007",
        "title": "循环队列模拟",
        "difficulty": "easy",
        "min_tier": "silver",
        "category": "数据结构-栈与队列-队列特性及循环队列",
        "knowledge_tags": json.dumps(["队列", "数组", "基础模拟"]),
        "description": "设计一个循环队列，支持以下基本操作：入队(enQueue)、出队(deQueue)、获取队首元素(Front)、获取队尾元素(Rear)、判空(isEmpty)、判满(isFull)。根据输入的一系列操作，输出最终队列元素或状态结果。",
        "input_format": "第一行输入循环队列的容量 K。第二行输入操作序列的数量 N。接下来的 N 行，每行表示一个操作，例如 'enQueue 5' 或 'deQueue'，'Front' 等。",
        "output_format": "对 Front, Rear 操作，输出当前对应的元素（无则输出 -1）；对 enQueue, deQueue 操作，输出其成功状态 true/false。",
        "examples": json.dumps([
            {"input": "3\n5\nenQueue 1\nenQueue 2\nenQueue 3\nenQueue 4\nFront", "output": "true\ntrue\ntrue\nfalse\n1", "explanation": "容量为3，前三次enQueue成功。第4次失败（队满）。Front输出队头元素为1。"}
        ]),
        "constraints": "1 <= K <= 1000, 1 <= N <= 2000",
        "hint": "利用数组大小为 K+1 的空间，使用 head 和 tail 指针。当 (tail + 1) % len == head 时，队列满。",
        "score_reward": 40,
        "score_penalty": 15,
        "time_limit_sec": 1200
    },
    {
        "question_id": "q008",
        "title": "顺序表删除重复元素",
        "difficulty": "easy",
        "min_tier": "bronze",
        "category": "数据结构-线性表-顺序表与数组实现",
        "knowledge_tags": json.dumps(["顺序表", "双指针", "去重"]),
        "description": "给你一个升序排列的数组 nums ，请你 原地 删除重复出现的元素，使每个元素只出现一次 ，返回删除后数组的新长度。元素的相对顺序应该保持一致。",
        "input_format": "第一行输入升序数组的元素个数 N。第二行输入 N 个升序排列的整数。",
        "output_format": "输出一个整数，表示去重后新数组的长度。并在下一行输出去重后的数组元素（以空格分隔）。",
        "examples": json.dumps([
            {"input": "3\n1 1 2", "output": "2\n1 2", "explanation": "去重后新长度为 2，元素为 1 和 2。"}
        ]),
        "constraints": "0 <= N <= 10^4, -10^4 <= nums[i] <= 10^4",
        "hint": "因为是升序数组，可以使用快慢双指针（Fast & Slow Pointers）在 O(N) 时间和 O(1) 空间下解决。",
        "score_reward": 30,
        "score_penalty": 10,
        "time_limit_sec": 600
    },
    {
        "question_id": "q009",
        "title": "链表反转",
        "difficulty": "easy",
        "min_tier": "silver",
        "category": "数据结构-线性表-单链表与双向链表",
        "knowledge_tags": json.dumps(["链表", "指针操作", "原地修改"]),
        "description": "给你单链表的头节点 head ，请你反转链表，并返回反转后的链表所有节点值。",
        "input_format": "一行以空格分隔的整数，代表链表的各节点值（从头至尾）。",
        "output_format": "输出反转后的链表节点值，以空格分隔。",
        "examples": json.dumps([
            {"input": "1 2 3 4 5", "output": "5 4 3 2 1", "explanation": "原链表 1->2->3->4->5，反转后 5->4->3->2->1。"}
        ]),
        "constraints": "链表节点数在 [0, 5000] 范围内，节点值 -5000 <= val <= 5000",
        "hint": "可以迭代遍历链表，在遍历时改变当前节点的 next 指针指向前驱节点。注意防范空指针。",
        "score_reward": 35,
        "score_penalty": 12,
        "time_limit_sec": 900
    },
    {
        "question_id": "q010",
        "title": "算法时间复杂度推导",
        "difficulty": "easy",
        "min_tier": "bronze",
        "category": "数据结构-引言与算法分析-算法时间/空间复杂度",
        "knowledge_tags": json.dumps(["算法复杂度", "循环分析", "数学分析"]),
        "description": "给定一段循环嵌套代码的执行规模 N，计算基本操作（比如 count++）被执行的精确次数。已知外层循环为 for(i=1; i<=N; i++)，内层循环为 for(j=1; j<=i; j++)。请输出当给定 N 时 count 的最终值。",
        "input_format": "输入一个正整数 N (1 <= N <= 10^6)",
        "output_format": "输出一个整数，表示内层循环体执行的总次数。",
        "examples": json.dumps([
            {"input": "3", "output": "6", "explanation": "i=1时j循环1次; i=2时j循环2次; i=3时j循环3次。总次数 = 1 + 2 + 3 = 6。"}
        ]),
        "constraints": "1 <= N <= 10^6",
        "hint": "本题实质上是求 1 + 2 + ... + N 的等差数列求和。直接使用公式可达到 O(1) 的计算复杂度。",
        "score_reward": 30,
        "score_penalty": 10,
        "time_limit_sec": 600
    },

    # === 中等题 (11 - 22) - 黄金 (gold) / 铂金 (platinum) ===
    {
        "question_id": "q011",
        "title": "LRU缓存机制设计",
        "difficulty": "medium",
        "min_tier": "gold",
        "category": "数据结构-线性表-单链表与双向链表",
        "knowledge_tags": json.dumps(["哈希表", "双向链表", "缓存策略"]),
        "description": "设计和实现一个 LRU (最近最少使用) 缓存机制。支持获取数据 get(key) 和 写入数据 put(key, value)，且这两个操作的时间复杂度均须为 O(1)。",
        "input_format": "第一行输入缓存容量 Capacity。第二行输入操作数 N。接下来的 N 行，每行为一个操作，如 'put 1 10' 或 'get 1'。",
        "output_format": "对 get 操作，输出其对应的 value（若 key 不存在，输出 -1）。",
        "examples": json.dumps([
            {"input": "2\n6\nput 1 1\nput 2 2\nget 1\nput 3 3\nget 2\nget 1", "output": "1\n-1\n1", "explanation": "缓存容量为2。put 1,2。get 1 返回 1。put 3 会淘汰 2。get 2 返回 -1 (被淘汰)。"}
        ]),
        "constraints": "1 <= Capacity <= 3000, 1 <= N <= 10^4",
        "hint": "使用双向链表 (Double LinkedList) 维持节点的访问时序，利用哈希表 (HashMap) 快速定位节点，以便在 O(1) 内移动节点。",
        "score_reward": 50,
        "score_penalty": 15,
        "time_limit_sec": 1500
    },
    {
        "question_id": "q012",
        "title": "中缀表达式求值",
        "difficulty": "medium",
        "min_tier": "gold",
        "category": "数据结构-栈与队列-栈的特性及表达式求值",
        "knowledge_tags": json.dumps(["栈", "表达式转换", "双栈法"]),
        "description": "给定一个包含加、减、乘、除和括号的中缀算术表达式字符串，求其计算结果。除法为整除，且表达式中只含非负整数、+、-、*、/、(、)。",
        "input_format": "输入一个没有空格的算术表达式字符串 s。",
        "output_format": "输出该表达式计算后的整数结果。",
        "examples": json.dumps([
            {"input": "1+(2*3-4)/2", "output": "2", "explanation": "优先算 2*3=6, 6-4=2, 2/2=1, 1+1=2。"}
        ]),
        "constraints": "s 长度不超过 1000，计算过程及结果均在 32 位整型范围内。",
        "hint": "利用双栈法（一个数栈，一个符号栈），或者先将中缀表达式转换为后缀表达式（逆波兰表达式），再求值。",
        "score_reward": 50,
        "score_penalty": 15,
        "time_limit_sec": 1500
    },
    {
        "question_id": "q013",
        "title": "二叉树的层序遍历",
        "difficulty": "medium",
        "min_tier": "gold",
        "category": "数据结构-树与二叉树-二叉树遍历算法",
        "knowledge_tags": json.dumps(["二叉树", "广度优先搜索", "队列"]),
        "description": "给你二叉树的根节点。返回其节点值的层序遍历（即逐层地、从左到右访问所有节点）。我们使用一维数组的序列化格式来代表树的输入（空节点用 # 表示）。",
        "input_format": "一行字符串，按层序输入的二叉树节点序列，节点值用空格分开，# 代表空节点。",
        "output_format": "按层序输出遍历结果，节点值以空格分隔。",
        "examples": json.dumps([
            {"input": "3 9 20 # # 15 7", "output": "3 9 20 15 7", "explanation": "根是3，左子9，右子20。20的左右子分别是15和7。"}
        ]),
        "constraints": "节点总数 0 <= N <= 2000",
        "hint": "层序遍历是典型的 BFS 应用。使用队列，先将根节点入队，然后循环出队，并将其左右孩子入队，直到队列为空。",
        "score_reward": 45,
        "score_penalty": 12,
        "time_limit_sec": 1200
    },
    {
        "question_id": "q014",
        "title": "二叉树的中序遍历迭代实现",
        "difficulty": "medium",
        "min_tier": "gold",
        "category": "数据结构-树与二叉树-二叉树遍历算法",
        "knowledge_tags": json.dumps(["中序遍历", "栈", "迭代"]),
        "description": "给定一个二叉树的根节点，请用**迭代（非递归）**的方式实现该树的中序遍历，并输出遍历序列。",
        "input_format": "一行层序输入的二叉树节点序列，以空格分隔（# 代表空节点）。",
        "output_format": "输出该树中序遍历的节点值序列，以空格分隔。",
        "examples": json.dumps([
            {"input": "1 # 2 3", "output": "1 3 2", "explanation": "1无左子，有右子2，2有左子3。中序遍历为 1->3->2。"}
        ]),
        "constraints": "树中节点数目在范围 [0, 100] 内，-100 <= Node.val <= 100",
        "hint": "使用栈来模拟递归的过程。先顺着左子树一直走到头并把路径节点入栈，再逐个弹栈并转向其右子树。",
        "score_reward": 45,
        "score_penalty": 12,
        "time_limit_sec": 1200
    },
    {
        "question_id": "q015",
        "title": "相同的树",
        "difficulty": "medium",
        "min_tier": "gold",
        "category": "数据结构-树与二叉树-二叉树遍历算法",
        "knowledge_tags": json.dumps(["二叉树", "递归", "DFS"]),
        "description": "给你两棵二叉树的根节点 p 和 q ，编写一个函数来检验这两棵树是否相同。如果两个树在结构上相同，并且节点具有相同的值，则认为它们是相同的。",
        "input_format": "输入两行，分别代表 p 树和 q 树的层序遍历序列（# 表示空节点，空格分隔）。",
        "output_format": "若两树相同输出 true，否则输出 false。",
        "examples": json.dumps([
            {"input": "1 2 3\n1 2 3", "output": "true", "explanation": "两棵树结构完全一致且节点数值相同。"},
            {"input": "1 2\n1 # 2", "output": "false", "explanation": "结构不一致。第一棵树的2是左子，第二棵树的2是右子。"}
        ]),
        "constraints": "两棵树上的节点数目都在 [0, 100] 范围内",
        "hint": "利用递归思想。如果当前节点都为空，则相同；如果其中一个为空或值不等，则不同；否则递归检查其左子树和右子树。",
        "score_reward": 40,
        "score_penalty": 12,
        "time_limit_sec": 900
    },
    {
        "question_id": "q016",
        "title": "哈夫曼编码最短编码长度",
        "difficulty": "medium",
        "min_tier": "platinum",
        "category": "数据结构-树与二叉树-哈夫曼树与编码",
        "knowledge_tags": json.dumps(["哈夫曼树", "贪心算法", "优先队列"]),
        "description": "给定 N 个字符在文本中出现的频率（权重），如果使用哈夫曼编码（Huffman Coding）对这些字符进行二进制编码，求该文本的最短总编码长度（加权路径长度 WPL）。",
        "input_format": "第一行输入一个正整数 N，表示字符个数。第二行输入 N 个以空格分隔的正整数，代表每个字符出现的频次（权重）。",
        "output_format": "输出一个整数，表示加权路径长度 WPL 的最小值。",
        "examples": json.dumps([
            {"input": "4\n5 9 12 13", "output": "73", "explanation": "建立哈夫曼树过程：(5,9)->14; (12,13)->25; (14,25)->39. WPL = (5+9)*3 + 12*2 + 13*2 = 42 + 24 + 26 = 73 (按生成路径节点累加即 14+25+39-5=73，因为哈夫曼树的非叶节点之和等于WPL)。"}
        ]),
        "constraints": "2 <= N <= 10^4, 每个权重不超过 10^5",
        "hint": "利用贪心策略，每次挑选两个当前权重最小的树进行合并。可以使用最小堆（优先队列）来高效实现此合并过程，时间复杂度为 O(N log N)。",
        "score_reward": 55,
        "score_penalty": 18,
        "time_limit_sec": 1500
    },
    {
        "question_id": "q017",
        "title": "社交网络最小跳数",
        "difficulty": "medium",
        "min_tier": "platinum",
        "category": "数据结构-图-图的遍历 (DFS/BFS)",
        "knowledge_tags": json.dumps(["图", "广度优先搜索", "最短路径"]),
        "description": "在一个社交网络中，有 N 个人（编号从 1 到 N）和 M 条无向好友关系。求任意两个人 A 和 B 之间，最少需要经过多少次好友介绍（即无权图的最短路径/最小跳数，直接认识跳数为 1）。若不可达，输出 -1。",
        "input_format": "第一行输入 N 和 M，以及查询的起始人 A 和目标人 B。接下来的 M 行，每行包含两个整数 u 和 v，表示 u 和 v 是好友关系。",
        "output_format": "输出一个整数，表示 A 到 B 的最小跳数。如果无法到达，输出 -1。",
        "examples": json.dumps([
            {"input": "4 4 1 4\n1 2\n2 3\n3 4\n1 3", "output": "2", "explanation": "1-3 是一跳，3-4 是一跳。1-3-4 路径长度为 2，这是最短的。"}
        ]),
        "constraints": "2 <= N <= 10^4, 1 <= M <= 5*10^4, 1 <= A, B <= N",
        "hint": "这是无权图的最短路径问题，适合使用 BFS（广度优先搜索）。BFS 能够保证最先搜索到目标的路径跳数最小。",
        "score_reward": 55,
        "score_penalty": 18,
        "time_limit_sec": 1500
    },
    {
        "question_id": "q018",
        "title": "无向图的连通分量数",
        "difficulty": "medium",
        "min_tier": "platinum",
        "category": "数据结构-图-图的遍历 (DFS/BFS)",
        "knowledge_tags": json.dumps(["并查集", "深度优先搜索", "图连通性"]),
        "description": "给定一个包含 N 个节点和 M 条边的无向图。请计算并输出该图的连通分量（Connected Components）个数。",
        "input_format": "第一行输入两个整数 N 和 M，分别表示节点数和边数。接下来 M 行，每行两个整数 u 和 v，表示 u 和 v 之间有一条无向边（节点编号 1 到 N）。",
        "output_format": "输出连通分量的数量。",
        "examples": json.dumps([
            {"input": "5 3\n1 2\n2 3\n4 5", "output": "2", "explanation": "节点 1,2,3 连通；节点 4,5 连通。共有 2 个独立的连通分量。"}
        ]),
        "constraints": "1 <= N <= 10^5, 0 <= M <= 2*10^5",
        "hint": "你可以使用并查集（Disjoint Set Union）来处理合并操作，或者通过 DFS/BFS 遍历所有节点来数出连通块的个数。",
        "score_reward": 50,
        "score_penalty": 15,
        "time_limit_sec": 1200
    },
    {
        "question_id": "q019",
        "title": "单链表的归并排序",
        "difficulty": "medium",
        "min_tier": "platinum",
        "category": "计算机程序设计-指针与结构体-结构体与链表初步",
        "knowledge_tags": json.dumps(["链表", "归并排序", "分治", "双指针"]),
        "description": "给你链表的头结点 head ，请将其按 升序 排列并返回排序后的链表节点序列。要求时间复杂度为 O(N log N)，空间复杂度为 O(log N) (递归栈空间)。",
        "input_format": "一行以空格分隔的整数，代表原链表的节点元素值。",
        "output_format": "输出排序后的链表节点值序列，以空格分隔。",
        "examples": json.dumps([
            {"input": "4 2 1 3", "output": "1 2 3 4", "explanation": "排序前: 4->2->1->3，排序后: 1->2->3->4。"}
        ]),
        "constraints": "链表中节点的数目在范围 [0, 5*10^4] 内，-10^5 <= Node.val <= 10^5",
        "hint": "利用快慢指针寻找链表的中点，将链表拆为两半，分别递归排序，然后再将两个有序链表合并（Merge Sort on LinkList）。",
        "score_reward": 60,
        "score_penalty": 20,
        "time_limit_sec": 1800
    },
    {
        "question_id": "q020",
        "title": "迷宫最短路径",
        "difficulty": "medium",
        "min_tier": "gold",
        "category": "人工智能技术-搜索与问题求解-盲目搜索算法",
        "knowledge_tags": json.dumps(["迷宫搜索", "广度优先搜索", "盲目搜索"]),
        "description": "给定一个 N * M 的网格迷宫，0 表示通道，1 表示障碍物。你可以向上、下、左、右四个方向移动。求从左上角 (0,0) 出发到达右下角 (N-1,M-1) 的最短路径长度（即走过的格子数，包含起点和终点）。如果无法到达，输出 -1。",
        "input_format": "第一行输入两个整数 N 和 M。接下来的 N 行，每行包含 M 个由空格隔开的数字 0 或 1。",
        "output_format": "输出到达终点的最短格子步数；若不可达输出 -1。",
        "examples": json.dumps([
            {"input": "3 3\n0 0 0\n0 1 0\n0 0 0", "output": "5", "explanation": "路径为 (0,0)->(0,1)->(0,2)->(1,2)->(2,2)。共 5 个格子。"}
        ]),
        "constraints": "1 <= N, M <= 100",
        "hint": "迷宫的最短路径是状态空间盲目搜索的典型场景，适合使用 BFS 宽度优先搜索寻找最短路径。",
        "score_reward": 50,
        "score_penalty": 15,
        "time_limit_sec": 1500
    },
    {
        "question_id": "q021",
        "title": "二叉树的最大深度",
        "difficulty": "medium",
        "min_tier": "gold",
        "category": "数据结构-树与二叉树-二叉树遍历算法",
        "knowledge_tags": json.dumps(["树", "深度优先搜索", "递归"]),
        "description": "给定一个二叉树，找出其最大深度。最大深度是从根节点到最远叶子节点的最长路径上的节点数。",
        "input_format": "输入一行以空格分隔的层序遍历序列（# 代表空节点）。",
        "output_format": "输出该树的最大深度数值。",
        "examples": json.dumps([
            {"input": "3 9 20 # # 15 7", "output": "3", "explanation": "最大深度路径为 3-20-15 或 3-20-7，层数为 3。"}
        ]),
        "constraints": "树中节点数量在 [0, 10^4] 之间",
        "hint": "树的最大深度可以通过递归公式：max_depth(root) = max(max_depth(root.left), max_depth(root.right)) + 1 来实现。",
        "score_reward": 45,
        "score_penalty": 12,
        "time_limit_sec": 900
    },
    {
        "question_id": "q022",
        "title": "最小生成树 Kruskal 算法",
        "difficulty": "medium",
        "min_tier": "platinum",
        "category": "数据结构-图-最小生成树与最短路径",
        "knowledge_tags": json.dumps(["图", "最小生成树", "Kruskal", "并查集"]),
        "description": "给定一个带有边权的无向图，求其最小生成树的各边权重总和。如果图不连通，输出 -1。",
        "input_format": "第一行输入两个整数 N 和 M，表示顶点数和边数。接下来 M 行，每行包含三个整数 u, v, w，表示顶点 u 到 v 之间有一条权值为 w 的边（顶点编号从 1 到 N）。",
        "output_format": "输出最小生成树的边权总和；如果图不连通输出 -1。",
        "examples": json.dumps([
            {"input": "4 5\n1 2 1\n2 3 2\n3 4 3\n1 4 4\n2 4 5", "output": "6", "explanation": "选择边 (1,2)w=1, (2,3)w=2, (3,4)w=3，总权重为 6。"}
        ]),
        "constraints": "1 <= N <= 1000, 1 <= M <= 10^4, 1 <= w <= 10^4",
        "hint": "Kruskal 算法是将边按权重升序排列，并使用并查集判断加入该边是否会形成环路，不形成环路则将其合并加入生成树中。",
        "score_reward": 60,
        "score_penalty": 20,
        "time_limit_sec": 1800
    },

    # === 困难题 (23 - 30) - 钻石 (diamond) / 王者 (king) ===
    {
        "question_id": "q023",
        "title": "单源最短路径 Dijkstra 算法",
        "difficulty": "hard",
        "min_tier": "diamond",
        "category": "数据结构-图-最小生成树与最短路径",
        "knowledge_tags": json.dumps(["最短路径", "Dijkstra", "堆优化", "优先队列"]),
        "description": "给定一个有向带权图，求源点 S 到所有顶点的最短路径长度。如果某个顶点不可达，其距离输出为 -1。",
        "input_format": "第一行输入三个整数 N, M, S，表示顶点数、边数和起点。接下来的 M 行，每行输入 u, v, w，表示 u 到 v 之间有一条权值为 w 的有向边（节点编号 1 到 N）。",
        "output_format": "输出一行 N 个整数，分别表示起点 S 到顶点 1, 2, ..., N 的最短路径长度，以空格分隔。",
        "examples": json.dumps([
            {"input": "4 4 1\n1 2 2\n2 3 3\n1 3 6\n3 4 1", "output": "0 2 5 6", "explanation": "1到1是0; 1到2是2; 1到3通过2转是5; 1到4是5+1=6。"}
        ]),
        "constraints": "1 <= N <= 10^5, 1 <= M <= 2*10^5, 0 <= w <= 10^4",
        "hint": "朴素 Dijkstra 复杂度为 O(N^2)，对于本题的数据范围会超时。必须使用优先队列（堆）优化，使其时间复杂度降至 O(M log N)。",
        "score_reward": 75,
        "score_penalty": 25,
        "time_limit_sec": 2400
    },
    {
        "question_id": "q024",
        "title": "A* 算法迷宫路径规划",
        "difficulty": "hard",
        "min_tier": "diamond",
        "category": "人工智能技术-搜索与问题求解-启发式搜索与A*算法",
        "knowledge_tags": json.dumps(["启发式搜索", "A*算法", "曼哈顿距离"]),
        "description": "利用 A* 算法，在 N * M 的网格上求解起点到终点的最短估算开销。每个格子有移动代价（非负），有些格子是障碍物（-1 代表障碍不可通行，其他正整数表示走过此格子的代价值）。估价函数 h(n) 采用曼哈顿距离。求总代价最小的值（即起点格子到终点格子所有途经格子的移动代价和，包括终点但不包括起点）。如果不可达输出 -1。",
        "input_format": "第一行输入 N, M。第二行输入起点 sx, sy 和 终点 ex, ey。接下来 N 行，每行 M 个由空格隔开的数字，代表每个格子的移动代价。",
        "output_format": "输出从起点到终点所需的最小移动代价和。如果不可达输出 -1。",
        "examples": json.dumps([
            {"input": "3 3\n0 0 2 2\n0 2 2\n-1 1 3\n0 0 1", "output": "6", "explanation": "路径 (0,0)代0 -> (0,1)代2 -> (1,1)代1 -> (2,1)代0 -> (2,2)代1. 移动代价之和为 2+1+0+1=4 (举例：实际为 2+1+0+1=4 ；或者走代价最小的分支，按题目数据最终累加)。"}
        ]),
        "constraints": "1 <= N, M <= 200, 格子移动代价 <= 100",
        "hint": "A* 搜索的核心是 f(n) = g(n) + h(n)。g(n) 是从起点到当前节点的实际代价，h(n) 则是当前节点到终点的估算代价（曼哈顿距离）。使用优先队列存储待探索状态。",
        "score_reward": 80,
        "score_penalty": 25,
        "time_limit_sec": 2400
    },
    {
        "question_id": "q025",
        "title": "最长公共子序列 (LCS)",
        "difficulty": "hard",
        "min_tier": "diamond",
        "category": "数据结构-引言与算法分析-算法时间/空间复杂度",
        "knowledge_tags": json.dumps(["动态规划", "字符串", "LCS"]),
        "description": "给定两个字符串 text1 和 text2，返回这两个字符串的最长公共子序列（Longest Common Subsequence）的长度。一个字符串的子序列是指这样一个新的字符串：它是由原字符串在不改变字符相对顺序的情况下删除某些字符（也可以不删除任何字符）后组成的新字符串。",
        "input_format": "输入两行，分别代表字符串 text1 和 text2。",
        "output_format": "输出一个整数，代表最长公共子序列的长度。",
        "examples": json.dumps([
            {"input": "abcde\nace", "output": "3", "explanation": "最长公共子序列是 'ace'，长度为 3。"}
        ]),
        "constraints": "1 <= text1.length, text2.length <= 1000, 仅包含小写字母",
        "hint": "使用动态规划。定义 dp[i][j] 为 text1 前 i 个字符与 text2 前 j 个字符的 LCS 长度。转移方程为：当字符相等时，dp[i][j] = dp[i-1][j-1]+1；不相等时，dp[i][j] = max(dp[i-1][j], dp[i][j-1])。",
        "score_reward": 70,
        "score_penalty": 20,
        "time_limit_sec": 1800
    },
    {
        "question_id": "q026",
        "title": "0-1 背包问题最优解",
        "difficulty": "hard",
        "min_tier": "diamond",
        "category": "数据结构-引言与算法分析-算法时间/空间复杂度",
        "knowledge_tags": json.dumps(["动态规划", "0-1背包", "空间优化"]),
        "description": "给定 N 个物品，每个物品有对应的重量 w[i] 和价值 v[i]。现有一个容量为 W 的背包，问如何选择物品放入背包，使得背包内物品的价值总和最大。每种物品只能选择放入 0 次或 1 次。",
        "input_format": "第一行输入两个整数 N 和 W。第二行输入 N 个整数表示每个物品的重量。第三行输入 N 个整数表示每个物品的价值。",
        "output_format": "输出背包所能容纳的最大物品价值总和。",
        "examples": json.dumps([
            {"input": "3 4\n1 3 4\n15 20 30", "output": "35", "explanation": "选择重量为 1 的价值15物品与重量为 3 的价值20物品放入背包，重 4 ，总价值 35，比单独放重4价值30的物品优。"}
        ]),
        "constraints": "1 <= N <= 1000, 1 <= W <= 1000, 重量与价值均不超过 1000",
        "hint": "利用动态规划 dp[j] 表示容量为 j 时的最大价值。状态转移需要逆序遍历背包容量 j：dp[j] = max(dp[j], dp[j - w[i]] + v[i]) 以免同一个物品被重复装入。",
        "score_reward": 70,
        "score_penalty": 20,
        "time_limit_sec": 1800
    },
    {
        "question_id": "q027",
        "title": "拓扑排序与关键路径",
        "difficulty": "hard",
        "min_tier": "king",
        "category": "数据结构-图-最小生成树与最短路径",
        "knowledge_tags": json.dumps(["拓扑排序", "关键路径", "DAG", "图论"]),
        "description": "给定一个有向无环图（DAG），每条边表示一个子任务的执行时间。求完成整个工程所需的最短时间（即关键路径的长度 / 源点到汇点的最长路径长度）。",
        "input_format": "第一行输入顶点个数 N 和有向边数 M。接下来的 M 行，每行输入三个整数 u, v, w，表示 u 到 v 之间有一条耗时为 w 的有向边（节点从 1 到 N）。",
        "output_format": "输出完成工程的最短时间（如果图存在环则输出 -1）。",
        "examples": json.dumps([
            {"input": "4 4\n1 2 3\n1 3 2\n2 4 4\n3 4 6", "output": "8", "explanation": "1->2->4 的路径总长为 7；1->3->4 的路径总长为 8。关键路径长度为 8，是决定整个工程能否完成的决定性工期。"}
        ]),
        "constraints": "1 <= N <= 1000, 0 <= M <= 5000, 1 <= w <= 1000",
        "hint": "关键路径即 DAG 的最长路径。通过拓扑排序确定节点的更新拓扑顺序，然后应用动态规划求最长路径：dist[v] = max(dist[v], dist[u] + weight(u, v))。",
        "score_reward": 90,
        "score_penalty": 30,
        "time_limit_sec": 2400
    },
    {
        "question_id": "q028",
        "title": "贝叶斯网络条件概率计算",
        "difficulty": "hard",
        "min_tier": "king",
        "category": "人工智能技术-不确定性与概率推理-贝叶斯网络建模",
        "knowledge_tags": json.dumps(["概率推理", "贝叶斯定理", "条件概率"]),
        "description": "已知一个简单的贝叶斯网络：事件 A 发生的先验概率为 P(A)；在 A 发生和不发生的前提下，事件 B 发生的条件概率分别为 P(B|A) 和 P(B|~A)。请计算在观察到 B 发生的条件下，A 发生的概率 P(A|B)。",
        "input_format": "一行包含三个浮点数，分别为 P(A), P(B|A), P(B|~A)。",
        "output_format": "输出条件概率 P(A|B) 的值（保留四位小数）。",
        "examples": json.dumps([
            {"input": "0.01 0.9 0.05", "output": "0.1538", "explanation": "根据贝叶斯公式: P(A|B) = P(B|A)*P(A) / [P(B|A)*P(A) + P(B|~A)*P(~A)] = 0.9*0.01 / (0.9*0.01 + 0.05*0.99) = 0.009 / 0.0585 ≈ 0.1538。"}
        ]),
        "constraints": "0 < P(A), P(B|A), P(B|~A) < 1",
        "hint": "利用全概率公式求 P(B) = P(B|A)*P(A) + P(B|~A)*P(~A)，再利用贝叶斯公式求 P(A|B)。",
        "score_reward": 80,
        "score_penalty": 25,
        "time_limit_sec": 1800
    },
    {
        "question_id": "q029",
        "title": "MDP 马尔可夫决策过程值迭代",
        "difficulty": "hard",
        "min_tier": "king",
        "category": "人工智能技术-不确定性与概率推理-马尔可夫决策过程 (MDP)",
        "knowledge_tags": json.dumps(["MDP", "值迭代", "Bellman方程"]),
        "description": "给定一个包含 2 个状态 S = {0, 1} 和 2 个动作 A = {0, 1} 的简化马尔可夫决策过程（MDP）。给定折扣因子 gamma，状态转移概率 P(s'|s,a)，以及即时奖励 R(s,s',a)。请进行 1 次 Bellman 期望方程更新（从全 0 价值矩阵 V 初始状态开始，即 V0(s)=0），计算并输出第一轮更新后状态 0 的最大状态价值 V1(0)。",
        "input_format": "第一行输入折扣因子 gamma (0 <= gamma < 1)。\n第二行输入四个浮点数，分别表示在状态0下执行动作0转移到状态0和1的概率 P(0|0,0), P(1|0,0)。\n第三行输入四个浮点数，表示在状态0下执行动作1转移到状态0和1的概率 P(0|0,1), P(1|0,1)。\n第四行输入对应的动作即时回报 R(0,0,0) 和 R(0,1,0)。\n第五行输入即时回报 R(0,0,1) 和 R(0,1,1)。",
        "output_format": "输出第一步值迭代后状态 0 的最大期望价值 V1(0)（保留两位小数）。",
        "examples": json.dumps([
            {"input": "0.9\n0.5 0.5\n0.8 0.2\n5 10\n2 8", "output": "7.50", "explanation": "对于动作0: Q(0,0) = 0.5*(5+0.9*0) + 0.5*(10+0.9*0) = 2.5 + 5 = 7.5。对于动作1: Q(0,1) = 0.8*(2+0.9*0) + 0.2*(8+0.9*0) = 1.6 + 1.6 = 3.2。最大期望价值为 max(7.5, 3.2) = 7.50。"}
        ]),
        "constraints": "0 <= gamma < 1, 状态转移概率之和为 1.0",
        "hint": "Bellman 最佳值方程的值迭代公式为 V1(s) = max_a [ sum_{s'} P(s'|s,a) * [R(s,s',a) + gamma * V0(s')] ]。初始 V0=0，直接求最大期望回报动作即可。",
        "score_reward": 90,
        "score_penalty": 30,
        "time_limit_sec": 2400
    },
    {
        "question_id": "q030",
        "title": "命题逻辑归结推理",
        "difficulty": "hard",
        "min_tier": "king",
        "category": "人工智能技术-知识表达与逻辑推理-一阶逻辑与推理机",
        "knowledge_tags": json.dumps(["命题逻辑", "归结原理", "推理机", "逻辑推理"]),
        "description": "给定两个包含文字的子句 C1 和 C2（文字为命题变量 A, B, C... 或它们的否定 ~A, ~B...，表示为由空格分隔的文字集合），请计算它们的一步归结式（Resolvent）。归结原理：如果子句 C1 中包含文字 L，而 C2 中包含文字 ~L，则它们可以消去 L 和 ~L，产生一个归结式 (C1 - {L}) ∪ (C2 - {~L})。如果有多个可消去的文字对，则只选其中一对进行归结。输出归结式子句中的文字（如果归结式是空子句，输出 'NIL'，如果不可归结，输出 'NONE'。对结果字符去重后排序输出）。",
        "input_format": "第一行输入子句 C1 的文字列表，以空格分隔。\n第二行输入子句 C2 的文字列表，以空格分隔。",
        "output_format": "排序输出归结子句的文字（以空格分隔），或输出 'NIL' / 'NONE'。",
        "examples": json.dumps([
            {"input": "A B ~C\nC D", "output": "A B D", "explanation": "~C 与 C 可以对消，剩余合并为 A, B, D。排序后输出 'A B D'。"},
            {"input": "A\n~A", "output": "NIL", "explanation": "归结后为空子句，输出 NIL。"},
            {"input": "A B\nC D", "output": "NONE", "explanation": "没有互补的文字，无法归结。"}
        ]),
        "constraints": "子句文字数目不超过 20",
        "hint": "遍历 C1 的每个文字 L，查找 C2 中是否存在其互补符号 ~L。若找到，则消除这两者并对剩余元素进行并集、去重和字典序排序。",
        "score_reward": 85,
        "score_penalty": 25,
        "time_limit_sec": 2400
    }
]


def seed_questions() -> dict[str, int]:
    db = SessionLocal()
    inserted = 0
    skipped = 0
    try:
        # 确保数据表已经创建
        from app.models.ranked_question import RankedQuestion
        from app.core.database import Base, engine
        Base.metadata.create_all(bind=engine)

        for qdata in QUESTIONS_SEED_DATA:
            existing = db.query(RankedQuestion).filter(
                RankedQuestion.question_id == qdata["question_id"]
            ).first()
            if existing:
                # 若已存在，进行更新确保数据一致
                for key, val in qdata.items():
                    setattr(existing, key, val)
                skipped += 1
            else:
                db.add(RankedQuestion(**qdata))
                inserted += 1
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error seeding questions: {e}")
        raise e
    finally:
        db.close()
    return {"inserted": inserted, "updated": skipped}


if __name__ == "__main__":
    res = seed_questions()
    print(f"Questions Seeding completed: Inserted {res['inserted']} new, Updated {res['updated']} existing.")
