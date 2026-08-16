import { ref, computed, onMounted } from 'vue';
import { examCenterApi } from '../api/examCenter.js';

export default {
    name: 'TeacherExamManager',
    emits: ['show-toast'],
    setup(_, { emit }) {
        const loading = ref(true);
        const dashboard = ref({ summary: {}, exams: [], submissions: [] });
        const errorAnalysis = ref({ summary: {}, weakKnowledge: [], questionRanking: [] });
        const wrongStudents = ref([]);
        const activeQuestionId = ref(null);
        const loadingWrongStudents = ref(false);
        const saving = ref(false);
        const activeTab = ref('overview');
        const examForm = ref({
            title: '数据结构期中综合考试',
            subject: '数据结构',
            startsAt: '2026-06-30T09:00',
            durationMinutes: 90,
            choiceCount: 20,
            blankCount: 8,
            programmingCount: 2,
            enableProgramming: true
        });
        const totalQuestions = computed(() => {
            return Number(examForm.value.choiceCount || 0) + 
                   Number(examForm.value.blankCount || 0) + 
                   Number(examForm.value.programmingCount || 0);
        });
        const programmingForm = ref({
            examId: 'exam-ds-midterm',
            title: '反转链表',
            language: 'javascript',
            timeLimitMs: 1000,
            memoryLimitMb: 128,
            score: 30,
            description: '给定单链表头节点 head，请返回反转后的链表。',
            starterCode: `function reverseList(head) {
  // TODO: 编写代码
  return head;
}`
        });

        const apiBase = computed(() => examCenterApi.getApiBase());

        const statusMeta = (status) => {
            const map = {
                running: { label: '进行中', cls: 'bg-emerald-50 text-emerald-700 border-emerald-100' },
                scheduled: { label: '已排期', cls: 'bg-amber-50 text-amber-700 border-amber-100' },
                draft: { label: '草稿', cls: 'bg-slate-100 text-slate-600 border-slate-200' },
                review: { label: '待阅卷', cls: 'bg-[#1c2b38]/5 text-[#1c2b38] border-[#1c2b38]/10' }
            };
            return map[status] || { label: status, cls: 'bg-slate-100 text-slate-600 border-slate-200' };
        };

        const formatDateTime = (value) => {
            if (!value) return '-';
            return new Date(value).toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        };

        const loadDashboard = async () => {
            loading.value = true;
            try {
                const [dashboardResult, errorResult] = await Promise.all([
                    examCenterApi.getTeacherDashboard(),
                    examCenterApi.getTeacherErrorAnalysis()
                ]);
                dashboard.value = dashboardResult;
                errorAnalysis.value = errorResult;
                if (!activeQuestionId.value && errorResult?.questionRanking?.length) {
                    activeQuestionId.value = errorResult.questionRanking[0].questionId;
                    await loadWrongStudents(activeQuestionId.value);
                }
            } catch (err) {
                emit('show-toast', `加载考试管理数据失败：${err.message}`, 'error');
            } finally {
                loading.value = false;
            }
        };

        const createExam = async () => {
            saving.value = true;
            try {
                const payload = {
                    ...examForm.value,
                    questionTypes: [
                        { type: 'choice', count: Number(examForm.value.choiceCount) },
                        { type: 'blank', count: Number(examForm.value.blankCount) },
                        { type: 'programming', count: Number(examForm.value.programmingCount) }
                    ]
                };
                const result = await examCenterApi.createExam(payload);
                emit('show-toast', `考试已保存为草稿: ${result.id}`, 'success');
                await loadDashboard();
            } catch (err) {
                emit('show-toast', `创建考试失败: ${err?.message || '未知错误'}`, 'error');
            } finally {
                saving.value = false;
            }
        };

        const createProgrammingProblem = async () => {
            saving.value = true;
            try {
                const result = await examCenterApi.createProgrammingProblem(programmingForm.value.examId, programmingForm.value);
                emit('show-toast', `编程题已保存: ${result.id}`, 'success');
            } catch (err) {
                emit('show-toast', `保存编程题失败: ${err?.message || '未知错误'}`, 'error');
            } finally {
                saving.value = false;
            }
        };

        const loadWrongStudents = async (questionId) => {
            if (!questionId) return;
            activeQuestionId.value = questionId;
            loadingWrongStudents.value = true;
            try {
                wrongStudents.value = (await examCenterApi.getWrongStudents(questionId)) || [];
            } catch (err) {
                emit('show-toast', `加载错误学生列表失败：${err.message}`, 'error');
            } finally {
                loadingWrongStudents.value = false;
            }
        };

        const createReviewTask = async (question) => {
            if (!question) return;
            try {
                const result = await examCenterApi.createReviewTask(question.questionId, {
                    title: `${question.title} 错题讲评`,
                    knowledgeTags: question.knowledgeTags,
                    suggestion: question.aiSuggestion
                });
                emit('show-toast', `讲评任务已生成: ${result.taskId}`, 'success');
            } catch (err) {
                emit('show-toast', `生成讲评任务失败: ${err?.message || '未知错误'}`, 'error');
            }
        };

        // 考试状态变更：draft→scheduled→running→completed
        const changeExamStatus = async (exam, targetStatus) => {
            if (!exam?.id) return;
            try {
                saving.value = true;
                await examCenterApi.updateExamStatus(exam.id, targetStatus);
                const labelMap = { scheduled: '已排期', running: '进行中', completed: '已结束', draft: '草稿' };
                emit('show-toast', `考试「${exam.title}」状态已变更为：${labelMap[targetStatus] || targetStatus}`, 'success');
                await loadDashboard();
            } catch (err) {
                emit('show-toast', `状态变更失败: ${err?.message || '未知错误'}`, 'error');
            } finally {
                saving.value = false;
            }
        };

        // 根据当前状态返回可执行的下一状态
        const nextStatusActions = (status) => {
            const map = {
                draft: [{ status: 'scheduled', label: '发布', cls: 'bg-amber-500 hover:bg-amber-600 text-white' }],
                scheduled: [
                    { status: 'running', label: '开始考试', cls: 'bg-emerald-500 hover:bg-emerald-600 text-white' },
                    { status: 'draft', label: '撤回', cls: 'bg-slate-400 hover:bg-slate-500 text-white' }
                ],
                running: [
                    { status: 'completed', label: '结束考试', cls: 'bg-rose-500 hover:bg-rose-600 text-white' }
                ],
                completed: [{ status: 'running', label: '重新开放', cls: 'bg-blue-500 hover:bg-blue-600 text-white' }]
            };
            return map[status] || [];
        };

        onMounted(loadDashboard);

        return {
            loading,
            dashboard,
            errorAnalysis,
            wrongStudents,
            activeQuestionId,
            loadingWrongStudents,
            saving,
            activeTab,
            examForm,
            programmingForm,
            apiBase,
            statusMeta,
            formatDateTime,
            loadDashboard,
            createExam,
            createProgrammingProblem,
            loadWrongStudents,
            createReviewTask,
            changeExamStatus,
            nextStatusActions,
            totalQuestions
        };
    },
    template: `
        <section class="absolute inset-0 overflow-y-auto p-8 lg:p-10 bg-slate-50">
            <div class="max-w-7xl mx-auto flex flex-col gap-6">
                <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
                    <div>
                        <h2 class="text-2xl font-bold text-slate-900" style="font-family: 'Noto Serif SC', serif;">考试管理</h2>
                        <p class="text-sm text-slate-500 mt-1">创建考试、下达编程题、监控学生进入与提交状态。</p>
                    </div>
                </div>

                <div class="flex flex-wrap gap-2">
                    <button @click="activeTab = 'overview'" class="px-4 py-2 rounded-xl text-sm font-bold border" :class="activeTab === 'overview' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200'">监控总览</button>
                    <button @click="activeTab = 'create'" class="px-4 py-2 rounded-xl text-sm font-bold border" :class="activeTab === 'create' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200'">创建考试</button>
                    <button @click="activeTab = 'programming'" class="px-4 py-2 rounded-xl text-sm font-bold border" :class="activeTab === 'programming' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200'">编程题配置</button>
                    <button @click="activeTab = 'errors'" class="px-4 py-2 rounded-xl text-sm font-bold border" :class="activeTab === 'errors' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200'">错题分析</button>
                </div>

                <div v-if="loading" class="bg-white border border-slate-200 shadow-sm p-8 text-sm text-slate-500">正在加载考试管理数据...</div>

                <template v-else>
                    <div v-show="activeTab === 'overview'" class="flex flex-col gap-6">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-xs text-slate-500">今日考试</p>
                                <p class="text-3xl font-bold text-slate-900 mt-2">{{ dashboard.summary.today }}</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-xs text-slate-500">草稿</p>
                                <p class="text-3xl font-bold text-slate-700 mt-2">{{ dashboard.summary.draft }}</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-xs text-slate-500">进行中</p>
                                <p class="text-3xl font-bold text-emerald-700 mt-2">{{ dashboard.summary.running }}</p>
                            </div>
                            <div class="bg-[#1c2b38] text-white rounded-2xl p-5">
                                <p class="text-xs text-white/70">待阅卷</p>
                                <p class="text-3xl font-bold mt-2">{{ dashboard.summary.review }}</p>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-6">
                            <div class="bg-white border border-slate-200 shadow-sm p-6">
                                <div class="flex items-center justify-between mb-5">
                                    <h3 class="text-lg font-bold text-slate-900">考试列表</h3>
                                    <button @click="loadDashboard" class="w-9 h-9 rounded-xl bg-white/70 border border-white flex items-center justify-center text-slate-600 hover:text-slate-900" title="刷新"><i class="ph ph-arrow-clockwise"></i></button>
                                </div>
                                <div class="overflow-x-auto">
                                    <table class="w-full text-left text-sm">
                                        <thead class="text-xs text-slate-500">
                                            <tr>
                                                <th class="py-3 pr-4">考试</th>
                                                <th class="py-3 pr-4">状态</th>
                                                <th class="py-3 pr-4">时间</th>
                                                <th class="py-3 pr-4">进入/提交</th>
                                                <th class="py-3 pr-4">异常</th>
                                                <th class="py-3 pr-4">操作</th>
                                            </tr>
                                        </thead>
                                        <tbody class="divide-y divide-white/60">
                                            <tr v-for="exam in dashboard.exams" :key="exam.id">
                                                <td class="py-4 pr-4">
                                                    <p class="font-bold text-slate-900">{{ exam.title }}</p>
                                                    <p class="text-xs text-slate-500 mt-1">{{ exam.subject }} · {{ exam.durationMinutes }} 分钟</p>
                                                </td>
                                                <td class="py-4 pr-4">
                                                    <span class="text-[11px] font-bold px-2.5 py-1 rounded-full border" :class="statusMeta(exam.status).cls">{{ statusMeta(exam.status).label }}</span>
                                                </td>
                                                <td class="py-4 pr-4 text-xs text-slate-500">{{ formatDateTime(exam.startsAt) }}</td>
                                                <td class="py-4 pr-4 text-xs text-slate-700">{{ exam.entrants }} / {{ exam.submitted }}</td>
                                                <td class="py-4 pr-4">
                                                    <span class="text-xs font-bold" :class="exam.abnormal > 0 ? 'text-rose-600' : 'text-slate-400'">{{ exam.abnormal }}</span>
                                                </td>
                                                <td class="py-4 pr-4">
                                                    <div class="flex items-center gap-1.5">
                                                        <button v-for="action in nextStatusActions(exam.status)" :key="action.status"
                                                            @click="changeExamStatus(exam, action.status)"
                                                            :disabled="saving"
                                                            class="px-3 py-1.5 rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                                                            :class="action.cls">
                                                            {{ action.label }}
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <aside class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col min-h-0 max-h-[min(70vh,640px)] overflow-hidden">
                                <h3 class="text-lg font-bold text-slate-900 mb-5 shrink-0">实时提交监控</h3>
                                <div class="flex flex-col gap-3 overflow-y-auto min-h-0 pr-1">
                                    <div v-for="item in dashboard.submissions" :key="item.id" class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 shrink-0 overflow-hidden">
                                        <div class="flex items-start justify-between gap-3 min-w-0">
                                            <div class="min-w-0 flex-1">
                                                <p class="font-bold text-slate-900 truncate" :title="item.student">{{ item.student }}</p>
                                                <p class="text-xs text-slate-500 mt-1 truncate" :title="item.exam">{{ item.exam }}</p>
                                            </div>
                                            <span class="text-[11px] font-bold px-2.5 py-1 rounded-full shrink-0 whitespace-nowrap" :class="item.abnormal ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'">{{ item.status }}</span>
                                        </div>
                                        <div class="mt-3 h-2 bg-slate-100 rounded-full overflow-hidden">
                                            <div class="h-full bg-[#1c2b38]" :style="{ width: item.progress + '%' }"></div>
                                        </div>
                                        <p class="text-[11px] text-slate-400 mt-2 truncate" :title="item.lastSavedAt">自动保存: {{ item.lastSavedAt }}</p>
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </div>

                    <form v-show="activeTab === 'create'" @submit.prevent="createExam" class="glass-panel-liquid p-8 lg:p-10 max-w-5xl transition-all duration-500 hover:shadow-lg">
                        <!-- 表单头部 -->
                        <div class="flex items-center gap-3 border-b border-[#1c2b38]/10 pb-5 mb-8">
                            <div class="w-10 h-10 rounded-xl bg-[#1c2b38]/5 flex items-center justify-center text-[#1c2b38]">
                                <i class="ph ph-file-plus text-xl"></i>
                            </div>
                            <div>
                                <h3 class="text-lg font-bold text-slate-900" style="font-family: 'Noto Serif SC', serif;">新建考卷蓝图</h3>
                                <p class="text-xs text-slate-500 mt-0.5 font-medium">规划考试的基本信息与题型配比，保存后自动进入草稿箱。</p>
                            </div>
                        </div>

                        <!-- 双栏布局 -->
                        <div class="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8 lg:gap-10">
                            <!-- 左栏：基本信息 -->
                            <div class="flex flex-col gap-6">
                                <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                                    <i class="ph ph-sliders"></i> 考试基本信息
                                </h4>
                                
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-pencil-line text-slate-400"></i> 考试名称
                                        </label>
                                        <input v-model="examForm.title" placeholder="如：数据结构期中综合考试" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>
                                    
                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-book-open text-slate-400"></i> 考试科目
                                        </label>
                                        <input v-model="examForm.subject" placeholder="如：数据结构" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>
                                    
                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-calendar-blank text-slate-400"></i> 开考时间
                                        </label>
                                        <input v-model="examForm.startsAt" type="datetime-local" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>
                                    
                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-timer text-slate-400"></i> 考试时长 (分钟)
                                        </label>
                                        <input v-model="examForm.durationMinutes" type="number" placeholder="90" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>
                                </div>
                            </div>
                            
                            <!-- 右栏：题型结构 -->
                            <div class="flex flex-col gap-6 lg:border-l lg:border-slate-200/60 lg:pl-8">
                                <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                                    <i class="ph ph-list-numbers"></i> 试卷题型配比
                                </h4>
                                
                                <div class="flex flex-col gap-4">
                                    <div class="flex items-center justify-between gap-4">
                                        <span class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-list-checks text-slate-400"></i> 选择题数量
                                        </span>
                                        <input v-model="examForm.choiceCount" type="number" 
                                            class="liquid-glass-input w-24 px-3 py-1.5 text-sm text-center outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>
                                    
                                    <div class="flex items-center justify-between gap-4">
                                        <span class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-textbox text-slate-400"></i> 填空题数量
                                        </span>
                                        <input v-model="examForm.blankCount" type="number" 
                                            class="liquid-glass-input w-24 px-3 py-1.5 text-sm text-center outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>
                                    
                                    <div class="flex items-center justify-between gap-4">
                                        <span class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-code-block text-slate-400"></i> 编程题数量
                                        </span>
                                        <input v-model="examForm.programmingCount" type="number" 
                                            class="liquid-glass-input w-24 px-3 py-1.5 text-sm text-center outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>
                                    
                                    <div class="flex items-center justify-between gap-4 pt-3 border-t border-slate-200/60">
                                        <span class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-terminal-window text-slate-400"></i> 启用编程考试入口
                                        </span>
                                        <label class="relative inline-flex items-center cursor-pointer">
                                            <input v-model="examForm.enableProgramming" type="checkbox" class="sr-only peer" />
                                            <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#1c2b38]"></div>
                                        </label>
                                    </div>
                                </div>
                                
                                <!-- 试卷结构可视化预览 -->
                                <div class="mt-4 bg-slate-50/80 rounded-2xl p-4 border border-slate-100/80">
                                    <div class="flex items-center justify-between mb-3">
                                        <span class="text-xs font-bold text-slate-600">考卷题量总览</span>
                                        <span class="text-sm font-extrabold text-[#1c2b38]" style="font-family: 'Barlow Condensed', sans-serif;">{{ totalQuestions }} 道题</span>
                                    </div>
                                    
                                    <!-- 比例图条 -->
                                    <div class="h-2.5 bg-slate-200 rounded-full flex overflow-hidden">
                                        <div v-if="examForm.choiceCount > 0" 
                                            class="bg-[#1c2b38] transition-all duration-300" 
                                            :style="{ width: (examForm.choiceCount / (totalQuestions || 1)) * 100 + '%' }"
                                            :title="'选择题: ' + examForm.choiceCount + '题'"></div>
                                        <div v-if="examForm.blankCount > 0" 
                                            class="bg-slate-400 transition-all duration-300" 
                                            :style="{ width: (examForm.blankCount / (totalQuestions || 1)) * 100 + '%' }"
                                            :title="'填空题: ' + examForm.blankCount + '题'"></div>
                                        <div v-if="examForm.programmingCount > 0" 
                                            class="bg-[#00e5ff] transition-all duration-300" 
                                            :style="{ width: (examForm.programmingCount / (totalQuestions || 1)) * 100 + '%' }"
                                            :title="'编程题: ' + examForm.programmingCount + '题'"></div>
                                    </div>
                                    
                                    <!-- 图例说明 -->
                                    <div class="flex flex-wrap gap-x-4 gap-y-2 mt-3 text-[10px] text-slate-500 font-bold">
                                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-[#1c2b38]"></span> 选择题</span>
                                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-slate-400"></span> 填空题</span>
                                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-[#00e5ff]"></span> 编程题</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 底部控制栏 -->
                        <div class="flex items-center justify-between border-t border-[#1c2b38]/10 pt-6 mt-8">
                            <div class="text-xs text-slate-400 hidden sm:block font-medium">
                                <i class="ph ph-info mr-1"></i> 您可以随时在“监控总览”中将草稿发布或排期。
                            </div>
                            <button :disabled="saving" class="liquid-glass-btn liquid-glass-btn-teacher px-6 py-3 rounded-xl text-sm font-bold flex items-center gap-2 disabled:opacity-60">
                                <i :class="saving ? 'ph ph-spinner animate-spin' : 'ph ph-floppy-disk'"></i> 保存考试草稿
                            </button>
                        </div>
                    </form>

                    <form v-show="activeTab === 'programming'" @submit.prevent="createProgrammingProblem" class="glass-panel-liquid p-8 lg:p-10 max-w-5xl transition-all duration-500 hover:shadow-lg">
                        <!-- 表单头部 -->
                        <div class="flex items-center gap-3 border-b border-[#1c2b38]/10 pb-5 mb-8">
                            <div class="w-10 h-10 rounded-xl bg-[#1c2b38]/5 flex items-center justify-center text-[#1c2b38]">
                                <i class="ph ph-terminal text-xl"></i>
                            </div>
                            <div>
                                <h3 class="text-lg font-bold text-slate-900" style="font-family: 'Noto Serif SC', serif;">配置编程评测题</h3>
                                <p class="text-xs text-slate-500 mt-0.5 font-medium">配置在线编程题目的编译环境、运行时限制及初始代码模板。</p>
                            </div>
                        </div>

                        <div class="flex flex-col gap-6">
                            <!-- 命题与限制配置 -->
                            <div>
                                <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-4">
                                    <i class="ph ph-sliders"></i> 命题与限制参数
                                </h4>
                                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-link text-slate-400"></i> 绑定考试 ID
                                        </label>
                                        <input v-model="programmingForm.examId" placeholder="输入关联的考试ID" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>

                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-text-t text-slate-400"></i> 题目名称
                                        </label>
                                        <input v-model="programmingForm.title" placeholder="如：链表反转" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>

                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-brackets-curly text-slate-400"></i> 编程语言
                                        </label>
                                        <select v-model="programmingForm.language" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20 bg-white/50 cursor-pointer">
                                            <option value="javascript">JavaScript</option>
                                            <option value="python">Python</option>
                                            <option value="cpp">C++</option>
                                            <option value="java">Java</option>
                                        </select>
                                    </div>

                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-trophy text-slate-400"></i> 题目分值 (分)
                                        </label>
                                        <input v-model="programmingForm.score" type="number" placeholder="30" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>

                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-gauge text-slate-400"></i> 时间限制 (ms)
                                        </label>
                                        <input v-model="programmingForm.timeLimitMs" type="number" placeholder="1000" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>

                                    <div class="flex flex-col gap-2">
                                        <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <i class="ph ph-cpu text-slate-400"></i> 内存限制 (MB)
                                        </label>
                                        <input v-model="programmingForm.memoryLimitMb" type="number" placeholder="128" 
                                            class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20" />
                                    </div>
                                </div>
                            </div>

                            <!-- 题目描述区 -->
                            <div class="flex flex-col gap-2">
                                <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                    <i class="ph ph-note-pencil text-slate-400"></i> 题目描述与规格说明
                                </label>
                                <textarea v-model="programmingForm.description" rows="3" placeholder="在此输入题目详细描述、输入输出规范及测试样本说明..." 
                                    class="liquid-glass-input w-full px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#1c2b38]/20 resize-none"></textarea>
                            </div>

                            <!-- 初始代码终端 -->
                            <div class="flex flex-col gap-2">
                                <label class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                    <i class="ph ph-file-code text-slate-400"></i> 初始代码模板
                                </label>
                                
                                <div class="bg-[#0d1117] rounded-2xl border border-slate-800 shadow-cinematic overflow-hidden flex flex-col mt-1">
                                    <!-- 终端头部 -->
                                    <div class="flex items-center justify-between px-4 py-3 bg-[#161b22] border-b border-slate-800/80">
                                        <div class="flex items-center gap-2">
                                            <span class="w-3 h-3 rounded-full bg-rose-500/90 shadow-sm"></span>
                                            <span class="w-3 h-3 rounded-full bg-amber-500/90 shadow-sm"></span>
                                            <span class="w-3 h-3 rounded-full bg-emerald-500/90 shadow-sm"></span>
                                            <span class="text-xs text-slate-400 font-mono ml-2">starter_code.template</span>
                                        </div>
                                        <div class="flex items-center gap-1.5 text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-md font-mono uppercase tracking-wider font-bold">
                                            <i class="ph ph-brackets-angle"></i> {{ programmingForm.language }}
                                        </div>
                                    </div>
                                    
                                    <!-- 编辑区域 -->
                                    <textarea v-model="programmingForm.starterCode" rows="9" 
                                        class="w-full bg-[#0d1117] text-emerald-400 font-mono p-4 text-sm outline-none resize-none focus:text-slate-100 transition-colors"
                                        placeholder="// 编写学生初始看到的代码框架"></textarea>
                                </div>
                            </div>
                        </div>

                        <!-- 底部控制栏 -->
                        <div class="flex items-center justify-between border-t border-[#1c2b38]/10 pt-6 mt-8">
                            <div class="text-xs text-slate-400 hidden sm:block font-medium">
                                <i class="ph ph-info mr-1"></i> 保存后学生即可在考试中使用 Monaco IDE 载入该代码。
                            </div>
                            <button :disabled="saving" class="liquid-glass-btn liquid-glass-btn-teacher px-6 py-3.5 rounded-xl text-sm font-bold flex items-center gap-2 disabled:opacity-60">
                                <i :class="saving ? 'ph ph-spinner animate-spin' : 'ph ph-code-block'"></i> 保存编程题
                            </button>
                        </div>
                    </form>

                    <div v-show="activeTab === 'errors'" class="flex flex-col gap-6">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-xs text-slate-500">高风险题目</p>
                                <p class="text-3xl font-bold text-rose-700 mt-2">{{ errorAnalysis.summary.highRiskQuestions }}</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-xs text-slate-500">平均错误率</p>
                                <p class="text-3xl font-bold text-slate-900 mt-2">{{ errorAnalysis.summary.averageErrorRate }}%</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-xs text-slate-500">影响学生</p>
                                <p class="text-3xl font-bold text-amber-700 mt-2">{{ errorAnalysis.summary.affectedStudents }}</p>
                            </div>
                            <div class="bg-[#1c2b38] text-white rounded-2xl p-5">
                                <p class="text-xs text-white/70">已生成讲评</p>
                                <p class="text-3xl font-bold mt-2">{{ errorAnalysis.summary.generatedReviewTasks }}</p>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-6 xl:items-start">
                            <div class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col min-h-0 max-h-[min(70vh,720px)] overflow-hidden">
                                <div class="flex items-center justify-between mb-5 shrink-0">
                                    <div class="min-w-0">
                                        <h3 class="text-lg font-bold text-slate-900">错误率最高题目</h3>
                                        <p class="text-xs text-slate-500 mt-1">按考试提交结果聚合，后续可接班级和考试筛选</p>
                                    </div>
                                    <button @click="loadDashboard" class="w-9 h-9 shrink-0 rounded-xl bg-white/70 border border-white flex items-center justify-center text-slate-600 hover:text-slate-900" title="刷新">
                                        <i class="ph ph-arrow-clockwise"></i>
                                    </button>
                                </div>

                                <div class="flex flex-col gap-3 overflow-y-auto min-h-0 pr-1">
                                    <article v-for="question in errorAnalysis.questionRanking" :key="question.questionId"
                                        class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 shrink-0 overflow-hidden"
                                        :class="activeQuestionId === question.questionId ? 'border-[#1c2b38]' : 'border-white'">
                                        <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                                            <div class="min-w-0 flex-1">
                                                <div class="flex flex-wrap items-center gap-2 mb-2">
                                                    <span class="text-[11px] font-bold bg-slate-100 text-slate-600 px-2 py-1 rounded-lg">{{ question.subject }}</span>
                                                    <span class="text-[11px] font-bold bg-[#b91c1c]/10 text-[#b91c1c] px-2 py-1 rounded-lg">{{ question.type }}</span>
                                                </div>
                                                <h4 class="font-bold text-slate-900 break-words">{{ question.title }}</h4>
                                                <p class="text-xs text-slate-500 mt-2">错误 {{ question.wrongStudents }}/{{ question.totalStudents }} 人 · 错误率 {{ question.errorRate }}%</p>
                                                <div class="flex flex-wrap gap-2 mt-3">
                                                    <span v-for="tag in question.knowledgeTags" :key="tag" class="text-[11px] bg-slate-100 text-slate-600 px-2 py-1 rounded-lg">{{ tag }}</span>
                                                </div>
                                            </div>
                                            <div class="lg:w-40 shrink-0 flex lg:flex-col gap-2">
                                                <button @click="loadWrongStudents(question.questionId)" class="bg-white border border-slate-200 text-slate-700 rounded-xl px-3 py-2 text-xs font-bold hover:bg-slate-50">
                                                    查看学生
                                                </button>
                                                <button @click="createReviewTask(question)" class="bg-[#1c2b38] text-white rounded-xl px-3 py-2 text-xs font-bold hover:bg-[#253645]">
                                                    生成讲评任务
                                                </button>
                                            </div>
                                        </div>

                                        <div class="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-3">
                                            <div class="bg-slate-50/80 rounded-xl p-3 flex flex-col min-h-0 max-h-28 overflow-hidden">
                                                <p class="text-[11px] font-bold text-slate-500 mb-2 shrink-0">常见错误答案</p>
                                                <div class="flex flex-wrap gap-2 overflow-y-auto min-h-0 pr-0.5">
                                                    <span v-for="answer in question.commonWrongAnswers" :key="answer" class="text-[11px] bg-white border border-slate-100 text-slate-600 px-2 py-1 rounded-lg max-w-full break-all">{{ answer }}</span>
                                                </div>
                                            </div>
                                            <div class="bg-[#1c2b38] text-white rounded-xl p-3 flex flex-col min-h-0 max-h-28 overflow-hidden">
                                                <p class="text-[11px] text-white/55 mb-1 shrink-0">AI 讲评建议</p>
                                                <p class="text-xs leading-relaxed overflow-y-auto min-h-0 pr-0.5 break-words">{{ question.aiSuggestion }}</p>
                                            </div>
                                        </div>
                                    </article>
                                </div>
                            </div>

                            <aside class="flex flex-col gap-6 min-h-0">
                                <div class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col min-h-0 max-h-[min(42vh,360px)] overflow-hidden">
                                    <h3 class="text-lg font-bold text-slate-900 mb-4 shrink-0">薄弱知识点</h3>
                                    <div class="flex flex-col gap-3 overflow-y-auto min-h-0 pr-1">
                                        <div v-for="item in errorAnalysis.weakKnowledge" :key="item.tag" class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 shrink-0 overflow-hidden">
                                            <div class="flex items-center justify-between gap-3 mb-2 min-w-0">
                                                <p class="font-bold text-slate-900 truncate min-w-0" :title="item.tag">{{ item.tag }}</p>
                                                <span class="text-xs font-bold text-rose-700 shrink-0">{{ item.errorRate }}%</span>
                                            </div>
                                            <div class="h-2 bg-slate-100 rounded-full overflow-hidden mb-2">
                                                <div class="h-full bg-[#b91c1c]" :style="{ width: item.errorRate + '%' }"></div>
                                            </div>
                                            <p class="text-[11px] text-slate-500 line-clamp-2" :title="item.questionCount + ' 道题关联 · ' + item.suggestion">{{ item.questionCount }} 道题关联 · {{ item.suggestion }}</p>
                                        </div>
                                    </div>
                                </div>

                                <div class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col min-h-0 max-h-[min(42vh,360px)] overflow-hidden">
                                    <div class="flex items-center justify-between mb-4 shrink-0 gap-3">
                                        <h3 class="text-lg font-bold text-slate-900">错误学生</h3>
                                        <span class="text-[11px] text-slate-500 shrink-0">{{ loadingWrongStudents ? '加载中' : wrongStudents.length + ' 人' }}</span>
                                    </div>
                                    <div class="flex flex-col gap-3 overflow-y-auto min-h-0 pr-1">
                                        <div v-for="student in wrongStudents" :key="student.id" class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 shrink-0 overflow-hidden">
                                            <div class="flex items-start justify-between gap-3 min-w-0">
                                                <div class="min-w-0 flex-1">
                                                    <p class="font-bold text-slate-900 truncate" :title="student.name">{{ student.name }}</p>
                                                    <p class="text-xs text-slate-500 mt-1 truncate" :title="student.className + ' · 得分 ' + student.score">{{ student.className }} · 得分 {{ student.score }}</p>
                                                    <p class="text-[11px] text-slate-500 mt-2 line-clamp-2 break-all" :title="'答案：' + student.answer">答案：{{ student.answer }}</p>
                                                </div>
                                                <span class="text-[11px] font-bold px-2 py-1 rounded-lg shrink-0 whitespace-nowrap" :class="student.status === '已订正' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'">{{ student.status }}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </div>
                </template>
            </div>
        </section>
    `
};
