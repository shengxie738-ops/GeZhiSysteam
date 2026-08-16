import { ref, computed, onMounted, watch } from 'vue';
import { homeworkApi, mockSubjects } from '../api/homework.js';
import RadarChart from './RadarChart.js';

export default {
    name: 'StudentHomework',
    props: {
        currentUser: { type: Object, default: null }
    },
    components: {
        RadarChart
    },
    emits: ['show-toast'],
    setup(props, { emit }) {
        const loading = ref(true);
        const homeworkList = ref([]);
        const subjects = ref(mockSubjects);
        
        // 导航控制：'overview' (科目首页) | 'subject' (科目做题工作台)
        const currentSubView = ref('overview');
        const selectedSubject = ref(null);
        
        // 作业选择
        const selectedHomework = ref(null);
        
        // 多题型做题管理
        const activeQuestionIndex = ref(0); // 当前作答题目索引
        const submittedAnswers = ref({}); // 存放临时答案：{ q1: 'B', q2_0: 'track', q2_1: 'trigger', q3: '...' }
        
        // 调试控制台
        const activeConsoleTab = ref('console');
        const consoleLines = ref([]);
        const runTesting = ref(false);

        // 提交与诊断
        const submitting = ref(false);
        const diagnosing = ref(false);
        const currentDiagnosis = ref(null);

        const username = computed(() => props.currentUser?.username || '李明');

        // 计算待提交汇总看板数据
        const summary = computed(() => {
            const list = homeworkList.value;
            const unsubmitted = list.filter(h => h.status === 'unsubmitted').length;
            const urgent = list.filter(h => h.status === 'unsubmitted' && h.urgent).length;
            const pending = list.filter(h => h.status === 'submitted').length;
            const graded = list.filter(h => h.status === 'graded').length;
            return { unsubmitted, urgent, pending, graded };
        });

        // 统计各科目未提交的作业数
        const subjectUnsubmittedCount = (subjectId) => {
            return homeworkList.value.filter(h => h.subjectId === subjectId && h.status === 'unsubmitted').length;
        };

        // 当前科目的所有作业
        const subjectHomeworks = computed(() => {
            if (!selectedSubject.value) return [];
            return homeworkList.value.filter(h => h.subjectId === selectedSubject.value.id);
        });

        // 当前选中作业的当前问题
        const activeQuestion = computed(() => {
            if (!selectedHomework.value || !selectedHomework.value.questions) return null;
            return selectedHomework.value.questions[activeQuestionIndex.value] || null;
        });

        // 载入作业
        const loadHomeworkData = async () => {
            loading.value = true;
            try {
                const list = await homeworkApi.getStudentHomeworkList(username.value);
                homeworkList.value = list;
            } catch (err) {
                emit('show-toast', '读取作业数据失败', 'error');
            } finally {
                loading.value = false;
            }
        };

        // 点击进入某一科目
        const enterSubject = (subject) => {
            selectedSubject.value = subject;
            currentSubView.value = 'subject';
            activeQuestionIndex.value = 0;
            
            // 默认选中当前科目的第一项作业
            const hws = homeworkHomeworkListFiltered(subject.id);
            if (hws.length > 0) {
                selectHomework(hws[0]);
            } else {
                selectedHomework.value = null;
            }
        };

        const homeworkHomeworkListFiltered = (subId) => {
            return homeworkList.value.filter(h => h.subjectId === subId);
        };

        // 退回科目首页
        const exitSubject = () => {
            currentSubView.value = 'overview';
            selectedSubject.value = null;
            selectedHomework.value = null;
        };

        // 选择作业
        const selectHomework = (hw) => {
            selectedHomework.value = hw;
            activeQuestionIndex.value = 0;
            currentDiagnosis.value = hw.diagnosis || null;
            consoleLines.value = [];
            
            // 复制答案到当前作答临时对象
            submittedAnswers.value = hw.submittedAnswers ? { ...hw.submittedAnswers } : {};
        };

        // 快速切换题目
        const switchQuestion = (index) => {
            activeQuestionIndex.value = index;
            consoleLines.value = [];
        };

        // 选择单选题答案
        const selectChoice = (qId, optionVal) => {
            submittedAnswers.value[qId] = optionVal;
        };

        // 运行代码测试 (Mock)
        const runCodeMock = () => {
            if (runTesting.value) return;
            runTesting.value = true;
            activeConsoleTab.value = 'console';
            consoleLines.value = ['[Compiler] 启动 JavaScript ESM 编译器...', '[Console] 绑定 Proxy 拦截断言桶...'];
            
            setTimeout(() => {
                const code = submittedAnswers.value.q3 || '';
                try {
                    if (selectedHomework.value.id === 'hw-daily-01') {
                        const hasReflect = code.includes('Reflect');
                        const hasProxy = code.includes('Proxy');
                        if (hasProxy) {
                            consoleLines.value.push('[Console] Success: reactive() 被成功拦截绑定！');
                            if (hasReflect) {
                                consoleLines.value.push('[Console] Success: 成功运用 Reflect 阻断 this 原型链指针漂移漏洞。');
                            } else {
                                consoleLines.value.push('[Console] Warn: 属性修改直接调用了 target[key]，继承 getter 时可能会引起 this 丢失。');
                            }
                        } else {
                            consoleLines.value.push('[Console] Error: 未定义 Proxy 对象代理。');
                        }
                    } else if (selectedHomework.value.id === 'hw-daily-02') {
                        consoleLines.value.push('[Console] Success: 用例 reverseList([1,2,3]) => [3,2,1] 运行通过；耗时 1.5ms。');
                    } else {
                        consoleLines.value.push('[Console] Success: 代码编译测试通过，暂未拦截异常。');
                    }
                } catch (e) {
                    consoleLines.value.push(`[Console] Error: ${e.message}`);
                } finally {
                    runTesting.value = false;
                    emit('show-toast', '算法试运行完成', 'success');
                }
            }, 1000);
        };

        // 请求智能体协同诊断舱
        const handleDiagnose = async () => {
            if (diagnosing.value) return;
            diagnosing.value = true;
            try {
                const diag = await homeworkApi.requestAgentDiagnosis(selectedHomework.value.id, submittedAnswers.value);
                currentDiagnosis.value = diag;
                // 同步本地
                const hw = homeworkList.value.find(h => h.id === selectedHomework.value.id);
                if (hw) {
                    hw.diagnosis = diag;
                }
                emit('show-toast', 'AI协同会诊报告生成完毕', 'success');
            } catch (err) {
                emit('show-toast', '请求诊断服务失败', 'error');
            } finally {
                diagnosing.value = false;
            }
        };

        // 提交当前科目作业
        const handleSubmit = async () => {
            if (submitting.value) return;
            submitting.value = true;
            
            const payload = {
                studentName: username.value,
                answers: submittedAnswers.value,
                file: null
            };

            try {
                await homeworkApi.submitHomework(selectedHomework.value.id, payload);
                const hw = homeworkList.value.find(h => h.id === selectedHomework.value.id);
                if (hw) {
                    hw.status = 'submitted';
                    hw.submittedAnswers = { ...submittedAnswers.value };
                }
                if (typeof window !== 'undefined') {
                    window.dispatchEvent(new CustomEvent('homework-submitted', {
                        detail: { homeworkId: selectedHomework.value.id }
                    }));
                }
                emit('show-toast', '作业成果已递交，等待教师评定', 'success');
            } catch (err) {
                emit('show-toast', '提交作业失败', 'error');
            } finally {
                submitting.value = false;
            }
        };

        // ECharts 雷达图选项
        const radarOption = computed(() => {
            if (!currentDiagnosis.value) return null;
            const s = currentDiagnosis.value.scores;
            return {
                radar: {
                    indicator: [
                        { name: '规划对齐力 (Alina)', max: 100 },
                        { name: '代码工程力 (Ninja)', max: 100 },
                        { name: '理论完备度 (Prof. X)', max: 100 }
                    ],
                    splitNumber: 4,
                    axisName: { color: '#1c2b38', fontSize: 11, fontWeight: 600 },
                    axisLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.1)' } },
                    splitLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.08)' } },
                    splitArea: { areaStyle: { color: ['rgba(255,255,255,0.4)', 'rgba(255,255,255,0.2)'] } }
                },
                series: [{
                    type: 'radar',
                    data: [{
                        value: [s.alina, s.codeninja, s.profx],
                        name: '协同评估',
                        areaStyle: { color: 'rgba(99, 102, 241, 0.12)' },
                        lineStyle: { color: '#6366f1', width: 2 },
                        itemStyle: { color: '#6366f1' }
                    }]
                }]
            };
        });

        // 关闭诊断舱 Modal
        const closeDiagnosis = () => {
            currentDiagnosis.value = null;
        };

        // Modal 打开时锁定 body 滚动，关闭时恢复（防止底部页面抖动）
        watch(currentDiagnosis, (val) => {
            if (typeof document !== 'undefined') {
                document.body.style.overflow = val ? 'hidden' : '';
            }
        });

        onMounted(loadHomeworkData);

        return {
            loading,
            homeworkList,
            subjects,
            currentSubView,
            selectedSubject,
            selectedHomework,
            activeQuestionIndex,
            submittedAnswers,
            activeConsoleTab,
            consoleLines,
            runTesting,
            submitting,
            diagnosing,
            currentDiagnosis,
            summary,
            subjectUnsubmittedCount,
            subjectHomeworks,
            activeQuestion,
            enterSubject,
            exitSubject,
            selectHomework,
            switchQuestion,
            selectChoice,
            runCodeMock,
            handleDiagnose,
            handleSubmit,
            closeDiagnosis,
            radarOption
        };
    },
    template: `
        <section class="absolute inset-0 overflow-hidden flex flex-col p-6 lg:p-8 bg-slate-50">
            <div v-if="loading" class="flex-1 flex items-center justify-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                    <i class="ph ph-circle-notch animate-spin text-3xl"></i>
                    <p class="text-xs font-medium">同步课程作业看板中...</p>
                </div>
            </div>

            <!-- ==================== 1. 科目首页 (Overview) ==================== -->
            <div v-else-if="currentSubView === 'overview'" class="flex-1 overflow-y-auto pr-1 flex flex-col gap-8">
                <!-- 待提交作业汇总大屏 (Aesthetic Panel) -->
                <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                        <p class="text-[10px] text-slate-400 font-semibold tracking-wider">未提交 Checkpoint</p>
                        <p class="text-3xl font-extrabold text-slate-800 mt-2 font-mono" style="font-family: 'Barlow Condensed', sans-serif;">{{ summary.unsubmitted }}</p>
                    </div>
                    <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                        <p class="text-[10px] text-slate-400 font-semibold tracking-wider">紧急待办任务</p>
                        <p class="text-3xl font-extrabold text-[#b91c1c] mt-2 font-mono" style="font-family: 'Barlow Condensed', sans-serif;">{{ summary.urgent }}</p>
                    </div>
                    <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                        <p class="text-[10px] text-slate-400 font-semibold tracking-wider">已递交待阅</p>
                        <p class="text-3xl font-extrabold text-indigo-600 mt-2 font-mono" style="font-family: 'Barlow Condensed', sans-serif;">{{ summary.pending }}</p>
                    </div>
                    <div class="bg-[#1c2b38] text-white rounded-2xl p-5 shadow-md flex flex-col justify-between">
                        <p class="text-[10px] text-white/60 font-semibold tracking-wider">已批定级别数</p>
                        <p class="text-3xl font-extrabold mt-2 font-mono text-[#00e5ff]" style="font-family: 'Barlow Condensed', sans-serif;">{{ summary.graded }}</p>
                    </div>
                </section>

                <!-- AI 规划师 Alina 气泡 -->
                <section data-testid="student-homework-alina-suggestion" class="student-homework-alina-suggestion glass-panel-liquid p-5 flex items-start gap-4 border border-white/90 bg-white/90">
                    <div class="w-10 h-10 rounded-full bg-indigo-500 text-white flex items-center justify-center font-bold shadow-sm shrink-0">Alina</div>
                    <div class="flex-1">
                        <h4 class="text-xs font-bold text-slate-700">Alina 协同学习决策支持</h4>
                        <p class="text-xs text-slate-500 leading-relaxed mt-1">
                            “ 同学，监控发现您在《数据结构与算法》的链表机制以及《高级前端程序设计》的 Proxy 拦截上面还有 2 个日常 Checkpoint 作业未完成。建议您今天优先攻克数据结构防指针悬挂的作业，以对齐您的个人进度规划。”
                        </p>
                    </div>
                </section>

                <!-- 科目分类卡片墙 -->
                <section class="flex flex-col gap-4">
                    <h3 class="label-minor tracking-widest">科目作业分类入口</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                        <div v-for="sub in subjects" :key="sub.id" @click="enterSubject(sub)"
                            class="glass-panel-liquid p-5 cursor-pointer flex flex-col justify-between min-h-[170px] group border border-white/60"
                            :class="sub.bgClass">
                            <div class="flex justify-between items-start">
                                <div class="w-10 h-10 rounded-xl bg-white flex items-center justify-center text-lg shadow-sm">
                                    <i :class="['ph', sub.icon]"></i>
                                </div>
                                <span class="text-[9px] font-mono font-bold tracking-wider px-2 py-0.5 bg-white/70 rounded-full border border-slate-200/50">{{ sub.code }}</span>
                            </div>
                            <div class="mt-4">
                                <h4 class="font-extrabold text-slate-800 text-sm leading-snug group-hover:translate-x-0.5 transition-transform">{{ sub.name }}</h4>
                                <div class="flex justify-between items-center mt-3 pt-3 border-t border-slate-200/40">
                                    <span class="text-[10px] text-slate-400 font-medium">未完成任务</span>
                                    <span class="text-xs font-bold" :class="subjectUnsubmittedCount(sub.id) > 0 ? 'text-[#b91c1c]' : 'text-slate-400'">
                                        {{ subjectUnsubmittedCount(sub.id) }} 项
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>

            <!-- ==================== 2. 科目作业下钻空间 (Subject Workspace) ==================== -->
            <div v-else class="flex-1 min-h-0 flex flex-col gap-4">
                <div class="flex-shrink-0 flex items-center justify-between border-b border-slate-200 pb-3 mb-1">
                    <button @click="exitSubject" class="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-semibold transition-all">
                        <i class="ph ph-arrow-left"></i> 返回科目入口
                    </button>
                    <div class="text-right">
                        <span class="text-[10px] text-slate-400 uppercase tracking-widest font-mono">WORKSPACE</span>
                        <h3 class="text-sm font-bold text-slate-800">{{ selectedSubject.name }}</h3>
                    </div>
                </div>

                <div v-if="!selectedHomework" class="flex-1 flex items-center justify-center">
                    <div class="text-center p-8 bg-white/40 border border-white/60 rounded-3xl max-w-sm">
                        <i class="ph ph-article-ny text-slate-300 text-3xl mb-2"></i>
                        <h4 class="font-bold text-slate-700 text-sm">该学科下暂无作业</h4>
                        <p class="text-xs text-slate-400 mt-1">Alina 尚未发现有需要递交的习题。您可以继续复习当前科目的课件。</p>
                    </div>
                </div>

                <div v-else class="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[300px_1fr] gap-6">
                    <!-- 左侧科目下作业列表 -->
                    <aside class="flex flex-col gap-3 overflow-hidden h-full">
                        <div class="glass-panel-liquid p-4 flex-1 overflow-y-auto pr-1 flex flex-col gap-2.5">
                            <h4 class="label-minor mb-1">作业任务列表</h4>
                            <article v-for="hw in subjectHomeworks" :key="hw.id"
                                @click="selectHomework(hw)"
                                class="p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col gap-2"
                                :class="selectedHomework.id === hw.id 
                                    ? 'bg-white border-[#1c2b38] shadow-md' 
                                    : 'bg-white/40 border-white/60 hover:bg-white/80'">
                                <div class="flex justify-between items-center">
                                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
                                        :class="hw.status === 'graded' 
                                            ? 'bg-emerald-50 text-emerald-600 border border-emerald-100'
                                            : hw.status === 'submitted'
                                                ? 'bg-blue-50 text-blue-600 border border-blue-100'
                                                : 'bg-amber-50 text-amber-600 border border-amber-100'">
                                        {{ hw.status === 'graded' ? '已批阅' : (hw.status === 'submitted' ? '已交' : '未交') }}
                                    </span>
                                    <span class="text-[9px] text-slate-400 font-mono">{{ hw.type === 'daily' ? '日常' : '阶段' }}</span>
                                </div>
                                <h5 class="font-bold text-slate-800 text-xs leading-snug line-clamp-2">{{ hw.title }}</h5>
                                <p class="text-[9px] text-slate-400 font-mono mt-0.5 flex items-center gap-1"><i class="ph ph-clock"></i> 截止: {{ hw.deadline }}</p>
                            </article>
                        </div>
                    </aside>

                    <!-- 右侧多题型做题主空间 -->
                    <main class="min-h-0 flex flex-col gap-6 overflow-y-auto pr-1">
                        <!-- 作业题目与要求标题 -->
                        <section class="glass-panel-liquid p-5">
                            <div class="flex items-center justify-between border-b border-slate-200/50 pb-3 mb-3">
                                <div>
                                    <span class="text-[10px] text-slate-400 font-mono">EXERCISE BRIEF</span>
                                    <h3 class="text-base font-bold text-slate-800 mt-0.5">{{ selectedHomework.title }}</h3>
                                </div>
                                <div class="text-right">
                                    <span class="text-[10px] text-slate-400 font-mono block">截止时间: {{ selectedHomework.deadline }}</span>
                                </div>
                            </div>

                            <!-- 题目选择面板 (Q1 / Q2 / Q3) -->
                            <div class="flex gap-2 mb-3">
                                <button v-for="(q, index) in selectedHomework.questions" :key="q.id"
                                    @click="switchQuestion(index)"
                                    class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                                    :class="activeQuestionIndex === index 
                                        ? 'bg-[#1c2b38] text-white border-[#1c2b38] shadow-sm'
                                        : 'bg-white/80 text-slate-600 border-slate-200 hover:bg-white'">
                                    {{ index + 1 }}. {{ q.type === 'choice' ? '选择题' : q.type === 'blank' ? '填空题' : q.type === 'programming' ? '编程题' : '简答题' }}
                                </button>
                            </div>
                        </section>

                        <!-- 多题型答题表单渲染 -->
                        <section v-if="activeQuestion" class="glass-panel-liquid p-6 flex flex-col gap-4">
                            <h4 class="text-xs font-bold text-slate-800 flex items-center gap-1">
                                <i class="ph ph-pencil-line text-base"></i> 题目要求与答题区
                            </h4>
                            
                            <!-- 1. 选择题 (Choice) -->
                            <div v-if="activeQuestion.type === 'choice'" class="flex flex-col gap-4">
                                <p class="text-sm font-semibold text-slate-700 leading-relaxed">{{ activeQuestion.title }}</p>
                                <div class="grid grid-cols-1 gap-3.5 mt-2">
                                    <button v-for="(opt, index) in activeQuestion.options" :key="opt"
                                        @click="selectChoice(activeQuestion.id, opt.match(/^[A-D]/) ? opt.charAt(0) : opt)"
                                        class="p-4 rounded-xl border text-left text-xs font-semibold transition-all duration-300 flex items-center gap-3"
                                        :class="(submittedAnswers[activeQuestion.id] === opt || submittedAnswers[activeQuestion.id] === opt.charAt(0))
                                            ? 'bg-[#1c2b38]/5 border-[#1c2b38] text-[#1c2b38] shadow-sm font-bold'
                                            : 'bg-white/50 border-slate-200 text-slate-600 hover:bg-white'">
                                        <div class="w-5 h-5 rounded-full border flex items-center justify-center text-[10px]"
                                            :class="(submittedAnswers[activeQuestion.id] === opt || submittedAnswers[activeQuestion.id] === opt.charAt(0)) ? 'border-[#1c2b38] bg-[#1c2b38] text-white' : 'border-slate-350'">
                                            {{ String.fromCharCode(65 + index) }}
                                        </div>
                                        <span>{{ opt.replace(/^[A-D][\.、]\s*/, '') }}</span>
                                    </button>
                                </div>
                            </div>

                            <!-- 2. 填空题 (Blank) -->
                            <div v-else-if="activeQuestion.type === 'blank'" class="flex flex-col gap-4">
                                <p class="text-sm font-semibold text-slate-700 leading-relaxed">{{ activeQuestion.title }}</p>
                                <div class="bg-white/40 border border-slate-200 rounded-2xl p-5 flex flex-col gap-4 mt-2">
                                    <div v-for="(ans, idx) in activeQuestion.correctAnswers" :key="idx" class="flex items-center gap-3">
                                        <span class="text-xs font-bold text-slate-500 w-16">填空第 ({{ idx + 1 }}) 空:</span>
                                        <input type="text" 
                                            v-model="submittedAnswers[activeQuestion.id + '_' + idx]"
                                            class="flex-1 bg-white border border-slate-250 text-slate-800 text-xs rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38] transition-all"
                                            placeholder="在此键入匹配答案..." />
                                    </div>
                                </div>
                            </div>

                            <!-- 3. 简答题 (Text) -->
                            <div v-else-if="activeQuestion.type === 'text'" class="flex flex-col gap-3">
                                <p class="text-sm font-semibold text-slate-700 leading-relaxed">{{ activeQuestion.title }}</p>
                                <p class="text-xs text-slate-400 leading-relaxed">{{ activeQuestion.desc }}</p>
                                <textarea v-model="submittedAnswers[activeQuestion.id]" rows="6"
                                    class="w-full mt-2 p-4 bg-white/60 border border-slate-250 rounded-2xl text-slate-700 text-xs focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38] outline-none transition-all resize-none font-mono"
                                    placeholder="在此处键入您的分析论证或推导过程..."></textarea>
                            </div>

                            <!-- 4. 编程算法题 (Programming) -->
                            <div v-else-if="activeQuestion.type === 'programming'" class="flex flex-col gap-4">
                                <div>
                                    <p class="text-sm font-semibold text-slate-700 leading-relaxed">{{ activeQuestion.title }}</p>
                                    <p class="text-xs text-slate-400 mt-1 leading-relaxed">{{ activeQuestion.desc }}</p>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] text-slate-400 font-mono">ONLINE EDITOR</span>
                                    <button @click="runCodeMock" :disabled="runTesting"
                                        class="px-4 py-1.5 bg-[#1c2b38] hover:bg-[#253645] text-white font-bold rounded-xl text-[10px] flex items-center gap-1.5 transition-all shadow-sm">
                                        <i :class="runTesting ? 'ph ph-spinner animate-spin' : 'ph ph-play-fill'"></i> 运行代码试调
                                    </button>
                                </div>
                                <div class="h-60 bg-[#1e1e1e] rounded-2xl overflow-hidden border border-slate-800 p-4">
                                    <textarea v-model="submittedAnswers[activeQuestion.id]"
                                        class="w-full h-full bg-[#1e1e1e] text-slate-200 font-mono text-xs outline-none resize-none border-0"></textarea>
                                </div>

                                <!-- 控制台 -->
                                <div class="border border-slate-200 bg-slate-50/50 rounded-2xl p-4 overflow-hidden h-[110px] flex flex-col">
                                    <div class="flex gap-4 border-b border-slate-200 pb-2 mb-2 text-[10px] font-bold text-slate-500">
                                        <span>测试控制台</span>
                                    </div>
                                    <div class="flex-1 overflow-y-auto font-mono text-[11px] text-slate-600 no-scrollbar">
                                        <p v-for="line in consoleLines" :key="line" class="py-0.5">{{ line }}</p>
                                        <p v-if="consoleLines.length === 0" class="text-slate-400">点击右上方“运行代码试调”查看测试用例评估结果。</p>
                                    </div>
                                </div>
                            </div>

                            <!-- 提交与会诊控制按钮 -->
                            <div class="flex gap-3 justify-end mt-4 pt-3 border-t border-slate-200/50">
                                <button @click="handleDiagnose" :disabled="diagnosing"
                                    class="px-5 py-2.5 rounded-xl border border-[#b91c1c] text-[#b91c1c] hover:bg-[#b91c1c]/5 font-bold text-xs flex items-center gap-1.5 transition-all shadow-sm">
                                    <i :class="diagnosing ? 'ph ph-spinner animate-spin' : 'ph ph-cpu'"></i> 联合智能会诊
                                </button>
                                <button @click="handleSubmit" :disabled="submitting"
                                    class="px-5 py-2.5 rounded-xl bg-[#1c2b38] hover:bg-[#253645] text-white font-bold text-xs flex items-center gap-1.5 transition-all shadow-sm">
                                    <i :class="submitting ? 'ph ph-spinner animate-spin' : 'ph ph-paper-plane-tilt'"></i> 递交科目作业
                                </button>
                            </div>
                        </section>

                        <!-- 多智能体协同诊断舱 - Modal 弹窗（脱离父容器层级，全屏遮罩居中显示） -->
                        <transition name="fade">
                            <div v-if="currentDiagnosis" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" @click.self="closeDiagnosis">
                                <div class="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 flex flex-col gap-5 border border-indigo-500/10">
                                    <!-- 头部 + 关闭按钮 -->
                                    <div class="flex items-center justify-between border-b border-slate-200 pb-4 sticky top-0 bg-white z-10 -mx-6 px-6 -mt-6 pt-6">
                                        <div class="flex items-center gap-2">
                                            <div class="w-8 h-8 rounded-lg bg-[#b91c1c]/10 text-[#b91c1c] flex items-center justify-center text-lg">
                                                <i class="ph ph-robot"></i>
                                            </div>
                                            <div>
                                                <h4 class="text-sm font-bold text-slate-800">多智能体协同评估舱</h4>
                                                <p class="text-xs text-slate-400">综合诊断 Q1-Q3 作答表现与知识覆盖</p>
                                            </div>
                                        </div>
                                        <button @click="closeDiagnosis" class="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-700 transition-colors shrink-0">
                                            <i class="ph ph-x text-lg"></i>
                                        </button>
                                    </div>

                                    <!-- 智能体卡片 + 雷达图 -->
                                    <div class="grid grid-cols-1 md:grid-cols-[1.2fr_0.8fr] gap-6">
                                        <div class="flex flex-col gap-4">
                                            <!-- Alina -->
                                            <div class="p-4 rounded-2xl bg-white/60 border border-slate-200/60 flex items-start gap-3">
                                                <div class="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">A</div>
                                                <div class="flex-1 min-w-0">
                                                    <div class="flex justify-between items-center mb-1">
                                                        <h5 class="text-xs font-bold text-slate-800">主规划师 Alina</h5>
                                                        <span class="text-xs text-blue-600 font-bold font-mono">{{ currentDiagnosis.scores.alina }}分</span>
                                                    </div>
                                                    <p class="text-xs text-slate-500 leading-relaxed">{{ currentDiagnosis.alinaMsg }}</p>
                                                </div>
                                            </div>
                                            <!-- CodeNinja -->
                                            <div class="p-4 rounded-2xl bg-white/60 border border-slate-200/60 flex items-start gap-3">
                                                <div class="w-8 h-8 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">C</div>
                                                <div class="flex-1 min-w-0">
                                                    <div class="flex justify-between items-center mb-1">
                                                        <h5 class="text-xs font-bold text-slate-800">代码专家 CodeNinja</h5>
                                                        <span class="text-xs text-emerald-600 font-bold font-mono">{{ currentDiagnosis.scores.codeninja }}分</span>
                                                    </div>
                                                    <p class="text-xs text-slate-500 leading-relaxed">{{ currentDiagnosis.codeninjaMsg }}</p>
                                                </div>
                                            </div>
                                            <!-- Prof. X -->
                                            <div class="p-4 rounded-2xl bg-white/60 border border-slate-200/60 flex items-start gap-3">
                                                <div class="w-8 h-8 rounded-full bg-purple-500 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">X</div>
                                                <div class="flex-1 min-w-0">
                                                    <div class="flex justify-between items-center mb-1">
                                                        <h5 class="text-xs font-bold text-slate-800">理论导师 Prof. X</h5>
                                                        <span class="text-xs text-purple-600 font-bold font-mono">{{ currentDiagnosis.scores.profx }}分</span>
                                                    </div>
                                                    <p class="text-xs text-slate-500 leading-relaxed">{{ currentDiagnosis.profxMsg }}</p>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- 极简雷达图 -->
                                        <div class="flex flex-col items-center justify-center bg-white/40 border border-white/60 rounded-2xl p-4 min-h-[260px]">
                                            <p class="text-[10px] text-slate-400 font-semibold mb-2 tracking-wider">诊断多维连线图</p>
                                            <radar-chart v-if="radarOption" :option="radarOption" class="w-full h-[220px]"></radar-chart>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </transition>

                        <!-- 教师批改反馈 -->
                        <transition name="fade">
                            <section v-if="selectedHomework.status === 'graded'" class="glass-panel-liquid p-6 flex flex-col gap-3 bg-emerald-50/20 border border-emerald-500/10">
                                <h3 class="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                                    <i class="ph ph-check-square-offset text-lg"></i> 教师最终阅卷评定
                                </h3>
                                <div class="flex items-center gap-4 py-2 border-b border-emerald-500/5">
                                    <span class="text-4xl font-extrabold text-emerald-700 tracking-tighter" style="font-family: 'Barlow Condensed', sans-serif;">{{ selectedHomework.grade }}</span>
                                    <div class="w-px h-8 bg-emerald-500/20"></div>
                                    <p class="text-xs text-slate-500">最终评分级别。由教师结合多智能体诊断进行最终审核后定稿发布。</p>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed italic mt-1 bg-white/60 p-3 rounded-xl border border-white">
                                    “ {{ selectedHomework.teacherComment || '暂无详细教师评语记录。' }} ”
                                </p>
                                <div v-if="selectedHomework.classInsight" class="bg-sky-50/70 border border-sky-100 rounded-xl p-3">
                                    <h4 class="text-[11px] font-bold text-sky-900 flex items-center gap-1">
                                        <i class="ph ph-lightbulb"></i> 本次作业共性提醒
                                    </h4>
                                    <p class="text-xs text-sky-800 leading-relaxed mt-1">{{ selectedHomework.classInsight }}</p>
                                </div>
                            </section>
                        </transition>
                    </main>
                </div>
            </div>
        </section>
    `
};
