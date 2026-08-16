import { computed, onMounted, reactive, ref } from 'vue';
import { teacherLessonPrepApi } from '../api/teacherLessonPrep.js';

const MAX_SELECTED_RESOURCES = 10;

const asList = (value) => {
    if (Array.isArray(value)) return value.map((item) => String(item || '').trim()).filter(Boolean);
    return String(value || '').split('\n').map((item) => item.trim()).filter(Boolean);
};

const toLines = (value) => asList(value).join('\n');

// 截断到后端 LessonPlanExportRequest 的字段上限，避免导出请求被 422 拒绝
const clipText = (value, max) => String(value || '').trim().slice(0, max);

const normalizeResource = (item = {}) => ({
    id: String(item.id || item.resource_id || ''),
    course: item.course || '未分类课程',
    name: item.name || item.filename || '未命名课件',
    extension: String(item.extension || item.file_type || '').toLowerCase(),
    sizeBytes: Number(item.size_bytes || item.sizeBytes || 0),
    searchable: item.searchable !== false,
    indexStatus: item.index_status || item.indexStatus || '',
    frontendUrl: item.frontend_url || item.frontendUrl || ''
});

const normalizeCitation = (item = {}) => ({
    resourceId: String(item.resource_id || item.resourceId || ''),
    name: item.name || item.filename || '课件片段',
    course: item.course || '',
    page: Number(item.page || 0),
    excerpt: item.excerpt || item.text || '',
    score: Number(item.score || 0)
});

const flowToText = (flow) => {
    if (!Array.isArray(flow)) return String(flow || '');
    return flow.map((item) => {
        const stage = item?.stage || '教学环节';
        const minutes = Number(item?.minutes || 0);
        const content = item?.content || '';
        return `${stage}｜${minutes}分钟｜${content}`;
    }).join('\n');
};

const textToFlow = (value) => String(value || '').split('\n').map((line) => line.trim()).filter(Boolean).map((line) => {
    const [stage = '教学环节', minutes = '0', ...content] = line.split('｜');
    return {
        stage: stage.trim(),
        minutes: Number(String(minutes).replace(/[^0-9]/g, '')) || 0,
        content: content.join('｜').trim()
    };
});

export default {
    name: 'TeacherAiLessonPrep',
    emits: ['show-toast'],
    setup(_, { emit }) {
        const loading = ref(true);
        const resourcesLoading = ref(false);
        const aiLoading = ref(false);
        const saving = ref(false);
        const exporting = ref(false);
        const loadError = ref('');
        const resources = ref([]);
        const resourceCatalog = ref([]);
        const selectedIds = ref([]);
        const expandedCourses = ref([]);
        const activeFileType = ref('all');
        const resourceQuery = ref('');
        const config = ref({ model: 'glm-4.5-air', ai_ready: false });
        const citations = ref([]);
        const summary = ref('');
        const drafts = ref([]);
        const activeDraftId = ref('');
        const instruction = ref('');

        const lesson = reactive({
            title: '新建教学设计',
            topic: '',
            courseName: '',
            audience: '',
            durationMinutes: 45,
            objectives: '',
            keyPoints: '',
            difficulties: '',
            teachingFlow: '',
            questions: '',
            exercises: '',
            homework: ''
        });

        const resourceSummary = computed(() => ({
            total: resourceCatalog.value.length,
            pdf: resourceCatalog.value.filter((item) => item.extension === '.pdf').length,
            slides: resourceCatalog.value.filter((item) => ['.ppt', '.pptx'].includes(item.extension)).length,
            searchable: resourceCatalog.value.filter((item) => item.searchable).length
        }));

        const selectedResources = computed(() => resourceCatalog.value.filter((item) => selectedIds.value.includes(item.id)));
        const displayedResources = computed(() => (
            activeFileType.value === 'selected' ? selectedResources.value : resources.value
        ));
        const groupedResources = computed(() => {
            const groups = new Map();
            displayedResources.value.forEach((resource) => {
                if (!groups.has(resource.course)) groups.set(resource.course, []);
                groups.get(resource.course).push(resource);
            });
            return [...groups.entries()].map(([course, items]) => ({ course, items }));
        });
        const selectedSearchableCount = computed(() => selectedResources.value.filter((item) => item.searchable).length);
        const modelName = computed(() => config.value?.model || 'glm-4.5-air');
        const aiReady = computed(() => config.value?.ai_ready === true);
        const hasLessonContent = computed(() => [
            lesson.objectives,
            lesson.keyPoints,
            lesson.difficulties,
            lesson.teachingFlow,
            lesson.questions,
            lesson.exercises,
            lesson.homework
        ].some((value) => String(value || '').trim()));

        const formatSize = (bytes) => {
            const value = Number(bytes || 0);
            if (!value) return '-';
            if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
            return `${(value / (1024 * 1024)).toFixed(1)} MB`;
        };

        const fileTypeLabel = (extension) => {
            if (extension === '.pdf') return 'PDF';
            if (extension === '.pptx') return 'PPTX';
            if (extension === '.ppt') return 'PPT';
            return String(extension || 'FILE').replace('.', '').toUpperCase();
        };

        const mergeResourceCatalog = (items) => {
            const byId = new Map(resourceCatalog.value.map((item) => [item.id, item]));
            items.forEach((item) => byId.set(item.id, item));
            resourceCatalog.value = [...byId.values()];
        };

        const syncExpandedCourses = (items) => {
            const courses = [...new Set(items.map((item) => item.course))];
            if (resourceQuery.value.trim()) {
                expandedCourses.value = courses;
                return;
            }
            const visibleExpanded = expandedCourses.value.filter((course) => courses.includes(course));
            expandedCourses.value = visibleExpanded.length ? visibleExpanded : courses.slice(0, 1);
        };

        const loadResources = async () => {
            resourcesLoading.value = true;
            loadError.value = '';
            try {
                const result = await teacherLessonPrepApi.listResources({
                    file_type: ['pdf', 'ppt'].includes(activeFileType.value) ? activeFileType.value : '',
                    query: resourceQuery.value.trim()
                });
                const items = Array.isArray(result) ? result : (result?.resources || result?.items || []);
                resources.value = items.map(normalizeResource).filter((item) => item.id);
                mergeResourceCatalog(resources.value);
                syncExpandedCourses(resources.value);
            } catch (error) {
                resources.value = [];
                loadError.value = error?.message || '课件资源加载失败';
            } finally {
                resourcesLoading.value = false;
            }
        };

        const loadWorkspace = async () => {
            loading.value = true;
            loadError.value = '';
            const [configResult, resourceResult, draftResult] = await Promise.allSettled([
                teacherLessonPrepApi.getConfig(),
                teacherLessonPrepApi.listResources(),
                teacherLessonPrepApi.listDrafts()
            ]);

            if (configResult.status === 'fulfilled') config.value = { ...config.value, ...(configResult.value || {}) };
            if (resourceResult.status === 'fulfilled') {
                const data = resourceResult.value;
                const items = Array.isArray(data) ? data : (data?.resources || data?.items || []);
                resources.value = items.map(normalizeResource).filter((item) => item.id);
                resourceCatalog.value = [...resources.value];
                syncExpandedCourses(resources.value);
            } else {
                loadError.value = resourceResult.reason?.message || '课件资源加载失败';
            }
            if (draftResult.status === 'fulfilled') {
                const data = draftResult.value;
                drafts.value = Array.isArray(data) ? data : (data?.drafts || data?.items || []);
            }
            loading.value = false;
        };

        const setFileType = async (type) => {
            activeFileType.value = type;
            if (type === 'selected') {
                syncExpandedCourses(selectedResources.value);
                return;
            }
            await loadResources();
        };

        const toggleCourse = (course) => {
            const index = expandedCourses.value.indexOf(course);
            if (index >= 0) expandedCourses.value.splice(index, 1);
            else expandedCourses.value.push(course);
        };

        const toggleResource = (resource) => {
            const index = selectedIds.value.indexOf(resource.id);
            if (index >= 0) selectedIds.value.splice(index, 1);
            else if (selectedIds.value.length >= MAX_SELECTED_RESOURCES) {
                emit('show-toast', `一次最多选择 ${MAX_SELECTED_RESOURCES} 份课件`, 'error');
            } else {
                selectedIds.value.push(resource.id);
            }
        };

        const ensureSelected = () => {
            if (!selectedIds.value.length) {
                emit('show-toast', '请先选择课件资源', 'error');
                return false;
            }
            if (!selectedSearchableCount.value) {
                emit('show-toast', '所选课件暂无可检索文本', 'error');
                return false;
            }
            return true;
        };

        const ensureAiReady = () => {
            if (aiReady.value) return true;
            emit('show-toast', 'AI备课服务未配置，请设置 AI_LESSON_PREP_API_KEY 后重启后端', 'error');
            return false;
        };

        const summarizeResources = async () => {
            if (!ensureAiReady() || !ensureSelected() || aiLoading.value) return;
            aiLoading.value = true;
            try {
                const result = await teacherLessonPrepApi.summarize({
                    resource_ids: selectedIds.value,
                    query: lesson.topic || resourceQuery.value.trim()
                });
                summary.value = result?.content || '';
                citations.value = (result?.citations || []).map(normalizeCitation);
                const points = toLines(result?.key_points || []);
                if (points && !lesson.keyPoints.trim()) lesson.keyPoints = points;
                emit('show-toast', '课件总结已生成', 'success');
            } catch (error) {
                emit('show-toast', `总结失败：${error?.message || '未知错误'}`, 'error');
            } finally {
                aiLoading.value = false;
            }
        };

        const currentContentText = () => [
            `教学目标：${lesson.objectives}`,
            `重点：${lesson.keyPoints}`,
            `难点：${lesson.difficulties}`,
            `教学流程：${lesson.teachingFlow}`,
            `课堂提问：${lesson.questions}`,
            `练习：${lesson.exercises}`,
            `作业：${lesson.homework}`
        ].join('\n');

        const applyGeneratedPlan = (result = {}) => {
            lesson.title = result.title || lesson.title;
            lesson.durationMinutes = Number(result.duration_minutes || lesson.durationMinutes || 45);
            lesson.objectives = toLines(result.objectives || lesson.objectives);
            lesson.keyPoints = toLines(result.key_points || lesson.keyPoints);
            lesson.difficulties = toLines(result.difficulties || lesson.difficulties);
            lesson.teachingFlow = flowToText(result.teaching_flow || lesson.teachingFlow);
            lesson.questions = toLines(result.questions || lesson.questions);
            lesson.exercises = toLines(result.exercises || lesson.exercises);
            lesson.homework = toLines(result.homework || lesson.homework);
            citations.value = (result.citations || citations.value).map(normalizeCitation);
        };

        const generatePlan = async (requirements = '', successMessage = '教案已生成') => {
            if (!ensureAiReady() || !ensureSelected() || aiLoading.value) return;
            if (!lesson.topic.trim()) {
                emit('show-toast', '请填写备课主题', 'error');
                return;
            }
            aiLoading.value = true;
            try {
                const contextRequirement = hasLessonContent.value
                    ? `${requirements}\n当前可编辑教案：\n${currentContentText()}`.trim()
                    : requirements;
                const result = await teacherLessonPrepApi.generate({
                    topic: lesson.topic.trim(),
                    course_name: lesson.courseName.trim(),
                    audience: lesson.audience.trim(),
                    duration_minutes: Number(lesson.durationMinutes || 45),
                    requirements: contextRequirement,
                    resource_ids: selectedIds.value
                });
                applyGeneratedPlan(result || {});
                emit('show-toast', successMessage, 'success');
            } catch (error) {
                emit('show-toast', `生成失败：${error?.message || '未知错误'}`, 'error');
            } finally {
                aiLoading.value = false;
            }
        };

        const runInstruction = () => {
            const value = instruction.value.trim();
            if (!value) {
                emit('show-toast', '请输入编辑指令', 'error');
                return;
            }
            generatePlan(value, '已按指令更新教案');
        };

        const saveDraft = async () => {
            if (saving.value) return;
            if (!lesson.topic.trim() || !lesson.title.trim()) {
                emit('show-toast', '请填写教案标题和备课主题', 'error');
                return;
            }
            saving.value = true;
            try {
                const result = await teacherLessonPrepApi.saveDraft({
                    draft_id: activeDraftId.value || undefined,
                    title: lesson.title.trim(),
                    topic: lesson.topic.trim(),
                    duration_minutes: Number(lesson.durationMinutes || 45),
                    resource_ids: selectedIds.value,
                    content: {
                        course_name: lesson.courseName.trim(),
                        audience: lesson.audience.trim(),
                        objectives: asList(lesson.objectives),
                        key_points: asList(lesson.keyPoints),
                        difficulties: asList(lesson.difficulties),
                        teaching_flow: textToFlow(lesson.teachingFlow),
                        questions: asList(lesson.questions),
                        exercises: asList(lesson.exercises),
                        homework: asList(lesson.homework),
                        summary: summary.value,
                        citations: citations.value
                    }
                });
                activeDraftId.value = result?.draft_id || activeDraftId.value;
                const draftResult = await teacherLessonPrepApi.listDrafts().catch(() => null);
                if (draftResult) drafts.value = draftResult?.drafts || draftResult?.items || draftResult || [];
                emit('show-toast', '草稿已保存', 'success');
            } catch (error) {
                emit('show-toast', `保存失败：${error?.message || '未知错误'}`, 'error');
            } finally {
                saving.value = false;
            }
        };

        const exportWord = async () => {
            if (exporting.value) return;
            if (!hasLessonContent.value) {
                emit('show-toast', '请先生成或填写教案内容', 'error');
                return;
            }
            exporting.value = true;
            try {
                // payload 需与后端 LessonPlanExportRequest(StrictRequestModel, extra=forbid) 契约严格对齐：
                // citations 只保留 name/page/excerpt（丢弃 resourceId/course/score 等多余键），
                // 各字段截断/收敛到后端上限（title 200、flow content 4000、summary 8000、minutes 0-600 等）。
                const payload = {
                    title: clipText(lesson.title, 200) || '未命名教案',
                    topic: clipText(lesson.topic, 200),
                    course_name: clipText(lesson.courseName, 200),
                    audience: clipText(lesson.audience, 200),
                    duration_minutes: Math.min(600, Math.max(1, Number(lesson.durationMinutes) || 45)),
                    objectives: asList(lesson.objectives).slice(0, 200),
                    key_points: asList(lesson.keyPoints).slice(0, 200),
                    difficulties: asList(lesson.difficulties).slice(0, 200),
                    teaching_flow: textToFlow(lesson.teachingFlow).map((item) => ({
                        stage: clipText(item.stage, 200) || '教学环节',
                        minutes: Math.min(600, Math.max(0, Number(item.minutes) || 0)),
                        content: clipText(item.content, 4000) || '—'
                    })).slice(0, 100),
                    questions: asList(lesson.questions).slice(0, 200),
                    exercises: asList(lesson.exercises).slice(0, 200),
                    homework: asList(lesson.homework).slice(0, 200),
                    summary: String(summary.value || '').slice(0, 8000),
                    citations: citations.value.map((item) => ({
                        name: clipText(item.name, 200),
                        page: Math.max(0, Math.round(Number(item.page) || 0)),
                        excerpt: clipText(item.excerpt, 4000)
                    })).slice(0, 50)
                };
                const result = await teacherLessonPrepApi.exportDocx(payload);
                const url = URL.createObjectURL(result.blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = result.filename;
                document.body.appendChild(link);
                link.click();
                link.remove();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
                emit('show-toast', `已导出：${result.filename}`, 'success');
            } catch (error) {
                emit('show-toast', `导出失败：${error?.message || '未知错误'}`, 'error');
            } finally {
                exporting.value = false;
            }
        };

        const resetLesson = async () => {
            activeDraftId.value = '';
            lesson.title = '新建教学设计';
            lesson.topic = '';
            lesson.courseName = '';
            lesson.audience = '';
            lesson.durationMinutes = 45;
            lesson.objectives = '';
            lesson.keyPoints = '';
            lesson.difficulties = '';
            lesson.teachingFlow = '';
            lesson.questions = '';
            lesson.exercises = '';
            lesson.homework = '';
            selectedIds.value = [];
            citations.value = [];
            summary.value = '';
            instruction.value = '';
            if (activeFileType.value === 'selected' || resourceQuery.value.trim()) {
                activeFileType.value = 'all';
                resourceQuery.value = '';
                await loadResources();
            }
            emit('show-toast', '已新建空白设计', 'success');
        };

        const loadDraft = async () => {
            if (!activeDraftId.value) {
                await resetLesson();
                return;
            }
            const draft = drafts.value.find((item) => String(item.draft_id || item.id) === activeDraftId.value);
            if (!draft) return;
            const content = draft.content || {};
            lesson.title = draft.title || '未命名教案';
            lesson.topic = draft.topic || '';
            lesson.durationMinutes = Number(draft.duration_minutes || 45);
            lesson.courseName = content.course_name || '';
            lesson.audience = content.audience || '';
            lesson.objectives = toLines(content.objectives);
            lesson.keyPoints = toLines(content.key_points);
            lesson.difficulties = toLines(content.difficulties);
            lesson.teachingFlow = flowToText(content.teaching_flow);
            lesson.questions = toLines(content.questions);
            lesson.exercises = toLines(content.exercises);
            lesson.homework = toLines(content.homework);
            summary.value = content.summary || '';
            citations.value = (content.citations || []).map(normalizeCitation);
            selectedIds.value = Array.isArray(draft.resource_ids) ? [...draft.resource_ids] : [];
            emit('show-toast', '草稿已加载', 'success');
        };

        onMounted(loadWorkspace);

        return {
            loading,
            resourcesLoading,
            aiLoading,
            saving,
            exporting,
            loadError,
            resources,
            selectedIds,
            expandedCourses,
            activeFileType,
            resourceQuery,
            config,
            citations,
            summary,
            drafts,
            activeDraftId,
            instruction,
            lesson,
            aiReady,
            hasLessonContent,
            resourceSummary,
            selectedResources,
            displayedResources,
            groupedResources,
            selectedSearchableCount,
            modelName,
            formatSize,
            fileTypeLabel,
            loadResources,
            setFileType,
            toggleCourse,
            toggleResource,
            summarizeResources,
            generatePlan,
            runInstruction,
            saveDraft,
            exportWord,
            resetLesson,
            loadDraft
        };
    },
    template: `
        <section data-testid="teacher-ai-lesson-prep" class="absolute inset-0 overflow-y-auto bg-slate-50 p-6 lg:p-8">
            <div class="mx-auto flex max-w-[1680px] flex-col gap-5">
                <header class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                    <div class="flex items-center gap-4">
                        <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#1c2b38] text-white shadow-sm">
                            <i class="ph ph-notebook text-2xl"></i>
                        </span>
                        <div>
                            <h2 class="text-3xl font-extrabold text-[#1c2b38]" style="font-family:'Noto Serif SC',serif;">AI备课中心</h2>
                            <div class="mt-2 flex flex-wrap gap-2">
                                <span data-testid="lesson-prep-resource-total" class="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-bold text-slate-600">课件 {{ resourceSummary.total }}</span>
                                <span class="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-bold text-slate-600">PDF {{ resourceSummary.pdf }}</span>
                                <span class="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-bold text-slate-600">PPT/PPTX {{ resourceSummary.slides }}</span>
                                <span class="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-bold text-slate-600">已选 {{ selectedIds.length }}</span>
                            </div>
                        </div>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        <select v-model="activeDraftId" @change="loadDraft" class="h-10 max-w-[220px] rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 outline-none focus:border-[#1c2b38]">
                            <option value="">新建空白设计</option>
                            <option v-for="draft in drafts" :key="draft.draft_id || draft.id" :value="String(draft.draft_id || draft.id)">{{ draft.title }}</option>
                        </select>
                        <span class="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600">
                            <i class="ph ph-cpu"></i>{{ modelName }}
                        </span>
                        <button type="button" @click="exportWord" :disabled="exporting || !hasLessonContent" data-testid="lesson-prep-export-docx" class="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50">
                            <i :class="exporting ? 'ph ph-spinner animate-spin' : 'ph ph-file-doc'"></i>{{ exporting ? '导出中' : '导出Word' }}
                        </button>
                        <button type="button" @click="saveDraft" :disabled="saving" class="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50">
                            <i :class="saving ? 'ph ph-spinner animate-spin' : 'ph ph-floppy-disk'"></i>{{ saving ? '保存中' : '保存草稿' }}
                        </button>
                        <button type="button" @click="generatePlan('', '教案已生成')" :disabled="aiLoading" class="flex h-10 items-center gap-2 rounded-xl bg-[#1c2b38] px-5 text-xs font-bold text-white shadow-sm hover:bg-[#253645] disabled:opacity-50">
                            <i :class="aiLoading ? 'ph ph-spinner animate-spin' : 'ph ph-sparkle'"></i>生成教案
                        </button>
                    </div>
                </header>

                <div v-if="loadError" class="flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-800">
                    <span class="flex items-center gap-2"><i class="ph ph-warning"></i>{{ loadError }}</span>
                    <button type="button" @click="loadResources" class="rounded-lg border border-amber-200 bg-white px-3 py-1.5">重试</button>
                </div>

                <div v-if="!aiReady && !loading" class="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-800">
                    <i class="ph ph-warning"></i>
                    <span>AI备课服务未配置，请在 backend/.env 设置 AI_LESSON_PREP_API_KEY 后重启后端。</span>
                </div>

                <div v-if="loading" class="flex min-h-[520px] items-center justify-center rounded-xl border border-slate-200 bg-white text-sm text-slate-400 shadow-sm">
                    <i class="ph ph-spinner mr-2 animate-spin text-lg"></i>正在加载备课工作区
                </div>

                <div v-else class="grid min-h-[calc(100vh-190px)] grid-cols-1 items-stretch gap-5 xl:grid-cols-[330px_minmax(560px,1fr)_330px]">
                    <div class="min-h-0 xl:relative">
                    <aside class="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white shadow-sm xl:absolute xl:inset-0 xl:overflow-hidden">
                        <div class="border-b border-slate-100 p-5">
                            <div class="flex items-center justify-between gap-3">
                                <div>
                                    <h3 class="text-base font-bold text-slate-900">课件资源</h3>
                                    <p class="mt-1 text-[11px] text-slate-400">可检索 {{ resourceSummary.searchable }} · 已选 {{ selectedSearchableCount }}</p>
                                </div>
                                <button type="button" @click="loadResources" :disabled="resourcesLoading" class="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50">
                                    <i :class="resourcesLoading ? 'ph ph-spinner animate-spin' : 'ph ph-arrow-clockwise'"></i>
                                </button>
                            </div>
                            <form @submit.prevent="loadResources" class="mt-4 flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 focus-within:border-[#1c2b38]">
                                <i class="ph ph-magnifying-glass text-slate-400"></i>
                                <input v-model="resourceQuery" type="search" placeholder="搜索课程、章节、文件名" class="min-w-0 flex-1 bg-transparent text-xs text-slate-700 outline-none placeholder:text-slate-400">
                                <button type="submit" class="text-[11px] font-bold text-[#1c2b38]">搜索</button>
                            </form>
                    <div class="mt-3 grid grid-cols-3 gap-2">
                        <button v-for="filter in [{id:'all',label:'全部'},{id:'pdf',label:'PDF'},{id:'selected',label:'已选'}]" :key="filter.id" type="button"
                                    @click="setFileType(filter.id)"
                                    class="h-9 rounded-lg border text-[11px] font-bold transition-colors"
                                    :class="activeFileType === filter.id ? 'border-[#1c2b38] bg-[#1c2b38] text-white' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'">
                                    {{ filter.label }}
                                </button>
                            </div>
                        </div>

                        <div class="min-h-0 flex-1 overflow-y-auto p-3">
                            <div v-if="resourcesLoading" class="flex h-40 items-center justify-center text-xs text-slate-400"><i class="ph ph-spinner mr-2 animate-spin"></i>加载课件</div>
                            <template v-else>
                                <section v-for="group in groupedResources" :key="group.course" class="mb-2 overflow-hidden rounded-xl border border-slate-200 bg-white">
                                    <button type="button" @click="toggleCourse(group.course)" :aria-expanded="expandedCourses.includes(group.course)"
                                        class="flex h-11 w-full items-center gap-2 px-3 text-left text-xs font-bold text-slate-700 transition-colors hover:bg-slate-50">
                                        <i :class="expandedCourses.includes(group.course) ? 'ph ph-caret-down' : 'ph ph-caret-right'" class="shrink-0 text-slate-400"></i>
                                        <i class="ph ph-folder shrink-0 text-slate-500"></i>
                                        <span class="min-w-0 flex-1 truncate" :title="group.course">{{ group.course }}</span>
                                        <span class="shrink-0 rounded-md bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">{{ group.items.length }}</span>
                                    </button>
                                    <div v-show="expandedCourses.includes(group.course)" class="border-t border-slate-100 bg-slate-50 p-2">
                                        <button v-for="resource in group.items" :key="resource.id" type="button" @click="toggleResource(resource)"
                                            class="mb-2 w-full rounded-lg border p-3 text-left transition-all last:mb-0"
                                            :class="selectedIds.includes(resource.id) ? 'border-[#1c2b38] bg-[#1c2b38] text-white shadow-sm' : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'">
                                            <div class="flex items-start justify-between gap-3">
                                                <p class="min-w-0 flex-1 truncate text-xs font-bold" :title="resource.name">{{ resource.name }}</p>
                                                <span class="shrink-0 rounded-md border px-2 py-0.5 text-[9px] font-bold" :class="selectedIds.includes(resource.id) ? 'border-white/20 bg-white/10 text-white' : 'border-slate-200 bg-slate-50 text-slate-500'">{{ fileTypeLabel(resource.extension) }}</span>
                                            </div>
                                            <div class="mt-3 flex items-center justify-between text-[10px]" :class="selectedIds.includes(resource.id) ? 'text-white/60' : 'text-slate-400'">
                                                <span>{{ formatSize(resource.sizeBytes) }}</span>
                                                <span class="flex items-center gap-1"><i :class="resource.searchable ? 'ph ph-check-circle' : 'ph ph-warning-circle'"></i>{{ resource.searchable ? '可检索' : '不可检索' }}</span>
                                            </div>
                                        </button>
                                    </div>
                                </section>
                            </template>
                            <div v-if="!resourcesLoading && !displayedResources.length" class="flex h-48 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-center text-xs text-slate-400">
                                <i class="ph ph-files mb-2 text-2xl"></i>
                                <span>暂无匹配课件</span>
                            </div>
                        </div>
                    </aside>
                    </div>

                    <main class="min-w-0 rounded-xl border border-slate-200 bg-white shadow-sm">
                        <div class="flex flex-col gap-4 border-b border-slate-100 p-5 lg:flex-row lg:items-center lg:justify-between">
                            <input v-model="lesson.title" type="text" aria-label="教案标题" class="min-w-0 flex-1 border-0 bg-transparent text-2xl font-extrabold text-slate-900 outline-none placeholder:text-slate-300" placeholder="教案标题">
                            <div class="flex items-center gap-2">
                                <label class="flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-[11px] text-slate-500">
                                    <i class="ph ph-clock"></i>
                                    <input v-model.number="lesson.durationMinutes" type="number" min="1" max="600" class="w-12 bg-transparent text-right font-bold text-slate-800 outline-none">
                                    分钟
                                </label>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 gap-4 border-b border-slate-100 p-5 lg:grid-cols-3">
                            <label class="block">
                                <span class="mb-2 block text-[11px] font-bold text-slate-500">备课主题</span>
                                <input v-model="lesson.topic" type="text" placeholder="如：线性表的顺序存储" class="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-xs text-slate-700 outline-none focus:border-[#1c2b38]">
                            </label>
                            <label class="block">
                                <span class="mb-2 block text-[11px] font-bold text-slate-500">课程名称</span>
                                <input v-model="lesson.courseName" type="text" placeholder="数据结构" class="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-xs text-slate-700 outline-none focus:border-[#1c2b38]">
                            </label>
                            <label class="block">
                                <span class="mb-2 block text-[11px] font-bold text-slate-500">授课对象</span>
                                <input v-model="lesson.audience" type="text" placeholder="软件工程 2024 级" class="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-xs text-slate-700 outline-none focus:border-[#1c2b38]">
                            </label>
                        </div>

                        <div class="grid grid-cols-1 gap-4 p-5 lg:grid-cols-2">
                            <label class="rounded-xl border border-slate-200 bg-slate-50/60 p-4 lg:col-span-2">
                                <span class="mb-2 flex items-center gap-2 text-xs font-bold text-slate-800"><i class="ph ph-target text-[#1c2b38]"></i>教学目标</span>
                                <textarea v-model="lesson.objectives" rows="3" placeholder="每行一个教学目标" class="w-full resize-y bg-transparent text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400"></textarea>
                            </label>
                            <label class="rounded-xl border border-slate-200 bg-white p-4">
                                <span class="mb-2 flex items-center gap-2 text-xs font-bold text-slate-800"><i class="ph ph-bookmark-simple text-[#1c2b38]"></i>重点</span>
                                <textarea v-model="lesson.keyPoints" rows="4" placeholder="每行一个教学重点" class="w-full resize-y text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400"></textarea>
                            </label>
                            <label class="rounded-xl border border-slate-200 bg-white p-4">
                                <span class="mb-2 flex items-center gap-2 text-xs font-bold text-slate-800"><i class="ph ph-warning-circle text-[#b91c1c]"></i>难点</span>
                                <textarea v-model="lesson.difficulties" rows="4" placeholder="每行一个教学难点" class="w-full resize-y text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400"></textarea>
                            </label>
                            <label class="rounded-xl border border-slate-200 bg-slate-50/60 p-4 lg:col-span-2">
                                <span class="mb-2 flex items-center gap-2 text-xs font-bold text-slate-800"><i class="ph ph-list-numbers text-[#1c2b38]"></i>教学流程</span>
                                <textarea v-model="lesson.teachingFlow" rows="8" placeholder="格式：环节｜分钟｜教学内容" class="w-full resize-y bg-transparent font-mono text-xs leading-6 text-slate-700 outline-none placeholder:text-slate-400"></textarea>
                            </label>
                            <label class="rounded-xl border border-slate-200 bg-white p-4">
                                <span class="mb-2 flex items-center gap-2 text-xs font-bold text-slate-800"><i class="ph ph-chat-circle-text text-[#1c2b38]"></i>课堂提问</span>
                                <textarea v-model="lesson.questions" rows="5" placeholder="每行一个课堂问题" class="w-full resize-y text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400"></textarea>
                            </label>
                            <label class="rounded-xl border border-slate-200 bg-white p-4">
                                <span class="mb-2 flex items-center gap-2 text-xs font-bold text-slate-800"><i class="ph ph-pencil-line text-[#1c2b38]"></i>课堂练习</span>
                                <textarea v-model="lesson.exercises" rows="5" placeholder="每行一道练习" class="w-full resize-y text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400"></textarea>
                            </label>
                            <label class="rounded-xl border border-slate-200 bg-slate-50/60 p-4 lg:col-span-2">
                                <span class="mb-2 flex items-center gap-2 text-xs font-bold text-slate-800"><i class="ph ph-house-line text-[#1c2b38]"></i>课后作业</span>
                                <textarea v-model="lesson.homework" rows="4" placeholder="每行一项课后作业" class="w-full resize-y bg-transparent text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400"></textarea>
                            </label>
                        </div>
                    </main>

                    <aside class="flex flex-col gap-4">
                        <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <div class="flex items-center justify-between gap-3">
                                <h3 class="text-base font-bold text-slate-900">AI辅助</h3>
                                <span class="text-[10px] font-semibold text-slate-400">{{ modelName }}</span>
                            </div>
                            <div class="mt-4 grid grid-cols-2 gap-2">
                                <button type="button" @click="summarizeResources" :disabled="aiLoading || !aiReady" class="col-span-2 flex h-10 items-center justify-center gap-2 rounded-xl bg-[#1c2b38] text-xs font-bold text-white hover:bg-[#253645] disabled:opacity-50"><i class="ph ph-file-text"></i>总结课件</button>
                                <button type="button" @click="generatePlan('优化现有教案的目标、重点难点与教学流程，保留合理内容。', '教案已优化')" :disabled="aiLoading || !aiReady" class="h-10 rounded-xl border border-slate-200 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50">优化教案</button>
                                <button type="button" @click="generatePlan('重点生成分层课堂练习，并同步完善课堂提问。', '练习已生成')" :disabled="aiLoading || !aiReady" class="h-10 rounded-xl border border-slate-200 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50">生成练习</button>
                                <button type="button" @click="lesson.durationMinutes = 45; generatePlan('将教学流程精简为45分钟，确保各环节总时长为45分钟。', '教案已精简为45分钟')" :disabled="aiLoading || !aiReady" class="col-span-2 h-10 rounded-xl border border-slate-200 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50">精简为45分钟</button>
                            </div>
                        </section>

                        <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <div class="flex items-center justify-between gap-3">
                                <h3 class="text-sm font-bold text-slate-900">命中课件依据</h3>
                                <span class="text-[10px] text-slate-400">{{ citations.length }} 条</span>
                            </div>
                            <div class="mt-4 max-h-64 space-y-2 overflow-y-auto pr-1">
                                <article v-for="(citation, index) in citations" :key="citation.resourceId + '-' + citation.page + '-' + index" class="rounded-xl border border-slate-200 bg-slate-50 p-3">
                                    <div class="flex items-center justify-between gap-2 text-[10px] font-bold text-slate-500">
                                        <span class="truncate">{{ citation.name }}</span>
                                        <span v-if="citation.page" class="shrink-0">第 {{ citation.page }} 页</span>
                                    </div>
                                    <p class="mt-2 line-clamp-3 text-[11px] leading-5 text-slate-600">{{ citation.excerpt }}</p>
                                </article>
                                <div v-if="!citations.length" class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-xs text-slate-400">生成或总结后显示引用依据</div>
                            </div>
                        </section>

                        <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <h3 class="text-sm font-bold text-slate-900">课件总结</h3>
                            <textarea v-model="summary" rows="6" placeholder="总结结果将在此显示，可继续编辑" class="mt-3 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-700 outline-none focus:border-[#1c2b38]"></textarea>
                        </section>

                        <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <div class="flex items-center justify-between gap-3">
                                <h3 class="text-sm font-bold text-slate-900">编辑指令</h3>
                                <span class="text-[10px] text-slate-400">可追溯生成</span>
                            </div>
                            <textarea v-model="instruction" rows="4" placeholder="例如：增加案例导入，练习分为基础与进阶两组" class="mt-3 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-700 outline-none focus:border-[#1c2b38]"></textarea>
                            <button type="button" @click="runInstruction" :disabled="aiLoading" class="mt-3 flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-[#1c2b38] text-xs font-bold text-white hover:bg-[#253645] disabled:opacity-50">
                                <i :class="aiLoading ? 'ph ph-spinner animate-spin' : 'ph ph-paper-plane-tilt'"></i>{{ aiLoading ? '处理中' : '执行指令' }}
                            </button>
                        </section>
                    </aside>
                </div>
            </div>
        </section>
    `
};
