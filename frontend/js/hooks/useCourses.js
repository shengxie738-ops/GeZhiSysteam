import { ref, computed, watch } from 'vue';
import { courseMindmaps } from '../data/mockData.js';
import { buildTreeOption } from '../config/chartOptions.js';

const dataStructureVideoLinks = {
    '数据结构': [
        { title: '课程总入口：王道计算机考研 数据结构', url: 'https://www.bilibili.com/video/BV1b7411N798' }
    ],
    '引言与算法分析': [
        { title: 'P2 1.0_开篇_数据结构在学什么', url: 'https://www.bilibili.com/video/BV1b7411N798?p=2' },
        { title: 'P5 1.2_1_算法的基本概念', url: 'https://www.bilibili.com/video/BV1b7411N798?p=5' }
    ],
    '数据结构基本概念': [
        { title: 'P3 1.1_数据结构的基本概念', url: 'https://www.bilibili.com/video/BV1b7411N798?p=3' },
        { title: 'P4 1.1_2_数据结构的三要素（旧版）', url: 'https://www.bilibili.com/video/BV1b7411N798?p=4' }
    ],
    '算法时间/空间复杂度': [
        { title: 'P6 1.2_2_算法的时间复杂度', url: 'https://www.bilibili.com/video/BV1b7411N798?p=6' },
        { title: 'P7 1.2_3_算法的空间复杂度', url: 'https://www.bilibili.com/video/BV1b7411N798?p=7' }
    ],
    '线性表': [
        { title: 'P8 2.1_线性表的定义和基本操作', url: 'https://www.bilibili.com/video/BV1b7411N798?p=8' }
    ],
    '顺序表与数组实现': [
        { title: 'P9 2.2.1_顺序表的定义', url: 'https://www.bilibili.com/video/BV1b7411N798?p=9' },
        { title: 'P10 2.2.2_1_顺序表的插入删除', url: 'https://www.bilibili.com/video/BV1b7411N798?p=10' },
        { title: 'P11 2.2.2_2_顺序表的查找', url: 'https://www.bilibili.com/video/BV1b7411N798?p=11' }
    ],
    '单链表与双向链表': [
        { title: 'P12 2.3.1_单链表的定义', url: 'https://www.bilibili.com/video/BV1b7411N798?p=12' },
        { title: 'P13 单链表的插入删除', url: 'https://www.bilibili.com/video/BV1b7411N798?p=13' },
        { title: 'P14 单链表的查找', url: 'https://www.bilibili.com/video/BV1b7411N798?p=14' },
        { title: 'P15 单链表的建立', url: 'https://www.bilibili.com/video/BV1b7411N798?p=15' },
        { title: 'P16 双链表', url: 'https://www.bilibili.com/video/BV1b7411N798?p=16' },
        { title: 'P17 循环链表', url: 'https://www.bilibili.com/video/BV1b7411N798?p=17' }
    ],
    '栈与队列': [
        { title: 'P20 3.1.1_栈的基本概念', url: 'https://www.bilibili.com/video/BV1b7411N798?p=20' },
        { title: 'P23 3.2.1_队列的基本概念', url: 'https://www.bilibili.com/video/BV1b7411N798?p=23' }
    ],
    '栈的特性及表达式求值': [
        { title: 'P20 栈的基本概念', url: 'https://www.bilibili.com/video/BV1b7411N798?p=20' },
        { title: 'P21 栈的顺序存储实现', url: 'https://www.bilibili.com/video/BV1b7411N798?p=21' },
        { title: 'P22 栈的链式存储实现', url: 'https://www.bilibili.com/video/BV1b7411N798?p=22' },
        { title: 'P28 表达式求值上', url: 'https://www.bilibili.com/video/BV1b7411N798?p=28' },
        { title: 'P29 表达式求值下', url: 'https://www.bilibili.com/video/BV1b7411N798?p=29' }
    ],
    '队列特性及循环队列': [
        { title: 'P23 队列的基本概念', url: 'https://www.bilibili.com/video/BV1b7411N798?p=23' },
        { title: 'P24 队列的顺序实现', url: 'https://www.bilibili.com/video/BV1b7411N798?p=24' },
        { title: 'P25 队列的链式实现', url: 'https://www.bilibili.com/video/BV1b7411N798?p=25' },
        { title: 'P26 双端队列', url: 'https://www.bilibili.com/video/BV1b7411N798?p=26' }
    ],
    '树与二叉树': [
        { title: 'P41 5.1.1+5.1.2_树的定义和基本术语', url: 'https://www.bilibili.com/video/BV1b7411N798?p=41' },
        { title: 'P43 5.2.1_1_二叉树的定义和基本术语', url: 'https://www.bilibili.com/video/BV1b7411N798?p=43' },
        { title: 'P45 二叉树的存储结构', url: 'https://www.bilibili.com/video/BV1b7411N798?p=45' }
    ],
    '二叉树遍历算法': [
        { title: 'P46 5.3.1_1_二叉树的先中后序遍历', url: 'https://www.bilibili.com/video/BV1b7411N798?p=46' },
        { title: 'P47 二叉树的层次遍历', url: 'https://www.bilibili.com/video/BV1b7411N798?p=47' },
        { title: 'P48 由遍历序列构造二叉树', url: 'https://www.bilibili.com/video/BV1b7411N798?p=48' }
    ],
    '哈夫曼树与编码': [
        { title: 'P55 5.5.1_哈夫曼树', url: 'https://www.bilibili.com/video/BV1b7411N798?p=55' }
    ],
    '图': [
        { title: 'P58 6.1.1_图的基本概念', url: 'https://www.bilibili.com/video/BV1b7411N798?p=58' },
        { title: 'P59 邻接矩阵法', url: 'https://www.bilibili.com/video/BV1b7411N798?p=59' },
        { title: 'P60 邻接表法', url: 'https://www.bilibili.com/video/BV1b7411N798?p=60' },
        { title: 'P61 十字链表、邻接多重表', url: 'https://www.bilibili.com/video/BV1b7411N798?p=61' },
        { title: 'P62 图的基本操作', url: 'https://www.bilibili.com/video/BV1b7411N798?p=62' }
    ],
    '图的遍历 (DFS/BFS)': [
        { title: 'P63 6.3.1_图的广度优先遍历', url: 'https://www.bilibili.com/video/BV1b7411N798?p=63' },
        { title: 'P64 6.3.2_图的深度优先遍历', url: 'https://www.bilibili.com/video/BV1b7411N798?p=64' }
    ],
    '最小生成树与最短路径': [
        { title: 'P65 6.4.1_最小生成树', url: 'https://www.bilibili.com/video/BV1b7411N798?p=65' },
        { title: 'P66 BFS最短路径', url: 'https://www.bilibili.com/video/BV1b7411N798?p=66' },
        { title: 'P67 Dijkstra', url: 'https://www.bilibili.com/video/BV1b7411N798?p=67' },
        { title: 'P68 Floyd', url: 'https://www.bilibili.com/video/BV1b7411N798?p=68' }
    ]
};

const courseVideoLinks = {
    data_structure: dataStructureVideoLinks,
    computer_programming: {
        '计算机程序设计': [
            { title: '课程总入口：黑马程序员 C++ 教程从0到1入门编程', url: 'https://www.bilibili.com/video/BV1et411b73Z/' }
        ],
        '程序设计基础': [
            { title: 'P24 单行 if 语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=24' },
            { title: 'P25 多行 if 语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=25' },
            { title: 'P26 多条件 if 语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=26' },
            { title: 'P27 循环控制语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=27' },
            { title: 'P28 break / continue / goto', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=28' }
        ],
        '分支逻辑与控制结构': [
            { title: 'P24 单行 if 语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=24' },
            { title: 'P25 多行 if 语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=25' },
            { title: 'P26 多条件 if 语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=26' }
        ],
        '循环迭代控制': [
            { title: 'P24 流程控制语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=24' },
            { title: 'P25 流程控制语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=25' },
            { title: 'P26 流程控制语句', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=26' },
            { title: 'P27 for / while / do while', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=27' },
            { title: 'P28 break / continue / goto', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=28' }
        ],
        '数组与函数': [
            { title: 'P39 数组概念与定义', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=39' },
            { title: 'P45 数组案例与排序', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=45' },
            { title: 'P50 函数定义与调用', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=50' },
            { title: 'P52 函数值传递', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=52' }
        ],
        '一维与二维数组': [
            { title: 'P39 数组概念、定义、初始化', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=39' },
            { title: 'P40 一维数组', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=40' },
            { title: 'P41 数组元素引用', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=41' },
            { title: 'P42 数组初始化', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=42' },
            { title: 'P43 数组应用', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=43' },
            { title: 'P45 数组逆置', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=45' },
            { title: 'P46 冒泡排序', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=46' },
            { title: 'P47 二维数组', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=47' },
            { title: 'P48 二维数组应用', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=48' },
            { title: 'P49 数组案例', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=49' }
        ],
        '函数定义与参数传递': [
            { title: 'P50 函数定义', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=50' },
            { title: 'P51 函数调用', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=51' },
            { title: 'P52 值传递', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=52' },
            { title: 'P53 函数常见样式', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=53' },
            { title: 'P54 函数声明', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=54' },
            { title: 'P55 函数分文件编写', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=55' }
        ],
        '指针与结构体': [
            { title: 'P56 指针定义', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=56' },
            { title: 'P61 指针与数组', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=61' },
            { title: 'P64 结构体定义', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=64' },
            { title: 'P66 结构体指针', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=66' }
        ],
        '指针与内存地址': [
            { title: 'P56 指针定义', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=56' },
            { title: 'P57 指针所占空间', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=57' },
            { title: 'P58 空指针', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=58' },
            { title: 'P59 野指针', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=59' },
            { title: 'P60 const 修饰指针', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=60' },
            { title: 'P61 指针与数组', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=61' },
            { title: 'P62 指针与函数', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=62' },
            { title: 'P63 指针综合案例', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=63' }
        ],
        '结构体与链表初步': [
            { title: 'P64 结构体定义', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=64' },
            { title: 'P65 结构体数组', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=65' },
            { title: 'P66 结构体指针', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=66' },
            { title: 'P67 结构体嵌套', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=67' },
            { title: 'P68 结构体做函数参数', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=68' },
            { title: 'P69 const 使用场景', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=69' },
            { title: 'P70 结构体案例', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=70' },
            { title: 'P71 结构体案例', url: 'https://www.bilibili.com/video/BV1et411b73Z/?p=71' }
        ],
        '面向对象基础': [
            { title: 'C++ 核心编程：类和对象 / 封装 / 构造析构', url: 'https://www.bilibili.com/video/BV1et411b73Z/' }
        ],
        '类定义与成员函数': [
            { title: 'C++ 核心编程：类和对象、封装、成员函数、构造/析构', url: 'https://www.bilibili.com/video/BV1et411b73Z/' }
        ],
        '多态与虚函数': [
            { title: 'C++ 核心编程：继承、多态、虚函数、企业职工系统项目', url: 'https://www.bilibili.com/video/BV1et411b73Z/' }
        ]
    },
    computer_organization: {
        '计算机组成原理': [
            { title: '课程总入口：王道计算机考研 计算机组成原理', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/' }
        ],
        '计算机系统概述': [
            { title: 'P2 计算机系统结构', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=2' },
            { title: 'P5 CPU 工作过程', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=5' },
            { title: 'P8 计算机层次结构', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=8' },
            { title: 'P67 总线概述', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=67' }
        ],
        '冯诺依曼结构与五大部件': [
            { title: 'P2 系统结构', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=2' },
            { title: 'P5 CPU 工作过程', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=5' },
            { title: 'P8 层次结构', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=8' }
        ],
        '系统总线与互连结构': [
            { title: 'P67 总线概述', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=67' },
            { title: 'P68 总线性能指标', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=68' },
            { title: 'P69 总线仲裁与定时', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=69' },
            { title: 'P70 总线标准', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=70' }
        ],
        '指令系统与计算': [
            { title: 'P46 指令格式', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=46' },
            { title: 'P48 寻址方式', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=48' },
            { title: 'P11 数据表示', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=11' },
            { title: 'P20 浮点运算', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=20' }
        ],
        'MIPS 指令集与寻址方式': [
            { title: 'P46 指令格式', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=46' },
            { title: 'P48 寻址方式', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=48' },
            { title: 'P50 CISC / RISC', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=50' }
        ],
        '定点数与浮点数运算': [
            { title: 'P11 数据表示', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=11' },
            { title: 'P14 定点运算', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=14' },
            { title: 'P18 浮点数表示', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=18' },
            { title: 'P20 浮点运算', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=20' },
            { title: 'P23 ALU', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=23' },
            { title: 'P26 运算器', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=26' }
        ],
        '单周期与流水线处理器': [
            { title: 'P56 数据通路', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=56' },
            { title: 'P59 控制器', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=59' },
            { title: 'P62 流水线基本概念', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=62' },
            { title: 'P64 五段式流水线', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=64' }
        ],
        '数据通路与控制逻辑设计': [
            { title: 'P56 数据通路', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=56' },
            { title: 'P57 数据通路', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=57' },
            { title: 'P58 硬布线控制器', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=58' },
            { title: 'P59 微程序控制器', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=59' },
            { title: 'P60 控制信号设计', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=60' },
            { title: 'P61 控制器综合', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=61' }
        ],
        '流水线冲突与冲突处理': [
            { title: 'P62 流水线基本概念', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=62' },
            { title: 'P63 流水线影响因素', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=63' },
            { title: 'P64 五段式流水线', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=64' }
        ],
        '存储器层次体系': [
            { title: 'P36 Cache 原理', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=36' },
            { title: 'P38 Cache 映射方式', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=38' },
            { title: 'P42 虚拟存储器', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=42' },
            { title: 'P44 TLB', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=44' }
        ],
        '高速缓存 (Cache) 映射': [
            { title: 'P36 Cache 原理', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=36' },
            { title: 'P38 Cache 映射方式', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=38' },
            { title: 'P40 Cache 替换算法与写策略', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=40' }
        ],
        '虚拟存储器与 TLB': [
            { title: 'P42 虚拟存储器', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=42' },
            { title: 'P44 页式 / 段式 / 段页式 / TLB', url: 'https://www.bilibili.com/video/BV1ps4y1d73V/?p=44' }
        ]
    },
    AI_technology: {
        '人工智能技术': [
            { title: '课程总入口：UC Berkeley CS188 Artificial Intelligence', url: 'https://www.bilibili.com/video/BV1vt41167c9/' }
        ],
        '搜索与问题求解': [
            { title: 'P2 Search', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=2' },
            { title: 'P3 Informed Search', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=3' }
        ],
        '盲目搜索算法': [
            { title: 'P2 Search', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=2' }
        ],
        '启发式搜索与 A* 算法': [
            { title: 'P3 Informed Search', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=3' }
        ],
        '知识表达与逻辑推理': [
            { title: 'P4 CSP / 推理基础', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=4' },
            { title: 'P5 CSP / 推理基础', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=5' },
            { title: 'P6 对抗搜索 / 推理基础', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=6' }
        ],
        '命题逻辑智能体': [
            { title: 'P4 CSP / 推理基础', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=4' },
            { title: 'P5 CSP / 推理基础', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=5' },
            { title: 'P6 对抗搜索 / 推理基础', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=6' }
        ],
        '一阶逻辑与推理机': [
            { title: 'CS188 总入口：补充查找 Logic 章节资料', url: 'https://www.bilibili.com/video/BV1vt41167c9/' }
        ],
        '不确定性与概率推理': [
            { title: 'P12 Probability', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=12' },
            { title: 'P13 Bayes Nets', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=13' },
            { title: 'P8 Markov Decision Processes', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=8' },
            { title: 'P9 MDP II', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=9' }
        ],
        '贝叶斯网络建模': [
            { title: 'P12 Probability', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=12' },
            { title: 'P13 Bayes Nets', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=13' },
            { title: 'P14 Independence', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=14' },
            { title: 'P15 Inference', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=15' },
            { title: 'P16 Sampling', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=16' }
        ],
        '马尔可夫决策过程 (MDP)': [
            { title: 'P8 Markov Decision Processes', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=8' },
            { title: 'P9 MDP II', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=9' },
            { title: 'P10 Reinforcement Learning', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=10' },
            { title: 'P11 Reinforcement Learning II', url: 'https://www.bilibili.com/video/BV1vt41167c9/?p=11' }
        ]
    },
    database_technology: {
        '数据库系统原理': [
            { title: '课程总入口：中国人民大学 王珊 数据库系统概论', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/' }
        ],
        '关系模型与 SQL': [
            { title: 'P5 关系演算', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=5' },
            { title: 'P6 关系代数', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=6' },
            { title: 'P8 SQL 数据定义', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=8' },
            { title: 'P10 SQL 复杂查询', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=10' }
        ],
        '关系模型与完整性约束': [
            { title: 'P5 关系演算', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=5' },
            { title: 'P6 关系代数', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=6' },
            { title: 'P7 关系演算', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=7' },
            { title: 'P15 完整性约束', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=15' },
            { title: 'P16 完整性约束', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=16' },
            { title: 'P17 触发器', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=17' }
        ],
        'SQL 复杂数据查询': [
            { title: 'P8 SQL 数据定义', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=8' },
            { title: 'P9 SQL 基本查询', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=9' },
            { title: 'P10 SQL 复杂查询', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=10' },
            { title: 'P11 SQL 空值', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=11' }
        ],
        '数据库建模与规范化': [
            { title: 'P23 数据库设计步骤', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=23' },
            { title: 'P25 E-R 模型', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=25' },
            { title: 'P18 函数依赖', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=18' },
            { title: 'P20 范式体系', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=20' }
        ],
        'E-R 模型概念设计': [
            { title: 'P23 数据库设计步骤', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=23' },
            { title: 'P24 需求分析', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=24' },
            { title: 'P25 E-R 模型', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=25' },
            { title: 'P26 数据模型优化', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=26' }
        ],
        '关系范式与函数依赖': [
            { title: 'P18 函数依赖', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=18' },
            { title: 'P19 多值依赖', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=19' },
            { title: 'P20 范式体系', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=20' },
            { title: 'P21 逻辑蕴涵', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=21' },
            { title: 'P22 模式分解', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=22' }
        ],
        '物理存储与索引结构': [
            { title: 'P31 关系数据库组织方式', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=31' },
            { title: 'P32 多表聚簇存放方式', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=32' },
            { title: 'P34 B+ 树索引', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=34' },
            { title: 'P35 哈希索引', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=35' }
        ],
        '磁盘空间管理与文件记录': [
            { title: 'P31 关系数据库组织方式', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=31' },
            { title: 'P32 多表聚簇存放方式', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=32' }
        ],
        'B+ 树与哈希索引': [
            { title: 'P33 顺序表索引', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=33' },
            { title: 'P34 B+ 树索引', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=34' },
            { title: 'P35 哈希索引', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=35' }
        ],
        '事务管理与并发控制': [
            { title: 'P44 数据异常与隔离级别', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=44' },
            { title: 'P45 封锁', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=45' },
            { title: 'P46 可串行化', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=46' },
            { title: 'P47 两阶段封锁协议', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=47' }
        ],
        '并发冲突与封锁协议': [
            { title: 'P44 数据异常与隔离级别', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=44' },
            { title: 'P45 封锁', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=45' },
            { title: 'P46 可串行化', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=46' },
            { title: 'P47 两阶段封锁协议', url: 'https://www.bilibili.com/video/BV1p1NoeTE89/?p=47' }
        ]
    }
};

export function useCourses(files, currentView, showToast) {
    const courses = ref([
        {
            id: 'data_structure',
            name: '数据结构',
            code: 'CS201',
            icon: 'ph-tree-structure',
            desc: '系统讲授线性表、栈、队列、树、图等核心数据结构及常用算法，培养算法思维与编程能力。',
            color: 'from-blue-500 to-indigo-600',
            files: [
                { name: '1-引言.ppt', type: 'ppt', path: 'courses/data_structure/1-引言.ppt', size: '739 KB' },
                { name: '2-线性表.pdf', type: 'pdf', path: 'courses/data_structure/2-线性表.pdf', size: '16.8 MB' },
                { name: '3-栈.pdf', type: 'pdf', path: 'courses/data_structure/3-栈.pdf', size: '18.2 MB' },
                { name: '4-队列.pdf', type: 'pdf', path: 'courses/data_structure/4-队列.pdf', size: '10.3 MB' },
                { name: '5-树.ppt', type: 'ppt', path: 'courses/data_structure/5-树.ppt', size: '1.4 MB' },
                { name: '6-集合.ppt', type: 'ppt', path: 'courses/data_structure/6-集合.ppt', size: '7.3 MB' },
                { name: '7-图.pdf', type: 'pdf', path: 'courses/data_structure/7-图.pdf', size: '2.8 MB' },
                { name: '8-算法设计.ppt', type: 'ppt', path: 'courses/data_structure/8-算法设计.ppt', size: '463 KB' },
            ]
        },
        {
            id: 'computer_programming',
            name: '计算机程序设计',
            code: 'CS101',
            icon: 'ph-code',
            desc: '以 C++ 为基础，讲授程序设计基本思想、控制结构、函数、数组及面向对象编程方法。',
            color: 'from-emerald-500 to-teal-600',
            files: [
                { name: 'ch00 关于课程.ppt', type: 'ppt', path: 'courses/computer_programming/ch00 关于课程.ppt', size: '182 KB' },
                { name: 'ch01 计算机简介.ppt', type: 'ppt', path: 'courses/computer_programming/ch01 计算机简介.ppt', size: '1.3 MB' },
                { name: 'ch02 通过例子学习.ppt', type: 'ppt', path: 'courses/computer_programming/ch02 通过例子学习.ppt', size: '626 KB' },
                { name: 'ch03 逻辑思维及分支程序设计.ppt', type: 'ppt', path: 'courses/computer_programming/ch03 逻辑思维及分支程序设计.ppt', size: '386 KB' },
                { name: 'ch04 循环控制.ppt', type: 'ppt', path: 'courses/computer_programming/ch04 循环控制.ppt', size: '342 KB' },
                { name: 'ch05 批量数据处理—数组.ppt', type: 'ppt', path: 'courses/computer_programming/ch05 批量数据处理—数组.ppt', size: '911 KB' },
                { name: 'ch06 过程封装－－函数.ppt', type: 'ppt', path: 'courses/computer_programming/ch06 过程封装－－函数.ppt', size: '938 KB' },
                { name: 'ch07 间接访问—指针.pptx', type: 'ppt', path: 'courses/computer_programming/ch07 间接访问—指针.pptx', size: '295 KB' },
                { name: 'ch08 数据封装—结构体.ppt', type: 'ppt', path: 'courses/computer_programming/ch08 数据封装—结构体.ppt', size: '591 KB' },
                { name: 'ch09 模块化开发.ppt', type: 'ppt', path: 'courses/computer_programming/ch09 模块化开发.ppt', size: '418 KB' },
                { name: 'ch10 创建功能更强的类型.ppt', type: 'ppt', path: 'courses/computer_programming/ch10 创建功能更强的类型.ppt', size: '599 KB' },
                { name: 'ch11 运算符重载.ppt', type: 'ppt', path: 'courses/computer_programming/ch11 运算符重载.ppt', size: '494 KB' },
                { name: 'ch12 组合与继承.ppt', type: 'ppt', path: 'courses/computer_programming/ch12 组合与继承.ppt', size: '585 KB' },
                { name: 'ch13 泛型机制—模板（最终版）.ppt', type: 'ppt', path: 'courses/computer_programming/ch13 泛型机制—模板（最终版）.ppt', size: '383 KB' },
                { name: 'ch14 输入输出与文件.ppt', type: 'ppt', path: 'courses/computer_programming/ch14 输入输出与文件.ppt', size: '917 KB' },
                { name: 'ch15 异常处理.ppt', type: 'ppt', path: 'courses/computer_programming/ch15 异常处理.ppt', size: '289 KB' },
                { name: 'ch16 容器和迭代器.ppt', type: 'ppt', path: 'courses/computer_programming/ch16 容器和迭代器.ppt', size: '229 KB' },
                { name: 'ch17 关于计算机.ppt', type: 'ppt', path: 'courses/computer_programming/ch17 关于计算机.ppt', size: '430 KB' },
            ]
        },
        {
            id: 'AI_technology',
            name: '人工智能技术',
            code: 'AI101',
            icon: 'ph-brain',
            desc: '系统介绍经典 AI 搜索、逻辑智能体、一阶逻辑推理以及现代不确定性概率推理与学习决策模型。',
            color: 'from-purple-500 to-indigo-600',
            files: [
                { name: "1-Introduction.ppt", type: "ppt", path: "courses/AI_technology/1-Introduction.ppt", size: "4.0 MB" },
                { name: "10-Knowledge Representation.ppt", type: "ppt", path: "courses/AI_technology/10-Knowledge Representation.ppt", size: "1.1 MB" },
                { name: "13-uncertainty.ppt", type: "ppt", path: "courses/AI_technology/13-uncertainty.ppt", size: "538.5 KB" },
                { name: "14-Probabilistic Reasoning.ppt", type: "ppt", path: "courses/AI_technology/14-Probabilistic Reasoning.ppt", size: "4.5 MB" },
                { name: "15-Probabilistic Reasoning over Time.ppt", type: "ppt", path: "courses/AI_technology/15-Probabilistic Reasoning over Time.ppt", size: "4.5 MB" },
                { name: "16-Making_Simple_Decisions.pdf", type: "pdf", path: "courses/AI_technology/16-Making_Simple_Decisions.pdf", size: "1.7 MB" },
                { name: "16-Making_Simple_Decisions.ppt", type: "ppt", path: "courses/AI_technology/16-Making_Simple_Decisions.ppt", size: "3.2 MB" },
                { name: "17-making_complex_decisions.ppt", type: "ppt", path: "courses/AI_technology/17-making_complex_decisions.ppt", size: "3.8 MB" },
                { name: "18-LearningfromObervations.ppt", type: "ppt", path: "courses/AI_technology/18-LearningfromObervations.ppt", size: "3.0 MB" },
                { name: "2-Intell-Agents.ppt", type: "ppt", path: "courses/AI_technology/2-Intell-Agents.ppt", size: "350.0 KB" },
                { name: "3-uninformedSearch.ppt", type: "ppt", path: "courses/AI_technology/3-uninformedSearch.ppt", size: "1.2 MB" },
                { name: "4-Informed Search and Exploration.ppt", type: "ppt", path: "courses/AI_technology/4-Informed Search and Exploration.ppt", size: "933.0 KB" },
                { name: "5-BeyondClassicalSearch.ppt", type: "ppt", path: "courses/AI_technology/5-BeyondClassicalSearch.ppt", size: "854.5 KB" },
                { name: "6-Adversarial Search.ppt", type: "ppt", path: "courses/AI_technology/6-Adversarial Search.ppt", size: "2.1 MB" },
                { name: "7-Constraint Satisfaction Problems.ppt", type: "ppt", path: "courses/AI_technology/7-Constraint Satisfaction Problems.ppt", size: "1.1 MB" },
                { name: "7-Logical Agents.ppt", type: "ppt", path: "courses/AI_technology/7-Logical Agents.ppt", size: "1.9 MB" },
                { name: "8-First-Order Logic.ppt", type: "ppt", path: "courses/AI_technology/8-First-Order Logic.ppt", size: "631.5 KB" },
                { name: "9-Inference in first-order logic.ppt", type: "ppt", path: "courses/AI_technology/9-Inference in first-order logic.ppt", size: "1.4 MB" }
            ]
        },
        {
            id: 'computer_organization',
            name: '计算机组成原理',
            code: 'CS202',
            icon: 'ph-cpu',
            desc: '深入探讨计算机硬件架构、指令系统、处理器设计、内存层次结构（Cache/主存）及多核集群。',
            color: 'from-amber-500 to-orange-600',
            files: [
                { name: "01_Introduction_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/01_Introduction_fang.pdf", size: "2.4 MB" },
                { name: "02_Computer Evolution and Performance_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/02_Computer Evolution and Performance_fang.pdf", size: "1.4 MB" },
                { name: "03_Top Level View of Computer Function and Interconnection_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/03_Top Level View of Computer Function and Interconnection_fang.pdf", size: "880.4 KB" },
                { name: "04a_ Instructions Language of the Computer_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/04a_ Instructions Language of the Computer_fang.pdf", size: "2.2 MB" },
                { name: "04b_ Instructions Language of the Computer_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/04b_ Instructions Language of the Computer_fang.pdf", size: "2.0 MB" },
                { name: "04c_ Instructions Language of the Computer_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/04c_ Instructions Language of the Computer_fang.pdf", size: "1.3 MB" },
                { name: "04d_ Instructions Language of the Computer_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/04d_ Instructions Language of the Computer_fang.pdf", size: "985.4 KB" },
                { name: "04_ Instructions Language of the Computer_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/04_ Instructions Language of the Computer_fang.pdf", size: "310.1 KB" },
                { name: "05a_The Processor_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/05a_The Processor_fang.pdf", size: "1.8 MB" },
                { name: "05b_The Processor_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/05b_The Processor_fang.pdf", size: "4.3 MB" },
                { name: "05c_The Processor_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/05c_The Processor_fang.pdf", size: "3.6 MB" },
                { name: "05_The Processor_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/05_The Processor_fang.pdf", size: "840.8 KB" },
                { name: "06a_Large and Fast Exploiting Memory Hierarchy_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/06a_Large and Fast Exploiting Memory Hierarchy_fang.pdf", size: "2.0 MB" },
                { name: "06b_Large and Fast Exploiting Memory Hierarchy_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/06b_Large and Fast Exploiting Memory Hierarchy_fang.pdf", size: "932.6 KB" },
                { name: "06_Large and Fast Exploiting Memory Hierarchy_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/06_Large and Fast Exploiting Memory Hierarchy_fang.pdf", size: "600.9 KB" },
                { name: "07_Multicores^JMultiprocessors and Clusters_fang.pdf", type: "pdf", path: "courses/Computer_ Organization/07_Multicores^JMultiprocessors and Clusters_fang.pdf", size: "2.4 MB" },
                { name: "Chapter 3 Arithmetic for Computers.pdf", type: "pdf", path: "courses/Computer_ Organization/Chapter 3 Arithmetic for Computers.pdf", size: "793.9 KB" },
                { name: "Chapter 6 Storage and Other IO Topics.pdf", type: "pdf", path: "courses/Computer_ Organization/Chapter 6 Storage and Other IO Topics.pdf", size: "1.7 MB" }
            ]
        },
        {
            id: 'database_technology',
            name: '数据库系统原理',
            code: 'CS203',
            icon: 'ph-database',
            desc: '系统讲授关系数据库设计、SQL 复杂查询、E-R 建模、物理存储介质、索引结构及事务管理。',
            color: 'from-pink-500 to-rose-600',
            files: [
                { name: "L10_Storage.pdf", type: "pdf", path: "courses/Database _Technology/L10_Storage.pdf", size: "4.5 MB" },
                { name: "L11_Indexing.pdf", type: "pdf", path: "courses/Database _Technology/L11_Indexing.pdf", size: "4.8 MB" },
                { name: "L12_QueryProcess.pdf", type: "pdf", path: "courses/Database _Technology/L12_QueryProcess.pdf", size: "5.0 MB" },
                { name: "L13_Transaction.pdf", type: "pdf", path: "courses/Database _Technology/L13_Transaction.pdf", size: "5.2 MB" },
                { name: "L1_Intro.pdf", type: "pdf", path: "courses/Database _Technology/L1_Intro.pdf", size: "10.3 MB" },
                { name: "L2_Model.pdf", type: "pdf", path: "courses/Database _Technology/L2_Model.pdf", size: "3.4 MB" },
                { name: "L3_SQL.pdf", type: "pdf", path: "courses/Database _Technology/L3_SQL.pdf", size: "6.5 MB" },
                { name: "L4_SQL.pdf", type: "pdf", path: "courses/Database _Technology/L4_SQL.pdf", size: "4.1 MB" },
                { name: "L5_SQL.pdf", type: "pdf", path: "courses/Database _Technology/L5_SQL.pdf", size: "2.8 MB" },
                { name: "L6_ER1.pdf", type: "pdf", path: "courses/Database _Technology/L6_ER1.pdf", size: "3.6 MB" },
                { name: "L7_ER2.pdf", type: "pdf", path: "courses/Database _Technology/L7_ER2.pdf", size: "6.6 MB" },
                { name: "L8_Design1.pdf", type: "pdf", path: "courses/Database _Technology/L8_Design1.pdf", size: "6.8 MB" },
                { name: "L9_Design2.pdf", type: "pdf", path: "courses/Database _Technology/L9_Design2.pdf", size: "3.0 MB" }
            ]
        }
    ]);

    const selectedCourse = ref(null);
    const previewFileUrl = ref('');
    const previewFileName = ref('');
    const showPreviewModal = ref(false);
    const activePreviewFile = ref(null);
    const previewMode = ref('pdf');
    const currentPptGuide = ref(null);
    const currentSlideIndex = ref(0);

    const selectedPathwayCourseId = ref(localStorage.getItem('selectedPathwayCourseId') || 'data_structure');
    if (!courseMindmaps[selectedPathwayCourseId.value]) {
        selectedPathwayCourseId.value = 'data_structure';
        localStorage.setItem('selectedPathwayCourseId', 'data_structure');
    }

    const pathwayOption = computed(() => {
        const treeData = courseMindmaps[selectedPathwayCourseId.value];
        return buildTreeOption(treeData);
    });

    const activeNodeDetails = ref(null);

    const selectCourse = (course) => {
        selectedCourse.value = course;
    };

    const handleNodeClick = (rawNodeData) => {
        activeNodeDetails.value = {
            title: rawNodeData.name,
            status: rawNodeData.value,
            desc: rawNodeData.desc,
            resources: rawNodeData.resources,
            videos: courseVideoLinks[selectedPathwayCourseId.value]?.[rawNodeData.name] || []
        };
    };

    const viewCoursePathway = (courseId) => {
        selectedPathwayCourseId.value = courseId;
        currentView.value = 'pathway';
        showToast(`已切换至《${courseMindmaps[courseId]?.name || ''}》的思维导图`);
    };

    const previewFile = async (file) => {
        activePreviewFile.value = file;
        previewFileName.value = file.name;
        currentSlideIndex.value = 0;
        if (file.type === 'pdf') {
            previewFileUrl.value = file.path;
            previewMode.value = 'pdf';
            showPreviewModal.value = true;
        } else {
            // 优先检测同名 PDF（convert_ppt_to_pdf.py 转换结果）
            const pdfPath = file.path.replace(/\.pptx?$/i, '.pdf');
            try {
                const resp = await fetch(pdfPath, { method: 'HEAD' });
                const contentType = resp.headers.get('content-type') || '';
                if (resp.ok && contentType.toLowerCase().includes('application/pdf')) {
                    previewFileUrl.value = pdfPath;
                    previewMode.value = 'pdf';
                    showPreviewModal.value = true;
                    return;
                }
            } catch (e) { /* PDF 未找到，降级 */ }
            // 降级：微软在线预览
            previewMode.value = 'office';
            const abs = new URL(file.path, window.location.href).href;
            previewFileUrl.value = `https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(abs)}`;
            showPreviewModal.value = true;
        }
    };

    const downloadCurrentFileDirectly = () => {
        if (!activePreviewFile.value) return;
        const link = document.createElement('a');
        link.href = activePreviewFile.value.path;
        link.download = activePreviewFile.value.name;
        link.click();
        showToast(`已触发下载: ${activePreviewFile.value.name}`);
    };

    const syncToKnowledgeBase = (file) => {
        const exists = files.value.some(f => f.name === file.name);
        if (exists) {
            showToast('该文件已在私有知识库中', 'error');
            return;
        }
        files.value.unshift({ id: Date.now(), name: file.name, size: file.size });
        showToast(`「${file.name}」已同步至私有知识库 ✓`);
    };

    // 监控 selectedPathwayCourseId 的改变
    watch(selectedPathwayCourseId, (newVal) => {
        localStorage.setItem('selectedPathwayCourseId', newVal);
    });

    return {
        courses,
        selectedCourse,
        previewFileUrl,
        previewFileName,
        showPreviewModal,
        activePreviewFile,
        previewMode,
        currentPptGuide,
        currentSlideIndex,
        selectedPathwayCourseId,
        pathwayOption,
        activeNodeDetails,
        selectCourse,
        handleNodeClick,
        viewCoursePathway,
        previewFile,
        downloadCurrentFileDirectly,
        syncToKnowledgeBase
    };
}
