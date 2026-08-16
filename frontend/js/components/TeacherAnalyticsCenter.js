import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { analyticsApi } from '../api/analytics.js';
import LineChart from './LineChart.js';
import RadarChart from './RadarChart.js';
import TeacherLearningDiagnosisReview from './TeacherLearningDiagnosisReview.js';

const TYPE_META = {
    nudge: { label: '教师提醒', icon: 'ph-bell-ringing', cls: 'bg-sky-50 text-sky-700 border-sky-100' },
    homework: { label: '补弱作业', icon: 'ph-clipboard-text', cls: 'bg-indigo-50 text-indigo-700 border-indigo-100' },
    mistake: { label: '错题订正', icon: 'ph-warning-diamond', cls: 'bg-rose-50 text-rose-700 border-rose-100' },
    quiz: { label: '短测任务', icon: 'ph-timer', cls: 'bg-amber-50 text-amber-700 border-amber-100' },
    'ai-guide': { label: 'AI 引导', icon: 'ph-sparkle', cls: 'bg-emerald-50 text-emerald-700 border-emerald-100' },
    system: { label: '系统建议', icon: 'ph-cpu', cls: 'bg-slate-100 text-slate-600 border-slate-200' }
};

const radarLabelStyle = {
    color: '#1c2b38',
    fontSize: 12,
    fontWeight: 700,
    backgroundColor: 'rgba(255, 255, 255, 0.72)',
    borderColor: 'rgba(255, 255, 255, 0.86)',
    borderWidth: 1,
    borderRadius: 6,
    padding: [4, 7],
    lineHeight: 18
};

export default {
    name: 'TeacherAnalyticsCenter',
    components: {
        LineChart,
        RadarChart,
        TeacherLearningDiagnosisReview
    },
    emits: ['show-toast'],
    setup(_, { emit }) {
        const loading = ref(true);
        const activeTab = ref('overview');
        const overviewStats = ref(null);
        const studentList = ref([]);
        const activeStudent = ref(null);
        const studentDetails = ref(null);
        const loadingDetails = ref(false);
        const studentSearchQuery = ref('');
        const searchingStudent = ref(false);
        const studentListEl = ref(null);
        const advicesList = ref([]);
        const generatingAdvices = ref(false);
        const actionQueue = ref([]);
        const generatingQueue = ref(false);
        const interactionRecords = ref([]);
        const interactionFilter = ref('all');
        const activeTask = ref(null);
        const taskType = ref('homework');
        const isDispatching = ref(false);
        const isSendingNudge = ref(false);
        const forwardDiagnosisToast = (...args) => emit('show-toast', ...args);

        const selectedHourData = ref(null);
        const hoveredHourData = ref(null);

        const taskForm = ref({
            title: '',
            subject: '',
            desc: '',
            deadline: '今天 23:59',
            priority: 'high',
            targetLabel: '全班'
        });

        const nudgeMessage = ref('同学你好，教师端检测到你近期在核心知识点上出现停留或重复错误，请优先完成已下发的订正任务；如遇到具体问题，请在作业诊断区发起 AI 会诊。');

        const hourlyStats = computed(() => {
            if (!overviewStats.value) return [];
            const activeData = overviewStats.value.hourlyActiveData || [];
            
            // 24小时专注力特征
            const focusData = [
                45, 30, 20, 0, 0, 15, 50, 75, 80, 85, 90, 85, // 0h - 11h
                60, 55, 75, 88, 80, 65, 85, 92, 95, 88, 70, 50  // 12h - 23h
            ];
            
            // 24小时学生端活跃倾向特征行为行为 (对应学生端五大组件)
            const behaviors = [
                { main: 'mistake', desc: '错题复习', rates: { mistake: 60, forum: 20, sandbox: 20 } }, 
                { main: 'forum', desc: '论坛闲聊', rates: { forum: 80, mistake: 20 } }, 
                { main: 'forum', desc: '论坛求助', rates: { forum: 90, mistake: 10 } }, 
                { main: 'offline', desc: '离线', rates: {} }, 
                { main: 'offline', desc: '离线', rates: {} }, 
                { main: 'offline', desc: '离线', rates: {} }, 
                { main: 'forum', desc: '晨间答疑', rates: { forum: 70, homework: 30 } }, 
                { main: 'homework', desc: '早读作业', rates: { homework: 80, forum: 20 } }, 
                { main: 'homework', desc: '随堂作业', rates: { homework: 70, sandbox: 30 } }, 
                { main: 'homework', desc: '作业诊断', rates: { homework: 60, forum: 20, sandbox: 20 } }, 
                { main: 'sandbox', desc: '沙箱调试', rates: { sandbox: 50, homework: 40, forum: 10 } }, 
                { main: 'exam', desc: '期末模拟考', rates: { exam: 80, sandbox: 20 } }, 
                { main: 'forum', desc: '午休闲聊', rates: { forum: 85, mistake: 15 } }, 
                { main: 'forum', desc: '学术讨论', rates: { forum: 70, homework: 30 } }, 
                { main: 'homework', desc: '课后练习', rates: { homework: 75, sandbox: 25 } }, 
                { main: 'homework', desc: '作业协同诊断', rates: { homework: 60, sandbox: 30, forum: 10 } }, 
                { main: 'sandbox', desc: '代码探索', rates: { sandbox: 60, homework: 30, forum: 10 } }, 
                { main: 'forum', desc: '课后求助论坛', rates: { forum: 75, homework: 25 } }, 
                { main: 'homework', desc: '课后复习', rates: { homework: 70, mistake: 30 } }, 
                { main: 'exam', desc: '在线编程挑战', rates: { exam: 70, sandbox: 30 } }, 
                { main: 'exam', desc: '算法高难短测', rates: { exam: 80, homework: 10, sandbox: 10 } }, 
                { main: 'homework', desc: '知识通关', rates: { homework: 50, mistake: 30, sandbox: 20 } }, 
                { main: 'mistake', desc: 'AI 错因分析', rates: { mistake: 70, forum: 20, sandbox: 10 } }, 
                { main: 'mistake', desc: '错题巩固订正', rates: { mistake: 80, forum: 20 } }, 
            ];
            
            const records = interactionRecords.value || [];
            
            return activeData.map((activeCount, hour) => {
                const focus = focusData[hour] || 0;
                const behavior = behaviors[hour] || { main: 'offline', desc: '离线', rates: {} };
                
                // 查找该小时段下发布的任务
                const matchedTasks = records.filter(record => {
                    if (!record.createdAt) return false;
                    const match = record.createdAt.match(/(\d{2}):\d{2}/);
                    if (match) {
                        const h = parseInt(match[1], 10);
                        return h === hour;
                    }
                    return false;
                });
                
                // 判断是否是黄金推荐时段
                const isGolden = hour === 10 || hour === 19 || hour === 20;
                
                // 推荐文本
                let aiRec = "常规下发窗口：可正常安排各类型教学辅导活动。";
                if (isGolden) {
                    aiRec = "黄金发布窗口：专注度与活跃度均达全天顶峰，适合推送【Monaco编程考试】或【高难度课后作业】。";
                } else if (hour >= 22 || hour <= 1) {
                    aiRec = "深夜脑力疲劳期：建议减少发布高强度编码任务，适合推送【错题本自主复习】与温和督学。";
                } else if (hour >= 2 && hour <= 5) {
                    aiRec = "凌晨休眠期：学生普遍处于睡眠状态，建议合理安排后台调度，不宜推送即时通知。";
                } else if (hour === 12 || hour === 13 || hour === 17) {
                    aiRec = "课余放松期：适合下发【论坛置顶大作业讨论】或【轻量级学习温馨提醒】。";
                }
                
                // 是否排期冲突 (同一个小时里有 2 个及以上正在运行的任务)
                const isConflict = matchedTasks.filter(t => t.status === 'running').length >= 2;
                
                return {
                    hour,
                    activeCount,
                    focusRate: focus,
                    behaviorMain: behavior.main,
                    behaviorDesc: behavior.desc,
                    behaviorRates: behavior.rates,
                    isGolden,
                    aiRec,
                    isConflict,
                    tasks: matchedTasks
                };
            });
        });

        const openInteractionTaskFromScheduler = (hourData) => {
            let type = 'homework';
            if (hourData.hour >= 22 || hourData.hour <= 5) {
                type = 'mistake'; 
            } else if (hourData.hour === 12 || hourData.hour === 13 || hourData.hour === 17) {
                type = 'nudge'; 
            } else if (hourData.hour === 11 || hourData.hour === 20) {
                type = 'quiz'; 
            }
            
            let defaultTitle = '学情提升任务';
            let defaultDesc = '请在指定时间内完成该任务，并在学生端提交完成状态。';
            let defaultSubject = '数据结构与算法';
            let defaultTarget = '全班';
            let weakPointId = null;

            const topWeakPoint = overviewStats.value?.weakPoints?.[0];
            if (topWeakPoint) {
                defaultSubject = topWeakPoint.subject;
                weakPointId = topWeakPoint.id;
                if (type === 'homework') {
                    defaultTitle = `${topWeakPoint.topic} 专项巩固作业`;
                    defaultDesc = `系统检测到全班在「${topWeakPoint.topic}」上理解偏低（错误率达 ${topWeakPoint.errorRate}%）。请进入编程沙箱，参考教材示例并完成对应的原地代码重构。`;
                } else if (type === 'quiz') {
                    defaultTitle = `${topWeakPoint.topic} 随堂短测`;
                    defaultDesc = `请在 Monaco IDE 编程考试室中，限时完成「${topWeakPoint.topic}」的三道选择/编程检测，用时 15 分钟。`;
                } else if (type === 'mistake') {
                    defaultTitle = `${topWeakPoint.topic} 错题本纠错`;
                    defaultDesc = `针对「${topWeakPoint.topic}」的卡点，请同学们打开错题本，查看 AI 专家 CodeNinja 诊断意见，完成代码纠错并确认掌握。`;
                } else if (type === 'nudge') {
                    defaultTitle = `${topWeakPoint.topic} 答疑与论坛热议`;
                    defaultDesc = `近期关于「${topWeakPoint.topic}」的讨论在学术论坛极高，请遇到疑问的同学积极前往答疑板块发帖，AI导师 Prof. X 将实时答疑。`;
                } else if (type === 'ai-guide') {
                    defaultTitle = `${topWeakPoint.topic} AI引导复习`;
                    defaultDesc = `系统已为你生成专属的「${topWeakPoint.topic}」Alina 三步复习路径，请点击入口逐步学习。`;
                }
            }

            taskType.value = type;
            taskForm.value = {
                title: defaultTitle,
                subject: defaultSubject,
                desc: defaultDesc,
                deadline: `今天 ${String(hourData.hour).padStart(2, '0')}:59`,
                priority: hourData.isGolden ? 'high' : 'medium',
                targetLabel: defaultTarget,
                scheduleHour: hourData.hour, 
                isScheduled: true
            };

            activeTask.value = {
                id: `sched-${Date.now()}`,
                weakPointId: weakPointId
            };
        };

        const handleSpotlightMove = (e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            e.currentTarget.style.setProperty('--mouse-x', `${x}px`);
            e.currentTarget.style.setProperty('--mouse-y', `${y}px`);
        };

        const typeMeta = (type) => TYPE_META[type] || TYPE_META.system;

        const classHealth = computed(() => {
            if (!overviewStats.value) return 0;
            const values = overviewStats.value.classRadarValues || [];
            if (!values.length) return 0;
            return Math.round(values.reduce((sum, item) => sum + item, 0) / values.length);
        });

        const highRiskStudents = computed(() => (
            studentList.value.filter(student => student.alert || student.focus < 55).slice(0, 6)
        ));

        const responseRate = computed(() => {
            if (!interactionRecords.value.length) return 0;
            const total = interactionRecords.value.reduce((sum, item) => sum + (item.completionRate || 0), 0);
            return Math.round(total / interactionRecords.value.length);
        });

        const filteredInteractionRecords = computed(() => {
            if (interactionFilter.value === 'all') return interactionRecords.value;
            return interactionRecords.value.filter(item => item.status === interactionFilter.value);
        });

        const interactionSummary = computed(() => {
            const running = interactionRecords.value.filter(item => item.status === 'running').length;
            const completed = interactionRecords.value.filter(item => item.status === 'completed').length;
            const unread = interactionRecords.value.reduce((sum, item) => sum + (item.unreadCount || 0), 0);
            return { running, completed, unread };
        });

        const loadStats = async () => {
            loading.value = true;
            try {
                const [stats, students, advices, queue, records] = await Promise.all([
                    analyticsApi.getOverviewStats(),
                    analyticsApi.getStudentList(),
                    analyticsApi.getAiInterventionAdvices(),
                    analyticsApi.getActionQueue(),
                    analyticsApi.getInteractionRecords()
                ]);
                overviewStats.value = stats;
                studentList.value = students;
                advicesList.value = advices;
                actionQueue.value = queue;
                interactionRecords.value = records;

                if (students.length > 0) {
                    await selectStudent(students[0]);
                }

                if (stats) {
                    const statsList = hourlyStats.value;
                    selectedHourData.value = statsList.find(s => s.hour === 20) || statsList[20] || null;
                }
            } catch (err) {
                emit('show-toast', '学情数据同步失败', 'error');
            } finally {
                loading.value = false;
            }
        };

        const selectStudent = async (student) => {
            activeStudent.value = student;
            loadingDetails.value = true;
            try {
                const details = await analyticsApi.getStudentDetails(student.id);
                const evidence = details.radarEvidence || student.radarEvidence || {};
                studentDetails.value = {
                    ...details,
                    radarEvidence: evidence,
                    evidenceSummary: Object.values(evidence)
                        .map(item => item?.label)
                        .filter(Boolean)
                        .slice(0, 4),
                    timeline: details.timeline || [
                        { label: '作业提交', value: student.progress >= 60 ? '节奏稳定' : '低于班级均值', tone: student.progress >= 60 ? 'good' : 'risk' },
                        { label: '错题新增', value: `${details.errors?.length || 0} 个卡点`, tone: (details.errors?.length || 0) > 2 ? 'risk' : 'normal' },
                        { label: 'AI 会诊', value: student.currentAgent || '未启用', tone: student.currentAgent ? 'good' : 'normal' },
                        { label: '教师干预', value: student.alert ? '待跟进' : '暂无异常', tone: student.alert ? 'risk' : 'good' }
                    ]
                };
                // 同步列表卡片上的雷达值，避免列表与详情口径分裂
                if (Array.isArray(details.radarValues) && details.radarValues.length) {
                    student.radarValues = details.radarValues;
                    student.focus = details.focus ?? student.focus;
                    student.progress = details.progress ?? student.progress;
                }
                nudgeMessage.value = student.alert
                    ? `同学你好，教师端检测到你在「${student.goal}」任务中专注度偏低（${student.focus}/100），请优先完成错题订正和补弱任务。`
                    : `同学你好，你近期学习节奏整体平稳，请继续保持当前进度，并在遇到卡点时及时发起 AI 会诊。`;
            } catch (err) {
                emit('show-toast', '无法拉取学生画像', 'error');
            } finally {
                loadingDetails.value = false;
            }
        };

        const resolveStudentFromList = (candidate) => {
            if (!candidate) return null;
            return studentList.value.find(item =>
                String(item.id) === String(candidate.id)
                || (candidate.username && item.username === candidate.username)
                || (candidate.userId && item.userId === candidate.userId)
                || (candidate.name && item.name === candidate.name)
            ) || candidate;
        };

        const scrollToStudentCard = async (student) => {
            await nextTick();
            const listEl = studentListEl.value;
            if (!listEl || !student) return;
            const card = listEl.querySelector(`[data-student-id="${student.id}"]`);
            if (!card) return;
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        };

        const searchAndScrollToStudent = async () => {
            const keyword = studentSearchQuery.value.trim();
            if (!keyword) {
                emit('show-toast', '请输入学生姓名', 'error');
                return;
            }
            if (searchingStudent.value) return;

            searchingStudent.value = true;
            try {
                let matched = null;
                try {
                    const result = await analyticsApi.searchStudents(keyword);
                    matched = resolveStudentFromList(result?.bestMatch || result?.matches?.[0] || null);
                } catch (_) {
                    matched = null;
                }

                if (!matched) {
                    const lower = keyword.toLowerCase();
                    matched = studentList.value.find(item => {
                        const name = String(item.name || '').toLowerCase();
                        const username = String(item.username || item.userId || '').toLowerCase();
                        return name === lower || username === lower || name.includes(lower) || username.includes(lower);
                    }) || null;
                }

                if (!matched) {
                    emit('show-toast', `未找到学生「${keyword}」`, 'error');
                    return;
                }

                await selectStudent(matched);
                await scrollToStudentCard(matched);
                emit('show-toast', `已定位到 ${matched.name}`, 'success');
            } finally {
                searchingStudent.value = false;
            }
        };

        const buildTaskDefaults = (source = {}, type = 'homework') => {
            const title = source.title || source.topic || source.name || '学情补弱任务';
            const subject = source.subject || '数据结构与算法';
            const defaultTarget = source.studentId
                ? (source.target || source.name || '单个学生')
                : (source.target || source.targetLabel || (source.errorRate ? '受影响学生组' : '全班'));
            return {
                title: type === 'nudge' ? `${title} 学习提醒` : title,
                subject,
                desc: source.suggestion || source.details || '请根据教师端诊断要求完成本次学习任务，并在学生端提交完成状态。',
                deadline: type === 'quiz' ? '今天 20:00' : '今天 23:59',
                priority: source.level === 'medium' ? 'medium' : 'high',
                targetLabel: defaultTarget
            };
        };

        const openInteractionTask = (source, type = null) => {
            const normalizedType = type || source.actionType || source.type || 'homework';
            taskType.value = normalizedType === 'system' ? 'ai-guide' : normalizedType;
            taskForm.value = buildTaskDefaults(source, taskType.value);
            activeTask.value = source;
        };

        const buildDispatchPayload = (overrides = {}) => {
            const form = taskForm.value;
            const rawStudentId = activeTask.value?.studentId
                || activeTask.value?.username
                || activeTask.value?.userId
                || '';
            // 个人任务优先传 username，后端会再解析数字 id
            const resolvedKey = rawStudentId
                ? (
                    studentList.value.find(item =>
                        String(item.id) === String(rawStudentId)
                        || item.username === rawStudentId
                        || item.userId === rawStudentId
                    )?.username || rawStudentId
                )
                : '';
            const studentIds = resolvedKey ? [resolvedKey] : [];
            
            let createdAt = overrides.createdAt || null;
            if (form.isScheduled && form.scheduleHour !== undefined) {
                createdAt = `今天 ${String(form.scheduleHour).padStart(2, '0')}:15`;
            }

            const payload = {
                type: overrides.type || taskType.value,
                title: overrides.title || form.title,
                target: overrides.target || {
                    scope: studentIds.length ? 'student' : 'group',
                    label: form.targetLabel,
                    studentIds
                },
                source: {
                    module: 'teacher-analytics',
                    weakPointId: activeTask.value?.weakPointId || activeTask.value?.id,
                    adviceId: activeTask.value?.type ? activeTask.value.id : null
                },
                payload: {
                    subject: form.subject,
                    desc: form.desc,
                    deadline: form.deadline,
                    priority: form.priority
                }
            };

            if (createdAt) {
                payload.createdAt = createdAt;
            }
            return payload;
        };

        const appendRecord = (record) => {
            if (!record) return;
            const exists = interactionRecords.value.some(item => item.id === record.id);
            if (!exists) {
                interactionRecords.value.unshift(record);
            }
        };

        const submitInteractionTask = async () => {
            if (isDispatching.value) return;
            isDispatching.value = true;
            try {
                const result = await analyticsApi.dispatchStudentInteraction(buildDispatchPayload());
                appendRecord(result.record);
                if (activeTask.value?.id && overviewStats.value?.weakPoints) {
                    overviewStats.value.weakPoints = overviewStats.value.weakPoints.filter(item => item.id !== activeTask.value.id);
                }
                activeTask.value = null;
                activeTab.value = 'interactions';
                emit('show-toast', '交互任务已下发，学生端将收到对应入口', 'success');
            } catch (err) {
                emit('show-toast', '交互任务下发失败', 'error');
            } finally {
                isDispatching.value = false;
            }
        };

        const handleSendNudge = async () => {
            if (!activeStudent.value || !nudgeMessage.value.trim() || isSendingNudge.value) return;
            isSendingNudge.value = true;
            try {
                const studentKey = activeStudent.value.username || activeStudent.value.userId || activeStudent.value.id;
                const result = await analyticsApi.dispatchStudentInteraction({
                    type: 'nudge',
                    title: `${activeStudent.value.name} 学习节奏提醒`,
                    target: { scope: 'student', label: activeStudent.value.name, studentIds: [studentKey] },
                    source: { module: 'teacher-analytics', studentId: studentKey },
                    payload: {
                        subject: activeStudent.value.goal,
                        desc: nudgeMessage.value,
                        deadline: '今天 23:59',
                        priority: activeStudent.value.alert ? 'high' : 'medium'
                    }
                });
                appendRecord(result.record);
                activeStudent.value.alert = false;
                if (activeStudent.value.focus < 60) activeStudent.value.focus = Math.min(100, activeStudent.value.focus + 18);
                await selectStudent(activeStudent.value);
                emit('show-toast', `已向 ${activeStudent.value.name} 下发学习提醒`, 'success');
            } catch (err) {
                emit('show-toast', '提醒下发失败', 'error');
            } finally {
                isSendingNudge.value = false;
            }
        };

        const handleAdoptAdvice = async (advice) => {
            if (!advice.active || isDispatching.value) return;
            const type = advice.type === 'system' ? 'ai-guide' : advice.type;
            taskType.value = type;
            taskForm.value = buildTaskDefaults({
                ...advice,
                target: type === 'mistake' ? '重复错题学生 8 人' : '全班'
            }, type);
            activeTask.value = advice;
            await submitInteractionTask();
            advice.active = false;
        };

        const handleGenerateAdvices = async () => {
            if (generatingAdvices.value) return;
            generatingAdvices.value = true;
            try {
                const result = await analyticsApi.generateAdvices();
                if (Array.isArray(result) && result.length > 0) {
                    advicesList.value = result;
                } else {
                    // 兜底：重新加载所有数据
                    const advices = await analyticsApi.getAiInterventionAdvices();
                    advicesList.value = advices;
                }
                emit('show-toast', `AI 建议已生成：${Array.isArray(result) ? result.length : advicesList.value.length} 条`, 'success');
            } catch (err) {
                emit('show-toast', `AI 建议生成失败：${err.message}`, 'error');
            } finally {
                generatingAdvices.value = false;
            }
        };

        const handleGenerateActionQueue = async () => {
            if (generatingQueue.value) return;
            generatingQueue.value = true;
            try {
                const result = await analyticsApi.generateActionQueue();
                if (Array.isArray(result) && result.length > 0) {
                    actionQueue.value = result;
                } else {
                    const queue = await analyticsApi.getActionQueue();
                    actionQueue.value = queue;
                }
                emit('show-toast', `今日行动队列已生成：${Array.isArray(result) ? result.length : actionQueue.value.length} 条`, 'success');
            } catch (err) {
                emit('show-toast', `行动队列生成失败：${err.message}`, 'error');
            } finally {
                generatingQueue.value = false;
            }
        };

        const repeatReminder = async (record) => {
            const unreadCount = Math.max(0, (record.unreadCount || 0) - 1);
            const patch = {
                unreadCount,
                nextAction: unreadCount > 0 ? '继续观察未读学生' : '等待学生完成任务'
            };
            try {
                await analyticsApi.updateInteractionRecord(record.id, patch);
                Object.assign(record, patch);
                emit('show-toast', '已补发提醒给未响应学生', 'success');
            } catch (err) {
                emit('show-toast', '补发提醒失败', 'error');
            }
        };

        const classRadarOption = computed(() => {
            if (!overviewStats.value) return {};
            return {
                radar: {
                    indicator: overviewStats.value.radarIndicators,
                    center: ['50%', '54%'],
                    radius: '58%',
                    nameGap: 18,
                    axisName: radarLabelStyle,
                    name: { textStyle: radarLabelStyle },
                    splitNumber: 4,
                    axisLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.18)' } },
                    splitLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.16)' } },
                    splitArea: { areaStyle: { color: ['rgba(255,255,255,0.18)', 'rgba(28,43,56,0.035)'] } }
                },
                series: [{
                    type: 'radar',
                    data: [{
                        value: overviewStats.value.classRadarValues,
                        name: '全班维度均值',
                        lineStyle: { color: '#1c2b38', width: 2.5 },
                        areaStyle: { color: 'rgba(28, 43, 56, 0.15)' },
                        itemStyle: { color: '#1c2b38' }
                    }]
                }]
            };
        });

        const classLineOption = computed(() => {
            if (!overviewStats.value) return {};
            return {
                tooltip: { trigger: 'axis' },
                xAxis: {
                    type: 'category',
                    data: overviewStats.value.weeklyActivityDates,
                    axisLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.1)' } }
                },
                yAxis: {
                    type: 'value',
                    name: '响应比例 (%)',
                    max: 100,
                    splitLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.08)' } }
                },
                series: [{
                    name: '学生端响应指数',
                    data: overviewStats.value.weeklyActivityRates,
                    type: 'line',
                    smooth: true,
                    itemStyle: { color: '#1c2b38' },
                    areaStyle: { color: 'rgba(28, 43, 56, 0.08)' }
                }]
            };
        });

        const studentRadarOption = computed(() => {
            if (!studentDetails.value || !overviewStats.value) return {};
            return {
                radar: {
                    indicator: overviewStats.value.radarIndicators,
                    center: ['50%', '54%'],
                    radius: '56%',
                    nameGap: 16,
                    axisName: radarLabelStyle,
                    name: { textStyle: radarLabelStyle },
                    splitNumber: 4,
                    axisLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.18)' } },
                    splitLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.16)' } },
                    splitArea: { areaStyle: { color: ['rgba(255,255,255,0.18)', 'rgba(28,43,56,0.035)'] } }
                },
                series: [{
                    type: 'radar',
                    data: [{
                        value: studentDetails.value.radarValues,
                        name: activeStudent.value.name,
                        lineStyle: { color: '#1c2b38', width: 2 },
                        areaStyle: { color: 'rgba(28, 43, 56, 0.15)' },
                        itemStyle: { color: '#1c2b38' }
                    }]
                }]
            };
        });

        const onInteractionCompleted = async () => {
            try {
                const [students, records] = await Promise.all([
                    analyticsApi.getStudentList(),
                    analyticsApi.getInteractionRecords()
                ]);
                studentList.value = students;
                interactionRecords.value = records;
                if (activeStudent.value) {
                    const refreshed = students.find(item =>
                        String(item.id) === String(activeStudent.value.id)
                        || item.username === activeStudent.value.username
                    ) || activeStudent.value;
                    await selectStudent(refreshed);
                }
            } catch (_) {
                // 刷新失败不打断教师操作
            }
        };

        onMounted(() => {
            loadStats();
            if (typeof window !== 'undefined') {
                window.addEventListener('interaction-completed', onInteractionCompleted);
            }
        });

        onBeforeUnmount(() => {
            if (typeof window !== 'undefined') {
                window.removeEventListener('interaction-completed', onInteractionCompleted);
            }
        });

        return {
            loading,
            activeTab,
            overviewStats,
            studentList,
            activeStudent,
            studentDetails,
            loadingDetails,
            studentSearchQuery,
            searchingStudent,
            studentListEl,
            advicesList,
            generatingAdvices,
            actionQueue,
            generatingQueue,
            interactionRecords,
            interactionFilter,
            activeTask,
            taskType,
            taskForm,
            isDispatching,
            isSendingNudge,
            nudgeMessage,
            classHealth,
            highRiskStudents,
            responseRate,
            filteredInteractionRecords,
            interactionSummary,
            typeMeta,
            loadStats,
            selectStudent,
            searchAndScrollToStudent,
            openInteractionTask,
            submitInteractionTask,
            handleSendNudge,
            handleAdoptAdvice,
            handleGenerateAdvices,
            handleGenerateActionQueue,
            repeatReminder,
            classRadarOption,
            classLineOption,
            studentRadarOption,
            selectedHourData,
            hoveredHourData,
            hourlyStats,
            openInteractionTaskFromScheduler,
            handleSpotlightMove,
            forwardDiagnosisToast
        };
    },
    template: `
        <section class="absolute inset-0 overflow-y-auto p-6 lg:p-8 bg-slate-50 select-none">
            <style>
            [v-cloak] { display: none; }
            .spotlight-card {
                position: relative;
                transition: transform 0.25s cubic-bezier(0.25, 1, 0.5, 1), border-color 0.2s, box-shadow 0.25s, background-color 0.2s;
            }
            .spotlight-card:hover {
                border-color: rgba(28, 43, 56, 0.3) !important;
                box-shadow: 0 4px 14px rgba(28, 43, 56, 0.06) !important;
                background: radial-gradient(120px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(28, 43, 56, 0.06) 0%, transparent 80%), rgba(255, 255, 255, 0.5) !important;
            }
            .spotlight-card.selected-card {
                background: radial-gradient(120px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(0, 229, 255, 0.18) 0%, transparent 80%), #1c2b38 !important;
                box-shadow: 0 6px 18px rgba(28, 43, 56, 0.15) !important;
                transform: translateY(-2px);
                border-color: #1c2b38 !important;
            }
            .spotlight-card:active {
                transform: translateY(1px) scale(0.985);
                transition: transform 0.08s ease;
            }
            .spotlight-card.selected-card:active {
                transform: translateY(0px) scale(0.985);
            }
            .conflict-card {
                border-color: #f43f5e !important;
                box-shadow: 0 0 12px rgba(244, 63, 94, 0.25) !important;
                animation: conflict-pulse 2s infinite cubic-bezier(0.25, 1, 0.5, 1);
            }
            @keyframes conflict-pulse {
                0%, 100% { box-shadow: 0 0 12px rgba(244, 63, 94, 0.2); }
                50% { box-shadow: 0 0 20px rgba(244, 63, 94, 0.45); }
            }
            .stack-segment {
                transition: transform 0.2s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.2s;
                transform-origin: bottom;
            }
            .stack-segment:hover {
                transform: scaleY(1.3) scaleX(1.02);
                opacity: 0.95;
                z-index: 10;
            }
            .btn-micro {
                transition: transform 0.15s cubic-bezier(0.25, 1, 0.5, 1), background-color 0.2s, box-shadow 0.2s;
            }
            .btn-micro:hover {
                transform: translateY(-1px);
            }
            .btn-micro:active {
                transform: translateY(1px) scale(0.97);
                transition: transform 0.08s ease;
            }
            button:focus, div:focus, input:focus, textarea:focus {
                outline: none;
            }
            button:focus-visible, div:focus-visible, input:focus-visible, textarea:focus-visible {
                outline: 2px solid #1c2b38;
                outline-offset: 2px;
            }
            .modal-slide-enter-active, .modal-slide-leave-active {
                transition: opacity 0.3s cubic-bezier(0.25, 1, 0.5, 1);
            }
            .modal-slide-enter-from, .modal-slide-leave-to {
                opacity: 0;
            }
            .modal-slide-enter-active .bg-white, .modal-slide-leave-active .bg-white {
                transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1);
            }
            .modal-slide-enter-from .bg-white {
                transform: scale(0.96) translateY(16px);
            }
            .modal-slide-leave-to .bg-white {
                transform: scale(0.96) translateY(16px);
            }
            .soft-scroll {
                scrollbar-width: thin;
                scrollbar-color: rgba(28, 43, 56, 0.22) transparent;
            }
            .soft-scroll::-webkit-scrollbar {
                width: 6px;
            }
            .soft-scroll::-webkit-scrollbar-track {
                background: transparent;
                margin: 4px 0;
            }
            .soft-scroll::-webkit-scrollbar-thumb {
                background: rgba(28, 43, 56, 0.16);
                border-radius: 999px;
            }
            .soft-scroll::-webkit-scrollbar-thumb:hover {
                background: rgba(28, 43, 56, 0.32);
            }
            .soft-scroll::-webkit-scrollbar-corner {
                background: transparent;
            }
            </style>
            <div class="max-w-7xl mx-auto flex flex-col gap-6">
                <div class="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-3 mb-2">
                            <div class="w-11 h-11 rounded-2xl bg-[#1c2b38] text-white flex items-center justify-center">
                                <i class="ph ph-chart-line-up text-xl"></i>
                            </div>
                            <div>
                                <h2 class="text-2xl font-bold text-slate-800" style="font-family: 'Noto Serif SC', serif;">班级学情干预指挥中心</h2>
                                <p class="text-sm text-slate-500 mt-1">从班级诊断到学生端任务下发、确认、订正与完成状态回流。</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="flex flex-wrap gap-2">
                    <button @click="activeTab = 'overview'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'overview' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">
                        班级诊断总览
                    </button>
                    <button @click="activeTab = 'profile'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'profile' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">
                        学生个人画像
                    </button>
                    <button @click="activeTab = 'alerts'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'alerts' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">
                        薄弱点预警
                        <span v-if="overviewStats?.weakPoints?.length > 0" class="ml-1 bg-red-600 text-white rounded-full px-1.5 py-0.5 text-[9px]">{{ overviewStats.weakPoints.length }}</span>
                    </button>
                    <button @click="activeTab = 'interactions'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'interactions' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">
                        师生交互闭环
                    </button>
                    <button @click="activeTab = 'advices'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'advices' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">
                        AI 干预策略
                    </button>
                    <button @click="activeTab = 'diagnosis-review'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'diagnosis-review' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-white'">
                        学习诊断审查
                    </button>
                </div>

                <div v-if="loading" class="bg-white border border-slate-200 shadow-sm p-8 text-sm text-slate-500">正在聚合班级学情、学生端响应与教师干预记录...</div>

                <template v-else>
                    <div v-show="activeTab === 'overview'" class="flex flex-col gap-6">
                        <div class="grid grid-cols-2 xl:grid-cols-4 gap-4">
                            <div class="bg-white border border-slate-200 shadow-sm p-5">
                                <p class="text-xs text-slate-500">班级健康指数</p>
                                <p class="text-3xl font-bold text-slate-900 mt-2">{{ classHealth }}</p>
                                <p class="text-[11px] text-slate-400 mt-1">六维画像均值</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm p-5">
                                <p class="text-xs text-slate-500">待干预学生</p>
                                <p class="text-3xl font-bold text-rose-700 mt-2">{{ highRiskStudents.length }}</p>
                                <p class="text-[11px] text-slate-400 mt-1">低专注或重复卡点</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm p-5">
                                <p class="text-xs text-slate-500">薄弱知识点</p>
                                <p class="text-3xl font-bold text-amber-700 mt-2">{{ overviewStats?.weakPoints?.length || 0 }}</p>
                                <p class="text-[11px] text-slate-400 mt-1">可一键转任务</p>
                            </div>
                            <div class="bg-[#1c2b38] text-white rounded-2xl p-5 shadow-md">
                                <p class="text-xs text-white/70">学生响应率</p>
                                <p class="text-3xl font-bold mt-2">{{ responseRate }}%</p>
                                <p class="text-[11px] text-white/50 mt-1">基于已下发交互</p>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-6">
                            <div class="bg-white border border-slate-200 shadow-sm p-6">
                                <div class="flex items-start justify-between gap-3 mb-4">
                                    <div>
                                        <h3 class="text-sm font-bold text-slate-800">班级六维能力雷达</h3>
                                        <p class="text-xs text-slate-400 mt-1">保留宏观诊断视角，用于判断补弱任务覆盖是否均衡。</p>
                                    </div>
                                    <span class="text-[10px] bg-white/70 border border-white px-2 py-1 rounded-lg text-slate-500">Macro View</span>
                                </div>
                                <radar-chart :option="classRadarOption" class="w-full h-[280px]"></radar-chart>
                            </div>

                            <div class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col gap-4">
                                <div class="flex items-start justify-between">
                                    <div>
                                        <h3 class="text-sm font-bold text-slate-800">今日行动队列</h3>
                                        <p class="text-xs text-slate-400 mt-1">把数据异常转成教师可执行任务。</p>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <button @click="handleGenerateActionQueue" :disabled="generatingQueue" class="px-3 py-1.5 rounded-lg bg-[#1c2b38] text-white text-xs font-bold hover:bg-slate-700 transition-all disabled:opacity-50 disabled:cursor-wait btn-micro">
                                            <i class="ph ph-lightning mr-1"></i>{{ generatingQueue ? '生成中...' : '生成今日行动' }}
                                        </button>
                                        <button @click="loadStats" class="w-9 h-9 rounded-xl bg-white/70 border border-white text-slate-600 hover:text-slate-900 btn-micro" title="刷新">
                                            <i class="ph ph-arrow-clockwise"></i>
                                        </button>
                                    </div>
                                </div>
                                <div class="flex flex-col gap-3">
                                    <article v-for="item in actionQueue" :key="item.id" class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4">
                                        <div class="flex items-start justify-between gap-3">
                                            <div class="min-w-0">
                                                <div class="flex flex-wrap items-center gap-2 mb-2">
                                                    <span class="text-[10px] font-bold px-2 py-1 rounded-lg" :class="item.level === 'high' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700'">{{ item.level === 'high' ? '高优先级' : '中优先级' }}</span>
                                                    <span class="text-[10px] text-slate-500">{{ item.target }}</span>
                                                </div>
                                                <h4 class="text-sm font-bold text-slate-900">{{ item.title }}</h4>
                                                <p class="text-xs text-slate-500 leading-relaxed mt-1">{{ item.suggestion }}</p>
                                            </div>
                                            <button @click="openInteractionTask(item)" class="px-3 py-2 rounded-xl bg-[#1c2b38] text-white text-[11px] font-bold shrink-0 btn-micro">
                                                处理
                                            </button>
                                        </div>
                                    </article>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col gap-5">
                                <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                                    <div>
                                        <h3 class="text-base font-bold text-slate-800" style="font-family: 'Noto Serif SC', serif;">24小时学情脉搏与智能排期决策台</h3>
                                        <p class="text-xs text-slate-400 mt-1">融合在线活跃与大脑专注力模型，辅助教师错峰下发并预约辅导任务。</p>
                                    </div>
                                    <span class="text-[10px] bg-[#1c2b38]/10 text-[#1c2b38] border border-[#1c2b38]/20 px-2.5 py-1 rounded-lg font-bold">Active Scheduler</span>
                                </div>

                                <div class="grid grid-cols-1 lg:grid-cols-[1.3fr_0.7fr] gap-6">
                                    <div class="flex flex-col gap-4">
                                        <div class="flex items-center justify-between">
                                            <span class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                                <i class="ph ph-calendar-blank text-[#1c2b38]"></i>
                                                学情脉搏时间线 (0h - 23h)
                                            </span>
                                            <div class="flex items-center gap-4 text-[10px] text-slate-500 select-none">
                                                <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block animate-pulse"></span>AI 推荐黄金窗口</span>
                                                <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded bg-rose-100 border border-rose-400 inline-block"></span>排期饱和警告</span>
                                            </div>
                                        </div>

                                        <div class="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-6 xl:grid-cols-8 gap-2.5">
                                            <div v-for="item in hourlyStats" :key="item.hour"
                                                @click="selectedHourData = item"
                                                @mouseenter="hoveredHourData = item"
                                                @mouseleave="hoveredHourData = null"
                                                @mousemove="handleSpotlightMove"
                                                class="relative rounded-2xl p-2.5 border cursor-pointer flex flex-col justify-between min-h-[92px] group select-none overflow-hidden spotlight-card"
                                                :class="[
                                                    selectedHourData && selectedHourData.hour === item.hour 
                                                        ? 'selected-card text-white' 
                                                        : item.isConflict
                                                            ? 'conflict-card text-rose-800'
                                                            : 'bg-white border-slate-200 text-slate-700'
                                                ]">
                                                
                                                <div v-if="item.isGolden" 
                                                    class="absolute top-1 right-1 w-4 h-4 rounded-full bg-amber-500 text-white flex items-center justify-center text-[9px] font-extrabold animate-bounce"
                                                    title="AI 推荐黄金时段">
                                                    荐
                                                </div>
                                                
                                                <div v-else-if="item.hour >= 22 || item.hour <= 1"
                                                    class="absolute top-1.5 right-1.5 text-[9px] opacity-60"
                                                    title="深夜时段">
                                                    <i class="ph ph-moon"></i>
                                                </div>

                                                <div v-if="item.isConflict" 
                                                    class="absolute top-1.5 right-1.5 text-rose-600 text-xs animate-pulse"
                                                    title="排期冲突饱和！建议推迟或改期">
                                                    <i class="ph ph-warning-circle"></i>
                                                </div>

                                                <div class="flex flex-col gap-0.5">
                                                    <span class="text-[10px] font-bold tracking-wide" :class="selectedHourData && selectedHourData.hour === item.hour ? 'text-white/60' : 'text-slate-400'">{{ String(item.hour).padStart(2, '0') }}:00</span>
                                                    <span class="text-lg font-extrabold" style="font-family: 'Barlow Condensed', sans-serif;">{{ item.activeCount }}<span class="text-[9px] font-semibold ml-0.5" :class="selectedHourData && selectedHourData.hour === item.hour ? 'text-white/70' : 'text-slate-500'">人</span></span>
                                                </div>

                                                <div class="w-full my-1.5">
                                                    <div class="h-1 rounded-full overflow-hidden" :class="selectedHourData && selectedHourData.hour === item.hour ? 'bg-white/20' : 'bg-slate-200/60'">
                                                        <div class="h-full rounded-full transition-all duration-500" 
                                                            :class="selectedHourData && selectedHourData.hour === item.hour ? 'bg-[#00e5ff]' : 'bg-[#1c2b38]'"
                                                            :style="{ width: item.focusRate + '%' }"></div>
                                                    </div>
                                                    <div class="flex justify-between items-center mt-1 text-[8px] opacity-75">
                                                        <span>专注度</span>
                                                        <strong>{{ item.focusRate }}%</strong>
                                                    </div>
                                                </div>

                                                <div class="flex flex-wrap gap-1 mt-1 border-t pt-1" :class="selectedHourData && selectedHourData.hour === item.hour ? 'border-white/10' : 'border-slate-100'">
                                                    <span v-if="item.tasks.length === 0" class="text-[8px] italic" :class="selectedHourData && selectedHourData.hour === item.hour ? 'text-white/40' : 'text-slate-400'">无排期</span>
                                                    <template v-else>
                                                        <div v-for="t in item.tasks" :key="t.id"
                                                            class="w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] relative group/icon"
                                                            :class="[
                                                                t.type === 'homework' ? 'bg-blue-100 text-blue-600' :
                                                                t.type === 'quiz' ? 'bg-purple-100 text-purple-600' :
                                                                t.type === 'mistake' ? 'bg-rose-100 text-rose-600' :
                                                                t.type === 'nudge' ? 'bg-amber-100 text-amber-600' : 'bg-emerald-100 text-emerald-600'
                                                            ]"
                                                            :title="t.title">
                                                            <i :class="['ph', typeMeta(t.type).icon]"></i>
                                                            <div class="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover/icon:block bg-slate-900 text-white text-[9px] px-2 py-1 rounded shadow-md whitespace-nowrap z-30">
                                                                [{{ typeMeta(t.type).label }}] {{ t.title }}
                                                            </div>
                                                        </div>
                                                    </template>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="bg-white border border-slate-200 shadow-sm p-4 flex flex-col justify-between min-h-[300px]">
                                        <div class="flex-1 flex flex-col gap-4">
                                            <h4 class="text-xs font-bold text-slate-800 flex items-center gap-1 border-b border-slate-100 pb-2">
                                                <i class="ph ph-chart-bar text-[#1c2b38]"></i>
                                                时段决策评估面板
                                            </h4>
                                            
                                            <div v-if="hoveredHourData || selectedHourData" class="flex flex-col gap-3">
                                                <div class="flex items-center justify-between">
                                                    <span class="text-base font-extrabold text-slate-900" style="font-family: 'Barlow Condensed', sans-serif;">
                                                        时段：{{ String((hoveredHourData || selectedHourData).hour).padStart(2, '0') }}:00 - {{ String(((hoveredHourData || selectedHourData).hour + 1) % 24).padStart(2, '0') }}:00
                                                    </span>
                                                    <span v-if="(hoveredHourData || selectedHourData).isGolden" class="text-[9px] bg-amber-500 text-white font-bold px-2 py-0.5 rounded-full animate-pulse">
                                                        AI 黄金时段
                                                    </span>
                                                    <span v-else-if="(hoveredHourData || selectedHourData).isConflict" class="text-[9px] bg-rose-600 text-white font-bold px-2 py-0.5 rounded-full">
                                                        排期高载警示
                                                    </span>
                                                </div>

                                                <div class="grid grid-cols-2 gap-2 text-center">
                                                    <div class="bg-white/50 border border-slate-100 rounded-xl p-2">
                                                        <p class="text-[9px] text-slate-400">预测活跃</p>
                                                        <p class="text-lg font-extrabold text-[#1c2b38] mt-0.5" style="font-family: 'Barlow Condensed', sans-serif;">{{ (hoveredHourData || selectedHourData).activeCount }} 人</p>
                                                    </div>
                                                    <div class="bg-white/50 border border-slate-100 rounded-xl p-2">
                                                        <p class="text-[9px] text-slate-400">平均专注度</p>
                                                        <p class="text-lg font-extrabold text-[#1c2b38] mt-0.5" style="font-family: 'Barlow Condensed', sans-serif;">{{ (hoveredHourData || selectedHourData).focusRate }}%</p>
                                                    </div>
                                                </div>

                                                <div v-if="(hoveredHourData || selectedHourData).behaviorRates && Object.keys((hoveredHourData || selectedHourData).behaviorRates).length > 0" class="flex flex-col gap-1.5 mt-1">
                                                    <span class="text-[10px] font-bold text-slate-600">学生倾向特征 (主要: {{ (hoveredHourData || selectedHourData).behaviorDesc }})</span>
                                                    <div class="h-2 rounded-full overflow-hidden flex bg-slate-100">
                                                        <div v-for="(rate, key) in (hoveredHourData || selectedHourData).behaviorRates" :key="key"
                                                            class="h-full transition-all duration-300 stack-segment"
                                                            :class="[
                                                                key === 'homework' ? 'bg-blue-500' :
                                                                key === 'exam' ? 'bg-purple-500' :
                                                                key === 'mistake' ? 'bg-rose-500' :
                                                                key === 'forum' ? 'bg-amber-500' : 'bg-emerald-500'
                                                            ]"
                                                            :style="{ width: rate + '%' }"
                                                            :title="key + ': ' + rate + '%'">
                                                        </div>
                                                    </div>
                                                    <div class="flex flex-wrap gap-2 text-[8px] text-slate-500 font-semibold mt-0.5">
                                                        <span v-for="(rate, key) in (hoveredHourData || selectedHourData).behaviorRates" :key="key" class="flex items-center gap-0.5">
                                                            <span class="w-1.5 h-1.5 rounded-full inline-block"
                                                                :class="[
                                                                    key === 'homework' ? 'bg-blue-500' :
                                                                    key === 'exam' ? 'bg-purple-500' :
                                                                    key === 'mistake' ? 'bg-rose-500' :
                                                                    key === 'forum' ? 'bg-amber-500' : 'bg-emerald-500'
                                                                ]"></span>
                                                            {{ key === 'homework' ? '📘 课后作业' : key === 'exam' ? '🏆 编程考试' : key === 'mistake' ? '📝 错题订正' : key === 'forum' ? '💬 答疑讨论' : '💻 沙箱调试' }} {{ rate }}%
                                                        </span>
                                                    </div>
                                                </div>

                                                <div class="bg-white/60 border border-slate-100 rounded-xl p-3 text-[10px] text-slate-600 leading-relaxed mt-1">
                                                    <p class="font-bold text-[#1c2b38] mb-1">AI 辅导排期建议：</p>
                                                    <p>{{ (hoveredHourData || selectedHourData).aiRec }}</p>
                                                </div>

                                                <div v-if="(hoveredHourData || selectedHourData).isConflict" class="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-2.5 text-[9px] leading-relaxed flex gap-1.5 items-start mt-0.5">
                                                    <i class="ph ph-warning-circle text-xs shrink-0 mt-0.5 text-rose-600"></i>
                                                    <div>
                                                        <strong class="font-bold">排期容量冲突！</strong>
                                                        当前时段已安排 {{ (hoveredHourData || selectedHourData).tasks.length }} 项进行中任务，继续下发可能引发学生脑力过载，建议选择其他空档时段或推迟任务。
                                                    </div>
                                                </div>
                                            </div>

                                            <div v-else class="text-center py-12 text-xs text-slate-400">
                                                <i class="ph ph-hand-pointing text-2xl mb-2 text-slate-300 block animate-bounce"></i>
                                                请在左侧时间轴悬停或点击小时卡片进行决策分析
                                            </div>
                                        </div>

                                        <button v-if="hoveredHourData || selectedHourData"
                                            @click="openInteractionTaskFromScheduler(hoveredHourData || selectedHourData)"
                                            class="w-full mt-4 py-2.5 rounded-xl bg-[#1c2b38] hover:bg-[#253645] text-white text-[11px] font-bold shadow-md transition-all flex items-center justify-center gap-1.5 btn-micro">
                                            <i class="ph ph-calendar-plus text-sm"></i>
                                            在该时段快速预约排期任务
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                    <div v-show="activeTab === 'profile'" class="grid grid-cols-1 xl:grid-cols-[320px_1fr] gap-6 xl:items-start">
                        <aside class="bg-white border border-slate-200 shadow-sm p-4 flex flex-col gap-4 overflow-hidden min-h-0 max-h-[min(78vh,760px)] xl:sticky xl:top-6">
                            <div class="shrink-0 space-y-3">
                                <div>
                                    <h3 class="text-sm font-bold text-slate-800">班级学生画像</h3>
                                    <p class="text-xs text-slate-400 mt-1">选择学生后查看旅程、错题和干预状态。</p>
                                </div>
                                <form @submit.prevent="searchAndScrollToStudent" class="flex items-center gap-2">
                                    <div class="relative flex-1 min-w-0">
                                        <i class="ph ph-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm pointer-events-none"></i>
                                        <input v-model="studentSearchQuery"
                                            type="text"
                                            placeholder="输入学生姓名"
                                            class="w-full pl-8 pr-3 py-2 rounded-xl border border-slate-200 bg-white text-xs text-slate-800 placeholder:text-slate-400 outline-none focus:ring-2 focus:ring-[#1c2b38]/15 focus:border-[#1c2b38]/30"
                                            :disabled="searchingStudent" />
                                    </div>
                                    <button type="submit"
                                        :disabled="searchingStudent"
                                        class="shrink-0 px-3 py-2 rounded-xl bg-[#1c2b38] hover:bg-[#253645] text-white text-xs font-bold disabled:opacity-60 transition-colors flex items-center gap-1">
                                        <i :class="searchingStudent ? 'ph ph-spinner animate-spin' : 'ph ph-magnifying-glass'"></i>
                                        搜索
                                    </button>
                                </form>
                            </div>
                            <div ref="studentListEl" class="flex-1 overflow-y-auto min-h-0 pr-1 flex flex-col gap-2 soft-scroll">
                                <button v-for="student in studentList" :key="student.id"
                                    :data-student-id="student.id"
                                    @click="selectStudent(student)"
                                    class="p-3 rounded-xl border transition-all cursor-pointer flex flex-col gap-2 text-left shrink-0 overflow-hidden"
                                    :class="activeStudent && activeStudent.id === student.id ? 'bg-white border-[#1c2b38] shadow-md' : 'bg-white/40 border-white/60 hover:bg-white/80'">
                                    <div class="flex justify-between items-center gap-2 min-w-0">
                                        <span class="font-bold text-slate-800 text-xs truncate" :title="student.name">{{ student.name }}</span>
                                        <span class="text-[9px] px-2 py-1 rounded-lg shrink-0 whitespace-nowrap"
                                            :class="student.alert ? 'bg-red-50 text-red-500 border border-red-100' : 'bg-emerald-50 text-emerald-600'">
                                            {{ student.alert ? '待干预' : '稳定' }}
                                        </span>
                                    </div>
                                    <p class="text-[10px] text-slate-400 line-clamp-2" :title="student.goal">{{ student.goal }}</p>
                                    <div class="grid grid-cols-2 gap-2 text-[9px] text-slate-500">
                                        <span>进度 {{ student.progress }}%</span>
                                        <span>专注 {{ student.focus }}</span>
                                    </div>
                                </button>
                            </div>
                        </aside>

                        <main v-if="activeStudent" class="min-h-0 flex flex-col gap-6">
                            <div v-if="loadingDetails" class="bg-white border border-slate-200 shadow-sm p-8 text-xs text-slate-500">正在生成学生旅程画像...</div>
                            <template v-else-if="studentDetails">
                                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:items-stretch">
                                    <section class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col min-h-0 overflow-hidden">
                                        <div class="flex items-start justify-between gap-3 mb-4 shrink-0">
                                            <div class="min-w-0">
                                                <h4 class="text-base font-bold text-slate-800 truncate" :title="studentDetails.name + ' 能力诊断'">{{ studentDetails.name }} 能力诊断</h4>
                                                <p class="text-xs text-slate-400 mt-1 line-clamp-2" :title="'主线目标：' + studentDetails.goal">主线目标：{{ studentDetails.goal }}</p>
                                            </div>
                                            <span class="text-[10px] bg-[#1c2b38] text-white px-2 py-1 rounded-lg shrink-0 whitespace-nowrap">ID 20260{{ studentDetails.studentId }}</span>
                                        </div>
                                        <radar-chart :option="studentRadarOption" class="w-full h-[240px] shrink-0"></radar-chart>
                                        <div v-if="studentDetails.evidenceSummary?.length" class="mt-3 pt-3 border-t border-slate-100 shrink-0">
                                            <p class="text-[10px] font-bold text-slate-500 mb-1.5">数据来源</p>
                                            <div class="flex flex-wrap gap-1.5">
                                                <span v-for="(label, idx) in studentDetails.evidenceSummary" :key="idx"
                                                    class="text-[10px] px-2 py-1 rounded-lg bg-slate-50 text-slate-600 border border-slate-100 truncate max-w-full"
                                                    :title="label">{{ label }}</span>
                                            </div>
                                        </div>
                                    </section>

                                    <section class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col min-h-0 max-h-[min(56vh,460px)] overflow-hidden">
                                        <h4 class="text-sm font-bold text-slate-800 mb-4 shrink-0">最近学习旅程</h4>
                                        <div class="flex-1 min-h-0 overflow-y-auto soft-scroll pr-1 flex flex-col gap-4">
                                            <div class="grid grid-cols-2 gap-3 shrink-0">
                                                <div v-for="item in studentDetails.timeline" :key="item.label" class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 overflow-hidden">
                                                    <p class="text-[10px] text-slate-400 truncate" :title="item.label">{{ item.label }}</p>
                                                    <p class="text-sm font-bold mt-2 truncate"
                                                        :class="item.tone === 'risk' ? 'text-rose-700' : item.tone === 'good' ? 'text-emerald-700' : 'text-slate-800'"
                                                        :title="item.value">
                                                        {{ item.value }}
                                                    </p>
                                                </div>
                                            </div>
                                            <div class="min-h-0">
                                                <h5 class="text-xs font-bold text-slate-700 mb-2 shrink-0">卡点错题追踪</h5>
                                                <div class="flex flex-col gap-2">
                                                    <div v-for="err in studentDetails.errors" :key="err.id" class="bg-white/50 border border-white rounded-xl p-3 shrink-0 overflow-hidden">
                                                        <div class="flex items-center justify-between gap-2 min-w-0">
                                                            <span class="text-xs font-bold text-slate-800 line-clamp-2 min-w-0" :title="err.topic">{{ err.topic }}</span>
                                                            <span class="text-[9px] text-rose-600 bg-rose-50 px-2 py-1 rounded-lg shrink-0 whitespace-nowrap">{{ err.count }} 次</span>
                                                        </div>
                                                        <p class="text-[10px] text-slate-400 mt-1 truncate">{{ err.date }}</p>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </section>
                                </div>

                                <section class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col gap-4 min-h-0 max-h-[min(36vh,280px)] overflow-hidden">
                                    <div class="flex items-start justify-between gap-4 shrink-0">
                                        <div class="min-w-0">
                                            <h4 class="text-sm font-bold text-slate-800">个人干预动作</h4>
                                            <p class="text-xs text-slate-400 mt-1">提醒会进入学生端通知；补弱任务会进入作业或错题入口。</p>
                                        </div>
                                        <button @click="openInteractionTask({ title: activeStudent.goal, target: activeStudent.name, studentId: activeStudent.username || activeStudent.userId || activeStudent.id, subject: activeStudent.goal }, 'homework')"
                                            class="px-4 py-2 rounded-xl bg-white/70 border border-white text-xs font-bold text-slate-700 hover:bg-white shrink-0 whitespace-nowrap">
                                            创建个人补弱任务
                                        </button>
                                    </div>
                                    <div class="flex-1 min-h-0 overflow-y-auto soft-scroll pr-1">
                                        <div class="flex flex-col lg:flex-row gap-4 items-end">
                                            <textarea v-model="nudgeMessage" rows="3"
                                                class="flex-1 min-w-0 bg-white/60 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 resize-none soft-scroll"></textarea>
                                            <button @click="handleSendNudge" :disabled="isSendingNudge"
                                                class="px-5 py-2.5 bg-[#1c2b38] hover:bg-[#253645] text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm transition-all shrink-0">
                                                <i :class="isSendingNudge ? 'ph ph-spinner animate-spin' : 'ph ph-paper-plane-tilt'"></i>
                                                下发提醒
                                            </button>
                                        </div>
                                    </div>
                                </section>
                            </template>
                        </main>
                    </div>

                    <div v-show="activeTab === 'alerts'" class="flex flex-col gap-6">
                        <div class="bg-white border border-slate-200 shadow-sm p-5">
                            <h3 class="text-base font-bold text-slate-800 mb-1">薄弱知识点预警区</h3>
                            <p class="text-xs text-slate-500">从错误率直接生成补弱作业、短测、错题订正或 AI 学习提示。</p>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                            <article v-for="wp in (overviewStats?.weakPoints || [])" :key="wp.id" class="bg-white border border-slate-200 shadow-sm p-6 flex flex-col justify-between min-h-[260px]">
                                <div>
                                    <div class="flex justify-between items-start mb-3">
                                        <span class="text-[10px] font-bold px-2 py-1 rounded-lg bg-red-50 border border-red-100 text-red-600">
                                            全班 {{ wp.errorRate }}% 错误率
                                        </span>
                                        <span class="text-[10px] text-slate-400">{{ wp.subject }}</span>
                                    </div>
                                    <h3 class="text-base font-bold text-slate-800 mb-2 leading-snug">{{ wp.topic }}</h3>
                                    <p class="text-xs text-slate-500 leading-relaxed">{{ wp.details }}</p>
                                </div>
                                <div class="grid grid-cols-2 gap-2 mt-5">
                                    <button @click="openInteractionTask(wp, 'homework')" class="px-3 py-2.5 bg-[#1c2b38] text-white font-bold rounded-xl text-[11px]">补弱作业</button>
                                    <button @click="openInteractionTask(wp, 'quiz')" class="px-3 py-2.5 bg-white/70 border border-white text-slate-700 font-bold rounded-xl text-[11px]">短测</button>
                                    <button @click="openInteractionTask(wp, 'mistake')" class="px-3 py-2.5 bg-white/70 border border-white text-slate-700 font-bold rounded-xl text-[11px]">错题订正</button>
                                    <button @click="openInteractionTask(wp, 'ai-guide')" class="px-3 py-2.5 bg-white/70 border border-white text-slate-700 font-bold rounded-xl text-[11px]">AI 引导</button>
                                </div>
                            </article>
                        </div>
                    </div>

                    <div v-show="activeTab === 'interactions'" class="flex flex-col gap-6">
                        <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
                            <div class="bg-white border border-slate-200 shadow-sm p-5">
                                <p class="text-xs text-slate-500">进行中任务</p>
                                <p class="text-3xl font-bold text-slate-900 mt-2">{{ interactionSummary.running }}</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm p-5">
                                <p class="text-xs text-slate-500">已完成任务</p>
                                <p class="text-3xl font-bold text-emerald-700 mt-2">{{ interactionSummary.completed }}</p>
                            </div>
                            <div class="bg-white border border-slate-200 shadow-sm p-5">
                                <p class="text-xs text-slate-500">未读学生</p>
                                <p class="text-3xl font-bold text-rose-700 mt-2">{{ interactionSummary.unread }}</p>
                            </div>
                            <div class="bg-[#1c2b38] text-white rounded-2xl p-5">
                                <p class="text-xs text-white/70">平均完成率</p>
                                <p class="text-3xl font-bold mt-2">{{ responseRate }}%</p>
                            </div>
                        </div>

                        <div class="bg-white border border-slate-200 shadow-sm p-5">
                            <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-4">
                                <div>
                                    <h3 class="text-base font-bold text-slate-800">交互记录追踪</h3>
                                    <p class="text-xs text-slate-500 mt-1">这些记录可直接映射到后端 interaction_records 数据表。</p>
                                </div>
                                <div class="flex gap-2">
                                    <button v-for="filter in ['all', 'running', 'completed']" :key="filter"
                                        @click="interactionFilter = filter"
                                        class="px-3 py-2 rounded-xl text-xs font-bold border"
                                        :class="interactionFilter === filter ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200'">
                                        {{ filter === 'all' ? '全部' : filter === 'running' ? '进行中' : '已完成' }}
                                    </button>
                                </div>
                            </div>

                            <div class="flex flex-col gap-3">
                                <article v-for="record in filteredInteractionRecords" :key="record.id" class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4">
                                    <div class="grid grid-cols-1 xl:grid-cols-[1fr_180px_160px] gap-4 xl:items-center">
                                        <div class="min-w-0">
                                            <div class="flex flex-wrap items-center gap-2 mb-2">
                                                <span class="text-[10px] font-bold px-2 py-1 rounded-lg border" :class="typeMeta(record.type).cls">
                                                    <i :class="['ph', typeMeta(record.type).icon, 'mr-1']"></i>{{ typeMeta(record.type).label }}
                                                </span>
                                                <span class="text-[10px] text-slate-400">{{ record.createdAt }}</span>
                                                <span class="text-[10px] text-slate-400">{{ record.targetLabel }}</span>
                                            </div>
                                            <h4 class="text-sm font-bold text-slate-900">{{ record.title }}</h4>
                                            <p class="text-xs text-slate-500 mt-1">未读 {{ record.unreadCount }} 人 · 进行中 {{ record.pendingCount }} 人 · 已完成 {{ record.completedCount }} 人</p>
                                        </div>
                                        <div>
                                            <div class="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                                                <span>完成率</span>
                                                <strong>{{ record.completionRate }}%</strong>
                                            </div>
                                            <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
                                                <div class="h-full bg-[#1c2b38]" :style="{ width: record.completionRate + '%' }"></div>
                                            </div>
                                        </div>
                                        <button @click="repeatReminder(record)" class="px-4 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50">
                                            {{ record.status === 'completed' ? '查看效果摘要' : '补发提醒' }}
                                        </button>
                                    </div>
                                </article>
                            </div>
                        </div>
                    </div>

                    <div v-show="activeTab === 'advices'" class="flex flex-col gap-6">
                        <div class="bg-white border border-slate-200 shadow-sm p-5 flex items-start justify-between gap-4">
                            <div>
                                <h3 class="text-base font-bold text-slate-800 mb-1">AI 干预策略建议</h3>
                                <p class="text-xs text-slate-500">仅保留异步任务、错题订正、短测和 AI 引导，不包含直播答疑。</p>
                            </div>
                            <button @click="handleGenerateAdvices" :disabled="generatingAdvices"
                                class="px-4 py-2 rounded-lg bg-[#1c2b38] text-white text-xs font-bold hover:bg-slate-700 transition-all disabled:opacity-50 disabled:cursor-wait btn-micro whitespace-nowrap">
                                <i class="ph ph-sparkle mr-1"></i>{{ generatingAdvices ? 'AI 生成中...' : '生成 AI 建议' }}
                            </button>
                        </div>
                        <div class="grid grid-cols-1 gap-4">
                            <article v-for="adv in advicesList" :key="adv.id" class="bg-white border border-slate-200 shadow-sm p-5"
                                :class="!adv.active && 'opacity-50'">
                                <div class="flex flex-col lg:flex-row lg:items-center gap-4 justify-between">
                                    <div class="flex-1 min-w-0">
                                        <div class="flex flex-wrap items-center gap-2 mb-2">
                                            <span class="text-[10px] font-bold px-2 py-1 rounded-lg border" :class="typeMeta(adv.type).cls">
                                                <i :class="['ph', typeMeta(adv.type).icon, 'mr-1']"></i>{{ typeMeta(adv.type).label }}
                                            </span>
                                            <span class="text-[10px] text-slate-400">{{ adv.title }}</span>
                                        </div>
                                        <p class="text-xs font-semibold text-slate-700 leading-relaxed">{{ adv.reason }}</p>
                                        <p class="text-xs text-slate-500 mt-1 leading-relaxed">{{ adv.suggestion }}</p>
                                    </div>
                                    <button v-if="adv.active" @click="handleAdoptAdvice(adv)" :disabled="isDispatching"
                                        class="px-4 py-2.5 bg-[#1c2b38] hover:bg-[#253645] text-white font-bold rounded-xl text-xs transition-all shadow-md shrink-0">
                                        一键下发
                                    </button>
                                    <span v-else class="text-xs font-semibold text-emerald-600 border border-emerald-100 bg-emerald-50 px-3 py-2 rounded-xl shrink-0">
                                        已生成闭环记录
                                    </span>
                                </div>
                            </article>
                        </div>
                    </div>
                    <div v-show="activeTab === 'diagnosis-review'" id="teacher-learning-diagnosis-review" class="flex flex-col gap-6">
                        <TeacherLearningDiagnosisReview @show-toast="forwardDiagnosisToast" />
                    </div>

                </template>
            </div>

            <transition name="modal-slide">
                <div v-if="activeTask" v-cloak class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
                    <div class="bg-white rounded-3xl shadow-float w-full max-w-2xl overflow-hidden border border-slate-200 flex flex-col max-h-[90vh]">
                        <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/70">
                            <div>
                                <h3 class="text-base font-bold text-slate-800 flex items-center gap-2">
                                    <i :class="['ph', typeMeta(taskType).icon, 'text-[#1c2b38]']"></i>
                                    互动任务分发
                                </h3>
                                <p class="text-[11px] text-slate-500 mt-1">将教师干预写入学生端入口，并同步生成后端可持久化的交互记录。</p>
                            </div>
                            <button @click="activeTask = null" class="text-slate-400 hover:text-slate-700"><i class="ph ph-x text-lg"></i></button>
                        </div>

                        <div class="p-6 overflow-y-auto flex-1 flex flex-col gap-4">
                            <div>
                                <label class="block text-xs font-semibold text-slate-600 mb-1.5">任务类型</label>
                                <div class="grid grid-cols-2 md:grid-cols-5 gap-2">
                                    <button v-for="type in ['nudge', 'homework', 'mistake', 'quiz', 'ai-guide']" :key="type"
                                        @click="taskType = type"
                                        class="px-3 py-2 rounded-xl text-[11px] font-bold border"
                                        :class="taskType === type ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-slate-50 text-slate-600 border-slate-200'">
                                        {{ typeMeta(type).label }}
                                    </button>
                                </div>
                            </div>

                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-xs font-semibold text-slate-600 mb-1">任务标题</label>
                                    <input v-model="taskForm.title" class="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none" />
                                </div>
                                <div>
                                    <label class="block text-xs font-semibold text-slate-600 mb-1">目标对象</label>
                                    <input v-model="taskForm.targetLabel" class="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none" />
                                </div>
                                <div>
                                    <label class="block text-xs font-semibold text-slate-600 mb-1">归属课程/主题</label>
                                    <input v-model="taskForm.subject" class="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none" />
                                </div>
                                <div>
                                    <label class="block text-xs font-semibold text-slate-600 mb-1">截止时间</label>
                                    <input v-model="taskForm.deadline" class="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none" />
                                </div>
                            </div>

                            <div>
                                <label class="block text-xs font-semibold text-slate-600 mb-1">学生端说明</label>
                                <textarea v-model="taskForm.desc" rows="5" class="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none resize-none"></textarea>
                            </div>

                            <div class="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs text-slate-500">
                                <p class="font-bold text-slate-700 mb-2">后端 payload 预览</p>
                                <p>type: {{ taskType }} · target: {{ taskForm.targetLabel }} · deadline: {{ taskForm.deadline }}</p>
                            </div>
                        </div>

                        <div class="px-6 py-4 border-t border-slate-100 bg-slate-50/70 flex justify-end gap-3 shrink-0">
                            <button @click="activeTask = null" class="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50">取消</button>
                            <button @click="submitInteractionTask" :disabled="isDispatching" class="px-5 py-2.5 bg-[#1c2b38] hover:bg-[#253645] text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm">
                                <i :class="isDispatching ? 'ph ph-spinner animate-spin' : 'ph ph-broadcast'"></i>
                                下发并生成闭环记录
                            </button>
                        </div>
                    </div>
                </div>
            </transition>
        </section>
    `
};

