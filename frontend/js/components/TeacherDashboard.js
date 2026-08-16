import { ref, computed, onMounted, onUnmounted } from 'vue';
import { homeworkApi } from '../api/homework.js';
import { forumApi } from '../api/forum.js';
import { formatTime } from '../utils/helpers.js';

export default {
    name: 'TeacherDashboard',
    emits: ['show-toast'],
    setup(_, { emit }) {
        const loading = ref(true);
        const currentUser = ref(null);
        
        // 时钟状态
        const currentTime = ref('');
        const currentDate = ref('');
        
        // 模块 A 考勤状态
        const attendanceRate = ref(96.5);
        const isSigning = ref(false);
        const absentStudents = ref([
            { name: '张强', status: '缺勤' },
            { name: '赵六', status: '请假' }
        ]);

        // 模块 B AI 预警干预状态
        const alertStudents = ref([
            { name: '黄子墨', reason: '作业连续 3 次未交', type: 'homework', recordId: 'record-1', avatarSeed: 'zimo' },
            { name: '赵一诺', reason: '考试成绩下滑明显 (↓ 25%)', type: 'exam', recordId: 'record-2', avatarSeed: 'yinuo' }
        ]);
        const showInterventionModal = ref(false);
        const activeInterventionStudent = ref(null);
        const selectedInterventionType = ref('homework'); // homework, mistake

        // 模块 C 论坛求助状态（从后端实时拉取未答疑的课程答疑帖）
        const latestForumQuestions = ref([]);

        // 今日授课日程
        const todaySchedule = ref([
            { id: 1, time: '09:00 - 10:35', name: '数据结构与算法', className: '计科 2301班', room: '东302', status: 'pending' },
            { id: 2, time: '14:00 - 15:35', name: '高级前端程序设计', className: '计科 2302班', room: '西201', status: 'completed' }
        ]);

        // 待批改作业/阅卷任务
        const pendingHomeworks = ref([]);

        // 动态计算教师姓氏及问候语
        const teacherSurname = computed(() => {
            const name = currentUser.value?.real_name || currentUser.value?.username || '';
            if (!name) return '老师';
            // 中文字符提取首字作为姓氏
            if (/^[\u4e00-\u9fa5]/.test(name)) {
                return name.charAt(0);
            }
            return name;
        });

        const greetingText = computed(() => {
            const surname = teacherSurname.value;
            if (surname === '老师' || surname.length > 2) {
                return `${surname}，早上好！`;
            }
            return `${surname}老师，早上好！`;
        });

        // 格式化时间与日期
        const updateDateTime = () => {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            currentTime.value = `${hours}:${minutes}:${seconds}`;

            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const date = String(now.getDate()).padStart(2, '0');
            currentDate.value = `${year}-${month}-${date}`;
        };

        // 考勤发起签到
        const startCheckIn = (schedule) => {
            if (schedule.status === 'completed' || isSigning.value) return;
            schedule.status = 'signing';
            isSigning.value = true;
            emit('show-toast', `已成功发起 ${schedule.name} 的课堂签到`, 'success');
            
            let step = 0;
            const startRate = attendanceRate.value;
            const targetRate = 100;
            
            const interval = setInterval(() => {
                step++;
                // 模拟百分比上升至 100%
                attendanceRate.value = Math.min(targetRate, parseFloat((startRate + (targetRate - startRate) * (step / 10)).toFixed(1)));
                if (step >= 10) {
                    clearInterval(interval);
                    schedule.status = 'completed';
                    isSigning.value = false;
                    // 移除一个缺勤的学生，代表其已补签到课
                    if (absentStudents.value.length > 0) {
                        const arrived = absentStudents.value.pop();
                        emit('show-toast', `${arrived.name} 已补签到课`, 'info');
                    }
                    emit('show-toast', '签到已结束，本节课出勤率已更新为 100%', 'success');
                }
            }, 200);
        };

        // 考勤催签
        const nudgeAbsentStudents = () => {
            if (absentStudents.value.length === 0) {
                emit('show-toast', '今日全员已出勤，无需催签', 'info');
                return;
            }
            const names = absentStudents.value.map(s => s.name).join('、');
            emit('show-toast', `已通过智能终端向缺勤学生（${names}）发送一键催签提醒`, 'success');
        };

        // 触发 AI 干预弹窗
        const openIntervention = (student) => {
            activeInterventionStudent.value = student;
            selectedInterventionType.value = 'homework';
            showInterventionModal.value = true;
        };

        // 执行 AI 决策干预
        const executeIntervention = () => {
            const student = activeInterventionStudent.value;
            const type = selectedInterventionType.value;
            
            // 广播自定义干预事件，主应用 main.js 捕获后会注入到学生端的 homeworkList 和 examAlerts 中实现闭环
            window.dispatchEvent(new CustomEvent('teacher-intervention-broadcast', {
                detail: {
                    type: type === 'homework' ? 'homework' : 'mistake',
                    topic: type === 'homework' ? '【AI协同】Proxy 核心原理专项改错' : '【错题订正】双向循环链表空悬指针改错',
                    payload: {
                        title: type === 'homework' ? 'Proxy 核心原理专项改错' : '双向循环链表空悬指针改错',
                        subject: '数据结构与算法',
                        deadline: '今天 23:59',
                        desc: type === 'homework'
                            ? '根据教师发起的学情干预，请针对 Proxy getter 的 receiver 参数绑定进行详细推导与上机调试。'
                            : '根据教师发起的学情干预，请完成双向链表删除操作中指针空悬的防范编程题。',
                        priority: 'high',
                        recordId: student.recordId
                    }
                }
            }));

            emit('show-toast', `已向学生 ${student.name} 下发${type === 'homework' ? '智能补弱作业' : '错题订正任务'}`, 'success');
            
            // 移除该预警学生，以示已干预处理
            alertStudents.value = alertStudents.value.filter(s => s.name !== student.name);
            showInterventionModal.value = false;
            activeInterventionStudent.value = null;
        };

        // 论坛快捷就地回帖
        const replyForumQuestion = async (item) => {
            if (!item.replyContent.trim()) {
                emit('show-toast', '请输入回复内容', 'warning');
                return;
            }
            try {
                // 直接使用帖子的真实 id 回复
                await forumApi.createReply(item.id, {
                    author: `${teacherSurname.value}老师(教师)`,
                    avatar: currentUser.value?.avatar_url || 'https://api.dicebear.com/7.x/notionists/svg?seed=Teacher',
                    isAi: false,
                    content: item.replyContent
                });

                emit('show-toast', `已成功回复学生 ${item.studentName}，已同步至学术论坛`, 'success');

                // GSAP 淡出动画后刷新列表
                if (window.gsap) {
                    window.gsap.to(`#forum-item-${item.id}`, {
                        opacity: 0,
                        x: -30,
                        duration: 0.4,
                        onComplete: () => {
                            loadLatestForumQuestions();
                        }
                    });
                } else {
                    loadLatestForumQuestions();
                }
            } catch (err) {
                emit('show-toast', '发送回复失败，请重试', 'error');
            }
        };

        // 拉取最新未答疑的课程答疑帖
        const loadLatestForumQuestions = async () => {
            try {
                const posts = await forumApi.getUnansweredQna(5);
                latestForumQuestions.value = (posts || []).map(p => ({
                    id: p.id,
                    studentName: p.author,
                    question: p.title + (p.content ? '：' + p.content.slice(0, 80) : ''),
                    time: formatTime(p.createdAt),
                    replyContent: '',
                    showReplyInput: false
                }));
            } catch (err) {
                latestForumQuestions.value = [];
            }
        };

        // 跳转至作业管理
        const goToGrading = () => {
            window.dispatchEvent(new CustomEvent('switch-view', { detail: 't_homework' }));
        };

        // 载入待阅作业汇总
        const loadOverview = async () => {
            loading.value = true;
            try {
                const data = await homeworkApi.getTeacherHomeworkOverview();
                if (data && data.homeworks) {
                    // 仅选取前 2 个有待批改份数的作业展示在仪表盘
                    pendingHomeworks.value = data.homeworks
                        .filter(h => h.totalCount > h.gradedCount)
                        .slice(0, 2);
                }
            } catch (err) {
                emit('show-toast', '获取作业批改统计失败', 'error');
            } finally {
                loading.value = false;
            }
        };

        let timer = null;
        onMounted(async () => {
            // 获取当前登录人
            const userStr = localStorage.getItem('currentUser');
            if (userStr) {
                currentUser.value = JSON.parse(userStr);
            }
            
            updateDateTime();
            timer = setInterval(updateDateTime, 1000);
            
            await loadOverview();
            await loadLatestForumQuestions();
            
            // GSAP Stagger 入场动效
            if (window.gsap) {
                window.gsap.from(".dashboard-card", {
                    opacity: 0,
                    y: 15,
                    duration: 0.6,
                    stagger: 0.08,
                    ease: "power2.out"
                });
                
                // 圆环的 dashoffset 做平滑过渡
                const circ = document.querySelector('.attendance-circle-path');
                if (circ) {
                    const length = 251.2;
                    const offset = length - (length * attendanceRate.value) / 100;
                    window.gsap.fromTo(circ, 
                        { strokeDashoffset: length },
                        { strokeDashoffset: offset, duration: 1.2, ease: "power2.out" }
                    );
                }
            }
        });

        onUnmounted(() => {
            if (timer) clearInterval(timer);
        });

        return {
            loading,
            currentTime,
            currentDate,
            attendanceRate,
            isSigning,
            absentStudents,
            alertStudents,
            showInterventionModal,
            activeInterventionStudent,
            selectedInterventionType,
            latestForumQuestions,
            todaySchedule,
            pendingHomeworks,
            greetingText,
            teacherSurname,
            startCheckIn,
            nudgeAbsentStudents,
            openIntervention,
            executeIntervention,
            replyForumQuestion,
            goToGrading
        };
    },
    template: `
        <section class="absolute inset-0 overflow-y-auto p-10 lg:p-12 bg-slate-50">
            <div class="max-w-[1440px] mx-auto flex flex-col gap-8 relative z-10">
                
                <!-- 页头问候区 -->
                <div class="dashboard-card flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4 p-8 bg-white border border-slate-200 shadow-sm rounded-2xl">
                    <div>
                        <h2 class="text-4xl font-extrabold text-[#1c2b38]" style="font-family: 'Noto Serif SC', serif;">
                            {{ greetingText }}
                        </h2>
                        <p class="text-sm text-[#b91c1c] font-medium mt-2 leading-relaxed flex items-center gap-1">
                            <span class="inline-block w-2 h-2 rounded-full bg-[#b91c1c] animate-pulse"></span>
                            今日简报：今日您有 {{ todaySchedule.length }} 场授课安排，有 {{ pendingHomeworks.length }} 门作业急需阅卷，另有 {{ latestForumQuestions.length }} 条论坛求助未回复。
                        </p>
                    </div>
                    <div class="flex flex-col items-start lg:items-end text-slate-500 font-mono text-xs select-none">
                        <span class="text-2xl font-extrabold text-[#1c2b38] tracking-wider" style="font-family: 'Barlow Condensed', sans-serif;">{{ currentTime }}</span>
                        <span class="text-xs text-slate-400 mt-1">{{ currentDate }} | 智能教学调度中枢</span>
                    </div>
                </div>

                <!-- Bento 左右主副布局栏 -->
                <div class="grid grid-cols-1 xl:grid-cols-[1fr_460px] gap-8 items-start">
                    
                    <!-- 左侧主栏 (待批改任务 + 今日授课日程) -->
                    <div class="flex flex-col gap-8">
                        
                        <!-- 待批改作业 -->
                        <div class="dashboard-card bg-white border border-slate-200 shadow-sm p-8 rounded-2xl">
                            <div class="flex items-center justify-between mb-5">
                                <h3 class="text-base font-bold text-slate-800 flex items-center gap-1.5">
                                    <i class="ph ph-article-ny text-base text-[#1c2b38]"></i> 待批改作业与阅卷提醒
                                </h3>
                                <button @click="goToGrading" class="px-5 py-2 bg-[#1c2b38] hover:bg-[#253645] active:scale-95 text-white font-semibold tracking-wider rounded-full text-xs transition-all flex items-center gap-1 shadow-sm whitespace-nowrap shrink-0">
                                    全部作业 <i class="ph ph-arrow-right"></i>
                                </button>
                            </div>
                            
                            <div v-if="loading" class="py-8 text-center text-xs text-slate-400">正在同步班级作业汇总数据...</div>
                            <div v-else-if="pendingHomeworks.length === 0" class="py-10 text-center text-xs text-slate-400">
                                暂时没有急需批阅的作业，太棒了！
                            </div>
                            <div v-else class="flex flex-col gap-4">
                                <div v-for="hw in pendingHomeworks" :key="hw.id" class="p-5.5 bg-slate-50/60 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all hover:bg-slate-100/60">
                                    <div class="flex-1 min-w-0">
                                        <h4 class="font-bold text-sm text-slate-800 line-clamp-1">{{ hw.title }}</h4>
                                        <p class="text-xs text-slate-500 mt-1">{{ hw.subject }} · 截止时间: {{ hw.deadline }}</p>
                                        
                                        <!-- 批改进度条 -->
                                        <div class="mt-3 flex items-center gap-2 max-w-md">
                                            <div class="flex-1 bg-slate-200/80 rounded-full h-2">
                                                <div class="h-2 rounded-full bg-[#b91c1c] transition-all duration-700" :style="'width: ' + Math.round((hw.gradedCount / hw.totalCount) * 100) + '%'"></div>
                                            </div>
                                            <span class="text-xs font-bold font-mono text-slate-600 shrink-0">
                                                {{ hw.gradedCount }}/{{ hw.totalCount }} 已改
                                            </span>
                                        </div>
                                    </div>
                                    <div class="shrink-0 flex items-center gap-3">
                                        <span class="text-xs text-slate-400 font-mono">已交率 {{ Math.round((hw.totalCount / hw.classSize) * 100) }}%</span>
                                        <button @click="goToGrading" class="px-5 py-2.5 bg-[#b91c1c] hover:bg-[#991b1b] active:scale-95 text-white font-semibold tracking-wider rounded-full text-xs transition-all flex items-center gap-1.5 shadow-sm whitespace-nowrap shrink-0">
                                            <i class="ph ph-pencil-simple-line"></i> 协同阅卷
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 今日授课日程 -->
                        <div class="dashboard-card bg-white border border-slate-200 shadow-sm p-8 rounded-2xl">
                            <h3 class="text-base font-bold text-slate-800 flex items-center gap-1.5 mb-5">
                                <i class="ph ph-calendar text-base text-[#1c2b38]"></i> 今日授课安排与日程轴
                            </h3>
                            
                            <div class="relative pl-8 border-l border-slate-300/60 flex flex-col gap-8 ml-4 py-2">
                                <div v-for="sch in todaySchedule" :key="sch.id" class="relative">
                                    <!-- 节点圆圈 -->
                                    <span class="absolute -left-[33px] top-2.5 w-3.5 h-3.5 rounded-full border-2 bg-white transition-colors duration-300"
                                        :class="sch.status === 'completed' ? 'border-emerald-500' : (sch.status === 'signing' ? 'border-[#b91c1c] scale-125' : 'border-slate-400')"></span>
                                    
                                    <div class="p-5.5 bg-slate-50/60 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all hover:bg-slate-100/60">
                                        <div>
                                            <span class="text-xs font-bold font-mono tracking-wider text-slate-400">{{ sch.time }}</span>
                                            <h4 class="font-bold text-sm text-slate-800 mt-1 flex items-center gap-2">
                                                {{ sch.name }}
                                                <span v-if="sch.status === 'completed'" class="inline-flex items-center gap-0.5 px-2.5 py-1 bg-emerald-50 text-emerald-600 rounded text-[10px] font-bold border border-emerald-100">已到课</span>
                                                <span v-else-if="sch.status === 'signing'" class="inline-flex items-center gap-0.5 px-2.5 py-1 bg-rose-50 text-[#b91c1c] rounded text-[10px] font-bold border border-rose-100 animate-pulse">签到中</span>
                                            </h4>
                                            <p class="text-xs text-slate-500 mt-1">{{ sch.className }} · 教室: {{ sch.room }}</p>
                                        </div>
                                        <div class="shrink-0">
                                            <button v-if="sch.status === 'pending'" @click="startCheckIn(sch)" class="px-5 py-2.5 bg-[#1c2b38] hover:bg-[#253645] text-white font-semibold tracking-wider rounded-full text-xs transition-all flex items-center gap-1.5 active:scale-95 shadow-sm whitespace-nowrap shrink-0">
                                                <i class="ph ph-radio-button"></i> 发起签到
                                            </button>
                                            <span v-else-if="sch.status === 'signing'" class="px-5.5 py-2.5 bg-rose-50 text-[#b91c1c] border border-rose-100/50 font-semibold tracking-wider rounded-full text-xs flex items-center gap-1.5 select-none shadow-sm animate-pulse whitespace-nowrap shrink-0">
                                                <i class="ph ph-spinner animate-spin"></i> 签到中...
                                            </span>
                                            <span v-else class="px-5.5 py-2.5 bg-emerald-50 text-emerald-600 border border-emerald-100/50 font-semibold tracking-wider rounded-full text-xs flex items-center gap-1.5 select-none shadow-sm whitespace-nowrap shrink-0">
                                                <i class="ph ph-check-circle"></i> 签到完成
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>

                    <!-- 右侧副栏 (考勤看板 + AI预警干预 + 论坛求助悬挂) -->
                    <div class="flex flex-col gap-8">
                        
                        <!-- 模块 A：今日班级到课签到看板 -->
                        <div class="dashboard-card bg-white border border-slate-200 shadow-sm p-8 rounded-2xl flex flex-col gap-6">
                            <div class="flex items-center justify-between">
                                <h3 class="text-base font-bold text-slate-800 flex items-center gap-1.5">
                                    <i class="ph ph-chart-pie-slice text-base text-[#1c2b38]"></i> 班级到课签到监控
                                </h3>
                                <button @click="nudgeAbsentStudents" class="px-4.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-[#b91c1c] font-semibold tracking-wider rounded-full text-xs border border-rose-200 transition-colors flex items-center gap-1 shadow-sm whitespace-nowrap shrink-0">
                                    <i class="ph ph-bell"></i> 一键催签
                                </button>
                            </div>
                            
                            <!-- 考勤仪表盘 -->
                            <div class="flex items-center gap-8 py-3">
                                <div class="relative w-28 h-28 flex items-center justify-center shrink-0">
                                    <!-- SVG 出勤圆环 -->
                                    <svg class="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                                        <circle cx="50" cy="50" r="40" stroke="rgba(28, 43, 56, 0.06)" stroke-width="7.5" fill="transparent" />
                                        <circle cx="50" cy="50" r="40" stroke="#b91c1c" stroke-width="7.5" fill="transparent"
                                            stroke-dasharray="251.2"
                                            :stroke-dashoffset="251.2 - (251.2 * attendanceRate) / 100"
                                            stroke-linecap="round"
                                            class="attendance-circle-path transition-all duration-700 ease-out" />
                                    </svg>
                                    <div class="absolute flex flex-col items-center select-none">
                                        <span class="text-xl font-extrabold font-mono text-[#1c2b38]" style="font-family: 'Barlow Condensed', sans-serif;">{{ attendanceRate }}%</span>
                                        <span class="text-[11px] text-slate-400">当前出勤</span>
                                    </div>
                                </div>
                                <div class="flex-1 text-sm">
                                    <p class="font-bold text-slate-700">缺勤/请假学生名单：</p>
                                    <div v-if="absentStudents.length === 0" class="mt-2 text-xs text-emerald-600 font-semibold flex items-center gap-1">
                                        <i class="ph ph-check-circle"></i> 全班到齐，出勤率 100%
                                    </div>
                                    <div v-else class="mt-2 flex flex-wrap gap-1.5">
                                        <span v-for="stu in absentStudents" :key="stu.name" class="inline-flex items-center gap-1 px-3 py-1.5 rounded bg-slate-100 border border-slate-200/60 text-xs text-slate-600 font-medium">
                                            <span class="w-2 h-2 rounded-full" :class="stu.status === '请假' ? 'bg-amber-400' : 'bg-[#b91c1c]'"></span>
                                            {{ stu.name }} ({{ stu.status }})
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 模块 B：AI 学情异常预警与干预 -->
                        <div class="dashboard-card bg-white border border-slate-200 shadow-sm p-8 rounded-2xl">
                            <h3 class="text-base font-bold text-slate-800 flex items-center gap-1.5 mb-4">
                                <i class="ph ph-warning-diamond text-base text-[#1c2b38]"></i> AI 学情预警与个性化干预
                            </h3>
                            
                            <div v-if="alertStudents.length === 0" class="py-6 text-center text-xs text-slate-400">
                                <i class="ph ph-smiley-wink text-base text-emerald-500"></i> 当前暂无触发学情告警的学生
                            </div>
                            <div v-else class="flex flex-col gap-4">
                                <div v-for="student in alertStudents" :key="student.name" class="p-4 bg-slate-50/60 rounded-xl flex items-center justify-between gap-4 transition-all hover:bg-slate-100/60">
                                    <div class="flex items-center gap-3.5 min-w-0">
                                        <div class="w-9.5 h-9.5 rounded-full bg-[#1c2b38]/10 text-[#1c2b38] flex items-center justify-center font-bold text-sm shrink-0 select-none">
                                            {{ student.name.charAt(0) }}
                                        </div>
                                        <div class="min-w-0">
                                            <h4 class="font-bold text-sm text-slate-800 truncate">{{ student.name }}</h4>
                                            <p class="text-[11px] text-[#b91c1c] font-semibold mt-0.5 truncate">{{ student.reason }}</p>
                                        </div>
                                    </div>
                                    <button @click="openIntervention(student)" class="shrink-0 px-4.5 py-2 bg-[#1c2b38] hover:bg-[#253645] active:scale-95 text-white font-semibold tracking-wider rounded-full text-xs transition-all flex items-center gap-1 shadow-sm whitespace-nowrap">
                                        <i class="ph ph-lightning"></i> AI干预
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- 模块 C：论坛最新求助悬挂 -->
                        <div class="dashboard-card bg-white border border-slate-200 shadow-sm p-8 rounded-2xl">
                            <h3 class="text-base font-bold text-slate-800 flex items-center gap-1.5 mb-4">
                                <i class="ph ph-chat-circle-dots text-base text-[#1c2b38]"></i> 论坛最新未答疑求助
                            </h3>
                            
                            <div v-if="latestForumQuestions.length === 0" class="py-8 text-center text-xs text-slate-400">
                                <i class="ph ph-shield-check text-base text-emerald-500"></i> 论坛无待处理的学生求助提问
                            </div>
                            <div v-else class="flex flex-col gap-4 max-h-[420px] overflow-y-auto pr-1">
                                <div v-for="item in latestForumQuestions" :key="item.id" :id="'forum-item-' + item.id" class="p-4.5 bg-slate-50/60 rounded-xl flex flex-col gap-3.5 transition-all hover:bg-slate-100/60">
                                    <div class="flex items-center justify-between gap-2">
                                        <span class="text-xs font-bold text-[#1c2b38]">{{ item.studentName }} 提问</span>
                                        <span class="text-[10px] text-slate-400 font-mono">{{ item.time }}</span>
                                    </div>
                                    <p class="text-xs text-slate-600 leading-relaxed font-medium line-clamp-2" :title="item.question">{{ item.question }}</p>
                                    
                                    <div class="flex flex-col gap-2 mt-1">
                                        <div class="flex justify-end">
                                            <button @click="item.showReplyInput = !item.showReplyInput" class="text-xs font-semibold tracking-wider text-[#1c2b38] hover:underline flex items-center gap-1 whitespace-nowrap shrink-0">
                                                <i class="ph ph-chat-text"></i> {{ item.showReplyInput ? '取消' : '就地解答' }}
                                            </button>
                                        </div>
                                        
                                        <!-- 就地回复框 -->
                                        <div v-if="item.showReplyInput" class="flex flex-col gap-2 pt-2 border-t border-slate-200/50">
                                            <textarea v-model="item.replyContent" placeholder="在此输入解答，直接推送到论坛..." rows="2" class="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 outline-none focus:border-[#1c2b38] resize-none"></textarea>
                                            <button @click="replyForumQuestion(item)" class="self-end px-5.5 py-2 bg-[#1c2b38] hover:bg-[#253645] active:scale-95 text-white font-semibold tracking-wider rounded-full text-xs transition-colors shadow-sm whitespace-nowrap shrink-0">
                                                发布回答
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>

                </div>

            </div>

            <!-- AI干预配置模态弹窗 -->
            <transition name="fade">
                <div v-if="showInterventionModal && activeInterventionStudent" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
                    <div class="w-full max-w-md bg-white border border-slate-200/80 p-6 rounded-2xl shadow-float flex flex-col gap-4">
                        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                            <h4 class="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                                <i class="ph ph-lightning text-[#b91c1c] text-base"></i> 发起 AI 协同干预决策
                            </h4>
                            <button @click="showInterventionModal = false" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-50 hover:text-slate-700 transition-colors">
                                <i class="ph ph-x"></i>
                            </button>
                        </div>
                        
                        <div class="text-xs">
                            <p class="font-bold text-slate-700">干预对象：</p>
                            <div class="mt-1.5 p-3 bg-slate-50 border border-slate-100 rounded-xl">
                                <span class="font-bold text-slate-800">{{ activeInterventionStudent.name }}</span>
                                <span class="text-slate-400 mx-2">|</span>
                                <span class="text-[#b91c1c] font-semibold">{{ activeInterventionStudent.reason }}</span>
                            </div>
                        </div>

                        <div class="text-xs">
                            <label class="block font-bold text-slate-700 mb-1.5">干预策略：</label>
                            <div class="grid grid-cols-2 gap-2">
                                <button @click="selectedInterventionType = 'homework'" class="p-3 border rounded-xl font-bold flex flex-col items-center gap-1 transition-all"
                                    :class="selectedInterventionType === 'homework' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-600'">
                                    <i class="ph ph-sparkles text-lg"></i>
                                    智能补弱作业
                                </button>
                                <button @click="selectedInterventionType = 'mistake'" class="p-3 border rounded-xl font-bold flex flex-col items-center gap-1 transition-all"
                                    :class="selectedInterventionType === 'mistake' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-600'">
                                    <i class="ph ph-check-square-offset text-lg"></i>
                                    错题本订正任务
                                </button>
                            </div>
                        </div>

                        <div class="text-[10px] text-slate-400 leading-relaxed bg-slate-50 p-3 rounded-xl">
                            * 注：点击执行后，系统将自动基于后台关联的知识图谱薄弱项进行智能题型拼装，并作为强制性任务广播下发到该生学生的个人终端。
                        </div>

                        <div class="flex justify-end gap-2 border-t border-slate-100 pt-4 mt-1">
                            <button @click="showInterventionModal = false" class="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl text-xs font-bold transition-all">取消</button>
                            <button @click="executeIntervention" class="px-4 py-2 bg-[#b91c1c] hover:bg-[#991b1b] text-white rounded-xl text-xs font-bold transition-all shadow-sm">下发干预指令</button>
                        </div>
                    </div>
                </div>
            </transition>
        </section>
    `
};
