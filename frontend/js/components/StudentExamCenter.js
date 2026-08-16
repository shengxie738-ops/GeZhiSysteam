import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue';
import { examCenterApi } from '../api/examCenter.js';

const deepEqual = (a, b) => {
    if (a === undefined && b === undefined) return true;
    if (a === undefined || b === undefined) return false;
    return JSON.stringify(a) === JSON.stringify(b);
};

export default {
    name: 'StudentExamCenter',
    props: {
        currentUser: { type: Object, default: null }
    },
    emits: ['show-toast'],
    setup(props, { emit }) {
        const loading = ref(true);
        const overview = ref({ summary: {}, exams: [], waitingSubjects: [] });
        const selectedExam = ref(null);
        const examDetail = ref(null);
        const attemptId = ref(null);
        const roomMode = ref('overview');
        const activeProblemIndex = ref(0);
        const activeTab = ref('cases');
        const editorHost = ref(null);
        const isEditorLoading = ref(false);
        const usePlainEditor = ref(false);
        const isRunning = ref(false);
        const consoleLines = ref([]);
        const caseResults = ref([]);
        const submitting = ref(false);
        const pendingExam = ref(null);
        const isEntryConfirmOpen = ref(false);
        const isExitConfirmOpen = ref(false);
        const enteringExam = ref(false);
        const securityActive = ref(false);
        const securityViolationReason = ref('');
        const answers = ref({});
        const remainingSeconds = ref(0);
        let editor = null;
        let timer = null;
        let watermarkTimer = null;
        let securityListenersBound = false;
        let securityAutoSubmitting = false;
        let securityToastLocked = false;
        let blurViolationCount = 0;
        let lastBlurTime = null;
        const MAX_BLUR_VIOLATIONS = 3;
        const MAX_BLUR_DURATION_MS = 10000;
        const watermarkTime = ref(new Date().toISOString().replace('T', ' ').slice(0, 19));

        const securityRules = [
            {
                icon: 'ph-monitor',
                title: '确认后进入全屏',
                desc: '系统会先请求浏览器全屏，未进入全屏不会创建考试作答记录。'
            },
            {
                icon: 'ph-arrows-out-cardinal',
                title: '禁止切屏与退出全屏',
                desc: '切到其他窗口、页面隐藏、窗口失焦或退出全屏会自动交卷。'
            },
            {
                icon: 'ph-copy-simple',
                title: '禁用复制、粘贴和右键',
                desc: '考试中全局拦截复制、剪切、粘贴、右键菜单和常见快捷键。'
            },
            {
                icon: 'ph-camera-slash',
                title: '禁止截屏快捷键',
                desc: '系统会拦截 PrintScreen、打印、保存等浏览器可捕获的截屏相关操作。'
            }
        ];

        const username = computed(() => props.currentUser?.username || 'guest_user');
        const apiBase = computed(() => examCenterApi.getApiBase());

        const upcomingExams = computed(() => overview.value.exams.filter(item => item.status === 'upcoming'));
        const activeExams = computed(() => overview.value.exams.filter(item => item.status === 'active'));
        const completedExams = computed(() => overview.value.exams.filter(item => item.status === 'completed'));
        const programmingExam = computed(() => overview.value.exams.find(item => item.programming || item.questionTypes?.some(type => type.type === 'programming')));
        const activeProblem = computed(() => examDetail.value?.programmingProblems?.[activeProblemIndex.value] || null);

        const formatDateTime = (value) => {
            if (!value) return '-';
            return new Date(value).toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        };

        const countdownText = (startsAt) => {
            const diff = new Date(startsAt).getTime() - Date.now();
            if (diff <= 0) return '已开考';
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(minutes / 60);
            const rest = minutes % 60;
            return hours > 0 ? `${hours} 小时 ${rest} 分钟后开考` : `${rest} 分钟后开考`;
        };

        const formatDuration = (seconds) => {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        };

        const statusMeta = (status) => {
            const map = {
                upcoming: { label: '未开始', cls: 'bg-amber-50 text-amber-700 border-amber-100' },
                active: { label: '进行中', cls: 'bg-emerald-50 text-emerald-700 border-emerald-100' },
                completed: { label: '已完成', cls: 'bg-slate-100 text-slate-600 border-slate-200' }
            };
            return map[status] || { label: status, cls: 'bg-slate-100 text-slate-600 border-slate-200' };
        };

        const showRestrictedToast = (message) => {
            if (securityToastLocked) return;
            securityToastLocked = true;
            emit('show-toast', message, 'error');
            window.setTimeout(() => {
                securityToastLocked = false;
            }, 1400);
        };

        const preventRestrictedOperation = (event) => {
            if (!securityActive.value) return;
            event.preventDefault();
            event.stopPropagation();
            showRestrictedToast('考试期间已禁用复制、粘贴、右键和截屏快捷键');
        };

        const handleSecurityKeydown = (event) => {
            if (!securityActive.value) return;
            const key = (event.key || '').toLowerCase();
            const hasCommandModifier = event.ctrlKey || event.metaKey;
            const blockedShortcut = hasCommandModifier && ['a', 'c', 'p', 's', 'u', 'v', 'x'].includes(key);
            const blockedSystemKey = ['escape', 'f11', 'printscreen'].includes(key);
            const blockedAltTab = event.altKey && key === 'tab';

            if (blockedShortcut || blockedSystemKey || blockedAltTab) {
                event.preventDefault();
                event.stopPropagation();
                if (key === 'printscreen') {
                    navigator.clipboard?.writeText?.('').catch(() => {});
                }
                showRestrictedToast('考试期间已拦截受限快捷键');
            }
        };

        const handleVisibilityChange = () => {
            if (securityActive.value && document.visibilityState === 'hidden') {
                autoSubmitForSecurity('切换页面或窗口');
            }
        };

        const handleFullscreenChange = () => {
            if (securityActive.value && roomMode.value === 'programming' && !document.fullscreenElement) {
                autoSubmitForSecurity('退出全屏模式');
            }
        };

        const handleWindowBlur = (event) => {
            if (event && event.target !== window && event.target !== document) return;
            if (securityActive.value && roomMode.value === 'programming') {
                lastBlurTime = Date.now();
                blurViolationCount++;
            }
        };

        const handleWindowFocus = (event) => {
            if (event && event.target !== window && event.target !== document) return;
            if (!securityActive.value || roomMode.value !== 'programming' || !lastBlurTime) return;
            
            const blurDuration = Date.now() - lastBlurTime;
            lastBlurTime = null;

            if (blurDuration > MAX_BLUR_DURATION_MS) {
                autoSubmitForSecurity('切出考试界面超过 10 秒');
                return;
            }

            if (blurViolationCount >= MAX_BLUR_VIOLATIONS) {
                autoSubmitForSecurity(`累计切出考试界面 ${MAX_BLUR_VIOLATIONS} 次`);
                return;
            }

            showRestrictedToast(`警告：您已切出考试界面 ${blurViolationCount} 次，满 ${MAX_BLUR_VIOLATIONS} 次将自动交卷`);
        };

        const bindExamSecurityGuards = () => {
            securityActive.value = true;
            securityViolationReason.value = '';
            if (securityListenersBound) return;
            document.addEventListener('copy', preventRestrictedOperation, true);
            document.addEventListener('cut', preventRestrictedOperation, true);
            document.addEventListener('paste', preventRestrictedOperation, true);
            document.addEventListener('contextmenu', preventRestrictedOperation, true);
            document.addEventListener('keydown', handleSecurityKeydown, true);
            document.addEventListener('visibilitychange', handleVisibilityChange, true);
            document.addEventListener('fullscreenchange', handleFullscreenChange, true);
            window.addEventListener('blur', handleWindowBlur, false);
            window.addEventListener('focus', handleWindowFocus, false);
            securityListenersBound = true;
        };

        const unbindExamSecurityGuards = () => {
            securityActive.value = false;
            if (!securityListenersBound) return;
            document.removeEventListener('copy', preventRestrictedOperation, true);
            document.removeEventListener('cut', preventRestrictedOperation, true);
            document.removeEventListener('paste', preventRestrictedOperation, true);
            document.removeEventListener('contextmenu', preventRestrictedOperation, true);
            document.removeEventListener('keydown', handleSecurityKeydown, true);
            document.removeEventListener('visibilitychange', handleVisibilityChange, true);
            document.removeEventListener('fullscreenchange', handleFullscreenChange, true);
            window.removeEventListener('blur', handleWindowBlur, false);
            window.removeEventListener('focus', handleWindowFocus, false);
            securityListenersBound = false;
        };

        const exitFullscreenIfNeeded = async () => {
            if (document.fullscreenElement && document.exitFullscreen) {
                await document.exitFullscreen().catch(() => {});
            }
        };

        const requestExamFullscreen = async () => {
            if (document.fullscreenElement) return true;
            if (!document.documentElement?.requestFullscreen) {
                emit('show-toast', '当前浏览器不支持全屏模式，无法进入考试', 'error');
                return false;
            }

            try {
                await document.documentElement.requestFullscreen();
                return true;
            } catch (error) {
                emit('show-toast', '请允许浏览器进入全屏模式后再开始考试', 'error');
                return false;
            }
        };

        const requestExamEntry = (exam = programmingExam.value) => {
            if (!exam || enteringExam.value) return;
            pendingExam.value = exam;
            isEntryConfirmOpen.value = true;
            securityViolationReason.value = '';
        };

        const cancelExamEntry = () => {
            if (enteringExam.value) return;
            pendingExam.value = null;
            isEntryConfirmOpen.value = false;
        };

        const loadOverview = async () => {
            loading.value = true;
            try {
                overview.value = await examCenterApi.getStudentOverview(username.value);
            } catch (err) {
                emit('show-toast', `加载考试数据失败：${err.message}`, 'error');
            } finally {
                loading.value = false;
            }
        };

        const openExamDetail = async (exam) => {
            selectedExam.value = exam;
            try {
                examDetail.value = await examCenterApi.getExamDetail(exam.id, username.value);
                roomMode.value = 'detail';
                remainingSeconds.value = examDetail.value.remainingSeconds || exam.durationMinutes * 60;
            } catch (err) {
                emit('show-toast', `加载考试详情失败：${err.message}`, 'error');
            }
        };

        const ensureAttempt = async (exam) => {
            if (attemptId.value) return attemptId.value;
            try {
                const result = await examCenterApi.startExamAttempt(exam.id, {
                    userId: username.value,
                    clientStartedAt: new Date().toISOString()
                });
                attemptId.value = result.attemptId;
                return attemptId.value;
            } catch (err) {
                emit('show-toast', `创建考试作答记录失败：${err.message}`, 'error');
                return null;
            }
        };

        const enterProgrammingRoom = async (exam = programmingExam.value, options = {}) => {
            if (!exam) return;
            if (!options.confirmed) {
                requestExamEntry(exam);
                return;
            }
            selectedExam.value = exam;
            examDetail.value = await examCenterApi.getExamDetail(exam.id, username.value);
            await ensureAttempt(exam);
            roomMode.value = 'programming';
            remainingSeconds.value = examDetail.value.remainingSeconds || exam.durationMinutes * 60;
            activeProblemIndex.value = 0;
            bindExamSecurityGuards();
            initTimer();
            initCaseResults();
            await nextTick();
            initEditor();
        };

        const confirmExamEntry = async () => {
            const exam = pendingExam.value;
            if (!exam || enteringExam.value) return;
            enteringExam.value = true;
            try {
                const fullscreenReady = await requestExamFullscreen();
                if (!fullscreenReady) return;
                await enterProgrammingRoom(exam, { confirmed: true });
                isEntryConfirmOpen.value = false;
                pendingExam.value = null;
                emit('show-toast', '已进入全屏考试模式', 'success');
            } finally {
                enteringExam.value = false;
            }
        };

        const backToOverview = async (options = {}) => {
            unbindExamSecurityGuards();
            roomMode.value = 'overview';
            selectedExam.value = null;
            examDetail.value = null;
            destroyEditor();
            if (timer) clearInterval(timer);
            timer = null;
            if (options.exitFullscreen) {
                await exitFullscreenIfNeeded();
            }
        };

        const initTimer = () => {
            if (timer) clearInterval(timer);
            timer = setInterval(() => {
                remainingSeconds.value = Math.max(0, remainingSeconds.value - 1);
                if (remainingSeconds.value === 0) {
                    clearInterval(timer);
                    emit('show-toast', '考试时间已结束，系统正在自动交卷', 'error');
                    submitAttempt({ reason: '考试时间结束', autoSubmitted: true });
                }
            }, 1000);
        };

        const initCaseResults = () => {
            caseResults.value = (activeProblem.value?.publicCases || []).map(item => ({
                ...item,
                actual: null,
                status: 'pending',
                error: ''
            }));
            consoleLines.value = [];
        };

        const destroyEditor = () => {
            if (editor) {
                editor.dispose();
                editor = null;
            }
        };

        const getEditorCode = () => {
            if (editor) return editor.getValue();
            return answers.value[activeProblem.value?.id] || activeProblem.value?.starterCode || '';
        };

        const setEditorCode = (code) => {
            if (editor) editor.setValue(code);
            if (activeProblem.value) answers.value[activeProblem.value.id] = code;
        };

        const createEditor = () => {
            if (!editorHost.value || !activeProblem.value) return;
            destroyEditor();
            isEditorLoading.value = false;
            const saved = answers.value[activeProblem.value.id] || activeProblem.value.starterCode;
            if (window.monaco) {
                usePlainEditor.value = false;
                editor = window.monaco.editor.create(editorHost.value, {
                    value: saved,
                    language: activeProblem.value.language || 'javascript',
                    theme: 'vs-dark',
                    fontSize: 14,
                    minimap: { enabled: false },
                    automaticLayout: true,
                    scrollBeyondLastLine: false,
                    fontFamily: 'Consolas, "Courier New", monospace'
                });
                editor.onDidChangeModelContent(() => {
                    if (activeProblem.value) {
                        answers.value[activeProblem.value.id] = editor.getValue();
                    }
                });
            }
        };

        const initEditor = () => {
            if (!activeProblem.value) return;
            isEditorLoading.value = true;
            if (window.monaco) {
                createEditor();
                return;
            }
            if (window.require) {
                window.require.config({ paths: { vs: 'https://s4.zstatic.net/ajax/libs/monaco-editor/0.39.0/min/vs' } });
                window.require(['vs/editor/editor.main'], createEditor);
            } else {
                isEditorLoading.value = false;
                usePlainEditor.value = true;
            }
        };

        const switchProblem = async (index) => {
            if (activeProblem.value) answers.value[activeProblem.value.id] = getEditorCode();
            activeProblemIndex.value = index;
            initCaseResults();
            await nextTick();
            initEditor();
        };

        const runCode = async () => {
            if (!activeProblem.value || isRunning.value) return;
            isRunning.value = true;
            activeTab.value = 'cases';
            consoleLines.value = [];
            caseResults.value = caseResults.value.map(item => ({ ...item, status: 'running', actual: null, error: '' }));
            await nextTick();

            const code = getEditorCode();
            answers.value[activeProblem.value.id] = code;
            const logs = [];
            const fakeConsole = {
                log: (...items) => logs.push(items.map(item => typeof item === 'object' ? JSON.stringify(item) : String(item)).join(' '))
            };

            caseResults.value = caseResults.value.map((item) => {
                try {
                    let inputArgs = Array.isArray(item.input) ? item.input : [item.input];
                    const funcBody = `${code}; if (typeof ${activeProblem.value.funcName} !== 'function') throw new Error("函数 ${activeProblem.value.funcName} 未定义"); return ${activeProblem.value.funcName}(...arguments[1]);`;
                    const runner = new Function('console', funcBody);
                    const actual = runner(fakeConsole, inputArgs);
                    return {
                        ...item,
                        actual,
                        status: deepEqual(actual, item.expected) ? 'passed' : 'failed',
                        error: deepEqual(actual, item.expected) ? '' : `期望 ${JSON.stringify(item.expected)}`
                    };
                } catch (error) {
                    return { ...item, actual: null, status: 'error', error: error.toString() };
                }
            });

            consoleLines.value = logs.length ? logs : ['公开样例运行完成。隐藏用例将在正式提交后由后端判题。'];
            isRunning.value = false;
            const passed = caseResults.value.filter(item => item.status === 'passed').length;
            emit('show-toast', `公开样例通过 ${passed}/${caseResults.value.length}`, passed === caseResults.value.length ? 'success' : 'error');
            if (attemptId.value) {
                examCenterApi.saveAnswer(attemptId.value, {
                    questionId: activeProblem.value.id,
                    answer: code,
                    result: caseResults.value
                }).catch(() => { /* 静默失败，不影响编程题作答流程 */ });
            }
        };

        const submitAttempt = async (options = {}) => {
            if (!selectedExam.value || submitting.value) return;
            const reason = options.reason || '手动提交';
            const autoSubmitted = Boolean(options.autoSubmitted);
            submitting.value = true;
            if (activeProblem.value) answers.value[activeProblem.value.id] = getEditorCode();
            try {
                const id = await ensureAttempt(selectedExam.value);
                const result = await examCenterApi.submitAttempt(id, {
                    userId: username.value,
                    answers: answers.value,
                    submittedAt: new Date().toISOString(),
                    submitReason: reason,
                    autoSubmitted
                });
                let successMessage = autoSubmitted
                    ? `检测到${reason}，系统已自动交卷`
                    : (result.programmingStatus === 'pending_judge' ? '已提交，编程题正在自动判题...' : '考试提交成功');
                emit('show-toast', successMessage, autoSubmitted ? 'error' : 'success');

                // 如果有编程题待判，自动触发判题并展示结果
                if (result.programmingStatus === 'pending_judge' && id) {
                    try {
                        const judgeResult = await examCenterApi.judgeProgramming(id, {
                            userId: username.value
                        });
                        const progScore = judgeResult?.programmingScore ?? 0;
                        const totalScore = judgeResult?.totalScore ?? result?.objectiveScore ?? 0;
                        const passedCount = (judgeResult?.results || []).filter(r => r.status === 'accepted').length;
                        const totalCount = judgeResult?.results?.length || 0;
                        const judgeMsg = `判题完成：编程题 ${passedCount}/${totalCount} 通过，编程得分 ${progScore}，总分 ${totalScore}`;
                        emit('show-toast', judgeMsg, passedCount === totalCount ? 'success' : 'error');
                    } catch (judgeErr) {
                        emit('show-toast', `编程题自动判题失败：${judgeErr.message}，请稍后查看成绩`, 'error');
                    }
                }

                await backToOverview({ exitFullscreen: true });
                await loadOverview();
            } catch (error) {
                emit('show-toast', `提交失败：${error.message}`, 'error');
            } finally {
                submitting.value = false;
                securityAutoSubmitting = false;
            }
        };

        const autoSubmitForSecurity = async (reason) => {
            if (!securityActive.value || securityAutoSubmitting || submitting.value || roomMode.value !== 'programming') return;
            securityAutoSubmitting = true;
            securityViolationReason.value = reason;
            await submitAttempt({ autoSubmitted: true, reason });
        };

        onMounted(() => {
            loadOverview();
            watermarkTimer = setInterval(() => {
                watermarkTime.value = new Date().toISOString().replace('T', ' ').slice(0, 19);
            }, 1000);
        });
        onBeforeUnmount(() => {
            unbindExamSecurityGuards();
            destroyEditor();
            if (timer) clearInterval(timer);
            if (watermarkTimer) clearInterval(watermarkTimer);
        });

        return {
            loading,
            overview,
            selectedExam,
            examDetail,
            roomMode,
            activeProblemIndex,
            activeProblem,
            activeTab,
            editorHost,
            isEditorLoading,
            usePlainEditor,
            isRunning,
            consoleLines,
            caseResults,
            submitting,
            pendingExam,
            isEntryConfirmOpen,
            isExitConfirmOpen,
            enteringExam,
            securityActive,
            securityRules,
            securityViolationReason,
            answers,
            remainingSeconds,
            apiBase,
            upcomingExams,
            activeExams,
            completedExams,
            programmingExam,
            formatDateTime,
            countdownText,
            formatDuration,
            statusMeta,
            loadOverview,
            openExamDetail,
            requestExamEntry,
            cancelExamEntry,
            confirmExamEntry,
            enterProgrammingRoom,
            backToOverview,
            switchProblem,
            runCode,
            submitAttempt,
            autoSubmitForSecurity,
            getEditorCode,
            setEditorCode,
            watermarkTime,
            attemptId,
            username
        };
    },
    template: `
        <section class="absolute inset-0 overflow-hidden bg-slate-50">
            <div v-if="roomMode === 'overview'" class="h-full overflow-y-auto p-8 lg:p-10">
                <div class="max-w-7xl mx-auto flex flex-col gap-6">
                    <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
                        <div>
                            <h2 class="text-2xl font-bold text-slate-900" style="font-family: 'Noto Serif SC', serif;">考试中心</h2>
                            <p class="text-sm text-slate-500 mt-1">集中查看待考科目、考试时间、客观题与编程考试入口。</p>
                        </div>
                    </div>

                    <div v-if="loading" class="glass-panel-static p-8 text-sm text-slate-500">正在加载考试安排...</div>

                    <template v-else>
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                                <p class="text-xs text-slate-500">未开始考试</p>
                                <p class="text-3xl font-bold text-slate-900 mt-2">{{ overview.summary.upcoming }}</p>
                            </div>
                            <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                                <p class="text-xs text-slate-500">进行中</p>
                                <p class="text-3xl font-bold text-emerald-700 mt-2">{{ overview.summary.active }}</p>
                            </div>
                            <div class="bg-white/70 border border-white/80 rounded-2xl p-5">
                                <p class="text-xs text-slate-500">已完成</p>
                                <p class="text-3xl font-bold text-slate-700 mt-2">{{ overview.summary.completed }}</p>
                            </div>
                            <div class="bg-[#1c2b38] text-white rounded-2xl p-5">
                                <p class="text-xs text-white/70">编程考试入口</p>
                                <p class="text-3xl font-bold mt-2">{{ overview.summary.programming }}</p>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 xl:grid-cols-[1.25fr_0.75fr] gap-6">
                            <div class="glass-panel-static p-6">
                                <div class="flex items-center justify-between mb-5">
                                    <div>
                                        <h3 class="text-lg font-bold text-slate-900">考试项目</h3>
                                        <p class="text-xs text-slate-500 mt-1">开考时间、题型构成与进入状态</p>
                                    </div>
                                    <button @click="loadOverview" class="w-9 h-9 rounded-xl bg-white/70 border border-white flex items-center justify-center text-slate-600 hover:text-slate-900" title="刷新">
                                        <i class="ph ph-arrow-clockwise"></i>
                                    </button>
                                </div>

                                <div class="flex flex-col gap-3">
                                    <article v-for="exam in overview.exams" :key="exam.id" class="bg-white/62 border border-white/80 rounded-2xl p-4 flex flex-col lg:flex-row lg:items-center gap-4">
                                        <div class="flex-1 min-w-0">
                                            <div class="flex flex-wrap items-center gap-2 mb-2">
                                                <span class="text-[11px] font-bold px-2.5 py-1 rounded-full border" :class="statusMeta(exam.status).cls">{{ statusMeta(exam.status).label }}</span>
                                                <span class="text-[11px] text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">{{ exam.subject }}</span>
                                                <span v-if="exam.programming" class="text-[11px] text-[#b91c1c] bg-[#b91c1c]/10 px-2.5 py-1 rounded-full">编程考试</span>
                                            </div>
                                            <h4 class="font-bold text-slate-900 truncate">{{ exam.title }}</h4>
                                            <p class="text-xs text-slate-500 mt-1">{{ formatDateTime(exam.startsAt) }} · {{ exam.durationMinutes }} 分钟 · {{ exam.location }}</p>
                                            <div class="flex flex-wrap gap-2 mt-3">
                                                <span v-for="type in exam.questionTypes" :key="type.type" class="text-[11px] bg-slate-50 border border-slate-100 text-slate-600 px-2 py-1 rounded-lg">
                                                    {{ type.label }} {{ type.count }} 题 / {{ type.score }} 分
                                                </span>
                                            </div>
                                        </div>
                                        <div class="lg:w-48 flex lg:flex-col gap-2 lg:items-stretch">
                                            <div class="text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-100 rounded-xl px-3 py-2 text-center">
                                                {{ exam.status === 'upcoming' ? countdownText(exam.startsAt) : (exam.status === 'completed' ? '成绩 ' + (exam.score || '待发布') : '可进入考试') }}
                                            </div>
                                            <button v-if="exam.programming || exam.status === 'active'" @click="requestExamEntry(exam)" class="bg-[#1c2b38] text-white rounded-xl px-4 py-2 text-xs font-bold hover:bg-[#253645] flex items-center justify-center gap-1.5">
                                                <i class="ph ph-code-block"></i> 进入考试
                                            </button>
                                            <button v-else @click="openExamDetail(exam)" class="bg-white border border-slate-200 text-slate-700 rounded-xl px-4 py-2 text-xs font-bold hover:bg-slate-50">
                                                查看详情
                                            </button>
                                        </div>
                                    </article>
                                </div>
                            </div>

                            <aside class="flex flex-col gap-6">
                                <div class="glass-panel-static p-6">
                                    <h3 class="text-base font-bold text-slate-900 mb-4">待考科目</h3>
                                    <div class="flex flex-col gap-3">
                                        <div v-for="item in overview.waitingSubjects" :key="item.subject" class="flex items-start gap-3 pb-3 border-b border-white/50 last:border-0 last:pb-0">
                                            <div class="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center">
                                                <i class="ph ph-calendar-check"></i>
                                            </div>
                                            <div>
                                                <p class="text-sm font-bold text-slate-900">{{ item.subject }}</p>
                                                <p class="text-xs text-slate-500 mt-0.5">{{ item.time }} · {{ item.duration }}</p>
                                                <p class="text-[11px] text-slate-400 mt-1">{{ item.type }}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="bg-[#1c2b38] rounded-2xl p-6 text-white">
                                    <div class="flex items-center gap-3 mb-4">
                                        <div class="w-10 h-10 rounded-xl bg-white/12 flex items-center justify-center">
                                            <i class="ph ph-terminal-window text-xl"></i>
                                        </div>
                                        <div>
                                            <h3 class="font-bold">编程考试入口</h3>
                                            <p class="text-xs text-white/60">IDE、控制台、公开样例与正式提交</p>
                                        </div>
                                    </div>
                                    <button @click="requestExamEntry(programmingExam)" :disabled="!programmingExam" class="w-full bg-white text-[#1c2b38] rounded-xl px-4 py-3 text-sm font-bold disabled:opacity-50 flex items-center justify-center gap-2">
                                        <i class="ph ph-play"></i> 打开编程考试
                                    </button>
                                </div>
                            </aside>
                        </div>

                    </template>
                </div>
            </div>

            <div v-else-if="roomMode === 'detail'" class="h-full overflow-y-auto p-8 lg:p-10">
                <div class="max-w-4xl mx-auto glass-panel-static p-6">
                    <button @click="backToOverview" class="text-sm text-slate-500 hover:text-slate-900 flex items-center gap-1 mb-5">
                        <i class="ph ph-arrow-left"></i> 返回考试中心
                    </button>
                    <h2 class="text-2xl font-bold text-slate-900">{{ selectedExam.title }}</h2>
                    <p class="text-sm text-slate-500 mt-2">{{ selectedExam.subject }} · {{ formatDateTime(selectedExam.startsAt) }} · {{ selectedExam.durationMinutes }} 分钟</p>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6">
                        <div v-for="type in selectedExam.questionTypes" :key="type.type" class="bg-white/70 border border-white/80 rounded-2xl p-4">
                            <p class="text-xs text-slate-500">{{ type.label }}</p>
                            <p class="text-xl font-bold text-slate-900 mt-1">{{ type.count }} 题</p>
                            <p class="text-xs text-slate-400 mt-1">{{ type.score }} 分</p>
                        </div>
                    </div>
                    <div class="mt-6">
                        <h3 class="text-sm font-bold text-slate-800 mb-3">考试规则</h3>
                        <ul class="space-y-2">
                            <li v-for="rule in selectedExam.rules" :key="rule" class="text-sm text-slate-600 flex gap-2">
                                <i class="ph ph-check-circle text-emerald-600 mt-0.5"></i>{{ rule }}
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <teleport to="body" v-if="roomMode === 'programming'">
                <div class="fixed inset-0 z-[100] bg-slate-50 p-4 overflow-hidden flex flex-col gap-3">
                    <!-- 全屏防盗动态盲水印 -->
                    <div class="pointer-events-none fixed inset-0 z-[200] overflow-hidden opacity-5" aria-hidden="true">
                        <div class="w-[200%] h-[200%] flex flex-wrap gap-x-24 gap-y-16 -ml-32 -mt-32 -rotate-12 transform-gpu">
                            <div v-for="n in 150" :key="n" class="text-slate-900 font-bold whitespace-nowrap text-xl tracking-widest uppercase">
                                {{ username }} • {{ attemptId?.slice(0,8) || 'NO_ATTEMPT' }} • {{ watermarkTime }}
                            </div>
                        </div>
                    </div>
                <div class="bg-white border border-slate-200 rounded-2xl px-4 py-3 text-slate-800 shadow-sm relative z-10">
                    <div class="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3">
                        <div class="flex items-center gap-3 min-w-0">
                            <button @click="isExitConfirmOpen = true" class="w-10 h-10 rounded-xl border border-slate-200 bg-slate-50 text-slate-600 hover:text-slate-900 hover:bg-slate-100 flex items-center justify-center" title="退出并交卷">
                                <i class="ph ph-arrow-left"></i>
                            </button>
                            <div class="min-w-0">
                                <div class="flex flex-wrap items-center gap-2">
                                    <h2 class="font-bold truncate text-slate-900">{{ examDetail?.title }}</h2>
                                    <span class="text-[10px] px-2 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">全屏监考中</span>
                                    <span class="text-[10px] px-2 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200">违规退出自动交卷</span>
                                </div>
                                <p class="text-[11px] text-slate-500 mt-1">attemptId: {{ attemptId }} · 第 {{ activeProblemIndex + 1 }} / {{ examDetail?.programmingProblems?.length || 0 }} 题</p>
                            </div>
                        </div>

                        <div class="flex flex-wrap items-center gap-2">
                            <div class="h-10 px-4 rounded-xl bg-slate-50 border border-slate-100 text-slate-700 flex items-center gap-2 font-mono font-bold tracking-wide">
                                <i class="ph ph-clock text-lg"></i>
                                {{ formatDuration(remainingSeconds) }}
                            </div>
                            <button @click="submitAttempt({ reason: '手动提交' })" :disabled="submitting" class="h-10 px-4 rounded-xl bg-[#b91c1c] text-white text-sm font-bold flex items-center gap-2 disabled:opacity-60 hover:bg-[#991b1b]">
                                <i :class="submitting ? 'ph ph-spinner animate-spin' : 'ph ph-paper-plane-tilt'"></i> 提交试卷
                            </button>
                        </div>
                    </div>
                </div>

                <div v-if="securityViolationReason" class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-semibold text-rose-700 flex items-center gap-2">
                    <i class="ph ph-warning-circle"></i>
                    已触发安全规则：{{ securityViolationReason }}，系统正在自动交卷。
                </div>

                <div class="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-3">
                    <aside class="min-h-0 rounded-2xl border border-slate-200 bg-white p-4 flex flex-col gap-4 shadow-sm">
                        <div class="flex items-center justify-between gap-3">
                            <div>
                                <p class="text-[11px] text-slate-500 font-semibold">题目导航</p>
                                <h3 class="text-lg font-bold text-slate-900 mt-0.5">{{ activeProblem?.title }}</h3>
                            </div>
                            <span class="text-xs font-bold text-[#1c2b38] bg-[#1c2b38]/8 border border-[#1c2b38]/10 rounded-lg px-2.5 py-1">{{ activeProblem?.score }} 分</span>
                        </div>

                        <div class="grid grid-cols-3 gap-2">
                            <button v-for="(problem, idx) in examDetail?.programmingProblems" :key="problem.id" @click="switchProblem(idx)"
                                class="h-11 rounded-xl text-xs font-bold border flex items-center justify-center transition-colors"
                                :class="activeProblemIndex === idx ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-100'">
                                {{ idx + 1 }}
                            </button>
                        </div>

                        <div class="grid grid-cols-2 gap-2 text-[11px]">
                            <div class="rounded-xl bg-amber-50 border border-amber-100 px-3 py-2 text-amber-700">
                                <p class="font-bold">时间限制</p>
                                <p class="font-mono mt-1">{{ activeProblem?.timeLimitMs }} ms</p>
                            </div>
                            <div class="rounded-xl bg-sky-50 border border-sky-100 px-3 py-2 text-sky-700">
                                <p class="font-bold">内存限制</p>
                                <p class="font-mono mt-1">{{ activeProblem?.memoryLimitMb }} MB</p>
                            </div>
                        </div>

                        <div class="flex-1 overflow-y-auto no-scrollbar pr-1">
                            <p class="text-sm text-slate-700 leading-relaxed">{{ activeProblem?.description }}</p>
                            <div class="mt-5 space-y-3 text-xs">
                                <div class="rounded-xl bg-slate-50 p-3 border border-slate-100">
                                    <p class="font-bold text-slate-800 mb-1">输入</p>
                                    <p class="text-slate-500 font-mono break-words">{{ activeProblem?.inputHint }}</p>
                                </div>
                                <div class="rounded-xl bg-slate-50 p-3 border border-slate-100">
                                    <p class="font-bold text-slate-800 mb-1">输出</p>
                                    <p class="text-slate-500 font-mono break-words">{{ activeProblem?.outputHint }}</p>
                                </div>
                            </div>
                        </div>
                    </aside>

                    <main class="min-h-0 flex flex-col gap-3">
                        <div class="rounded-2xl border border-slate-200 bg-white flex-1 min-h-0 p-4 flex flex-col shadow-sm">
                            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
                                <div>
                                    <p class="text-[11px] text-slate-500 font-semibold">在线 IDE</p>
                                    <p class="text-sm font-bold text-slate-900 mt-0.5">{{ activeProblem?.language || 'javascript' }}</p>
                                </div>
                                <div class="flex items-center gap-2">
                                    <button @click="setEditorCode(activeProblem?.starterCode || '')" class="h-9 px-3 text-xs rounded-xl border border-slate-200 bg-white text-slate-600 hover:text-slate-900">重置</button>
                                    <button @click="runCode" :disabled="isRunning" class="h-9 px-4 text-xs rounded-xl bg-[#1c2b38] text-white font-bold flex items-center gap-1.5 disabled:opacity-60">
                                        <i :class="isRunning ? 'ph ph-spinner animate-spin' : 'ph ph-play-fill'"></i> 运行代码
                                    </button>
                                </div>
                            </div>
                            <div class="flex-1 min-h-[320px] bg-[#171717] rounded-2xl overflow-hidden border border-slate-900 relative">
                                <div ref="editorHost" class="absolute inset-0"></div>
                                <textarea v-if="usePlainEditor" :value="answers[activeProblem?.id] || activeProblem?.starterCode" @input="activeProblem && (answers[activeProblem.id] = $event.target.value)" class="absolute inset-0 w-full h-full bg-[#171717] text-slate-100 font-mono text-sm p-4 outline-none resize-none"></textarea>
                                <div v-if="isEditorLoading" class="absolute inset-0 flex items-center justify-center text-indigo-200 bg-slate-950/70 text-sm">正在加载 Monaco Editor...</div>
                            </div>
                        </div>

                        <div class="rounded-2xl border border-slate-200 bg-white h-[220px] p-4 flex flex-col overflow-hidden shadow-sm">
                            <div class="flex items-center justify-between border-b border-slate-200/70 mb-3">
                                <div class="flex gap-4 text-xs font-bold">
                                    <button @click="activeTab = 'cases'" :class="activeTab === 'cases' ? 'text-[#1c2b38] border-b-2 border-[#1c2b38]' : 'text-slate-500'" class="pb-2">公开样例</button>
                                    <button @click="activeTab = 'console'" :class="activeTab === 'console' ? 'text-[#1c2b38] border-b-2 border-[#1c2b38]' : 'text-slate-500'" class="pb-2">控制台</button>
                                </div>
                                <span class="text-[10px] text-slate-400 font-semibold pb-2">隐藏用例提交后判题</span>
                            </div>
                            <div class="flex-1 overflow-y-auto no-scrollbar">
                                <div v-show="activeTab === 'cases'" class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <div v-for="item in caseResults" :key="item.label" class="bg-slate-50 border border-slate-100 rounded-xl p-3 text-xs">
                                        <div class="flex items-center justify-between gap-2">
                                            <p class="font-bold text-slate-800">{{ item.label }}</p>
                                            <span class="px-2 py-1 rounded-lg text-[10px] font-bold" :class="item.status === 'passed' ? 'bg-emerald-50 text-emerald-700' : item.status === 'failed' || item.status === 'error' ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-500'">{{ item.status }}</span>
                                        </div>
                                        <p class="text-slate-500 mt-2 font-mono truncate">输入 {{ JSON.stringify(item.input) }}</p>
                                        <p class="text-slate-500 mt-1 font-mono truncate">期望 {{ JSON.stringify(item.expected) }}</p>
                                        <p v-if="item.actual !== null" class="text-slate-700 mt-1 font-mono truncate">输出 {{ JSON.stringify(item.actual) }}</p>
                                        <p v-if="item.error" class="text-rose-600 mt-1 font-mono truncate">{{ item.error }}</p>
                                    </div>
                                </div>
                                <div v-show="activeTab === 'console'" class="bg-slate-950 text-slate-300 rounded-xl p-3 font-mono text-xs min-h-full">
                                    <p v-for="(line, idx) in consoleLines" :key="idx" class="border-b border-slate-800/70 py-1">{{ line }}</p>
                                    <p v-if="consoleLines.length === 0" class="text-slate-500">运行代码后，这里会显示 console.log、运行错误和判题提示。</p>
                                </div>
                            </div>
                        </div>
                    </main>
                </div>
                </div>

                <div v-if="isExitConfirmOpen" class="fixed inset-0 z-[300] flex items-center justify-center bg-slate-900/40 px-4 backdrop-blur-sm">
                    <div class="w-full max-w-md rounded-2xl bg-white shadow-2xl overflow-hidden p-6 sm:p-8" role="dialog" aria-modal="true">
                        <div class="flex items-center justify-center w-16 h-16 rounded-full bg-rose-50 text-rose-600 mb-6 mx-auto">
                            <i class="ph ph-warning text-3xl"></i>
                        </div>
                        <h2 class="text-xl font-bold text-slate-900 text-center">考生注意！</h2>
                        <p class="text-sm text-slate-600 text-center mt-3 leading-relaxed">
                            点击退出考试页面，系统将<span class="font-bold text-rose-600">立刻交卷</span>。确认退出考试？请点击下方确认。
                        </p>
                        <div class="mt-8 flex flex-col sm:flex-row justify-center gap-3">
                            <button @click="isExitConfirmOpen = false" class="h-11 px-6 rounded-xl border border-slate-200 bg-white text-sm font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors flex-1">
                                取消，继续考试
                            </button>
                            <button @click="isExitConfirmOpen = false; autoSubmitForSecurity('主动退出考试')" class="h-11 px-6 rounded-xl bg-[#b91c1c] text-white text-sm font-bold hover:bg-[#991b1b] transition-colors flex-1">
                                确认退出
                            </button>
                        </div>
                    </div>
                </div>
            </teleport>

            <div v-if="isEntryConfirmOpen" class="absolute inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
                <div class="w-full max-w-2xl rounded-2xl bg-white shadow-2xl overflow-hidden" role="dialog" aria-modal="true" aria-labelledby="exam-entry-confirm-title">
                    <div class="p-6 sm:p-8">
                        <div class="flex items-start justify-between gap-4 mb-6">
                            <div>
                                <p class="text-xs font-bold text-slate-500 uppercase tracking-wider">考试安全确认</p>
                                <h2 id="exam-entry-confirm-title" class="text-2xl font-bold text-slate-900 mt-2">确定进入考试？</h2>
                                <p class="text-sm text-slate-600 mt-2">{{ pendingExam?.title }} · {{ pendingExam?.durationMinutes }} 分钟</p>
                            </div>
                            <div class="w-12 h-12 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center shrink-0">
                                <i class="ph ph-shield-warning text-2xl"></i>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div v-for="rule in securityRules" :key="rule.title" class="rounded-xl bg-slate-50 border border-slate-100 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-slate-700 shadow-sm flex items-center justify-center shrink-0">
                                    <i :class="'ph ' + rule.icon + ' text-lg'"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-900">{{ rule.title }}</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1.5">{{ rule.desc }}</p>
                                </div>
                            </div>
                        </div>

                        <div class="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-xs text-amber-800 leading-relaxed flex items-start gap-3">
                            <i class="ph ph-warning-circle text-lg shrink-0 mt-0.5"></i>
                            <div>
                                点击确认后，系统会立即请求全屏并创建考试作答记录。考试过程中如果退出全屏、切换页面、窗口失焦或主动返回，将自动提交当前答案。
                            </div>
                        </div>

                        <div class="mt-8 flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
                            <button @click="cancelExamEntry" :disabled="enteringExam" class="h-11 px-6 rounded-xl border border-slate-200 bg-white text-sm font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-60 transition-colors">
                                取消
                            </button>
                            <button @click="confirmExamEntry" :disabled="enteringExam" class="h-11 px-6 rounded-xl bg-[#b91c1c] text-white text-sm font-bold hover:bg-[#991b1b] disabled:opacity-60 flex items-center justify-center gap-2 transition-colors">
                                <i :class="enteringExam ? 'ph ph-spinner animate-spin' : 'ph ph-corners-out'"></i>
                                确认并进入全屏考试
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    `
};
