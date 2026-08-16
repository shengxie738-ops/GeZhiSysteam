import { computed, onMounted, ref } from 'vue';
import { teacherLearningDiagnosisApi } from '../api/teacherLearningDiagnosis.js';

const SAMPLE_QUEUE = [
    {
        snapshotId: 'diag-snap-001',
        studentId: 'student-001',
        studentName: '林同学',
        className: '数据结构 1 班',
        subject: '栈与递归',
        riskLevel: 'high',
        status: 'pending',
        watched: true,
        noteCount: 2,
        evidenceScore: 82,
        updatedAt: '08-15 09:20',
        summary: '递归调用边界掌握不稳，建议继续观察后续练习中的栈帧理解与终止条件表达。',
        evidenceSummary: ['答题耗时偏高', '错题重复出现', '证据较完整'],
        notes: [
            { id: 'note-1', author: '张老师', content: '先观察两次练习结果。', createdAt: '08-15 09:05' },
            { id: 'note-2', author: '张老师', content: '关注栈帧理解。', createdAt: '08-15 09:12' }
        ]
    },
    {
        snapshotId: 'diag-snap-002',
        studentId: 'student-002',
        studentName: '周同学',
        className: '数据结构 1 班',
        subject: '哈希表',
        riskLevel: 'medium',
        status: 'reviewed',
        watched: false,
        noteCount: 1,
        evidenceScore: 68,
        updatedAt: '08-15 08:55',
        summary: '能完成基本检索，但冲突处理说明不完整，建议保留为中风险复核对象。',
        evidenceSummary: ['单次提交', '证据完整度中等'],
        notes: [
            { id: 'note-3', author: '张老师', content: '已完成审查，保留观察位。', createdAt: '08-15 08:40' }
        ]
    },
    {
        snapshotId: 'diag-snap-003',
        studentId: 'student-003',
        studentName: '陈同学',
        className: '数据结构 2 班',
        subject: '二分查找',
        riskLevel: 'low',
        status: 'follow_up',
        watched: true,
        noteCount: 0,
        evidenceScore: 91,
        updatedAt: '08-15 08:10',
        summary: '总体稳定，只需在下次课堂检测后做一次轻量复核。',
        evidenceSummary: ['证据充分', '风险较低'],
        notes: []
    }
];

const pick = (...values) => values.find((value) => value !== undefined && value !== null && value !== '');

const normalizeStatus = (status) => {
    const value = String(status || 'pending').toLowerCase();
    if (value === 'reviewed') return 'reviewed';
    if (['follow_up', 'follow-up', 'observing', 'risk_confirmed'].includes(value)) return 'follow_up';
    if (['ignored', 'risk_dismissed'].includes(value)) return 'ignored';
    if (['pending', 'review-pending', 'not_reviewed', 'not-reviewed'].includes(value)) return 'pending';
    return value;
};

const normalizeReview = (item = {}, fallback = {}) => {
    const snapshot = item.snapshot || fallback.snapshot || {};
    const reviewState = item.review_state || item.reviewState || fallback.review_state || fallback.reviewState || {};
    const watchFlag = item.watch_flag || item.watchFlag || fallback.watch_flag || fallback.watchFlag || {};
    const rawNotes = Array.isArray(item.notes) ? item.notes : (Array.isArray(fallback.notes) ? fallback.notes : []);
    const notes = rawNotes.map((note, index) => ({
        id: pick(note.id, note.note_id, note.noteId, `note-${index}`),
        author: pick(note.author, note.author_name, note.teacher_id, note.reviewer, '教师'),
        content: pick(note.content, note.comment, note.text, ''),
        createdAt: pick(note.createdAt, note.created_at, note.updatedAt, '-'),
        raw: note
    }));
    const assessments = Array.isArray(snapshot.assessments) ? snapshot.assessments : [];
    const derivedEvidenceSummary = assessments
        .map((entry) => pick(entry.label, entry.name, entry.topic, entry.knowledge_point_name, entry.knowledge_point_id))
        .filter(Boolean)
        .slice(0, 4);
    const evidenceSummary = Array.isArray(item.evidenceSummary)
        ? item.evidenceSummary
        : (Array.isArray(snapshot.evidenceSummary) ? snapshot.evidenceSummary : (Array.isArray(fallback.evidenceSummary) ? fallback.evidenceSummary : []));
    const masteryScores = assessments
        .map((entry) => Number(entry.mastery_score))
        .filter((value) => Number.isFinite(value));
    const evidenceScore = Number(pick(
        item.evidenceScore,
        item.evidence_score,
        snapshot.evidence_score,
        snapshot.evidenceScore,
        masteryScores.length ? Math.round(masteryScores.reduce((sum, value) => sum + value, 0) / masteryScores.length) : '',
        fallback.evidenceScore,
        0
    ));

    const snapshotId = String(pick(
        item.snapshotId,
        item.snapshot_id,
        snapshot.id,
        reviewState.snapshot_id,
        reviewState.snapshotId,
        item.recordKey,
        item.record_key,
        item.id,
        fallback.snapshotId,
        ''
    ));
    const studentId = String(pick(
        item.studentId,
        item.student_id,
        snapshot.student_id,
        reviewState.student_id,
        fallback.studentId,
        ''
    ));

    return {
        snapshotId,
        studentId,
        studentName: pick(item.studentName, item.student_name, snapshot.student_name, snapshot.studentName, snapshot.student, fallback.studentName, '未命名学生'),
        className: pick(item.className, item.class_name, snapshot.class_name, snapshot.className, snapshot.class, fallback.className, '未分班'),
        subject: pick(item.subject, item.topic, snapshot.subject, snapshot.topic, fallback.subject, '学习诊断'),
        riskLevel: pick(item.riskLevel, item.risk_level, snapshot.risk_level, reviewState.risk_level, fallback.riskLevel, 'medium'),
        status: normalizeStatus(pick(reviewState.status, item.status, item.reviewStatus, fallback.status, 'pending')),
        watched: Boolean(pick(watchFlag.pinned, watchFlag.watched, item.watched, item.isWatched, fallback.watched, false)),
        noteCount: Number(pick(item.noteCount, item.note_count, notes.length, fallback.noteCount, notes.length, 0)),
        evidenceScore,
        updatedAt: pick(reviewState.updated_at, reviewState.updatedAt, watchFlag.updated_at, item.updatedAt, item.updated_at, fallback.updatedAt, '-'),
        reviewer: pick(reviewState.teacher_id, item.reviewer, item.reviewerName, fallback.reviewer, ''),
        summary: pick(item.summary, reviewState.comment, snapshot.summary, snapshot.diagnosis, fallback.summary, '暂无审查摘要。'),
        evidenceSummary: evidenceSummary.length ? evidenceSummary : derivedEvidenceSummary,
        notes,
        raw: item
    };
};

const statusMeta = (status) => ({
    pending: { label: '待审查', cls: 'bg-amber-50 text-amber-700 border-amber-100', dot: 'bg-amber-500' },
    reviewed: { label: '已审查', cls: 'bg-emerald-50 text-emerald-700 border-emerald-100', dot: 'bg-emerald-500' },
    follow_up: { label: '待复核', cls: 'bg-rose-50 text-rose-700 border-rose-100', dot: 'bg-rose-500' },
    ignored: { label: '已忽略', cls: 'bg-slate-100 text-slate-600 border-slate-200', dot: 'bg-slate-400' }
}[status] || { label: '待审查', cls: 'bg-amber-50 text-amber-700 border-amber-100', dot: 'bg-amber-500' });

const riskMeta = (riskLevel) => ({
    high: { label: '高风险', cls: 'bg-rose-50 text-rose-700 border-rose-100' },
    medium: { label: '中风险', cls: 'bg-amber-50 text-amber-700 border-amber-100' },
    low: { label: '低风险', cls: 'bg-emerald-50 text-emerald-700 border-emerald-100' }
}[riskLevel] || { label: '中风险', cls: 'bg-amber-50 text-amber-700 border-amber-100' });

export default {
    name: 'TeacherLearningDiagnosisReview',
    emits: ['show-toast'],
    setup(_, { emit }) {
        const loading = ref(true);
        const saving = ref(false);
        const activeFilter = ref('all');
        const searchText = ref('');
        const reviewQueue = ref([]);
        const activeReview = ref(null);
        const noteDraft = ref('');
        const loadError = ref('');

        const deriveQueue = (items) => items
            .map((item) => normalizeReview(item))
            .sort((a, b) => {
                const rank = { high: 0, medium: 1, low: 2 };
                const statusRank = { pending: 0, follow_up: 1, reviewed: 2, ignored: 3 };
                const riskDiff = (rank[a.riskLevel] ?? 9) - (rank[b.riskLevel] ?? 9);
                if (riskDiff !== 0) return riskDiff;
                const statusDiff = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
                if (statusDiff !== 0) return statusDiff;
                return String(b.updatedAt).localeCompare(String(a.updatedAt));
            });

        const queueSummary = computed(() => ({
            pending: reviewQueue.value.filter((item) => item.status === 'pending').length,
            reviewed: reviewQueue.value.filter((item) => item.status === 'reviewed').length,
            watched: reviewQueue.value.filter((item) => item.watched).length,
            highRisk: reviewQueue.value.filter((item) => item.riskLevel === 'high').length
        }));

        const filteredQueue = computed(() => {
            let items = [...reviewQueue.value];
            if (activeFilter.value === 'pending') {
                items = items.filter((item) => item.status === 'pending');
            } else if (activeFilter.value === 'high-risk') {
                items = items.filter((item) => item.riskLevel === 'high' || item.status === 'follow_up');
            } else if (activeFilter.value === 'watched') {
                items = items.filter((item) => item.watched);
            } else if (activeFilter.value === 'reviewed') {
                items = items.filter((item) => item.status === 'reviewed');
            }

            const keyword = searchText.value.trim().toLowerCase();
            if (keyword) {
                items = items.filter((item) => [
                    item.studentName,
                    item.className,
                    item.subject,
                    item.snapshotId,
                    item.summary
                ].join(' ').toLowerCase().includes(keyword));
            }
            return items;
        });

        const activeStatus = computed(() => statusMeta(activeReview.value?.status));
        const activeRisk = computed(() => riskMeta(activeReview.value?.riskLevel));
        const noteHistory = computed(() => activeReview.value?.notes || []);
        const topEvidence = computed(() => (activeReview.value?.evidenceSummary || []).slice(0, 5));
        const reviewProgress = computed(() => {
            const total = reviewQueue.value.length || 1;
            return Math.round((queueSummary.value.reviewed / total) * 100);
        });

        const selectReview = async (item) => {
            const snapshotId = typeof item === 'string' ? item : item?.snapshotId;
            if (!snapshotId) return;
            activeReview.value = reviewQueue.value.find((review) => review.snapshotId === snapshotId) || null;
            const result = await teacherLearningDiagnosisApi.getReviewDetail(snapshotId).catch(() => null);
            if (result) {
                const merged = normalizeReview(result, activeReview.value || {});
                reviewQueue.value = reviewQueue.value.map((review) => (
                    review.snapshotId === snapshotId ? { ...review, ...merged } : review
                ));
                activeReview.value = merged;
            }
            noteDraft.value = activeReview.value?.notes?.[0]?.content || '';
        };

        const loadQueue = async () => {
            loading.value = true;
            loadError.value = '';
            try {
                const reviewResult = await teacherLearningDiagnosisApi.listReviews().catch(() => null);
                const rawItems = Array.isArray(reviewResult)
                    ? reviewResult
                    : (reviewResult?.reviews || reviewResult?.items || reviewResult?.data || []);
                const nextQueue = rawItems.length ? deriveQueue(rawItems) : deriveQueue(SAMPLE_QUEUE);
                reviewQueue.value = nextQueue;
                if (!activeReview.value || !nextQueue.some((item) => item.snapshotId === activeReview.value.snapshotId)) {
                    activeReview.value = nextQueue[0] || null;
                    noteDraft.value = activeReview.value?.notes?.[0]?.content || '';
                }
            } catch (error) {
                loadError.value = error?.message || '加载失败';
                reviewQueue.value = deriveQueue(SAMPLE_QUEUE);
                activeReview.value = reviewQueue.value[0] || null;
            } finally {
                loading.value = false;
            }
        };

        const patchLocalRecord = (snapshotId, patch = {}) => {
            reviewQueue.value = reviewQueue.value.map((item) => (
                item.snapshotId === snapshotId ? { ...item, ...patch } : item
            ));
            if (activeReview.value?.snapshotId === snapshotId) {
                activeReview.value = { ...activeReview.value, ...patch };
            }
        };

        const submitNote = async () => {
            const snapshotId = activeReview.value?.snapshotId;
            const content = noteDraft.value.trim();
            if (!snapshotId || !content || saving.value) return;

            saving.value = true;
            try {
                const result = await teacherLearningDiagnosisApi.addNote(snapshotId, {
                    comment: content,
                    note_type: 'teacher_review'
                });
                const merged = normalizeReview(result, activeReview.value || {});
                patchLocalRecord(snapshotId, merged);
                noteDraft.value = '';
                emit('show-toast', '备注已保存', 'success');
            } catch (error) {
                emit('show-toast', `备注保存失败：${error?.message || '未知错误'}`, 'error');
            } finally {
                saving.value = false;
            }
        };

        const markReviewed = async (status = 'reviewed') => {
            const snapshotId = activeReview.value?.snapshotId;
            if (!snapshotId || saving.value) return;

            const backendStatus = String(status || 'REVIEWED').toUpperCase() === 'FOLLOW_UP'
                ? 'OBSERVING'
                : String(status || 'REVIEWED').toUpperCase();

            saving.value = true;
            try {
                const result = await teacherLearningDiagnosisApi.markReviewed(snapshotId, {
                    status: backendStatus,
                    comment: noteDraft.value.trim()
                });
                const merged = normalizeReview(result, activeReview.value || {});
                patchLocalRecord(snapshotId, merged);
                emit('show-toast', backendStatus === 'OBSERVING' ? '已标记为待复核' : '已标记为已审查', 'success');
            } catch (error) {
                emit('show-toast', `状态保存失败：${error?.message || '未知错误'}`, 'error');
            } finally {
                saving.value = false;
            }
        };

        const toggleWatch = async () => {
            const snapshotId = activeReview.value?.snapshotId;
            const studentId = activeReview.value?.studentId || activeReview.value?.raw?.snapshot?.student_id;
            if (!snapshotId || !studentId || saving.value) return;

            saving.value = true;
            try {
                const nextWatched = !activeReview.value.watched;
                const result = await teacherLearningDiagnosisApi.toggleWatch(studentId, {
                    watched: nextWatched,
                    reason: nextWatched ? 'teacher_follow_up' : ''
                });
                const merged = normalizeReview(result, activeReview.value || {});
                patchLocalRecord(snapshotId, merged);
                emit('show-toast', nextWatched ? '已加入关注' : '已取消关注', 'success');
            } catch (error) {
                emit('show-toast', `关注状态更新失败：${error?.message || '未知错误'}`, 'error');
            } finally {
                saving.value = false;
            }
        };

        onMounted(loadQueue);

        return {
            loading,
            saving,
            activeFilter,
            searchText,
            reviewQueue,
            activeReview,
            noteDraft,
            loadError,
            filteredQueue,
            queueSummary,
            activeStatus,
            activeRisk,
            noteHistory,
            topEvidence,
            reviewProgress,
            statusMeta,
            riskMeta,
            loadQueue,
            selectReview,
            markReviewed,
            toggleWatch,
            submitNote
        };
    },
    template: `
        <section class="absolute inset-0 overflow-y-auto p-8 lg:p-10 bg-slate-50">
            <div class="max-w-[1500px] mx-auto flex flex-col gap-7">
                <div class="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-5">
                    <div>
                        <div class="flex items-center gap-3 mb-3">
                            <span class="w-11 h-11 rounded-2xl bg-[#1c2b38] text-white flex items-center justify-center shadow-sm">
                                <i class="ph ph-clipboard-text text-xl"></i>
                            </span>
                            <div>
                                <h2 class="text-3xl font-extrabold text-[#1c2b38]" style="font-family:'Noto Serif SC',serif;">学习诊断审查</h2>
                                <p class="text-xs text-slate-400 mt-1">仅处理教师侧审查、监督、备注与关注状态</p>
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <span class="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-600">待审查 {{ queueSummary.pending }}</span>
                            <span class="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-600">已审查 {{ queueSummary.reviewed }}</span>
                            <span class="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-bold text-slate-600">关注中 {{ queueSummary.watched }}</span>
                            <span class="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-bold text-[#b91c1c]">高风险 {{ queueSummary.highRisk }}</span>
                        </div>
                    </div>
                    <div class="bg-white border border-slate-200 rounded-2xl shadow-sm p-4 min-w-[280px]">
                        <div class="flex items-center justify-between text-xs text-slate-500 mb-2">
                            <span>审查完成度</span>
                            <strong class="text-[#1c2b38]">{{ reviewProgress }}%</strong>
                        </div>
                        <div class="h-2 rounded-full bg-slate-100 overflow-hidden">
                            <div class="h-full bg-[#1c2b38] transition-all" :style="{ width: reviewProgress + '%' }"></div>
                        </div>
                    </div>
                </div>

                <div v-if="loadError" class="bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl px-4 py-3 text-xs font-semibold">{{ loadError }}</div>

                <div class="grid grid-cols-1 xl:grid-cols-[430px_1fr] gap-7 items-start">
                    <aside class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5 flex flex-col gap-4 xl:sticky xl:top-0">
                        <div class="flex items-center justify-between gap-3">
                            <div>
                                <h3 class="text-base font-bold text-slate-800">审查队列</h3>
                                <p class="text-xs text-slate-400 mt-1">{{ filteredQueue.length }} 条匹配记录</p>
                            </div>
                            <button @click="loadQueue" :disabled="loading" class="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 hover:bg-white flex items-center justify-center">
                                <i :class="loading ? 'ph ph-spinner animate-spin' : 'ph ph-arrow-clockwise'"></i>
                            </button>
                        </div>

                        <div class="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2">
                            <i class="ph ph-magnifying-glass text-slate-400"></i>
                            <input v-model="searchText" type="text" placeholder="搜索学生、班级、主题" class="w-full bg-transparent text-xs text-slate-700 outline-none placeholder:text-slate-400">
                        </div>

                        <div class="grid grid-cols-4 gap-2">
                            <button v-for="filter in [
                                { id: 'all', label: '全部' },
                                { id: 'pending', label: '待审' },
                                { id: 'high-risk', label: '风险' },
                                { id: 'watched', label: '关注' }
                            ]" :key="filter.id"
                                @click="activeFilter = filter.id"
                                class="h-9 rounded-xl border text-[11px] font-bold transition-all"
                                :class="activeFilter === filter.id ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'">
                                {{ filter.label }}
                            </button>
                        </div>

                        <div class="flex flex-col gap-3 max-h-[calc(100vh-330px)] overflow-y-auto pr-1">
                            <button v-for="item in filteredQueue" :key="item.snapshotId" @click="selectReview(item)"
                                class="text-left rounded-2xl border p-4 transition-all"
                                :class="activeReview && activeReview.snapshotId === item.snapshotId ? 'bg-[#1c2b38] text-white border-[#1c2b38] shadow-md' : 'bg-slate-50/60 border-slate-200 hover:bg-white'">
                                <div class="flex items-start justify-between gap-3">
                                    <div class="min-w-0">
                                        <div class="flex items-center gap-2">
                                            <span class="w-2 h-2 rounded-full" :class="statusMeta(item.status).dot"></span>
                                            <strong class="text-sm truncate">{{ item.studentName }}</strong>
                                        </div>
                                        <p class="text-[11px] mt-1" :class="activeReview && activeReview.snapshotId === item.snapshotId ? 'text-white/65' : 'text-slate-400'">{{ item.className }} · {{ item.subject }}</p>
                                    </div>
                                    <span class="shrink-0 rounded-lg border px-2 py-0.5 text-[10px] font-bold"
                                        :class="activeReview && activeReview.snapshotId === item.snapshotId ? 'border-white/20 bg-white/10 text-white' : riskMeta(item.riskLevel).cls">
                                        {{ riskMeta(item.riskLevel).label }}
                                    </span>
                                </div>
                                <p class="mt-3 line-clamp-2 text-xs leading-relaxed" :class="activeReview && activeReview.snapshotId === item.snapshotId ? 'text-white/80' : 'text-slate-600'">{{ item.summary }}</p>
                                <div class="mt-4 flex items-center justify-between text-[10px]" :class="activeReview && activeReview.snapshotId === item.snapshotId ? 'text-white/55' : 'text-slate-400'">
                                    <span>证据 {{ item.evidenceScore }}%</span>
                                    <span>{{ item.updatedAt }}</span>
                                </div>
                            </button>
                        </div>
                    </aside>

                    <main class="min-w-0">
                        <div v-if="loading" class="bg-white border border-slate-200 shadow-sm rounded-2xl p-10 text-center text-sm text-slate-400">正在加载诊断审查数据...</div>

                        <div v-else-if="activeReview" class="grid grid-cols-1 2xl:grid-cols-[1fr_360px] gap-7">
                            <section class="bg-white border border-slate-200 shadow-sm rounded-2xl p-7 flex flex-col gap-6">
                                <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                                    <div class="min-w-0">
                                        <div class="flex flex-wrap items-center gap-2 mb-2">
                                            <h3 class="text-2xl font-bold text-slate-900">{{ activeReview.studentName }}</h3>
                                            <span class="rounded-lg border px-2.5 py-1 text-[11px] font-bold" :class="activeStatus.cls">{{ activeStatus.label }}</span>
                                            <span class="rounded-lg border px-2.5 py-1 text-[11px] font-bold" :class="activeRisk.cls">{{ activeRisk.label }}</span>
                                            <span v-if="activeReview.watched" class="rounded-lg border border-[#1c2b38]/10 bg-[#1c2b38]/5 px-2.5 py-1 text-[11px] font-bold text-[#1c2b38]">关注中</span>
                                        </div>
                                        <p class="text-xs text-slate-400">{{ activeReview.className }} · {{ activeReview.subject }} · {{ activeReview.updatedAt }}</p>
                                    </div>
                                    <div class="flex flex-wrap gap-2">
                                        <button @click="toggleWatch" :disabled="saving" class="px-4 py-2 rounded-xl border border-slate-200 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50">
                                            {{ activeReview.watched ? '取消关注' : '加入关注' }}
                                        </button>
                                        <button @click="markReviewed('follow_up')" :disabled="saving" class="px-4 py-2 rounded-xl border border-slate-200 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50">
                                            标记待复核
                                        </button>
                                        <button @click="markReviewed('reviewed')" :disabled="saving" class="px-5 py-2 rounded-xl bg-[#1c2b38] text-white text-xs font-bold hover:bg-[#253645] shadow-sm">
                                            {{ saving ? '保存中...' : '标记已审查' }}
                                        </button>
                                    </div>
                                </div>

                                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div class="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                                        <p class="text-xs text-slate-400">证据完整度</p>
                                        <p class="text-3xl font-extrabold text-[#1c2b38] mt-2">{{ activeReview.evidenceScore }}%</p>
                                    </div>
                                    <div class="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                                        <p class="text-xs text-slate-400">备注记录</p>
                                        <p class="text-3xl font-extrabold text-slate-900 mt-2">{{ activeReview.noteCount }}</p>
                                    </div>
                                    <div class="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                                        <p class="text-xs text-slate-400">当前状态</p>
                                        <p class="text-xl font-extrabold text-slate-900 mt-3">{{ activeStatus.label }}</p>
                                    </div>
                                </div>

                                <div class="grid grid-cols-1 lg:grid-cols-[1fr_0.85fr] gap-5">
                                    <div class="rounded-2xl border border-slate-200 bg-white p-5">
                                        <h4 class="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                                            <i class="ph ph-file-text text-[#1c2b38]"></i> 审查摘要
                                        </h4>
                                        <p class="mt-3 text-sm leading-relaxed text-slate-600">{{ activeReview.summary }}</p>
                                    </div>
                                    <div class="rounded-2xl border border-slate-200 bg-white p-5">
                                        <h4 class="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                                            <i class="ph ph-tag text-[#1c2b38]"></i> 证据标签
                                        </h4>
                                        <div class="mt-3 flex flex-wrap gap-2">
                                            <span v-for="tag in topEvidence" :key="tag" class="rounded-lg bg-slate-50 border border-slate-200 px-3 py-1.5 text-[11px] font-semibold text-slate-600">{{ tag }}</span>
                                            <span v-if="!topEvidence.length" class="text-xs text-slate-400">暂无证据标签</span>
                                        </div>
                                    </div>
                                </div>

                                <div class="rounded-2xl border border-slate-200 bg-slate-50/70 p-5">
                                    <div class="flex items-center justify-between gap-3 mb-3">
                                        <h4 class="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                                            <i class="ph ph-note-pencil text-[#1c2b38]"></i> 教师备注
                                        </h4>
                                        <span class="text-[10px] text-slate-400">仅保存到教师审查模块</span>
                                    </div>
                                    <textarea v-model="noteDraft" rows="5" placeholder="记录复核判断、课堂观察或后续关注点" class="w-full resize-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#1c2b38]"></textarea>
                                    <div class="mt-3 flex justify-end">
                                        <button @click="submitNote" :disabled="saving || !noteDraft.trim()" class="px-5 py-2.5 rounded-xl bg-[#1c2b38] text-white text-xs font-bold hover:bg-[#253645] disabled:opacity-50">
                                            保存备注
                                        </button>
                                    </div>
                                </div>
                            </section>

                            <aside class="flex flex-col gap-5">
                                <section class="bg-white border border-slate-200 shadow-sm rounded-2xl p-5">
                                    <h4 class="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                                        <i class="ph ph-clock-counter-clockwise text-[#1c2b38]"></i> 审查记录
                                    </h4>
                                    <div class="mt-4 flex flex-col gap-3">
                                        <div v-for="note in noteHistory" :key="note.id" class="rounded-xl bg-slate-50 border border-slate-200 p-3">
                                            <div class="flex items-center justify-between gap-2 text-[10px] text-slate-400">
                                                <span>{{ note.author || '教师' }}</span>
                                                <span>{{ note.createdAt || '-' }}</span>
                                            </div>
                                            <p class="mt-2 text-xs leading-relaxed text-slate-700">{{ note.content }}</p>
                                        </div>
                                        <div v-if="!noteHistory.length" class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-xs text-slate-400">
                                            暂无备注记录
                                        </div>
                                    </div>
                                </section>

                                <section class="bg-[#1c2b38] text-white rounded-2xl p-5 shadow-sm">
                                    <h4 class="text-sm font-bold flex items-center gap-1.5">
                                        <i class="ph ph-shield-check"></i> 当前判定
                                    </h4>
                                    <div class="mt-4 grid grid-cols-2 gap-3">
                                        <div class="rounded-xl bg-white/8 border border-white/10 p-3">
                                            <p class="text-[10px] text-white/50">状态</p>
                                            <p class="mt-1 text-sm font-bold">{{ activeStatus.label }}</p>
                                        </div>
                                        <div class="rounded-xl bg-white/8 border border-white/10 p-3">
                                            <p class="text-[10px] text-white/50">风险</p>
                                            <p class="mt-1 text-sm font-bold">{{ activeRisk.label }}</p>
                                        </div>
                                    </div>
                                    <p class="mt-4 text-[11px] leading-relaxed text-white/60">本页不向学生端推送任务，不修改学生学习路径，仅写入教师审查状态、备注和关注标记。</p>
                                </section>
                            </aside>
                        </div>

                        <div v-else class="bg-white border border-slate-200 shadow-sm rounded-2xl p-10 text-center text-sm text-slate-400">请选择一条审查记录</div>
                    </main>
                </div>
            </div>
        </section>
    `
};
