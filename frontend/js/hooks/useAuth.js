import { ref, reactive, computed, watch } from 'vue';

const studentMenus = [
    { id: 'dashboard', name: '仪表盘', icon: 'ph-squares-four', title: '学习数据总览', desc: '您的专属智能学习进度报表' },
    { id: 'pathway', name: '图谱', icon: 'ph-git-branch', title: '动态知识图谱', desc: 'AI 生成的学习路线与能力树' },
    { id: 'workspace', name: '工作台', icon: 'ph-chat-teardrop', title: '协同核心枢纽', desc: '与多智能体集群实时互动对话' },
    { id: 'learning-diagnosis', name: '学习诊断', icon: 'ph-chart-line-up', title: '编程学习诊断', desc: '基于学习证据生成动态路径与分级训练' },
    { id: 'knowledge', name: '知识库', icon: 'ph-database', title: '个人私有库', desc: '专属资料 RAG 检索解析' },
    { id: 'mistakes', name: '错题本', icon: 'ph-warning-diamond', title: '错题本', desc: '汇总测试错题与 AI 错因分析' },
    { id: 'exam', name: '考试', icon: 'ph-exam', title: '考试中心', desc: '查看待考科目、进入客观题与编程考试' },
    { id: 'homework', name: '作业', icon: 'ph-article', title: '作业提交与诊断区', desc: '日常作业、阶段任务与大作业项目递交与智能诊断' },
    { id: 'courses', name: '课程库', icon: 'ph-books', title: '公共课程库', desc: '浏览数据结构、计算机程序设计等公开课件' },
    { id: 'agents', name: '智能体', icon: 'ph-robot', title: 'Agent 编排工坊', desc: '自定义与管理您的 AI 角色群' },
    { id: 'coding', name: '编程实战', icon: 'ph-code', title: '在线编程实战', desc: '在 Web 编辑器中手写算法并运行评测' },
    { id: 'academic-space', name: '学术空间', icon: 'ph-git-pull-request', title: '学术空间', desc: '整合个人代码仓库、拉取请求与论坛协作' }
];

const teacherMenus = [
    { id: 't_dashboard', name: '仪表盘', icon: 'ph-squares-four', title: '教师工作台', desc: '总览今日授课日程、待阅批改任务及 AI 学情预警' },
    { id: 't_analytics', name: '学情决策台', icon: 'ph-chart-polar', title: '班级学情分析与干预', desc: '宏观查看学情并向学生一键推送补弱干预' },    { id: 't_diagnosis_review', name: '诊断审查', icon: 'ph-clipboard-text', title: '学习诊断审查', desc: '审查、监督、备注与关注学生学习诊断情况' },
    { id: 't_space', name: '空间管理', icon: 'ph-layout', title: '学术空间管理', desc: '统一管理论坛内容、置顶公告与仓库举报审核' },
    { id: 't_exams', name: '考试管理', icon: 'ph-exam', title: '考试管理中心', desc: '创建考试、下达编程题并监控提交状态' },
    { id: 't_homework', name: '作业管理', icon: 'ph-article', title: '作业管理中心', desc: '管理班级作业提交、查看智能诊断与协同评阅' },
    { id: 't_projects', name: '项目管理', icon: 'ph-projector-screen', title: '项目实训管理', desc: '管理大作业递交与编程团队实训' },
    { id: 't_courses', name: '课程库', icon: 'ph-books', title: '课程库管理', desc: '管理公共课程库的课件资源，支持上传、删除与重命名' },
    { id: 't_lesson_prep', name: 'AI备课', icon: 'ph-notebook', title: 'AI备课中心', desc: '课件检索 · 教案生成 · 草稿编辑' },
    { id: 'agents', name: 'AI 工坊', icon: 'ph-robot', title: 'Agent 编排与预设', desc: '配置班级级公共智能体参数与 Prompt' }
];

export function useAuth(showToast, onLoginSuccess) {
    const isLoggedIn = ref(localStorage.getItem('isLoggedIn') === 'true');
    const currentUser = ref(localStorage.getItem('currentUser') ? JSON.parse(localStorage.getItem('currentUser')) : null);
    const isRegistering = ref(false);
    const isTeacherLogin = ref(localStorage.getItem('isTeacherLogin') === 'true');
    const authLoading = ref(false);
    const authForm = reactive({ username: '', password: '' });

    const currentRole = ref(localStorage.getItem('currentRole') || 'student');
    const normalizeStoredView = (role, view) => {
        if (role === 'student' && ['repository', 'forum'].includes(view)) return 'academic-space';
        if (role === 'teacher' && ['t_repository', 't_forum'].includes(view)) return 't_space';
        return view || (role === 'student' ? 'dashboard' : 't_dashboard');
    };
    const currentView = ref(normalizeStoredView(currentRole.value, localStorage.getItem('currentView')));

    const activeMenus = computed(() => currentRole.value === 'student' ? studentMenus : teacherMenus);
    const currentMenuInfo = computed(() => {
        const menu = activeMenus.value.find(m => m.id === currentView.value);
        if (!menu) {
            currentView.value = currentRole.value === 'student' ? 'dashboard' : 't_dashboard';
            return activeMenus.value[0];
        }
        return menu;
    });

    const handleAuth = () => {
        authLoading.value = true;
        setTimeout(() => {
            authLoading.value = false;
            currentUser.value = {
                username: authForm.username,
                real_name: '',
                student_id: '',
                class_name: '',
                avatar_url: ''
            };
            currentRole.value = isTeacherLogin.value ? 'teacher' : 'student';
            currentView.value = currentRole.value === 'student' ? 'dashboard' : 't_dashboard';
            isLoggedIn.value = true;
            showToast(`系统登录成功 (${currentRole.value === 'teacher' ? '教师端' : '学生端'})`);

            if (onLoginSuccess) {
                onLoginSuccess(authForm.username, currentRole.value);
            }
        }, 800);
    };

    const toggleAuthMode = () => {
        isRegistering.value = !isRegistering.value;
    };

    const handleLogout = (onLogout) => {
        isLoggedIn.value = false;
        currentUser.value = null;
        localStorage.removeItem('isLoggedIn');
        localStorage.removeItem('currentUser');
        localStorage.removeItem('currentRole');
        localStorage.removeItem('currentView');
        localStorage.removeItem('isTeacherLogin');
        localStorage.removeItem('messages');
        if (onLogout) onLogout();
    };

    // 持久化监视器
    watch(isLoggedIn, (newVal) => {
        localStorage.setItem('isLoggedIn', newVal);
        if (newVal === false || newVal === 'false') {
            window.location.href = './login/index.html';
        }
    });
    watch(currentUser, (newVal) => {
        if (newVal) {
            localStorage.setItem('currentUser', JSON.stringify(newVal));
        } else {
            localStorage.removeItem('currentUser');
        }
    }, { deep: true });
    watch(currentRole, (newVal) => {
        localStorage.setItem('currentRole', newVal);
    });
    watch(currentView, (newVal) => {
        localStorage.setItem('currentView', newVal);
    });
    watch(isTeacherLogin, (newVal) => {
        localStorage.setItem('isTeacherLogin', newVal);
    });

    return {
        isLoggedIn,
        currentUser,
        isRegistering,
        isTeacherLogin,
        authLoading,
        authForm,
        currentRole,
        currentView,
        activeMenus,
        currentMenuInfo,
        handleAuth,
        toggleAuthMode,
        handleLogout
    };
}
