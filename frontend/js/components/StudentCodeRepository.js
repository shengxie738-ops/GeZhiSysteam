import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { repositoryApi, fetchGiteaIdentity, rotateGiteaToken } from '../api/repository.js';
import { formatTime } from '../utils/helpers.js';

export default {
    name: 'StudentCodeRepository',
    props: {
        currentUser: { type: Object, default: null },
        initialProject: { type: Object, default: null }
    },
    emits: ['show-toast', 'project-opened'],
    setup(props, { emit }) {
        const projects = ref([]);
        const currentProject = ref(null);
        const loading = ref(true);
        const query = ref('');
        const activeLanguage = ref('all');
        const sortBy = ref('recommended');
        const isPublishing = ref(false);
        const publishOpen = ref(false);
        const copiedProjectId = ref('');
        const reportTarget = ref(null);

        const publishForm = ref({
            title: '',
            slug: '',
            description: '',
            language: 'Vue',
            course: '数据结构',
            tags: '',
            collaborators: '',
            private: false
        });

        const reportForm = ref({
            reason: '违规内容',
            description: ''
        });

        const giteaIdentity = ref(null);
        const generatedToken = ref('');
        const tokenWarning = ref('');
        const copiedToken = ref(false);
        const copiedGitConfigAll = ref(false);
        const copiedGitConfigLine = ref('');
        const repoBrowserPath = ref('');
        const repoBrowserEntries = ref([]);
        const repoBrowserLoading = ref(false);
        const repoBrowserBlob = ref(null);
        const repoBrowserLanguages = ref([]);
        const repoBrowserError = ref('');
        const cloneMode = ref('token');
        const cloneToken = ref(sessionStorage.getItem('giteaCloneToken') || '');
        const copiedAuthClone = ref(false);

        const currentUserId = computed(() => props.currentUser?.username || 'anonymous');

        const authenticatedCloneUrl = computed(() => {
            if (!currentProject.value?.cloneUrl || !giteaIdentity.value?.giteaUsername || !cloneToken.value) {
                return '';
            }
            return currentProject.value.cloneUrl.replace(
                /^https:\/\//,
                `https://${giteaIdentity.value.giteaUsername}:${cloneToken.value}@`
            );
        });

        const loadGiteaIdentity = async () => {
            try {
                giteaIdentity.value = await fetchGiteaIdentity();
            } catch (error) {
                giteaIdentity.value = {
                    giteaUsername: '',
                    giteaEmail: '',
                    syncStatus: 'mock',
                    gitConfigCommands: []
                };
            }
        };

        const handleRotateGiteaToken = async () => {
            try {
                const result = await rotateGiteaToken();
                generatedToken.value = result.token || '';
                tokenWarning.value = result.warning || 'Token 只显示一次，请保存。';
                cloneToken.value = result.token || '';
                if (result.token) {
                    sessionStorage.setItem('giteaCloneToken', result.token);
                }
                await loadGiteaIdentity();
                emit('show-toast', 'Gitea Token 已生成', 'success');
            } catch (err) {
                emit('show-toast', err?.message || 'Token 生成失败', 'error');
            }
        };

        const loadProjects = async () => {
            loading.value = true;
            try {
                projects.value = await repositoryApi.getRepositories({ sort: sortBy.value, userId: currentUserId.value });
                if (currentProject.value) {
                    currentProject.value = await repositoryApi.getRepository(currentProject.value.id, currentUserId.value);
                }
            } catch (err) {
                emit('show-toast', '代码仓库数据加载失败', 'error');
            } finally {
                loading.value = false;
            }
        };

        const languages = computed(() => {
            const map = new Map();
            projects.value.forEach((project) => {
                const language = project.language || 'Other';
                map.set(language, (map.get(language) || 0) + 1);
            });
            return Array.from(map.entries()).map(([name, count]) => ({ name, count }));
        });

        const filteredProjects = computed(() => {
            const keyword = query.value.trim().toLowerCase();
            let result = [...projects.value];
            if (activeLanguage.value !== 'all') {
                result = result.filter((project) => project.language === activeLanguage.value);
            }
            if (keyword) {
                result = result.filter((project) =>
                    project.title.toLowerCase().includes(keyword) ||
                    project.description.toLowerCase().includes(keyword) ||
                    (project.tags || []).join(' ').toLowerCase().includes(keyword)
                );
            }
            if (sortBy.value === 'favorites') {
                result.sort((a, b) => b.favoriteCount - a.favoriteCount);
            } else if (sortBy.value === 'relevant') {
                result.sort((a, b) => ((b.recommendScore || 0) + b.favoriteCount * 5 + b.starCount * 2) - ((a.recommendScore || 0) + a.favoriteCount * 5 + a.starCount * 2));
            } else if (sortBy.value === 'stars') {
                result.sort((a, b) => b.starCount - a.starCount);
            } else if (sortBy.value === 'latest') {
                result.sort((a, b) => String(b.updatedAt || b.createdAt).localeCompare(String(a.updatedAt || a.createdAt)));
            } else {
                result.sort((a, b) => (b.recommendScore + b.starCount * 4) - (a.recommendScore + a.starCount * 4));
            }
            return result;
        });

        const featuredProjects = computed(() => filteredProjects.value.slice(0, 3));

        const repoStats = computed(() => ({
            total: projects.value.length,
            stars: projects.value.reduce((sum, item) => sum + (item.starCount || 0), 0),
            favorites: projects.value.reduce((sum, item) => sum + (item.favoriteCount || 0), 0)
        }));

        const repoBreadcrumbs = computed(() => {
            const crumbs = [{ label: '根目录', path: '' }];
            const parts = String(repoBrowserPath.value || '').split('/').filter(Boolean);
            let current = '';
            parts.forEach((part) => {
                current = current ? `${current}/${part}` : part;
                crumbs.push({ label: part, path: current });
            });
            return crumbs;
        });

        const resetRepoBrowser = () => {
            repoBrowserPath.value = '';
            repoBrowserEntries.value = [];
            repoBrowserBlob.value = null;
            repoBrowserLanguages.value = [];
            repoBrowserError.value = '';
        };

        const loadRepoLanguages = async () => {
            if (!currentProject.value?.id) return;
            try {
                repoBrowserLanguages.value = await repositoryApi.getRepositoryLanguages(currentProject.value.id);
            } catch (err) {
                repoBrowserLanguages.value = [];
            }
        };

        const loadRepoBrowser = async (path = '') => {
            if (!currentProject.value?.id) return;
            repoBrowserLoading.value = true;
            repoBrowserError.value = '';
            repoBrowserBlob.value = null;
            try {
                const data = await repositoryApi.getRepositoryTree(currentProject.value.id, {
                    path,
                    ref: currentProject.value.defaultBranch || 'main'
                });
                repoBrowserPath.value = data.path || '';
                repoBrowserEntries.value = data.entries || [];
            } catch (err) {
                repoBrowserEntries.value = [];
                repoBrowserError.value = err?.message || '文件目录加载失败';
            } finally {
                repoBrowserLoading.value = false;
            }
        };

        const loadRepoBlob = async (path) => {
            if (!currentProject.value?.id || !path) return;
            repoBrowserLoading.value = true;
            repoBrowserError.value = '';
            try {
                repoBrowserBlob.value = await repositoryApi.getRepositoryBlob(currentProject.value.id, {
                    path,
                    ref: currentProject.value.defaultBranch || 'main'
                });
            } catch (err) {
                repoBrowserBlob.value = null;
                repoBrowserError.value = err?.message || '文件预览失败';
            } finally {
                repoBrowserLoading.value = false;
            }
        };

        const openRepoEntry = async (entry) => {
            if (!entry) return;
            if (entry.type === 'dir') {
                await loadRepoBrowser(entry.path || entry.name);
                return;
            }
            await loadRepoBlob(entry.path || entry.name);
        };

        const formatFileSize = (size) => {
            const value = Number(size || 0);
            if (!value) return '-';
            if (value < 1024) return `${value} B`;
            if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
            return `${(value / (1024 * 1024)).toFixed(1)} MB`;
        };

        const viewProject = async (project) => {
            loading.value = true;
            resetRepoBrowser();
            try {
                currentProject.value = await repositoryApi.getRepository(project.id, currentUserId.value);
                await Promise.all([loadRepoBrowser(''), loadRepoLanguages()]);
                await nextTick();
            } catch (err) {
                emit('show-toast', '项目详情读取失败', 'error');
            } finally {
                loading.value = false;
            }
        };

        const backToList = () => {
            currentProject.value = null;
            resetRepoBrowser();
        };

        const createRepository = async () => {
            const title = publishForm.value.title.trim();
            const description = publishForm.value.description.trim();
            if (!title || !description) {
                emit('show-toast', '请填写项目名称和简介', 'error');
                return;
            }
            isPublishing.value = true;
            try {
                const tags = publishForm.value.tags
                    .replace(/，/g, ',')
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean);
                const collaborators = publishForm.value.collaborators
                    .replace(/，/g, ',')
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean);
                const project = await repositoryApi.createRepository({
                    ...publishForm.value,
                    title,
                    description,
                    tags,
                    collaborators,
                    author: currentUserId.value,
                    avatar: props.currentUser?.avatar_url || ''
                });
                projects.value.unshift(project);
                publishOpen.value = false;
                publishForm.value = {
                    title: '',
                    slug: '',
                    description: '',
                    language: 'Vue',
                    course: '数据结构',
                    tags: '',
                    collaborators: '',
                    private: false
                };
                emit('show-toast', '项目已发布，Gitea 仓库地址已生成', 'success');
                currentProject.value = project;
                await Promise.all([loadRepoBrowser(''), loadRepoLanguages()]);
            } catch (err) {
                emit('show-toast', '项目发布失败，请检查仓库名称或稍后重试', 'error');
            } finally {
                isPublishing.value = false;
            }
        };

        const syncProjectState = (state) => {
            const target = projects.value.find((project) => project.id === state.projectId);
            if (target) {
                target.starCount = state.starCount;
                target.favoriteCount = state.favoriteCount;
                target.isStarred = state.isStarred;
                target.isFavorited = state.isFavorited;
            }
            if (currentProject.value?.id === state.projectId) {
                currentProject.value = { ...currentProject.value, ...state };
            }
        };

        const toggleStar = async (project, event) => {
            if (event) event.stopPropagation();
            const previous = { ...project };
            project.isStarred = !project.isStarred;
            project.starCount += project.isStarred ? 1 : -1;
            try {
                syncProjectState(await repositoryApi.toggleStar(project.id, currentUserId.value));
            } catch (err) {
                Object.assign(project, previous);
                emit('show-toast', 'Star 操作失败', 'error');
            }
        };

        const toggleFavorite = async (project, event) => {
            if (event) event.stopPropagation();
            const previous = { ...project };
            project.isFavorited = !project.isFavorited;
            project.favoriteCount += project.isFavorited ? 1 : -1;
            try {
                syncProjectState(await repositoryApi.toggleFavorite(project.id, currentUserId.value));
            } catch (err) {
                Object.assign(project, previous);
                emit('show-toast', '收藏操作失败', 'error');
            }
        };

        const copyClone = async (project, event) => {
            if (event) event.stopPropagation();
            try {
                await navigator.clipboard.writeText(project.cloneUrl);
                copiedProjectId.value = project.id;
                emit('show-toast', 'clone 地址已复制', 'success');
                setTimeout(() => {
                    if (copiedProjectId.value === project.id) copiedProjectId.value = '';
                }, 1400);
            } catch (err) {
                emit('show-toast', project.cloneUrl, 'info');
            }
        };

        const copyAuthClone = async () => {
            if (!authenticatedCloneUrl.value) return;
            const command = `git clone ${authenticatedCloneUrl.value}`;
            try {
                await navigator.clipboard.writeText(command);
                copiedAuthClone.value = true;
                emit('show-toast', '带 Token 的 Clone 命令已复制', 'success');
                setTimeout(() => { copiedAuthClone.value = false; }, 1400);
            } catch (err) {
                emit('show-toast', command, 'info');
            }
        };

        const generateTokenForClone = async () => {
            await handleRotateGiteaToken();
        };

        const copyText = async (text, { toast, onCopied, resetCopied }) => {
            if (!text) return;
            try {
                await navigator.clipboard.writeText(text);
                onCopied?.();
                emit('show-toast', toast, 'success');
                if (resetCopied) {
                    setTimeout(resetCopied, 1400);
                }
            } catch (err) {
                emit('show-toast', text, 'info');
            }
        };

        const copyGeneratedToken = async () => {
            await copyText(generatedToken.value, {
                toast: 'Token 已复制',
                onCopied: () => { copiedToken.value = true; },
                resetCopied: () => { copiedToken.value = false; }
            });
        };

        const copyGitConfig = async () => {
            const text = formatGitConfigCommands(giteaIdentity.value?.gitConfigCommands);
            await copyText(text, {
                toast: 'Git 配置已复制',
                onCopied: () => { copiedGitConfigAll.value = true; },
                resetCopied: () => { copiedGitConfigAll.value = false; }
            });
        };

        const copyGitConfigLine = async (command) => {
            await copyText(command, {
                toast: '命令已复制',
                onCopied: () => { copiedGitConfigLine.value = command; },
                resetCopied: () => {
                    if (copiedGitConfigLine.value === command) copiedGitConfigLine.value = '';
                }
            });
        };

        const openReport = (project, event) => {
            if (event) event.stopPropagation();
            reportTarget.value = project;
            reportForm.value = { reason: '违规内容', description: '' };
        };

        const submitReport = async () => {
            if (!reportTarget.value) return;
            if (!reportForm.value.description.trim()) {
                emit('show-toast', '请填写举报说明，方便教师判断', 'error');
                return;
            }
            try {
                await repositoryApi.reportRepository(reportTarget.value.id, {
                    ...reportForm.value,
                    reporter: currentUserId.value
                });
                reportTarget.value = null;
                emit('show-toast', '举报已提交，教师会在审核台处理', 'success');
            } catch (err) {
                emit('show-toast', '举报提交失败', 'error');
            }
        };

        const formatMarkdown = (text) => {
            if (window.marked && typeof window.marked.parse === 'function') {
                return window.marked.parse(text || 'README 尚未同步。');
            }
            return String(text || 'README 尚未同步。').replace(/\n/g, '<br>');
        };

        const languageTone = (language) => ({
            Vue: 'bg-emerald-500',
            Python: 'bg-blue-500',
            TypeScript: 'bg-indigo-500',
            Java: 'bg-amber-500',
            C: 'bg-slate-700',
            Cpp: 'bg-slate-700'
        }[language] || 'bg-slate-400');

        const formatGitConfigCommands = (commands) => (commands || []).join('\n');

        onMounted(async () => {
            await Promise.all([loadProjects(), loadGiteaIdentity()]);
        });

        watch(() => props.initialProject, async (project) => {
            if (!project?.id) return;
            await viewProject(project);
            emit('project-opened');
        }, { immediate: true });

        return {
            projects,
            currentProject,
            loading,
            query,
            activeLanguage,
            sortBy,
            publishOpen,
            isPublishing,
            publishForm,
            reportTarget,
            reportForm,
            copiedProjectId,
            giteaIdentity,
            generatedToken,
            tokenWarning,
            copiedToken,
            copiedGitConfigAll,
            copiedGitConfigLine,
            loadGiteaIdentity,
            handleRotateGiteaToken,
            copyGeneratedToken,
            copyGitConfig,
            copyGitConfigLine,
            currentUserId,
            languages,
            filteredProjects,
            featuredProjects,
            repoStats,
            repoBrowserPath,
            repoBrowserEntries,
            repoBrowserLoading,
            repoBrowserBlob,
            repoBrowserLanguages,
            repoBrowserError,
            repoBreadcrumbs,
            loadRepoBrowser,
            openRepoEntry,
            formatFileSize,
            loadProjects,
            viewProject,
            backToList,
            createRepository,
            toggleStar,
            toggleFavorite,
            copyClone,
            cloneMode,
            authenticatedCloneUrl,
            copiedAuthClone,
            copyAuthClone,
            generateTokenForClone,
            openReport,
            submitReport,
            formatMarkdown,
            languageTone,
            formatGitConfigCommands,
            formatTime
        };
    },
    template: `
        <section class="absolute inset-0 overflow-hidden bg-slate-50 p-4 lg:p-6 select-none">
            <div class="h-full flex flex-col gap-4 min-h-0">
                <header class="flex items-center justify-between border-b border-slate-200 pb-3 shrink-0">
                    <div class="flex items-center gap-2">
                        <button v-if="currentProject" @click="backToList" class="text-xs text-slate-500 hover:text-slate-900 font-bold flex items-center gap-1.5">
                            <i class="ph ph-arrow-left"></i> 返回代码仓库
                        </button>
                        <span v-else class="text-xs text-slate-500 font-bold flex items-center gap-1.5">
                            <i class="ph ph-code text-lg text-primary"></i> 校园代码仓库
                        </span>
                    </div>
                    <div class="text-right">
                        <span class="text-[10px] text-slate-400 uppercase tracking-widest font-mono">CAMPUS OPEN SOURCE</span>
                        <h3 class="text-xs font-bold text-slate-700">格物致知 · 项目索引</h3>
                    </div>
                </header>

                <div v-if="currentProject" class="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-5 overflow-hidden">
                    <main class="glass-panel-liquid p-6 overflow-y-auto no-scrollbar">
                        <div class="flex flex-col gap-5">
                            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 border-b border-slate-100 pb-5">
                                <div>
                                    <div class="flex items-center gap-2 mb-2">
                                        <span class="w-2.5 h-2.5 rounded-full" :class="languageTone(currentProject.language)"></span>
                                        <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{{ currentProject.language }}</span>
                                        <span class="text-[10px] text-slate-400">/{{ currentProject.defaultBranch || 'main' }}</span>
                                    </div>
                                    <h1 class="text-2xl lg:text-3xl font-serif font-bold text-slate-900 tracking-tight">{{ currentProject.title }}</h1>
                                    <p class="text-xs text-slate-500 mt-2 leading-relaxed max-w-2xl">{{ currentProject.description }}</p>
                                </div>
                                <div class="flex flex-wrap gap-2 shrink-0">
                                    <button @click="toggleStar(currentProject)" class="px-3 py-2 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5"
                                            :class="currentProject.isStarred ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-white/70 text-slate-600 border-slate-200 hover:bg-white'">
                                        <i :class="currentProject.isStarred ? 'ph ph-star-fill' : 'ph ph-star'"></i> Star {{ currentProject.starCount }}
                                    </button>
                                    <button @click="toggleFavorite(currentProject)" class="px-3 py-2 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5"
                                            :class="currentProject.isFavorited ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-white/70 text-slate-600 border-slate-200 hover:bg-white'">
                                        <i :class="currentProject.isFavorited ? 'ph ph-bookmark-simple-fill' : 'ph ph-bookmark-simple'"></i> 收藏
                                    </button>
                                </div>
                            </div>

                            <div class="rounded-2xl bg-[#132231] text-slate-100 border border-slate-900 shadow-lg overflow-hidden">
                                <div class="px-4 py-3 border-b border-white/10 flex items-center justify-between gap-2">
                                    <span class="text-xs font-bold flex items-center gap-2 shrink-0"><i class="ph ph-git-branch"></i> Clone 地址</span>
                                    <div class="flex items-center gap-1.5">
                                        <button @click="cloneMode = 'token'" class="text-[10px] font-bold px-2.5 py-1 rounded-lg transition-all"
                                                :class="cloneMode === 'token' ? 'bg-white/25 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'">
                                            HTTPS + Token
                                        </button>
                                        <button @click="cloneMode = 'https'" class="text-[10px] font-bold px-2.5 py-1 rounded-lg transition-all"
                                                :class="cloneMode === 'https' ? 'bg-white/25 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'">
                                            HTTPS
                                        </button>
                                    </div>
                                </div>
                                <div v-if="cloneMode === 'token'" class="px-4 py-3">
                                    <div v-if="authenticatedCloneUrl" class="flex items-center gap-2">
                                        <code class="flex-1 font-mono text-xs overflow-x-auto select-text text-emerald-300 whitespace-nowrap">git clone {{ authenticatedCloneUrl }}</code>
                                        <button @click="copyAuthClone" class="text-[10px] font-bold px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 transition-all flex items-center gap-1 shrink-0">
                                            <i :class="copiedAuthClone ? 'ph ph-check' : 'ph ph-copy'"></i> {{ copiedAuthClone ? '已复制' : '复制' }}
                                        </button>
                                    </div>
                                    <div v-else class="flex items-center justify-between gap-3">
                                        <p class="text-[11px] text-slate-400 leading-relaxed">生成 Token 后可获取可直接粘贴的 Clone 命令。</p>
                                        <button @click="generateTokenForClone" class="text-[10px] font-bold px-3 py-1.5 rounded-lg bg-emerald-500/80 hover:bg-emerald-500 text-white transition-all flex items-center gap-1 shrink-0">
                                            <i class="ph ph-key"></i> 生成 Token
                                        </button>
                                    </div>
                                </div>
                                <div v-else class="px-4 py-3">
                                    <div class="flex items-center gap-2">
                                        <code class="flex-1 font-mono text-xs overflow-x-auto select-text whitespace-nowrap">{{ currentProject.cloneUrl }}</code>
                                        <button @click="copyClone(currentProject)" class="text-[10px] font-bold px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 transition-all flex items-center gap-1 shrink-0">
                                            <i :class="copiedProjectId === currentProject.id ? 'ph ph-check' : 'ph ph-copy'"></i> {{ copiedProjectId === currentProject.id ? '已复制' : '复制' }}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <section class="rounded-2xl bg-white/55 border border-white/70 overflow-hidden">
                                <div class="px-4 py-3 border-b border-slate-100 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                                    <div>
                                        <h3 class="text-xs font-bold text-slate-700 flex items-center gap-1.5"><i class="ph ph-folder-open"></i> 项目文件</h3>
                                        <p class="text-[10px] text-slate-400 mt-1">实时读取 Gitea 仓库目录，点击文件夹进入、点击文件预览。</p>
                                    </div>
                                    <div class="flex flex-wrap items-center gap-1.5 text-[10px]">
                                        <button
                                            v-for="crumb in repoBreadcrumbs"
                                            :key="crumb.path || 'root'"
                                            @click="loadRepoBrowser(crumb.path)"
                                            class="px-2 py-1 rounded-lg border transition-all"
                                            :class="crumb.path === repoBrowserPath ? 'bg-slate-900 text-white border-slate-900' : 'bg-white/70 text-slate-600 border-slate-200 hover:bg-white'"
                                        >
                                            {{ crumb.label }}
                                        </button>
                                    </div>
                                </div>

                                <div v-if="repoBrowserLoading" class="px-4 py-8 text-center text-xs text-slate-400">正在同步 Gitea 文件目录...</div>
                                <div v-else-if="repoBrowserError" class="px-4 py-6 text-center text-xs text-rose-500">{{ repoBrowserError }}</div>
                                <div v-else-if="repoBrowserEntries.length === 0" class="px-4 py-6 text-center text-xs text-slate-400">当前目录为空，等待首次 push 后刷新。</div>
                                <div v-else class="overflow-x-auto">
                                    <table class="w-full text-left text-[11px]">
                                        <thead class="bg-slate-50/80 text-slate-500">
                                            <tr>
                                                <th class="px-4 py-2 font-bold">名称</th>
                                                <th class="px-4 py-2 font-bold w-28">大小</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr
                                                v-for="entry in repoBrowserEntries"
                                                :key="entry.path || entry.name"
                                                @click="openRepoEntry(entry)"
                                                class="border-t border-slate-100 hover:bg-white/80 cursor-pointer transition-colors"
                                            >
                                                <td class="px-4 py-2.5 font-medium text-slate-800">
                                                    <span class="inline-flex items-center gap-2 min-w-0">
                                                        <i :class="entry.type === 'dir' ? 'ph ph-folder text-amber-500' : 'ph ph-file-text text-slate-400'"></i>
                                                        <span class="truncate">{{ entry.name }}</span>
                                                    </span>
                                                </td>
                                                <td class="px-4 py-2.5 text-slate-500 font-mono">{{ entry.type === 'dir' ? '目录' : formatFileSize(entry.size) }}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>

                                <div v-if="repoBrowserBlob" class="border-t border-slate-100 bg-slate-950 text-slate-100">
                                    <div class="px-4 py-2 border-b border-white/10 flex items-center justify-between gap-3">
                                        <span class="text-[10px] font-bold truncate">{{ repoBrowserBlob.path }}</span>
                                        <span class="text-[10px] text-slate-400 shrink-0">{{ formatFileSize(repoBrowserBlob.size) }}</span>
                                    </div>
                                    <pre v-if="repoBrowserBlob.previewable" class="px-4 py-3 text-[11px] leading-relaxed overflow-x-auto whitespace-pre-wrap">{{ repoBrowserBlob.content }}</pre>
                                    <div v-else class="px-4 py-4 text-[11px] text-slate-400">该文件为二进制或体积较大，暂不支持在线预览，请下载 ZIP 或 clone 后查看。</div>
                                </div>
                            </section>

                            <div class="grid grid-cols-1 xl:grid-cols-3 gap-3">
                                <section class="rounded-2xl bg-white/55 border border-white/70 p-4 min-w-0">
                                    <h3 class="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-3"><i class="ph ph-git-commit"></i> 最近提交</h3>
                                    <div v-if="(currentProject.recentCommits || []).length === 0" class="text-[11px] text-slate-400">暂无真实 push 记录。</div>
                                    <div v-else class="space-y-2">
                                        <article v-for="commit in (currentProject.recentCommits || []).slice(0, 4)" :key="commit.sha || commit.id" class="min-w-0">
                                            <div class="text-[11px] font-bold text-slate-800 truncate">{{ commit.message }}</div>
                                            <div class="text-[10px] text-slate-400 truncate">{{ commit.author }} · {{ commit.branch }}</div>
                                        </article>
                                    </div>
                                </section>

                                <section class="rounded-2xl bg-white/55 border border-white/70 p-4 min-w-0">
                                    <h3 class="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-3"><i class="ph ph-git-pull-request"></i> Pull Request</h3>
                                    <div v-if="(currentProject.pullRequests || []).length === 0" class="text-[11px] text-slate-400">暂无 PR 同步记录。</div>
                                    <div v-else class="space-y-2">
                                        <article v-for="pr in (currentProject.pullRequests || []).slice(0, 4)" :key="pr.id || pr.number" class="min-w-0">
                                            <div class="flex items-center justify-between gap-2">
                                                <span class="text-[11px] font-bold text-slate-800 truncate">#{{ pr.number }} {{ pr.title }}</span>
                                                <span class="text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{{ pr.status }}</span>
                                            </div>
                                            <div class="text-[10px] text-slate-400 truncate">{{ pr.sourceBranch }} -> {{ pr.targetBranch }}</div>
                                        </article>
                                    </div>
                                </section>

                                <section class="rounded-2xl bg-white/55 border border-white/70 p-4 min-w-0">
                                    <h3 class="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-3"><i class="ph ph-robot"></i> AI Git 教练</h3>
                                    <div v-if="(currentProject.aiGitCoachFeedback || []).length === 0" class="text-[11px] text-slate-400">等待提交后生成反馈。</div>
                                    <div v-else class="space-y-2">
                                        <article v-for="feedback in (currentProject.aiGitCoachFeedback || []).slice(0, 3)" :key="feedback.id || feedback.sha" class="text-[11px] text-slate-600 leading-relaxed">
                                            {{ feedback.summary }}
                                        </article>
                                    </div>
                                </section>
                            </div>

                            <article class="markdown-body bg-white/50 border border-white/70 rounded-2xl p-5 text-sm text-slate-700" v-html="formatMarkdown(currentProject.readme)"></article>
                        </div>
                    </main>

                    <aside class="flex flex-col gap-5 overflow-y-auto no-scrollbar min-h-0 pb-4">
                        <div class="glass-panel-liquid glass-panel-sidebar p-5">
                            <h3 class="text-xs font-bold text-slate-600 mb-4 flex items-center gap-1.5"><i class="ph ph-user-circle"></i> 项目信息</h3>
                            <div class="repo-sidebar-meta">
                                <div class="repo-sidebar-meta-row"><span>发布者</span><span>{{ currentProject.author }}</span></div>
                                <div class="repo-sidebar-meta-row"><span>课程</span><span>{{ currentProject.course || '未标注' }}</span></div>
                                <div class="repo-sidebar-meta-row"><span>更新</span><span class="font-mono font-normal text-slate-600">{{ formatTime(currentProject.updatedAt || currentProject.createdAt) }}</span></div>
                            </div>
                            <div v-if="currentProject.tags?.length" class="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-slate-100/80">
                                <span v-for="tag in currentProject.tags" :key="tag" class="text-[9px] font-bold px-2 py-0.5 bg-white/70 text-slate-500 rounded border border-slate-100">#{{ tag }}</span>
                            </div>
                        </div>

                        <div class="glass-panel-liquid glass-panel-sidebar p-5">
                            <h3 class="text-xs font-bold text-slate-600 mb-4 flex items-center gap-1.5"><i class="ph ph-webhooks-logo"></i> Gitea 同步</h3>
                            <div class="repo-sidebar-meta">
                                <div class="repo-sidebar-meta-row">
                                    <span>Webhook</span>
                                    <span :class="currentProject.webhookConfigured ? 'text-emerald-700' : 'text-amber-600'">{{ currentProject.webhookConfigured ? '已配置' : 'Fallback' }}</span>
                                </div>
                                <div class="repo-sidebar-meta-row"><span>同步状态</span><span>{{ currentProject.giteaSyncStatus || 'fallback' }}</span></div>
                                <div class="repo-sidebar-meta-row"><span>最近同步</span><span class="font-mono font-normal text-slate-600">{{ currentProject.lastSyncedAt ? formatTime(currentProject.lastSyncedAt) : '-' }}</span></div>
                            </div>
                            <div v-if="repoBrowserLanguages.length" class="mt-4 pt-4 border-t border-slate-100/80 space-y-2">
                                <div class="text-[10px] font-bold text-slate-500">语言占比</div>
                                <div v-for="lang in repoBrowserLanguages.slice(0, 5)" :key="lang.name" class="space-y-1">
                                    <div class="flex items-center justify-between text-[10px] text-slate-600">
                                        <span>{{ lang.name }}</span>
                                        <span>{{ lang.percent }}%</span>
                                    </div>
                                    <div class="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                                        <div class="h-full bg-primary/70 rounded-full" :style="{ width: lang.percent + '%' }"></div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="glass-panel-liquid glass-panel-sidebar p-5 flex flex-col gap-3">
                            <h3 class="text-xs font-bold text-slate-600 flex items-center gap-1.5"><i class="ph ph-git-branch"></i> Gitea 账号</h3>
                            <div class="repo-sidebar-meta">
                                <div class="repo-sidebar-meta-row"><span>用户名</span><span>{{ giteaIdentity?.giteaUsername || '等待同步' }}</span></div>
                                <div class="repo-sidebar-meta-row"><span>邮箱</span><span class="font-normal">{{ giteaIdentity?.giteaEmail || '等待同步' }}</span></div>
                                <div class="repo-sidebar-meta-row"><span>同步</span><span>{{ giteaIdentity?.syncStatus || 'mock' }}</span></div>
                            </div>
                            <button @click="handleRotateGiteaToken" class="liquid-glass-btn w-full min-h-[40px] py-2.5 rounded-xl text-xs font-bold mt-1">生成/重置访问 Token</button>
                            <div v-if="generatedToken" class="repo-token-box">
                                <p>{{ tokenWarning }}</p>
                                <code>{{ generatedToken }}</code>
                                <button type="button" @click="copyGeneratedToken" class="repo-copy-btn repo-copy-btn--dark">
                                    <i :class="copiedToken ? 'ph ph-check' : 'ph ph-copy'"></i>
                                    {{ copiedToken ? '已复制' : '复制 Token' }}
                                </button>
                            </div>
                            <div v-if="giteaIdentity?.gitConfigCommands?.length" class="repo-git-config-box">
                                <div class="repo-git-config-header">
                                    <span>Git 配置</span>
                                    <button type="button" @click="copyGitConfig" class="repo-copy-btn repo-copy-btn--light">
                                        <i :class="copiedGitConfigAll ? 'ph ph-check' : 'ph ph-copy'"></i>
                                        {{ copiedGitConfigAll ? '已复制' : '复制全部' }}
                                    </button>
                                </div>
                                <div v-for="(command, index) in giteaIdentity.gitConfigCommands" :key="index" class="repo-git-config-line">
                                    <code>{{ command }}</code>
                                    <button type="button" @click="copyGitConfigLine(command)" class="repo-copy-btn-icon" :title="copiedGitConfigLine === command ? '已复制' : '复制此行'">
                                        <i :class="copiedGitConfigLine === command ? 'ph ph-check' : 'ph ph-copy'"></i>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="glass-panel-liquid glass-panel-sidebar p-5 flex flex-col gap-2.5">
                            <button @click="openReport(currentProject)" class="w-full min-h-[40px] py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 bg-red-50 border border-red-100 text-red-600 hover:bg-red-100 transition-all">
                                <i class="ph ph-flag"></i> 举报违规项目
                            </button>
                        </div>
                    </aside>
                </div>

                <div v-else class="flex-1 min-h-0 flex flex-col lg:flex-row gap-5 overflow-hidden">
                    <aside class="w-full lg:w-[20%] shrink-0 flex lg:flex-col gap-4 overflow-x-auto lg:overflow-visible">
                        <div class="glass-panel-liquid p-4 flex-1 min-w-[260px]">
                            <div class="text-xs font-bold text-slate-400 mb-3 px-2 flex items-center gap-1">
                                <i class="ph ph-brackets-curly"></i> 语言索引
                            </div>
                            <button @click="activeLanguage = 'all'" class="w-full text-left py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-between transition-all mb-2"
                                    :class="activeLanguage === 'all' ? 'bg-primary text-white shadow-md' : 'bg-white/40 text-slate-600 hover:bg-white'">
                                <span>全部项目</span><span>{{ projects.length }}</span>
                            </button>
                            <button v-for="language in languages" :key="language.name" @click="activeLanguage = language.name"
                                    class="w-full text-left py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-between transition-all mb-2"
                                    :class="activeLanguage === language.name ? 'bg-primary text-white shadow-md' : 'bg-white/40 text-slate-600 hover:bg-white'">
                                <span class="flex items-center gap-2"><span class="w-2 h-2 rounded-full" :class="languageTone(language.name)"></span>{{ language.name }}</span>
                                <span>{{ language.count }}</span>
                            </button>
                        </div>
                    </aside>

                    <main class="flex-1 min-w-0 h-full flex flex-col gap-4">
                        <div class="glass-panel-liquid p-4 shrink-0 flex flex-col gap-3">
                            <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-3">
                                <div class="relative flex-1">
                                    <i class="ph ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
                                    <input v-model="query" placeholder="搜索项目名、标签、课程或 README 关键词..." class="liquid-glass-input w-full pl-9 pr-4 py-2.5 text-xs outline-none">
                                </div>
                                <div class="flex items-center gap-2">
                                    <div class="flex border border-slate-200/60 rounded-xl overflow-hidden p-0.5 bg-white/40">
                                        <button @click="sortBy = 'recommended'" class="px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all" :class="sortBy === 'recommended' ? 'bg-primary text-white' : 'text-slate-500'">推荐</button>
                                        <button @click="sortBy = 'favorites'" class="px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all" :class="sortBy === 'favorites' ? 'bg-primary text-white' : 'text-slate-500'">收藏最多</button>
                                        <button @click="sortBy = 'relevant'" class="px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all" :class="sortBy === 'relevant' ? 'bg-primary text-white' : 'text-slate-500'">最相关</button>
                                        <button @click="sortBy = 'latest'" class="px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all" :class="sortBy === 'latest' ? 'bg-primary text-white' : 'text-slate-500'">最新</button>
                                    </div>
                                    <button @click="publishOpen = !publishOpen" class="liquid-glass-btn px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5">
                                        <i :class="publishOpen ? 'ph ph-x' : 'ph ph-plus-circle'"></i> {{ publishOpen ? '收起' : '发布项目' }}
                                    </button>
                                </div>
                            </div>

                            <transition name="fade">
                                <form v-if="publishOpen" @submit.prevent="createRepository" class="border-t border-slate-100 pt-4 grid grid-cols-1 xl:grid-cols-2 gap-3">
                                    <input v-model="publishForm.title" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="项目名称，如：图算法可视化实验室">
                                    <input v-model="publishForm.slug" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="仓库 slug，如 graph-lab（可留空自动生成）">
                                    <textarea v-model="publishForm.description" rows="3" class="liquid-glass-input px-4 py-3 text-xs outline-none resize-none xl:col-span-2" placeholder="项目简介：说明它解决什么学习问题、适合什么课程场景"></textarea>
                                    <div class="grid grid-cols-2 gap-2">
                                        <select v-model="publishForm.language" class="bg-white/70 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2.5 outline-none">
                                            <option>Vue</option><option>TypeScript</option><option>Python</option><option>Java</option><option>C++</option><option>Other</option>
                                        </select>
                                        <input v-model="publishForm.course" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="关联课程">
                                    </div>
                                    <div class="flex gap-2">
                                        <input v-model="publishForm.tags" class="liquid-glass-input flex-1 px-4 py-2.5 text-xs outline-none" placeholder="标签，用逗号分隔">
                                        <label class="shrink-0 px-3 py-2.5 rounded-xl bg-white/60 border border-slate-200 text-[10px] font-bold text-slate-600 flex items-center gap-1.5">
                                            <input type="checkbox" v-model="publishForm.private" class="accent-slate-900">
                                            {{ publishForm.private ? '私有' : '公开' }}
                                        </label>
                                    </div>
                                    <div class="xl:col-span-2 flex gap-2">
                                        <input v-model="publishForm.collaborators" class="liquid-glass-input flex-1 px-4 py-2.5 text-xs outline-none" placeholder="拉取好友共同管理：输入用户名，用逗号分隔">
                                        <button type="submit" :disabled="isPublishing" class="liquid-glass-btn px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5">
                                            <i :class="isPublishing ? 'ph ph-spinner animate-spin' : 'ph ph-paper-plane-tilt'"></i> 发布
                                        </button>
                                    </div>
                                </form>
                            </transition>
                        </div>

                        <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col gap-4">
                            <div v-if="loading" class="glass-panel-liquid p-8 text-center text-xs text-slate-400">正在同步代码仓库索引...</div>
                            <div v-else-if="filteredProjects.length === 0" class="glass-panel-liquid p-8 text-center text-xs text-slate-400">没有匹配项目，换个关键词或发布第一个开源项目。</div>
                            <article v-for="project in filteredProjects" :key="project.id" @click="viewProject(project)" class="glass-panel-liquid p-5 shrink-0 cursor-pointer border border-white/60 hover:-translate-y-0.5 transition-all group">
                                <div class="flex items-start justify-between gap-4">
                                    <div class="min-w-0">
                                        <div class="flex items-center gap-2 mb-2">
                                            <span class="w-2.5 h-2.5 rounded-full" :class="languageTone(project.language)"></span>
                                            <span class="text-[10px] font-bold text-slate-500">{{ project.language }}</span>
                                            <span class="text-[10px] text-slate-400">{{ project.course }}</span>
                                        </div>
                                        <h2 class="text-base font-serif font-bold text-slate-900 group-hover:text-primary transition-colors">{{ project.title }}</h2>
                                        <p class="text-[11px] text-slate-500 leading-relaxed mt-1 line-clamp-2">{{ project.description }}</p>
                                    </div>
                                    <div class="flex gap-2 shrink-0">
                                        <button @click="copyClone(project, $event)" class="w-9 h-9 rounded-xl bg-white/70 border border-slate-200 text-slate-500 hover:text-primary hover:bg-white transition-all" :title="project.cloneUrl">
                                            <i class="ph ph-copy"></i>
                                        </button>
                                    </div>
                                </div>
                                <div class="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 text-[10px] text-slate-500 font-bold">
                                    <div class="flex flex-wrap gap-1.5">
                                        <span v-for="tag in project.tags" :key="tag" class="px-2 py-0.5 bg-white/70 rounded border border-slate-100">#{{ tag }}</span>
                                    </div>
                                    <div class="flex items-center gap-3">
                                        <button @click="toggleStar(project, $event)" class="flex items-center gap-1 hover:text-amber-600" :class="project.isStarred && 'text-amber-600'"><i :class="project.isStarred ? 'ph ph-star-fill' : 'ph ph-star'"></i>{{ project.starCount }}</button>
                                        <button @click="toggleFavorite(project, $event)" class="flex items-center gap-1 hover:text-rose-600" :class="project.isFavorited && 'text-rose-600'"><i :class="project.isFavorited ? 'ph ph-bookmark-simple-fill' : 'ph ph-bookmark-simple'"></i>{{ project.favoriteCount }}</button>
                                        <span class="font-mono">{{ formatTime(project.updatedAt || project.createdAt) }}</span>
                                    </div>
                                </div>
                            </article>
                        </div>
                    </main>

                    <aside class="w-full lg:w-[25%] shrink-0 h-full flex flex-col gap-5 overflow-y-auto no-scrollbar min-h-0 pb-4">
                        <div class="glass-panel-liquid glass-panel-sidebar p-5 grid grid-cols-3 gap-3 text-center">
                            <div><div class="text-xl font-serif font-bold text-slate-900">{{ repoStats.total }}</div><div class="text-[9px] text-slate-400 font-bold mt-1">项目</div></div>
                            <div><div class="text-xl font-serif font-bold text-slate-900">{{ repoStats.stars }}</div><div class="text-[9px] text-slate-400 font-bold mt-1">Star</div></div>
                            <div><div class="text-xl font-serif font-bold text-slate-900">{{ repoStats.favorites }}</div><div class="text-[9px] text-slate-400 font-bold mt-1">收藏</div></div>
                        </div>
                        <div class="glass-panel-liquid glass-panel-sidebar p-5 flex flex-col gap-3">
                            <h3 class="text-xs font-bold text-slate-600 flex items-center gap-1.5"><i class="ph ph-git-branch"></i> Gitea 账号</h3>
                            <div class="repo-sidebar-meta">
                                <div class="repo-sidebar-meta-row"><span>用户名</span><span>{{ giteaIdentity?.giteaUsername || '等待同步' }}</span></div>
                                <div class="repo-sidebar-meta-row"><span>邮箱</span><span class="font-normal">{{ giteaIdentity?.giteaEmail || '等待同步' }}</span></div>
                                <div class="repo-sidebar-meta-row"><span>同步</span><span>{{ giteaIdentity?.syncStatus || 'mock' }}</span></div>
                            </div>
                            <button @click="handleRotateGiteaToken" class="liquid-glass-btn w-full min-h-[40px] py-2.5 rounded-xl text-xs font-bold mt-1">生成/重置访问 Token</button>
                            <div v-if="generatedToken" class="repo-token-box">
                                <p>{{ tokenWarning }}</p>
                                <code>{{ generatedToken }}</code>
                                <button type="button" @click="copyGeneratedToken" class="repo-copy-btn repo-copy-btn--dark">
                                    <i :class="copiedToken ? 'ph ph-check' : 'ph ph-copy'"></i>
                                    {{ copiedToken ? '已复制' : '复制 Token' }}
                                </button>
                            </div>
                            <div v-if="giteaIdentity?.gitConfigCommands?.length" class="repo-git-config-box">
                                <div class="repo-git-config-header">
                                    <span>Git 配置</span>
                                    <button type="button" @click="copyGitConfig" class="repo-copy-btn repo-copy-btn--light">
                                        <i :class="copiedGitConfigAll ? 'ph ph-check' : 'ph ph-copy'"></i>
                                        {{ copiedGitConfigAll ? '已复制' : '复制全部' }}
                                    </button>
                                </div>
                                <div v-for="(command, index) in giteaIdentity.gitConfigCommands" :key="index" class="repo-git-config-line">
                                    <code>{{ command }}</code>
                                    <button type="button" @click="copyGitConfigLine(command)" class="repo-copy-btn-icon" :title="copiedGitConfigLine === command ? '已复制' : '复制此行'">
                                        <i :class="copiedGitConfigLine === command ? 'ph ph-check' : 'ph ph-copy'"></i>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="glass-panel-liquid glass-panel-sidebar p-5 flex flex-col gap-3">
                            <h3 class="text-xs font-bold text-slate-600 flex items-center gap-1.5"><i class="ph ph-compass"></i> 热门项目仓库</h3>
                            <button v-for="project in featuredProjects" :key="project.id" @click="viewProject(project)" class="text-left p-3 rounded-xl bg-white/45 border border-white/60 hover:bg-white transition-all shrink-0">
                                <div class="text-xs font-bold text-slate-800 line-clamp-2">{{ project.title }}</div>
                                <div class="mt-2 flex items-center justify-between text-[10px] text-slate-400 font-bold">
                                    <span>{{ project.language }}</span><span><i class="ph ph-star"></i> {{ project.starCount }}</span>
                                </div>
                            </button>
                        </div>
                    </aside>
                </div>
            </div>

            <transition name="fade">
                <div v-if="reportTarget" class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
                    <div class="bg-white rounded-3xl shadow-float w-full max-w-lg border border-slate-200 overflow-hidden">
                        <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                            <h3 class="text-base font-bold text-slate-900 flex items-center gap-1.5"><i class="ph ph-flag text-red-500"></i> 举报项目仓库</h3>
                            <button @click="reportTarget = null" class="text-slate-400 hover:text-slate-700"><i class="ph ph-x text-lg"></i></button>
                        </div>
                        <div class="p-6 flex flex-col gap-4">
                            <div class="text-xs text-slate-500">项目：<span class="font-bold text-slate-900">{{ reportTarget.title }}</span></div>
                            <select v-model="reportForm.reason" class="bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2.5 outline-none">
                                <option>违规内容</option><option>版权风险</option><option>恶意代码</option><option>无关广告</option>
                            </select>
                            <textarea v-model="reportForm.description" rows="5" class="bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2.5 outline-none resize-none" placeholder="请说明具体位置或原因，教师审核时会看到这段说明。"></textarea>
                            <div class="flex justify-end gap-2">
                                <button @click="reportTarget = null" class="px-4 py-2 rounded-xl text-xs font-bold bg-white border border-slate-200 text-slate-500">取消</button>
                                <button @click="submitReport" class="px-5 py-2 rounded-xl text-xs font-bold bg-red-600 text-white hover:bg-red-700">提交举报</button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition>
        </section>
    `
};
