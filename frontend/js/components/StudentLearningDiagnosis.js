import { computed, ref } from 'vue';
import LearningDiagnosisEvidenceModal from './LearningDiagnosisEvidenceModal.js';
import LearningDiagnosisVersionPage from './LearningDiagnosisVersionPage.js';
import LearningDiagnosisGoalModal from './LearningDiagnosisGoalModal.js';
import LearningKnowledgeReviewPage from './LearningKnowledgeReviewPage.js';
import LearningGuidedPracticePage from './LearningGuidedPracticePage.js';
import LearningCodingPracticePage from './LearningCodingPracticePage.js';
import LearningIndependentRetestPage from './LearningIndependentRetestPage.js';
import { useLearningDiagnosis } from '../hooks/useLearningDiagnosis.js';

const evidenceTypeLabel = {
    ASSIGNMENT: '作业', EXAM_WRONG: '考试错题', RANKED_RESULT: '排位赛',
    SANDBOX: '代码沙箱', GIT: 'Git', COURSEWARE: '课件'
};

export default {
    name: 'StudentLearningDiagnosis',
    components: {
        LearningDiagnosisEvidenceModal, LearningDiagnosisVersionPage, LearningDiagnosisGoalModal,
        LearningKnowledgeReviewPage, LearningGuidedPracticePage, LearningCodingPracticePage,
        LearningIndependentRetestPage
    },
    props: { currentUser: { type: Object, default: null } },
    emits: ['show-toast'],
    setup(props, { emit }) {
        const state = useLearningDiagnosis(computed(() => props.currentUser), emit);
        const selectedMetricKey = ref(null);
        const score = (key) => Math.round(Number(state.primaryAssessment.value?.[key] || 0));
        const metrics = computed(() => [
            { key: 'mastery_score', label: '掌握度', value: score('mastery_score'), tone: '#b91c1c', detail: '当前掌握度情况' },
            { key: 'practice_score', label: '实践应用度', value: score('practice_score'), tone: '#2f6174', detail: state.gitEnabled.value ? '已纳入 Git 的实践应用度' : '当前实践应用度（Git 未纳入）' },
            { key: 'confidence', label: '置信度', value: Math.round(Number(state.primaryAssessment.value?.confidence || 0) * 100), tone: '#6b7280', detail: '当前诊断结论置信度' }
        ]);
        const displayEvidence = computed(() => state.evidence.value.slice(0, 4).map((item) => ({
            ...item,
            typeLabel: evidenceTypeLabel[item.source_type] || item.source_type || '学习活动',
            reliability: Math.round(Number(item.provenance?.reliability || 0) * 100),
            pointLabel: (item.knowledge_point_ids || []).join('、') || '当前目标'
        })));
        const masteryScore = computed(() => metrics.value[0].value);
        const practiceScore = computed(() => metrics.value[1].value);
        const confidence = computed(() => metrics.value[2].value);
        const openMetric = (metric) => {
            selectedMetricKey.value = selectedMetricKey.value === metric.key ? null : metric.key;
        };
        const collapseMetric = () => { selectedMetricKey.value = null; };
        const taskPage = computed(() => ({
            knowledge: 'learning-knowledge-review-page', guided: 'learning-guided-practice-page',
            coding: 'learning-coding-practice-page', retest: 'learning-independent-retest-page'
        }[state.activePage.value]));
        const emptyPathStages = ['基础理解', '引导练习', '编程实践', '独立复测'];
        return { ...state, metrics, displayEvidence, masteryScore, practiceScore, confidence, selectedMetricKey, openMetric, collapseMetric, taskPage, emptyPathStages };
    },
    mounted() {
        if (document.getElementById('learning-diagnosis-motion')) return;
        const style = document.createElement('style');
        style.id = 'learning-diagnosis-motion';
        style.textContent = `
          .metric-card{position:relative;overflow:hidden;transition:transform .24s ease,box-shadow .24s ease,grid-column .24s ease}
          .metric-card:before{content:'';position:absolute;inset:-45%;background:linear-gradient(115deg,transparent 38%,rgba(255,255,255,.72) 50%,transparent 62%);transform:translateX(-70%) rotate(8deg);transition:transform .55s ease}
          .metric-flow:before{animation:metric-flow 2.1s linear infinite}
          @keyframes metric-flow{0%{transform:translateX(-70%) rotate(8deg)}100%{transform:translateX(70%) rotate(8deg)}}
          .metric-card:hover{transform:translateY(-5px);box-shadow:0 14px 28px rgba(28,43,56,.12)}
          .metric-card:hover:before{transform:translateX(70%) rotate(8deg)}
          .metrics-grid{position:relative;min-height:82px}
          .metric-card.metric-expanded{position:absolute;inset:0;height:190px;transform:scale(1);z-index:20;box-shadow:0 22px 42px rgba(28,43,56,.24);padding:22px;transition:transform .3s ease,box-shadow .3s ease,opacity .3s ease}
          .metric-card.metric-expanded .progress-ring{width:108px;height:108px;margin:0 auto}
          .metric-card.metric-expanded .progress-ring:after{inset:10px}
          .metric-card.metric-expanded .progress-ring span{font-size:24px}
          .metric-card.metric-expanded .metric-note{display:block}
          .progress-ring{width:58px;height:58px;border-radius:999px;display:grid;place-items:center;background:conic-gradient(var(--ring-color) var(--progress),#dbe3e7 0);position:relative;transition:width .24s ease,height .24s ease}
          .progress-ring:after{content:'';position:absolute;inset:6px;border-radius:999px;background:#f4f7f8}
          .progress-ring span{position:relative;z-index:1;font-size:14px;font-weight:800;color:#1c2b38}
          .metric-note{display:none}
        `;
        document.head.appendChild(style);
    },
    template: `
      <section class="absolute inset-0 overflow-hidden bg-[#eef2f4]">
        <component v-if="taskPage" :is="taskPage" :task="activeTask" :code="code" :hint-level="currentHintLevel" :hint="currentHint" :execution="lastExecution" :loading="loading" @back="goHome" @hint="requestHint" @run="runTaskCode" @reset="resetTaskCode" @submit="submitTask" @update:code="updateTaskCode"></component>
        <learning-diagnosis-version-page v-else-if="activePage === 'version'" :paths="pathHistory" :current-path="path" :loading="loading" @back="goHome"></learning-diagnosis-version-page>
        <div v-else class="h-full overflow-y-auto p-5 lg:p-8">
          <div v-if="initializing" class="max-w-[1240px] mx-auto bg-white rounded-2xl border border-white p-8 text-center"><p class="text-sm font-bold text-slate-700">正在恢复诊断数据</p></div>
          <div v-else class="max-w-[1240px] mx-auto">
            <header class="flex items-start justify-between gap-4 pb-5 border-b border-slate-300/70">
              <div><p class="text-[10px] uppercase tracking-[0.24em] text-slate-500 font-bold">Learning diagnosis / Agent</p><h1 class="text-3xl font-bold text-[#1c2b38] mt-2" style="font-family:'Noto Serif SC',serif">编程学习诊断</h1><p class="text-sm text-slate-500 mt-1">把学习证据转成下一步可执行的动态路径</p></div>
              <div class="flex flex-col items-end gap-2"><span class="px-3 py-1.5 rounded-full bg-white border border-[#b91c1c]/25 text-[#b91c1c] text-[10px] font-bold">{{ session ? '诊断会话进行中 · v' + (snapshot?.version || 1) : '等待设置目标' }}</span><button :disabled="!session" class="min-h-[34px] px-3 rounded-lg border text-[10px] font-bold disabled:cursor-not-allowed disabled:opacity-45" :class="gitEnabled ? 'border-red-300 bg-red-50 text-red-700' : 'border-slate-300 bg-white text-slate-700'" @click="toggleGit">{{ gitEnabled ? '已纳入 Git 证据' : '纳入 Git 证据' }}</button><span class="text-[10px] text-slate-400">Git 证据默认关闭</span></div>
            </header>
            <div class="grid grid-cols-1 xl:grid-cols-[1.35fr_0.9fr] gap-4 mt-5">
              <article class="bg-white border border-white rounded-2xl p-6 shadow-soft"><p class="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-bold">Current goal</p><h2 class="text-2xl font-bold text-[#1c2b38] mt-2">{{ session ? (session.goal?.course_name || session.goal?.course || '学习目标') : '尚未设置学习目标' }}</h2><p class="text-sm text-slate-500 mt-2">{{ session ? (session.goal?.raw_goal_text || session.goal?.self_reported_difficulty || '等待目标解析') : '制定目标后，Agent 将检索真实学习资源并生成动态路径。' }}</p><div class="flex gap-2 mt-5"><button v-if="session" :disabled="!tasks.length" class="min-h-[40px] px-4 rounded-xl bg-[#1c2b38] text-white text-xs font-bold disabled:cursor-not-allowed disabled:opacity-45" @click="tasks[0] && openTask(tasks[0])">继续今日任务</button><button v-else class="min-h-[40px] px-4 rounded-xl bg-[#1c2b38] text-white text-xs font-bold" @click="openGoalModal">制定学习目标</button><button v-if="session" class="min-h-[40px] px-4 rounded-xl bg-white border border-slate-300 text-slate-700 text-xs font-bold" @click="openGoalModal">更换目标</button></div></article>
              <article class="bg-white border border-white rounded-2xl p-5 shadow-soft"><div class="flex items-center justify-between"><h2 class="text-xl font-bold text-[#1c2b38]">当前结论</h2><span class="px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 text-[10px] font-bold">{{ session ? '需复测' : '待诊断' }}</span></div><div class="metrics-grid grid grid-cols-3 gap-2 mt-4"><button v-for="metric in metrics" :key="metric.key" class="metric-card metric-flow rounded-xl bg-[#f4f7f8] border border-slate-200 p-3 text-left" :class="{ 'metric-expanded': selectedMetricKey === metric.key }" @click="openMetric(metric)" @mouseleave="selectedMetricKey === metric.key && collapseMetric()"><div class="progress-ring" :style="{ '--progress': metric.value + '%', '--ring-color': metric.tone }"><span>{{ metric.value }}%</span></div><p class="text-[11px] font-bold text-slate-600 mt-2">{{ metric.label }}</p><p class="metric-note text-[10px] text-slate-500 mt-2 text-right">{{ metric.detail }}</p></button></div></article>
            </div>
            <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
              <article class="bg-white border border-white rounded-2xl p-5 shadow-soft">
                <div class="flex items-center justify-between pb-3 border-b border-slate-200"><div><h2 class="text-xl font-bold text-[#1c2b38]">诊断证据</h2><p class="text-[10px] text-slate-400 mt-1">{{ evidence.length }} 条证据已归因到当前目标</p></div><button class="min-h-[34px] px-3 rounded-lg border border-slate-300 text-[10px] font-bold" @click="evidenceOpen = true">查看全部</button></div>
                <div v-if="displayEvidence.length" class="divide-y divide-slate-200"><article v-for="(item, index) in displayEvidence" :key="item.evidence_id || item.id || index" class="evidence-summary py-3"><div class="flex items-center justify-between gap-3"><span class="text-xs font-bold text-slate-800">{{ item.typeLabel }}</span><span class="text-[10px] text-slate-400">可靠度 {{ item.reliability }}%</span></div><p class="text-xs text-slate-600 mt-1 line-clamp-2">{{ item.summary || '已记录与当前目标相关的学习活动。' }}</p><p class="text-[10px] text-slate-400 mt-1">关联知识点：{{ item.pointLabel }}</p></article></div>
                <div v-else class="rounded-xl border border-dashed border-slate-300 bg-[#f7f9fa] p-5 mt-4"><p class="text-xs font-bold text-slate-700">当前目标尚无有效证据</p><p class="text-[10px] text-slate-500 mt-1">完成路径任务或其他路由中的关联内容后，此处会自动出现真实证据。</p></div>
              </article>
              <article class="bg-white border border-white rounded-2xl p-5 shadow-soft"><div class="flex items-center justify-between pb-3 border-b border-slate-200"><div><h2 class="text-xl font-bold text-[#1c2b38]">四阶段学习路径</h2><p class="text-[10px] text-slate-400 mt-1">{{ path ? 'Path version v' + (path.path_version || 1) : 'Path version --' }}</p></div><button :disabled="!session" class="min-h-[34px] px-3 rounded-lg border border-slate-300 text-[10px] font-bold disabled:cursor-not-allowed disabled:opacity-45" @click="openVersion">查看版本变化</button></div><div v-if="tasks.length" class="divide-y divide-slate-200"><button v-for="(task,index) in tasks" :key="task.task_id" class="w-full flex items-center gap-3 py-3 text-left" @click="openTask(task)"><span class="w-7 h-7 rounded-full bg-[#eef3f5] flex items-center justify-center text-xs font-bold">{{ index + 1 }}</span><span class="flex-1"><span class="block text-xs font-bold text-slate-800">{{ task.title }}</span><span class="block text-[10px] text-slate-400 mt-1">{{ task.task_type }} · {{ task.estimated_minutes }} 分钟</span></span><span class="text-[10px] text-slate-500">{{ task.status || '待开始' }}</span></button></div><div v-else class="divide-y divide-slate-200"><div v-for="stage in emptyPathStages" :key="stage" class="flex items-center gap-3 py-3"><span class="w-7 h-7 rounded-full bg-[#eef3f5] flex items-center justify-center text-slate-400">--</span><span class="flex-1 text-xs font-bold text-slate-600">{{ stage }}</span><span class="text-[10px] text-slate-400">待生成</span></div></div></article>
            </div>
          </div>
        </div>
        <learning-diagnosis-evidence-modal :open="evidenceOpen" :snapshot="snapshot" :evidence="evidence" @close="evidenceOpen = false"></learning-diagnosis-evidence-modal>
        <learning-diagnosis-goal-modal :open="goalModalOpen" :form="goalForm" :loading="loading" :title="session ? '更换学习目标' : '制定学习目标'" @close="goalModalOpen = false" @submit="updateGoal"></learning-diagnosis-goal-modal>
        <div v-if="gitRiskOpen" class="fixed inset-0 z-[95] bg-slate-950/40 backdrop-blur-sm flex items-center justify-center p-4"><section class="max-w-md w-full bg-[#fcfbfa] rounded-2xl p-6 shadow-2xl"><p class="text-[10px] uppercase tracking-[0.2em] text-red-700 font-bold">Git evidence risk reminder</p><h3 class="text-xl font-bold text-slate-900 mt-2">确认纳入 Git 证据</h3><p class="text-xs text-slate-600 leading-relaxed mt-3">提交代码可能包含协作者、模板或 AI 生成内容，不能单独证明掌握。开启后仅作降权实践证据，并保留来源与不确定性。</p><div class="flex justify-end gap-2 mt-5"><button class="px-4 min-h-[40px] rounded-xl border border-slate-200 text-xs font-bold" @click="gitRiskOpen = false">暂不纳入</button><button class="px-4 min-h-[40px] rounded-xl bg-[#b91c1c] text-white text-xs font-bold" @click="confirmGit">确认开启</button></div></section></div>
      </section>`
};
