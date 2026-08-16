import { ref, computed, onMounted } from 'vue';
import { examCenterApi } from '../api/examCenter.js';
import { formatDisplayDateTime } from '../utils/timeFormat.js';

export default {
    name: 'StudentMistakeBook',
    props: {
        currentUser: { type: Object, default: null },
        mistakeAgentConfig: { type: Object, default: null }
    },
    emits: ['show-toast'],
    setup(props, { emit }) {
        const loading = ref(true);
        const mistakesData = ref({
            summary: { total: 0, unresolved: 0, repeated: 0, aiAnalyzed: 0 },
            filters: { subjects: ['全部'], types: ['全部'], mastery: ['全部'] },
            mistakes: []
        });
        const reviewTasks = ref([]);
        const filters = ref({ subject: '全部', type: '全部', mastery: '全部' });
        const activeMistakeId = ref(null);
        const analyzingMistakeId = ref(null);

        const username = computed(() => props.currentUser?.username || 'guest_user');
        const apiBase = computed(() => examCenterApi.getApiBase());
        const mistakeAgent = computed(() => props.mistakeAgentConfig || {
            id: 'agent_mistake_analyst',
            name: '错题分析师',
            model: 'qwen3.7-plus',
            prompt: ''
        });

        const filteredMistakes = computed(() => {
            return mistakesData.value.mistakes.filter(item => {
                const subjectOk = filters.value.subject === '全部' || item.subject === filters.value.subject;
                const typeOk = filters.value.type === '全部' || item.questionType === filters.value.type;
                const masteryOk =
                    filters.value.mastery === '全部' ||
                    (filters.value.mastery === '已掌握' ? item.mastered : !item.mastered);
                return subjectOk && typeOk && masteryOk;
            });
        });

        const activeMistake = computed(() => (
            filteredMistakes.value.find(item => item.id === activeMistakeId.value) ||
            filteredMistakes.value[0] ||
            null
        ));

        const loadMistakes = async () => {
            loading.value = true;
            const [mistakesResult, tasksResult] = await Promise.all([
                examCenterApi.getStudentMistakes(username.value),
                examCenterApi.getStudentReviewTasks(username.value).catch(() => ({ total: 0, tasks: [] }))
            ]);
            mistakesData.value = mistakesResult;
            reviewTasks.value = tasksResult?.tasks || [];
            if (!activeMistakeId.value && mistakesData.value.mistakes?.length) {
                activeMistakeId.value = mistakesData.value.mistakes[0].id;
            }
            loading.value = false;
        };

        const requestAiAnalysis = async (mistake) => {
            if (!mistake || analyzingMistakeId.value) return;
            analyzingMistakeId.value = mistake.id;
            try {
                const result = await examCenterApi.requestMistakeAiAnalysis(mistake.id, {
                    userId: username.value,
                    agentId: mistakeAgent.value.id,
                    agentName: mistakeAgent.value.name,
                    agentModel: mistakeAgent.value.model,
                    agentPrompt: mistakeAgent.value.prompt,
                    questionTitle: mistake.questionTitle,
                    studentAnswer: mistake.studentAnswer,
                    correctAnswer: mistake.correctAnswer
                });
                mistake.aiAnalysis = result;
                emit('show-toast', 'AI 错因分析已生成', 'success');
            } catch (error) {
                emit('show-toast', `AI 错题分析失败：${error?.message || '后端服务暂不可用'}`, 'error');
            } finally {
                analyzingMistakeId.value = null;
            }
        };

        const formatAiPath = (path) => {
            if (Array.isArray(path)) {
                return path.filter(Boolean).join(' → ');
            }
            return String(path || '').trim() || '复盘原题 → 补齐概念 → 同类练习 → 隔天重测';
        };

        const toggleMistakeMastered = async (mistake) => {
            if (!mistake) return;
            const oldValue = mistake.mastered;
            mistake.mastered = !mistake.mastered; // 乐观更新
            try {
                await examCenterApi.updateMistake(mistake.id, {
                    mastered: mistake.mastered,
                    userId: username.value
                });
                if (typeof window !== 'undefined') {
                    window.dispatchEvent(new CustomEvent('mistake-mastered-changed', {
                        detail: { mistakeId: mistake.id, mastered: mistake.mastered }
                    }));
                }
                emit('show-toast', mistake.mastered ? '已标记为掌握' : '已恢复为待掌握', 'success');
            } catch (err) {
                mistake.mastered = oldValue; // 回滚
                emit('show-toast', `操作失败：${err.message}`, 'error');
            }
        };

        onMounted(loadMistakes);

        return {
            loading,
            mistakesData,
            reviewTasks,
            filters,
            activeMistakeId,
            activeMistake,
            filteredMistakes,
            analyzingMistakeId,
            username,
            apiBase,
            mistakeAgent,
            loadMistakes,
            requestAiAnalysis,
            formatAiPath,
            formatDisplayDateTime,
            toggleMistakeMastered
        };
    },
    template: `
        <section class="absolute inset-0 overflow-y-auto p-8 lg:p-10 bg-slate-50">
            <div class="max-w-7xl mx-auto flex flex-col gap-6">
                <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-3 mb-2">
                            <div class="w-11 h-11 rounded-2xl bg-[#1c2b38] text-white flex items-center justify-center">
                                <i class="ph ph-warning-diamond text-xl"></i>
                            </div>
                            <div>
                                <h2 class="text-2xl font-bold text-slate-900" style="font-family: 'Noto Serif SC', serif;">错题本</h2>
                                <p class="text-sm text-slate-500 mt-1">汇总每次测试的错题、错误原因与 AI 复习建议。</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div v-if="loading" class="glass-panel-liquid p-8 text-sm text-slate-500">正在加载错题记录...</div>

                <template v-else>
                    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                            <p class="text-xs text-slate-500">错题总量</p>
                            <p class="text-3xl font-bold text-slate-900 mt-2">{{ mistakesData.summary.total }}</p>
                        </div>
                        <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                            <p class="text-xs text-slate-500">待掌握</p>
                            <p class="text-3xl font-bold text-rose-700 mt-2">{{ mistakesData.summary.unresolved }}</p>
                        </div>
                        <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                            <p class="text-xs text-slate-500">重复错误</p>
                            <p class="text-3xl font-bold text-amber-700 mt-2">{{ mistakesData.summary.repeated }}</p>
                        </div>
                        <div class="bg-[#1c2b38] text-white rounded-2xl p-5">
                            <p class="text-xs text-white/70">AI 已分析</p>
                            <p class="text-3xl font-bold mt-2">{{ mistakesData.summary.aiAnalyzed }}</p>
                        </div>
                    </div>

                    <!-- 教师下发的讲评任务 -->
                    <div v-if="reviewTasks.length > 0" class="bg-amber-50 border border-amber-200 rounded-2xl p-6">
                        <div class="flex items-center gap-3 mb-4">
                            <div class="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700">
                                <i class="ph ph-chalkboard-teacher text-xl"></i>
                            </div>
                            <div>
                                <h3 class="text-base font-bold text-amber-900">教师讲评任务</h3>
                                <p class="text-xs text-amber-600">教师针对错题下发的专项讲评，请配合错题复习</p>
                            </div>
                            <span class="ml-auto bg-amber-200 text-amber-800 text-xs font-bold px-2.5 py-1 rounded-full">{{ reviewTasks.length }} 个任务</span>
                        </div>
                        <div class="flex flex-col gap-2">
                            <div v-for="task in reviewTasks" :key="task.id" class="bg-white/80 border border-amber-100 rounded-xl p-4 flex items-center gap-4">
                                <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center text-amber-700">
                                    <i class="ph ph-megaphone"></i>
                                </div>
                                <div class="flex-1 min-w-0">
                                    <p class="text-sm font-bold text-slate-900 truncate">{{ task.title || '讲评任务' }}</p>
                                    <p class="text-xs text-slate-500 mt-0.5">{{ task.knowledgeTags?.join('、') || '综合知识点' }} · {{ task.suggestion || '' }}</p>
                                </div>
                                <span class="text-[11px] font-bold px-2.5 py-1 rounded-full" :class="task.status === 'completed' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'">
                                    {{ task.status === 'completed' ? '已完成' : '待完成' }}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-6">
                        <aside class="glass-panel-liquid p-6 flex flex-col gap-5 min-h-[620px]">
                            <div class="flex items-start justify-between gap-4">
                                <div>
                                    <h3 class="text-lg font-bold text-slate-900">错题列表</h3>
                                    <p class="text-xs text-slate-500 mt-1">按科目、题型、掌握状态快速定位薄弱项</p>
                                </div>
                                <button @click="loadMistakes" class="w-9 h-9 rounded-xl bg-white/70 border border-white flex items-center justify-center text-slate-600 hover:text-slate-900" title="刷新">
                                    <i class="ph ph-arrow-clockwise"></i>
                                </button>
                            </div>

                            <div class="grid grid-cols-3 gap-2">
                                <select v-model="filters.subject" class="rounded-xl border border-white bg-white/70 px-3 py-2 text-xs text-slate-700 outline-none">
                                    <option v-for="item in mistakesData.filters.subjects" :key="item">{{ item }}</option>
                                </select>
                                <select v-model="filters.type" class="rounded-xl border border-white bg-white/70 px-3 py-2 text-xs text-slate-700 outline-none">
                                    <option v-for="item in mistakesData.filters.types" :key="item">{{ item }}</option>
                                </select>
                                <select v-model="filters.mastery" class="rounded-xl border border-white bg-white/70 px-3 py-2 text-xs text-slate-700 outline-none">
                                    <option v-for="item in mistakesData.filters.mastery" :key="item">{{ item }}</option>
                                </select>
                            </div>

                            <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col gap-3 pr-1">
                                <button v-for="mistake in filteredMistakes" :key="mistake.id" @click="activeMistakeId = mistake.id"
                                    class="text-left bg-white/65 border rounded-2xl p-4 transition-colors"
                                    :class="activeMistake?.id === mistake.id ? 'border-[#1c2b38] bg-white/90' : 'border-white hover:bg-white/80'">
                                    <div class="flex items-center justify-between gap-3 mb-2">
                                        <span class="text-[11px] font-bold px-2 py-1 rounded-lg bg-slate-100 text-slate-600">{{ mistake.questionType }}</span>
                                        <span class="text-[11px] font-bold px-2 py-1 rounded-lg" :class="mistake.mastered ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'">{{ mistake.mastered ? '已掌握' : '待掌握' }}</span>
                                    </div>
                                    <p class="text-sm font-bold text-slate-900 line-clamp-2">{{ mistake.questionTitle }}</p>
                                    <p class="text-[11px] text-slate-500 mt-2">{{ mistake.subject }} · 错 {{ mistake.wrongCount }} 次 · {{ formatDisplayDateTime(mistake.lastWrongAt) }}</p>
                                </button>
                                <div v-if="filteredMistakes.length === 0" class="text-sm text-slate-500 bg-white/60 border border-white rounded-2xl p-6 text-center">
                                    当前筛选下暂无错题。
                                </div>
                            </div>
                        </aside>

                        <main class="glass-panel-liquid p-6 min-h-[620px] overflow-y-auto">
                            <template v-if="activeMistake">
                                <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                                    <div>
                                        <div class="flex flex-wrap items-center gap-2 mb-3">
                                            <span class="text-[11px] font-bold bg-slate-100 text-slate-600 px-2.5 py-1 rounded-lg">{{ activeMistake.examTitle }}</span>
                                            <span class="text-[11px] font-bold bg-[#b91c1c]/10 text-[#b91c1c] px-2.5 py-1 rounded-lg">{{ activeMistake.questionType }}</span>
                                        </div>
                                        <h3 class="text-xl font-bold text-slate-900">{{ activeMistake.questionTitle }}</h3>
                                        <p class="text-xs text-slate-500 mt-2">{{ activeMistake.subject }} · 最近错误 {{ formatDisplayDateTime(activeMistake.lastWrongAt) }}</p>
                                    </div>
                                    <button @click="toggleMistakeMastered(activeMistake)" class="px-4 py-2 rounded-xl text-xs font-bold border bg-white/70 text-slate-700 border-white hover:bg-white">
                                        <i class="ph ph-check-circle mr-1"></i> {{ activeMistake.mastered ? '恢复待掌握' : '标记已掌握' }}
                                    </button>
                                </div>

                                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
                                    <div class="bg-white/70 border border-white rounded-2xl p-4">
                                        <p class="text-xs font-bold text-slate-500 mb-2">我的答案</p>
                                        <p class="text-sm text-rose-700 leading-relaxed">{{ activeMistake.studentAnswer }}</p>
                                    </div>
                                    <div class="bg-white/70 border border-white rounded-2xl p-4">
                                        <p class="text-xs font-bold text-slate-500 mb-2">正确答案</p>
                                        <p class="text-sm text-emerald-700 leading-relaxed">{{ activeMistake.correctAnswer }}</p>
                                    </div>
                                </div>

                                <div class="bg-white/65 border border-white rounded-2xl p-4 mt-4">
                                    <p class="text-xs font-bold text-slate-500 mb-2">系统记录的错误原因</p>
                                    <p class="text-sm text-slate-700 leading-relaxed">{{ activeMistake.errorReason }}</p>
                                    <div class="flex flex-wrap gap-2 mt-3">
                                        <span v-for="tag in activeMistake.knowledgeTags" :key="tag" class="text-[11px] bg-slate-100 text-slate-600 px-2 py-1 rounded-lg">{{ tag }}</span>
                                    </div>
                                </div>

                                <div class="mt-6 bg-[#1c2b38] text-white rounded-2xl p-5 overflow-visible">
                                    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-4">
                                        <div>
                                            <h4 class="font-bold">AI 错题分析</h4>
                                            <p class="text-xs text-white/60 mt-1">生成错因诊断、知识点解释和复习路径</p>
                                            <p class="text-[11px] text-white/45 mt-1">当前 Agent：{{ mistakeAgent.name }} · {{ mistakeAgent.model }}</p>
                                        </div>
                                        <button @click="requestAiAnalysis(activeMistake)" :disabled="analyzingMistakeId === activeMistake.id" class="bg-white text-[#1c2b38] rounded-xl px-4 py-2 text-xs font-bold disabled:opacity-60 flex items-center gap-1.5">
                                            <i :class="analyzingMistakeId === activeMistake.id ? 'ph ph-spinner animate-spin' : 'ph ph-sparkle'"></i>
                                            {{ activeMistake.aiAnalysis ? '重新分析' : '生成分析' }}
                                        </button>
                                    </div>
                                    <div v-if="activeMistake.aiAnalysis" class="grid grid-cols-1 lg:grid-cols-2 gap-3 items-stretch">
                                        <div class="bg-white/10 rounded-xl p-3 min-h-0 h-auto">
                                            <p class="text-[11px] text-white/50 mb-1">错因诊断</p>
                                            <p class="text-sm leading-relaxed whitespace-pre-line break-words">{{ activeMistake.aiAnalysis.diagnosis }}</p>
                                        </div>
                                        <div class="bg-white/10 rounded-xl p-3 min-h-0 h-auto">
                                            <p class="text-[11px] text-white/50 mb-1">知识点解释</p>
                                            <p class="text-sm leading-relaxed whitespace-pre-line break-words">{{ activeMistake.aiAnalysis.concept }}</p>
                                        </div>
                                        <div class="bg-white/10 rounded-xl p-3 min-h-0 h-auto">
                                            <p class="text-[11px] text-white/50 mb-1">练习建议</p>
                                            <p class="text-sm leading-relaxed whitespace-pre-line break-words">{{ activeMistake.aiAnalysis.practice }}</p>
                                        </div>
                                        <div class="bg-white/10 rounded-xl p-3 min-h-0 h-auto">
                                            <p class="text-[11px] text-white/50 mb-1">复习路径</p>
                                            <p class="text-sm leading-relaxed whitespace-pre-line break-words">{{ formatAiPath(activeMistake.aiAnalysis.path) }}</p>
                                        </div>
                                    </div>
                                    <div v-else class="text-sm text-white/65 bg-white/10 rounded-xl p-4">
                                        点击“生成分析”后，后端可接入大模型生成个性化错因诊断。
                                    </div>
                                </div>
                            </template>
                        </main>
                    </div>
                </template>
            </div>
        </section>
    `
};
