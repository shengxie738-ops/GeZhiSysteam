import request from '../utils/request.js';

const API_BASE =
    window.HOMEWORK_API_BASE_URL ||
    localStorage.getItem('homeworkApiBaseUrl') ||
    '';

const now = new Date();
const addDays = (days) => {
    const date = new Date(now.getTime() + days * 24 * 60 * 60 * 1000);
    return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

async function requestJson(path, options = {}, mockFallback) {
    const useMockFirst = localStorage.getItem('homeworkMockFirst') === 'true';

    // 将原始数据包装为前后端约定的标准 DTO 格式
    const wrapStandardDTO = (data) => ({
        code: 200,
        message: 'ok',
        data: data
    });

    // 核心的拦截器解包逻辑
    const handleResponseDTO = (json) => {
        if (json && json.code === 200) {
            return json.data; // 只向组件返回纯净的业务数据
        } else {
            console.error('[API 业务异常]', json?.message || '未知错误');
            // 后续可以在此接入全局 Toast
            throw new Error(json?.message || 'API 请求失败');
        }
    };

    if (useMockFirst && typeof mockFallback === 'function') {
        // Mock 模式：打包成 DTO 后再解包，保证执行链路完全一致
        const mockData = await mockFallback();
        const mockDTO = wrapStandardDTO(mockData);
        return handleResponseDTO(mockDTO);
    }

    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    try {
        const json = await request(`${API_BASE}${path}`, {
            ...options,
            headers
        });
        // 真实请求：校验契约并解包
        return handleResponseDTO(json);
    } catch (error) {
        if (typeof mockFallback === 'function') {
            const mockData = await mockFallback(error);
            const mockDTO = wrapStandardDTO(mockData);
            return handleResponseDTO(mockDTO);
        }
        throw error;
    }
}

// 预设科目卡片墙数据
export const mockSubjects = [
    { id: 'FE-401', name: '高级前端程序设计', code: 'FE-401', icon: 'ph-code', bgClass: 'from-blue-500/10 to-indigo-500/5 border-blue-500/20 text-blue-600' },
    { id: 'DS-201', name: '数据结构与算法', code: 'DS-201', icon: 'ph-git-fork', bgClass: 'from-emerald-500/10 to-teal-500/5 border-emerald-500/20 text-emerald-600' },
    { id: 'AI-101', name: '人工智能技术基础', code: 'AI-101', icon: 'ph-brain', bgClass: 'from-purple-500/10 to-pink-500/5 border-purple-500/20 text-purple-600' },
    { id: 'DB-301', name: '数据库系统原理', code: 'DB-301', icon: 'ph-database', bgClass: 'from-amber-500/10 to-orange-500/5 border-amber-500/20 text-amber-600' }
];

// 升级后的 Mock 作业数据库（支持科目分配与混合题型）
let mockHomeworkStore = [
    {
        id: 'hw-daily-01',
        subjectId: 'FE-401',
        subjectName: '高级前端程序设计',
        type: 'daily',
        title: '响应式系统与Proxy核心拦截器',
        deadline: addDays(0.4),
        urgent: true,
        status: 'unsubmitted', // unsubmitted, submitted, graded
        grade: null,
        teacherComment: '',
        diagnosis: null,
        questions: [
            {
                id: 'q1',
                type: 'choice',
                title: '在 Vue 3 的 reactive 响应式实现中，在 Proxy 的 get 与 set 拦截器中，为何必须配合使用 Reflect.get 与 Reflect.set 访问属性？',
                options: [
                    'A. 为了提升 Proxy 在属性劫持与检索时的底层调用吞吐性能。',
                    'B. 为了保证当代理对象被继承时，getter/setter 内部的 this 能够正确指向当前代理对象（Receiver）。',
                    'C. 它是 TypeScript 编译器的硬性强类型检测要求。',
                    'D. 为了实现深度 Proxy 响应式嵌套，否则只能做浅层属性捕获。'
                ],
                correctAnswer: 'B'
            },
            {
                id: 'q2',
                type: 'blank',
                title: 'Vue 3 的响应式原理中，在 Proxy 拦截的 get 操作中需要执行 ______ 动作以收集依赖；而在 set 拦截操作中则需要执行 ______ 动作来分发更新。',
                correctAnswers: ['track', 'trigger']
            },
            {
                id: 'q3',
                type: 'programming',
                title: '编写一个简易的 reactive(target) 壳体',
                desc: '请编写一个 reactive(target) 函数。如果传入参数是对象，使用 Proxy 进行属性劫持，并在 get 拦截时调用 track(target, key)，set 拦截时调用 trigger(target, key, val) 并返回。',
                starterCode: `// 模拟依赖收集与分发
function track(target, key) {
  console.log(\`[track] 收集属性: \${key}\`);
}
function trigger(target, key, val) {
  console.log(\`[trigger] 属性更新: \${key} = \${val}\`);
}

function reactive(target) {
  if (typeof target !== 'object' || target === null) {
    return target;
  }
  
  const handler = {
    get(target, key, receiver) {
      // 1. 调用 track
      // 2. 结合 Reflect 返回结果
      return Reflect.get(target, key, receiver);
    },
    set(target, key, value, receiver) {
      // 1. 调用 trigger
      // 2. 结合 Reflect 返回布尔结果
      return Reflect.set(target, key, value, receiver);
    }
  };
  
  return new Proxy(target, handler);
}`,
                correctAnswers: ['Reflect', 'Proxy']
            }
        ],
        submittedAnswers: { q1: '', q2_0: '', q2_1: '', q3: '' },
        submittedFile: null
    },
    {
        id: 'hw-daily-02',
        subjectId: 'DS-201',
        subjectName: '数据结构与算法',
        type: 'daily',
        title: '双向链表防悬挂与单链表反转实战',
        deadline: addDays(0.6),
        urgent: true,
        status: 'unsubmitted',
        grade: null,
        teacherComment: '',
        diagnosis: null,
        questions: [
            {
                id: 'q1',
                type: 'choice',
                title: '在执行双向循环链表节点插入时，为了避免“指针空悬”与“前驱节点丢失”，最合理的指针修改次序是：',
                options: [
                    'A. 先修改前驱节点的后继，再修改后继节点的前驱，最后挂接新节点。',
                    'B. 先将新节点的前驱、后继指针挂接，再修改周围关联节点的指向。',
                    'C. 必须先释放前驱节点内存，再建立关联。',
                    'D. 顺序完全无关，只要在同一事件循环中执行即可。'
                ],
                correctAnswer: 'B'
            },
            {
                id: 'q2',
                type: 'blank',
                title: '递归算法在底层运行中，系统通常借助 ______ 这一先进后出的数据结构来保存函数调用的现场，以在返回时逆序复盘。',
                correctAnswers: ['栈']
            },
            {
                id: 'q3',
                type: 'programming',
                title: '空间复杂度为 O(1) 的单链表反转算法',
                desc: '手写完成单链表节点反转算法 `reverseList(head)`，要求在原地执行，不得分配额外的链表节点空间。',
                starterCode: `class ListNode {
  constructor(val = 0, next = null) {
    this.val = val;
    this.next = next;
  }
}

function reverseList(head) {
  let prev = null;
  let curr = head;
  while (curr !== null) {
    let nextTemp = curr.next;
    curr.next = prev;
    prev = curr;
    curr = nextTemp;
  }
  return prev;
}`,
                correctAnswers: ['curr.next', 'prev']
            }
        ],
        submittedAnswers: { q1: '', q2_0: '', q3: '' },
        submittedFile: null
    },
    {
        id: 'hw-milestone-01',
        subjectId: 'AI-101',
        subjectName: '人工智能技术基础',
        type: 'milestone',
        title: '自注意力机制矩阵计算与梯度分析',
        deadline: addDays(1.9),
        urgent: false,
        status: 'unsubmitted',
        grade: null,
        teacherComment: '',
        diagnosis: null,
        questions: [
            {
                id: 'q1',
                type: 'choice',
                title: '在 Transformer 的 Scaled Dot-Product Attention 中，除以 1/sqrt(d_k) 缩放因子的核心学术动因是：',
                options: [
                    'A. 防止点积计算结果过大，导致 Softmax 计算所得概率向极端分化（0或1），从而引发严重的梯度消失。',
                    'B. 对向量进行单位化归一化，使其欧氏距离为 1。',
                    'C. 它是多头自注意力并行的多线程对齐占位符。',
                    'D. 提升全连接前向传播的稀疏度。'
                ],
                correctAnswer: 'A'
            },
            {
                id: 'q2',
                type: 'blank',
                title: '输入维度为 [Batch, SeqLen, d_model] 时，经线性变换映射到 Query、Key、Value，若投影到多头，单头维数为 d_k，则 Q 矩阵的最终单头维度应为 ______。',
                correctAnswers: ['[Batch, SeqLen, d_k]']
            },
            {
                id: 'q3',
                type: 'text',
                title: '自注意力机制的优势与缺陷分析',
                desc: '推导自注意力机制的核心公式并结合公式，分析它在处理超长上下文（SeqLen > 10K）时所面临的空间与时间复杂度瓶颈。',
                starterCode: ''
            }
        ],
        submittedAnswers: { q1: '', q2_0: '', q3: '' },
        submittedFile: null
    },
    {
        id: 'hw-capstone-01',
        subjectId: 'DB-301',
        subjectName: '数据库系统原理',
        type: 'capstone',
        title: '支持事务并发的 B+ 树索引方案提报',
        deadline: addDays(5.0),
        urgent: false,
        status: 'unsubmitted',
        grade: null,
        teacherComment: '',
        diagnosis: null,
        questions: [
            {
                id: 'q1',
                type: 'choice',
                title: '在数据库引擎的隔离级别中，为了彻底避免“幻读”现象，最理想的隔离级别是：',
                options: [
                    'A. 读未提交 (Read Uncommitted)',
                    'B. 读已提交 (Read Committed)',
                    'C. 可重复读 (Repeatable Read)',
                    'D. 可串行化 (Serializable)'
                ],
                correctAnswer: 'D'
            },
            {
                id: 'q2',
                type: 'blank',
                title: '在经典的 B+ 树索引结构中，非叶子节点通常仅存放 ______ 键值作为路由；而真实的数据行记录或物理数据指针，则强制集中存放在 ______ 节点上。',
                correctAnswers: ['索引', '叶子']
            },
            {
                id: 'q3',
                type: 'text',
                title: '大作业：设计支持并发及 ACID 事务的 B+ 树',
                desc: '请提交您的设计书，说明两阶段锁（2PL）锁升级原理与物理 Write-Ahead Logging (WAL) 在 B+ 树分裂时的事务崩溃恢复设计。请提交压缩成果包。',
                starterCode: ''
            }
        ],
        submittedAnswers: { q1: '', q2_0: '', q2_1: '', q3: '' },
        submittedFile: null
    }
];

const CLASS_SIZE = 48;
const HW_DAILY_01_TITLE = '响应式系统与Proxy核心拦截器';

function resolveSubjectId(subject = '') {
    const matched = mockSubjects.find(item => subject.includes(item.name) || item.name.includes(subject));
    if (matched) return matched.id;
    if (subject.includes('前端') || subject.includes('Proxy') || subject.includes('Vue')) return 'FE-401';
    if (subject.includes('数据结构') || subject.includes('AVL') || subject.includes('链表')) return 'DS-201';
    if (subject.includes('人工智能') || subject.includes('AI')) return 'AI-101';
    if (subject.includes('数据库')) return 'DB-301';
    return 'DS-201';
}

function buildTeacherAssignedHomework(payload = {}) {
    const subject = payload.subject || '数据结构与算法';
    const subjectId = resolveSubjectId(subject);
    const subjectMeta = mockSubjects.find(item => item.id === subjectId);
    const isQuiz = payload.type === 'quiz';
    return {
        id: `teacher-${payload.type || 'homework'}-${Date.now()}`,
        subjectId,
        subjectName: subjectMeta?.name || subject,
        type: isQuiz ? 'daily' : (payload.type || 'daily'),
        title: payload.title || '教师下发补弱任务',
        deadline: payload.deadline || '今天 23:59',
        urgent: payload.priority !== 'low',
        status: 'unsubmitted',
        grade: null,
        teacherComment: '',
        classInsight: '该任务由教师端班级学情干预指挥中心下发，完成后会回流到教师端交互闭环记录。',
        diagnosis: null,
        questions: [
            {
                id: 'q1',
                type: 'choice',
                title: `${payload.title || '补弱任务'}：请选择最符合本次知识点的处理策略。`,
                options: [
                    'A. 先复盘错因，再完成同类题迁移。',
                    'B. 只看答案，不需要重新提交。',
                    'C. 跳过薄弱点，等待期末统一复习。',
                    'D. 只完成客观题即可。'
                ],
                correctAnswer: 'A'
            },
            {
                id: 'q2',
                type: 'text',
                title: '写下本次订正后的关键理解',
                desc: payload.desc || '请用自己的话说明错因、修正方法和下一步练习计划。',
                starterCode: ''
            },
            {
                id: 'q3',
                type: 'programming',
                title: isQuiz ? '短测编程/推导题' : '补弱实战题',
                desc: payload.desc || '请完成教师下发的补弱练习，并在运行后提交。',
                starterCode: `// 根据教师端下发的任务要求完成
function solve() {
  return null;
}`
            }
        ],
        submittedAnswers: { q1: '', q2: '', q3: '' },
        submittedFile: null,
        source: {
            module: 'teacher-analytics',
            recordId: payload.recordId || null
        }
    };
}

const strongReactiveCode = `function reactive(target) {
  if (typeof target !== 'object' || target === null) return target;
  return new Proxy(target, {
    get(target, key, receiver) {
      track(target, key);
      return Reflect.get(target, key, receiver);
    },
    set(target, key, value, receiver) {
      const result = Reflect.set(target, key, value, receiver);
      trigger(target, key, value);
      return result;
    }
  });
}`;

const partialReactiveCode = `function reactive(target) {
  if (!target || typeof target !== 'object') return target;
  return new Proxy(target, {
    get(target, key) {
      track(target, key);
      return target[key];
    },
    set(target, key, value) {
      target[key] = value;
      trigger(target, key, value);
      return true;
    }
  });
}`;

const weakReactiveCode = `function reactive(target) {
  return new Proxy(target, {
    get(target, key) {
      return target[key];
    },
    set(target, key, val) {
      target[key] = val;
      return true;
    }
  });
}`;

function diagnosis(scores, alinaMsg, codeninjaMsg, profxMsg) {
    return {
        scores,
        alinaMsg: `Alina诊断：${alinaMsg}`,
        codeninjaMsg: `CodeNinja诊断：${codeninjaMsg}`,
        profxMsg: `Prof. X诊断：${profxMsg}`
    };
}

// 教师端 Mock 提交表单。字段结构按后端返回形态组织，便于后续数据库接入。
let mockSubmissions = [
    {
        id: 'sub-01',
        studentName: '李明',
        className: '计科 2301',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '1小时前',
        status: 'pending',
        answers: { q1: 'B', q2_0: 'track', q2_1: 'trigger', q3: strongReactiveCode },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 90, codeninja: 94, profx: 88 },
            '学习路线对齐精准，Proxy 及 Reflect 配合完整，建议继续研究 effect.js 副作用调度。',
            '正确使用 Reflect 并传入 receiver，能解释原型继承链上的 this 绑定风险。',
            '客观题回答无误，编程题在 get/set 的 track/trigger 职责拆分上表述清晰。'
        )
    },
    {
        id: 'sub-02',
        studentName: '王雨辰',
        className: '计科 2301',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '1.5小时前',
        status: 'graded',
        answers: { q1: 'B', q2_0: 'track', q2_1: 'trigger', q3: strongReactiveCode },
        file: null,
        grade: 'A',
        teacherComment: '完成度高，尤其是 receiver 参数的解释准确。下一步可以补充 effect 栈和嵌套依赖场景。',
        diagnosis: diagnosis(
            { alina: 92, codeninja: 91, profx: 90 },
            '作业节奏和知识目标高度一致，具备迁移到复杂响应式系统的基础。',
            '代码结构紧凑，边界判断完整，Reflect 使用符合工程规范。',
            '能把依赖收集和更新触发放回发布订阅模型中解释，理论表达稳定。'
        )
    },
    {
        id: 'sub-03',
        studentName: '陈思远',
        className: '计科 2301',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '2小时前',
        status: 'pending',
        answers: { q1: 'B', q2_0: 'track', q2_1: 'trigger', q3: strongReactiveCode },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 88, codeninja: 90, profx: 86 },
            '整体掌握扎实，答题路径清晰，但对异常对象输入的说明还可以更完整。',
            'Proxy 与 Reflect 组合正确，代码可读性好。',
            '理论题命中核心概念，建议补充 receiver 与 getter 的案例推导。'
        )
    },
    {
        id: 'sub-04',
        studentName: '赵一诺',
        className: '计科 2301',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '2.5小时前',
        status: 'pending',
        answers: { q1: 'B', q2_0: 'track', q2_1: 'trigger', q3: partialReactiveCode },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 84, codeninja: 74, profx: 80 },
            '客观题掌握良好，说明基础概念已经建立。',
            '代码能完成基本拦截，但直接读取 target[key]，在 getter 继承场景下存在 this 指向偏差。',
            '能区分 track 与 trigger，但没有说明 Reflect receiver 的理论价值。'
        )
    },
    {
        id: 'sub-05',
        studentName: '刘佳琪',
        className: '计科 2301',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '3小时前',
        status: 'review',
        answers: { q1: 'B', q2_0: 'collect', q2_1: 'trigger', q3: partialReactiveCode },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 72, codeninja: 70, profx: 68 },
            '能识别 set 阶段触发更新，但 get 阶段依赖收集命名和职责仍不稳定。',
            '实现有 Proxy 主体，但未使用 Reflect，边界说明不足。',
            '发布订阅模型理解处于半成型状态，需要回看依赖收集桶的定义。'
        )
    },
    {
        id: 'sub-06',
        studentName: '周泽宇',
        className: '计科 2302',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '3.5小时前',
        status: 'pending',
        answers: { q1: 'C', q2_0: 'track', q2_1: 'trigger', q3: partialReactiveCode },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 70, codeninja: 72, profx: 66 },
            '填空题稳定，但选择题误把语言工具约束当成框架原理。',
            '代码完成主流程，缺少 Reflect receiver，工程边界不够稳。',
            '能记住术语，但对为什么使用 Reflect 的解释偏弱。'
        )
    },
    {
        id: 'sub-07',
        studentName: '黄子墨',
        className: '计科 2302',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '4小时前',
        status: 'pending',
        answers: { q1: 'A', q2_0: 'get', q2_1: 'set', q3: weakReactiveCode },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 55, codeninja: 48, profx: 50 },
            '日常 Checkpoint 掌握度不佳，客观题答题偏差较大，需要重建基本概念。',
            '未引入 Reflect，且缺少 track/trigger，当前实现更接近普通属性代理。',
            '选择题与填空题均未命中核心理论概念，模型抽象能力需要重塑。'
        )
    },
    {
        id: 'sub-08',
        studentName: '吴桐',
        className: '计科 2302',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '4.5小时前',
        status: 'pending',
        answers: { q1: 'D', q2_0: 'watch', q2_1: 'notify', q3: weakReactiveCode },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 52, codeninja: 45, profx: 46 },
            '把深层代理和基础依赖收集混在一起，答题路线偏离本次目标。',
            '代码缺少依赖收集和更新触发，无法支撑响应式闭环。',
            '术语替换较多，但没有对应到 Vue 3 响应式源码中的职责划分。'
        )
    },
    {
        id: 'sub-09',
        studentName: '孙嘉禾',
        className: '计科 2302',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '5小时前',
        status: 'review',
        answers: { q1: 'B', q2_0: 'track', q2_1: 'set', q3: `function reactive(target) {
  return new Proxy(target, {
    get(target, key, receiver) {
      track(target, key);
      return Reflect.get(target, key, receiver);
    }
  });
}` },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 69, codeninja: 62, profx: 64 },
            '选择题正确，说明知道 receiver 的价值，但 set 阶段职责没有闭环。',
            'get 拦截写法较好，缺少 set 拦截导致更新触发路径断裂。',
            'trigger 概念掌握不稳，需要用数据流图复盘 get 与 set 的先后职责。'
        )
    },
    {
        id: 'sub-10',
        studentName: '郑可欣',
        className: '计科 2302',
        homeworkId: 'hw-daily-01',
        homeworkTitle: HW_DAILY_01_TITLE,
        submittedAt: '6小时前',
        status: 'pending',
        answers: { q1: 'A', q2_0: '', q2_1: 'trigger', q3: weakReactiveCode },
        file: null,
        grade: null,
        teacherComment: '',
        diagnosis: diagnosis(
            { alina: 48, codeninja: 42, profx: 44 },
            '答题完整度偏低，依赖收集环节缺失，是本次作业首要补弱对象。',
            '代码只保留了 Proxy 外壳，没有建立响应式更新链路。',
            '对 get 阶段为什么要收集依赖缺少明确认识，建议从最小发布订阅例子重学。'
        )
    }
];

// 智能体协同会诊生成算法
function generateMockDiagnosis(homeworkId, answers) {
    if (homeworkId === 'hw-daily-01') {
        const isQ1Correct = answers.q1 === 'B';
        const isQ2_0Correct = answers.q2_0?.toLowerCase().trim() === 'track';
        const isQ2_1Correct = answers.q2_1?.toLowerCase().trim() === 'trigger';
        const codeText = answers.q3 || '';
        const hasReflect = codeText.includes('Reflect');
        const hasProxy = codeText.includes('Proxy');

        let alinaScore = 60;
        let ninjaScore = 55;
        let profScore = 50;

        if (isQ1Correct) { alinaScore += 10; profScore += 10; }
        if (isQ2_0Correct && isQ2_1Correct) { alinaScore += 15; profScore += 15; }
        if (hasProxy) { ninjaScore += 15; }
        if (hasReflect) { ninjaScore += 15; profScore += 5; }

        alinaScore = Math.min(alinaScore, 100);
        ninjaScore = Math.min(ninjaScore, 100);
        profScore = Math.min(profScore, 100);

        return {
            scores: { alina: alinaScore, codeninja: ninjaScore, profx: profScore },
            alinaMsg: alinaScore > 85 
                ? 'Alina诊断：客观题全对，整体学习步调完全对齐大纲，响应式系统的拦截器建模处于班级领先水平。' 
                : 'Alina诊断：进度卡点，客观题中的依赖桶交互理论尚未消化完全，建议在控制台反复调试 track/trigger。',
            codeninjaMsg: hasReflect
                ? 'CodeNinja诊断：极其标准的 Proxy-Reflect 组合拦截！成功通过 Receiver 绑定抵抗了 Proxy 原型链 getter 穿透问题。'
                : 'CodeNinja诊断：警告！未使用 Reflect.get，在处理继承了代理对象的普通对象时，getter 中的 this 会指向原始对象而非代理，存在安全漏洞。',
            profxMsg: isQ2_0Correct && isQ2_1Correct
                ? 'Prof. X诊断：正确指出了依赖收集桶 track 与更新触发器 trigger 的功能属性，在发布订阅模式机制上掌握扎实。'
                : 'Prof. X诊断：依赖项拦截概念不清晰，未能明确区分 track 桶与 trigger 触发器的理论差异。'
        };
    } else {
        // 通用诊断
        return {
            scores: { alina: 82, codeninja: 84, profx: 80 },
            alinaMsg: 'Alina诊断：科目作业总体完成度较高，规划目标已圆满实现，本阶段学习任务推进平稳。',
            codeninjaMsg: 'CodeNinja诊断：对于代码部分和算法部分的工程设计符合规范，边界条件基本实现闭环。',
            profxMsg: 'Prof. X诊断：客观题考查的概念模型掌握到位，展现了合格的理论分析素养与知识底蕴。'
        };
    }
}

function getSubmissionAiScore(submission) {
    const scores = submission?.diagnosis?.scores;
    if (!scores) return null;
    return Math.round((scores.alina + scores.codeninja + scores.profx) / 3);
}

function gradeFromAiScore(score) {
    if (score === null || score === undefined) return '-';
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'E';
}

function getQuestionKnowledgePoint(question) {
    const mapping = {
        q1: 'Reflect receiver 与 getter this 绑定',
        q2: 'Vue 响应式依赖收集 track 与触发更新 trigger',
        q3: 'Proxy / Reflect 工程实现与响应式闭环'
    };
    return mapping[question.id] || '课程核心知识点';
}

function normalizeAnswer(value) {
    return String(value || '').trim().toLowerCase();
}

function getQuestionResult(submission, question) {
    const answers = submission?.answers || {};
    if (question.type === 'choice') {
        return normalizeAnswer(answers[question.id]) === normalizeAnswer(question.correctAnswer);
    }
    if (question.type === 'blank') {
        return question.correctAnswers.every((answer, index) => {
            return normalizeAnswer(answers[`${question.id}_${index}`]) === normalizeAnswer(answer);
        });
    }
    if (question.type === 'programming') {
        const code = String(answers[question.id] || '');
        if (question.id === 'q3' && submission.homeworkId === 'hw-daily-01') {
            return code.includes('Proxy') && code.includes('Reflect') && code.includes('track') && code.includes('trigger');
        }
        return getSubmissionAiScore(submission) >= 75;
    }
    return getSubmissionAiScore(submission) >= 75;
}

function enrichSubmission(homework, submission) {
    const questionResults = {};
    (homework?.questions || []).forEach((question) => {
        questionResults[question.id] = getQuestionResult(submission, question);
    });
    const aiScore = getSubmissionAiScore(submission);
    return {
        ...submission,
        aiScore,
        recommendedGrade: gradeFromAiScore(aiScore),
        questionResults
    };
}

function buildHomeworkAnalysis(homework, submissions) {
    const enriched = submissions.map((submission) => enrichSubmission(homework, submission));
    const submittedCount = enriched.length;
    const gradedCount = enriched.filter((submission) => submission.status === 'graded').length;
    const pendingCount = enriched.filter((submission) => submission.status !== 'graded').length;
    const scoreItems = enriched.map((submission) => submission.aiScore).filter((score) => score !== null);
    const averageAiScore = scoreItems.length
        ? Math.round(scoreItems.reduce((sum, score) => sum + score, 0) / scoreItems.length)
        : 0;

    const questionStats = (homework?.questions || []).map((question, index) => {
        const wrongStudents = enriched.filter((submission) => !submission.questionResults[question.id]);
        const errorRate = submittedCount ? Math.round((wrongStudents.length / submittedCount) * 100) : 0;
        return {
            id: question.id,
            label: `Q${index + 1}`,
            title: question.title,
            type: question.type,
            knowledgePoint: getQuestionKnowledgePoint(question),
            wrongCount: wrongStudents.length,
            correctCount: submittedCount - wrongStudents.length,
            totalCount: submittedCount,
            errorRate,
            wrongStudents: wrongStudents.map((submission) => submission.studentName),
            insight: buildQuestionInsight(question, errorRate),
            typicalWrongCode: buildTypicalWrongCode(question)
        };
    }).sort((a, b) => b.errorRate - a.errorRate);

    const topErrorQuestion = questionStats[0] || null;
    const weakKnowledgePoints = questionStats
        .filter((item) => item.errorRate >= 30)
        .map((item) => item.knowledgePoint);

    // Mock: 为 Q3 生成思路族谱
    const thoughtGenealogy = {
        questionTitle: 'Proxy 与 Reflect 响应式拦截 (Q3)',
        totalAnalyzed: 48,
        branches: [
            {
                id: 'b1',
                type: 'correct',
                name: '标准代理 + 接收器转发',
                desc: '正确使用了 Proxy 和 Reflect.get(..., receiver)，保证了 this 指向。',
                studentCount: 25,
                percentage: 52
            },
            {
                id: 'b2',
                type: 'flawed',
                name: '属性直读丢失上下文',
                desc: '使用了 Proxy 但在 get 中直接 return target[key]，导致继承时 this 穿透错误。',
                studentCount: 15,
                percentage: 31,
                sampleCode: 'get(target, key) {\\n  return target[key];\\n}'
            },
            {
                id: 'b3',
                type: 'flawed',
                name: '依赖收集节点错位',
                desc: '未在正确生命周期调用 track()，或 track 逻辑外漏。',
                studentCount: 8,
                percentage: 17,
                sampleCode: 'track();\\nreturn Reflect.get(...);'
            }
        ]
    };

    return {
        homeworkId: homework?.id,
        homeworkTitle: homework?.title,
        submittedCount,
        classSize: CLASS_SIZE,
        submitRate: Math.round((submittedCount / CLASS_SIZE) * 100) || 0,
        gradedCount,
        pendingCount,
        averageAiScore,
        topErrorQuestion,
        weakKnowledgePoints,
        thoughtGenealogy,
        questionStats,
        highRiskStudents: enriched
            .filter((submission) => (submission.aiScore || 0) < 60 || submission.status === 'review')
            .map((submission) => submission.studentName),
        generatedAt: new Date().toLocaleString()
    };
}

function buildQuestionInsight(question, errorRate) {
    const point = getQuestionKnowledgePoint(question);
    if (question.id === 'q2') {
        return `多数错误集中在 ${point}，学生容易把 get 阶段的依赖收集和 set 阶段的更新触发混为普通读写操作。`;
    }
    if (question.id === 'q3') {
        return `错误主要来自 ${point}，常见问题是直接使用 target[key]，忽略 Reflect.get / Reflect.set 的 receiver 语义。`;
    }
    if (question.id === 'q1') {
        return `错误说明学生对 ${point} 的必要性理解不足，容易把框架原理误判为性能优化或类型系统要求。`;
    }
    return errorRate >= 50
        ? `${point} 掌握不稳，建议安排课堂复盘。`
        : `${point} 整体掌握可接受，可用少量例题巩固。`;
}

function buildTypicalWrongCode(question) {
    if (question.type !== 'programming') return null;
    if (question.id === 'q3') {
        return `// 未正确处理 receiver 与 trigger
function reactive(target) {
  return new Proxy(target, {
    get(target, key) {
      return target[key];
    },
    set(target, key, val) {
      target[key] = val;
      return true;
    }
  });
}`;
    }
    return null;
}

function buildHomeworkReport(homework, submissions) {
    const analysis = buildHomeworkAnalysis(homework, submissions);
    const masteryLevel = analysis.averageAiScore >= 85
        ? '整体掌握良好'
        : analysis.averageAiScore >= 70
            ? '整体掌握中等，存在局部卡点'
            : '整体掌握偏弱，需要集中补救';
    const topItems = analysis.questionStats.slice(0, 3);
    const studentInsight = `本次作业班级共性问题集中在 ${analysis.weakKnowledgePoints.join('、') || '核心题目复盘'}。建议复看响应式依赖收集部分，并完成针对性补弱练习。`;

    return {
        homeworkId: homework?.id,
        title: `${homework?.title || '作业'} AI 作业报告`,
        generatedAt: analysis.generatedAt,
        overview: {
            submittedCount: analysis.submittedCount,
            classSize: analysis.classSize,
            gradedCount: analysis.gradedCount,
            pendingCount: analysis.pendingCount,
            averageAiScore: analysis.averageAiScore,
            masteryLevel
        },
        topErrorQuestions: topItems,
        weakKnowledgePoints: analysis.weakKnowledgePoints,
        layeredAdvice: {
            advanced: '高分学生可补做 effect 栈、嵌套依赖和调度器设计题，形成源码级理解。',
            middle: '中段学生需要用一张数据流图复盘 get -> track、set -> trigger 的职责分界。',
            risk: '低分学生先完成最小发布订阅模型，再回到 Proxy/Reflect 组合实现。'
        },
        teacherSuggestions: [
            '下次课先用 getter 继承案例解释 receiver 的必要性。',
            '用表格对比 track、trigger、Reflect.get、Reflect.set 的输入输出。',
            '安排 10 分钟随堂改错，让学生修复 target[key] 直接访问的问题。'
        ],
        studentInsight,
        summary: `${masteryLevel}。最高错误率题目为 ${analysis.topErrorQuestion?.label || '-'}，薄弱知识点集中在 ${analysis.weakKnowledgePoints.join('、') || '暂无明显集中项'}。`
    };
}

export const homeworkApi = {
    // 学生端：获取作业列表
    getStudentHomeworkList(userId) {
        return requestJson(`/homework/student/list?userId=${encodeURIComponent(userId)}`, {}, () => {
            return mockHomeworkStore;
        });
    },

    // 学生端：获取单项作业详情
    getHomeworkDetails(homeworkId, userId) {
        return requestJson(`/homework/${encodeURIComponent(homeworkId)}?userId=${encodeURIComponent(userId)}`, {}, () => {
            const hw = mockHomeworkStore.find(h => h.id === homeworkId);
            return hw || mockHomeworkStore[0];
        });
    },

    // 学生端：提交作业
    submitHomework(homeworkId, payload) {
        return requestJson(`/homework/${encodeURIComponent(homeworkId)}/submit`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const hw = mockHomeworkStore.find(h => h.id === homeworkId);
            if (hw) {
                hw.status = 'submitted';
                hw.submittedAnswers = { ...payload.answers };
                hw.submittedFile = payload.file || null;
                
                // 推送或更新教师端 submissions
                const submitterName = payload.studentName || '李明';
                const existingSub = mockSubmissions.find(s => s.homeworkId === homeworkId && s.studentName === submitterName);
                if (existingSub) {
                    existingSub.status = 'pending';
                    existingSub.answers = { ...payload.answers };
                    existingSub.file = payload.file || null;
                    existingSub.diagnosis = hw.diagnosis;
                } else {
                    mockSubmissions.push({
                        id: `sub-${Date.now()}`,
                        studentName: submitterName,
                        className: '计科 2301',
                        homeworkId: homeworkId,
                        homeworkTitle: hw.title,
                        submittedAt: '刚刚',
                        answers: { ...payload.answers },
                        file: payload.file || null,
                        status: 'pending',
                        grade: null,
                        teacherComment: '',
                        diagnosis: hw.diagnosis
                    });
                }
            }
            return { success: true, submittedAt: new Date().toISOString() };
        });
    },

    // 学生端：请求多智能体诊断
    requestAgentDiagnosis(homeworkId, answers) {
        return requestJson(`/homework/${encodeURIComponent(homeworkId)}/diagnose`, {
            method: 'POST',
            body: JSON.stringify({ answers })
        }, () => {
            const diagnosis = generateMockDiagnosis(homeworkId, answers);
            
            // 同步回学生 store
            const hw = mockHomeworkStore.find(h => h.id === homeworkId);
            if (hw) {
                hw.diagnosis = diagnosis;
            }
            
            // 同步回教师批改表中的对应记录
            const sub = mockSubmissions.find(s => s.homeworkId === homeworkId && s.studentName === '李明');
            if (sub) {
                sub.diagnosis = diagnosis;
            }

            return diagnosis;
        });
    },

    // 教师端：获取作业总览
    getTeacherHomeworkOverview() {
        return requestJson('/homework/teacher/overview', {}, () => {
            const totalHws = mockHomeworkStore.length;
            const totalSubs = mockSubmissions.length;
            const gradedSubs = mockSubmissions.filter(s => s.status === 'graded').length;
            const allScores = mockSubmissions.map(getSubmissionAiScore).filter((score) => score !== null);
            const averageAiScore = allScores.length
                ? Math.round(allScores.reduce((sum, score) => sum + score, 0) / allScores.length)
                : 0;
            
            return {
                summary: {
                    activeHomeworks: totalHws,
                    totalSubmissions: totalSubs,
                    pendingGrading: totalSubs - gradedSubs,
                    averageAiScore
                },
                homeworks: mockHomeworkStore.map(hw => {
                    const hwSubs = mockSubmissions.filter(s => s.homeworkId === hw.id);
                    const analysis = buildHomeworkAnalysis(hw, hwSubs);
                    return {
                        id: hw.id,
                        title: hw.title,
                        type: hw.type,
                        subject: hw.subjectName,
                        deadline: hw.deadline,
                        questions: hw.questions,
                        submitRate: analysis.submitRate,
                        gradedCount: hwSubs.filter(s => s.status === 'graded').length,
                        pendingCount: analysis.pendingCount,
                        totalCount: hwSubs.length,
                        classSize: CLASS_SIZE,
                        averageAiScore: analysis.averageAiScore,
                        topErrorQuestion: analysis.topErrorQuestion,
                        weakKnowledgePoints: analysis.weakKnowledgePoints,
                        thoughtGenealogy: analysis.thoughtGenealogy
                    };
                })
            };
        });
    },

    // 教师端：获取特定作业的所有学生提交
    getHomeworkSubmissions(homeworkId) {
        return requestJson(`/homework/teacher/submissions?homeworkId=${encodeURIComponent(homeworkId)}`, {}, () => {
            const hw = mockHomeworkStore.find(h => h.id === homeworkId);
            return mockSubmissions
                .filter(s => s.homeworkId === homeworkId)
                .map((submission) => enrichSubmission(hw, submission));
        });
    },

    // 教师端：获取本次作业的题目错误率、薄弱知识点和风险学生
    getHomeworkAnalysis(homeworkId) {
        return requestJson(`/homework/teacher/analysis?homeworkId=${encodeURIComponent(homeworkId)}`, {}, () => {
            const hw = mockHomeworkStore.find(h => h.id === homeworkId);
            const submissions = mockSubmissions.filter(s => s.homeworkId === homeworkId);
            return buildHomeworkAnalysis(hw, submissions);
        });
    },

    // 教师端：生成可用于课堂复盘和学生端反馈的 AI 作业报告
    generateHomeworkReport(homeworkId) {
        return requestJson('/homework/teacher/report', {
            method: 'POST',
            body: JSON.stringify({ homeworkId })
        }, () => {
            const hw = mockHomeworkStore.find(h => h.id === homeworkId);
            const submissions = mockSubmissions.filter(s => s.homeworkId === homeworkId);
            const report = buildHomeworkReport(hw, submissions);
            if (hw) {
                hw.classInsight = report.studentInsight;
            }
            return report;
        });
    },

    // 教师端：批改作业
    gradeHomework(attemptId, payload) {
        return requestJson(`/homework/attempts/${encodeURIComponent(attemptId)}/grade`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const sub = mockSubmissions.find(s => s.id === attemptId);
            if (sub) {
                sub.status = 'graded';
                sub.grade = payload.grade;
                sub.teacherComment = payload.comment;
                
                // 将成绩同步回学生本地 Store
                const studentHw = mockHomeworkStore.find(h => h.id === sub.homeworkId);
                if (studentHw) {
                    studentHw.status = 'graded';
                    studentHw.grade = payload.grade;
                    studentHw.teacherComment = payload.comment;
                    studentHw.classInsight = payload.classInsight || studentHw.classInsight || '';
                }
            }
            return { success: true, gradedAt: new Date().toISOString() };
        });
    },

    // 学生端 Mock：接收教师端学情中心下发的补弱作业或短测。
    appendTeacherAssignedHomework(payload) {
        const newHw = buildTeacherAssignedHomework(payload);
        mockHomeworkStore.unshift(newHw);
        return newHw;
    },

    // 教师端：发布新作业
    createHomework(payload) {
        return requestJson('/homework', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const newHw = {
                id: `hw-${payload.type}-${Date.now()}`,
                subjectId: 'FE-401', // 默认分配
                subjectName: payload.subject,
                type: payload.type,
                title: payload.title,
                deadline: payload.deadline,
                urgent: false,
                status: 'unsubmitted',
                grade: null,
                teacherComment: '',
                diagnosis: null,
                questions: [
                    {
                        id: 'q1',
                        type: 'choice',
                        title: '新发布作业选择题：' + payload.title,
                        options: ['选项A', '选项B', '选项C', '选项D'],
                        correctAnswer: 'A'
                    },
                    {
                        id: 'q2',
                        type: 'blank',
                        title: '新发布作业填空题：' + payload.title,
                        correctAnswers: ['答案']
                    },
                    {
                        id: 'q3',
                        type: 'programming',
                        title: '编程任务实战',
                        desc: payload.desc,
                        starterCode: `// 开始编写代码
function solve() {

}`
                    }
                ],
                submittedAnswers: { q1: '', q2_0: '', q3: '' },
                submittedFile: null
            };
            mockHomeworkStore.unshift(newHw);
            return newHw;
        });
    }
};
