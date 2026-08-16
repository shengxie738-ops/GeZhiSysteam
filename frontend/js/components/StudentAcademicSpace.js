import { ref, computed, onMounted, watch } from 'vue';
import StudentCodeRepository from './StudentCodeRepository.js';
import StudentForum from './StudentForum.js';
import { repositoryApi } from '../api/repository.js';
import { userApi } from '../api/userApi.js';
import { getUserDisplayName } from '../utils/dashboardGreeting.js';

export default {
    name: 'StudentAcademicSpace',
    components: {
        StudentCodeRepository,
        StudentForum
    },
    props: {
        currentUser: { type: Object, default: null }
    },
    emits: ['show-toast'],
    setup(props, { emit }) {
        const activeSection = ref('profile');
        const loadingProfile = ref(true);
        const profile = ref({ ownProjects: [], favoriteProjects: [], starredProjects: [] });
        const profileUser = ref(null);
        const creating = ref(false);
        const createOpen = ref(false);
        const createForm = ref({
            title: '',
            slug: '',
            description: '',
            language: 'Vue',
            course: '数据结构',
            tags: '',
            private: false,
            collaborators: ''
        });

        const currentUserId = computed(() => props.currentUser?.username || 'anonymous');
        const looksLikeStudentId = (value) => /^\d{8,}$/.test(String(value || ''));
        const currentUserDisplayName = computed(() => {
            const propDisplayName = getUserDisplayName(props.currentUser);
            if (propDisplayName !== '同学' && propDisplayName !== currentUserId.value) {
                return propDisplayName;
            }

            const fetchedDisplayName = getUserDisplayName(profileUser.value);
            if (fetchedDisplayName !== '同学' && fetchedDisplayName !== currentUserId.value) {
                return fetchedDisplayName;
            }

            return looksLikeStudentId(currentUserId.value) ? '同学' : propDisplayName;
        });

        const spaceNav = [
            { id: 'profile', name: '个人主页', desc: '仓库与收藏夹', icon: 'ph-house' },
            { id: 'repositories', name: '代码仓库', desc: '发现热门项目', icon: 'ph-git-branch' },
            { id: 'pulls', name: '代码拉取请求', desc: '协作变更审阅', icon: 'ph-git-pull-request' },
            { id: 'forum', name: '论坛', desc: '进入现有论坛', icon: 'ph-chat-circle-dots' }
        ];

        const pullRequests = ref([
            {
                id: 'pr-2026-071',
                title: 'feat: 为图算法实验补充 DFS 可视化轨迹',
                repo: '算法可视化实验室',
                author: '李心悦',
                status: '待审阅',
                checks: '3/3',
                updatedAt: '今天 10:24'
            },
            {
                id: 'pr-2026-069',
                title: 'docs: 更新 RAG 助教插件 README 引用来源',
                repo: '课程 RAG 助教插件',
                author: '王明',
                status: '可合并',
                checks: '2/2',
                updatedAt: '昨天 21:16'
            },
            {
                id: 'pr-2026-064',
                title: 'fix: 修复 Mini Compiler 词法状态回退问题',
                repo: 'Mini Compiler Notes',
                author: '赵雷',
                status: '需修改',
                checks: '1/3',
                updatedAt: '6月30日'
            }
        ]);

        const profileStats = computed(() => ({
            own: profile.value.ownProjects.length,
            favorites: profile.value.favoriteProjects.length,
            stars: profile.value.starredProjects.length
        }));

        const loadProfile = async () => {
            loadingProfile.value = true;
            try {
                profile.value = await repositoryApi.getUserRepositoryProfile(currentUserId.value);
            } catch (err) {
                emit('show-toast', '个人学术空间资料加载失败', 'error');
            } finally {
                loadingProfile.value = false;
            }
        };

        const loadProfileUser = async () => {
            if (!currentUserId.value || currentUserId.value === 'anonymous') {
                profileUser.value = null;
                return;
            }

            try {
                profileUser.value = await userApi.getUserInfo(currentUserId.value);
            } catch (err) {
                profileUser.value = null;
            }
        };

        const createRepository = async () => {
            const title = createForm.value.title.trim();
            const description = createForm.value.description.trim();
            if (!title || !description) {
                emit('show-toast', '请填写仓库名称和简介', 'error');
                return;
            }

            creating.value = true;
            try {
                const tags = createForm.value.tags
                    .replace(/，/g, ',')
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean);
                const collaborators = createForm.value.collaborators
                    .replace(/，/g, ',')
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean);

                await repositoryApi.createRepository({
                    ...createForm.value,
                    title,
                    description,
                    tags,
                    collaborators,
                    author: currentUserId.value,
                    avatar: props.currentUser?.avatar_url || ''
                });

                createForm.value = {
                    title: '',
                    slug: '',
                    description: '',
                    language: 'Vue',
                    course: '数据结构',
                    tags: '',
                    private: false,
                    collaborators: ''
                };
                createOpen.value = false;
                emit('show-toast', '个人仓库已创建，可在学术空间共同管理', 'success');
                await loadProfile();
            } catch (err) {
                emit('show-toast', '仓库创建失败，请稍后再试', 'error');
            } finally {
                creating.value = false;
            }
        };

        const navigateProject = ref(null);

        const openRepository = (project) => {
            navigateProject.value = project;
            activeSection.value = 'repositories';
        };

        const clearNavigateProject = () => {
            navigateProject.value = null;
        };

        const relayToast = (...args) => {
            emit('show-toast', ...args);
        };

        onMounted(loadProfile);
        watch(() => props.currentUser?.username, loadProfileUser, { immediate: true });

        return {
            activeSection,
            loadingProfile,
            profile,
            profileUser,
            creating,
            createOpen,
            createForm,
            currentUserId,
            currentUserDisplayName,
            spaceNav,
            pullRequests,
            profileStats,
            loadProfile,
            createRepository,
            openRepository,
            navigateProject,
            clearNavigateProject,
            relayToast
        };
    },
    template: `
        <section class="academic-space-shell absolute inset-0 overflow-hidden bg-slate-50 select-none">
            <div class="h-full grid grid-cols-1 lg:grid-cols-[236px_1fr]">
                <aside class="border-r border-slate-200 bg-white/82 backdrop-blur-xl flex flex-col min-h-0">
                    <div class="px-5 py-5 border-b border-slate-200">
                        <div class="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-sm mb-4">
                            <i class="ph ph-git-branch text-xl"></i>
                        </div>
                        <p class="text-[10px] font-bold text-slate-400 tracking-[0.18em] uppercase">Academic Space</p>
                        <h2 class="text-xl font-bold text-slate-900 mt-1" style="font-family: 'Noto Serif SC', serif;">学术空间</h2>
                        <p class="text-xs text-slate-500 leading-relaxed mt-2">统一管理代码资产、协作请求与学术讨论。</p>
                    </div>

                    <nav class="p-3 flex lg:flex-col gap-2 overflow-x-auto lg:overflow-y-auto no-scrollbar">
                        <button v-for="item in spaceNav" :key="item.id"
                                @click="activeSection = item.id"
                                class="min-w-[148px] lg:min-w-0 w-full px-3 py-3 rounded-xl text-left transition-all border flex items-center gap-3"
                                :class="activeSection === item.id
                                    ? 'bg-slate-100 text-slate-950 border-slate-200 shadow-sm'
                                    : 'bg-transparent text-slate-600 border-transparent hover:bg-slate-50 hover:text-slate-900'">
                            <span class="w-8 h-8 rounded-lg flex items-center justify-center border"
                                  :class="activeSection === item.id ? 'bg-white border-slate-200' : 'bg-white/70 border-slate-100'">
                                <i :class="['ph', item.icon, 'text-base']"></i>
                            </span>
                            <span class="min-w-0">
                                <span class="block text-sm font-bold truncate">{{ item.name }}</span>
                                <span class="block text-[10px] text-slate-400 truncate">{{ item.desc }}</span>
                            </span>
                        </button>
                    </nav>

                    <div class="mt-auto px-5 py-4 border-t border-slate-200 hidden lg:block">
                        <p class="text-[10px] text-slate-400 font-mono">Signed in as</p>
                        <p class="text-sm text-slate-800 font-bold truncate">{{ currentUserId }}</p>
                    </div>
                </aside>

                <main class="min-w-0 min-h-0 flex flex-col">
                    <header class="h-16 border-b border-slate-200 bg-white/78 backdrop-blur-xl px-5 lg:px-7 flex items-center justify-between shrink-0">
                        <div class="min-w-0">
                            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">GitHub-like layout</p>
                            <h1 class="text-base font-bold text-slate-900 truncate">
                                {{ spaceNav.find(item => item.id === activeSection)?.name || '学术空间' }}
                            </h1>
                        </div>
                        <div class="hidden md:flex items-center gap-2 text-[10px] text-slate-500 font-bold">
                            <template v-if="activeSection === 'forum'">
                                <div class="text-right flex flex-col items-end justify-center">
                                    <span class="text-[10px] text-slate-400 uppercase tracking-widest font-mono mb-0.5">STUDENT COMMUNITY</span>
                                    <span class="text-xs font-bold text-slate-700">格物致知 · 学术广场</span>
                                </div>
                            </template>
                            <template v-else>
                                <span class="px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200">仓库 {{ profileStats.own }}</span>
                                <span class="px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200">收藏 {{ profileStats.favorites }}</span>
                                <span class="px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200">Star {{ profileStats.stars }}</span>
                            </template>
                        </div>
                    </header>

                    <div class="flex-1 min-h-0 overflow-hidden">
                        <div v-if="activeSection === 'profile'" class="h-full overflow-y-auto p-5 lg:p-7">
                            <div class="max-w-[1600px] mx-auto grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-5">
                                <section class="flex flex-col gap-5 min-w-0">
                                    <div class="bg-white border border-slate-200 rounded-xl p-5">
                                        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                                            <div>
                                                <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Profile</p>
                                                <h2 class="text-2xl font-bold text-slate-900 mt-1" style="font-family: 'Noto Serif SC', serif;">{{ currentUserDisplayName }} 的个人主页</h2>
                                                <p class="text-xs text-slate-500 leading-relaxed mt-2 max-w-[62ch]">个人仓库列表、收藏夹、公开权限与协作者配置集中在这里，保持与代码仓库发现页分工清晰。</p>
                                            </div>
                                            <button @click="createOpen = !createOpen" class="min-h-[44px] px-4 rounded-xl text-xs font-bold bg-slate-900 text-white hover:bg-slate-800 active:scale-[0.98] transition-all flex items-center gap-1.5 justify-center">
                                                <i :class="createOpen ? 'ph ph-x' : 'ph ph-plus-circle'"></i>
                                                {{ createOpen ? '收起创建' : '创建代码仓库' }}
                                            </button>
                                        </div>
                                    </div>

                                    <form v-if="createOpen" @submit.prevent="createRepository" class="bg-white border border-slate-200 rounded-xl p-5 grid grid-cols-1 md:grid-cols-2 gap-3">
                                        <div class="md:col-span-2 flex items-center justify-between gap-4 pb-2 border-b border-slate-100">
                                            <div>
                                                <h3 class="text-sm font-bold text-slate-900">新建个人代码仓库</h3>
                                                <p class="text-xs text-slate-500 mt-1">可选择公开权限，或拉取好友共同管理仓库。</p>
                                            </div>
                                            <label class="inline-flex items-center gap-2 text-xs font-bold text-slate-600">
                                                <input type="checkbox" v-model="createForm.private" class="accent-slate-900">
                                                {{ createForm.private ? '私有仓库' : '公开仓库' }}
                                            </label>
                                        </div>
                                        <label class="text-xs font-bold text-slate-600 flex flex-col gap-1.5">
                                            仓库名称
                                            <input v-model="createForm.title" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="如：图算法可视化实验室">
                                        </label>
                                        <label class="text-xs font-bold text-slate-600 flex flex-col gap-1.5">
                                            仓库 Slug
                                            <input v-model="createForm.slug" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="graph-lab，可留空自动生成">
                                        </label>
                                        <label class="md:col-span-2 text-xs font-bold text-slate-600 flex flex-col gap-1.5">
                                            项目简介
                                            <textarea v-model="createForm.description" rows="3" class="liquid-glass-input px-4 py-3 text-xs outline-none resize-none" placeholder="说明项目解决什么学习问题、有哪些协作边界"></textarea>
                                        </label>
                                        <label class="text-xs font-bold text-slate-600 flex flex-col gap-1.5">
                                            语言
                                            <select v-model="createForm.language" class="bg-white/80 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2.5 outline-none">
                                                <option>Vue</option><option>TypeScript</option><option>Python</option><option>Java</option><option>C++</option><option>Other</option>
                                            </select>
                                        </label>
                                        <label class="text-xs font-bold text-slate-600 flex flex-col gap-1.5">
                                            关联课程
                                            <input v-model="createForm.course" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="数据结构">
                                        </label>
                                        <label class="text-xs font-bold text-slate-600 flex flex-col gap-1.5">
                                            标签
                                            <input v-model="createForm.tags" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="算法, 可视化, 课程项目">
                                        </label>
                                        <label class="text-xs font-bold text-slate-600 flex flex-col gap-1.5">
                                            协作者
                                            <input v-model="createForm.collaborators" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="输入好友用户名，用逗号分隔">
                                        </label>
                                        <div class="md:col-span-2 flex justify-end">
                                            <button type="submit" :disabled="creating" class="min-h-[44px] px-5 rounded-xl bg-[#1c2b38] text-white text-xs font-bold hover:bg-[#253645] disabled:opacity-60 flex items-center gap-1.5">
                                                <i :class="creating ? 'ph ph-spinner animate-spin' : 'ph ph-check'"></i>
                                                创建仓库
                                            </button>
                                        </div>
                                    </form>

                                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
                                        <section class="bg-white border border-slate-200 rounded-xl p-5 min-w-0">
                                            <div class="flex items-center justify-between mb-4">
                                                <h3 class="text-sm font-bold text-slate-900 flex items-center gap-1.5"><i class="ph ph-folder-open"></i> 个人仓库列表</h3>
                                                <button @click="loadProfile" class="text-[10px] font-bold text-slate-500 hover:text-slate-900">刷新</button>
                                            </div>
                                            <div v-if="loadingProfile" class="text-xs text-slate-400 py-8 text-center">正在同步个人仓库...</div>
                                            <div v-else-if="profile.ownProjects.length === 0" class="text-xs text-slate-400 py-8 text-center">暂无个人仓库，创建第一个项目开始协作。</div>
                                            <button v-for="project in profile.ownProjects" :key="project.id" @click="openRepository(project)" class="w-full text-left p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-white hover:border-slate-200 transition-all mb-3">
                                                <div class="flex items-center justify-between gap-3">
                                                    <span class="text-sm font-bold text-slate-900 truncate">{{ project.title }}</span>
                                                    <span class="text-[9px] px-2 py-0.5 rounded-full border" :class="project.visibility === 'private' ? 'bg-amber-50 text-amber-700 border-amber-100' : 'bg-emerald-50 text-emerald-700 border-emerald-100'">
                                                        {{ project.visibility === 'private' ? '私有' : '公开' }}
                                                    </span>
                                                </div>
                                                <p class="text-[11px] text-slate-500 line-clamp-2 mt-1">{{ project.description }}</p>
                                                <div class="mt-2 text-[10px] text-slate-400 font-bold flex gap-3">
                                                    <span><i class="ph ph-star"></i> {{ project.starCount }}</span>
                                                    <span><i class="ph ph-bookmark-simple"></i> {{ project.favoriteCount }}</span>
                                                </div>
                                            </button>
                                        </section>

                                        <section class="bg-white border border-slate-200 rounded-xl p-5 min-w-0">
                                            <h3 class="text-sm font-bold text-slate-900 flex items-center gap-1.5 mb-4"><i class="ph ph-bookmark-simple"></i> 收藏夹</h3>
                                            <div v-if="loadingProfile" class="text-xs text-slate-400 py-8 text-center">正在同步收藏夹...</div>
                                            <div v-else-if="profile.favoriteProjects.length === 0" class="text-xs text-slate-400 py-8 text-center">收藏其他用户仓库后会显示在这里。</div>
                                            <button v-for="project in profile.favoriteProjects" :key="project.id" @click="openRepository(project)" class="w-full text-left p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-white hover:border-slate-200 transition-all mb-3">
                                                <div class="flex items-center justify-between gap-3">
                                                    <span class="text-sm font-bold text-slate-900 truncate">{{ project.title }}</span>
                                                    <span class="text-[10px] text-slate-400 font-mono shrink-0">{{ project.language }}</span>
                                                </div>
                                                <p class="text-[11px] text-slate-500 line-clamp-2 mt-1">{{ project.description }}</p>
                                                <p class="text-[10px] text-slate-400 mt-2">作者：{{ project.author }}</p>
                                            </button>
                                        </section>
                                    </div>
                                </section>

                                <aside class="flex flex-col gap-5">
                                    <div class="glass-panel-liquid p-5">
                                        <p class="text-[10px] text-slate-400 font-bold uppercase tracking-[0.18em]">Overview</p>
                                        <div class="grid grid-cols-3 gap-3 mt-4 text-center">
                                             <div><div class="text-2xl font-bold text-slate-900">{{ profileStats.own }}</div><div class="text-[10px] text-slate-500 font-bold mt-1">仓库</div></div>
                                             <div><div class="text-2xl font-bold text-slate-900">{{ profileStats.favorites }}</div><div class="text-[10px] text-slate-500 font-bold mt-1">收藏</div></div>
                                             <div><div class="text-2xl font-bold text-slate-900">{{ profileStats.stars }}</div><div class="text-[10px] text-slate-500 font-bold mt-1">Star</div></div>
                                        </div>
                                    </div>
                                    <div class="bg-white border border-slate-200 rounded-xl p-5">
                                        <h3 class="text-sm font-bold text-slate-900 mb-3">共同管理建议</h3>
                                        <p class="text-xs text-slate-500 leading-relaxed">私有仓库适合小组阶段任务；公开仓库适合作业展示、课程项目沉淀和班级内互相收藏学习。</p>
                                    </div>
                                </aside>
                            </div>
                        </div>

                        <div v-else-if="activeSection === 'repositories'" class="relative h-full min-h-0">
                            <student-code-repository
                                :current-user="currentUser"
                                :initial-project="navigateProject"
                                @show-toast="relayToast"
                                @project-opened="clearNavigateProject"
                            ></student-code-repository>
                        </div>

                        <div v-else-if="activeSection === 'pulls'" class="h-full overflow-y-auto p-5 lg:p-7">
                            <div class="max-w-[1600px] mx-auto flex flex-col gap-5">
                                <section class="bg-white border border-slate-200 rounded-xl p-5">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Pull requests</p>
                                    <h2 class="text-2xl font-bold text-slate-900 mt-1" style="font-family: 'Noto Serif SC', serif;">代码拉取请求</h2>
                                    <p class="text-xs text-slate-500 mt-2 max-w-[64ch] leading-relaxed">集中查看好友协作提交、检查状态与合并风险，后续可接入真实 Git 服务的 PR API。</p>
                                </section>
                                <article v-for="pull in pullRequests" :key="pull.id" class="bg-white border border-slate-200 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div class="min-w-0">
                                        <div class="flex items-center gap-2 mb-2">
                                            <span class="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center">
                                                <i class="ph ph-git-pull-request text-slate-700"></i>
                                            </span>
                                            <span class="text-[10px] text-slate-400 font-mono">{{ pull.id }}</span>
                                            <span class="text-[9px] px-2 py-0.5 rounded-full border"
                                                  :class="pull.status === '可合并' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : pull.status === '需修改' ? 'bg-red-50 text-red-700 border-red-100' : 'bg-amber-50 text-amber-700 border-amber-100'">
                                                {{ pull.status }}
                                            </span>
                                        </div>
                                        <h3 class="text-sm font-bold text-slate-900 truncate">{{ pull.title }}</h3>
                                        <p class="text-xs text-slate-500 mt-1">{{ pull.repo }} / {{ pull.author }} / 检查 {{ pull.checks }} / {{ pull.updatedAt }}</p>
                                    </div>
                                    <div class="flex gap-2 shrink-0">
                                        <button class="min-h-[40px] px-4 rounded-xl text-xs font-bold bg-white border border-slate-200 text-slate-600 hover:bg-slate-50">查看差异</button>
                                        <button class="min-h-[40px] px-4 rounded-xl text-xs font-bold bg-slate-900 text-white hover:bg-slate-800">合并请求</button>
                                    </div>
                                </article>
                            </div>
                        </div>

                        <div v-else-if="activeSection === 'forum'" class="relative h-full min-h-0">
                            <student-forum :current-user="currentUser" :current-user-display-name="currentUserDisplayName" @show-toast="relayToast"></student-forum>
                        </div>
                    </div>
                </main>
            </div>
        </section>
    `
};
