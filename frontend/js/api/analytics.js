import { mockStudents, mockAnalyticsData } from '../data/mockData.js';
import { apiRequest } from '../utils/request.js';

// 获取主页面挂载的 examAlerts、homeworkList、errorNotebook 来完成干预操作的闭环
// 这里的 examAlerts、homeworkList、errorNotebook 是 Vue 主实例中的响应式状态
// 我们需要在干预任务下发时，能够操作主实例里的这部分数据
// 我们可以在 localStorage 或者直接在 window 对象、或者通过事件总线进行事件派发
// 这里我们最简单又极其可靠的闭环方式是：在 API 中修改 localStorage 并抛出自定义事件，
// 然后由主实例（main.js）或相应的学生端组件监听事件并更新对应的数组状态！
// 或者更直观地，我们在 window 上注册共享变量，在初始化时将 ref 挂上去。
// 让我们在 API 里支持直接抛出系统事件，同时在 API 响应式地修改共享的对象。

async function requestJson(path, options = {}, mockFn) {
    const useMockFirst = localStorage.getItem('analyticsMockFirst') === 'true';

    if (useMockFirst && typeof mockFn === 'function') {
        return await mockFn();
    }

    try {
        return await apiRequest(path, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
        });
    } catch (error) {
        if (typeof mockFn === 'function') {
            return await mockFn(error);
        }
        throw error;
    }
}

function buildInteractionRecord(payload) {
    const id = payload.id || `ir-${Date.now()}`;
    const targetLabel = payload.target?.label || payload.targetLabel || payload.target || '全班';
    const initialCount = payload.target?.studentIds?.length || (targetLabel.includes('全班') ? 48 : 1);
    return {
        id,
        type: payload.type,
        title: payload.title || payload.topic || '学情干预任务',
        targetLabel,
        completionRate: payload.completionRate ?? 0,
        unreadCount: payload.unreadCount ?? initialCount,
        pendingCount: payload.pendingCount ?? initialCount,
        completedCount: payload.completedCount ?? 0,
        createdAt: payload.createdAt || new Date().toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        }),
        status: payload.status || 'running',
        nextAction: payload.nextAction || '追踪学生响应并按需补发提醒'
    };
}

function broadcastStudentInteraction(record, payload) {
    if (!window.dispatchEvent) return;
    window.dispatchEvent(new CustomEvent('teacher-intervention-broadcast', {
        detail: {
            type: record.type,
            topic: record.title,
            target: payload.target || { scope: 'class', label: record.targetLabel },
            payload: payload.payload || {},
            recordId: record.id
        }
    }));
}

export const analyticsApi = {
    // 获取全局班级学情大盘指标
    getOverviewStats() {
        return requestJson('/analytics/overview', {}, () => {
            return mockAnalyticsData.value;
        });
    },

    // 获取班级学生学情画像列表
    getStudentList() {
        return requestJson('/analytics/students', {}, () => {
            // 给 mockStudents 追加一些额外的多维画像数值，使卡片内容更高级
            return mockStudents.value.map(student => {
                let errorCount = 4;
                let forumCount = 2;
                if (student.id === 1) { errorCount = 3; forumCount = 5; }
                else if (student.id === 2) { errorCount = 1; forumCount = 8; }
                else if (student.id === 3) { errorCount = 8; forumCount = 3; }
                else if (student.id === 4) { errorCount = 5; forumCount = 0; }
                else if (student.id === 5) { errorCount = 2; forumCount = 12; }
                else if (student.id === 6) { errorCount = 7; forumCount = 1; }

                // 顺序对齐后端 RADAR_INDICATORS：规划/代码/理论/论坛/专注/Checkpoint
                const planning = student.progress;
                const codeQuality = student.focus || 60;
                const theory = 70 + (student.id % 3) * 10;
                const forum = Math.min(100, forumCount * 10);
                const focus = Math.max(0, 80 - errorCount * 5);
                const checkpoint = Math.min(100, student.progress + 10);

                return {
                    ...student,
                    errorCount,
                    forumCount,
                    activeRate: student.status === 'offline' ? 0 : (100 - student.id * 8),
                    radarValues: [planning, codeQuality, theory, forum, focus, checkpoint],
                    radarEvidence: {
                        '规划一致性': { label: `Mock进度 ${planning}`, sampleCount: 0 },
                        '代码质量与工程': { label: `Mock专注 ${codeQuality}`, sampleCount: 0 },
                        '理论逻辑完备度': { label: `Mock理论 ${theory}`, sampleCount: 0 },
                        '学术论坛活跃度': { label: `发帖折算 ${forum}`, sampleCount: forumCount },
                        '专注度均值': { label: `错题代理 ${focus}`, sampleCount: errorCount },
                        'Checkpoint完成率': { label: `Mock完成率 ${checkpoint}`, sampleCount: 0 }
                    }
                };
            });
        });
    },

    // 按姓名 / 学号搜索班级学生画像
    searchStudents(query) {
        const q = String(query || '').trim();
        return requestJson(`/analytics/students/search?q=${encodeURIComponent(q)}`, {}, () => {
            const keyword = q.toLowerCase();
            if (!keyword) {
                return { query: q, matches: [], total: 0, bestMatch: null };
            }
            const scored = mockStudents.value
                .map(student => {
                    const name = String(student.name || '').toLowerCase();
                    const username = String(student.username || student.userId || '').toLowerCase();
                    let score = -1;
                    if (keyword === name || keyword === username) score = 0;
                    else if (name.startsWith(keyword) || username.startsWith(keyword)) score = 1;
                    else if (name.includes(keyword) || username.includes(keyword)) score = 2;
                    return score < 0 ? null : { score, student };
                })
                .filter(Boolean)
                .sort((a, b) => a.score - b.score || String(a.student.name).localeCompare(String(b.student.name), 'zh'));
            const matches = scored.map(item => item.student);
            return { query: q, matches, total: matches.length, bestMatch: matches[0] || null };
        });
    },

    // 获取单个学生的能力维度详情与错题明细
    getStudentDetails(studentId) {
        return requestJson(`/analytics/students/${studentId}`, {}, () => {
            const student = mockStudents.value.find(s => s.id === studentId);
            if (!student) throw new Error('学生不存在');

            // 根据学生 ID Mock 不同的错题本数据
            let errors = [];
            if (studentId === 3 || studentId === 6) { // 卡点预警学生
                errors = [
                    { id: 'err-1', topic: '平衡二叉树 AVL 旋转失衡指针空悬', severity: 'high', count: 3, date: '昨天' },
                    { id: 'err-2', topic: '单链表反转 curr.next 备份丢失导致断裂', severity: 'medium', count: 2, date: '3天前' },
                    { id: 'err-3', topic: '中缀表达式求值栈运算操作符优先级混乱', severity: 'low', count: 1, date: '10-24' }
                ];
            } else {
                errors = [
                    { id: 'err-1', topic: '二分查找中 left 与 right 越界死循环', severity: 'medium', count: 1, date: '10-22' },
                    { id: 'err-2', topic: '定点数补码加减法符号位溢出判断错误', severity: 'low', count: 1, date: '10-18' }
                ];
            }

            const planning = student.progress;
            const codeQuality = student.focus || 60;
            const theory = 75;
            const forum = Math.min(100, student.id * 15);
            const focus = 85;
            const checkpoint = Math.min(100, student.progress + 8);

            return {
                studentId: student.id,
                username: student.username || student.userId,
                name: student.name,
                progress: student.progress,
                focus: student.focus,
                goal: student.goal,
                agentName: student.currentAgent,
                errors: errors,
                radarValues: [planning, codeQuality, theory, forum, focus, checkpoint],
                radarEvidence: {
                    '规划一致性': { label: `Mock进度 ${planning}`, sampleCount: 0 },
                    '代码质量与工程': { label: `Mock专注 ${codeQuality}`, sampleCount: 0 },
                    '理论逻辑完备度': { label: `Mock理论 ${theory}`, sampleCount: 0 },
                    '学术论坛活跃度': { label: `Mock论坛 ${forum}`, sampleCount: 0 },
                    '专注度均值': { label: `Mock专注 ${focus}`, sampleCount: 0 },
                    'Checkpoint完成率': { label: `Mock完成率 ${checkpoint}`, sampleCount: 0 }
                },
                timeline: [
                    { label: '作业提交', value: student.progress >= 60 ? '节奏稳定' : '低于班级均值', tone: student.progress >= 60 ? 'good' : 'risk' },
                    { label: '错题新增', value: `${errors.length} 个卡点`, tone: errors.length > 2 ? 'risk' : 'normal' },
                    { label: 'AI 会诊', value: student.currentAgent || 'Alina', tone: 'good' },
                    { label: '教师干预', value: student.alert ? '待跟进' : '暂无异常', tone: student.alert ? 'risk' : 'good' }
                ]
            };
        });
    },

    // 学生端同源六维雷达
    getMyRadar(userId) {
        return requestJson(`/analytics/students/me?user_id=${encodeURIComponent(userId || '')}`, {}, () => {
            const indicators = [
                { name: '规划一致性', max: 100 },
                { name: '代码质量与工程', max: 100 },
                { name: '理论逻辑完备度', max: 100 },
                { name: '学术论坛活跃度', max: 100 },
                { name: '专注度均值', max: 100 },
                { name: 'Checkpoint完成率', max: 100 }
            ];
            return {
                studentId: userId,
                name: userId,
                radarIndicators: indicators,
                radarValues: [60, 55, 58, 20, 65, 40],
                classRadarValues: [68, 62, 70, 35, 72, 55],
                radarEvidence: {},
                progress: 60,
                focus: 65,
                goal: ''
            };
        });
    },

    // 提醒督学干预
    sendNudgeMessage(studentId, message) {
        return requestJson(`/analytics/students/${studentId}/nudge`, {
            method: 'POST',
            body: JSON.stringify({ message })
        }, () => {
            const student = mockStudents.value.find(s => s.id === studentId);
            if (student) {
                // 如果专注度太低，督学提醒后可以稍微回升
                if (student.focus < 50) {
                    student.focus = Math.min(100, student.focus + 25);
                    student.alert = false;
                }
            }
            return { success: true, nudgedAt: new Date().toLocaleTimeString() };
        });
    },

    // 获取 AI 干预决策建议
    getAiInterventionAdvices() {
        return requestJson('/analytics/advices', {}, () => {
            return mockAnalyticsData.value.aiAdvices;
        });
    },

    // 获取教师端今日行动队列。后端接入时返回数组即可。
    getActionQueue() {
        return requestJson('/analytics/action-queue', {}, () => {
            return mockAnalyticsData.value.actionQueue || [];
        });
    },

    // 获取师生交互闭环记录。后端可从 interaction_records 表聚合返回。
    getInteractionRecords() {
        return requestJson('/analytics/interactions', {}, () => {
            return mockAnalyticsData.value.interactionRecords || [];
        });
    },

    // 创建教师到学生端的非直播交互任务。
    async dispatchStudentInteraction(payload) {
        const result = await requestJson('/analytics/interactions', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const record = buildInteractionRecord(payload);
            if (!mockAnalyticsData.value.interactionRecords) {
                mockAnalyticsData.value.interactionRecords = [];
            }
            mockAnalyticsData.value.interactionRecords.unshift(record);

            if (payload.source?.adviceId) {
                const advice = mockAnalyticsData.value.aiAdvices.find(item => item.id === payload.source.adviceId);
                if (advice) advice.active = false;
            }

            return { success: true, record };
        });
        if (result?.record) {
            broadcastStudentInteraction(result.record, payload);
        }
        return result;
    },

    // 更新交互记录状态，后端可用于已读、完成率、关闭等更新。
    updateInteractionRecord(recordId, patch) {
        return requestJson(`/analytics/interactions/${encodeURIComponent(recordId)}`, {
            method: 'PATCH',
            body: JSON.stringify(patch)
        }, () => {
            const record = mockAnalyticsData.value.interactionRecords?.find(item => item.id === recordId);
            if (record) Object.assign(record, patch);
            return { success: true, record };
        });
    },

    // 教师执行一键干预任务分发
    dispatchInterventionTask(payload) {
        return requestJson('/analytics/dispatch', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const { type, topic, targetId } = payload;
            const interactionPayload = {
                type,
                title: topic,
                target: payload.target || { scope: 'class', label: '全班' },
                source: { module: 'teacher-analytics', weakPointId: targetId },
                payload: payload.payload || {}
            };
            const record = buildInteractionRecord(interactionPayload);
            
            // 为了达成双向交互闭环，当教师发布干预任务后，抛出全局自定义事件
            // main.js 可以截获此事件，并更新对应的全局 Vue ref（如 examAlerts、homeworkList、errorNotebook）
            // 这样能够保证只要教师端一点击，学生端就能立刻看到结果！
            if (!mockAnalyticsData.value.interactionRecords) {
                mockAnalyticsData.value.interactionRecords = [];
            }
            mockAnalyticsData.value.interactionRecords.unshift(record);
            broadcastStudentInteraction(record, interactionPayload);

            // 修改 mock 数据源中建议状态
            if (targetId) {
                const adv = mockAnalyticsData.value.aiAdvices.find(a => a.id === targetId);
                if (adv) {
                    adv.active = false; // 标记为已处理
                }
            }

            return { success: true, dispatchedAt: new Date().toISOString() };
        });
    },

    // 学生标记交互任务完成
    markInteractionComplete(recordId, payload = {}) {
        return requestJson(`/analytics/interactions/${encodeURIComponent(recordId)}/complete`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => ({ success: true, record: { id: recordId, status: 'completed', ...payload } }));
    },

    // AI 生成干预建议
    generateAdvices() {
        return requestJson('/analytics/advices/generate', {
            method: 'POST',
            body: JSON.stringify({})
        });
    },

    // 自动生成行动队列
    generateActionQueue() {
        return requestJson('/analytics/action-queue/generate', {
            method: 'POST',
            body: JSON.stringify({})
        });
    },

    // 获取学生端交互任务
    getStudentInteractions(userId) {
        return requestJson(`/dashboard/student/${encodeURIComponent(userId)}/interactions`, {}, {
            interventions: [],
            nudges: [],
            interactions: []
        });
    }
};
