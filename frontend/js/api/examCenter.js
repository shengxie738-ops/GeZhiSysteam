import { API_BASE_URL } from '../config/env.js';
import { apiRequest } from '../utils/request.js';

const now = new Date();
const addHours = (hours) => {
    const date = new Date(now.getTime() + hours * 60 * 60 * 1000);
    return date.toISOString();
};

const mockStudentOverview = {
    summary: {
        upcoming: 3,
        active: 1,
        completed: 2,
        programming: 1
    },
    exams: [
        {
            id: 'exam-ds-midterm',
            title: '数据结构期中综合考试',
            subject: '数据结构',
            status: 'upcoming',
            startsAt: addHours(3.5),
            durationMinutes: 90,
            location: '线上考试中心',
            rules: ['开考前 15 分钟可进入候考', '考试期间自动保存答案', '禁止切换窗口超过 3 次'],
            questionTypes: [
                { type: 'choice', label: '选择题', count: 20, score: 40 },
                { type: 'blank', label: '填空题', count: 8, score: 24 },
                { type: 'programming', label: '编程题', count: 2, score: 36 }
            ],
            readiness: '设备检测未完成'
        },
        {
            id: 'exam-ai-quiz',
            title: '人工智能技术阶段测评',
            subject: '人工智能技术',
            status: 'upcoming',
            startsAt: addHours(26),
            durationMinutes: 60,
            location: '线上考试中心',
            rules: ['单选、多选与填空混合', '提交后显示客观题结果'],
            questionTypes: [
                { type: 'choice', label: '选择题', count: 25, score: 70 },
                { type: 'blank', label: '填空题', count: 5, score: 30 }
            ],
            readiness: '已完成设备检测'
        },
        {
            id: 'exam-code-final',
            title: '计算机程序设计上机考试',
            subject: '计算机程序设计',
            status: 'active',
            startsAt: addHours(-0.2),
            durationMinutes: 120,
            location: '编程考试入口',
            rules: ['仅允许使用内置 IDE', '可运行公开样例', '隐藏用例由后端判题'],
            questionTypes: [
                { type: 'programming', label: '编程题', count: 3, score: 100 }
            ],
            readiness: '可进入考试',
            programming: true,
            attemptId: 'attempt-code-final-demo'
        },
        {
            id: 'exam-db-closed',
            title: '数据库系统原理闭卷测验',
            subject: '数据库系统原理',
            status: 'completed',
            startsAt: addHours(-72),
            durationMinutes: 75,
            location: '线上考试中心',
            rules: ['已提交'],
            questionTypes: [
                { type: 'choice', label: '选择题', count: 30, score: 60 },
                { type: 'blank', label: '填空题', count: 10, score: 40 }
            ],
            score: 86,
            submittedAt: addHours(-70.5)
        }
    ],
    waitingSubjects: [
        { subject: '数据结构', time: '今天 19:30', duration: '90 分钟', type: '选择题 / 填空题 / 编程题' },
        { subject: '人工智能技术', time: '明天 18:00', duration: '60 分钟', type: '选择题 / 填空题' },
        { subject: '计算机组成原理', time: '06月30日 09:00', duration: '80 分钟', type: '选择题 / 填空题' }
    ]
};

const mockExamDetail = {
    id: 'exam-code-final',
    title: '计算机程序设计上机考试',
    subject: '计算机程序设计',
    status: 'active',
    startsAt: addHours(-0.2),
    durationMinutes: 120,
    remainingSeconds: 6420,
    programmingProblems: [
        {
            id: 'prog-two-sum',
            title: '两数之和',
            language: 'javascript',
            timeLimitMs: 1000,
            memoryLimitMb: 128,
            score: 35,
            description: '给定一个整数数组 nums 和一个目标值 target，请返回数组中和为目标值的两个整数下标。',
            inputHint: 'nums: number[], target: number',
            outputHint: 'number[]',
            funcName: 'twoSum',
            starterCode: `function twoSum(nums, target) {
  // 在这里编写你的代码
  return [];
}`,
            publicCases: [
                { label: '样例 1', input: [[2, 7, 11, 15], 9], expected: [0, 1] },
                { label: '样例 2', input: [[3, 2, 4], 6], expected: [1, 2] }
            ]
        },
        {
            id: 'prog-valid-brackets',
            title: '括号有效性',
            language: 'javascript',
            timeLimitMs: 1000,
            memoryLimitMb: 128,
            score: 30,
            description: '给定只包含 ()[]{} 的字符串，判断括号是否有效闭合。',
            inputHint: 's: string',
            outputHint: 'boolean',
            funcName: 'isValid',
            starterCode: `function isValid(s) {
  // 在这里编写你的代码
  return false;
}`,
            publicCases: [
                { label: '样例 1', input: ['()[]{}'], expected: true },
                { label: '样例 2', input: ['(]'], expected: false }
            ]
        }
    ],
    objectiveQuestions: [
        {
            id: 'choice-1',
            type: 'choice',
            title: '以下哪种结构适合实现函数调用栈？',
            options: ['队列', '栈', '哈希表', '堆'],
            score: 4
        },
        {
            id: 'blank-1',
            type: 'blank',
            title: '二分查找要求待查找序列满足 ______ 条件。',
            score: 4
        }
    ]
};

const mockTeacherDashboard = {
    summary: {
        today: 2,
        draft: 3,
        running: 1,
        review: 4
    },
    exams: [
        { id: 'exam-code-final', title: '计算机程序设计上机考试', subject: '计算机程序设计', status: 'running', startsAt: addHours(-0.2), durationMinutes: 120, entrants: 48, submitted: 17, abnormal: 2 },
        { id: 'exam-ds-midterm', title: '数据结构期中综合考试', subject: '数据结构', status: 'scheduled', startsAt: addHours(3.5), durationMinutes: 90, entrants: 0, submitted: 0, abnormal: 0 },
        { id: 'exam-ai-quiz', title: '人工智能技术阶段测评', subject: '人工智能技术', status: 'draft', startsAt: addHours(26), durationMinutes: 60, entrants: 0, submitted: 0, abnormal: 0 }
    ],
    submissions: [
        { id: 1, student: '李同学', exam: '计算机程序设计上机考试', status: '答题中', progress: 68, lastSavedAt: '2 分钟前', abnormal: false },
        { id: 2, student: '王同学', exam: '计算机程序设计上机考试', status: '已提交', progress: 100, lastSavedAt: '刚刚', abnormal: false },
        { id: 3, student: '陈同学', exam: '计算机程序设计上机考试', status: '异常', progress: 42, lastSavedAt: '9 分钟前', abnormal: true }
    ]
};

const mockStudentMistakes = {
    summary: {
        total: 18,
        unresolved: 11,
        repeated: 5,
        aiAnalyzed: 7
    },
    filters: {
        subjects: ['全部', '数据结构', '计算机程序设计', '数据库系统原理', '人工智能技术'],
        types: ['全部', '选择题', '填空题', '编程题'],
        mastery: ['全部', '待掌握', '已掌握']
    },
    mistakes: [
        {
            id: 'mistake-ds-stack-01',
            examId: 'exam-ds-midterm',
            examTitle: '数据结构期中综合考试',
            subject: '数据结构',
            questionType: '选择题',
            questionTitle: '递归函数调用时，系统通常使用哪种数据结构保存调用现场？',
            studentAnswer: '队列',
            correctAnswer: '栈',
            errorReason: '混淆了先进先出与后进先出的应用场景。',
            knowledgeTags: ['栈', '递归', '函数调用'],
            wrongCount: 3,
            lastWrongAt: '2026-06-24 20:16',
            mastered: false,
            aiAnalysis: null
        },
        {
            id: 'mistake-code-two-sum',
            examId: 'exam-code-final',
            examTitle: '计算机程序设计上机考试',
            subject: '计算机程序设计',
            questionType: '编程题',
            questionTitle: '两数之和',
            studentAnswer: '双层循环未提前返回，且返回值顺序不稳定。',
            correctAnswer: '使用哈希表记录已访问数字，O(n) 查找补数。',
            errorReason: '没有把“补数是否出现过”抽象成哈希查询，导致复杂度偏高。',
            knowledgeTags: ['哈希表', '数组', '复杂度'],
            wrongCount: 2,
            lastWrongAt: '2026-06-27 21:03',
            mastered: false,
            aiAnalysis: {
                diagnosis: '你已经能枚举数组，但还没有利用 target - nums[i] 这个补数关系。',
                concept: '哈希表适合把“是否出现过”从 O(n) 查找压缩到 O(1) 查询。',
                practice: '先重做两数之和，再做“存在重复元素”和“最长连续序列”的哈希题。',
                path: ['数组遍历', '哈希映射', '复杂度对比', '同类题迁移']
            }
        },
        {
            id: 'mistake-db-index-02',
            examId: 'exam-db-closed',
            examTitle: '数据库系统原理闭卷测验',
            subject: '数据库系统原理',
            questionType: '填空题',
            questionTitle: 'B+ 树索引中，所有数据记录指针通常存放在 ______ 节点。',
            studentAnswer: '根',
            correctAnswer: '叶子',
            errorReason: '对 B+ 树内部节点与叶子节点的职责区分不清。',
            knowledgeTags: ['B+ 树', '索引结构', '数据库存储'],
            wrongCount: 1,
            lastWrongAt: '2026-06-21 09:34',
            mastered: true,
            aiAnalysis: null
        }
    ]
};

const mockTeacherErrorAnalysis = {
    summary: {
        highRiskQuestions: 6,
        averageErrorRate: 37,
        affectedStudents: 42,
        generatedReviewTasks: 2
    },
    weakKnowledge: [
        { tag: '哈希表建模', errorRate: 64, questionCount: 4, suggestion: '用补数、频次统计、集合去重三个模型做对比讲解。' },
        { tag: '栈与递归', errorRate: 58, questionCount: 3, suggestion: '用函数调用栈动画复盘递归现场保存过程。' },
        { tag: 'B+ 树索引', errorRate: 46, questionCount: 2, suggestion: '对比 B 树与 B+ 树的数据存放位置。' }
    ],
    questionRanking: [
        {
            questionId: 'prog-two-sum',
            title: '两数之和',
            subject: '计算机程序设计',
            type: '编程题',
            errorRate: 72,
            wrongStudents: 35,
            totalStudents: 48,
            commonWrongAnswers: ['双层循环超时', '返回数值而非下标', '未处理重复数字'],
            knowledgeTags: ['哈希表', '数组', '复杂度'],
            aiSuggestion: '建议先讲“补数”关系，再用一张表演示 map 从空到命中答案的过程。'
        },
        {
            questionId: 'choice-stack-recursion',
            title: '递归调用现场保存结构',
            subject: '数据结构',
            type: '选择题',
            errorRate: 58,
            wrongStudents: 28,
            totalStudents: 48,
            commonWrongAnswers: ['队列', '堆'],
            knowledgeTags: ['栈', '递归'],
            aiSuggestion: '建议用一次阶乘递归展开过程让学生画出入栈和出栈顺序。'
        },
        {
            questionId: 'blank-bplus-leaf',
            title: 'B+ 树记录指针位置',
            subject: '数据库系统原理',
            type: '填空题',
            errorRate: 46,
            wrongStudents: 22,
            totalStudents: 48,
            commonWrongAnswers: ['根节点', '内部节点'],
            knowledgeTags: ['B+ 树', '索引'],
            aiSuggestion: '建议用“内部节点导航、叶子节点承载数据”这条规则组织讲评。'
        }
    ]
};

const mockWrongStudents = [
    { id: 'stu-01', name: '李同学', className: '计科 2301', answer: '双层循环超时', score: 12, status: '待订正' },
    { id: 'stu-02', name: '陈同学', className: '计科 2301', answer: '返回数值而非下标', score: 18, status: '已订正' },
    { id: 'stu-03', name: '王同学', className: '计科 2302', answer: '未处理重复数字', score: 20, status: '待订正' }
];

function buildMockAiAnalysis(mistakeId) {
    return {
        mistakeId,
        diagnosis: '这道题的错误集中在概念触发条件没有识别出来，导致选择了熟悉但不匹配的方法。',
        concept: '先判断题目真正考查的知识点，再选择对应结构或算法。不要只看题干中的表层名词。',
        practice: '建议完成 3 道同知识点变式题，并在每题后写一句“为什么用这个方法”。',
        path: ['复盘原题', '补齐概念', '同类题迁移', '24 小时后再测']
    };
}

function createTeacherMistakeTask(payload = {}) {
    const mistake = {
        id: `teacher-mistake-${Date.now()}`,
        examId: payload.recordId || 'teacher-analytics',
        examTitle: '教师端学情干预任务',
        subject: payload.subject || '数据结构',
        questionType: '错题订正',
        questionTitle: payload.title || '教师下发错题订正任务',
        studentAnswer: '待学生补写订正过程',
        correctAnswer: payload.desc || '请按照教师要求完成错因复盘、正确解法和同类迁移。',
        errorReason: payload.desc || '教师端检测到该知识点存在重复错误，需要完成一次结构化订正。',
        knowledgeTags: [payload.subject || '薄弱知识点', '教师下发', '待订正'],
        wrongCount: 1,
        lastWrongAt: new Date().toLocaleString('zh-CN'),
        mastered: false,
        aiAnalysis: null,
        source: {
            module: 'teacher-analytics',
            recordId: payload.recordId || null
        }
    };
    mockStudentMistakes.mistakes.unshift(mistake);
    mockStudentMistakes.summary.total += 1;
    mockStudentMistakes.summary.unresolved += 1;
    return mistake;
}

async function requestJson(path, options = {}, fallback) {
    const useMockFirst = localStorage.getItem('examMockFirst') === 'true';

    if (useMockFirst && fallback !== undefined) {
        return typeof fallback === 'function' ? await fallback() : fallback;
    }

    try {
        return await apiRequest(path, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
        });
    } catch (error) {
        console.info('[ExamCenter] Backend unavailable, using mock fallback:', path, error.message);
        if (fallback !== undefined) {
            return typeof fallback === 'function' ? await fallback(error) : fallback;
        }
        throw error;
    }
}

export const examCenterApi = {
    getStudentOverview(userId) {
        return requestJson(`/exams/student/${encodeURIComponent(userId)}/overview`, {}, mockStudentOverview);
    },
    getExamDetail(examId, userId) {
        return requestJson(`/exams/${encodeURIComponent(examId)}?user_id=${encodeURIComponent(userId)}`, {}, {
            ...mockExamDetail,
            id: examId
        });
    },
    startExamAttempt(examId, payload) {
        return requestJson(`/exams/${encodeURIComponent(examId)}/attempts`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, {
            attemptId: `attempt-${examId}-${Date.now()}`,
            startedAt: new Date().toISOString(),
            status: 'started'
        });
    },
    saveAnswer(attemptId, payload) {
        return requestJson(`/exams/attempts/${encodeURIComponent(attemptId)}/answers`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        }, {
            status: 'saved',
            savedAt: new Date().toISOString()
        });
    },
    submitAttempt(attemptId, payload) {
        return requestJson(`/exams/attempts/${encodeURIComponent(attemptId)}/submit`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, {
            status: 'submitted',
            submittedAt: new Date().toISOString(),
            objectiveScore: 8,
            programmingStatus: 'pending_judge'
        });
    },
    getTeacherDashboard() {
        return requestJson('/exams/teacher/dashboard', {}, mockTeacherDashboard);
    },
    createExam(payload) {
        return requestJson('/exams', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, {
            id: `exam-${Date.now()}`,
            ...payload,
            status: 'draft'
        });
    },
    createProgrammingProblem(examId, payload) {
        return requestJson(`/exams/${encodeURIComponent(examId)}/programming-problems`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, {
            id: `prog-${Date.now()}`,
            examId,
            ...payload
        });
    },
    getExamSubmissions(examId) {
        return requestJson(`/exams/${encodeURIComponent(examId)}/submissions`, {}, mockTeacherDashboard.submissions);
    },
    getStudentMistakes(userId) {
        return requestJson(`/exams/student/${encodeURIComponent(userId)}/mistakes`, {}, mockStudentMistakes);
    },
    requestMistakeAiAnalysis(mistakeId, payload = {}) {
        return requestJson(`/exams/mistakes/${encodeURIComponent(mistakeId)}/ai-analysis`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },
    updateMistake(mistakeId, payload) {
        return requestJson(`/exams/mistakes/${encodeURIComponent(mistakeId)}`, {
            method: 'PATCH',
            body: JSON.stringify(payload)
        }, {
            id: mistakeId,
            ...payload,
            updatedAt: new Date().toISOString()
        });
    },
    appendTeacherMistakeTask(payload) {
        return createTeacherMistakeTask(payload);
    },
    getTeacherErrorAnalysis(params = {}) {
        const query = new URLSearchParams(params).toString();
        return requestJson(`/exams/teacher/error-analysis${query ? `?${query}` : ''}`, {}, mockTeacherErrorAnalysis);
    },
    getWrongStudents(questionId) {
        return requestJson(`/exams/questions/${encodeURIComponent(questionId)}/wrong-students`, {}, mockWrongStudents);
    },
    createReviewTask(questionId, payload = {}) {
        return requestJson(`/exams/questions/${encodeURIComponent(questionId)}/review-task`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, {
            taskId: `review-${questionId}-${Date.now()}`,
            status: 'created',
            createdAt: new Date().toISOString()
        });
    },
    getStudentReviewTasks(userId) {
        return requestJson(`/exams/student/${encodeURIComponent(userId)}/review-tasks`, {}, { total: 0, tasks: [] });
    },
    updateExamStatus(examId, status) {
        return requestJson(`/exams/${encodeURIComponent(examId)}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ status })
        }, { examId, status, updatedAt: new Date().toISOString() });
    },
    judgeProgramming(attemptId, payload = {}) {
        return requestJson(`/exams/attempts/${encodeURIComponent(attemptId)}/judge-programming`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },
    getApiBase() {
        return API_BASE_URL;
    }
};
