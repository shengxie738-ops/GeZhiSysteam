import { ref, watch } from 'vue';

export const mockStudents = ref([
    { id: 1, name: '张子豪', avatar: 'Felix', goal: '大语言模型底层架构 - Attention', progress: 35, status: 'active', currentAgent: 'Alina (规划师)', focus: 85, alert: false },
    { id: 2, name: '李心悦', avatar: 'Aneka', goal: 'React Fiber 源码解析', progress: 78, status: 'active', currentAgent: 'CodeNinja', focus: 92, alert: false },
    { id: 3, name: '王明', avatar: 'Jude', goal: 'Vue 3 Proxy 响应式原理', progress: 12, status: 'active', currentAgent: 'Prof. X', focus: 35, alert: true },
    { id: 4, name: '赵佳佳', avatar: 'Mimi', goal: 'LangChain 链式调用基础', progress: 55, status: 'offline', currentAgent: null, focus: 0, alert: false },
    { id: 5, name: '刘宇', avatar: 'Jack', goal: '微积分 - 泰勒展开式', progress: 88, status: 'active', currentAgent: 'Prof. X', focus: 70, alert: false },
    { id: 6, name: '陈思思', avatar: 'Luna', goal: 'Docker 容器化部署实战', progress: 42, status: 'active', currentAgent: 'DataBot', focus: 45, alert: true }
]);

export const rawNodes = [
    { name: '概念与认知', value: 'done', desc: '了解大模型发展史及基本分类，掌握最基础的 Prompt 编写与结构设计。', resources: ['《大语言模型导论》', 'OpenAI 官方 Prompt 指南'] },
    { name: '核心原理深度解析', value: 'doing', desc: 'Transformer 结构、Self-Attention 机制结构详解，以及其前向传播计算过程推导。', resources: ['《Attention Is All You Need》经典论文', 'Illustrated Transformer 交互式博客'] },
    { name: '微调与本地部署', value: 'pending', desc: 'LoRA, P-Tuning 等微调技术机制，以及使用 Ollama/Llama.cpp 实现本地大模型量化及运行。', resources: ['HuggingFace PEFT 微调实践', 'Ollama 本地化部署手册'] },
    { name: '检索增强生成 (RAG)', value: 'pending', desc: '向量数据库搭建，文档解析分块，嵌入（Embeddings）向量化，以及混合检索（Hybrid Search）优化。', resources: ['LangChain RAG 知识检索系统架构', 'Pinecone / Milvus 接入实操'] },
    { name: '多智能体框架开发', value: 'pending', desc: '基于 MetaGPT/AutoGen 开发能够自主规划并协同工作的智能体群组，掌握 ReAct 提示词模式与 Tool Calling。', resources: ['MetaGPT 智能体协作架构白皮书', 'Microsoft AutoGen 多智能体开发教程'] }
];

export const chartLinks = [
    { source: '概念与认知', target: '核心原理深度解析', lineStyle: { color: '#10B981', width: 3 } },
    { source: '核心原理深度解析', target: '微调与本地部署', lineStyle: { color: '#3B82F6', width: 2, type: 'dashed' } },
    { source: '核心原理深度解析', target: '检索增强生成 (RAG)', lineStyle: { color: '#3B82F6', width: 2, type: 'dashed' } },
    { source: '微调与本地部署', target: '多智能体框架开发', lineStyle: { color: '#CBD5E1', width: 2 } },
    { source: '检索增强生成 (RAG)', target: '多智能体框架开发', lineStyle: { color: '#CBD5E1', width: 2 } }
];

const DEFAULT_AGENTS = [
    { id: 'agent_planner', name: 'Alina', role: '首席规划师', avatar: './assets/agents/alina.png', icon: 'ph-map-trifold', colorClass: 'bg-purple-500', isThinking: false, isActive: true, modelCategory: 'text', model: 'qwen3.7-max', prompt: '你负责分析用户的总体目标，并将其拆解为具体的学习路径和待办任务。' },
    { id: 'agent_tutor', name: 'Prof. X', role: '知识讲授导师', avatar: './assets/agents/profx.png', icon: 'ph-graduation-cap', colorClass: 'bg-blue-500', isThinking: false, isActive: true, modelCategory: 'text', model: 'qwen3.7-plus', prompt: '你是一位资深教授。请用费曼技巧向用户解释复杂的技术理论与概念。' },
    { id: 'agent_researcher', name: 'DataBot', role: '数据检索助手', avatar: './assets/agents/databot.png', icon: 'ph-magnifying-glass', colorClass: 'bg-emerald-500', isThinking: false, isActive: true, modelCategory: 'text', model: 'qwen3.6-plus', prompt: '你负责在本地知识库中进行 RAG (检索增强生成) 查询，提取关键信息。' },
    { id: 'agent_mistake_analyst', name: '错题分析师', role: '错题诊断与复习路径规划师', avatar: '', icon: 'ph-warning-diamond', colorClass: 'bg-rose-500', isThinking: false, isActive: true, modelCategory: 'text', model: 'qwen3.7-plus', prompt: '你是学生错题本的专属错题分析师。请基于题目、学生答案、正确答案、系统错因和知识标签，诊断学生的认知偏差，解释关键知识点，并生成具体练习建议与复习路径。输出必须贴合当前错题，不要给模板化结论。' },
    { id: 'agent_coder', name: 'CodeNinja', role: '代码演示助手', avatar: './assets/agents/codeninja.png', icon: 'ph-code', colorClass: 'bg-slate-700', isThinking: false, isActive: true, modelCategory: 'text', model: 'kimi-k2.7-code', prompt: '你专注于编写高质量的代码示例。提供带有详尽注释的代码片段。' },
    { id: 'agent_visual_guide', name: 'Mira', role: 'AI引导图生成师', avatar: '', icon: 'ph-flow-arrow', colorClass: 'bg-white', avatarShellClass: 'bg-white shadow-[0_10px_24px_rgba(28,43,56,0.10)] border border-white/80', iconTextClass: 'text-[#1c2b38] text-[18px]', isThinking: false, isActive: true, modelCategory: 'image', model: 'qwen-image-2.0-pro', prompt: '把左侧问题转译成概念图与步骤图。你负责根据学习问题生成通俗易懂的 AI 引导图，帮助学生理解抽象知识结构。' },
    { id: 'agent_ranked_coach', name: '排位赛AI教练', role: '排位诊断与冲分策略教练', avatar: '', icon: 'ph-robot', colorClass: 'bg-orange-500', isThinking: false, isActive: true, modelCategory: 'text', model: 'qwen3.7-plus', prompt: '你是排位赛 AI 教练。请基于学生的排位积分、段位、对战记录、错题现象和知识点薄弱项，给出具体的错题诊断、补强训练、限时刷题、连胜/连败管理和赛季冲分计划。回答要具体、可执行，并优先服务于提升竞技排位赛表现。' }
];

const savedAgentsStr = localStorage.getItem('agents_config');
let initialAgents = DEFAULT_AGENTS;
if (savedAgentsStr) {
    try {
        initialAgents = JSON.parse(savedAgentsStr);
    } catch (e) {
        console.error('Failed to parse agents from localStorage', e);
    }
}

export const agents = ref(initialAgents);

watch(agents, (newVal) => {
    localStorage.setItem('agents_config', JSON.stringify(newVal));
}, { deep: true });

export const courseMindmaps = {
    'data_structure': {
        name: '数据结构',
        value: 'root',
        desc: '《数据结构》核心课程思维导图',
        children: [
            {
                name: '引言与算法分析',
                value: 'done',
                desc: '学习数据结构的基本概念，以及算法的时间复杂度和空间复杂度分析方法。',
                resources: ['1-引言.ppt'],
                children: [
                    { name: '数据结构基本概念', value: 'done', desc: '掌握什么是数据、数据元素、数据结构及逻辑结构与物理结构分类。', resources: ['1-引言.ppt'] },
                    { name: '算法时间/空间复杂度', value: 'done', desc: '学习大O表示法，计算常见算法（如循环、递归）的时间复杂度。', resources: ['1-引言.ppt'] }
                ]
            },
            {
                name: '线性表',
                value: 'doing',
                desc: '系统学习线性表的定义、顺序存储与链式存储结构，掌握常见链表操作。',
                resources: ['2-线性表.pdf'],
                children: [
                    { name: '顺序表与数组实现', value: 'done', desc: '顺序表的连续内存分配、随机访问特性及其插入和删除算法复杂度。', resources: ['2-线性表.pdf'] },
                    { name: '单链表与双向链表', value: 'doing', desc: '理解链式存储的指针原理，手写实现单链表的插入、删除、反转操作。', resources: ['2-线性表.pdf'] }
                ]
            },
            {
                name: '栈与队列',
                value: 'pending',
                desc: '掌握这两种操作受限的特殊线性表，理解其在系统调用、递归和缓冲区中的应用。',
                resources: ['3-栈.pdf', '4-队列.pdf'],
                children: [
                    { name: '栈的特性及表达式求值', value: 'pending', desc: '后进先出（LIFO）特性，利用栈实现中缀表达式转后缀表达式及括号匹配。', resources: ['3-栈.pdf'] },
                    { name: '队列特性及循环队列', value: 'pending', desc: '先进先出（FIFO）特性，掌握循环队列的判满/判空条件及指针计算。', resources: ['4-队列.pdf'] }
                ]
            },
            {
                name: '树与二叉树',
                value: 'pending',
                desc: '深入学习树的层级结构、二叉树性质、树与二叉树的转换以及二叉树的遍历算法。',
                resources: ['5-树.ppt'],
                children: [
                    { name: '二叉树遍历算法', value: 'pending', desc: '掌握前序、中序、后序遍历的递归与非递归实现，以及层次遍历。', resources: ['5-树.ppt'] },
                    { name: '哈夫曼树与编码', value: 'pending', desc: '理解最优二叉树的概念，掌握哈夫曼树的构建过程及其在数据压缩中的应用。', resources: ['5-树.ppt'] }
                ]
            },
            {
                name: '图',
                value: 'pending',
                desc: '掌握图的表示（邻接矩阵、邻接表）、深度优先/广度优先遍历以及图的经典应用算法。',
                resources: ['7-图.pdf'],
                children: [
                    { name: '图的遍历 (DFS/BFS)', value: 'pending', desc: '掌握深度优先搜索与广度优先搜索的算法思想、代码实现与复杂度。', resources: ['7-图.pdf'] },
                    { name: '最小生成树与最短路径', value: 'pending', desc: '手写 Prim/Kruskal 最小生成树算法及 Dijkstra 最短路径算法。', resources: ['7-图.pdf'] }
                ]
            }
        ]
    },
    'computer_programming': {
        name: '计算机程序设计',
        value: 'root',
        desc: '《计算机程序设计》核心课程思维导图',
        children: [
            {
                name: '程序设计基础',
                value: 'done',
                desc: '学习 C++ 程序设计基本概念，控制流程与输入输出。',
                resources: ['ch03 逻辑思维及分支程序设计.ppt', 'ch04 循环控制.ppt'],
                children: [
                    { name: '分支逻辑与控制结构', value: 'done', desc: '掌握 if-else, switch-case 等分支结构，培养计算逻辑思维。', resources: ['ch03 逻辑思维及分支程序设计.ppt'] },
                    { name: '循环迭代控制', value: 'done', desc: '理解 for, while, do-while 循环的执行流程，掌握循环控制关键字 break/continue。', resources: ['ch04 循环控制.ppt'] }
                ]
            },
            {
                name: '数组与函数',
                value: 'done',
                desc: '掌握批量数据存储结构（数组）与面向过程封装的核心概念（函数）。',
                resources: ['ch05 批量数据处理—数组.ppt', 'ch06 过程封装－－函数.ppt'],
                children: [
                    { name: '一维与二维数组', value: 'done', desc: '了解数组的连续内存空间设计，进行排序、查找等常用数组操作。', resources: ['ch05 批量数据处理—数组.ppt'] },
                    { name: '函数定义与参数传递', value: 'done', desc: '掌握值传递、指针传递与引用传递的区别，理解作用域与生命周期。', resources: ['ch06 过程封装－－函数.ppt'] }
                ]
            },
            {
                name: '指针与结构体',
                value: 'doing',
                desc: '理解 C++ 底层内存地址操作（指针）以及自定义复合数据结构（结构体）。',
                resources: ['ch07 间接访问—指针.pptx', 'ch08 数据封装—结构体.ppt'],
                children: [
                    { name: '指针与内存地址', value: 'doing', desc: '理解取地址符 & 与解引用符 *，掌握指针运算、动态内存分配（new/delete）。', resources: ['ch07 间接访问—指针.pptx'] },
                    { name: '结构体与链表初步', value: 'pending', desc: '使用 struct 封装数据，掌握指向结构体的指针，并尝试构建简单单链表。', resources: ['ch08 数据封装—结构体.ppt'] }
                ]
            },
            {
                name: '面向对象基础',
                value: 'pending',
                desc: '掌握类与对象、封装、继承与多态，理解面向对象设计方法。',
                resources: ['ch10 创建功能更强的类型.ppt', 'ch12 组合与继承.ppt'],
                children: [
                    { name: '类定义与成员函数', value: 'pending', desc: '封装的意义，定义私有与公有成员，掌握构造函数与析构函数的执行时机。', resources: ['ch10 创建功能更强的类型.ppt'] },
                    { name: '多态与虚函数', value: 'pending', desc: '理解基类与派生类的继承关系，通过虚函数（virtual）与动态绑定实现运行时多态。', resources: ['ch12 组合与继承.ppt'] }
                ]
            }
        ]
    },
    'AI_technology': {
        name: '人工智能技术',
        value: 'root',
        desc: '《人工智能技术》核心课程思维导图',
        children: [
            {
                name: '搜索与问题求解',
                value: 'done',
                desc: '学习经典人工智能的图搜索与问题求解框架。',
                resources: ['3-uninformedSearch.ppt', '4-Informed Search and Exploration.ppt'],
                children: [
                    { name: '盲目搜索算法', value: 'done', desc: '掌握宽度优先搜索（BFS）、深度优先搜索（DFS）及一致代价搜索（UCS）原理与实现。', resources: ['3-uninformedSearch.ppt'] },
                    { name: '启发式搜索与 A* 算法', value: 'done', desc: '理解启发式函数，掌握贪婪最佳优先搜索及 A* 搜索的优缺点与采纳性条件。', resources: ['4-Informed Search and Exploration.ppt'] }
                ]
            },
            {
                name: '知识表达与逻辑推理',
                value: 'doing',
                desc: '学习如何使用逻辑智能体来表示世界的知识，并进行确定性的推理决策。',
                resources: ['7-Logical Agents.ppt', '8-First-Order Logic.ppt'],
                children: [
                    { name: '命题逻辑智能体', value: 'done', desc: '理解命题逻辑语法与语义，利用归结原理（Resolution）和蕴含关系进行推理。', resources: ['7-Logical Agents.ppt'] },
                    { name: '一阶逻辑与推理机', value: 'doing', desc: '一阶逻辑（FOL）的量词与谓词，掌握前向链接、后向链接和合一操作。', resources: ['8-First-Order Logic.ppt'] }
                ]
            },
            {
                name: '不确定性与概率推理',
                value: 'pending',
                desc: '针对现实世界的不确定性，学习基于概率论的推理和复杂决策机制。',
                resources: ['13-uncertainty.ppt', '14-Probabilistic Reasoning.ppt'],
                children: [
                    { name: '贝叶斯网络建模', value: 'pending', desc: '理解贝叶斯网络的拓扑结构与条件独立性，掌握网络中概率分布的精确推理算法。', resources: ['14-Probabilistic Reasoning.ppt'] },
                    { name: '马尔可夫决策过程 (MDP)', value: 'pending', desc: '理解状态、动作、奖励与状态转移概率，掌握值迭代（Value Iteration）算法。', resources: ['17-making_complex_decisions.ppt'] }
                ]
            }
        ]
    },
    'computer_organization': {
        name: '计算机组成原理',
        value: 'root',
        desc: '《计算机组成原理》核心课程思维导图',
        children: [
            {
                name: '计算机系统概述',
                value: 'done',
                desc: '学习计算机系统的基本结构、冯诺依曼架构及性能指标。',
                resources: ['01_Introduction_fang.pdf', '03_Top Level View of Computer Function and Interconnection_fang.pdf'],
                children: [
                    { name: '冯诺依曼结构与五大部件', value: 'done', desc: '掌握运算器、控制器、存储器、输入设备和输出设备的核心作用与互连方式。', resources: ['01_Introduction_fang.pdf'] },
                    { name: '系统总线与互连结构', value: 'done', desc: '掌握总线的概念、分类（数据/地址/控制总线），以及串行总线与并行总线的区别。', resources: ['03_Top Level View of Computer Function and Interconnection_fang.pdf'] }
                ]
            },
            {
                name: '指令系统与计算',
                value: 'done',
                desc: '掌握计算机硬/软件的交界界面——指令系统，以及数据在底层的运算实现。',
                resources: ['04a_ Instructions Language of the Computer_fang.pdf', 'Chapter 3 Arithmetic for Computers.pdf'],
                children: [
                    { name: 'MIPS 指令集与寻址方式', value: 'done', desc: '理解汇编指令、寄存器使用规范，掌握立即数寻址、寄存器寻址等常见方式。', resources: ['04a_ Instructions Language of the Computer_fang.pdf'] },
                    { name: '定点数与浮点数运算', value: 'done', desc: '理解补码加减运算、溢出检测，掌握 IEEE 754 浮点数表示格式及运算流程。', resources: ['Chapter 3 Arithmetic for Computers.pdf'] }
                ]
            },
            {
                name: '单周期与流水线处理器',
                value: 'doing',
                desc: '深入学习处理器的内部架构（CPU），掌握单周期通路与流水线技术。',
                resources: ['05a_The Processor_fang.pdf', '05b_The Processor_fang.pdf'],
                children: [
                    { name: '数据通路与控制逻辑设计', value: 'doing', desc: '分析 ALU、寄存器堆、程序计数器（PC）在单周期中的数据流向与控制信号。', resources: ['05a_The Processor_fang.pdf'] },
                    { name: '流水线冲突与冲突处理', value: 'pending', desc: '理解流水线加速原理，掌握结构冲突、数据冲突（前旁路技术）、控制冲突的处理机制。', resources: ['05b_The Processor_fang.pdf'] }
                ]
            },
            {
                name: '存储器层次体系',
                value: 'pending',
                desc: '解决 CPU 高速与主存慢速之间的矛盾，深入学习层次化存储结构设计。',
                resources: ['06a_Large and Fast Exploiting Memory Hierarchy_fang.pdf'],
                children: [
                    { name: '高速缓存 (Cache) 映射', value: 'pending', desc: '掌握直接映射、全相联映射和组相联映射的原理、地址格式划分及写策略。', resources: ['06a_Large and Fast Exploiting Memory Hierarchy_fang.pdf'] },
                    { name: '虚拟存储器与 TLB', value: 'pending', desc: '理解页表与虚拟地址转换，掌握快表（TLB）的作用及缺页处理过程。', resources: ['06a_Large and Fast Exploiting Memory Hierarchy_fang.pdf'] }
                ]
            }
        ]
    },
    'database_technology': {
        name: '数据库系统原理',
        value: 'root',
        desc: '《数据库系统原理》核心课程思维导图',
        children: [
            {
                name: '关系模型与 SQL',
                value: 'done',
                desc: '理解关系代数、SQL 语言与关系数据模型。',
                resources: ['L2_Model.pdf', 'L3_SQL.pdf'],
                children: [
                    { name: '关系模型与完整性约束', value: 'done', desc: '掌握关系模型的定义，主键、外键、实体完整性、参照完整性定义。', resources: ['L2_Model.pdf'] },
                    { name: 'SQL 复杂数据查询', value: 'done', desc: '手写多表连接、嵌套子查询、聚合函数与 GROUP BY, HAVING 等高级 SQL 指令。', resources: ['L3_SQL.pdf'] }
                ]
            },
            {
                name: '数据库建模与规范化',
                value: 'done',
                desc: '学习数据库逻辑结构设计规范，掌握从 E-R 模型到关系表的映射及范式分析。',
                resources: ['L6_ER1.pdf', 'L8_Design1.pdf'],
                children: [
                    { name: 'E-R 模型概念设计', value: 'done', desc: '绘制实体-联系图（E-R图），映射多元联系，并将其转换为规范的关系模式。', resources: ['L6_ER1.pdf'] },
                    { name: '关系范式与函数依赖', value: 'done', desc: '理解第一范式、第二范式、第三范式及 BCNF 范式，掌握模式分解的无损连接与依赖保持性。', resources: ['L8_Design1.pdf'] }
                ]
            },
            {
                name: '物理存储与索引结构',
                value: 'doing',
                desc: '探索关系数据库底层的物理实现，学习高效的文件管理与索引查询方法。',
                resources: ['L10_Storage.pdf', 'L11_Indexing.pdf'],
                children: [
                    { name: '磁盘空间管理与文件记录', value: 'doing', desc: '了解定长/变长记录的块组织结构，理解文件的聚簇存储方案。', resources: ['L10_Storage.pdf'] },
                    { name: 'B+ 树与哈希索引', value: 'pending', desc: '掌握 B+ 树索引的内部节点分叉与顺序检索设计，分析其插入/删除分裂合并操作。', resources: ['L11_Indexing.pdf'] }
                ]
            },
            {
                name: '事务管理与并发控制',
                value: 'pending',
                desc: '解决多用户并发访问时的数据安全保障，确保数据库的 ACID 属性。',
                resources: ['L13_Transaction.pdf'],
                children: [
                    { name: '并发冲突与封锁协议', value: 'pending', desc: '理解可串行化调度，掌握两段锁协议（2PL）以及死锁预防和检测方法。', resources: ['L13_Transaction.pdf'] }
                ]
            }
        ]
    }
};

export const codingProblems = [
    // === 大类 1：数组与链表 ===
    {
        id: 'two_sum',
        title: '两数之和',
        category: '数组与链表',
        funcName: 'twoSum',
        difficulty: 'Easy',
        tags: ['数组', '哈希表'],
        desc: '给定一个整数数组 `nums` 和一个目标值 `target`，请在该数组中找出和为目标值的那**两个**整数，并返回他们的数组下标。同一个元素不能使用两遍。\\n例如：`twoSum([2, 7, 11, 15], 9)` 应返回 `[0, 1]`。',
        initCode: `function twoSum(nums, target) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[2, 7, 11, 15], 9], expected: [0, 1], label: '常规测试' },
            { input: [[3, 2, 4], 6], expected: [1, 2], label: '无序数组' }
        ]
    },
    {
        id: 'reverse_list',
        title: '反转单链表',
        category: '数组与链表',
        funcName: 'reverseList',
        difficulty: 'Easy',
        tags: ['链表', '双指针'],
        ds: 'linkedlist',
        desc: '给你单链表的头节点 `head`，请你反转链表，并返回反转后的链表。\\n链表节点定义：`{ val: number, next: Node | null }`。',
        initCode: `function reverseList(head) {\n    // 在此编写你的代码\n    \n    return head;\n}`,
        testCases: [
            { input: [[1, 2, 3, 4, 5]], expected: [5, 4, 3, 2, 1], label: '常规链表反转' },
            { input: [[1, 2]], expected: [2, 1], label: '双节点链表' }
        ]
    },
    {
        id: 'merge_two_lists',
        title: '合并两个有序链表',
        category: '数组与链表',
        funcName: 'mergeTwoLists',
        difficulty: 'Easy',
        tags: ['链表', '递归'],
        ds: 'linkedlist_two',
        desc: '将两个升序链表合并为一个新的升序链表并返回。新链表是通过拼接给定的两个链表的所有节点组成的。',
        initCode: `function mergeTwoLists(l1, l2) {\n    // 在此编写你的代码\n    \n    return null;\n}`,
        testCases: [
            { input: [[1, 2, 4], [1, 3, 4]], expected: [1, 1, 2, 3, 4, 4], label: '常规合并' },
            { input: [[], [0]], expected: [0], label: '单侧空链表' }
        ]
    },
    {
        id: 'has_cycle',
        title: '环形链表检测',
        category: '数组与链表',
        funcName: 'hasCycle',
        difficulty: 'Easy',
        tags: ['链表', '快慢指针'],
        ds: 'linkedlist_cycle',
        desc: '给你一个链表的头节点 `head`，判断链表中是否有环。如果链表中有某个节点，可以通过连续跟踪 `next` 指针再次到达，则链表中存在环。返回 `true` 或 `false`。',
        initCode: `function hasCycle(head) {\n    // 在此编写你的代码\n    \n    return false;\n}`,
        testCases: [
            { input: [[3, 2, 0, -4], 1], expected: true, label: '带环链表' }, // 1表示索引1处有环
            { input: [[1, 2], -1], expected: false, label: '无环链表' }
        ]
    },
    {
        id: 'remove_nth_from_end',
        title: '删除倒数第 N 个节点',
        category: '数组与链表',
        funcName: 'removeNthFromEnd',
        difficulty: 'Medium',
        tags: ['链表', '双指针'],
        ds: 'linkedlist_num',
        desc: '给你一个链表，删除链表的倒数第 `n` 个结点，并且返回链表的头结点。',
        initCode: `function removeNthFromEnd(head, n) {\n    // 在此编写你的代码\n    \n    return head;\n}`,
        testCases: [
            { input: [[1, 2, 3, 4, 5], 2], expected: [1, 2, 3, 5], label: '删除倒数第2个' },
            { input: [[1], 1], expected: [], label: '删除唯一节点' }
        ]
    },

    // === 大类 2：栈与队列 ===
    {
        id: 'valid_parentheses',
        title: '有效的括号',
        category: '栈与队列',
        funcName: 'isValid',
        difficulty: 'Easy',
        tags: ['栈', '字符串'],
        desc: '给定一个只包括 `(\`, `)\`, `{\`, `}\`, `[\`, `]\` 的字符串 `s`，判断字符串是否有效。\\n有效需满足：左括号必须用相同类型的右括号闭合；左括号必须以正确的顺序闭合。',
        initCode: `function isValid(s) {\n    // 在此编写你的代码\n    \n    return false;\n}`,
        testCases: [
            { input: ["()[]{}"], expected: true, label: '多种括号闭合' },
            { input: ["(]"], expected: false, label: '未正确闭合' }
        ]
    },
    {
        id: 'min_stack',
        title: '最小栈设计',
        category: '栈与队列',
        funcName: 'testMinStack',
        difficulty: 'Medium',
        tags: ['栈', '设计'],
        desc: '设计一个支持 `push` ，`pop` ，`top` 操作，并能在常数时间内检索到最小元素的栈。\\n请实现包含这些操作的函数，在评测时系统会传入操作指令流并验证输出。',
        initCode: `// 请以类或构造函数形式实现 MinStack\nfunction testMinStack(commands, values) {\n    class MinStack {\n        constructor() { this.stack = []; this.minStack = []; }\n        push(x) {\n            this.stack.push(x);\n            if (this.minStack.length === 0 || x <= this.minStack[this.minStack.length-1]) this.minStack.push(x);\n        }\n        pop() {\n            const val = this.stack.pop();\n            if (val === this.minStack[this.minStack.length-1]) this.minStack.pop();\n        }\n        top() { return this.stack[this.stack.length-1]; }\n        getMin() { return this.minStack[this.minStack.length-1]; }\n    }\n    \n    const stack = new MinStack();\n    const out = [];\n    commands.forEach((cmd, i) => {\n        if (cmd === 'push') stack.push(values[i]);\n        else if (cmd === 'pop') stack.pop();\n        else if (cmd === 'top') out.push(stack.top());\n        else if (cmd === 'getMin') out.push(stack.getMin());\n    });\n    return out;\n}`,
        testCases: [
            { input: [['push', 'push', 'push', 'getMin', 'pop', 'top', 'getMin'], [-2, 0, -3, null, null, null, null]], expected: [-3, 0, -2], label: '最小栈连续操作' }
        ]
    },
    {
        id: 'queue_by_stacks',
        title: '用栈实现队列',
        category: '栈与队列',
        funcName: 'testMyQueue',
        difficulty: 'Easy',
        tags: ['栈', '队列', '设计'],
        desc: '请使用两个栈实现先入先出队列。队列应当支持 `push`、`pop`、`peek` 和 `empty` 操作。',
        initCode: `function testMyQueue(commands, values) {\n    // 用数组作为两个栈进行模拟\n    // 在此实现你的队列逻辑\n    return [];\n}`,
        testCases: [
            { input: [['push', 'push', 'peek', 'pop', 'empty'], [1, 2, null, null, null]], expected: [1, 1, false], label: '队列基础测试' }
        ]
    },
    {
        id: 'eval_rpn',
        title: '逆波兰表达式求值',
        category: '栈与队列',
        funcName: 'evalRPN',
        difficulty: 'Medium',
        tags: ['栈', '数学'],
        desc: '给你一个字符串数组 `tokens` ，表示一个根据逆波兰表示法表示的算术表达式。请计算该表达式的值，并返回结果。有效算符包括 `+`、`-`、`*`、`/`，除法应当只保留整数部分。',
        initCode: `function evalRPN(tokens) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [["2", "1", "+", "3", "*"]], expected: 9, label: '基础加乘' },
            { input: [["4", "13", "5", "/", "+"]], expected: 6, label: '带整除运算' }
        ]
    },
    {
        id: 'sliding_window_max',
        title: '滑动窗口最大值',
        category: '栈与队列',
        funcName: 'maxSlidingWindow',
        difficulty: 'Hard',
        tags: ['队列', '双端队列', '滑动窗口'],
        desc: '给你一个整数数组 `nums`，有一个大小为 `k` 的滑动窗口从数组的最左侧移动到数组的最右侧。你只可以看到在滑动窗口内的 `k` 个数字。滑动窗口每次只向右移动一位。返回滑动窗口中的最大值数组。',
        initCode: `function maxSlidingWindow(nums, k) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[1, 3, -1, -3, 5, 3, 6, 7], 3], expected: [3, 3, 5, 5, 6, 7], label: '常规移动滑窗' },
            { input: [[1], 1], expected: [1], label: '单元素滑窗' }
        ]
    },

    // === 大类 3：树与二叉树 ===
    {
        id: 'tree_max_depth',
        title: '二叉树的最大深度',
        category: '树与二叉树',
        funcName: 'maxDepth',
        difficulty: 'Easy',
        tags: ['树', '深度优先搜索'],
        ds: 'binarytree',
        desc: '给定一个二叉树，找出其最大深度。最大深度是从根节点到最远叶子节点的最长路径上的节点数。\\n树节点定义：`{ val: number, left: Node | null, right: Node | null }`。',
        initCode: `function maxDepth(root) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[3, 9, 20, null, null, 15, 7]], expected: 3, label: '标准满二叉树' },
            { input: [[1, null, 2]], expected: 2, label: '倾斜单侧树' }
        ]
    },
    {
        id: 'invert_tree',
        title: '翻转二叉树',
        category: '树与二叉树',
        funcName: 'invertTree',
        difficulty: 'Easy',
        tags: ['树', '广度优先搜索'],
        ds: 'binarytree_node',
        desc: '给你一棵二叉树的根节点 `root`，翻转这棵二叉树（即左右子树交换），并返回其根节点。',
        initCode: `function invertTree(root) {\n    // 在此编写你的代码\n    \n    return root;\n}`,
        testCases: [
            { input: [[4, 2, 7, 1, 3, 6, 9]], expected: [4, 7, 2, 9, 6, 3, 1], label: '满二叉树对称交换' },
            { input: [[2, 1, 3]], expected: [2, 3, 1], label: '三节点对称交换' }
        ]
    },
    {
        id: 'preorder_traversal',
        title: '二叉树的前序遍历',
        category: '树与二叉树',
        funcName: 'preorderTraversal',
        difficulty: 'Easy',
        tags: ['树', '栈'],
        ds: 'binarytree',
        desc: '给你二叉树的根节点 `root` ，返回它节点值的**前序**（根-左-右）遍历。',
        initCode: `function preorderTraversal(root) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[1, null, 2, 3]], expected: [1, 2, 3], label: '右倾且含子节点' },
            { input: [[]], expected: [], label: '空树' }
        ]
    },
    {
        id: 'inorder_traversal',
        title: '二叉树的中序遍历',
        category: '树与二叉树',
        funcName: 'inorderTraversal',
        difficulty: 'Easy',
        tags: ['树', '递归'],
        ds: 'binarytree',
        desc: '给你二叉树的根节点 `root` ，返回它节点值的**中序**（左-根-右）遍历。',
        initCode: `function inorderTraversal(root) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[1, null, 2, 3]], expected: [1, 3, 2], label: '典型右倾遍历' },
            { input: [[1, 2]], expected: [2, 1], label: '左子树遍历' }
        ]
    },
    {
        id: 'level_order',
        title: '二叉树的层序遍历',
        category: '树与二叉树',
        funcName: 'levelOrder',
        difficulty: 'Medium',
        tags: ['树', '队列'],
        ds: 'binarytree',
        desc: '给你二叉树的根节点 `root` ，返回其节点值的**层序遍历**。（即逐层地、从左往右访问所有节点）。返回一个二维数组，如 `[[3], [9, 20], [15, 7]]`。',
        initCode: `function levelOrder(root) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[3, 9, 20, null, null, 15, 7]], expected: [[3], [9, 20], [15, 7]], label: '标准层序遍历' }
        ]
    },

    // === 大类 4：排序与搜索 ===
    {
        id: 'bubble_sort',
        title: '冒泡排序的实现',
        category: '排序与搜索',
        funcName: 'bubbleSort',
        difficulty: 'Easy',
        tags: ['排序', '数组'],
        desc: '实现冒泡排序算法，将数组按升序进行排列，并返回排序后的原数组。',
        initCode: `function bubbleSort(arr) {\n    // 在此编写你的代码\n    \n    return arr;\n}`,
        testCases: [
            { input: [[5, 3, 8, 4, 2]], expected: [2, 3, 4, 5, 8], label: '常规排序' }
        ]
    },
    {
        id: 'quick_sort',
        title: '快速排序的实现',
        category: '排序与搜索',
        funcName: 'quickSort',
        difficulty: 'Medium',
        tags: ['分治', '排序'],
        desc: '实现快速排序算法，使用分治策略将输入数组按升序排列并返回。',
        initCode: `function quickSort(arr) {\n    // 在此编写你的代码\n    \n    return arr;\n}`,
        testCases: [
            { input: [[12, 11, 13, 5, 6]], expected: [5, 6, 11, 12, 13], label: '无序大数组' }
        ]
    },
    {
        id: 'binary_search',
        title: '二分查找',
        category: '排序与搜索',
        funcName: 'search',
        difficulty: 'Easy',
        tags: ['二分查找', '数组'],
        desc: '给定一个 `n` 个元素有序的（升序）整型数组 `nums` 和一个目标值 `target` ，写一个函数搜索 `nums` 中的 `target`，如果目标值存在返回下标，否则返回 `-1`。',
        initCode: `function search(nums, target) {\n    // 在此编写你的代码\n    \n    return -1;\n}`,
        testCases: [
            { input: [[-1, 0, 3, 5, 9, 12], 9], expected: 4, label: '存在该目标值' },
            { input: [[-1, 0, 3, 5, 9, 12], 2], expected: -1, label: '不存在该值' }
        ]
    },
    {
        id: 'merge_intervals',
        title: '合并区间',
        category: '排序与搜索',
        funcName: 'merge',
        difficulty: 'Medium',
        tags: ['数组', '排序'],
        desc: '以数组 `intervals` 表示若干个区间的集合，其中单个区间为 `intervals[i] = [starti, endi]`。请合并所有重叠的区间，并返回一个不重叠的区间数组。',
        initCode: `function merge(intervals) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[[1, 3], [2, 6], [8, 10], [15, 18]]], expected: [[1, 6], [8, 10], [15, 18]], label: '区间部分交错合并' },
            { input: [[[1, 4], [4, 5]]], expected: [[1, 5]], label: '区间边界贴合合并' }
        ]
    },
    {
        id: 'search_rotated',
        title: '搜索旋转排序数组',
        category: '排序与搜索',
        funcName: 'searchRotated',
        difficulty: 'Medium',
        tags: ['二分查找', '数组'],
        desc: '整数数组 `nums` 按升序排列，数组中的值互不相同。在传递给函数之前，`nums` 在预先未知的某个轴点上进行了旋转（例如 `[0,1,2,4,5,6,7]` 旋转后可能变为 `[4,5,6,7,0,1,2]`）。给你旋转后的数组和一个整数目标值，如果数组中存在这个目标值，则返回它的下标，否则返回 `-1`。',
        initCode: `function searchRotated(nums, target) {\n    // 在此编写你的代码\n    \n    return -1;\n}`,
        testCases: [
            { input: [[4, 5, 6, 7, 0, 1, 2], 0], expected: 4, label: '目标值在旋转轴后侧' },
            { input: [[4, 5, 6, 7, 0, 1, 2], 3], expected: -1, label: '不存在目标值' }
        ]
    },

    // === 大类 5：字符串与双指针 ===
    {
        id: 'is_palindrome',
        title: '验证回文字符串',
        category: '字符串与双指针',
        funcName: 'isPalindrome',
        difficulty: 'Easy',
        tags: ['双指针', '字符串'],
        desc: '如果在将所有大写字符转换为小写字符、并移除所有非字母数字字符之后，短语正着读和反着读都一样。则认为该短语是一个回文串。',
        initCode: `function isPalindrome(s) {\n    // 在此编写你的代码\n    \n    return false;\n}`,
        testCases: [
            { input: ["A man, a plan, a canal: Panama"], expected: true, label: '含标点回文字符串' },
            { input: ["race a car"], expected: false, label: '非回文字符串' }
        ]
    },
    {
        id: 'longest_substring',
        title: '无重复字符的最长子串',
        category: '字符串与双指针',
        funcName: 'lengthOfLongestSubstring',
        difficulty: 'Medium',
        tags: ['哈希表', '滑动窗口'],
        desc: '给定一个字符串 `s` ，请你找出其中不含有重复字符的**最长子串**的长度。',
        initCode: `function lengthOfLongestSubstring(s) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: ["abcabcbb"], expected: 3, label: '重叠字母最长子串' },
            { input: ["bbbbb"], expected: 1, label: '全相同字母' }
        ]
    },
    {
        id: 'max_area',
        title: '盛最多水的容器',
        category: '字符串与双指针',
        funcName: 'maxArea',
        difficulty: 'Medium',
        tags: ['数组', '双指针'],
        desc: '给定一个长度为 `n` 的整数数组 `height` 。有 `n` 条垂线，第 `i` 条线的两个端点是 `(i, 0)` 和 `(i, height[i])`。找出其中的两条线，使得它们与 x 轴共同构成的容器可以容纳最多的水。返回容器可以储存的最大水量。',
        initCode: `function maxArea(height) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[1, 8, 6, 2, 5, 4, 8, 3, 7]], expected: 49, label: '常规高度数组' },
            { input: [[1, 1]], expected: 1, label: '边界窄底容器' }
        ]
    },
    {
        id: 'three_sum',
        title: '三数之和',
        category: '字符串与双指针',
        funcName: 'threeSum',
        difficulty: 'Medium',
        tags: ['数组', '排序', '双指针'],
        desc: '给你一个整数数组 `nums` ，判断是否存在三元组 `[nums[i], nums[j], nums[k]]` 满足 `i != j`、`i != k` 且 `j != k` ，同时满足 `nums[i] + nums[j] + nums[k] == 0` 。请你返回所有和为 `0` 且不重复的三元组。',
        initCode: `function threeSum(nums) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[-1, 0, 1, 2, -1, -4]], expected: [[-1, -1, 2], [-1, 0, 1]], label: '常规数组' }
        ]
    },
    {
        id: 'min_window',
        title: '最小覆盖子串',
        category: '字符串与双指针',
        funcName: 'minWindow',
        difficulty: 'Hard',
        tags: ['哈希表', '字符串', '滑动窗口'],
        desc: '给你一个字符串 `s` 、一个字符串 `t` 。返回 `s` 中涵盖 `t` 所有字符的最小子串。如果 `s` 中不存在涵盖 `t` 所有字符的子串，则返回空字符串 `""`。',
        initCode: `function minWindow(s, t) {\n    // 在此编写你的代码\n    \n    return "";\n}`,
        testCases: [
            { input: ["ADOBECODEBANC", "ABC"], expected: "BANC", label: '覆盖窗口搜索' }
        ]
    },

    // === 大类 6：动态规划 ===
    {
        id: 'fibonacci',
        title: '斐波那契数列（第 N 项）',
        category: '动态规划',
        funcName: 'fibonacci',
        difficulty: 'Easy',
        tags: ['递归', '动态规划'],
        desc: '求斐波那契数列的第 `n` 项。`F(0)=0`, `F(1)=1`, `F(n)=F(n-1)+F(n-2)`。输入 `n <= 30`。',
        initCode: `function fibonacci(n) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [10], expected: 55, label: '求第10项' }
        ]
    },
    {
        id: 'climb_stairs',
        title: '爬楼梯',
        category: '动态规划',
        funcName: 'climbStairs',
        difficulty: 'Easy',
        tags: ['动态规划', '数学'],
        desc: '假设你正在爬楼梯。需要 `n` 阶你才能到达楼顶。每次你可以爬 `1` 或 `2` 个台阶。你有多少种不同的方法可以爬到楼顶呢？',
        initCode: `function climbStairs(n) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [2], expected: 2, label: '2阶楼梯' },
            { input: [3], expected: 3, label: '3阶楼梯' }
        ]
    },
    {
        id: 'max_sub_array',
        title: '最大子数组和',
        category: '动态规划',
        funcName: 'maxSubArray',
        difficulty: 'Easy',
        tags: ['数组', '分治', '动态规划'],
        desc: '给你一个整数数组 `nums` ，请你找出一个具有最大和的连续子数组（子数组最少包含一个元素），返回其最大和。',
        initCode: `function maxSubArray(nums) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[-2, 1, -3, 4, -1, 2, 1, -5, 4]], expected: 6, label: '中间连续大子数组' },
            { input: [[5, 4, -1, 7, 8]], expected: 23, label: '全正大子数组' }
        ]
    },
    {
        id: 'coin_change',
        title: '零钱兑换',
        category: '动态规划',
        funcName: 'coinChange',
        difficulty: 'Medium',
        tags: ['广度优先搜索', '数组', '动态规划'],
        desc: '给你一个整数数组 `coins` ，表示不同面额的硬币；以及一个整数 `amount` ，表示总金额。计算并返回可以凑成总金额所需的**最少的硬币个数**。如果没有任何一种硬币组合能组成总金额，返回 `-1`。',
        initCode: `function coinChange(coins, amount) {\n    // 在此编写你的代码\n    \n    return -1;\n}`,
        testCases: [
            { input: [[1, 2, 5], 11], expected: 3, label: '可以拼出最小硬币数' },
            { input: [[2], 3], expected: -1, label: '无法拼出该金额' }
        ]
    },
    {
        id: 'longest_lis',
        title: '最长递增子序列',
        category: '动态规划',
        funcName: 'lengthOfLIS',
        difficulty: 'Medium',
        tags: ['数组', '二分查找', '动态规划'],
        desc: '给你一个整数数组 `nums` ，找到其中最长严格递增子序列的长度。子序列是由数组派生而来的序列，删除（或不删除）数组中的元素而不改变其余元素的顺序。',
        initCode: `function lengthOfLIS(nums) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[10, 9, 2, 5, 3, 7, 101, 18]], expected: 4, label: '常规子序列查找' }
        ]
    },

    // === 大类 7：贪心与回溯 ===
    {
        id: 'max_profit',
        title: '买卖股票的最佳时机',
        category: '贪心与回溯',
        funcName: 'maxProfit',
        difficulty: 'Easy',
        tags: ['数组', '动态规划'],
        desc: '给定一个数组 `prices` ，它的第 `i` 个元素 `prices[i]` 表示一支给定股票第 `i` 天的价格。你只能选择某一天买入这只股票，并选择在未来的某一个不同的日子卖出该股票。设计一个算法来计算你所能获取的最大利润。返回你可以从这笔交易中获取的最大利润。如果你不能获取任何利润，返回 `0`。',
        initCode: `function maxProfit(prices) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[7, 1, 5, 3, 6, 4]], expected: 5, label: '常规买卖股票' },
            { input: [[7, 6, 4, 3, 1]], expected: 0, label: '股价单调下跌' }
        ]
    },
    {
        id: 'can_jump',
        title: '跳跃游戏',
        category: '贪心与回溯',
        funcName: 'canJump',
        difficulty: 'Medium',
        tags: ['贪心', '数组'],
        desc: '给你一个非负整数数组 `nums` ，你最初位于数组的**第一个下标**。数组中的每个元素代表你在该位置可以跳跃的最大长度。判断你是否能够到达最后一个下标。如果可以，返回 `true` ；否则，返回 `false` 。',
        initCode: `function canJump(nums) {\n    // 在此编写你的代码\n    \n    return false;\n}`,
        testCases: [
            { input: [[2, 3, 1, 1, 4]], expected: true, label: '可以顺利跳跃到达' },
            { input: [[3, 2, 1, 0, 4]], expected: false, label: '陷入0元素无法前进' }
        ]
    },
    {
        id: 'permute',
        title: '全排列',
        category: '贪心与回溯',
        funcName: 'permute',
        difficulty: 'Medium',
        tags: ['回溯', '数组'],
        desc: '给定一个不含重复数字的数组 `nums` ，返回其所有可能的全排列。你可以**按任意顺序**返回答案。',
        initCode: `function permute(nums) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[1, 2, 3]], expected: [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]], label: '三个元素的全排列' }
        ]
    },
    {
        id: 'subsets',
        title: '子集生成',
        category: '贪心与回溯',
        funcName: 'subsets',
        difficulty: 'Medium',
        tags: ['位运算', '回溯', '数组'],
        desc: '给你一个整数数组 `nums` ，数组中的元素**互不相同**。返回该数组所有可能的子集（幂集）。解集不能包含重复的子集。你可以按任意顺序返回解集。',
        initCode: `function subsets(nums) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[1, 2]], expected: [[], [1], [2], [1, 2]], label: '双元素集合子集' }
        ]
    },
    {
        id: 'generate_parentheses',
        title: '括号生成',
        category: '贪心与回溯',
        funcName: 'generateParenthesis',
        difficulty: 'Medium',
        tags: ['回溯', '字符串'],
        desc: '数字 `n` 代表生成括号的对数，请你设计一个函数，用于能够生成所有可能的并且**有效的**括号组合。',
        initCode: `function generateParenthesis(n) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [3], expected: ["((()))", "(()())", "(())()", "()(())", "()()()"], label: '生成3对括号组合' }
        ]
    },

    // === 大类 8：数学与趣味算法 ===
    {
        id: 'single_number',
        title: '只出现一次的数字',
        category: '数学与趣味算法',
        funcName: 'singleNumber',
        difficulty: 'Easy',
        tags: ['位运算', '数组'],
        desc: '给你一个非空整数数组 `nums` ，除了某个元素只出现一次以外，其余每个元素均出现两次。找出那个只出现了一次的元素。你必须设计并实现线性时间复杂度的算法，且仅使用常数级额外空间。',
        initCode: `function singleNumber(nums) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[2, 2, 1]], expected: 1, label: '单侧孤立元素' },
            { input: [[4, 1, 2, 1, 2]], expected: 4, label: '多对异或查找' }
        ]
    },
    {
        id: 'majority_element',
        title: '多数元素',
        category: '数学与趣味算法',
        funcName: 'majorityElement',
        difficulty: 'Easy',
        tags: ['计数', '哈希表', '分治'],
        desc: '给定一个大小为 `n` 的数组 `nums` ，返回其中的多数元素。多数元素是指在数组中出现次数大于 `⌊ n/2 ⌋` 的元素。你可以假设数组是非空的，并且给定的数组总是存在多数元素。',
        initCode: `function majorityElement(nums) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[3, 2, 3]], expected: 3, label: '简单占优元素' },
            { input: [[2, 2, 1, 1, 1, 2, 2]], expected: 2, label: '多数投票查找' }
        ]
    },
    {
        id: 'is_happy',
        title: '快乐数',
        category: '数学与趣味算法',
        funcName: 'isHappy',
        difficulty: 'Easy',
        tags: ['哈希表', '数学'],
        desc: '编写一个算法来判断一个数 `n` 是不是快乐数。快乐数定义：对于一个正整数，每一次将该数替换为它每个位置上的数字的平方和。然后重复这个过程直到这个数变为 1，也可能是无限循环但始终变不到 1。如果这个数最后变成了 1，那么这个数就是快乐数。如果是快乐数返回 `true` ；否则返回 `false` 。',
        initCode: `function isHappy(n) {\n    // 在此编写你的代码\n    \n    return false;\n}`,
        testCases: [
            { input: [19], expected: true, label: '经典快乐数' },
            { input: [2], expected: false, label: '无限循环非快乐数' }
        ]
    },
    {
        id: 'plus_one',
        title: '加一',
        category: '数学与趣味算法',
        funcName: 'plusOne',
        difficulty: 'Easy',
        tags: ['数组', '数学'],
        desc: '给定一个由**整数**组成的**非空**数组所表示的非负整数，在该数的基础上加一。最高位数字存放在数组的首位，数组中每个元素只存储单个数字。你可以假设除了整数 0 之外，这个整数不会以零开头。',
        initCode: `function plusOne(digits) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [[1, 2, 3]], expected: [1, 2, 4], label: '常规非进位' },
            { input: [[9, 9]], expected: [1, 0, 0], label: '连续最高位进位' }
        ]
    },
    {
        id: 'roman_to_int',
        title: '罗马数字转整数',
        category: '数学与趣味算法',
        funcName: 'romanToInt',
        difficulty: 'Easy',
        tags: ['字符串', '数学', '哈希表'],
        desc: '给定一个罗马数字，将其转换成整数。罗马数字包含以下七种字符: `I`， `V`， `X`， `L`，`C`，`D` 和 `M`。\\n例如，罗马数字 `III` 写做 `3` ，罗马数字 `IX` 特殊写作 `9`。',
        initCode: `function romanToInt(s) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: ["LVIII"], expected: 58, label: '加法罗马字符' },
            { input: ["MCMXCIV"], expected: 1994, label: '带减法前缀罗马字' }
        ]
    },
    // === 大类 1 扩充：数组与链表 (Hard) ===
    {
        id: 'merge_k_lists',
        title: '合并 K 个升序链表',
        category: '数组与链表',
        funcName: 'mergeKLists',
        difficulty: 'Hard',
        tags: ['链表', '分治', '堆（优先队列）'],
        ds: 'linkedlist_array',
        desc: '给你一个链表数组，每个链表都已经按升序排列。\\n请将所有链表合并为一个升序链表，返回合并后的链表。',
        initCode: `function mergeKLists(lists) {\n    // 在此编写你的代码\n    \n    return null;\n}`,
        testCases: [
            { input: [[[1, 4, 5], [1, 3, 4], [2, 6]]], expected: [1, 1, 2, 3, 4, 4, 5, 6], label: '合并三个升序链表' },
            { input: [[]], expected: [], label: '空链表数组' }
        ]
    },
    {
        id: 'reverse_k_group',
        title: 'K 个一组翻转链表',
        category: '数组与链表',
        funcName: 'reverseKGroup',
        difficulty: 'Hard',
        tags: ['链表', '递归'],
        ds: 'linkedlist_num',
        desc: '给你双向/单链表的头节点 `head` ，每 `k` 个节点一组进行翻转，返回修改后的链表。\\n`k` 是一个正整数，它的值小于或等于链表的长度。如果节点总数不是 `k` 的整数倍，那么请将最后剩余的节点保持原有顺序。',
        initCode: `function reverseKGroup(head, k) {\n    // 在此编写你的代码\n    \n    return head;\n}`,
        testCases: [
            { input: [[1, 2, 3, 4, 5], 2], expected: [2, 1, 4, 3, 5], label: '以2个节点为一组翻转' },
            { input: [[1, 2, 3, 4, 5], 3], expected: [3, 2, 1, 4, 5], label: '以3个节点为一组翻转' }
        ]
    },
    {
        id: 'find_median_sorted_arrays',
        title: '寻找两个正序数组的中位数',
        category: '数组与链表',
        funcName: 'findMedianSortedArrays',
        difficulty: 'Hard',
        tags: ['数组', '二分查找', '分治'],
        desc: '给定两个大小分别为 `m` 和 `n` 的正序（从小到大）数组 `nums1` 和 `nums2`。请你找出并返回这两个正序数组的 **中位数** 。\\n算法的时间复杂度应该为 `O(log (m+n))`。',
        initCode: `function findMedianSortedArrays(nums1, nums2) {\n    // 在此编写你的代码\n    \n    return 0.0;\n}`,
        testCases: [
            { input: [[1, 3], [2]], expected: 2.0, label: '奇数个总元素' },
            { input: [[1, 2], [3, 4]], expected: 2.5, label: '偶数个总元素' }
        ]
    },

    // === 大类 2 扩充：栈与队列 (Hard) ===
    {
        id: 'trap',
        title: '接雨水',
        category: '栈与队列',
        funcName: 'trap',
        difficulty: 'Hard',
        tags: ['栈', '双指针', '单调栈'],
        desc: '给定 `n` 个非负整数表示每个宽度为 `1` 的柱子的高度图，计算按此排列的柱子，下雨之后能接多少雨水。',
        initCode: `function trap(height) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]], expected: 6, label: '高低起伏地形' },
            { input: [[4, 2, 0, 3, 2, 5]], expected: 9, label: '深谷积水测试' }
        ]
    },
    {
        id: 'largest_rectangle_area',
        title: '柱状图中最大的矩形',
        category: '栈与队列',
        funcName: 'largestRectangleArea',
        difficulty: 'Hard',
        tags: ['栈', '数组', '单调栈'],
        desc: '给定非负整数数组 `heights` ，空间中相邻柱子宽度为 `1`。请找出并返回柱状图中能够勾勒出的最大矩形面积。',
        initCode: `function largestRectangleArea(heights) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[2, 1, 5, 6, 2, 3]], expected: 10, label: '常规柱状图' },
            { input: [[2, 4]], expected: 4, label: '双柱状图面积' }
        ]
    },
    {
        id: 'maximal_rectangle',
        title: '最大矩形面积',
        category: '栈与队列',
        funcName: 'maximalRectangle',
        difficulty: 'Hard',
        tags: ['栈', '数组', '动态规划', '单调栈'],
        desc: '给定一个仅包含 `0` 和 `1` 、大小为 `rows x cols` 的二维二进制矩阵，找出只包含 `1` 的最大矩形，并返回其面积。',
        initCode: `function maximalRectangle(matrix) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[["1","0","1","0","0"],["1","0","1","1","1"],["1","1","1","1","1"],["1","0","0","1","0"]]], expected: 6, label: '经典二进制网格' },
            { input: [[[]]], expected: 0, label: '空矩阵测试' }
        ]
    },

    // === 大类 3 扩充：树与二叉树 (Hard) ===
    {
        id: 'max_path_sum',
        title: '二叉树中的最大路径和',
        category: '树与二叉树',
        funcName: 'maxPathSum',
        difficulty: 'Hard',
        tags: ['树', '深度优先搜索', '动态规划'],
        ds: 'binarytree',
        desc: '二叉树中的 **路径** 被定义为一条节点序列，序列中相邻节点之间存在一条边。同一个节点在一条路径序列中 **至多出现一次** 。该路径至少包含一个节点，且不一定经过根节点。\\n**路径和** 是路径中各节点值的总和。给你一个二叉树的根节点 `root` ，返回其 **最大路径和** 。',
        initCode: `function maxPathSum(root) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[1, 2, 3]], expected: 6, label: '简单三节点树' },
            { input: [[-10, 9, 20, null, null, 15, 7]], expected: 42, label: '含负权根节点树' }
        ]
    },
    {
        id: 'serialize_deserialize',
        title: '二叉树的序列化与反序列化',
        category: '树与二叉树',
        funcName: 'testCodec',
        difficulty: 'Hard',
        tags: ['树', '深度优先搜索', '设计'],
        ds: 'binarytree_node',
        desc: '请设计一个算法，能将二叉树序列化为字符串，并且能将该字符串反序列化为原始的二叉树。\\n本题评测时会调用您的序列化与反序列化逻辑，并对比最终还原出的树。',
        initCode: `// 请实现 serialize 与 deserialize 并在入口函数中包装测试\nfunction testCodec(root) {\n    function serialize(node) {\n        if (!node) return '#';\n        return node.val + ',' + serialize(node.left) + ',' + serialize(node.right);\n    }\n    \n    function deserialize(str) {\n        const vals = str.split(',');\n        let i = 0;\n        function build() {\n            if (i >= vals.length || vals[i] === '#') {\n                i++;\n                return null;\n            }\n            let node = { val: Number(vals[i++]), left: null, right: null };\n            node.left = build();\n            node.right = build();\n            return node;\n        }\n        return build();\n    }\n    \n    // 评测包装：将传入的树转换回树以验证还原度\n    const serializedStr = serialize(root);\n    return deserialize(serializedStr);\n}`,
        testCases: [
            { input: [[1, 2, 3, null, null, 4, 5]], expected: [1, 2, 3, null, null, 4, 5], label: '标准二叉树串行还原' }
        ]
    },
    {
        id: 'min_camera_cover',
        title: '监控二叉树',
        category: '树与二叉树',
        funcName: 'minCameraCover',
        difficulty: 'Hard',
        tags: ['树', '深度优先搜索', '贪心'],
        ds: 'binarytree',
        desc: '给定一个二叉树，我们在树的节点上安装摄像头。\\n每个相机可以直接监视其父对象、自身以及直接子对象。\\n计算监控树的所有节点所需的最小摄像头数量。',
        initCode: `function minCameraCover(root) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[0, 0, null, 0, 0]], expected: 1, label: '单侧偏斜监控树' },
            { input: [[0, 0, null, 0, null, 0, null, null, 0]], expected: 2, label: '链状树多监控点' }
        ]
    },

    // === 大类 4 扩充：排序与搜索 (Hard) ===
    {
        id: 'median_finder',
        title: '数据流的中位数',
        category: '排序与搜索',
        funcName: 'testMedianFinder',
        difficulty: 'Hard',
        tags: ['双指针', '设计', '堆（优先队列）'],
        desc: '设计一个支持以下两个操作的数据结构：\\n1. \`addNum(num)\` - 从数据流中添加一个整数到数据结构中。\\n2. \`findMedian()\` - 返回目前所有元素的中位数。',
        initCode: `function testMedianFinder(commands, values) {\n    class MedianFinder {\n        constructor() { this.nums = []; }\n        addNum(num) {\n            // 简易插入排序维护有序数组\n            let l = 0, r = this.nums.length - 1;\n            while (l <= r) {\n                let mid = (l + r) >> 1;\n                if (this.nums[mid] < num) l = mid + 1;\n                else r = mid - 1;\n            }\n            this.nums.splice(l, 0, num);\n        }\n        findMedian() {\n            let n = this.nums.length;\n            if (n % 2 === 1) return this.nums[Math.floor(n / 2)];\n            return (this.nums[n / 2 - 1] + this.nums[n / 2]) / 2;\n        }\n    }\n    \n    const finder = new MedianFinder();\n    const out = [];\n    commands.forEach((cmd, i) => {\n        if (cmd === 'addNum') finder.addNum(values[i]);\n        else if (cmd === 'findMedian') out.push(finder.findMedian());\n    });\n    return out;\n}`,
        testCases: [
            { input: [['addNum', 'addNum', 'findMedian', 'addNum', 'findMedian'], [1, 2, null, 3, null]], expected: [1.5, 2], label: '中位数添加流测试' }
        ]
    },
    {
        id: 'count_range_sum',
        title: '区间和的个数',
        category: '排序与搜索',
        funcName: 'countRangeSum',
        difficulty: 'Hard',
        tags: ['树状数组', '线段树', '分治', '二分查找'],
        desc: '给你一个整数数组 `nums` 以及两个整数 `lower` 和 `upper` 。求数组中，值介于 `[lower, upper]` 之间的区间和的个数。\\n**区间和** `S(i, j)` 表示在 `nums` 中从下标 `i` 到 `j` 的元素之和，包含两者（`i <= j`）。',
        initCode: `function countRangeSum(nums, lower, upper) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[-2, 5, -1], -2, 2], expected: 3, label: '含负权数区间' },
            { input: [[[0], 0, 0]], expected: 1, label: '单元素区间匹配' }
        ]
    },
    {
        id: 'find_min_ii',
        title: '寻找旋转排序数组中的最小值 II',
        category: '排序与搜索',
        funcName: 'findMin',
        difficulty: 'Hard',
        tags: ['数组', '二分查找'],
        desc: '已知一个长度为 `n` 的数组，预先按照升序排列，经由旋转后得到新的输入数组。注意，数组中可能存在 **重复** 元素。请找出并返回数组中的 **最小元素** 。',
        initCode: `function findMin(nums) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[1, 3, 5]], expected: 1, label: '升序排列' },
            { input: [[2, 2, 2, 0, 1]], expected: 0, label: '含大量重复值旋转' }
        ]
    },

    // === 大类 5 扩充：字符串与双指针 (Hard) ===
    {
        id: 'is_match',
        title: '正则表达式匹配',
        category: '字符串与双指针',
        funcName: 'isMatch',
        difficulty: 'Hard',
        tags: ['递归', '字符串', '动态规划'],
        desc: '给你一个字符串 `s` 和一个字符规律 `p`，请你来实现一个支持 `.` 和 `*` 的正则表达式匹配。\\n- `.` 匹配任意单个字符\\n- `*` 匹配零个或多个前面的那一个元素',
        initCode: `function isMatch(s, p) {\n    // 在此编写你的代码\n    \n    return false;\n}`,
        testCases: [
            { input: ["aa", "a*"], expected: true, label: '星号零字匹配' },
            { input: ["ab", ".*"], expected: true, label: '万能通配符' }
        ]
    },
    {
        id: 'min_distance',
        title: '编辑距离',
        category: '字符串与双指针',
        funcName: 'minDistance',
        difficulty: 'Hard',
        tags: ['字符串', '动态规划'],
        desc: '给你两个单词 `word1` 和 `word2`， 请返回将 `word1` 转换成 `word2` 所使用的最少操作数。\\n你可以对一个单词进行如下三种操作：\\n1. 插入一个字符\\n2. 删除一个字符\\n3. 替换一个字符',
        initCode: `function minDistance(word1, word2) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: ["horse", "ros"], expected: 3, label: '经典编辑距离' },
            { input: ["intention", "execution"], expected: 5, label: '长单词替换匹配' }
        ]
    },
    {
        id: 'find_substring',
        title: '串联所有单词的子串',
        category: '字符串与双指针',
        funcName: 'findSubstring',
        difficulty: 'Hard',
        tags: ['哈希表', '双指针', '滑动窗口'],
        desc: '给定一个字符串 `s` 和一个字符串数组 `words`。`words` 中所有单词 **长度相同**。\\n在 `s` 中找出所有恰好由 `words` 中所有单词串联形成的子串的起始位置，返回它们。顺序不限。',
        initCode: `function findSubstring(s, words) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: ["barfoothefoobarman", ["foo", "bar"]], expected: [0, 9], label: '连续串联字搜索' },
            { input: ["wordgoodgoodgoodbestword", ["word", "good", "best", "word"]], expected: [], label: '无重叠词匹配' }
        ]
    },

    // === 大类 6 扩充：动态规划 (Hard) ===
    {
        id: 'max_profit_iv',
        title: '买卖股票的最佳时机 IV',
        category: '动态规划',
        funcName: 'maxProfitIV',
        difficulty: 'Hard',
        tags: ['数组', '动态规划'],
        desc: '给你一个整数数组 `prices` ，其中 `prices[i]` 是某支股票第 `i` 天的价格；另一个整数 `k` 表示最多能交易的次数。\\n设计一个算法来计算你所能获取的最大利润。你最多可以进行 `k` 次交易。注意：你不能同时参与多笔交易（你必须在再次购买前出售掉之前的股票）。',
        initCode: `function maxProfitIV(k, prices) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [2, [2, 4, 1]], expected: 2, label: '限制2次交易' },
            { input: [2, [3, 2, 6, 5, 0, 3]], expected: 7, label: '多峰高低交易' }
        ]
    },
    {
        id: 'max_coins',
        title: '戳气球',
        category: '动态规划',
        funcName: 'maxCoins',
        difficulty: 'Hard',
        tags: ['数组', '动态规划'],
        desc: '有 `n` 个气球，编号为 `0` 到 `n - 1`，每个气球上都标有一个数字，这些数字存在数组 `nums` 中。现在要求你戳破所有的气球。\\n戳破第 `i` 个气球，可以获得 `nums[i - 1] * nums[i] * nums[i + 1]` 枚硬币。其中 `nums[-1] = nums[n] = 1`。求能获得的最大硬币数。',
        initCode: `function maxCoins(nums) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[3, 1, 5, 8]], expected: 167, label: '常规气球破裂策略' }
        ]
    },
    {
        id: 'calculate_minimum_hp',
        title: '地下城游戏',
        category: '动态规划',
        funcName: 'calculateMinimumHP',
        difficulty: 'Hard',
        tags: ['矩阵', '动态规划'],
        desc: '恶魔们抓走了公主并将她关在了地下城的右下角。地下城是由一个 `m x n` 的二维网格组成的。骑士从左上角出发，每次只能向右或向下移动一步。\\n骑士拥有一笔初始健康点数。如果健康点数降低到 0 或以下，骑士会立即死亡。每一格可能加血或扣血。求进入地下城时骑士所需的 **最小初始健康点数** 。',
        initCode: `function calculateMinimumHP(dungeon) {\n    // 在此编写你的代码\n    \n    return 1;\n}`,
        testCases: [
            { input: [[[-2, -3, 3], [-5, -10, 1], [10, 30, -5]]], expected: 7, label: '经典地下网格' }
        ]
    },

    // === 大类 7 扩充：贪心与回溯 (Hard) ===
    {
        id: 'solve_n_queens',
        title: 'N 皇后问题',
        category: '贪心与回溯',
        funcName: 'solveNQueens',
        difficulty: 'Hard',
        tags: ['回溯', '数组'],
        desc: '按照国际象棋的规则，皇后可以攻击与之处在同一行、同一列或同一对角线上的棋子。\\n**n 皇后问题** 研究的是如何将 `n` 个皇后放置在 `n x n` 的棋盘上，并且使皇后彼此之间不能相互攻击。\\n给你一个整数 `n` ，返回所有不同的 **n 皇后问题** 的解决方案。每一种解决方案都包含一个棋盘布局，其中 `Q` 代表皇后，`.` 代表空位。',
        initCode: `function solveNQueens(n) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: [4], expected: [[".Q..","...Q","Q...","..Q."],["..Q.","Q...","...Q",".Q.."]], label: '4皇后布局解' }
        ]
    },
    {
        id: 'solve_sudoku',
        title: '解数独',
        category: '贪心与回溯',
        funcName: 'testSudoku',
        difficulty: 'Hard',
        tags: ['回溯', '矩阵'],
        desc: '编写一个程序，通过填充空格来解决数独问题。\\n数独的解法需 **遵循以下规则**：\\n- 数字 `1-9` 在每一行只能出现一次。\\n- 数字 `1-9` 在每一列只能出现一次。\\n- 数字 `1-9` 在每一个以粗实线分隔的 `3x3` 宫内只能出现一次。\\n数独部分空格内用字符 `.` 表示。',
        initCode: `function testSudoku(board) {\n    function solve(b) {\n        for (let r = 0; r < 9; r++) {\n            for (let c = 0; c < 9; c++) {\n                if (b[r][c] === '.') {\n                    for (let val = 1; val <= 9; val++) {\n                        const charVal = String(val);\n                        if (isValid(b, r, c, charVal)) {\n                            b[r][c] = charVal;\n                            if (solve(b)) return true;\n                            b[r][c] = '.';\n                        }\n                    }\n                    return false;\n                }\n            }\n        }\n        return true;\n    }\n    \n    function isValid(b, row, col, char) {\n        for (let i = 0; i < 9; i++) {\n            if (b[row][i] === char) return false;\n            if (b[i][col] === char) return false;\n            const boxRow = 3 * Math.floor(row / 3) + Math.floor(i / 3);\n            const boxCol = 3 * Math.floor(col / 3) + (i % 3);\n            if (b[boxRow][boxCol] === char) return false;\n        }\n        return true;\n    }\n    \n    const boardClone = JSON.parse(JSON.stringify(board));\n    solve(boardClone);\n    return boardClone;\n}`,
        testCases: [
            { input: [[
                ["5","3",".",".","7",".",".",".","."],
                ["6",".",".","1","9","5",".",".","."],
                [".","9","8",".",".",".",".","6","."],
                ["8",".",".",".","6",".",".",".","3"],
                ["4",".",".","8",".","3",".",".","1"],
                ["7",".",".",".","2",".",".",".","6"],
                [".","6",".",".",".",".","2","8","."],
                [".",".",".","4","1","9",".",".","5"],
                [".",".",".",".","8",".",".","7","9"]
            ]], expected: [
                ["5","3","4","6","7","8","9","1","2"],
                ["6","7","2","1","9","5","3","4","8"],
                ["1","9","8","3","4","2","5","6","7"],
                ["8","5","9","7","6","1","4","2","3"],
                ["4","2","6","8","5","3","7","9","1"],
                ["7","1","3","9","2","4","8","5","6"],
                ["9","6","1","5","3","7","2","8","4"],
                ["2","8","7","4","1","9","6","3","5"],
                ["3","4","5","2","8","6","1","7","9"]
            ], label: '典型数独求解' }
        ]
    },
    {
        id: 'find_ladders',
        title: '单词接龙 II',
        category: '贪心与回溯',
        funcName: 'findLadders',
        difficulty: 'Hard',
        tags: ['广度优先搜索', '回溯', '哈希表', '字符串'],
        desc: '按字典 `wordList` 中最少转换次数完成从 `beginWord` 到 `endWord` 的转换路径，返回所有可能的 **最短转换路径** 。\\n每次转换只能改变一个字符。',
        initCode: `function findLadders(beginWord, endWord, wordList) {\n    // 在此编写你的代码\n    \n    return [];\n}`,
        testCases: [
            { input: ["hit", "cog", ["hot", "dot", "dog", "lot", "log", "cog"]], expected: [["hit", "hot", "dot", "dog", "cog"], ["hit", "hot", "lot", "log", "cog"]], label: '有多个最短路径' }
        ]
    },

    // === 大类 8 扩充：数学与趣味算法 (Hard) ===
    {
        id: 'max_points',
        title: '直线上最多的点数',
        category: '数学与趣味算法',
        funcName: 'maxPoints',
        difficulty: 'Hard',
        tags: ['几何', '哈希表', '数学'],
        desc: '给你一个数组 `points` ，其中 `points[i] = [xi, yi]` 表示 X-Y 平面上的一个点。求最多有多少个点共线。',
        initCode: `function maxPoints(points) {\n    // 在此编写你的代码\n    \n    return 0;\n}`,
        testCases: [
            { input: [[[1, 1], [2, 2], [3, 3]]], expected: 3, label: '三点完美共线' },
            { input: [[[1, 1], [3, 2], [5, 3], [4, 1], [2, 3], [1, 4]]], expected: 4, label: '多点共线散布' }
        ]
    },
    {
        id: 'number_to_words',
        title: '整数转英文表示',
        category: '数学与趣味算法',
        funcName: 'numberToWords',
        difficulty: 'Hard',
        tags: ['数学', '字符串'],
        desc: '将非负整数 `num` 转换为其对应的英文单词表示。例如 123 转换为 "One Hundred Twenty Three"。',
        initCode: `function numberToWords(num) {\n    // 在此编写你的代码\n    \n    return "";\n}`,
        testCases: [
            { input: [12345], expected: "Twelve Thousand Three Hundred Forty Five", label: '五位整数' },
            { input: [1234567], expected: "One Million Two Hundred Thirty Four Thousand Five Hundred Sixty Seven", label: '七位百万整数' }
        ]
    },
    {
        id: 'nth_super_ugly_number',
        title: '超级丑数',
        category: '数学与趣味算法',
        funcName: 'nthSuperUglyNumber',
        difficulty: 'Hard',
        tags: ['数学', '动态规划', '堆（优先队列）'],
        desc: '超级丑数是指其所有质因数都在一个给定的质数列表 `primes` 中的正整数。\\n给你一个整数 `n` 和一个整数数组 `primes` ，返回第 `n` 个 **超级丑数** 。\\n数据保证第 `n` 个超级丑数在 32 位有符号整型范围内。',
        initCode: `function nthSuperUglyNumber(n, primes) {\n    // 在此编写你的代码\n    \n    return 1;\n}`,
        testCases: [
            { input: [12, [2, 7, 13, 19]], expected: 32, label: '特定质因数列表超级丑数' }
        ]
    }
];

// ==================== 论坛管理与交互闭环共享数据 ====================

// 论坛置顶公告 Mock 数据
export const mockAnnouncements = ref([
    { id: 1, title: '【重要】2026年数据结构与算法期末大作业评优方案发布', date: '今日' },
    { id: 2, title: '【学术】第十五届全国大学生程序设计竞赛（邀请赛）报名通道开启', date: '昨天' },
    { id: 3, title: '【公告】平台多智能体协作工坊升级，新增 CodeNinja 审查专家', date: '3天前' }
]);

// 今日热议话题排行
export const mockHotTopics = ref([
    { tag: 'Vue3响应式', count: 185 },
    { tag: '单链表反转', count: 142 },
    { tag: 'Transformer矩阵乘法', count: 98 },
    { tag: '哈夫曼树编码', count: 76 }
]);

// 初始化帖子 Mock 数据
export const mockPosts = ref([
    {
        id: 'post-1',
        title: '手写 Vue 3 的 reactive 响应式系统时，Reflect.get 的 receiver 到底起什么作用？',
        content: '最近在做高级前端大作业，用 Proxy 实现了简易响应式，但是 Prof. X 导师说如果不配合 Reflect 并传入 receiver，在原型链继承时会出现 this 指向问题。请问有大牛能给个代码示例具体解释下吗？比如：\n\n```javascript\nconst parent = reactive({ \n  get child() { return this.name; } \n});\n```',
        author: '王小明',
        avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Felix',
        category: 'qna',
        categoryLabel: '课程答疑',
        tags: ['Vue3', 'Proxy', 'JS高级'],
        likes: 24,
        isLiked: false,
        views: 186,
        createdAt: '2小时前',
        replies: [
            {
                id: 'reply-1-1',
                author: '张小华',
                avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Jack',
                content: '简单来说，如果对象里有 getter，且该对象被作为另一个对象的原型。当你访问原型链底端对象的属性时，如果不传 receiver，getter 里的 this 指向的是原型对象（parent），而不是实际触发属性访问的那个子对象。这样就无法触发子对象的依赖收集了。',
                createdAt: '1.5小时前',
                likes: 8
            },
            {
                id: 'reply-1-2',
                author: 'Prof. X (AI导师)',
                avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=ProfX',
                isAi: true,
                content: '张同学解释得非常准确。在 Proxy 拦截器中，`Reflect.get(target, key, receiver)` 的第三个参数 `receiver` 就是代理对象本身。当读取继承自代理对象的属性时，它可以确保 `this` 指向的是子代理对象本身，从而正确触发子代理的 `get` 陷阱进行依赖收集。这是非常经典的 JS 原型继承中隐式绑定丢失问题，也是必须要配合使用 Reflect 的核心原因。',
                createdAt: '1小时前',
                likes: 18
            }
        ]
    },
    {
        id: 'post-2',
        title: '耗时三个月，我的算法学习与图谱通关经验总结（附 preorder 遍历代码）',
        content: '从零基础到手撕二叉树、图的 DFS/BFS。分享我的学习图谱路线，推荐大家多去使用我们平台的“协同核心枢纽”和 Mira 生成的概念引导图，帮助建立空间想象力。附带我写的一段二叉树前序遍历通用代码：\n\n```javascript\nfunction preorderTraversal(root) {\n  const res = [];\n  function dfs(node) {\n    if (!node) return;\n    res.push(node.val);\n    dfs(node.left);\n    dfs(node.right);\n  }\n  dfs(root);\n  return res;\n}\n```\n大家可以直接导入沙箱测试！',
        author: '李萌',
        avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Jude',
        category: 'experience',
        categoryLabel: '经验分享',
        tags: ['二叉树', 'DFS', '前端算法'],
        likes: 42,
        isLiked: false,
        views: 312,
        createdAt: '5小时前',
        replies: [
            {
                id: 'reply-2-1',
                author: '刘星',
                avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Jordan',
                content: '写得很清晰！一键导入沙箱这个联动确实方便，直接过去就能跑测试用例了！',
                createdAt: '4小时前',
                likes: 4
            }
        ]
    },
    {
        id: 'post-3',
        title: '2026年“高校杯”大学生程序设计邀请赛组队招募！',
        content: '本届邀请赛重点考察数据结构与图算法，有没有同学组队使用平台的“团队协作实训”舱一起练习？目前我们队伍缺一个负责 I/O 读写和测试用例编写的同学，最好能对图的最小生成树（Kruskal/Prim）有所了解。有兴趣的同学可以直接在下面跟帖或者私信我！',
        author: '赵雷',
        avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Jack',
        category: 'competition',
        categoryLabel: '竞赛交流',
        tags: ['程序设计竞赛', '组队招募', '图算法'],
        likes: 12,
        isLiked: false,
        views: 95,
        createdAt: '1天前',
        replies: [
            {
                id: 'reply-3-1',
                author: '孙宇',
                avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=George',
                content: '我这学期刚好精读了图论，Kruskal 用并查集实现很熟练。求加入队伍！',
                createdAt: '20小时前',
                likes: 3
            }
        ]
    },
    {
        id: 'post-4',
        title: '智能体工坊里编排的 Ninja 导师也太真实了，简直是 24 小时待命的代码审查狂魔',
        content: '昨天晚上两点提交了单链表反转大作业，以为没有人看，结果 Ninja 导师秒回了一条诊断：“这段代码的 next 指针处理存在空悬风险，O(N) 空间复杂度可以优化到 O(1) 原地反转”。简直太卷了，不过确实帮我理清了指针走向！大家都给自己的智能体配了些什么 Prompt？',
        author: '钱多多',
        avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Luna',
        category: 'chat',
        categoryLabel: '日常闲聊',
        tags: ['智能体工坊', 'Ninja导师', '日常吐槽'],
        likes: 31,
        isLiked: false,
        views: 220,
        createdAt: '2天前',
        replies: []
    },
    {
        id: 'post-5',
        title: '项目里碰到数据库死锁(Deadlock)的排查经验',
        content: '今天在做后端的事务处理时，遇到了数据库死锁。排查后发现是由于两个并发事务以不同的顺序请求锁引起的。分享一下我的排查过程和避免死锁的建议。',
        author: '江景珩',
        avatar: './assets/avatars/avatar1.jpg',
        category: 'experience',
        categoryLabel: '经验分享',
        tags: ['数据库', '死锁', '后端开发'],
        likes: 15,
        isLiked: false,
        views: 120,
        createdAt: '1小时前',
        replies: []
    },
    {
        id: 'post-6',
        title: '这周日的CCCC天梯赛，大家有什么拿分策略分享吗？',
        content: '天梯赛马上就要到了，这几天一直在刷题。对于团队赛来说，有什么好的策略吗？是不是应该优先保证基础题全部拿满分，再去死磕难题？',
        author: '陆知屿',
        avatar: './assets/avatars/avatar2.jpg',
        category: 'competition',
        categoryLabel: '竞赛交流',
        tags: ['CCCC天梯赛', '算法竞赛', '经验分享'],
        likes: 20,
        isLiked: false,
        views: 150,
        createdAt: '3小时前',
        replies: []
    }
]);

// AI 导师自动回复日志 Mock 数据
export const mockAiReplyLogs = ref([
    {
        id: 'log-1',
        postId: 'post-1',
        postTitle: '手写 Vue 3 的 reactive 响应式系统时，Reflect.get 的 receiver 到底起什么作用？',
        replyId: 'reply-1-2',
        agentName: 'Prof. X',
        content: '张同学解释得非常准确。在 Proxy 拦截器中，`Reflect.get(target, key, receiver)` 的第三个参数 `receiver` 就是代理对象本身。当读取继承自代理对象的属性时，它可以确保 `this` 指向的是子代理对象本身，从而正确触发子代理的 `get` 陷阱进行依赖收集。这是非常经典的 JS 原型继承中隐式绑定丢失问题，也是必须要配合使用 Reflect 的核心原因。',
        time: '1小时前',
        status: 'approved'
    },
    {
        id: 'log-2',
        postId: 'post-2',
        postTitle: '耗时三个月，我的算法学习与图谱通关经验总结（附 preorder 遍历代码）',
        replyId: 'reply-2-1',
        agentName: 'CodeNinja',
        content: '写得非常清晰！一键导入沙箱这个联动确实方便，直接过去就能跑测试用例了！',
        time: '4小时前',
        status: 'approved'
    }
]);

export const mockCodeRepositories = ref([
    {
        id: 'algo-visual-lab',
        title: '算法可视化实验室',
        slug: 'algo-visual-lab',
        description: '把排序、图遍历、最短路径做成可交互演示，适合数据结构课程复习。',
        author: '谢生',
        avatar: './assets/agents/codeninja.png',
        language: 'Vue',
        course: '数据结构',
        tags: ['算法', '可视化', '课程项目'],
        visibility: 'public',
        status: 'active',
        recommendScore: 92,
        giteaOwner: 'campus',
        giteaRepo: 'algo-visual-lab',
        htmlUrl: 'https://gezhisystem.com/gitea/campus/algo-visual-lab',
        cloneUrl: 'https://gezhisystem.com/gitea/campus/algo-visual-lab.git',
        sshUrl: 'ssh://git@gezhisystem.com:2222/campus/algo-visual-lab.git',
        defaultBranch: 'main',
        archiveUrl: 'https://gezhisystem.com/gitea/campus/algo-visual-lab/archive/main.zip',
        readme: '# 算法可视化实验室\n\n面向《数据结构》课程的交互式算法展示项目。\n\n## 功能\n\n- 排序过程逐帧演示\n- BFS / DFS 路径追踪\n- Dijkstra 最短路径对比\n\n## 本地运行\n\n```bash\npnpm install\npnpm dev\n```',
        createdAt: '2026-06-28T09:30:00+08:00',
        updatedAt: '2026-07-01T10:12:00+08:00'
    },
    {
        id: 'mini-compiler-notes',
        title: 'Mini Compiler Notes',
        slug: 'mini-compiler-notes',
        description: '从词法分析到简单中间代码生成的编译原理课程项目。',
        author: '李心悦',
        avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Aneka',
        language: 'Python',
        course: '编译原理',
        tags: ['编译器', 'Python', '实验报告'],
        visibility: 'public',
        status: 'active',
        recommendScore: 81,
        giteaOwner: 'campus',
        giteaRepo: 'mini-compiler-notes',
        htmlUrl: 'https://gezhisystem.com/gitea/campus/mini-compiler-notes',
        cloneUrl: 'https://gezhisystem.com/gitea/campus/mini-compiler-notes.git',
        sshUrl: 'ssh://git@gezhisystem.com:2222/campus/mini-compiler-notes.git',
        defaultBranch: 'main',
        archiveUrl: 'https://gezhisystem.com/gitea/campus/mini-compiler-notes/archive/main.zip',
        readme: '# Mini Compiler Notes\n\n一个用于课程实验的迷你编译器。\n\n## Milestones\n\n1. Tokenizer\n2. Recursive descent parser\n3. AST walker\n4. Simple IR emitter',
        createdAt: '2026-06-25T19:20:00+08:00',
        updatedAt: '2026-06-30T21:00:00+08:00'
    },
    {
        id: 'rag-course-assistant',
        title: '课程 RAG 助教插件',
        slug: 'rag-course-assistant',
        description: '把课程 PDF 切片、检索、引用来源展示整合成轻量插件。',
        author: '王明',
        avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Jude',
        language: 'TypeScript',
        course: '人工智能技术',
        tags: ['RAG', 'AI', '知识库'],
        visibility: 'public',
        status: 'active',
        recommendScore: 88,
        giteaOwner: 'campus',
        giteaRepo: 'rag-course-assistant',
        htmlUrl: 'https://gezhisystem.com/gitea/campus/rag-course-assistant',
        cloneUrl: 'https://gezhisystem.com/gitea/campus/rag-course-assistant.git',
        sshUrl: 'ssh://git@gezhisystem.com:2222/campus/rag-course-assistant.git',
        defaultBranch: 'main',
        archiveUrl: 'https://gezhisystem.com/gitea/campus/rag-course-assistant/archive/main.zip',
        readme: '# 课程 RAG 助教插件\n\n用于课程知识库检索、引用来源整理和学生侧问答辅助。',
        createdAt: '2026-06-20T15:45:00+08:00',
        updatedAt: '2026-07-01T08:10:00+08:00'
    }
]);

export const mockRepositoryStars = ref([
    { id: 'algo-visual-lab:谢生', projectId: 'algo-visual-lab', userId: '谢生', active: true },
    { id: 'algo-visual-lab:李心悦', projectId: 'algo-visual-lab', userId: '李心悦', active: true },
    { id: 'rag-course-assistant:谢生', projectId: 'rag-course-assistant', userId: '谢生', active: true }
]);

export const mockRepositoryFavorites = ref([
    { id: 'algo-visual-lab:王明', projectId: 'algo-visual-lab', userId: '王明', active: true },
    { id: 'mini-compiler-notes:谢生', projectId: 'mini-compiler-notes', userId: '谢生', active: true }
]);

export const mockRepositoryReports = ref([
    {
        id: 'repo-report-1',
        projectId: 'mini-compiler-notes',
        projectTitle: 'Mini Compiler Notes',
        projectAuthor: '李心悦',
        reporter: '赵雷',
        reason: '版权风险',
        description: '怀疑 README 中引用了未授权实验讲义。',
        status: 'pending',
        createdAt: '2026-07-01T09:40:00+08:00',
        auditedAt: '',
        auditor: '',
        note: ''
    }
]);

// 班级大数据与学情分析 Mock 数据
export const mockAnalyticsData = ref({
    radarIndicators: [
        { name: '规划一致性', max: 100 },
        { name: '代码质量与工程', max: 100 },
        { name: '理论逻辑完备度', max: 100 },
        { name: '学术论坛活跃度', max: 100 },
        { name: '专注度均值', max: 100 },
        { name: 'Checkpoint完成率', max: 100 }
    ],
    classRadarValues: [82, 75, 80, 64, 78, 85],
    weeklyActivityDates: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    weeklyActivityRates: [45, 58, 62, 79, 83, 91, 95],
    hourlyActiveData: [12, 5, 2, 0, 0, 1, 8, 25, 42, 68, 85, 74, 52, 60, 80, 95, 70, 50, 88, 112, 120, 98, 64, 30],
    
    // 薄弱知识点预警列表
    weakPoints: [
        { id: 'wp-1', topic: '平衡二叉树 AVL 失衡旋转编码', errorRate: 68, subject: '数据结构与算法', category: '树与二叉树', details: '有 68% 的学生在 LL/RR 单旋转或 LR/RL 双旋转编码测试中发生指针空悬，未正确更新高度平衡因子。' },
        { id: 'wp-2', topic: '双向循环链表防悬挂指针处理', errorRate: 48, subject: '数据结构与算法', category: '线性表', details: '有 48% 的学生在头节点删除或空链表边界插入时，因前后指针重链次序错误导致程序崩溃。' },
        { id: 'wp-3', topic: 'Proxy 拦截器中 Reflect 与 Receiver 的上下文绑定', errorRate: 42, subject: '高级前端程序设计', category: '响应式系统', details: '有 42% 的学生在手写 Proxy 劫持时，忘记在 Reflect.get 中传入 receiver 参数，导致继承原型链上的 this 绑定紊乱。' }
    ],

    // 教师今日待处理行动队列
    actionQueue: [
        { id: 'aq-1', level: 'high', title: 'AVL 旋转编码错误率异常', target: '高风险组 12 人', suggestion: '生成分层补弱任务，并要求 24 小时内完成订正。', actionType: 'homework', weakPointId: 'wp-1', subject: '数据结构与算法' },
        { id: 'aq-2', level: 'high', title: '王明 Proxy/Reflect 概念混淆', target: '王明', suggestion: '下发错题订正提醒，并追加 5 题 Checkpoint。', actionType: 'mistake', studentId: 3, weakPointId: 'wp-3', subject: '高级前端程序设计' },
        { id: 'aq-3', level: 'medium', title: '陈思思学习进度停滞', target: '陈思思', suggestion: '发送学习节奏提醒，引导先完成 Docker 部署基础任务。', actionType: 'nudge', studentId: 6, subject: '云原生与部署实践' },
        { id: 'aq-4', level: 'medium', title: '单链表反转空间复杂度偏高', target: '中风险组 8 人', suggestion: '推送 AI 学习提示，要求学生对比 O(N) 与 O(1) 写法。', actionType: 'ai-guide', weakPointId: 'wp-2', subject: '数据结构与算法' }
    ],

    // 师生交互闭环记录，后端可直接映射为 interaction_records 表
    interactionRecords: [
        { id: 'ir-1', type: 'homework', title: 'AVL 旋转编码分层补弱', targetLabel: '高风险组 12 人', completionRate: 58, unreadCount: 3, pendingCount: 5, completedCount: 7, createdAt: '今天 09:20', status: 'running', nextAction: '补发提醒给未响应学生' },
        { id: 'ir-2', type: 'mistake', title: 'Proxy Receiver 错题订正', targetLabel: '王明等 8 人', completionRate: 25, unreadCount: 1, pendingCount: 6, completedCount: 2, createdAt: '昨天 18:40', status: 'running', nextAction: '查看错因分析' },
        { id: 'ir-3', type: 'nudge', title: '阶段学习节奏提醒', targetLabel: '陈思思', completionRate: 100, unreadCount: 0, pendingCount: 0, completedCount: 1, createdAt: '昨天 12:10', status: 'completed', nextAction: '观察 48 小时学习活跃度' }
    ],
    
    // AI 决策建议列表
    aiAdvices: [
        { id: 'adv-1', title: 'AVL平衡树分层补弱建议', type: 'homework', reason: '由于「平衡二叉树 AVL 失衡旋转编码」本周错误率达 68%，系统判定属于重度理解障碍。', suggestion: '建议生成高风险组、中风险组、巩固组三层补弱任务，分别覆盖旋转图解、手写代码和边界测试。', active: true },
        { id: 'adv-2', title: 'Proxy专项测试补发建议', type: 'homework', reason: '有 42% 的学生在 Proxy/Reflect 原型继承链劫持上理解存在卡点。', suggestion: '建议一键下发《Proxy 拦截器 Receiver 上下文还原》Checkpoint 随堂测试强化理解。', active: true },
        { id: 'adv-3', title: '错题订正任务推送', type: 'mistake', reason: '检测到 8 位同学在单链表反转空间复杂度优化上使用 O(N) 代替 O(1)。', suggestion: '建议下发错题订正任务，要求学生在错题本中补写 O(1) 原地反转推导并标记掌握。', active: true },
        { id: 'adv-4', title: 'AI 个性化复习路径生成', type: 'ai-guide', reason: '部分学生同一知识点多次错误但未主动发起会诊。', suggestion: '建议让学生端 Alina 生成 3 步复习路径，并把完成状态回流到教师端。', active: true }
    ]
});
