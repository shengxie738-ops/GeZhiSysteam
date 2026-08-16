import { ref, computed, onMounted } from 'vue';
import { homeworkApi } from '../api/homework.js';
import LineChart from './LineChart.js';

export default {
    name: 'TeacherHomework',
    components: {
        LineChart
    },
    emits: ['show-toast'],
    setup(_, { emit }) {
        const loading = ref(true);
        const detailLoading = ref(false);
        const activeTab = ref('overview'); // overview, create, detail
        const detailMode = ref('student'); // student, diagnosis, report
        const overviewData = ref({ summary: {}, homeworks: [] });

        const selectedHomework = ref(null);
        const submissionList = ref([]);
        const activeSubmission = ref(null);
        const activeQuestionIndex = ref(0);
        const homeworkAnalysis = ref(null);
        const homeworkReport = ref(null);
        const reportGenerating = ref(false);
        const statusFilter = ref('all');
        const highlightedQuestionId = ref(null);

        const isSavingGrade = ref(false);
        const gradeLevel = ref('A');
        const teacherComment = ref('');

        const isSavingHw = ref(false);
        const hwForm = ref({
            title: '',
            subject: '数据结构与算法',
            type: 'milestone',
            deadline: '',
            knowledgeTags: '',
            antiCheat: false,
            blocks: []
        });

        const availableSubjects = ['数据结构与算法', '操作系统', '计算机网络', '计算机组成原理', '离散数学'];
        
        const addBlock = (type) => {
            const id = 'blk_' + Math.random().toString(36).substr(2, 9);
            if (type === 'ai_objective') {
                hwForm.value.blocks.push({ id, type, config: { qType: 'choice', count: 3, difficulty: 'medium' } });
            } else if (type === 'programming') {
                hwForm.value.blocks.push({ id, type, config: { count: 1, difficulty: 'hard', template: '' } });
            } else if (type === 'document') {
                hwForm.value.blocks.push({ id, type, config: { fileName: '实验指导书.pdf', rubric: '' } });
            }
        };

        const removeBlock = (index) => {
            hwForm.value.blocks.splice(index, 1);
        };
        
        const moveBlock = (index, direction) => {
            if (direction === 'up' && index > 0) {
                const temp = hwForm.value.blocks[index];
                hwForm.value.blocks[index] = hwForm.value.blocks[index - 1];
                hwForm.value.blocks[index - 1] = temp;
            } else if (direction === 'down' && index < hwForm.value.blocks.length - 1) {
                const temp = hwForm.value.blocks[index];
                hwForm.value.blocks[index] = hwForm.value.blocks[index + 1];
                hwForm.value.blocks[index + 1] = temp;
            }
        };

        const loadOverview = async () => {
            loading.value = true;
            try {
                overviewData.value = await homeworkApi.getTeacherHomeworkOverview();
            } catch (err) {
                emit('show-toast', '获取作业概览失败', 'error');
            } finally {
                loading.value = false;
            }
        };

        const loadDetailData = async (homeworkId) => {
            detailLoading.value = true;
            try {
                const [submissions, analysis] = await Promise.all([
                    homeworkApi.getHomeworkSubmissions(homeworkId),
                    homeworkApi.getHomeworkAnalysis(homeworkId)
                ]);
                submissionList.value = submissions;
                homeworkAnalysis.value = analysis;
                if (submissions.length > 0) {
                    selectSubmission(sortedSubmissions(submissions)[0]);
                } else {
                    activeSubmission.value = null;
                }
            } catch (err) {
                emit('show-toast', '获取作业详情失败', 'error');
            } finally {
                detailLoading.value = false;
            }
        };

        const openHomeworkDetail = async (hw) => {
            selectedHomework.value = hw;
            activeTab.value = 'detail';
            detailMode.value = 'student';
            activeSubmission.value = null;
            activeQuestionIndex.value = 0;
            homeworkReport.value = null;
            highlightedQuestionId.value = null;
            statusFilter.value = 'all';
            await loadDetailData(hw.id);
        };

        const backToOverview = () => {
            activeTab.value = 'overview';
            selectedHomework.value = null;
            activeSubmission.value = null;
            highlightedQuestionId.value = null;
        };

        const sortedSubmissions = (items) => {
            const statusWeight = { review: 0, pending: 1, graded: 2 };
            return [...items].sort((a, b) => {
                if (highlightedQuestionId.value) {
                    const aWrong = a.questionResults && a.questionResults[highlightedQuestionId.value] === false ? 0 : 1;
                    const bWrong = b.questionResults && b.questionResults[highlightedQuestionId.value] === false ? 0 : 1;
                    if (aWrong !== bWrong) return aWrong - bWrong;
                }
                const statusDiff = (statusWeight[a.status] ?? 3) - (statusWeight[b.status] ?? 3);
                if (statusDiff !== 0) return statusDiff;
                return (a.aiScore ?? 100) - (b.aiScore ?? 100);
            });
        };

        const filteredSubmissions = computed(() => {
            const filtered = statusFilter.value === 'all'
                ? submissionList.value
                : submissionList.value.filter((sub) => sub.status === statusFilter.value);
            return sortedSubmissions(filtered);
        });

        const selectedQuestions = computed(() => selectedHomework.value?.questions || []);

        const activeQuestion = computed(() => {
            return selectedQuestions.value[activeQuestionIndex.value] || null;
        });

        const pendingCount = computed(() => {
            return submissionList.value.filter((sub) => sub.status !== 'graded').length;
        });

        const selectSubmission = (sub) => {
            activeSubmission.value = sub;
            activeQuestionIndex.value = 0;
            gradeLevel.value = sub.grade || sub.recommendedGrade || 'A';
            teacherComment.value = sub.teacherComment || '';
            detailMode.value = 'student';
        };

        const switchQuestion = (index) => {
            activeQuestionIndex.value = index;
        };

        const focusQuestionStat = (stat) => {
            highlightedQuestionId.value = stat.id;
            detailMode.value = 'student';
            const target = submissionList.value.find((sub) => sub.questionResults && sub.questionResults[stat.id] === false);
            if (target) selectSubmission(target);
        };

        const clearQuestionHighlight = () => {
            highlightedQuestionId.value = null;
        };

        const generateReport = async () => {
            if (!selectedHomework.value || reportGenerating.value) return;
            reportGenerating.value = true;
            try {
                homeworkReport.value = await homeworkApi.generateHomeworkReport(selectedHomework.value.id);
                detailMode.value = 'report';
                emit('show-toast', 'AI作业报告已生成', 'success');
            } catch (err) {
                emit('show-toast', '生成作业报告失败', 'error');
            } finally {
                reportGenerating.value = false;
            }
        };

        const adoptAiFeedback = () => {
            if (!activeSubmission.value || !activeSubmission.value.diagnosis) {
                emit('show-toast', '该作业尚无智能体诊断记录', 'error');
                return;
            }
            gradeLevel.value = activeSubmission.value.recommendedGrade || 'B';
            const diag = activeSubmission.value.diagnosis;
            teacherComment.value = `[多智能体协同评估报告]
Alina反馈: ${diag.alinaMsg.replace('Alina建议：', '').replace('Alina诊断：', '')}
CodeNinja反馈: ${diag.codeninjaMsg.replace('CodeNinja建议：', '').replace('CodeNinja诊断：', '')}
Prof. X反馈: ${diag.profxMsg.replace('Prof. X建议：', '').replace('Prof. X诊断：', '')}
教师复核结论：建议评定为 ${gradeLevel.value} 级。`;
            emit('show-toast', '已采纳 AI 预批改得分与诊断意见', 'success');
        };

        const submitGrading = async () => {
            if (!activeSubmission.value || isSavingGrade.value) return;
            isSavingGrade.value = true;
            try {
                await homeworkApi.gradeHomework(activeSubmission.value.id, {
                    grade: gradeLevel.value,
                    comment: teacherComment.value,
                    classInsight: homeworkReport.value?.studentInsight || ''
                });
                const sub = submissionList.value.find((item) => item.id === activeSubmission.value.id);
                if (sub) {
                    sub.status = 'graded';
                    sub.grade = gradeLevel.value;
                    sub.teacherComment = teacherComment.value;
                }
                activeSubmission.value = sub || activeSubmission.value;
                await refreshAnalysisOnly();
                emit('show-toast', '批改发布成功，学生端反馈已同步', 'success');
            } catch (err) {
                emit('show-toast', '提交批改失败', 'error');
            } finally {
                isSavingGrade.value = false;
            }
        };

        const refreshAnalysisOnly = async () => {
            if (!selectedHomework.value) return;
            try {
                homeworkAnalysis.value = await homeworkApi.getHomeworkAnalysis(selectedHomework.value.id);
            } catch (err) {
                // 分析刷新失败不阻塞批改主流程。
            }
        };

        const handleCreateHw = async () => {
            if (isSavingHw.value) return;
            
            if (!hwForm.value.title.trim()) {
                emit('show-toast', '请输入作业标题', 'error');
                return;
            }
            if (hwForm.value.blocks.length === 0) {
                emit('show-toast', '请至少添加一个作业模块', 'error');
                return;
            }

            isSavingHw.value = true;
            try {
                const defaultDeadline = new Date();
                defaultDeadline.setDate(defaultDeadline.getDate() + 3);
                const deadlineStr = hwForm.value.deadline
                    ? new Date(hwForm.value.deadline).toLocaleString()
                    : defaultDeadline.toLocaleString();

                await homeworkApi.createHomework({
                    title: hwForm.value.title,
                    type: hwForm.value.type,
                    subject: hwForm.value.subject,
                    deadline: deadlineStr,
                    knowledgeTags: hwForm.value.knowledgeTags ? hwForm.value.knowledgeTags.split(',').map(s=>s.trim()) : [],
                    antiCheat: hwForm.value.antiCheat,
                    blocks: hwForm.value.blocks
                });

                emit('show-toast', '新混合式作业规划已下发至智能体网络', 'success');
                activeTab.value = 'overview';
                await loadOverview();
                
                hwForm.value = {
                    title: '',
                    subject: '数据结构与算法',
                    type: 'milestone',
                    deadline: '',
                    knowledgeTags: '',
                    antiCheat: false,
                    blocks: []
                };
            } catch (err) {
                emit('show-toast', '作业发布失败', 'error');
            } finally {
                isSavingHw.value = false;
            }
        };

        const getStudentAnswer = (q) => {
            if (!activeSubmission.value || !activeSubmission.value.answers || !q) return '-';
            const answers = activeSubmission.value.answers;
            if (q.type === 'choice') {
                return answers[q.id] || '未作答';
            }
            if (q.type === 'blank') {
                return q.correctAnswers.map((_, i) => `(${i + 1}) ${answers[`${q.id}_${i}`] || '未填'}`).join(' ； ');
            }
            return answers[q.id] || '未作答';
        };

        const getCorrectAnswerText = (q) => {
            if (!q) return '-';
            if (q.type === 'choice') return q.correctAnswer;
            if (q.type === 'blank') return q.correctAnswers.map((ans, idx) => `(${idx + 1}) ${ans}`).join(' ； ');
            if (q.type === 'programming') return '应包含 Proxy、Reflect.get / Reflect.set、track 与 trigger 的完整闭环';
            return '简答与分析设计类题，无唯一客观标准答案';
        };

        const statusText = (status) => {
            if (status === 'graded') return '已批改';
            if (status === 'review') return '需复核';
            return '待批改';
        };

        const statusClass = (status) => {
            if (status === 'graded') return 'bg-emerald-50 text-emerald-700 border border-emerald-100';
            if (status === 'review') return 'bg-rose-50 text-rose-700 border border-rose-100';
            return 'bg-amber-50 text-amber-700 border border-amber-100';
        };

        const resultClass = (result) => {
            return result
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                : 'bg-rose-50 text-rose-700 border border-rose-100';
        };

        const resultIcon = (result) => result ? 'ph ph-check' : 'ph ph-x';

        const formatSubmitTime = (value) => {
            if (!value) return '';
            const str = String(value).trim();
            // If it's already a human-readable string (like '1小时前', '刚刚'), return as-is
            if (!/^\d{4}-\d{2}-\d{2}/.test(str)) return str;
            try {
                const date = new Date(str);
                if (isNaN(date.getTime())) return str;
                const y = date.getFullYear();
                const mo = String(date.getMonth() + 1).padStart(2, '0');
                const d = String(date.getDate()).padStart(2, '0');
                const h = String(date.getHours()).padStart(2, '0');
                const mi = String(date.getMinutes()).padStart(2, '0');
                return `${y}-${mo}-${d} ${h}:${mi}`;
            } catch {
                return str;
            }
        };

        const activeAnswerCorrect = computed(() => {
            if (!activeSubmission.value || !activeQuestion.value) return null;
            return activeSubmission.value.questionResults?.[activeQuestion.value.id] ?? null;
        });

        const answerBoxClass = computed(() => {
            if (activeAnswerCorrect.value === false) {
                return 'bg-rose-50 text-rose-900 border-rose-200';
            }
            if (activeAnswerCorrect.value === true) {
                return 'bg-emerald-50 text-emerald-900 border-emerald-200';
            }
            return 'bg-slate-50 text-slate-700 border-slate-200';
        });

        const answerStateLabel = computed(() => {
            if (activeAnswerCorrect.value === false) return '学生实际作答 · 答错';
            if (activeAnswerCorrect.value === true) return '学生实际作答 · 答对';
            return '学生实际作答';
        });

        const answerStateIcon = computed(() => {
            if (activeAnswerCorrect.value === false) return 'ph ph-x-circle text-rose-600';
            if (activeAnswerCorrect.value === true) return 'ph ph-check-circle text-emerald-600';
            return 'ph ph-circle text-slate-400';
        });

        const typeLabel = (type) => {
            if (type === 'daily') return '日常Checkpoint';
            if (type === 'milestone') return '阶段Milestone';
            return '大项目Capstone';
        };

        const scoreText = (score) => {
            return score === null || score === undefined ? '-' : `${score}`;
        };

        const lineOption = computed(() => ({
            tooltip: { trigger: 'axis' },
            xAxis: {
                type: 'category',
                data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                axisLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.1)' } }
            },
            yAxis: {
                type: 'value',
                name: '提交率 (%)',
                max: 100,
                splitLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.08)' } }
            },
            series: [{
                name: '作业平均提交率',
                data: [42, 58, 65, 78, 85, 92, 96],
                type: 'line',
                smooth: true,
                itemStyle: { color: '#6366f1' },
                areaStyle: { color: 'rgba(99, 102, 241, 0.1)' }
            }]
        }));

        const thoughtGenealogy = computed(() => {
            if (!overviewData.value || !overviewData.value.homeworks) return null;
            // 获取当前最新作业的族谱数据（如果有的话）
            const hw = overviewData.value.homeworks[0];
            return hw ? hw.thoughtGenealogy : null;
        });

        const annotateBranch = (branch) => {
            emit('show-toast', `已由智能体 Prof.X 将针对 [${branch.name}] 的全局批注，定向推送至 ${branch.studentCount} 名学生的沙箱控制台。`, 'success');
        };

        onMounted(loadOverview);

        return {
            loading,
            detailLoading,
            activeTab,
            detailMode,
            overviewData,
            selectedHomework,
            submissionList,
            activeSubmission,
            activeQuestionIndex,
            homeworkAnalysis,
            homeworkReport,
            reportGenerating,
            statusFilter,
            highlightedQuestionId,
            isSavingGrade,
            gradeLevel,
            teacherComment,
            isSavingHw,
            hwForm,
            availableSubjects,
            addBlock,
            removeBlock,
            moveBlock,
            filteredSubmissions,
            selectedQuestions,
            activeQuestion,
            pendingCount,
            loadOverview,
            openHomeworkDetail,
            backToOverview,
            selectSubmission,
            switchQuestion,
            focusQuestionStat,
            clearQuestionHighlight,
            generateReport,
            adoptAiFeedback,
            submitGrading,
            handleCreateHw,
            getStudentAnswer,
            getCorrectAnswerText,
            statusText,
            statusClass,
            resultClass,
            resultIcon,
            activeAnswerCorrect,
            answerBoxClass,
            answerStateLabel,
            answerStateIcon,
            typeLabel,
            scoreText,
            lineOption,
            thoughtGenealogy,
            annotateBranch,
            formatSubmitTime
        };
    },
    template: `
        <section class="absolute inset-0 overflow-y-auto p-6 lg:p-8 bg-slate-50">
            <div class="max-w-7xl mx-auto flex flex-col gap-6">
                <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
                    <div>
                        <h2 class="text-2xl font-bold text-slate-800" style="font-family: 'Noto Serif SC', serif;">作业管理</h2>
                        <p class="text-sm text-slate-500 mt-1">先按作业查看班级提交，再进入学生答卷、AI 诊断与作业报告分析。</p>
                    </div>
                </div>

                <div class="flex flex-wrap gap-2">
                    <button @click="activeTab = 'overview'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]"
                        :class="activeTab === 'overview' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">作业总览</button>
                    <button @click="activeTab = 'create'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]"
                        :class="activeTab === 'create' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">布置新作业</button>
                    <button v-if="selectedHomework" @click="activeTab = 'detail'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]"
                        :class="activeTab === 'detail' ? 'bg-[#b91c1c] text-white border-[#b91c1c]' : 'bg-white text-slate-600 border-slate-200'">作业详情: {{ selectedHomework.title }}</button>
                </div>

                <div v-if="loading" class="bg-white border border-slate-200 shadow-sm p-8 text-xs text-slate-500">正在同步班级作业汇总...</div>

                <template v-else>
                    <div v-show="activeTab === 'overview'" class="flex flex-col gap-6">
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-[10px] text-slate-400 font-semibold tracking-wider">活跃作业排期</p>
                                <p class="text-3xl font-extrabold text-slate-800 mt-2 font-mono" style="font-family: 'Barlow Condensed', sans-serif;">{{ overviewData.summary.activeHomeworks }}</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-[10px] text-slate-400 font-semibold tracking-wider">已接收提交</p>
                                <p class="text-3xl font-extrabold text-slate-800 mt-2 font-mono" style="font-family: 'Barlow Condensed', sans-serif;">{{ overviewData.summary.totalSubmissions }}</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                <p class="text-[10px] text-slate-400 font-semibold tracking-wider">待批改份数</p>
                                <p class="text-3xl font-extrabold text-rose-600 mt-2 font-mono" style="font-family: 'Barlow Condensed', sans-serif;">{{ overviewData.summary.pendingGrading }}</p>
                            </div>
                            <div class="bg-[#1c2b38] text-white rounded-2xl p-5 shadow-md">
                                <p class="text-[10px] text-white/60 font-semibold tracking-wider">智能诊断平均分</p>
                                <p class="text-3xl font-extrabold mt-2 font-mono text-[#00e5ff]" style="font-family: 'Barlow Condensed', sans-serif;">{{ overviewData.summary.averageAiScore }}%</p>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-6">
                            <div class="bg-white border border-slate-200 shadow-sm p-6">
                                <div class="flex items-center justify-between mb-5">
                                    <h3 class="text-lg font-bold text-slate-800">作业标题列表</h3>
                                    <button @click="loadOverview" class="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]"><i class="ph ph-arrow-clockwise"></i></button>
                                </div>
                                <div class="overflow-x-auto">
                                    <table class="w-full text-left text-sm border-collapse">
                                        <thead class="text-slate-500 font-semibold border-b border-slate-200">
                                            <tr>
                                                <th class="py-3 px-2 min-w-[240px]">作业标题</th>
                                                <th class="py-3 px-2">类别</th>
                                                <th class="py-3 px-2">提交进度</th>
                                                <th class="py-3 px-2">批改进度</th>
                                                <th class="py-3 px-2">AI均分</th>
                                                <th class="py-3 px-2 min-w-[130px]">最高错误率题</th>
                                                <th class="py-3 px-2 text-center">操作</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="hw in overviewData.homeworks" :key="hw.id" class="border-b border-slate-100 hover:bg-slate-50/60 transition-colors">
                                                <td class="py-3 px-2">
                                                    <p class="font-bold text-slate-800 line-clamp-2">{{ hw.title }}</p>
                                                    <p class="text-xs text-slate-500 mt-0.5">{{ hw.subject }} · 截止 {{ hw.deadline }}</p>
                                                </td>
                                                <td class="py-3 px-2">
                                                    <span class="text-[11px] font-bold px-2 py-0.5 rounded-full"
                                                        :class="hw.type === 'daily' ? 'bg-blue-50 text-blue-700 border border-blue-100' : hw.type === 'milestone' ? 'bg-purple-50 text-purple-700 border border-purple-100' : 'bg-amber-50 text-amber-700 border border-amber-100'">
                                                        {{ typeLabel(hw.type) }}
                                                    </span>
                                                </td>
                                                <td class="py-3 px-2 font-mono text-slate-700">{{ hw.totalCount }} / {{ hw.classSize }}</td>
                                                <td class="py-3 px-2 text-slate-600">{{ hw.gradedCount }} / {{ hw.totalCount }}</td>
                                                <td class="py-3 px-2 font-mono text-slate-800">{{ hw.averageAiScore || '-' }}</td>
                                                <td class="py-3 px-2 text-slate-600">
                                                    <span v-if="hw.topErrorQuestion">{{ hw.topErrorQuestion.label }} · {{ hw.topErrorQuestion.errorRate }}%错误</span>
                                                    <span v-else class="text-slate-400">暂无提交</span>
                                                </td>
                                                <td class="py-3 px-2 text-center">
                                                    <button @click="openHomeworkDetail(hw)" class="px-3 py-2 bg-[#1c2b38] hover:bg-[#253645] active:bg-[#111c25] text-white font-bold rounded-lg text-xs transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]">
                                                        查看详情
                                                    </button>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <aside class="flex flex-col gap-6">
                                <div class="bg-white border border-slate-200 shadow-sm p-5 flex flex-col">
                                    <h4 class="text-xs font-bold text-slate-800 mb-4">学情提交率趋势</h4>
                                    <line-chart :option="lineOption" class="w-full h-[180px]"></line-chart>
                                </div>
                                <div class="bg-white border border-slate-200 shadow-sm p-5 flex flex-col">
                                    <div class="flex items-center justify-between mb-4">
                                        <h4 class="text-xs font-bold text-slate-800 flex items-center gap-1.5"><i class="ph ph-git-branch text-[#1c2b38] text-lg"></i> AI 智能思路族谱</h4>
                                    </div>
                                    <div v-if="!thoughtGenealogy" class="text-xs text-slate-400 py-6 text-center">正在进行 AST 分析与聚类...</div>
                                    <div v-else class="flex flex-col">
                                        <h5 class="text-[11px] font-bold text-slate-500 mb-2">{{ thoughtGenealogy.questionTitle }}</h5>
                                        <div class="relative pl-4 border-l-2 border-slate-200 ml-2 mt-2 flex flex-col gap-5">
                                            <div v-for="branch in thoughtGenealogy.branches" :key="branch.id" class="relative">
                                                <div class="absolute w-4 h-0.5 bg-slate-200 -left-4 top-4"></div>
                                                <div class="absolute w-2.5 h-2.5 rounded-full border-2 border-white -left-[21px] top-3" :class="branch.type === 'correct' ? 'bg-emerald-500' : 'bg-rose-500'"></div>
                                                
                                                <div class="border border-slate-100 rounded-xl overflow-hidden bg-white/60 p-3 shadow-sm hover:border-[#1c2b38]/20 transition-colors">
                                                    <div class="flex items-center justify-between">
                                                        <h5 class="text-xs font-bold text-slate-800">{{ branch.name }}</h5>
                                                        <span class="text-[10px] font-bold font-mono px-2 py-0.5 rounded" :class="branch.type === 'correct' ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'">{{ branch.percentage }}% ({{ branch.studentCount }}人)</span>
                                                    </div>
                                                    <p class="text-[11px] text-slate-500 mt-1 leading-relaxed">{{ branch.desc }}</p>
                                                    <div v-if="branch.sampleCode" class="mt-2 bg-[#1c2b38] text-slate-300 p-2 text-[10px] font-mono rounded overflow-x-auto">
                                                        <pre><code>{{ branch.sampleCode }}</code></pre>
                                                    </div>
                                                    <div v-if="branch.type === 'flawed'" class="mt-2 pt-2 border-t border-slate-100">
                                                        <button @click="annotateBranch(branch)" class="w-full text-[11px] font-bold text-[#1c2b38] hover:text-white bg-slate-50 hover:bg-[#1c2b38] border border-slate-200 hover:border-[#1c2b38] transition-colors py-1.5 rounded flex items-center justify-center gap-1.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]">
                                                            <i class="ph ph-chat-teardrop-text"></i> 一键下发全局批注
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </div>

                    <form v-show="activeTab === 'create'" @submit.prevent="handleCreateHw" class="flex flex-col gap-6 max-w-4xl mx-auto w-full">
                        <div class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col gap-5">
                            <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                                <h3 class="text-base font-bold text-slate-800 flex items-center gap-1.5">
                                    <i class="ph ph-file-plus text-lg"></i> 画布式作业构建
                                </h3>
                                <div class="flex items-center gap-2">
                                    <label class="flex items-center gap-1.5 cursor-pointer text-xs font-bold" :class="hwForm.antiCheat ? 'text-[#1c2b38]' : 'text-slate-500'">
                                        <div class="relative inline-flex items-center h-4 w-7 rounded-full transition-colors" :class="hwForm.antiCheat ? 'bg-[#1c2b38]' : 'bg-slate-300'">
                                            <span class="inline-block w-3 h-3 transform bg-white rounded-full transition-transform" :class="hwForm.antiCheat ? 'translate-x-3.5' : 'translate-x-0.5'"></span>
                                        </div>
                                        <input type="checkbox" v-model="hwForm.antiCheat" class="sr-only" />
                                        千人千卷防作弊
                                    </label>
                                </div>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div class="md:col-span-2">
                                    <label class="block text-[11px] font-bold text-slate-500 mb-1">作业标题</label>
                                    <input v-model="hwForm.title" placeholder="例如：第四章 树与二叉树综合测验" required class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38]" />
                                </div>
                                <div>
                                    <label class="block text-[11px] font-bold text-slate-500 mb-1">学科归属</label>
                                    <select v-model="hwForm.subject" required class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38]">
                                        <option v-for="sub in availableSubjects" :key="sub" :value="sub">{{ sub }}</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[11px] font-bold text-slate-500 mb-1">作业类别</label>
                                    <select v-model="hwForm.type" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38]">
                                        <option value="daily">日常 Checkpoint</option>
                                        <option value="milestone">阶段 Milestone</option>
                                        <option value="capstone">大作业 Capstone</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[11px] font-bold text-slate-500 mb-1">截止日期 (可选)</label>
                                    <input v-model="hwForm.deadline" type="datetime-local" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38]" />
                                </div>
                                <div>
                                    <label class="block text-[11px] font-bold text-slate-500 mb-1">全局挂载知识点</label>
                                    <div class="relative">
                                        <input placeholder="多知识点以逗号分隔" v-model="hwForm.knowledgeTags" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38]" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="flex flex-col gap-4">
                            <div v-if="hwForm.blocks.length === 0" class="border-2 border-dashed border-slate-200 rounded-2xl p-12 text-center bg-white/30 flex flex-col items-center justify-center">
                                <div class="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center text-slate-400 text-xl mb-3">
                                    <i class="ph ph-squares-four"></i>
                                </div>
                                <h4 class="text-sm font-bold text-slate-700">画布是空的</h4>
                                <p class="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">使用下方工具栏添加 AI 出题、编程沙箱或文档上传模块，构建混合式作业体系。</p>
                            </div>

                            <transition-group name="list" tag="div" class="flex flex-col gap-4">
                                <div v-for="(block, index) in hwForm.blocks" :key="block.id" class="bg-white border border-slate-200 shadow-sm relative group flex overflow-hidden">
                                    <div class="w-8 shrink-0 bg-slate-50/80 border-r border-slate-100 flex flex-col items-center py-3 gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button type="button" @click.prevent="moveBlock(index, 'up')" :disabled="index === 0" class="text-slate-400 hover:text-[#1c2b38] disabled:opacity-30"><i class="ph ph-caret-up"></i></button>
                                        <span class="text-[9px] font-bold text-slate-400 font-mono">{{ index + 1 }}</span>
                                        <button type="button" @click.prevent="moveBlock(index, 'down')" :disabled="index === hwForm.blocks.length - 1" class="text-slate-400 hover:text-[#1c2b38] disabled:opacity-30"><i class="ph ph-caret-down"></i></button>
                                    </div>
                                    
                                    <div class="flex-1 p-5">
                                        <div class="flex items-start justify-between mb-4">
                                            <div class="flex items-center gap-2">
                                                <span v-if="block.type === 'ai_objective'" class="w-6 h-6 rounded-md bg-purple-50 text-purple-600 flex items-center justify-center"><i class="ph ph-magic-wand"></i></span>
                                                <span v-else-if="block.type === 'programming'" class="w-6 h-6 rounded-md bg-sky-50 text-sky-600 flex items-center justify-center"><i class="ph ph-code"></i></span>
                                                <span v-else class="w-6 h-6 rounded-md bg-amber-50 text-amber-600 flex items-center justify-center"><i class="ph ph-file-doc"></i></span>
                                                
                                                <h4 class="text-xs font-bold text-slate-800">
                                                    {{ block.type === 'ai_objective' ? 'AI 智能客观题库' : block.type === 'programming' ? '编程实战沙箱' : '文档附件批改' }}
                                                </h4>
                                            </div>
                                            <button type="button" @click.prevent="removeBlock(index)" class="text-slate-400 hover:text-rose-600 transition-colors"><i class="ph ph-x"></i></button>
                                        </div>

                                        <div v-if="block.type === 'ai_objective'" class="grid grid-cols-3 gap-4">
                                            <div>
                                                <label class="block text-[10px] font-bold text-slate-500 mb-1">题型</label>
                                                <select v-model="block.config.qType" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg px-2.5 py-2 outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500">
                                                    <option value="choice">单项选择题</option>
                                                    <option value="blank">填空题</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label class="block text-[10px] font-bold text-slate-500 mb-1">生成数量 ({{ block.config.count }}道)</label>
                                                <input type="range" v-model.number="block.config.count" min="1" max="10" class="w-full mt-1 accent-purple-600" />
                                            </div>
                                            <div>
                                                <label class="block text-[10px] font-bold text-slate-500 mb-1">难度等级</label>
                                                <select v-model="block.config.difficulty" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg px-2.5 py-2 outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500">
                                                    <option value="easy">基础 (Easy)</option>
                                                    <option value="medium">进阶 (Medium)</option>
                                                    <option value="hard">挑战 (Hard)</option>
                                                </select>
                                            </div>
                                        </div>

                                        <div v-else-if="block.type === 'programming'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <label class="block text-[10px] font-bold text-slate-500 mb-1">题目数量 ({{ block.config.count }}道)</label>
                                                <input type="range" v-model.number="block.config.count" min="1" max="5" class="w-full mt-1 accent-sky-600" />
                                            </div>
                                            <div>
                                                <label class="block text-[10px] font-bold text-slate-500 mb-1">算法难度</label>
                                                <select v-model="block.config.difficulty" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg px-2.5 py-2 outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500">
                                                    <option value="easy">入门实现</option>
                                                    <option value="medium">核心算法</option>
                                                    <option value="hard">大厂真题</option>
                                                </select>
                                            </div>
                                            <div class="md:col-span-2">
                                                <label class="block text-[10px] font-bold text-slate-500 mb-1">启动代码模板 (可选)</label>
                                                <textarea v-model="block.config.template" placeholder="// 设定默认的类结构或函数签名，AI 将据此补全要求..." rows="2" class="w-full bg-slate-800 text-sky-300 font-mono text-xs rounded-lg px-3 py-2 outline-none resize-none"></textarea>
                                            </div>
                                        </div>

                                        <div v-else-if="block.type === 'document'" class="flex flex-col gap-3">
                                            <div class="border border-dashed border-slate-300 rounded-lg p-4 flex items-center justify-between bg-white/40">
                                                <div class="flex items-center gap-2">
                                                    <i class="ph ph-file-pdf text-rose-500 text-xl"></i>
                                                    <div>
                                                        <p class="text-xs font-bold text-slate-700">{{ block.config.fileName }}</p>
                                                        <p class="text-[10px] text-slate-400">模拟：文件已准备就绪</p>
                                                    </div>
                                                </div>
                                                <button type="button" class="px-3 py-1.5 bg-white border border-slate-200 rounded text-[10px] font-bold text-slate-600 hover:text-[#1c2b38] transition-colors">更换文件</button>
                                            </div>
                                            <div>
                                                <label class="block text-[10px] font-bold text-slate-500 mb-1">智能体阅卷评分细则 (Rubric)</label>
                                                <textarea v-model="block.config.rubric" placeholder="例如：1. 数据分析步骤完整（40分）；2. 图表规范（30分）；3. 结论合理（30分）" rows="2" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 resize-none"></textarea>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </transition-group>
                        </div>

                        <div class="sticky bottom-4 z-10 mx-auto w-max bg-white/80 backdrop-blur-md border border-slate-200 rounded-full shadow-lg shadow-slate-200/50 p-1.5 flex items-center gap-1.5">
                            <button type="button" @click.prevent="addBlock('ai_objective')" class="px-4 py-2 rounded-full flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:bg-purple-50 hover:text-purple-700 transition-colors">
                                <i class="ph ph-magic-wand"></i> AI客观题
                            </button>
                            <div class="w-px h-4 bg-slate-200"></div>
                            <button type="button" @click.prevent="addBlock('programming')" class="px-4 py-2 rounded-full flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:bg-sky-50 hover:text-sky-700 transition-colors">
                                <i class="ph ph-code"></i> 编程实战
                            </button>
                            <div class="w-px h-4 bg-slate-200"></div>
                            <button type="button" @click.prevent="addBlock('document')" class="px-4 py-2 rounded-full flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:bg-amber-50 hover:text-amber-700 transition-colors">
                                <i class="ph ph-file-doc"></i> 文档作业
                            </button>
                        </div>

                        <div class="flex justify-end border-t border-slate-200 pt-5 mt-2">
                            <button type="submit" :disabled="isSavingHw" class="px-6 py-2.5 bg-[#1c2b38] hover:bg-[#253645] text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-sm transition-all disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]">
                                <i :class="isSavingHw ? 'ph ph-spinner animate-spin' : 'ph ph-paper-plane-tilt'"></i> 生成并下发作业
                            </button>
                        </div>
                    </form>

                    <div v-show="activeTab === 'detail'" class="flex flex-col gap-6">
                        <section v-if="selectedHomework" class="bg-white border border-slate-200 shadow-sm p-5">
                            <div class="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                                <div class="flex items-start gap-3 min-w-0">
                                    <button @click="backToOverview" class="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-800 shrink-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]">
                                        <i class="ph ph-arrow-left"></i>
                                    </button>
                                    <div class="min-w-0">
                                        <p class="text-[10px] text-slate-500 font-mono">作业详情 · 截止 {{ selectedHomework.deadline }}</p>
                                        <h3 class="text-lg font-bold text-slate-800 leading-snug">{{ selectedHomework.title }}</h3>
                                    </div>
                                </div>
                                <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                                    <div class="bg-white/60 border border-white/80 rounded-xl px-3 py-2">
                                        <p class="text-[10px] text-slate-500">提交率</p>
                                        <p class="font-mono font-bold text-slate-800">{{ homeworkAnalysis?.submitRate || 0 }}%</p>
                                    </div>
                                    <div class="bg-white/60 border border-white/80 rounded-xl px-3 py-2">
                                        <p class="text-[10px] text-slate-500">待批改</p>
                                        <p class="font-mono font-bold text-rose-700">{{ pendingCount }}</p>
                                    </div>
                                    <div class="bg-white/60 border border-white/80 rounded-xl px-3 py-2">
                                        <p class="text-[10px] text-slate-500">AI均分</p>
                                        <p class="font-mono font-bold text-slate-800">{{ homeworkAnalysis?.averageAiScore || '-' }}</p>
                                    </div>
                                    <div class="bg-white/60 border border-white/80 rounded-xl px-3 py-2">
                                        <p class="text-[10px] text-slate-500">薄弱点</p>
                                        <p class="font-mono font-bold text-slate-800">{{ homeworkAnalysis?.weakKnowledgePoints?.length || 0 }}</p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <div v-if="detailLoading" class="bg-white border border-slate-200 shadow-sm p-8 text-xs text-slate-500">正在载入作业详情...</div>

                        <div v-else class="grid grid-cols-1 2xl:grid-cols-[520px_1fr] gap-6">
                            <aside class="bg-white border border-slate-200 shadow-sm p-5 flex flex-col gap-4 h-[680px]">
                                <div class="flex items-center justify-between gap-3">
                                    <h4 class="text-sm font-bold text-slate-800">学生答题情况</h4>
                                    <div class="flex gap-1 bg-white/60 border border-white/80 rounded-xl p-1">
                                        <button v-for="item in [{id:'all',label:'全部'}, {id:'pending',label:'待批'}, {id:'review',label:'复核'}, {id:'graded',label:'已阅'}]" :key="item.id"
                                            @click="statusFilter = item.id"
                                            class="px-2.5 py-1.5 rounded-lg text-[10px] font-bold transition-colors"
                                            :class="statusFilter === item.id ? 'bg-[#1c2b38] text-white' : 'text-slate-500 hover:text-slate-800'">
                                            {{ item.label }}
                                        </button>
                                    </div>
                                </div>
                                <div v-if="highlightedQuestionId" class="flex items-center justify-between bg-rose-50 border border-rose-100 rounded-xl px-3 py-2 text-[11px] text-rose-700">
                                    <span>正在优先查看 {{ highlightedQuestionId.toUpperCase() }} 答错学生</span>
                                    <button @click="clearQuestionHighlight" class="font-bold hover:text-rose-900">清除</button>
                                </div>
                                <div v-if="filteredSubmissions.length === 0" class="flex-1 flex items-center justify-center text-center text-xs text-slate-500">
                                    当前筛选下暂无学生提交。
                                </div>
                                <div v-else class="flex-1 overflow-y-auto -mx-1 pr-1 min-h-0">
                                    <table class="w-full text-left text-[11px] border-collapse">
                                        <thead class="text-slate-500 border-b border-slate-200">
                                            <tr>
                                                <th class="py-2 px-1">学生</th>
                                                <th class="py-2 px-1">状态</th>
                                                <th class="py-2 px-1">AI分</th>
                                                <th class="py-2 px-1" v-for="(q, idx) in selectedQuestions" :key="q.id">Q{{ idx + 1 }}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="sub in filteredSubmissions" :key="sub.id"
                                                @click="selectSubmission(sub)"
                                                class="border-b border-slate-100 cursor-pointer transition-colors"
                                                :class="activeSubmission && activeSubmission.id === sub.id ? 'bg-white' : 'hover:bg-white/50'">
                                                <td class="py-2.5 px-1 min-w-[100px]">
                                                    <p class="font-bold text-slate-800">{{ sub.studentName }}</p>
                                                    <p class="text-[9px] text-slate-400">{{ sub.className }} · {{ formatSubmitTime(sub.submittedAt) }}</p>
                                                </td>
                                                <td class="py-2.5 px-1">
                                                    <span class="px-2 py-0.5 rounded-full text-[9px] font-bold whitespace-nowrap" :class="statusClass(sub.status)">{{ statusText(sub.status) }}</span>
                                                </td>
                                                <td class="py-2.5 px-1 font-mono font-bold text-slate-700">{{ scoreText(sub.aiScore) }}</td>
                                                <td class="py-2.5 px-1" v-for="q in selectedQuestions" :key="q.id">
                                                    <span class="w-6 h-6 rounded-full flex items-center justify-center text-[10px]" :class="resultClass(sub.questionResults?.[q.id])">
                                                        <i :class="resultIcon(sub.questionResults?.[q.id])"></i>
                                                    </span>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </aside>

                            <main class="min-w-0 flex flex-col gap-4">
                                <div class="flex flex-wrap gap-2">
                                    <button @click="detailMode = 'student'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-colors"
                                        :class="detailMode === 'student' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">学生答卷</button>
                                    <button @click="detailMode = 'diagnosis'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-colors"
                                        :class="detailMode === 'diagnosis' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">AI诊断窗口</button>
                                    <button @click="detailMode = 'report'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-colors"
                                        :class="detailMode === 'report' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">AI作业报告</button>
                                    <button @click="generateReport" :disabled="reportGenerating || !submissionList.length" class="ml-auto px-4 py-2 rounded-xl text-xs font-bold border border-sky-200 text-sky-700 bg-sky-50 hover:bg-sky-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                                        <i :class="reportGenerating ? 'ph ph-spinner animate-spin' : 'ph ph-sparkle'"></i> 生成AI作业报告
                                    </button>
                                </div>

                                <section v-show="detailMode === 'student'" class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col gap-5">
                                    <div v-if="!activeSubmission" class="py-20 text-center text-xs text-slate-500">请选择左侧学生查看答卷。</div>
                                    <template v-else>
                                        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                                            <div>
                                                <p class="text-[10px] text-slate-500 font-mono">STUDENT SUBMISSION</p>
                                                <h4 class="text-base font-bold text-slate-800">{{ activeSubmission.studentName }} · {{ activeSubmission.homeworkTitle }}</h4>
                                                <p class="text-xs text-slate-500 mt-1">{{ activeSubmission.className }} · {{ formatSubmitTime(activeSubmission.submittedAt) }}</p>
                                            </div>
                                            <div class="flex items-center gap-2">
                                                <span class="px-2.5 py-1 rounded-full text-[10px] font-bold" :class="statusClass(activeSubmission.status)">{{ statusText(activeSubmission.status) }}</span>
                                                <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">AI {{ scoreText(activeSubmission.aiScore) }} / {{ activeSubmission.recommendedGrade }}</span>
                                            </div>
                                        </div>

                                        <div class="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
                                            <button v-for="(q, idx) in selectedQuestions" :key="q.id"
                                                @click="switchQuestion(idx)"
                                                class="px-3 py-2 rounded-lg text-[10px] font-bold border transition-all"
                                                :class="activeQuestionIndex === idx ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'">
                                                Q{{ idx + 1 }} · {{ q.type === 'choice' ? '选择' : q.type === 'blank' ? '填空' : q.type === 'programming' ? '编程' : '简答' }}
                                            </button>
                                        </div>

                                        <div v-if="activeQuestion" class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                                            <div class="flex flex-col gap-3">
                                                <div>
                                                    <span class="text-[10px] text-slate-500 font-bold">题目 {{ activeQuestionIndex + 1 }}</span>
                                                    <p class="text-xs font-bold text-slate-700 leading-relaxed mt-1">{{ activeQuestion.title }}</p>
                                                    <p v-if="activeQuestion.desc" class="text-[10px] text-slate-500 mt-1 leading-relaxed">{{ activeQuestion.desc }}</p>
                                                </div>
                                                <div class="p-3.5 rounded-xl font-mono text-xs border whitespace-pre-line overflow-auto max-h-[260px]" :class="answerBoxClass">
                                                    <span class="font-bold flex items-center gap-1.5 mb-1.5 select-none text-[10px]" :class="activeAnswerCorrect === false ? 'text-rose-700' : 'text-emerald-700'">
                                                        <i :class="answerStateIcon"></i> // {{ answerStateLabel }}
                                                    </span>
                                                    {{ getStudentAnswer(activeQuestion) }}
                                                </div>
                                                <div class="p-3.5 rounded-xl bg-emerald-50 text-emerald-900 font-mono text-xs border border-emerald-200">
                                                    <span class="text-emerald-700 font-bold flex items-center gap-1.5 mb-1.5 select-none text-[10px]">
                                                        <i class="ph ph-check-circle text-emerald-600"></i> // 参考答案
                                                    </span>
                                                    {{ getCorrectAnswerText(activeQuestion) }}
                                                </div>
                                            </div>

                                            <div class="flex flex-col gap-3">
                                                <div class="flex items-center justify-between">
                                                    <h5 class="text-xs font-bold text-slate-800 flex items-center gap-1"><i class="ph ph-cpu"></i> 学生 AI 诊断</h5>
                                                    <button @click="adoptAiFeedback" class="px-3 py-1.5 bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 rounded-lg text-[10px] font-bold transition-colors">
                                                        采纳AI意见
                                                    </button>
                                                </div>
                                                <div v-if="activeSubmission.diagnosis" class="flex flex-col gap-2 text-xs">
                                                    <div class="p-3 rounded-xl bg-blue-50/70 border border-blue-100">
                                                        <div class="flex justify-between font-semibold text-slate-700"><span>规划师 Alina</span><span>{{ activeSubmission.diagnosis.scores.alina }}分</span></div>
                                                        <p class="text-slate-600 leading-relaxed mt-1">{{ activeSubmission.diagnosis.alinaMsg }}</p>
                                                    </div>
                                                    <div class="p-3 rounded-xl bg-emerald-50/70 border border-emerald-100">
                                                        <div class="flex justify-between font-semibold text-slate-700"><span>代码专家 CodeNinja</span><span>{{ activeSubmission.diagnosis.scores.codeninja }}分</span></div>
                                                        <p class="text-slate-600 leading-relaxed mt-1">{{ activeSubmission.diagnosis.codeninjaMsg }}</p>
                                                    </div>
                                                    <div class="p-3 rounded-xl bg-purple-50/70 border border-purple-100">
                                                        <div class="flex justify-between font-semibold text-slate-700"><span>理论导师 Prof. X</span><span>{{ activeSubmission.diagnosis.scores.profx }}分</span></div>
                                                        <p class="text-slate-600 leading-relaxed mt-1">{{ activeSubmission.diagnosis.profxMsg }}</p>
                                                    </div>
                                                </div>
                                                <div v-else class="text-xs text-slate-500 py-8 text-center border border-dashed border-slate-200 rounded-xl">
                                                    该学生尚未触发智能体诊断。
                                                </div>
                                            </div>
                                        </div>

                                        <div class="border-t border-slate-200 pt-4 flex flex-col gap-4">
                                            <h5 class="text-xs font-bold text-slate-800 flex items-center gap-1">
                                                <i class="ph ph-check-square-offset"></i> 教师最终批改
                                            </h5>
                                            <div class="flex flex-col md:flex-row gap-4">
                                                <div class="md:w-48 shrink-0">
                                                    <label class="block text-xs font-semibold text-slate-600 mb-1">成绩评级</label>
                                                    <select v-model="gradeLevel" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38]">
                                                        <option value="A">A级 (优秀卓越)</option>
                                                        <option value="B">B级 (良好平稳)</option>
                                                        <option value="C">C级 (合格待进)</option>
                                                        <option value="D">D级 (勉强通过)</option>
                                                        <option value="E">E级 (尚需补做)</option>
                                                    </select>
                                                </div>
                                                <div class="flex-1">
                                                    <label class="block text-xs font-semibold text-slate-600 mb-1">教师寄语 / 批改总结评语</label>
                                                    <textarea v-model="teacherComment" rows="4" class="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38] resize-none" placeholder="输入最终讲评建议..."></textarea>
                                                </div>
                                            </div>
                                            <div class="flex justify-end">
                                                <button @click="submitGrading" :disabled="isSavingGrade" class="px-5 py-2.5 bg-[#b91c1c] hover:bg-[#991b1b] text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50">
                                                    <i :class="isSavingGrade ? 'ph ph-spinner animate-spin' : 'ph ph-floppy-disk'"></i> 发布成绩与反馈
                                                </button>
                                            </div>
                                        </div>
                                    </template>
                                </section>

                                <section v-show="detailMode === 'diagnosis'" class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col gap-5">
                                    <div class="flex items-start justify-between gap-4">
                                        <div>
                                            <p class="text-[10px] text-slate-500 font-mono">ASSIGNMENT AI DIAGNOSIS</p>
                                            <h4 class="text-base font-bold text-slate-800">本次作业错误率与薄弱知识点</h4>
                                        </div>
                                        <span class="px-3 py-1 rounded-full bg-white/70 border border-slate-200 text-[10px] text-slate-600">AI均分 {{ homeworkAnalysis?.averageAiScore || '-' }}</span>
                                    </div>
                                    <div v-if="!homeworkAnalysis || !homeworkAnalysis.questionStats.length" class="py-16 text-center text-xs text-slate-500">
                                        暂无可分析的提交数据。
                                    </div>
                                    <div v-else class="flex flex-col gap-3">
                                        <button v-for="stat in homeworkAnalysis.questionStats" :key="stat.id"
                                            @click="focusQuestionStat(stat)"
                                            class="text-left bg-white/60 hover:bg-white border border-white/80 rounded-xl p-4 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1c2b38]">
                                            <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2">
                                                <div class="min-w-0">
                                                    <div class="flex items-center gap-2">
                                                        <span class="font-mono text-xs font-bold text-[#b91c1c]">{{ stat.label }}</span>
                                                        <span class="text-xs font-bold text-slate-800">{{ stat.knowledgePoint }}</span>
                                                    </div>
                                                    <p class="text-xs text-slate-600 leading-relaxed mt-2">{{ stat.insight }}</p>
                                                    <p class="text-[10px] text-slate-500 mt-2">答错学生：{{ stat.wrongStudents.join('、') || '无' }}</p>
                                                </div>
                                                <div class="shrink-0 text-right">
                                                    <p class="text-2xl font-extrabold text-[#b91c1c] font-mono" style="font-family: 'Barlow Condensed', sans-serif;">{{ stat.errorRate }}%</p>
                                                    <p class="text-[10px] text-slate-500">{{ stat.wrongCount }} / {{ stat.totalCount }} 错误</p>
                                                </div>
                                            </div>
                                        </button>
                                    </div>
                                </section>

                                <section v-show="detailMode === 'report'" class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col gap-5">
                                    <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                                        <div>
                                            <p class="text-[10px] text-slate-500 font-mono">AI HOMEWORK REPORT</p>
                                            <h4 class="text-base font-bold text-slate-800">AI 作业报告分析</h4>
                                        </div>
                                        <button @click="generateReport" :disabled="reportGenerating || !submissionList.length" class="px-4 py-2 rounded-xl text-xs font-bold bg-[#1c2b38] text-white hover:bg-[#253645] disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                                            <i :class="reportGenerating ? 'ph ph-spinner animate-spin' : 'ph ph-sparkle'"></i> {{ homeworkReport ? '重新生成报告' : '生成报告' }}
                                        </button>
                                    </div>
                                    <div v-if="!homeworkReport" class="py-16 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl bg-white/30">
                                        点击“生成报告”后，将汇总本次作业错误率、薄弱知识点、分层建议和可回流学生端的共性提醒。
                                    </div>
                                    <template v-else>
                                        <div class="bg-white/60 border border-white/80 rounded-xl p-4">
                                            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                                                <div>
                                                    <h5 class="text-sm font-bold text-slate-800">{{ homeworkReport.title }}</h5>
                                                    <p class="text-xs text-slate-600 leading-relaxed mt-2">{{ homeworkReport.summary }}</p>
                                                </div>
                                                <span class="text-[10px] text-slate-500 font-mono whitespace-nowrap">{{ homeworkReport.generatedAt }}</span>
                                            </div>
                                        </div>
                                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
                                            <div class="bg-white/60 border border-white/80 rounded-xl p-3">
                                                <p class="text-[10px] text-slate-500">提交人数</p>
                                                <p class="text-lg font-bold font-mono text-slate-800">{{ homeworkReport.overview.submittedCount }} / {{ homeworkReport.overview.classSize }}</p>
                                            </div>
                                            <div class="bg-white/60 border border-white/80 rounded-xl p-3">
                                                <p class="text-[10px] text-slate-500">已批改</p>
                                                <p class="text-lg font-bold font-mono text-slate-800">{{ homeworkReport.overview.gradedCount }}</p>
                                            </div>
                                            <div class="bg-white/60 border border-white/80 rounded-xl p-3">
                                                <p class="text-[10px] text-slate-500">AI均分</p>
                                                <p class="text-lg font-bold font-mono text-slate-800">{{ homeworkReport.overview.averageAiScore }}</p>
                                            </div>
                                            <div class="bg-white/60 border border-white/80 rounded-xl p-3">
                                                <p class="text-[10px] text-slate-500">掌握判断</p>
                                                <p class="text-xs font-bold text-slate-800 leading-snug mt-1">{{ homeworkReport.overview.masteryLevel }}</p>
                                            </div>
                                        </div>
                                        <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                                            <div class="bg-white/60 border border-white/80 rounded-xl p-4">
                                                <h5 class="text-xs font-bold text-slate-800 mb-3">高错误率题目排行</h5>
                                                <div class="flex flex-col gap-2">
                                                    <div v-for="item in homeworkReport.topErrorQuestions" :key="item.id" class="flex items-start justify-between gap-3 text-xs border-b border-slate-100 last:border-0 pb-2 last:pb-0">
                                                        <div>
                                                            <p class="font-bold text-slate-800">{{ item.label }} · {{ item.knowledgePoint }}</p>
                                                            <p class="text-slate-500 leading-relaxed mt-1">{{ item.insight }}</p>
                                                        </div>
                                                        <span class="font-mono font-bold text-[#b91c1c] whitespace-nowrap">{{ item.errorRate }}%</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="bg-white/60 border border-white/80 rounded-xl p-4">
                                                <h5 class="text-xs font-bold text-slate-800 mb-3">教师讲解建议</h5>
                                                <ul class="flex flex-col gap-2 text-xs text-slate-600 leading-relaxed">
                                                    <li v-for="item in homeworkReport.teacherSuggestions" :key="item" class="flex gap-2">
                                                        <i class="ph ph-check-circle text-emerald-600 mt-0.5"></i>
                                                        <span>{{ item }}</span>
                                                    </li>
                                                </ul>
                                            </div>
                                        </div>
                                        <div class="bg-sky-50 border border-sky-100 rounded-xl p-4">
                                            <h5 class="text-xs font-bold text-sky-900 mb-2">可回流学生端的共性提醒</h5>
                                            <p class="text-xs text-sky-800 leading-relaxed">{{ homeworkReport.studentInsight }}</p>
                                        </div>
                                    </template>
                                </section>
                            </main>
                        </div>
                    </div>
                </template>
            </div>
        </section>
    `
};
