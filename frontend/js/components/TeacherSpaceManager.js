import { ref } from 'vue';
import TeacherForumManager from './TeacherForumManager.js';
import TeacherRepositoryManager from './TeacherRepositoryManager.js';

export default {
    name: 'TeacherSpaceManager',
    components: {
        TeacherForumManager,
        TeacherRepositoryManager
    },
    emits: ['show-toast'],
    setup(_, { emit }) {
        const activePanel = ref('overview');
        const panels = [
            { id: 'overview', name: '管理总览', icon: 'ph-layout', desc: '空间秩序、举报与公告状态' },
            { id: 'forum', name: '论坛管理', icon: 'ph-chat-circle-dots', desc: '帖子审查、公告和话题权重' },
            { id: 'repository', name: '仓库审核', icon: 'ph-git-branch', desc: '项目举报与违规仓库处理' }
        ];

        const signals = [
            { label: '待审帖子', value: '12', tone: 'text-amber-700 bg-amber-50 border-amber-100', icon: 'ph-chat-teardrop' },
            { label: '仓库举报', value: '3', tone: 'text-red-700 bg-red-50 border-red-100', icon: 'ph-flag' },
            { label: '置顶公告', value: '5', tone: 'text-slate-700 bg-slate-50 border-slate-200', icon: 'ph-megaphone' },
            { label: '已校准 AI 回复', value: '18', tone: 'text-emerald-700 bg-emerald-50 border-emerald-100', icon: 'ph-robot' }
        ];

        const relayToast = (...args) => {
            emit('show-toast', ...args);
        };

        return {
            activePanel,
            panels,
            signals,
            relayToast
        };
    },
    template: `
        <section class="absolute inset-0 overflow-hidden bg-slate-50 select-none">
            <div class="h-full grid grid-cols-1 lg:grid-cols-[248px_1fr]">
                <aside class="bg-white/84 backdrop-blur-xl border-r border-slate-200 flex flex-col min-h-0">
                    <div class="px-5 py-5 border-b border-slate-200">
                        <div class="w-10 h-10 rounded-xl bg-[#1c2b38] text-white flex items-center justify-center shadow-sm mb-4">
                            <i class="ph ph-shield-check text-xl"></i>
                        </div>
                        <p class="text-[10px] font-bold text-slate-400 tracking-[0.18em] uppercase">Space Control</p>
                        <h2 class="text-xl font-bold text-slate-900 mt-1" style="font-family: 'Noto Serif SC', serif;">空间管理</h2>
                        <p class="text-xs text-slate-500 leading-relaxed mt-2">论坛治理与仓库审核统一入口，减少教师端重复跳转。</p>
                    </div>

                    <nav class="p-3 flex lg:flex-col gap-2 overflow-x-auto lg:overflow-y-auto no-scrollbar">
                        <button v-for="panel in panels" :key="panel.id"
                                @click="activePanel = panel.id"
                                class="min-w-[158px] lg:min-w-0 w-full px-3 py-3 rounded-xl text-left transition-all border flex items-center gap-3"
                                :class="activePanel === panel.id
                                    ? 'bg-slate-100 text-slate-950 border-slate-200 shadow-sm'
                                    : 'bg-transparent text-slate-600 border-transparent hover:bg-slate-50 hover:text-slate-900'">
                            <span class="w-8 h-8 rounded-lg flex items-center justify-center border"
                                  :class="activePanel === panel.id ? 'bg-white border-slate-200' : 'bg-white/70 border-slate-100'">
                                <i :class="['ph', panel.icon, 'text-base']"></i>
                            </span>
                            <span class="min-w-0">
                                <span class="block text-sm font-bold truncate">{{ panel.name }}</span>
                                <span class="block text-[10px] text-slate-400 truncate">{{ panel.desc }}</span>
                            </span>
                        </button>
                    </nav>

                    <div class="mt-auto px-5 py-4 border-t border-slate-200 hidden lg:block">
                        <p class="text-[10px] text-slate-400 font-mono">Teacher console</p>
                        <p class="text-sm text-slate-800 font-bold truncate">论坛与仓库治理</p>
                    </div>
                </aside>

                <main class="min-w-0 min-h-0 flex flex-col">
                    <header class="h-16 border-b border-slate-200 bg-white/78 backdrop-blur-xl px-5 lg:px-7 flex items-center justify-between shrink-0">
                        <div class="min-w-0">
                            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Unified moderation</p>
                            <h1 class="text-base font-bold text-slate-900 truncate">
                                {{ panels.find(panel => panel.id === activePanel)?.name || '空间管理' }}
                            </h1>
                        </div>
                        <button @click="$emit('show-toast', '空间管理数据已准备同步', 'info')"
                                class="min-h-[40px] px-4 rounded-xl text-xs font-bold bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 flex items-center gap-1.5">
                            <i class="ph ph-arrows-clockwise"></i> 同步状态
                        </button>
                    </header>

                    <div class="flex-1 min-h-0 overflow-hidden">
                        <div v-if="activePanel === 'overview'" class="h-full overflow-y-auto p-5 lg:p-8">
                            <div class="max-w-7xl mx-auto flex flex-col gap-6">
                                <section class="bg-white border border-slate-200 rounded-xl p-6">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Overview</p>
                                    <h2 class="text-2xl font-bold text-slate-900 mt-1" style="font-family: 'Noto Serif SC', serif;">学术空间治理总览</h2>
                                    <p class="text-sm text-slate-500 leading-relaxed max-w-[72ch] mt-2">将老师端原有论坛管理与仓库审核统一到一个工作面板中，教师可以先看风险信号，再进入具体审查台处理。</p>
                                </section>

                                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                                    <button v-for="signal in signals" :key="signal.label"
                                            class="bg-white border border-slate-200 rounded-xl p-5 text-left hover:border-slate-300 transition-all">
                                        <div class="flex items-center justify-between gap-3">
                                            <span class="w-9 h-9 rounded-lg border flex items-center justify-center" :class="signal.tone">
                                                <i :class="['ph', signal.icon]"></i>
                                            </span>
                                            <span class="text-3xl font-bold text-slate-900" style="font-family: 'Barlow Condensed', sans-serif;">{{ signal.value }}</span>
                                        </div>
                                        <p class="text-xs font-bold text-slate-700 mt-4">{{ signal.label }}</p>
                                        <p class="text-[11px] text-slate-400 mt-1">来自论坛、公告、仓库举报与 AI 审核日志。</p>
                                    </button>
                                </div>

                                <div class="grid grid-cols-1 xl:grid-cols-2 gap-5">
                                    <section class="bg-white border border-slate-200 rounded-xl p-5">
                                        <h3 class="text-sm font-bold text-slate-900 flex items-center gap-1.5 mb-3"><i class="ph ph-chat-circle-dots"></i> 论坛管理范围</h3>
                                        <ul class="space-y-2 text-xs text-slate-500 leading-relaxed">
                                            <li>帖子审查、置顶加精、违规删除。</li>
                                            <li>置顶公告发布与热议话题权重配置。</li>
                                            <li>AI 导师回复校准，保证论坛内容严谨。</li>
                                        </ul>
                                        <button @click="activePanel = 'forum'" class="mt-5 min-h-[40px] px-4 rounded-xl bg-[#1c2b38] text-white text-xs font-bold">进入论坛管理</button>
                                    </section>

                                    <section class="bg-white border border-slate-200 rounded-xl p-5">
                                        <h3 class="text-sm font-bold text-slate-900 flex items-center gap-1.5 mb-3"><i class="ph ph-git-branch"></i> 仓库审核范围</h3>
                                        <ul class="space-y-2 text-xs text-slate-500 leading-relaxed">
                                            <li>处理学生举报，核对版权、恶意代码和广告风险。</li>
                                            <li>通过举报后同步移除学习系统项目与 Gitea 仓库。</li>
                                            <li>查看当前公开项目，必要时直接移除违规内容。</li>
                                        </ul>
                                        <button @click="activePanel = 'repository'" class="mt-5 min-h-[40px] px-4 rounded-xl bg-[#1c2b38] text-white text-xs font-bold">进入仓库审核</button>
                                    </section>
                                </div>
                            </div>
                        </div>

                        <div v-else-if="activePanel === 'forum'" class="relative h-full min-h-0">
                            <teacher-forum-manager @show-toast="relayToast"></teacher-forum-manager>
                        </div>

                        <div v-else-if="activePanel === 'repository'" class="relative h-full min-h-0">
                            <teacher-repository-manager @show-toast="relayToast"></teacher-repository-manager>
                        </div>
                    </div>
                </main>
            </div>
        </section>
    `
};
