import { createApp, ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import RadarChart from './components/RadarChart.js';
import LineChart from './components/LineChart.js';
import GraphChart from './components/GraphChart.js';
import TreeChart from './components/TreeChart.js';
import CodingSandbox from './components/CodingSandbox.js?v=20260715';
import StudentExamCenter from './components/StudentExamCenter.js';
import StudentMistakeBook from './components/StudentMistakeBook.js';
import TeacherExamManager from './components/TeacherExamManager.js';
import StudentHomework from './components/StudentHomework.js?v=20260717_0100';
import TeacherHomework from './components/TeacherHomework.js';
import StudentAcademicSpace from './components/StudentAcademicSpace.js';
import StudentLearningDiagnosis from './components/StudentLearningDiagnosis.js';
import TeacherSpaceManager from './components/TeacherSpaceManager.js';
import TeacherAnalyticsCenter from './components/TeacherAnalyticsCenter.js';
import TeacherLearningDiagnosisReview from './components/TeacherLearningDiagnosisReview.js';
import TeacherCourseManager from './components/TeacherCourseManager.js';
import TeacherDashboard from './components/TeacherDashboard.js';
import TeacherProjectManager from './components/TeacherProjectManager.js?v=20260816_002';
import TeacherAiLessonPrep from './components/TeacherAiLessonPrep.js';
import { homeworkApi } from './api/homework.js';
import { examCenterApi } from './api/examCenter.js';
import { profileApi } from './api/profileApi.js';
import { getDashboardGreeting, getUserDisplayName } from './utils/dashboardGreeting.js';


// 导入自定义 Hooks
import { useToast } from './hooks/useToast.js';
import { useAuth } from './hooks/useAuth.js';
import { useChat } from './hooks/useChat.js';
import { useCourses } from './hooks/useCourses.js';
import { useMonitor } from './hooks/useMonitor.js';
import { useAgents } from './hooks/useAgents.js';
import { useProfile } from './hooks/useProfile.js';
import { useUserCenter } from './hooks/useUserCenter.js';
import { useDashboard } from './hooks/useDashboard.js';

import { courseMindmaps } from './data/mockData.js?v=20260620';
import { radarOptionTemplate, getLineOptionTemplate } from './config/chartOptions.js';

const app = createApp({
    components: {
        RadarChart,
        LineChart,
        GraphChart,
        TreeChart,
        CodingSandbox,
        StudentExamCenter,
        StudentMistakeBook,
        TeacherExamManager,
        StudentHomework,
        TeacherHomework,
        StudentAcademicSpace,
        StudentLearningDiagnosis,
        TeacherSpaceManager,
        TeacherAnalyticsCenter,
        TeacherLearningDiagnosisReview,
        TeacherCourseManager,
        TeacherDashboard,
        TeacherProjectManager,
        TeacherAiLessonPrep,
    },
    setup() {
        // 1. 全局提示 Hook
        const { toast, showToast } = useToast();


        // 2. 预声明 chat 变量以供闭包动态引用
        let chat = null;

        // 3. 登录/登出回调逻辑
        const onLoginSuccess = (username, role) => {
            if (chat && chat.messages.value.length === 0 && role === 'student') {
                const msg = `欢迎进入格至智能协同教育系统，**${username}**！我是您的主规划师 Alina。`;
                const id = Date.now();
                chat.messages.value.push({ id, senderType: 'agent', senderId: 'agent_planner', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), content: msg });
                chat.parsedHtmlCache[id] = (window.marked && window.marked.parse) ? window.marked.parse(msg) : msg;
            }
            // 登录后加载仪表盘真实数据
            if (role === 'student') {
                setTimeout(() => dashboardState.refreshDashboard(), 300);
            }
        };

        const onLogout = () => {
            if (chat) {
                chat.messages.value = [];
            }
            workspaceMode.value = null; // 重置工作台模式选择
        };

        // 4. 用户认证与导航 Hook
        const auth = useAuth(showToast, onLoginSuccess);

        // 5. 仿真监控 Hook (传入真实的响应式 currentRole 和 currentView)
        const profileRef = ref(null);
        const {
            studentRadarOption, activeTaskReasonId, agentLogs,
            toggleTaskReason, loadMyRadar
        } = useMonitor(auth.currentRole, auth.currentView, showToast, profileRef, auth.currentUser);

        // 6. 画像 Hook
        const profileState = useProfile(auth.currentUser, showToast);
        watch(profileState.profile, (newVal) => {
            profileRef.value = newVal;
        }, { deep: true, immediate: true });

        // 监听对话结束事件，延时拉取画像以实现“随学随新”
        if (typeof window !== 'undefined') {
            window.addEventListener('agent-log', () => {
                setTimeout(() => {
                    profileState.fetchProfile();
                }, 2000);
            });
        }

        // 7. 智能体工坊 Hook
        const agentsState = useAgents(showToast);

        // 8. 对话与知识库 Hook (赋值给预先声明的 chat 变量)
        chat = useChat(auth.currentUser, showToast, agentsState.getAgentInfo);

        // 9. 用户中心 Hook
        const userCenter = useUserCenter(auth.currentUser, showToast);

        // 10. 课程库与预览 Hook
        const coursesState = useCourses(chat.files, auth.currentView, showToast);

        // ================== 新增：工作台学习模式分流控制 ==================
        const workspaceMode = ref(null);
        const selectWorkspaceMode = (mode) => {
            workspaceMode.value = mode;
            chat.setAgentMode(mode);
            showToast(mode === 'rag' ? '已开启专属知识库检索模式' : '已进入多智能体协同引导式学习', 'success');
        };

        // ================== 仪表盘真实数据 Hook（替换原有静态 Mock 数据）==================
        const currentGoal = ref('理解并手写 Vue 3 的 reactive 响应式系统原理');
        const progress = ref(45);
        const showMiniprogramQR = ref(false);
        const tasks = ref([
            { id: 1, title: '阅读 Vue 3 官方响应式文档', status: 'done', completed: true, source: 'Alina', agent: 'Alina', reason: 'Alina建议：这是构建响应式心智模型的起点，建议先理清基本概念。' },
            { id: 2, title: '手写一个基础 Proxy 拦截器', status: 'doing', completed: false, source: 'CodeNinja', agent: 'CodeNinja', reason: 'CodeNinja建议：通过Proxy捕获get/set操作，是理解Vue3双向绑定的核心代码实践。' },
            { id: 3, title: '理解 track 与 trigger 依赖收集与触发机制', status: 'pending', completed: false, source: 'Prof. X', agent: 'Prof. X', reason: 'Prof. X建议：track用来收集依赖，trigger用来触发更新。这是设计模式中观察者模式的升级版。' }
        ]);

        const radarOption = ref(radarOptionTemplate);
        const lineOption = ref(getLineOptionTemplate());

        // ── 仪表盘 Hook（真实数据驱动）──
        const dashboardState = useDashboard(auth.currentUser);
        const {
            homeworkList, deadlines, examAlerts, errorPoints, errorNotebook,
            pendingHomeworkCount, submittedHomeworkCount,
            dashboardLoading, dashboardError,
            interventions, nudges, notifications, interactions,
            refreshDashboard, appendTeacherIntervention, completeInteractionTask
        } = dashboardState;

        // ── 非 API 静态数据（暂无后端端点，保留原有定义）──
        const liveSlots = ref([
            { id: 1, teacher: 'Prof. X', subject: '数据结构难点答疑：图的 DFS/BFS 与最小生成树', time: '10-28 19:00', booked: false },
            { id: 2, teacher: 'CodeNinja', subject: '手写代码特训：Vue 3 响应式系统与 Diff 算法精讲', time: '10-29 20:00', booked: true }
        ]);

        const courseNotes = ref([
            { id: 1, subject: '数据结构', title: '哈夫曼树构建与最优编码推导', preview: '哈夫曼树（Huffman Tree）又称最优二叉树，是一种带权路径长度最短的二叉树。构建步骤：1. 排序 2. 合并 3. 重复...', date: '10-26', wordCount: 1250, color: '#00e5ff' },
            { id: 2, subject: '高级前端程序设计', title: 'Vue 3 Proxy 拦截器与 Reflect 的配合使用', preview: '为什么在 Proxy 中一定要配合 Reflect 使用？Reflect 的作用是保证属性访问时的 receiver（即 this）指向正确的代理对象...', date: '10-24', wordCount: 840, color: '#6366f1' },
            { id: 3, subject: '人工智能技术基础', title: 'Transformer 中的 Self-Attention 机制推导', preview: '自注意力机制的核心公式为 Attention(Q, K, V) = softmax(QK^T / sqrt(d_k))V。其中 d_k 是键向量的维度...', date: '10-20', wordCount: 1560, color: '#10b981' }
        ]);

        const currentMoment = ref(new Date());
        const currentTime = ref('');
        const updateTime = () => {
            const now = new Date();
            currentMoment.value = now;
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            currentTime.value = `${hours}:${minutes}:${seconds}`;
        };
        const dashboardDisplayName = computed(() => getUserDisplayName(auth.currentUser.value));
        const dashboardGreeting = computed(() => getDashboardGreeting(currentMoment.value));

        const handleSwitchView = (e) => {
            if (e.detail) {
                auth.currentView.value = e.detail;
            }
        };

        const handleTeacherIntervention = (e) => {
            const { type, topic, payload = {}, recordId } = e.detail || {};
            const taskTitle = topic || payload.title || '教师下发学情任务';
            const subject = payload.subject || '数据结构与算法';
            const subjectId = payload.subjectId || 'GENERAL';
            const deadline = payload.deadline || '今天 23:59';
            const desc = payload.desc || '请根据教师端下发要求完成本次学习任务。';

            // 1. 实时更新仪表盘响应式状态（即时反馈，无需等待后端）
            appendTeacherIntervention({ type, title: taskTitle, subject, subjectId, deadline, desc });

            // 2. 向后端持久化干预记录，确保刷新后数据不丢失
            dashboardState.createTeacherIntervention({
                type,
                title: taskTitle,
                subject,
                subjectId,
                deadline,
                desc,
                recordId,
                targetUserId: auth.currentUser?.value?.username || '',
                teacherId: payload.teacherId || '',
                ...payload,
            }).catch(err => console.warn('[干预持久化失败]', err));

            // 3. 同步到原有 API（保持作业页面的兼容性）
            if (type === 'homework' || type === 'quiz') {
                homeworkApi.appendTeacherAssignedHomework({
                    ...payload, type, title: taskTitle, subject, deadline, recordId
                });
                showToast(`收到教师下发的${type === 'quiz' ? '短测' : '补弱作业'}：《${taskTitle}》`, 'warning');
            } else if (type === 'mistake') {
                examCenterApi.appendTeacherMistakeTask({
                    ...payload, title: taskTitle, subject, desc, recordId
                });
                showToast(`收到教师下发的错题订正：《${taskTitle}》`, 'warning');
            } else if (type === 'nudge' || type === 'ai-guide') {
                showToast(type === 'nudge' ? '收到教师学习提醒' : '收到 AI 个性化复习路径', 'info');
            }
        };


        let timeInterval = null;
        // 教师端课程库预览代理：转发 teacher-preview-file 事件给已有 previewFile 方法
        const handleTeacherPreviewFile = (e) => {
            if (e.detail) coursesState.previewFile(e.detail);
        };

        onMounted(() => {
            updateTime();
            timeInterval = setInterval(updateTime, 1000);
            window.addEventListener('switch-view', handleSwitchView);
            window.addEventListener('teacher-intervention-broadcast', handleTeacherIntervention);
            window.addEventListener('teacher-preview-file', handleTeacherPreviewFile);
            // 若用户已登录，立即加载仪表盘真实数据
            if (auth.isLoggedIn?.value && auth.currentRole?.value === 'student') {
                dashboardState.refreshDashboard();
            }
        });

        onUnmounted(() => {
            if (timeInterval) clearInterval(timeInterval);
            window.removeEventListener('switch-view', handleSwitchView);
            window.removeEventListener('teacher-intervention-broadcast', handleTeacherIntervention);
            window.removeEventListener('teacher-preview-file', handleTeacherPreviewFile);
        });

        const handlePreviewOrLearn = (res) => {
            coursesState.activeNodeDetails.value = null;
            const courseFiles = coursesState.courses.value.find(c => c.id === coursesState.selectedPathwayCourseId.value)?.files || [];
            const foundFile = courseFiles.find(f => f.name === res);
            if (foundFile) {
                coursesState.previewFile(foundFile);
            } else {
                chat.fillInput('我想学习这篇文献资源：' + res);
            }
        };

        // ================== 新增：Chat 代码块后处理器与自测题交互 ==================
        const processChatCodeBlocks = () => {
            nextTick(() => {
                const container = chat.chatContainer.value;
                if (!container) return;
                const pres = container.querySelectorAll('.markdown-body pre');
                pres.forEach(pre => {
                    if (pre.querySelector('.chat-code-actions')) return;

                    pre.classList.add('relative', 'group', 'overflow-visible');

                    const actionBar = document.createElement('div');
                    actionBar.className = 'chat-code-actions absolute right-2.5 top-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-all duration-300 z-30 select-none';

                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'px-2 py-1 bg-slate-950/80 text-white rounded text-[10px] font-bold flex items-center gap-1 hover:bg-slate-800 border border-slate-700 transition-all active:scale-95';
                    copyBtn.innerHTML = '<i class="ph ph-copy"></i> 复制';
                    copyBtn.onclick = (e) => {
                        e.stopPropagation();
                        const code = pre.querySelector('code')?.innerText || pre.innerText;
                        navigator.clipboard.writeText(code).then(() => {
                            showToast('代码已复制到剪贴板', 'success');
                        });
                    };

                    const importBtn = document.createElement('button');
                    importBtn.className = 'px-2 py-1 bg-violet-600 text-white rounded text-[10px] font-bold flex items-center gap-1 hover:bg-violet-700 border border-violet-500 transition-all active:scale-95';
                    importBtn.innerHTML = '<i class="ph ph-arrow-square-out"></i> 导入代码沙箱';
                    importBtn.onclick = (e) => {
                        e.stopPropagation();
                        const code = pre.querySelector('code')?.innerText || pre.innerText;
                        auth.currentView.value = 'coding';
                        setTimeout(() => {
                            window.dispatchEvent(new CustomEvent('import-code', { detail: code }));
                        }, 150);
                    };

                    actionBar.appendChild(copyBtn);
                    actionBar.appendChild(importBtn);
                    pre.appendChild(actionBar);
                });
            });
        };

        const processMermaidAndECharts = () => {
            nextTick(() => {
                const container = chat.chatContainer.value;
                if (!container) return;

                // 1. 动态查找并渲染 Mermaid.js 拓扑结构
                const mermaidBlocks = container.querySelectorAll('.markdown-body pre code.language-mermaid');
                mermaidBlocks.forEach(async (codeBlock, index) => {
                    const rawCode = codeBlock.innerText;
                    const preElement = codeBlock.parentElement;
                    const renderId = `mermaid-render-${Date.now()}-${index}`;

                    const wrapper = document.createElement('div');
                    wrapper.id = renderId;
                    wrapper.className = 'mermaid-chart-card my-4 p-4 rounded-xl bg-slate-900/90 border border-slate-700/50 flex flex-col items-center justify-center transition-all hover:border-violet-500/50 hover:shadow-lg overflow-x-auto w-full';
                    wrapper.innerHTML = `
                        <div class="flex items-center gap-2 mb-2 text-xs text-violet-400 font-bold self-start select-none">
                            <i class="ph ph-tree-structure"></i> 动态算法拓扑结构图
                        </div>
                        <div class="mermaid-svg-container w-full flex justify-center text-slate-100"></div>
                    `;

                    preElement.parentNode.replaceChild(wrapper, preElement);

                    try {
                        if (window.mermaid) {
                            const svgContainer = wrapper.querySelector('.mermaid-svg-container');
                            const { svg } = await window.mermaid.render(`${renderId}-svg`, rawCode);
                            svgContainer.innerHTML = svg;
                        }
                    } catch (err) {
                        console.error('Mermaid 渲染报错:', err);
                        wrapper.querySelector('.mermaid-svg-container').innerHTML = `
                            <div class="text-rose-400 text-xs flex items-center gap-1.5 p-2 bg-rose-950/30 rounded border border-rose-900/40">
                                <i class="ph ph-warning"></i> 图谱绘制失败: 语法有误
                            </div>
                        `;
                    }
                });

                // 2. 处理 ECharts 联动数据（支持由 AI 改变右侧数据结构画布）
                if (chat.messages.value.length > 0) {
                    const lastMsg = chat.messages.value[chat.messages.value.length - 1];
                    if (lastMsg.senderType === 'agent' && lastMsg.content && lastMsg.content.includes('<echarts-data')) {
                        const regex = /<echarts-data\s+type="([^"]+)">([\s\S]*?)<\/echarts-data>/;
                        const match = lastMsg.content.match(regex);
                        if (match) {
                            const type = match[1];
                            const rawJson = match[2].trim();
                            try {
                                const data = JSON.parse(rawJson);

                                // 隐藏标签以保持聊天流整洁
                                lastMsg.content = lastMsg.content.replace(regex, '').trim();
                                if (chat.parsedHtmlCache[lastMsg.id]) {
                                    chat.parsedHtmlCache[lastMsg.id] = (window.marked && window.marked.parse) ? window.marked.parse(lastMsg.content) : lastMsg.content;
                                }

                                if (type === 'tree') {
                                    // 自动将右侧视图切换到课程路径图 (courses/pathway)，实现可视化画布聚焦
                                    auth.currentView.value = 'courses';
                                    setTimeout(() => {
                                        const newOption = {
                                            tooltip: { trigger: 'item', triggerOn: 'mousemove' },
                                            series: [{
                                                type: 'tree',
                                                data: [data],
                                                left: '8%', right: '8%', top: '12%', bottom: '12%',
                                                symbol: 'emptyCircle', symbolSize: 10,
                                                itemStyle: { color: '#3B82F6', borderColor: '#60A5FA', borderWidth: 2 },
                                                label: { position: 'top', rotate: 0, verticalAlign: 'middle', align: 'right', fontSize: 11, color: '#334155' },
                                                leaves: { label: { position: 'right', align: 'left' } },
                                                expandAndCollapse: true,
                                                animationDuration: 550,
                                                animationDurationUpdate: 750
                                            }]
                                        };
                                        coursesState.pathwayOption.value = newOption;
                                        showToast('💡 已为您在右侧画布中渲染交互式算法树！', 'success');
                                    }, 250);
                                }
                            } catch (e) {
                                console.error("ECharts 联动数据解析失败:", e);
                            }
                        }
                    }
                }
            });
        };

        // 监听消息列表变动及智能体思考状态，智能处理代码块高亮与 Mermaid/ECharts 异步渲染
        watch(
            [chat.messages, chat.thinkingAgent],
            ([msgs, thinking]) => {
                processChatCodeBlocks();
                // 仅在智能体生成结束时一次性渲染，避免流式输出时的卡顿、闪烁和未闭合语法报错
                if (!thinking) {
                    processMermaidAndECharts();
                }
            },
            { deep: true }
        );

        // 概念自测题互动状态
        const quizStates = ref({});

        const parseQuiz = (content) => {
            const lines = content.split('\n');
            let question = '';
            const options = [];
            let answer = '';
            lines.forEach(line => {
                if (line.startsWith('[QUIZ]')) {
                    question = line.replace('[QUIZ]', '').trim();
                } else if (line.match(/^[A-D]\./)) {
                    options.push(line.trim());
                } else if (line.startsWith('[ANSWER]')) {
                    answer = line.replace('[ANSWER]', '').trim();
                }
            });
            return { question, options, answer };
        };

        const checkQuizAnswer = (msgId, opt, correctOpt) => {
            if (quizStates.value[msgId]?.answered) return;
            const isCorrect = opt === correctOpt;
            quizStates.value[msgId] = {
                answered: true,
                selected: opt,
                correct: isCorrect
            };

            const username = auth.currentUser.value?.username || 'guest_user';
            profileApi.recordTest({
                user_id: username,
                problem_id: `quiz_${msgId}`,
                category: '概念自测',
                status: isCorrect ? 'passed' : 'failed',
                difficulty: 'Easy',
                error_msg: isCorrect ? null : `自测选择错误: 选了 ${opt}, 正确是 ${correctOpt}`
            }).then(() => {
                profileState.fetchProfile();
                showToast(isCorrect ? '自测正确，知识分值提升！' : '自测错误，已为您记入错题集', isCorrect ? 'success' : 'error');
            }).catch(e => console.error(e));
        };

        const getQuizOptClass = (msgId, opt, correctOpt) => {
            const state = quizStates.value[msgId];
            if (!state) return 'bg-white border-slate-200 hover:bg-slate-100 text-slate-700 cursor-pointer';
            if (state.selected === opt) {
                return opt === correctOpt
                    ? 'bg-emerald-50 border-emerald-400 text-emerald-700 font-bold'
                    : 'bg-red-50 border-red-400 text-red-700 font-bold';
            }
            if (opt === correctOpt) {
                return 'bg-emerald-50/50 border-emerald-300 text-emerald-600';
            }
            return 'bg-white/40 border-slate-100 text-slate-400 opacity-60 pointer-events-none';
        };

        // ================== 初始化运行 ==================
        if (auth.isLoggedIn.value) {
            if (chat.messages.value.length === 0 && auth.currentRole.value === 'student') {
                const username = auth.currentUser.value?.username || '同学';
                const msg = `欢迎进入格至智能协同教育系统，**${username}**！我是您的主规划师 Alina。`;
                const id = Date.now();
                chat.messages.value.push({ id, senderType: 'agent', senderId: 'agent_planner', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), content: msg });
                chat.parsedHtmlCache[id] = (window.marked && window.marked.parse) ? window.marked.parse(msg) : msg;
            }
        }

        // 整合返回供模板挂载
        return {
            // Toast
            toast,
            showToast,

            // Auth & Role
            isLoggedIn: auth.isLoggedIn,
            currentUser: auth.currentUser,
            isRegistering: auth.isRegistering,
            isTeacherLogin: auth.isTeacherLogin,
            authForm: auth.authForm,
            authLoading: auth.authLoading,
            currentRole: auth.currentRole,
            currentView: auth.currentView,
            activeMenus: auth.activeMenus,
            currentMenuInfo: auth.currentMenuInfo,
            handleAuth: auth.handleAuth,
            toggleAuthMode: auth.toggleAuthMode,
            handleLogout: () => auth.handleLogout(onLogout),

            // 工作台模式控制
            workspaceMode,
            selectWorkspaceMode,

            // Chat & Files
            inputText: chat.inputText,
            chatContainer: chat.chatContainer,
            thinkingAgent: chat.thinkingAgent,
            forceRAG: chat.forceRAG,
            agentMode: chat.agentMode,
            historyLoading: chat.historyLoading,
            historyError: chat.historyError,
            showHistoryPanel: chat.showHistoryPanel,
            highlightedMessageId: chat.highlightedMessageId,
            historyPanelTitle: chat.historyPanelTitle,
            messages: chat.messages,
            files: chat.files,
            knowledgeRepositories: chat.knowledgeRepositories,
            selectedRepositoryId: chat.selectedRepositoryId,
            selectedRepository: chat.selectedRepository,
            newRepositoryName: chat.newRepositoryName,
            knowledgeLoading: chat.knowledgeLoading,
            knowledgeUploading: chat.knowledgeUploading,
            knowledgeDeletingId: chat.knowledgeDeletingId,
            knowledgeRepositoryDeletingId: chat.knowledgeRepositoryDeletingId,
            knowledgeDatasetId: chat.knowledgeDatasetId,
            courseKnowledgeBases: chat.courseKnowledgeBases,
            selectedCourseDatasetIds: chat.selectedCourseDatasetIds,
            toggleCourseDataset: chat.toggleCourseDataset,
            loadKnowledgeRepositories: chat.loadKnowledgeRepositories,
            selectKnowledgeRepository: chat.selectKnowledgeRepository,
            createKnowledgeRepository: chat.createKnowledgeRepository,
            deleteKnowledgeRepository: chat.deleteKnowledgeRepository,
            deleteKnowledgeDocument: chat.deleteKnowledgeDocument,
            getKnowledgeFileStatusLabel: chat.getKnowledgeFileStatusLabel,
            visualGuidePrompt: chat.visualGuidePrompt,
            visualGuideType: chat.visualGuideType,
            visualGuideTypes: chat.visualGuideTypes,
            visualGuideStatus: chat.visualGuideStatus,
            visualGuide: chat.visualGuide,
            visualGuideImage: chat.visualGuideImage,
            visualGuideHistory: chat.visualGuideHistory,
            showVisualGuideViewer: chat.showVisualGuideViewer,
            canOpenVisualGuideViewer: chat.canOpenVisualGuideViewer,
            toggleRAG: chat.toggleRAG,
            setAgentMode: chat.setAgentMode,
            loadChatHistory: chat.loadChatHistory,
            openHistoryPanel: chat.openHistoryPanel,
            closeHistoryPanel: chat.closeHistoryPanel,
            jumpToHistoryMessage: chat.jumpToHistoryMessage,
            deleteHistoryMessage: chat.deleteHistoryMessage,
            clearChatHistory: chat.clearChatHistory,
            fillInput: chat.fillInput,
            getVisualGuideTypeMeta: chat.getVisualGuideTypeMeta,
            getVisualGuideSourceLabel: chat.getVisualGuideSourceLabel,
            switchVisualGuideType: chat.switchVisualGuideType,
            regenerateVisualGuide: chat.regenerateVisualGuide,
            selectVisualGuideHistory: chat.selectVisualGuideHistory,
            openVisualGuideViewer: chat.openVisualGuideViewer,
            closeVisualGuideViewer: chat.closeVisualGuideViewer,
            downloadVisualGuide: chat.downloadVisualGuide,
            triggerFileInput: () => chat.triggerFileInput(auth.isLoggedIn.value),
            handleFileUpload: chat.handleFileUpload,
            sendMessage: chat.sendMessage,
            parsedHtmlCache: chat.parsedHtmlCache,


            // Monitor & Simulation
            studentRadarOption,
            activeTaskReasonId,
            agentLogs,
            toggleTaskReason,

            // Agents
            agents: agentsState.agents,
            textModelOptions: agentsState.textModelOptions,
            imageModelOptions: agentsState.imageModelOptions,
            activeAgentModelOptions: agentsState.activeAgentModelOptions,
            showAgentModal: agentsState.showAgentModal,
            isEditingAgent: agentsState.isEditingAgent,
            agentForm: agentsState.agentForm,
            getAgentModelOptions: agentsState.getAgentModelOptions,
            openAgentModal: agentsState.openAgentModal,
            closeAgentModal: agentsState.closeAgentModal,
            updateAgentModel: agentsState.updateAgentModel,
            saveAgent: agentsState.saveAgent,
            deleteAgent: agentsState.deleteAgent,
            getAgentInfo: agentsState.getAgentInfo,
            getAgentInfoBySource: agentsState.getAgentInfoBySource,

            // Courses & Preview
            handlePreviewOrLearn,
            courses: coursesState.courses,
            selectedCourse: coursesState.selectedCourse,
            previewFileUrl: coursesState.previewFileUrl,
            previewFileName: coursesState.previewFileName,
            showPreviewModal: coursesState.showPreviewModal,
            activePreviewFile: coursesState.activePreviewFile,
            previewMode: coursesState.previewMode,
            currentPptGuide: coursesState.currentPptGuide,
            currentSlideIndex: coursesState.currentSlideIndex,
            selectedPathwayCourseId: coursesState.selectedPathwayCourseId,
            pathwayOption: coursesState.pathwayOption,
            activeNodeDetails: coursesState.activeNodeDetails,
            selectCourse: coursesState.selectCourse,
            handleNodeClick: coursesState.handleNodeClick,
            viewCoursePathway: coursesState.viewCoursePathway,
            previewFile: coursesState.previewFile,
            downloadCurrentFileDirectly: coursesState.downloadCurrentFileDirectly,
            syncToKnowledgeBase: coursesState.syncToKnowledgeBase,

            // Dashboard mock fields
            currentGoal: computed(() => profileState.profile.value.goal),
            progress: computed(() => profileState.profile.value.knowledge),
            studentProfile: profileState.profile,
            tasks,
            radarOption,
            lineOption,
            courseMindmaps,
            pendingHomeworkCount,
            submittedHomeworkCount,
            homeworkList,
            deadlines,
            examAlerts,
            errorPoints,
            errorNotebook,
            interventions,
            nudges,
            notifications,
            interactions,
            completeInteractionTask,
            liveSlots,
            courseNotes,
            currentTime,
            dashboardDisplayName,
            dashboardGreeting,
            // 仪表盘数据加载状态（用于模板中显示 loading 动画）
            dashboardLoading,
            dashboardError,
            refreshDashboard,
            showMiniprogramQR,

            // Quiz & Code post-processor
            quizStates,
            parseQuiz,
            checkQuizAnswer,
            getQuizOptClass,
            processChatCodeBlocks,

            // User Center
            showUserCenter: userCenter.showUserCenter,
            userCenterTab: userCenter.activeTab,
            userCenterLoading: userCenter.isLoading,
            isSaveSuccess: userCenter.isSaveSuccess,
            isPwdSuccess: userCenter.isPwdSuccess,
            avatarPreviewUrl: userCenter.avatarPreviewUrl,
            userInfoForm: userCenter.infoForm,
            userPwdForm: userCenter.pwdForm,
            openUserCenter: userCenter.openUserCenter,
            closeUserCenter: userCenter.closeUserCenter,
            saveUserInfo: userCenter.saveUserInfo,
            changePassword: userCenter.changePassword,
            handleAvatarUpload: userCenter.handleAvatarUpload,
            triggerAvatarInput: userCenter.triggerAvatarInput
        };
    }
});

app.config.errorHandler = (err, instance, info) => {
    alert(`Vue 渲染或运行时错误：\n${err.stack || err}\n附加信息: ${info}`);
};

app.mount('#app');
