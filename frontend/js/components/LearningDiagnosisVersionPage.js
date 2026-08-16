import { computed, ref, watch } from 'vue';

const changeLabels = { all: '全部', added: '新增', retained: '保留', removed: '移除' };
const stageLabels = {
    KNOWLEDGE_REVIEW: '知识回顾', GUIDED_PRACTICE: '引导练习',
    CODING_PRACTICE: '编程实践', INDEPENDENT_RETEST: '独立复测'
};
const triggerLabels = {
    INITIAL: '目标生成', INITIAL_DIAGNOSIS: '初始诊断', GOAL_CHANGED: '目标变更',
    TASK_SUBMISSION: '任务完成', ACTIVITY_COMPLETED: '跨路由证据更新',
    REMEDIATION_COMPLETED: '补救任务完成', MANUAL_REFRESH: '证据更新',
    GIT_EVIDENCE_TOGGLE: 'Git 证据变化', GIT_EVIDENCE_ENABLED: '启用 Git 证据',
    GIT_EVIDENCE_DISABLED: '关闭 Git 证据'
};
const reasonLabels = {
    INITIAL_DIAGNOSIS: '初始诊断', CONSECUTIVE_FAILURES: '连续练习失误',
    PREREQUISITE_REMEDIATION: '补充前置知识', TASK_SPLIT: '任务拆分',
    BOUNDARY_CASES_IMPROVED: '边界题表现改善', REMEDIATION_COMPLETED: '补救任务完成',
    TASK_SUBMISSION: '任务完成', ACTIVITY_COMPLETED: '跨路由证据更新',
    GOAL_CHANGED: '目标变更', GIT_EVIDENCE_TOGGLE: 'Git 证据变化'
};

export default {
    name: 'LearningDiagnosisVersionPage',
    props: {
        paths: { type: Array, default: () => [] },
        currentPath: { type: Object, default: null },
        loading: Boolean
    },
    emits: ['back'],
    setup(props) {
        const selectedVersion = ref(null);
        const changeFilter = ref('all');
        const stageFilter = ref('all');
        const searchText = ref('');

        const versionRecords = computed(() => {
            const source = props.paths.length ? props.paths : (props.currentPath ? [props.currentPath] : []);
            return [...source].sort((a, b) => Number(b.path_version || 0) - Number(a.path_version || 0));
        });
        watch(versionRecords, (records) => {
            if (!records.length) return;
            const currentVersion = Number(props.currentPath?.path_version || records[0].path_version);
            if (!records.some((item) => Number(item.path_version) === Number(selectedVersion.value))) selectedVersion.value = currentVersion;
        }, { immediate: true });

        const selectedPath = computed(() => versionRecords.value.find((item) => Number(item.path_version) === Number(selectedVersion.value)) || versionRecords.value[0] || {});
        const previousPath = computed(() => versionRecords.value.find((item) => Number(item.path_version) === Number(selectedPath.value.previous_version || selectedPath.value.path_version - 1)) || {});
        const selectedTriggerLabel = computed(() => triggerLabels[selectedPath.value.trigger_type] || selectedPath.value.trigger_type || '版本更新');
        const selectedReasonLabel = computed(() => {
            const reasonCodes = selectedPath.value.change_reason_codes || [];
            const labels = reasonCodes.map((code) => reasonLabels[code] || code).filter(Boolean);
            return labels.join(' · ') || selectedTriggerLabel.value;
        });
        const currentVersion = computed(() => Number(props.currentPath?.path_version || versionRecords.value[0]?.path_version || 1));
        const isCurrentVersion = computed(() => Number(selectedPath.value.path_version) === currentVersion.value);

        const taskRows = computed(() => {
            const currentTasks = new Map((selectedPath.value.tasks || []).map((task) => [String(task.task_id), task]));
            const previousTasks = new Map((previousPath.value.tasks || []).map((task) => [String(task.task_id), task]));
            const added = new Set((selectedPath.value.added_tasks || []).map(String));
            const retained = new Set((selectedPath.value.retained_tasks || []).map(String));
            const removed = new Set((selectedPath.value.removed_tasks || []).map(String));
            const ids = [...new Set([...added, ...retained, ...removed, ...currentTasks.keys()])];
            return ids.map((taskId, index) => {
                const task = currentTasks.get(taskId) || previousTasks.get(taskId) || { task_id: taskId, title: taskId };
                const changeType = added.has(taskId) ? 'added' : removed.has(taskId) ? 'removed' : 'retained';
                const knowledgePoints = Array.isArray(task.knowledge_point_ids) ? task.knowledge_point_ids : [task.knowledge_point_ids].filter(Boolean);
                const basis = changeType === 'added'
                    ? `因${selectedReasonLabel.value}加入当前路径。`
                    : changeType === 'removed'
                        ? '当前版本已移出该任务。'
                        : '仍符合当前目标，保留已有学习进度。';
                return {
                    ...task,
                    rowNumber: `T-${String(index + 1).padStart(2, '0')}`,
                    changeType,
                    changeLabel: changeLabels[changeType],
                    stageLabel: stageLabels[task.task_type] || task.task_type || '学习任务',
                    statusLabel: String(task.status || 'PENDING').toUpperCase() === 'COMPLETED' ? '已完成' : String(task.status || '').toUpperCase() === 'IN_PROGRESS' ? '进行中' : '待完成',
                    knowledgePointLabel: knowledgePoints.join('、') || '当前目标',
                    basis
                };
            });
        });
        const stageOptions = computed(() => [...new Map(taskRows.value.map((task) => [task.task_type || task.stageLabel, task.stageLabel])).entries()]);
        const filteredTasks = computed(() => {
            const keyword = searchText.value.trim().toLowerCase();
            return taskRows.value.filter((task) => {
                if (changeFilter.value !== 'all' && task.changeType !== changeFilter.value) return false;
                if (stageFilter.value !== 'all' && String(task.task_type || task.stageLabel) !== stageFilter.value) return false;
                if (!keyword) return true;
                return [task.title, task.knowledgePointLabel, task.stageLabel, task.task_id].some((value) => String(value || '').toLowerCase().includes(keyword));
            });
        });
        const countChange = (type) => type === 'all' ? taskRows.value.length : taskRows.value.filter((task) => task.changeType === type).length;
        const selectVersion = (version) => {
            selectedVersion.value = Number(version);
            changeFilter.value = 'all';
            stageFilter.value = 'all';
            searchText.value = '';
        };
        return {
            selectedVersion, changeFilter, stageFilter, searchText, versionRecords, selectedPath,
            selectedTriggerLabel, selectedReasonLabel, currentVersion, isCurrentVersion, taskRows, stageOptions,
            filteredTasks, changeLabels, triggerLabels, reasonLabels, countChange, selectVersion
        };
    },
    template: `
      <section class="h-full overflow-y-auto bg-[#eef2f4] p-5 lg:p-7">
        <div class="max-w-[1320px] mx-auto">
          <div class="flex items-center justify-between mb-4">
            <button class="text-xs font-bold text-slate-600 flex items-center gap-2" @click="$emit('back')"><i class="ph ph-arrow-left"></i>返回学习诊断　/　路径版本管理</button>
            <span class="px-3 py-1.5 rounded-full bg-white border border-[#b91c1c]/30 text-[#b91c1c] text-[10px] font-bold">当前生效版本 · v{{ currentVersion }}</span>
          </div>

          <div class="min-h-[760px] bg-white rounded-[20px] border border-white shadow-soft overflow-hidden grid grid-cols-1 lg:grid-cols-[238px_minmax(0,1fr)]">
            <aside class="bg-[#f7f9fa] border-r border-slate-200 p-5">
              <p class="text-[10px] uppercase tracking-[0.22em] text-slate-400 font-bold">Path history</p>
              <h1 class="text-2xl font-bold text-[#1c2b38] mt-2" style="font-family:'Noto Serif SC',serif">版本记录</h1>
              <div v-if="loading && !versionRecords.length" class="mt-6 text-xs text-slate-400">正在加载版本记录</div>
              <div v-else class="mt-5 space-y-2">
                <button v-for="record in versionRecords" :key="record.path_version" class="w-full rounded-xl border p-3 text-left transition" :class="selectedVersion === record.path_version ? 'bg-white border-slate-300 shadow-sm' : 'border-transparent hover:bg-white/70'" @click="selectVersion(record.path_version)">
                  <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full" :class="selectedVersion === record.path_version ? 'bg-[#b91c1c] ring-4 ring-red-100' : 'bg-slate-300'"></span><strong class="text-xs" :class="selectedVersion === record.path_version ? 'text-[#a32923]' : 'text-slate-800'">v{{ record.path_version }} {{ Number(record.path_version) === currentVersion ? '当前版本' : '' }}</strong></div>
                  <p class="text-[10px] text-slate-400 mt-2 pl-4">{{ triggerLabels[record.trigger_type] || record.trigger_type || '版本更新' }}</p>
                </button>
              </div>
              <div class="border-t border-slate-200 mt-6 pt-5">
                <p class="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-bold">Change triggers</p>
                <div class="mt-3 space-y-3 text-xs text-slate-600"><p>学习任务完成</p><p>跨路由证据更新</p><p>目标或周期调整</p><p>Git 证据开关变化</p></div>
              </div>
            </aside>

            <main class="p-5 lg:p-6 min-w-0">
              <header class="flex items-start justify-between gap-4 pb-5 border-b border-slate-200">
                <div><p class="text-[10px] uppercase tracking-[0.22em] text-slate-400 font-bold">Version overview</p><h2 class="text-2xl font-bold text-[#1c2b38] mt-2" style="font-family:'Noto Serif SC',serif">动态学习路径 v{{ selectedPath.path_version || 1 }}</h2></div>
                <span class="px-3 py-2 rounded-lg text-[10px] font-bold border" :class="isCurrentVersion ? 'border-[#b91c1c]/30 text-[#b91c1c] bg-red-50' : 'border-slate-200 text-slate-500 bg-slate-50'">{{ isCurrentVersion ? '当前版本' : '历史版本' }}</span>
              </header>

              <section class="grid grid-cols-2 xl:grid-cols-4 gap-2.5 mt-4">
                <article class="rounded-xl border border-emerald-100 bg-emerald-50/70 p-3"><p class="text-[10px] text-emerald-700">新增任务</p><strong class="block text-xl text-emerald-800 mt-1">{{ countChange('added') }}</strong></article>
                <article class="rounded-xl border border-slate-200 bg-[#f8fafb] p-3"><p class="text-[10px] text-slate-500">保留任务</p><strong class="block text-xl text-slate-800 mt-1">{{ countChange('retained') }}</strong></article>
                <article class="rounded-xl border border-red-100 bg-red-50/70 p-3"><p class="text-[10px] text-red-700">移除任务</p><strong class="block text-xl text-red-800 mt-1">{{ countChange('removed') }}</strong></article>
                <article class="rounded-xl border border-slate-200 bg-[#f8fafb] p-3"><p class="text-[10px] text-slate-500">调整依据</p><strong class="block text-xs text-slate-800 mt-2 truncate" :title="selectedReasonLabel">{{ selectedReasonLabel }}</strong></article>
              </section>

              <section class="mt-4 min-h-[50px] rounded-xl border border-slate-200 bg-[#f8fafb] px-3 py-2 flex flex-wrap items-center gap-2">
                <div class="flex bg-[#edf2f4] rounded-lg p-1">
                  <button v-for="type in ['all','added','retained','removed']" :key="type" class="px-3 py-2 rounded-md text-[10px]" :class="changeFilter === type ? 'bg-white text-slate-900 font-bold shadow-sm' : 'text-slate-500'" @click="changeFilter = type">{{ changeLabels[type] }} {{ countChange(type) }}</button>
                </div>
                <select v-model="stageFilter" class="h-9 rounded-lg border border-slate-300 bg-white px-3 text-[10px] text-slate-600"><option value="all">全部阶段</option><option v-for="option in stageOptions" :key="option[0]" :value="option[0]">{{ option[1] }}</option></select>
                <div class="ml-auto relative min-w-[220px]"><i class="ph ph-magnifying-glass absolute left-3 top-2.5 text-slate-400"></i><input v-model="searchText" class="w-full h-9 rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-[11px] outline-none focus:border-slate-500" placeholder="搜索任务或知识点"></div>
              </section>

              <section class="mt-3 border border-slate-200 rounded-xl overflow-x-auto">
                <div class="min-w-[920px]">
                  <div class="grid grid-cols-[62px_minmax(230px,1.35fr)_105px_78px_90px_minmax(190px,1fr)] items-center min-h-[42px] px-3 bg-[#f4f7f8] text-[10px] font-bold text-slate-500"><span>编号</span><span>任务标题</span><span>学习阶段</span><span>变化</span><span>状态</span><span>调整依据</span></div>
                  <article v-for="task in filteredTasks" :key="task.task_id + task.changeType" class="grid grid-cols-[62px_minmax(230px,1.35fr)_105px_78px_90px_minmax(190px,1fr)] items-center min-h-[63px] px-3 border-t border-slate-200 text-[11px]" :class="task.changeType === 'added' ? 'bg-red-50/20 border-l-[3px] border-l-[#b91c1c]' : ''">
                    <span class="font-mono text-[10px] text-slate-500">{{ task.rowNumber }}</span>
                    <span class="min-w-0 pr-3"><strong class="block text-xs text-slate-800 truncate">{{ task.title }}</strong><small class="block text-[10px] text-slate-400 mt-1 truncate">{{ task.knowledgePointLabel }}</small></span>
                    <span><em class="not-italic px-2 py-1 rounded-full bg-[#eaf0f3] text-[#456170] text-[10px] font-bold">{{ task.stageLabel }}</em></span>
                    <span><em class="not-italic px-2 py-1 rounded-full text-[10px] font-bold" :class="task.changeType === 'added' ? 'bg-emerald-50 text-emerald-700' : task.changeType === 'removed' ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-600'">{{ task.changeLabel }}</em></span>
                    <span><em class="not-italic px-2 py-1 rounded-full text-[10px] font-bold" :class="task.statusLabel === '已完成' ? 'bg-slate-100 text-slate-600' : 'bg-amber-50 text-amber-700'">{{ task.statusLabel }}</em></span>
                    <span class="text-[10px] text-slate-600 leading-relaxed pr-2">{{ task.basis }}</span>
                  </article>
                  <div v-if="!filteredTasks.length" class="py-12 text-center text-xs text-slate-400 border-t border-slate-200">没有符合当前筛选条件的任务</div>
                </div>
              </section>

              <div class="flex gap-4 mt-3 text-[10px] text-slate-500"><span><i class="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1"></i>新增任务</span><span><i class="inline-block w-2 h-2 rounded-full bg-slate-400 mr-1"></i>保留任务</span><span><i class="inline-block w-2 h-2 rounded-full bg-red-500 mr-1"></i>移除任务</span></div>
            </main>
          </div>
        </div>
      </section>`
};
