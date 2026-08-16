import { ref, watch, onBeforeUnmount, getCurrentInstance } from 'vue';
import { radarOptionTemplate } from '../config/chartOptions.js';
import { analyticsApi } from '../api/analytics.js';

const SIX_DIM_INDICATORS = [
    { name: '规划一致性', max: 100 },
    { name: '代码质量与工程', max: 100 },
    { name: '理论逻辑完备度', max: 100 },
    { name: '学术论坛活跃度', max: 100 },
    { name: '专注度均值', max: 100 },
    { name: 'Checkpoint完成率', max: 100 }
];

const RADAR_DISPLAY_ORDER = [0, 1, 2, 3, 4, 5];

function normalizeRadarIndicators(indicators) {
    const source = Array.isArray(indicators) && indicators.length === 6
        ? indicators
        : SIX_DIM_INDICATORS;
    return RADAR_DISPLAY_ORDER.map((sourceIndex) => ({
        ...SIX_DIM_INDICATORS[sourceIndex],
        max: source[sourceIndex]?.max || SIX_DIM_INDICATORS[sourceIndex].max
    }));
}

function normalizeRadarValues(values, fallback) {
    const source = Array.isArray(values) && values.length === 6 ? values : fallback;
    return RADAR_DISPLAY_ORDER.map((sourceIndex) => {
        const value = Number(source[sourceIndex]);
        return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
    });
}

export function buildStudentRadarOption(studentValues, classValues, indicators) {
    const dims = normalizeRadarIndicators(indicators);
    const orderedStudentValues = normalizeRadarValues(studentValues, [50, 50, 50, 0, 50, 0]);
    const orderedClassValues = normalizeRadarValues(classValues, [60, 60, 60, 30, 65, 50]);
    return {
        ...radarOptionTemplate,
        legend: {
            data: ['您的当前学情', '全班平均表现'],
            bottom: 0,
            itemWidth: 14,
            itemHeight: 10,
            itemGap: 18,
            textStyle: { color: '#64748B' }
        },
        radar: {
            ...radarOptionTemplate.radar,
            center: ['50%', '44%'],
            radius: '58%',
            nameGap: 18,
            splitNumber: 4,
            indicator: dims
        },
        series: [{
            name: '能力维度对比',
            type: 'radar',
            symbol: 'circle',
            symbolSize: 7,
            data: [
                {
                    value: orderedStudentValues,
                    name: '您的当前学情',
                    areaStyle: { color: 'rgba(28, 43, 56, 0.18)' },
                    lineStyle: { width: 3, color: '#1c2b38' },
                    itemStyle: { borderWidth: 3, color: '#1c2b38' }
                },
                {
                    value: orderedClassValues,
                    name: '全班平均表现',
                    areaStyle: { color: 'rgba(59, 130, 246, 0.08)' },
                    lineStyle: { width: 2, color: '#3B82F6' },
                    itemStyle: { borderWidth: 2, color: '#3B82F6' }
                }
            ]
        }]
    };
}

export function useMonitor(currentRole, currentView, showToast, profile = null, currentUser = null) {
    const studentRadarOption = ref(JSON.parse(JSON.stringify(radarOptionTemplate)));
    const activeTaskReasonId = ref(null);
    const radarLoading = ref(false);
    const myRadarEvidence = ref({});

    const loadMyRadar = async () => {
        const username = currentUser?.value?.username;
        if (!username) return;
        radarLoading.value = true;
        try {
            const data = await analyticsApi.getMyRadar(username);
            const indicators = data.radarIndicators || SIX_DIM_INDICATORS;
            const values = Array.isArray(data.radarValues) && data.radarValues.length === 6
                ? data.radarValues
                : [50, 50, 50, 0, 50, 0];
            const classValues = Array.isArray(data.classRadarValues) && data.classRadarValues.length === 6
                ? data.classRadarValues
                : [60, 60, 60, 30, 65, 50];
            myRadarEvidence.value = data.radarEvidence || {};
            studentRadarOption.value = buildStudentRadarOption(values, classValues, indicators);
        } catch (err) {
            console.warn('[useMonitor] 同源雷达加载失败，保留当前图:', err);
        } finally {
            radarLoading.value = false;
        }
    };

    // 登录用户变化时拉取同源六维
    if (currentUser) {
        watch(
            () => currentUser.value?.username,
            (username) => {
                if (username) loadMyRadar();
            },
            { immediate: true }
        );
    }

    // profile 变化时也尝试刷新（作业诊断回写后画像可能更新）
    if (profile) {
        watch(profile, () => {
            if (currentUser?.value?.username) loadMyRadar();
        }, { deep: true });
    }

    const agentLogs = ref([
        { agent: 'Alina', role: '首席规划师', icon: 'ph-map-trifold', time: '10:24:15', content: '已根据用户目标「手写Vue3响应式系统」自动拆解出 3 项子任务并推送至学习网络。' },
        { agent: 'Prof. X', role: '知识讲授导师', icon: 'ph-graduation-cap', time: '10:25:30', content: '已检索到关联知识节点「核心原理深度解析」，准备生成学习图谱。' },
        { agent: 'Mira', role: 'AI引导图生成师', icon: 'ph-flow-arrow', time: '10:26:10', content: '已将当前学习问题转译为概念图草图，等待学生继续追问。' },
        { agent: 'CodeNinja', role: '代码演示助手', icon: 'ph-code', time: '10:27:00', content: '检测到任务「手写基础Proxy拦截器」，已准备响应式代码库测试用例。' }
    ]);

    const _onAgentLog = (e) => {
        const icons = {
            'Alina': 'ph-map-trifold',
            'Prof. X': 'ph-graduation-cap',
            'DataBot': 'ph-magnifying-glass',
            'CodeNinja': 'ph-code',
            'Mira': 'ph-flow-arrow'
        };
        const roles = {
            'Alina': '首席规划师',
            'Prof. X': '知识讲授导师',
            'DataBot': '数据检索助手',
            'CodeNinja': '代码演示助手',
            'Mira': 'AI引导图生成师'
        };
        agentLogs.value.unshift({
            agent: e.detail.agent,
            role: roles[e.detail.agent] || '协同智能体',
            icon: icons[e.detail.agent] || 'ph-robot',
            time: e.detail.time,
            content: e.detail.content
        });
        if (agentLogs.value.length > 25) {
            agentLogs.value.pop();
        }
    };

    const _onRadarRefresh = () => {
        loadMyRadar();
    };

    if (typeof window !== 'undefined') {
        window.addEventListener('agent-log', _onAgentLog);
        window.addEventListener('interaction-completed', _onRadarRefresh);
        window.addEventListener('homework-submitted', _onRadarRefresh);
        window.addEventListener('radar-refresh', _onRadarRefresh);
    }

    if (getCurrentInstance()) {
        onBeforeUnmount(() => {
            if (typeof window !== 'undefined') {
                window.removeEventListener('agent-log', _onAgentLog);
                window.removeEventListener('interaction-completed', _onRadarRefresh);
                window.removeEventListener('homework-submitted', _onRadarRefresh);
                window.removeEventListener('radar-refresh', _onRadarRefresh);
            }
        });
    }

    const toggleTaskReason = (id) => {
        activeTaskReasonId.value = activeTaskReasonId.value === id ? null : id;
    };

    return {
        studentRadarOption,
        activeTaskReasonId,
        agentLogs,
        radarLoading,
        myRadarEvidence,
        loadMyRadar,
        toggleTaskReason
    };
}
