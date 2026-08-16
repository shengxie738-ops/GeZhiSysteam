import { ref, computed, onMounted } from 'vue';
import { repositoryApi } from '../api/repository.js';
import { formatTime } from '../utils/helpers.js';

export default {
    name: 'TeacherRepositoryManager',
    emits: ['show-toast'],
    setup(_, { emit }) {
        const loading = ref(true);
        const reports = ref([]);
        const projects = ref([]);
        const activeStatus = ref('pending');
        const auditNote = ref('');
        const showProjectsModal = ref(false);

        const loadData = async () => {
            loading.value = true;
            try {
                const [reportData, projectData] = await Promise.all([
                    repositoryApi.getReports(),
                    repositoryApi.getRepositories({ sort: 'recommended' })
                ]);
                reports.value = reportData;
                projects.value = projectData;
            } catch (err) {
                emit('show-toast', '仓库审核数据加载失败', 'error');
            } finally {
                loading.value = false;
            }
        };

        const filteredReports = computed(() => {
            if (activeStatus.value === 'all') return reports.value;
            return reports.value.filter((item) => item.status === activeStatus.value);
        });

        const stats = computed(() => ({
            pending: reports.value.filter((item) => item.status === 'pending').length,
            approved: reports.value.filter((item) => item.status === 'approved').length,
            rejected: reports.value.filter((item) => item.status === 'rejected').length
        }));

        const projectById = (projectId) => projects.value.find((item) => item.id === projectId);

        const auditReport = async (report, action) => {
            try {
                const result = await repositoryApi.auditReport(report.id, {
                    action,
                    teacherId: 'teacher',
                    note: auditNote.value || (action === 'approve_delete' ? '确认违规，已删除仓库' : '证据不足，驳回举报')
                });
                reports.value = reports.value.map((item) => item.id === report.id ? { ...item, ...result } : item);
                activeStatus.value = action === 'approve_delete' ? 'approved' : 'rejected';
                auditNote.value = '';
                if (action === 'approve_delete') {
                    projects.value = projects.value.filter((item) => item.id !== report.projectId);
                }
                emit('show-toast', action === 'approve_delete' ? '已通过举报并删除项目仓库' : '已驳回举报', 'success');
            } catch (err) {
                emit('show-toast', '审核操作失败', 'error');
            }
        };

        const removeProject = async (project) => {
            try {
                await repositoryApi.deleteRepository(project.id, { reason: '教师主动删除违规项目' });
                projects.value = projects.value.filter((item) => item.id !== project.id);
                emit('show-toast', '项目已从校园代码仓库移除', 'success');
            } catch (err) {
                emit('show-toast', '项目删除失败', 'error');
            }
        };

        onMounted(loadData);

        return {
            loading,
            reports,
            projects,
            activeStatus,
            auditNote,
            showProjectsModal,
            filteredReports,
            stats,
            projectById,
            auditReport,
            removeProject,
            loadData,
            formatTime
        };
    },
    template: `
        <section class="absolute inset-0 overflow-y-auto p-6 lg:p-8 select-none">
            <div class="max-w-7xl mx-auto flex flex-col gap-6">
                <header class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
                    <div>
                        <h2 class="text-2xl font-serif font-bold text-slate-900">代码仓库审核台</h2>
                        <p class="text-sm text-slate-500 mt-1">处理学生举报、删除违规项目，并保持学习系统数据库与 Gitea 仓库状态一致。</p>
                    </div>
                    <button @click="loadData" class="px-4 py-2 rounded-xl text-xs font-bold bg-white/70 border border-slate-200 text-slate-600 hover:bg-white flex items-center gap-1.5 w-fit">
                        <i class="ph ph-arrows-clockwise"></i> 同步数据
                    </button>
                </header>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <button @click="activeStatus = 'pending'" class="glass-panel-liquid p-5 text-left" :class="activeStatus === 'pending' && 'ring-2 ring-[#1c2b38]/10'">
                        <div class="text-2xl font-serif font-bold text-slate-900">{{ stats.pending }}</div>
                        <div class="text-xs font-bold text-amber-600 mt-1">待审核举报</div>
                    </button>
                    <button @click="activeStatus = 'approved'" class="glass-panel-liquid p-5 text-left" :class="activeStatus === 'approved' && 'ring-2 ring-[#1c2b38]/10'">
                        <div class="text-2xl font-serif font-bold text-slate-900">{{ stats.approved }}</div>
                        <div class="text-xs font-bold text-red-600 mt-1">已删除项目</div>
                    </button>
                    <button @click="activeStatus = 'rejected'" class="glass-panel-liquid p-5 text-left" :class="activeStatus === 'rejected' && 'ring-2 ring-[#1c2b38]/10'">
                        <div class="text-2xl font-serif font-bold text-slate-900">{{ stats.rejected }}</div>
                        <div class="text-xs font-bold text-emerald-600 mt-1">已驳回举报</div>
                    </button>
                </div>

                <div v-if="loading" class="glass-panel-liquid p-8 text-xs text-slate-500">正在同步仓库举报信息...</div>

                <div v-else class="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
                    <main class="flex flex-col gap-4">
                        <div class="flex items-center gap-2">
                            <button @click="activeStatus = 'all'" class="px-3 py-1.5 rounded-xl text-xs font-bold border transition-all" :class="activeStatus === 'all' ? 'bg-primary text-white border-primary' : 'bg-white/70 text-slate-500 border-slate-200'">全部</button>
                            <button @click="activeStatus = 'pending'" class="px-3 py-1.5 rounded-xl text-xs font-bold border transition-all" :class="activeStatus === 'pending' ? 'bg-primary text-white border-primary' : 'bg-white/70 text-slate-500 border-slate-200'">待审核</button>
                            <button @click="activeStatus = 'approved'" class="px-3 py-1.5 rounded-xl text-xs font-bold border transition-all" :class="activeStatus === 'approved' ? 'bg-primary text-white border-primary' : 'bg-white/70 text-slate-500 border-slate-200'">已删除</button>
                            <button @click="activeStatus = 'rejected'" class="px-3 py-1.5 rounded-xl text-xs font-bold border transition-all" :class="activeStatus === 'rejected' ? 'bg-primary text-white border-primary' : 'bg-white/70 text-slate-500 border-slate-200'">已驳回</button>
                        </div>

                        <div v-if="filteredReports.length === 0" class="glass-panel-liquid p-8 text-center text-xs text-slate-400">当前没有匹配的举报记录。</div>

                        <article v-for="report in filteredReports" :key="report.id" class="glass-panel-liquid p-5 flex flex-col gap-4">
                            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                                <div>
                                    <div class="flex items-center gap-2 mb-2">
                                        <span class="text-[9px] px-2 py-0.5 rounded-full font-bold border"
                                              :class="report.status === 'pending' ? 'bg-amber-50 text-amber-700 border-amber-100' : (report.status === 'approved' ? 'bg-red-50 text-red-700 border-red-100' : 'bg-emerald-50 text-emerald-700 border-emerald-100')">
                                            {{ report.status === 'pending' ? '待审核' : (report.status === 'approved' ? '已删除' : '已驳回') }}
                                        </span>
                                        <span class="text-[10px] text-slate-400 font-mono">{{ formatTime(report.createdAt) }}</span>
                                    </div>
                                    <h3 class="text-base font-bold text-slate-900">{{ report.projectTitle }}</h3>
                                    <p class="text-xs text-slate-500 mt-1">举报人：{{ report.reporter }} / 发布者：{{ report.projectAuthor }}</p>
                                </div>
                                <div class="text-right shrink-0">
                                    <div class="text-xs font-bold text-red-600">{{ report.reason }}</div>
                                    <div class="text-[10px] text-slate-400 mt-1">{{ report.id }}</div>
                                </div>
                            </div>

                            <p class="text-xs text-slate-600 leading-relaxed bg-white/50 border border-white/70 rounded-xl p-3">{{ report.description || '未填写详细说明' }}</p>

                            <div v-if="report.status === 'pending'" class="flex flex-col lg:flex-row gap-3 lg:items-center">
                                <input v-model="auditNote" class="liquid-glass-input flex-1 px-4 py-2.5 text-xs outline-none" placeholder="审核备注，可留空使用默认说明">
                                <div class="flex gap-2">
                                    <button @click="auditReport(report, 'reject')" class="px-4 py-2 rounded-xl text-xs font-bold bg-white border border-slate-200 text-slate-600 hover:bg-slate-50">驳回</button>
                                    <button @click="auditReport(report, 'approve_delete')" class="px-4 py-2 rounded-xl text-xs font-bold bg-red-600 text-white hover:bg-red-700 flex items-center gap-1.5">
                                        <i class="ph ph-trash"></i> 通过并删除仓库
                                    </button>
                                </div>
                            </div>

                            <div v-else class="text-xs text-slate-500 bg-slate-50/70 border border-slate-100 rounded-xl p-3">
                                审核人：{{ report.auditor || 'teacher' }} / 备注：{{ report.note || '无' }}
                            </div>
                        </article>
                    </main>

                    <aside class="flex flex-col gap-4">
                        <div class="glass-panel-liquid p-5 cursor-pointer hover:bg-white/60 transition-all group" @click="showProjectsModal = true">
                            <div class="flex items-center justify-between mb-3">
                                <h3 class="text-xs font-bold text-slate-700 flex items-center gap-1.5"><i class="ph ph-folder-open"></i> 当前公开项目</h3>
                                <i class="ph ph-arrow-square-out text-slate-400 group-hover:text-slate-700 transition-colors"></i>
                            </div>
                            <div class="flex items-center gap-3">
                                <div class="text-3xl font-serif font-bold text-slate-900">{{ projects.length }}</div>
                                <div class="text-[10px] text-slate-500 leading-tight">个公开项目<br/><span class="text-slate-400">点击查看全部并管理</span></div>
                            </div>
                            <div v-if="projects.length > 0" class="mt-3 flex flex-col gap-1.5">
                                <div v-for="project in projects.slice(0, 2)" :key="project.id" class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/40 border border-white/50">
                                    <i class="ph ph-folder text-slate-400 text-[10px]"></i>
                                    <span class="text-[10px] font-bold text-slate-700 truncate flex-1">{{ project.title }}</span>
                                    <span class="text-[9px] text-slate-400 shrink-0">{{ project.language }}</span>
                                </div>
                                <div v-if="projects.length > 2" class="text-[10px] text-slate-400 text-center pt-1">还有 {{ projects.length - 2 }} 个项目...</div>
                            </div>
                            <div v-else class="mt-3 text-[10px] text-slate-400 text-center py-2">暂无公开项目</div>
                        </div>
                        <div class="glass-panel-liquid p-5">
                            <h3 class="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-2"><i class="ph ph-shield-check"></i> 审核规则</h3>
                            <p class="text-xs text-slate-500 leading-relaxed">通过举报会先把学习系统项目状态标记为 removed，再调用后端 Gitea 删除接口。若 Gitea 暂未配置，本地演示会走稳定 mock 删除，不影响数据库状态同步。</p>
                        </div>
                    </aside>
                </div>
            </div>

        <!-- 公开项目列表弹窗 -->
        <transition name="fade">
            <div v-if="showProjectsModal"
                 class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4"
                 @click.self="showProjectsModal = false">
                <div class="bg-white/95 backdrop-blur-xl rounded-3xl shadow-float w-full max-w-2xl
                            overflow-hidden border border-white flex flex-col max-h-[85vh]">
                    <!-- 弹窗头部 -->
                    <div class="px-6 py-4 border-b border-white/20 flex justify-between items-center bg-white/40">
                        <h3 class="text-lg font-bold text-slate-800 flex items-center gap-2"
                            style="font-family:'Noto Serif SC',serif;">
                            <i class="ph ph-folder-open text-[#1c2b38]"></i> 当前公开项目
                            <span class="text-xs font-normal text-slate-400">（共 {{ projects.length }} 个）</span>
                        </h3>
                        <button @click="showProjectsModal = false"
                                class="text-slate-400 hover:text-slate-700 transition-colors">
                            <i class="ph ph-x text-xl"></i>
                        </button>
                    </div>

                    <!-- 弹窗内容 -->
                    <div class="overflow-y-auto flex-1 p-6">
                        <div v-if="projects.length === 0" class="text-center text-xs text-slate-400 py-12">
                            <i class="ph ph-package text-4xl block mb-3 text-slate-300"></i>
                            暂无公开项目
                        </div>

                        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div v-for="project in projects" :key="project.id"
                                 class="p-4 rounded-2xl bg-white/60 border border-white/70 hover:bg-white/90 hover:shadow-sm transition-all flex flex-col gap-2">
                                <div class="flex items-start justify-between gap-2">
                                    <div class="flex items-center gap-2 min-w-0">
                                        <i class="ph ph-folder text-slate-400 text-sm shrink-0"></i>
                                        <span class="text-sm font-bold text-slate-800 truncate">{{ project.title }}</span>
                                    </div>
                                </div>
                                <div class="flex items-center gap-2 text-[10px] text-slate-400">
                                    <span class="px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-600 font-mono">{{ project.language }}</span>
                                    <span>{{ project.author }}</span>
                                </div>
                                <button @click="removeProject(project)"
                                        class="mt-1 self-start text-[10px] font-bold text-red-600 hover:text-red-700 hover:underline flex items-center gap-1">
                                    <i class="ph ph-trash"></i> 直接移除
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- 弹窗底部 -->
                    <div class="px-6 py-3 border-t border-white/20 flex justify-end bg-white/30">
                        <button @click="showProjectsModal = false"
                                class="px-5 py-2 rounded-xl text-xs font-bold bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors">
                            关闭
                        </button>
                    </div>
                </div>
            </div>
        </transition>
        </section>
    `
};
