/**
 * useDashboard.js
 * 仪表盘真实数据 Hook
 *
 * 通过调用后端 /api/dashboard/student/{userId} 聚合端点，
 * 一次性获取仪表盘所需的全部动态数据，替换 main.js 中的硬编码静态数据。
 *
 * 返回值与 main.js 原有模板绑定字段完全兼容，无需修改 HTML 模板。
 */
import { ref, computed, watch, onBeforeUnmount, getCurrentInstance } from 'vue';
import { apiRequest } from '../utils/request.js';
import { analyticsApi } from '../api/analytics.js';

// ─── 工具函数 ───────────────────────────────────────────────

/** 将 ISO 考试时间格式化为仪表盘展示用短日期 */
function formatExamAlertDate(isoStr) {
    if (!isoStr) return '';
    const text = String(isoStr).trim();
    if (/^\d{1,2}月\d{1,2}日/.test(text)) return text;
    const d = new Date(text);
    if (Number.isNaN(d.getTime())) return text;
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${d.getMonth() + 1}月${d.getDate()}日 ${hh}:${mm}`;
}

// ─── Hook 主体 ──────────────────────────────────────────────

export function useDashboard(currentUser) {
    // ---------- 响应式状态 ----------
    const dashboardLoading = ref(false);
    const dashboardError = ref(null);

    // 作业相关
    const homeworkList = ref([]);       // 仪表盘作业卡片列表
    const deadlines = ref([]);          // 各科目截止时间面板
    const pendingHomeworkCount = computed(() =>
        homeworkList.value.filter(h => !h.submitted).length
    );
    const submittedHomeworkCount = computed(() =>
        homeworkList.value.filter(h => h.submitted).length
    );

    // 考试通知
    const examAlerts = ref([]);

    // 错题相关
    const errorNotebook = ref([]);      // 最近 5 条错题复盘
    const errorPoints = ref([]);        // 未掌握高频易错点
    const mistakeSummary = ref({        // 错题统计概要
        total: 0,
        unresolved: 0,
        repeated: 0,
        aiAnalyzed: 0,
    });

    // 干预任务和 nudge
    const interventions = ref([]);
    const nudges = ref([]);

    // 补发提醒通知
    const notifications = ref([]);

    // 教师下发的 interaction 任务（补弱作业、短测、错题订正等）
    const interactions = ref([]);

    // ---------- 辅助计算 ----------

    /** 当前登录用户名 */
    const _username = computed(() => currentUser?.value?.username || '');

    // ---------- 核心加载函数 ----------

    /**
     * 调用后端聚合端点，一次性刷新全部仪表盘数据
     */
    const refreshDashboard = async () => {
        const username = _username.value;
        if (!username) return;

        dashboardLoading.value = true;
        dashboardError.value = null;

        try {
            const data = await apiRequest(`/dashboard/student/${encodeURIComponent(username)}`);

            // ── 作业数据 ──
            if (Array.isArray(data.homeworkList)) {
                homeworkList.value = data.homeworkList;
            }
            if (Array.isArray(data.deadlines)) {
                deadlines.value = data.deadlines;
            }

            // ── 考试通知（后端返回 ISO，前端格式化显示） ──
            if (Array.isArray(data.examAlerts)) {
                examAlerts.value = data.examAlerts.map((exam) => ({
                    ...exam,
                    date: formatExamAlertDate(exam.date),
                }));
            }

            // ── 错题数据 ──
            if (Array.isArray(data.errorNotebook)) {
                errorNotebook.value = data.errorNotebook;
            }
            if (Array.isArray(data.errorPoints)) {
                errorPoints.value = data.errorPoints;
            }
            if (data.mistakeSummary) {
                mistakeSummary.value = data.mistakeSummary;
            }

            // ── 干预任务和 nudge ──
            if (Array.isArray(data.interventions)) {
                interventions.value = data.interventions;
            }
            if (Array.isArray(data.nudges)) {
                nudges.value = data.nudges;
            }

            // ── 补发提醒通知 ──
            if (Array.isArray(data.notifications)) {
                notifications.value = data.notifications;
            }

        } catch (err) {
            console.error('[useDashboard] 仪表盘数据加载失败:', err);
            dashboardError.value = err?.message || '数据加载失败，请稍后重试';
        } finally {
            dashboardLoading.value = false;
        }

        // ── 教师下发的 interaction 任务（独立端点，后台加载，不阻塞 loading） ──
        try {
            const interactionData = await analyticsApi.getStudentInteractions(username);
            if (Array.isArray(interactionData?.interactions)) {
                interactions.value = interactionData.interactions;
            } else if (Array.isArray(interactionData)) {
                interactions.value = interactionData;
            }
        } catch (err) {
            console.warn('[useDashboard] interaction 任务加载失败（非致命）:', err);
        }
    };

    // ---------- 局部刷新函数 ----------

    /**
     * 提交作业后，同步更新仪表盘中对应作业的状态
     * @param {string} homeworkId
     */
    const markHomeworkSubmitted = (homeworkId) => {
        const hw = homeworkList.value.find(h => h.id === homeworkId);
        if (hw) {
            hw.submitted = true;
            hw.status = 'submitted';
        }
        // 同时清除该科目的 deadlines 紧急标记
        const subjectId = hw?.subjectId;
        if (subjectId) {
            const dl = deadlines.value.find(d => d.subjectId === subjectId);
            if (dl) dl.urgent = false;
        }
    };

    /**
     * 教师端干预下发后，实时追加到仪表盘（无需等待后端刷新）
     * 兼容 main.js 中 handleTeacherIntervention 的直接调用
     */
    const appendTeacherIntervention = ({ type, title, subject, deadline, desc, subjectId } = {}) => {
        const now = new Date();
        const id = `teacher-${Date.now()}`;

        // 追加到作业列表（homework / quiz 类型）
        if (type === 'homework' || type === 'quiz') {
            homeworkList.value.unshift({
                id,
                title: title || '教师下发任务',
                subject: subject || '',
                subjectId: subjectId || 'GENERAL',
                deadline: deadline || '',
                urgent: true,
                submitted: false,
                status: 'unsubmitted',
                type: type === 'quiz' ? 'quiz' : 'daily',
            });
            deadlines.value.unshift({
                subject: subject || '',
                subjectId: subjectId || 'GENERAL',
                date: deadline || '',
                remaining: type === 'quiz' ? '短测待完成' : '剩余 12 小时',
                urgent: true,
                color: '#ef4444',
            });
        }

        // 追加到考试通知
        examAlerts.value.unshift({
            id,
            name: type === 'mistake' ? `【错题订正】${title}` : `【教师下发】${title}`,
            subject: subject || '',
            date: deadline || '',
            note: desc || '',
            status: 'active',
        });

        // 如果是错题类型，追加到错题本
        if (type === 'mistake') {
            errorNotebook.value.unshift({
                id,
                subject: subject || '',
                date: `${now.getMonth() + 1}-${String(now.getDate()).padStart(2, '0')}`,
                question: title || '',
                mastered: false,
                wrongCount: 1,
            });
            // 同步更新错题统计
            mistakeSummary.value.total = (mistakeSummary.value.total || 0) + 1;
            mistakeSummary.value.unresolved = (mistakeSummary.value.unresolved || 0) + 1;
        }
    };

    // ---------- 向后端持久化教师干预 ----------

    /**
     * 教师端下发干预任务并持久化到数据库
     * @param {object} interventionPayload
     * @returns {Promise<object>} 后端返回的干预记录
     */
    const createTeacherIntervention = async (interventionPayload) => {
        try {
            const result = await apiRequest('/dashboard/teacher/intervention', {
                method: 'POST',
                body: JSON.stringify(interventionPayload),
            });
            return result;
        } catch (err) {
            console.error('[useDashboard] 教师干预下发失败:', err);
            throw err;
        }
    };

    // ---------- 学生标记交互任务完成 ----------

    /**
     * 学生完成教师下发的交互任务后，调用后端标记完成并刷新仪表盘
     * @param {string} recordId - interaction 记录 ID
     * @param {object} extra - 额外提交的数据（如 result）
     */
    const completeInteractionTask = async (recordId, extra = {}) => {
        const username = _username.value;
        if (!recordId || !username) return;
        try {
            // 先尝试作为 interaction 完成；若是纯 nudge id，后端 404 时本地消掉即可
            try {
                await analyticsApi.markInteractionComplete(recordId, {
                    userId: username,
                    ...extra,
                });
            } catch (err) {
                const isNudgeOnly = nudges.value.some(item => item.id === recordId);
                if (!isNudgeOnly) throw err;
            }
            // 本地先更新状态，避免等待刷新
            interactions.value = interactions.value.map(item =>
                item.id === recordId ? { ...item, status: 'completed' } : item
            );
            nudges.value = nudges.value.filter(item =>
                item.id !== recordId && item.interactionId !== recordId
            );
            // 触发事件，由事件监听器统一刷新仪表盘与同源雷达
            window.dispatchEvent(new CustomEvent('interaction-completed', {
                detail: { recordId, userId: username },
            }));
            window.dispatchEvent(new CustomEvent('radar-refresh', {
                detail: { reason: 'interaction-completed', recordId },
            }));
        } catch (err) {
            console.error('[useDashboard] 标记交互任务完成失败:', err);
        }
    };

    // ---------- 自动监听用户登录变化 ----------

    // 当用户登录状态变化（username 从空变为有值）时，自动触发加载
    watch(
        () => _username.value,
        (newUsername, oldUsername) => {
            if (newUsername && newUsername !== oldUsername) {
                refreshDashboard();
            }
        },
        { immediate: false }
    );

    // ---------- 事件总线监听 ----------
    // 提取具名函数以便 onBeforeUnmount 时移除
    const _onHomeworkSubmitted = (e) => {
        const homeworkId = e?.detail?.homeworkId;
        if (homeworkId) markHomeworkSubmitted(homeworkId);
    };
    const _onInteractionCompleted = () => {
        refreshDashboard();
    };
    const _onMistakeMastered = (e) => {
        const { mistakeId, mastered } = e?.detail || {};
        const nb = errorNotebook.value.find(n => n.id === mistakeId);
        if (nb) nb.mastered = mastered;
        const ep = errorPoints.value.find(p => p.id === mistakeId);
        if (ep) {
            if (mastered) {
                errorPoints.value = errorPoints.value.filter(p => p.id !== mistakeId);
            }
        }
        mistakeSummary.value = {
            ...mistakeSummary.value,
            unresolved: errorNotebook.value.filter(n => !n.mastered).length,
            total: errorNotebook.value.length,
            repeated: errorNotebook.value.filter(n => (n.wrongCount || 0) > 1).length,
        };
    };

    // 监听 token 失效事件（request.js 在 401 时派发），清空登录态并通知主应用登出
    const _onAuthExpired = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('currentUser');
        window.dispatchEvent(new CustomEvent('force-logout'));
    };

    if (typeof window !== 'undefined') {
        window.addEventListener('homework-submitted', _onHomeworkSubmitted);
        window.addEventListener('interaction-completed', _onInteractionCompleted);
        window.addEventListener('mistake-mastered-changed', _onMistakeMastered);
        window.addEventListener('auth-expired', _onAuthExpired);
    }

    // 组件卸载时移除事件监听器，防止内存泄漏和重复执行
    if (getCurrentInstance()) {
        onBeforeUnmount(() => {
            if (typeof window !== 'undefined') {
                window.removeEventListener('homework-submitted', _onHomeworkSubmitted);
                window.removeEventListener('interaction-completed', _onInteractionCompleted);
                window.removeEventListener('mistake-mastered-changed', _onMistakeMastered);
                window.removeEventListener('auth-expired', _onAuthExpired);
            }
        });
    }

    // ---------- 返回 ----------
    return {
        // 响应式数据
        dashboardLoading,
        dashboardError,
        homeworkList,
        deadlines,
        pendingHomeworkCount,
        submittedHomeworkCount,
        examAlerts,
        errorNotebook,
        errorPoints,
        mistakeSummary,
        interventions,
        nudges,
        notifications,
        interactions,
        // 操作函数
        refreshDashboard,
        markHomeworkSubmitted,
        appendTeacherIntervention,
        createTeacherIntervention,
        completeInteractionTask,
    };
}
