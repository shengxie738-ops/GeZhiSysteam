import { ref, computed, onMounted } from 'vue';
import { teamGitApi } from '../api/teamGit.js';

export default {
    name: 'TeacherProjectManager',
    template: `
        <div class="absolute inset-0 overflow-hidden tpm-root" style="background: #ffffff;">
            
            <!-- PORTAL HUB (门户页) -->
            <transition name="fade">
                <div v-if="activeModule === 'portal'" class="absolute inset-0 flex flex-col items-center justify-center p-8 z-50">
                    <div class="mb-12 text-center reveal-up" :class="{ 'revealed': mounted }">
                        <h1 class="text-4xl lg:text-5xl font-serif font-bold text-slate-900 mb-4 tracking-tight drop-shadow-sm">请选择教学场景</h1>
                        <p class="text-lg text-slate-500 font-medium">全局掌控大作业递交验收，或沉浸式跟踪编程团队协作。</p>
                    </div>

                    <div class="flex flex-col md:flex-row gap-8 w-full max-w-6xl mx-auto px-4">
                        
                        <!-- Card A: Assignment -->
                        <div @click="activeModule = 'assignment'" @keydown.enter.prevent="activeModule = 'assignment'" role="button" tabindex="0" class="flex-1 group cursor-pointer relative overflow-hidden rounded-[2.5rem] bg-white border border-slate-200/80 shadow-cinematic transition-all duration-500 hover:border-cyan-300/60 hover:shadow-lg active:scale-[0.98] reveal-up p-10 lg:p-14 outline-none focus:ring-4 focus:ring-cyan-200/70" :class="{ 'revealed': mounted }" style="transition-delay: 100ms">
                            <!-- Halo effect -->
                            <div class="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl group-hover:bg-cyan-500/20 transition-all duration-700 ease-out transform group-hover:scale-150 pointer-events-none"></div>
                            
                            <div class="relative z-10">
                                <div class="w-20 h-20 rounded-2xl bg-cyan-50 border border-cyan-100 flex items-center justify-center mb-8 shadow-sm group-hover:bg-cyan-100 transition-colors duration-500">
                                    <i class="ph ph-folder-open text-4xl text-cyan-600 group-hover:text-cyan-700"></i>
                                </div>
                                <h2 class="text-3xl font-bold font-serif text-slate-900 mb-4">大作业项目管理</h2>
                                <p class="text-slate-600 text-lg leading-relaxed max-w-sm">
                                    掌控班级大作业的阶段递交、流水线打分与最终 AI 联评验收。
                                </p>
                            </div>
                        </div>

                        <!-- Card B: Team Training -->
                        <div @click.stop="activeModule = 'training'; loadTrainingProjects()" @keydown.enter.prevent="activeModule = 'training'; loadTrainingProjects()" role="button" tabindex="0" class="flex-1 group cursor-pointer relative overflow-hidden rounded-[2.5rem] bg-white border border-slate-200/80 shadow-cinematic transition-all duration-500 hover:border-indigo-200 hover:shadow-lg active:scale-[0.98] reveal-up p-10 lg:p-14 outline-none focus:ring-4 focus:ring-indigo-200/70" :class="{ 'revealed': mounted }" style="transition-delay: 200ms">
                            <!-- Halo effect -->
                            <div class="absolute bottom-0 left-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-3xl group-hover:bg-indigo-500/15 transition-all duration-700 ease-out transform group-hover:scale-150 pointer-events-none"></div>
                            
                            <div class="relative z-10">
                                <div class="w-20 h-20 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mb-8 shadow-sm group-hover:bg-indigo-100 transition-colors duration-500">
                                    <i class="ph ph-users-three text-4xl text-indigo-600 group-hover:text-indigo-700"></i>
                                </div>
                                <h2 class="text-3xl font-bold font-serif text-slate-900 mb-4">编程团队实训管理</h2>
                                <p class="text-slate-600 text-lg leading-relaxed max-w-sm">
                                    沉浸式追踪学生团队的代码提交热力图、多分支协作与健康度预警。
                                </p>
                            </div>
                        </div>

                    </div>
                </div>
            </transition>

            <!-- SUB-MODULE: 大作业项目管理 (Assignment) -->
            <transition name="fade">
                <div v-if="activeModule === 'assignment'" class="absolute inset-0 overflow-y-auto dark-scroll p-8 lg:p-12 z-40 bg-transparent">
                    
                    <!-- Header section -->
                    <div class="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6 reveal-up" :class="{ 'revealed': mounted }">
                        <div>
                            <button @click="activeModule = 'portal'" class="mb-4 text-sm font-bold text-slate-500 hover:text-slate-800 transition-colors flex items-center gap-1.5 w-fit">
                                <i class="ph ph-arrow-left"></i> 返回入口
                            </button>
                            <h1 class="text-4xl font-serif font-bold text-slate-900 mb-2 tracking-tight">大作业项目管理</h1>
                            <p class="text-slate-500 font-medium">全局掌控大作业递交与验收生命周期。</p>
                        </div>
                        <div class="flex items-center gap-4">
                            <button @click="notifyFeature('大作业报表导出')" class="px-5 py-2.5 bg-white border border-slate-200 text-slate-700 font-bold rounded-xl shadow-sm hover:shadow hover:border-slate-300 transition-all active:scale-95 flex items-center gap-2">
                                <i class="ph ph-export"></i> 导出报表
                            </button>
                            <button @click="notifyFeature('新建大作业向导')" class="px-5 py-2.5 bg-slate-900 text-white font-bold rounded-xl shadow-md hover:bg-slate-800 transition-all active:scale-95 flex items-center gap-2">
                                <i class="ph ph-plus-circle"></i> 新建大作业
                            </button>
                        </div>
                    </div>

            <!-- Class Stats Overview -->
            <div class="mb-8 grid grid-cols-2 lg:grid-cols-4 gap-4 reveal-up" :class="{ 'revealed': mounted }">
                <div class="bg-white border border-slate-200/70 rounded-2xl px-5 py-4 flex items-center gap-4 shadow-sm">
                    <div class="w-11 h-11 rounded-xl bg-slate-900/5 border border-slate-200/60 flex items-center justify-center shrink-0">
                        <i class="ph ph-users-three text-xl text-slate-700"></i>
                    </div>
                    <div>
                        <p class="text-[10px] font-bold text-slate-400 tracking-wider">在管团队</p>
                        <p class="text-2xl font-bold font-serif text-slate-900 leading-tight">{{ teamStats.total }} <span class="text-xs font-bold text-slate-400">组</span></p>
                    </div>
                </div>
                <div class="bg-white border border-slate-200/70 rounded-2xl px-5 py-4 flex items-center gap-4 shadow-sm">
                    <div class="w-11 h-11 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center shrink-0">
                        <i class="ph ph-gauge text-xl text-emerald-600"></i>
                    </div>
                    <div>
                        <p class="text-[10px] font-bold text-slate-400 tracking-wider">平均健康分</p>
                        <p class="text-2xl font-bold font-serif text-slate-900 leading-tight">{{ teamStats.avg }} <span class="text-xs font-bold text-slate-400">/100</span></p>
                    </div>
                </div>
                <div class="bg-white border border-slate-200/70 rounded-2xl px-5 py-4 flex items-center gap-4 shadow-sm">
                    <div class="w-11 h-11 rounded-xl bg-red-50 border border-red-100 flex items-center justify-center shrink-0">
                        <i class="ph ph-warning-circle text-xl text-red-500"></i>
                    </div>
                    <div>
                        <p class="text-[10px] font-bold text-slate-400 tracking-wider">高风险团队</p>
                        <p class="text-2xl font-bold font-serif leading-tight" :class="teamStats.risk > 0 ? 'text-red-600' : 'text-slate-900'">{{ teamStats.risk }} <span class="text-xs font-bold text-slate-400">组</span></p>
                    </div>
                </div>
                <div class="bg-white border border-slate-200/70 rounded-2xl px-5 py-4 flex items-center gap-4 shadow-sm">
                    <div class="w-11 h-11 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center shrink-0">
                        <i class="ph ph-git-commit text-xl text-indigo-500"></i>
                    </div>
                    <div>
                        <p class="text-[10px] font-bold text-slate-400 tracking-wider">累计提交</p>
                        <p class="text-2xl font-bold font-serif text-slate-900 leading-tight">{{ teamStats.commits }} <span class="text-xs font-bold text-slate-400">次</span></p>
                    </div>
                </div>
            </div>

            <!-- Pipeline Tabs (流水线全局导航) -->
            <div class="mb-8 p-1.5 bg-white rounded-2xl border border-slate-200/80 flex gap-2 shadow-sm reveal-up" :class="{ 'revealed': mounted }" style="transition-delay: 100ms">
                <button 
                    v-for="(stage, idx) in pipelineStages" :key="stage.id"
                    @click="activeStage = stage.id"
                    class="flex-1 py-3 px-4 rounded-xl font-bold text-sm transition-all duration-300 relative overflow-hidden"
                    :class="activeStage === stage.id ? 'bg-slate-900 text-white shadow-md' : 'text-slate-500 hover:bg-slate-100/50 hover:text-slate-800'"
                >
                    <div class="flex items-center justify-center gap-2 relative z-10">
                        <span class="w-5 h-5 rounded-full flex items-center justify-center text-[10px]"
                            :class="activeStage === stage.id ? 'bg-white/20' : 'bg-slate-200 text-slate-600'">
                            {{ idx + 1 }}
                        </span>
                        {{ stage.name }}
                    </div>
                </button>
            </div>

            <!-- Bento Grid Board -->
            <div class="bento-grid reveal-up" :class="{ 'revealed': mounted }" style="transition-delay: 200ms">
                
                <div v-for="(team, index) in filteredTeams" :key="team.id"
                    @click="openTeamDetail(team)"
                    class="glass-light p-6 cursor-pointer group flex flex-col justify-between"
                    :class="[
                        team.isHot ? 'col-span-12 md:col-span-8 lg:col-span-8 min-h-[320px]' : 'col-span-12 md:col-span-6 lg:col-span-4 min-h-[280px]',
                        team.health === 'danger' ? 'border-red-200/60 hover:border-red-300' : ''
                    ]"
                >
                    <!-- Top section: Title & Gauge -->
                    <div class="flex justify-between items-start mb-4">
                        <div class="pr-4 min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                                <h3 class="text-xl font-bold text-slate-800 truncate">{{ team.name }}</h3>
                                <span v-if="team.isHot" class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700 border border-amber-200 shrink-0">高活跃</span>
                            </div>
                            <p class="text-sm font-bold text-slate-500 font-serif leading-tight line-clamp-2">{{ team.projectTopic }}</p>
                        </div>
                        
                        <!-- Circular Gauge Dashboard -->
                        <div class="relative w-[76px] h-[76px] flex-shrink-0 drop-shadow-sm" title="完成度 / 综合健康分">
                            <svg viewBox="0 0 36 36" class="w-full h-full transform -rotate-90">
                                <!-- Background Track -->
                                <path class="text-slate-200/80 drop-shadow-sm" stroke-width="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <!-- Progress Track -->
                                <path :class="{
                                    'text-emerald-400': team.health === 'good',
                                    'text-amber-400': team.health === 'warning',
                                    'text-red-400': team.health === 'danger'
                                }" stroke-width="3" :stroke-dasharray="(mounted ? team.score : 0) + ', 100'" stroke-linecap="round" stroke="currentColor" fill="none" class="transition-all duration-1000 ease-out" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                            </svg>
                            <div class="absolute inset-0 flex flex-col items-center justify-center">
                                <span class="text-lg font-bold font-serif leading-none" :class="{
                                    'text-emerald-700': team.health === 'good',
                                    'text-amber-700': team.health === 'warning',
                                    'text-red-700': team.health === 'danger'
                                }">{{ team.score }}<span class="text-[10px]">%</span></span>
                                <span class="text-[8px] font-bold text-slate-400 tracking-wider mt-0.5">健康分</span>
                            </div>
                        </div>
                    </div>

                    <!-- Progress / Activity Visualization based on Bento Size -->
                    <div class="flex-1 flex flex-col justify-end">
                        <div v-if="team.isHot" class="mb-4 w-full h-28 bg-gradient-to-b from-slate-50 to-white rounded-xl border border-slate-200/70 relative overflow-hidden flex items-end px-3 pb-2.5 gap-1.5 shadow-inner">
                            <!-- Mock Mini Chart -->
                            <div v-for="(val, i) in team.activityData" :key="i"
                                class="flex-1 bg-gradient-to-t from-indigo-500/80 to-indigo-400 rounded-t-[4px] transition-all duration-700 ease-out group-hover:from-indigo-500 group-hover:to-indigo-300"
                                :style="{ height: mounted ? val + '%' : '0%', opacity: 0.35 + (val/100)*0.65 }"></div>
                            <span class="absolute top-2 left-3 text-[10px] font-bold text-slate-400 tracking-wider">近期提交活跃度</span>
                        </div>

                        <!-- Milestone Progress -->
                        <div class="mb-4">
                            <div class="flex justify-between text-[11px] font-bold text-slate-500 mb-1.5">
                                <span>里程碑进度</span>
                                <span>{{ milestoneProgress(team).done }} / {{ milestoneProgress(team).total }}</span>
                            </div>
                            <div class="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                <div class="h-full rounded-full transition-all duration-1000 ease-out"
                                    :class="{
                                        'bg-gradient-to-r from-emerald-400 to-emerald-500': team.health === 'good',
                                        'bg-gradient-to-r from-amber-400 to-amber-500': team.health === 'warning',
                                        'bg-gradient-to-r from-red-400 to-red-500': team.health === 'danger'
                                    }"
                                    :style="{ width: (mounted ? milestoneProgress(team).pct : 0) + '%' }"></div>
                            </div>
                        </div>
                        
                        <!-- Members (Full Chips) & Stats -->
                        <div class="flex flex-col gap-3 mt-auto pt-3 border-t border-slate-200/50">
                            <!-- Member Chips -->
                            <div class="flex flex-wrap gap-2">
                                <div v-for="(member, mIdx) in team.members" :key="mIdx"
                                    class="flex items-center px-2.5 py-1 rounded-md bg-white border border-slate-200/60 shadow-sm transition-transform hover:-translate-y-0.5"
                                >
                                    <span class="text-xs font-bold text-slate-700">{{ member }}</span>
                                </div>
                            </div>
                            
                            <!-- Stats Footer -->
                            <div class="flex items-center justify-between">
                                <div class="text-xs font-bold text-slate-500 flex items-center gap-1 bg-slate-100/50 px-2 py-1 rounded-lg">
                                    <i class="ph ph-git-commit text-indigo-400"></i> {{ team.commits }} 次提交
                                </div>
                                <div class="text-[10px] font-bold px-2 py-1 rounded-lg"
                                    :class="{
                                        'bg-emerald-50 text-emerald-600 border border-emerald-100': team.health === 'good',
                                        'bg-amber-50 text-amber-600 border border-amber-100': team.health === 'warning',
                                        'bg-red-50 text-red-600 border border-red-100': team.health === 'danger'
                                    }"
                                >
                                    {{ team.health === 'good' ? '状态健康' : (team.health === 'warning' ? '进度受阻' : '高风险预警') }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Full-Height Drawer overlay -->
            <transition name="fade">
                <div v-if="selectedTeam" class="fixed inset-0 z-[100] bg-slate-900/20 backdrop-blur-sm" @click="closeTeamDetail"></div>
            </transition>
            
            <!-- Drawer Panel -->
            <transition name="drawer-slide">
                <div v-if="selectedTeam" class="fixed top-4 bottom-4 right-4 w-full max-w-3xl glass-panel-liquid shadow-cinematic z-[110] flex flex-col overflow-hidden border border-white/60">
                    
                    <!-- Drawer Header -->
                    <div class="px-8 py-6 border-b border-slate-200/60 bg-white/80 flex justify-between items-center relative z-10">
                        <div>
                            <div class="flex items-center gap-3 mb-1">
                                <h2 class="text-2xl font-bold font-serif text-slate-900">{{ selectedTeam.name }}</h2>
                                <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200">
                                    组号: {{ selectedTeam.id }}
                                </span>
                            </div>
                            <p class="text-sm font-medium text-slate-500">{{ selectedTeam.projectTopic }}</p>
                        </div>
                        
                        <button @click="closeTeamDetail" class="w-10 h-10 rounded-full bg-white border border-slate-200 text-slate-500 hover:text-slate-800 hover:shadow-md transition-all flex items-center justify-center">
                            <i class="ph ph-x text-lg"></i>
                        </button>
                    </div>

                    <!-- Drawer Tabs -->
                    <div class="px-8 pt-4 bg-white/70 border-b border-slate-200/60 flex gap-6 relative z-10">
                        <button v-for="tab in drawerTabs" :key="tab.id"
                            @click="activeDrawerTab = tab.id"
                            class="pb-3 text-sm font-bold transition-all relative"
                            :class="activeDrawerTab === tab.id ? 'text-slate-900' : 'text-slate-400 hover:text-slate-600'"
                        >
                            {{ tab.name }}
                            <div v-if="activeDrawerTab === tab.id" class="absolute bottom-0 left-0 w-full h-0.5 bg-slate-900 rounded-t-full"></div>
                        </button>
                    </div>

                    <!-- Drawer Content Area -->
                    <div class="flex-1 overflow-y-auto dark-scroll p-8 relative z-10">
                        
                        <!-- Tab A: 里程碑 (Milestones) -->
                        <div v-if="activeDrawerTab === 'milestone'" class="space-y-6">
                            <div v-for="(ms, index) in selectedTeam.milestones" :key="index"
                                class="bg-white border border-slate-200/70 rounded-2xl p-6 transition-all hover:shadow-md"
                            >
                                <div class="flex justify-between items-start mb-4">
                                    <div class="flex items-center gap-3">
                                        <div class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm"
                                            :class="ms.status === 'done' ? 'bg-emerald-100 text-emerald-600' : (ms.status === 'doing' ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400')"
                                        >
                                            <i v-if="ms.status === 'done'" class="ph ph-check"></i>
                                            <span v-else>{{ index + 1 }}</span>
                                        </div>
                                        <div>
                                            <h4 class="font-bold text-slate-800">{{ ms.name }}</h4>
                                            <p class="text-xs font-bold text-slate-500 mt-0.5">{{ ms.date }}</p>
                                        </div>
                                    </div>
                                    <div v-if="ms.status === 'done'" class="text-right">
                                        <span class="text-2xl font-bold font-serif text-slate-900">{{ ms.score }}</span><span class="text-sm font-bold text-slate-400">/100</span>
                                    </div>
                                    <div v-else-if="ms.status === 'doing'" class="flex gap-2">
                                        <input v-model.number="milestoneScoreDraft[selectedTeam.id + '-' + index]" type="number" min="0" max="100" placeholder="打分" class="w-20 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-700 outline-none focus:border-indigo-400">
                                        <button @click="confirmMilestoneScore(ms, index)" class="px-3 py-1.5 bg-slate-900 text-white rounded-lg text-sm font-bold hover:bg-slate-800">确认</button>
                                    </div>
                                </div>
                                <p class="text-sm text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/60">{{ ms.desc }}</p>
                            </div>
                        </div>

                        <!-- Tab B: 协作监控 (Collaboration) -->
                        <div v-if="activeDrawerTab === 'collaboration'" class="space-y-6">
                            
                            <div class="bg-white border border-slate-200/70 rounded-2xl p-6">
                                <h4 class="font-bold text-slate-800 mb-4 flex items-center gap-2">
                                    <i class="ph ph-squares-four text-indigo-500"></i> 代码提交热力图
                                </h4>
                                <!-- Mock GitHub style heat map -->
                                <div class="flex gap-1.5 overflow-x-auto pb-2">
                                    <div v-for="col in 24" :key="col" class="flex flex-col gap-1.5">
                                        <div v-for="row in 7" :key="row" 
                                            class="w-[18px] h-[18px] rounded-[4px] transition-transform hover:scale-125"
                                            :style="{ backgroundColor: getHeatColor(col, row) }"
                                            title="当日提交次数"
                                        ></div>
                                    </div>
                                </div>
                                <div class="flex items-center justify-between mt-3 pt-2 border-t border-slate-100">
                                    <span class="text-[10px] font-bold text-slate-400 tracking-wider">近 24 周代码提交热力</span>
                                    <div class="flex items-center gap-1">
                                        <span class="text-[10px] text-slate-400 mr-0.5">少</span>
                                        <span class="w-2.5 h-2.5 rounded-[3px]" style="background-color: #f1f5f9;"></span>
                                        <span class="w-2.5 h-2.5 rounded-[3px]" style="background-color: #c7d2fe;"></span>
                                        <span class="w-2.5 h-2.5 rounded-[3px]" style="background-color: #818cf8;"></span>
                                        <span class="w-2.5 h-2.5 rounded-[3px]" style="background-color: #4f46e5;"></span>
                                        <span class="w-2.5 h-2.5 rounded-[3px]" style="background-color: #312e81;"></span>
                                        <span class="text-[10px] text-slate-400 ml-0.5">多</span>
                                    </div>
                                </div>
                            </div>

                            <div class="bg-white border border-slate-200/70 rounded-2xl p-6">
                                <h4 class="font-bold text-slate-800 mb-4 flex items-center gap-2">
                                    <i class="ph ph-users-three text-blue-500"></i> 成员贡献度
                                </h4>
                                <div class="space-y-4">
                                    <div v-for="(member, mIdx) in selectedTeam.members" :key="mIdx" class="flex items-center gap-4">
                                        <div class="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-600 shrink-0">
                                            {{ member.substring(0, 1) }}
                                        </div>
                                        <div class="flex-1">
                                            <div class="flex justify-between text-xs font-bold mb-1.5">
                                                <span class="text-slate-700">{{ member }}</span>
                                                <span class="text-slate-500">{{ memberShare(mIdx, selectedTeam.members.length) }}%</span>
                                            </div>
                                            <div class="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                                <div class="h-full bg-gradient-to-r from-indigo-400 to-indigo-500 rounded-full transition-all duration-700 ease-out" :style="{ width: memberShare(mIdx, selectedTeam.members.length) + '%' }"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                        </div>

                        <!-- Tab C: 成果验收 (Deliverables) -->
                        <div v-if="activeDrawerTab === 'deliverables'" class="space-y-6">
                            
                            <div class="bg-indigo-50/50 border border-indigo-100 rounded-2xl p-6 relative overflow-hidden">
                                <div class="absolute -right-4 -top-4 text-indigo-500/10 text-9xl"><i class="ph ph-robot"></i></div>
                                <h4 class="font-bold text-indigo-900 mb-2 relative z-10">AI 智能体初步审阅报告</h4>
                                <p class="text-sm text-indigo-700/80 mb-4 relative z-10 leading-relaxed">
                                    基于提交的最终代码与文档，架构完整性得分为 85/100，代码规范度 A-。未发现明显的安全漏洞，但在大并发场景下的状态管理可能存在性能瓶颈。
                                </p>
                                <button @click="notifyFeature('完整 AI 审阅报告')" class="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold shadow-md hover:bg-indigo-700 transition-all relative z-10">
                                    查看完整 AI 报告
                                </button>
                            </div>

                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div class="bg-white border border-slate-200/70 rounded-2xl p-5 hover:bg-slate-50 transition-all cursor-pointer group flex items-center gap-4">
                                    <div class="w-12 h-12 rounded-xl bg-red-50 text-red-500 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                                        <i class="ph ph-file-pdf"></i>
                                    </div>
                                    <div>
                                        <h5 class="font-bold text-slate-800 text-sm">最终设计文档.pdf</h5>
                                        <p class="text-xs text-slate-400 mt-0.5">2.4 MB · 昨天 18:30</p>
                                    </div>
                                </div>
                                
                                <div class="bg-white border border-slate-200/70 rounded-2xl p-5 hover:bg-slate-50 transition-all cursor-pointer group flex items-center gap-4">
                                    <div class="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-500 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                                        <i class="ph ph-file-zip"></i>
                                    </div>
                                    <div>
                                        <h5 class="font-bold text-slate-800 text-sm">Release_v1.0.zip</h5>
                                        <p class="text-xs text-slate-400 mt-0.5">15 MB · 昨天 19:15</p>
                                    </div>
                                </div>
                                
                                <div class="bg-white border border-slate-200/70 rounded-2xl p-5 hover:bg-slate-50 transition-all cursor-pointer group flex items-center gap-4">
                                    <div class="w-12 h-12 rounded-xl bg-purple-50 text-purple-500 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                                        <i class="ph ph-video-camera"></i>
                                    </div>
                                    <div>
                                        <h5 class="font-bold text-slate-800 text-sm">项目演示视频.mp4</h5>
                                        <p class="text-xs text-slate-400 mt-0.5">45 MB · 昨天 20:00</p>
                                    </div>
                                </div>
                            </div>
                            
                        </div>

                    </div>
                    
                </div>
            </transition>
                </div>
            </transition>
            
            <!-- SUB-MODULE: 编程团队实训 (Training) -->
            <transition name="fade">
                <div v-if="activeModule === 'training'" class="absolute inset-0 overflow-y-auto dark-scroll p-8 lg:p-12 z-50 bg-transparent">
                    
                    <!-- Header section -->
                    <div class="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6 reveal-up" :class="{ 'revealed': mounted }">
                        <div>
                            <button @click="activeModule = 'portal'" class="mb-4 text-sm font-bold text-slate-500 hover:text-slate-800 transition-colors flex items-center gap-1.5 w-fit">
                                <i class="ph ph-arrow-left"></i> 返回入口
                            </button>
                            <h1 class="text-4xl font-serif font-bold text-slate-900 mb-2 tracking-tight">编程团队实训管理</h1>
                            <p class="text-slate-500 font-medium">管理员统一管理团队、任务、Git 进度、PR 审核与贡献评价。</p>
                        </div>
                        <div class="flex items-center gap-4">
                            <button @click="loadTrainingProjects" class="px-5 py-2.5 bg-white border border-slate-200 text-slate-700 font-bold rounded-xl shadow-sm hover:bg-white/90 transition-all active:scale-95 flex items-center gap-2">
                                <i class="ph ph-arrows-clockwise" :class="trainingLoading ? 'animate-spin' : ''"></i> 同步团队
                            </button>
                            <button @click="createTeacherTrainingProject" class="px-5 py-2.5 bg-slate-900 text-white font-bold rounded-xl shadow-md hover:bg-slate-800 transition-all active:scale-95 flex items-center gap-2">
                                <i class="ph ph-users"></i> 分配实训团队
                            </button>
                        </div>
                    </div>

                    <div v-if="trainingLoading" class="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-6 reveal-up" :class="{ 'revealed': mounted }" style="transition-delay: 100ms">
                        <div v-for="i in 2" :key="i" class="glass-panel-liquid p-6 animate-pulse min-h-[320px]">
                            <div class="h-5 w-36 bg-slate-200 rounded mb-5"></div>
                            <div class="space-y-3">
                                <div class="h-20 bg-slate-100 rounded-2xl"></div>
                                <div class="h-20 bg-slate-100 rounded-2xl"></div>
                                <div class="h-20 bg-slate-100 rounded-2xl"></div>
                            </div>
                        </div>
                    </div>

                    <div v-else class="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-6 reveal-up" :class="{ 'revealed': mounted }" style="transition-delay: 100ms">
                        <aside class="glass-panel-liquid p-5 flex flex-col gap-4 min-h-[560px]">
                            <div class="flex items-center justify-between gap-3">
                                <div>
                                    <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Training teams</p>
                                    <h3 class="text-lg font-serif font-bold text-slate-900">实训团队</h3>
                                </div>
                                <span class="text-xs font-bold text-slate-500 bg-white/80 border border-slate-200/70 rounded-xl px-2 py-1">{{ trainingProjects.length }} 组</span>
                            </div>
                            <div v-if="trainingProjects.length === 0" class="rounded-2xl bg-white/70 border border-slate-200/70 p-6 text-center text-xs text-slate-500">暂无团队数据，点击“分配实训团队”创建演示团队。</div>
                            <button v-for="project in trainingProjects" :key="project.id" @click="selectTrainingProject(project)" class="text-left rounded-2xl border p-4 transition-all duration-300"
                                :class="selectedTrainingProject && selectedTrainingProject.id === project.id
                                    ? 'bg-[#1c2b38]/85 backdrop-blur-sm text-white border-white/10 shadow-xl ring-1 ring-white/5'
                                    : 'bg-white/60 border-white hover:bg-white hover:shadow-md'">
                                <div class="flex items-start justify-between gap-3">
                                    <div class="min-w-0">
                                        <h4 class="text-sm font-bold truncate">{{ project.project.teamName }}</h4>
                                        <p class="text-[11px] mt-1 line-clamp-2" :class="selectedTrainingProject && selectedTrainingProject.id === project.id ? 'text-white/55' : 'text-slate-500'">{{ project.project.title }}</p>
                                    </div>
                                    <span class="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full"
                                        :class="selectedTrainingProject && selectedTrainingProject.id === project.id
                                            ? (project.teamSummary.unsubmittedMembers > 0 ? 'bg-amber-400/20 text-amber-200 ring-1 ring-amber-400/30' : 'bg-emerald-400/20 text-emerald-200 ring-1 ring-emerald-400/30')
                                            : (project.teamSummary.unsubmittedMembers > 0 ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700')">
                                        {{ project.teamSummary.averageProgress }}%
                                    </span>
                                </div>
                                <div class="mt-3 grid grid-cols-3 gap-2 text-center text-[10px]">
                                    <div><strong>{{ project.teamSummary.totalMembers }}</strong><br><span :class="selectedTrainingProject && selectedTrainingProject.id === project.id ? 'text-white/45' : 'text-slate-400'">成员</span></div>
                                    <div><strong>{{ project.teamSummary.openPullRequests }}</strong><br><span :class="selectedTrainingProject && selectedTrainingProject.id === project.id ? 'text-white/45' : 'text-slate-400'">PR</span></div>
                                    <div><strong>{{ project.teamSummary.pushedMembers }}</strong><br><span :class="selectedTrainingProject && selectedTrainingProject.id === project.id ? 'text-white/45' : 'text-slate-400'">Push</span></div>
                                </div>
                            </button>
                        </aside>

                        <main v-if="selectedTrainingProject" class="flex flex-col gap-6 min-w-0">
                            <section class="glass-panel-liquid p-6">
                                <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-5">
                                    <div class="min-w-0">
                                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Admin overview</p>
                                        <h2 class="text-2xl font-serif font-bold text-slate-900 mt-1">{{ selectedTrainingProject.project.teamName }} · {{ selectedTrainingProject.project.title }}</h2>
                                        <p class="text-sm text-slate-500 leading-relaxed mt-2 max-w-[72ch]">{{ selectedTrainingProject.project.description }}</p>
                                        <p v-if="selectedTrainingProject.repository?.lastSyncedAt" class="text-[11px] text-slate-400 mt-2">上次 Gitea 同步：{{ selectedTrainingProject.repository.lastSyncedAt }}</p>
                                        <p v-if="selectedTrainingProject.repository?.syncError" class="text-[11px] text-rose-600 mt-1">同步异常：{{ selectedTrainingProject.repository.syncError }}</p>
                                    </div>
                                    <button @click="openTeacherRepositoryHome(selectedTrainingProject)" class="shrink-0 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 flex items-center gap-1.5">
                                        <i class="ph ph-book-open-text"></i> 仓库主页
                                    </button>
                                </div>
                                <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mt-6">
                                    <div class="bg-white/80 border border-slate-200/70 rounded-2xl p-4"><p class="text-[10px] text-slate-400 font-bold">成员数</p><p class="text-xl font-bold text-slate-900">{{ selectedTrainingProject.teamSummary.totalMembers }}</p></div>
                                    <div class="bg-white/80 border border-slate-200/70 rounded-2xl p-4"><p class="text-[10px] text-slate-400 font-bold">已完成</p><p class="text-xl font-bold text-emerald-700">{{ selectedTrainingProject.teamSummary.completedMembers }}</p></div>
                                    <div class="bg-white/80 border border-slate-200/70 rounded-2xl p-4"><p class="text-[10px] text-slate-400 font-bold">未提交</p><p class="text-xl font-bold text-amber-700">{{ selectedTrainingProject.teamSummary.unsubmittedMembers }}</p></div>
                                    <div class="bg-white/80 border border-slate-200/70 rounded-2xl p-4"><p class="text-[10px] text-slate-400 font-bold">待审 PR</p><p class="text-xl font-bold text-blue-700">{{ selectedTrainingProject.teamSummary.openPullRequests }}</p></div>
                                    <div class="bg-white/80 border border-slate-200/70 rounded-2xl p-4"><p class="text-[10px] text-slate-400 font-bold">平均进度</p><p class="text-xl font-bold text-slate-900">{{ selectedTrainingProject.teamSummary.averageProgress }}%</p></div>
                                </div>
                            </section>

                            <section class="grid grid-cols-1 2xl:grid-cols-[minmax(0,1fr)_380px] gap-6">
                                <div class="glass-panel-liquid p-6 min-w-0">
                                    <div class="flex items-center justify-between gap-3 mb-4">
                                        <div>
                                            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Members and tasks</p>
                                            <h3 class="text-lg font-serif font-bold text-slate-900">成员 Git 协作进度</h3>
                                        </div>
                                        <button @click="sendTeacherReminder" class="px-3 py-2 rounded-xl bg-amber-500 text-white text-xs font-bold hover:bg-amber-600">提醒未提交成员</button>
                                    </div>
                                    <div class="overflow-x-auto">
                                        <table class="w-full min-w-[820px] text-left text-xs">
                                            <thead class="text-[10px] text-slate-400 uppercase">
                                                <tr class="border-b border-slate-100">
                                                    <th class="py-2 pr-3">成员</th>
                                                    <th class="py-2 pr-3">任务</th>
                                                    <th class="py-2 pr-3">分支</th>
                                                    <th class="py-2 pr-3">Commit</th>
                                                    <th class="py-2 pr-3">PR</th>
                                                    <th class="py-2 pr-3">进度</th>
                                                    <th class="py-2 pr-3">操作</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr v-for="member in filteredMemberProgress" :key="member.id" class="border-b border-slate-100 last:border-0">
                                                    <td class="py-3 pr-3 font-bold text-slate-800 whitespace-nowrap">{{ member.name }}</td>
                                                    <td class="py-3 pr-3 text-slate-600 max-w-[240px] truncate">{{ member.task }}</td>
                                                    <td class="py-3 pr-3 font-mono text-[11px] text-slate-500">{{ member.branch }}</td>
                                                    <td class="py-3 pr-3 text-slate-700">{{ member.commitCount }} 次</td>
                                                    <td class="py-3 pr-3 text-slate-700">{{ member.statusLabel }}</td>
                                                    <td class="py-3 pr-3 font-bold text-slate-900">{{ member.progress }}%</td>
                                                    <td class="py-3 pr-3">
                                                        <button @click="quickAssignTeacherTask(member)" class="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-[10px] font-bold text-slate-600 hover:bg-slate-50">分配任务</button>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                <aside class="glass-panel-liquid p-6">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Pull request audit</p>
                                    <h3 class="text-lg font-serif font-bold text-slate-900 mt-1 mb-4">审核 Pull Request</h3>
                                    <textarea v-model="teacherReviewComment" rows="3" class="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs outline-none focus:border-slate-900 resize-none mb-3" placeholder="教师审核意见"></textarea>
                                    <div v-if="selectedTrainingProject.pullRequests.length === 0" class="rounded-2xl bg-white/70 border border-slate-200/70 p-5 text-center text-xs text-slate-500">暂无 PR。</div>
                                    <div v-else class="flex flex-col gap-3">
                                        <article v-for="pr in selectedTrainingProject.pullRequests" :key="pr.id" class="bg-white/80 border border-slate-200/70 rounded-2xl p-4">
                                            <div class="flex items-start justify-between gap-3">
                                                <div class="min-w-0">
                                                    <h4 class="text-sm font-bold text-slate-900 truncate">#{{ pr.number }} {{ pr.title }}</h4>
                                                    <p class="text-[11px] text-slate-500 mt-1 truncate">{{ pr.creator }} · {{ pr.sourceBranch }} -> {{ pr.targetBranch }}</p>
                                                </div>
                                                <span class="text-[10px] px-2 py-1 rounded-full font-bold border"
                                                    :class="pr.status === 'merged' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : pr.leaderReviewStatus === 'recommended' ? 'bg-teal-50 text-teal-700 border-teal-100' : 'bg-blue-50 text-blue-700 border-blue-100'">
                                                    {{ pr.statusLabel }}
                                                </span>
                                            </div>
                                            <p v-if="pr.reviewComment" class="mt-2 text-[11px] text-slate-500 bg-slate-50 border border-slate-100 rounded-xl p-2">队长意见：{{ pr.reviewComment }}</p>
                                            <div v-if="pr.status === 'open'" class="mt-3 flex flex-wrap gap-2">
                                                <button @click="teacherAuditPr(pr, 'teacher_reject')" class="px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50">要求修改</button>
                                                <button @click="teacherAuditPr(pr, 'teacher_approve')" class="px-3 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800">审核并合并</button>
                                            </div>
                                        </article>
                                    </div>
                                </aside>
                            </section>

                            <section class="glass-panel-liquid p-6">
                                <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-5">
                                    <div>
                                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Contribution review</p>
                                        <h3 class="text-lg font-serif font-bold text-slate-900 mt-1">评价团队贡献</h3>
                                    </div>
                                    <button @click="saveTeacherContribution" class="px-4 py-2.5 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800">保存贡献评价</button>
                                </div>
                                <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-3">
                                    <div v-for="member in filteredMemberProgress" :key="member.id" class="bg-white/80 border border-slate-200/70 rounded-2xl p-4">
                                        <h4 class="text-sm font-bold text-slate-900">{{ member.name }}</h4>
                                        <p class="text-[11px] text-slate-500 line-clamp-2 mt-1">{{ member.task }}</p>
                                        <label class="block mt-3 text-[10px] font-bold text-slate-500">得分</label>
                                        <input v-model.number="contributionDraft[member.name].score" type="number" min="0" max="100" class="mt-1 w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs outline-none focus:border-slate-900">
                                        <label class="block mt-2 text-[10px] font-bold text-slate-500">贡献度 %</label>
                                        <input v-model.number="contributionDraft[member.name].contribution" type="number" min="0" max="100" class="mt-1 w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs outline-none focus:border-slate-900">
                                    </div>
                                </div>
                            </section>
                        </main>

                        <main v-else class="glass-panel-liquid p-10 flex items-center justify-center min-h-[560px]">
                            <div class="text-center max-w-md">
                                <i class="ph ph-code text-5xl text-slate-300 mb-4 inline-block"></i>
                                <h3 class="text-xl font-bold text-slate-700">请选择左侧团队</h3>
                                <p class="text-slate-500 mt-2">选择团队后可管理任务、查看 Git 协作进度、审核 PR 并评价贡献。</p>
                            </div>
                        </main>
                    </div>

                    <!-- Repository Home Modal -->
                    <transition name="fade">
                        <div v-if="teacherRepositoryOpen" class="fixed inset-0 z-[300] bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 md:p-6" @click.self="teacherRepositoryOpen = false">
                            <div class="relative w-full max-w-5xl flex flex-col border border-slate-200/70 rounded-[1.25rem] shadow-2xl overflow-hidden" style="background: rgba(255,255,255,0.88); backdrop-filter: blur(32px) saturate(180%); max-height: calc(100vh - 3rem);">
                                <!-- Sticky Modal Header -->
                                <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200/60 shrink-0" style="background: rgba(255,255,255,0.75);">
                                    <div>
                                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.18em]">Repository home</p>
                                        <h3 class="text-lg font-serif font-bold text-slate-900 mt-0.5">仓库主页</h3>
                                        <p class="text-xs text-slate-500 mt-0.5">实时查看 Gitea 文件、README、项目类图，并写下教师评语与修改建议。</p>
                                    </div>
                                    <button @click="teacherRepositoryOpen = false" class="w-9 h-9 ml-4 shrink-0 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-800 hover:shadow-md transition-all">
                                        <i class="ph ph-x text-base"></i>
                                    </button>
                                </div>
                                <!-- Scrollable Modal Body -->
                                <div class="flex-1 overflow-y-auto dark-scroll p-6">
                                    <div v-if="teacherRepositoryLoading" class="rounded-2xl bg-white/80 border border-slate-200/70 p-6 animate-pulse">
                                        <div class="h-4 w-40 bg-slate-200 rounded mb-4"></div>
                                        <div class="h-32 bg-slate-100 rounded-xl"></div>
                                    </div>
                                    <div v-else-if="teacherRepositoryHome" class="grid grid-cols-1 2xl:grid-cols-[minmax(0,1fr)_360px] gap-5">
                                        <div class="min-w-0 space-y-4">
                                            <!-- 仓库头信息 -->
                                            <div class="rounded-2xl bg-white/80 border border-slate-200/70 p-4">
                                                <div class="flex flex-wrap items-center justify-between gap-3">
                                                    <div class="min-w-0">
                                                        <p class="text-xs text-slate-500"><span class="font-bold text-slate-700">{{ teacherRepositoryHomeInfo.namespace || 'campus' }}</span> /</p>
                                                        <h4 class="text-xl font-extrabold text-slate-900 truncate">{{ teacherRepositoryHomeInfo.repoName }}</h4>
                                                        <p class="text-xs text-slate-500 mt-1">{{ teacherRepositoryHome.project?.title }} · {{ teacherRepositoryHomeInfo.course }}</p>
                                                    </div>
                                                    <span class="px-2 py-1 rounded-full border border-slate-200 bg-white text-xs font-bold text-slate-600">{{ teacherRepositoryHomeInfo.visibility || 'private' }}</span>
                                                </div>
                                            </div>

                                            <!-- 文件浏览器 -->
                                            <div class="rounded-2xl bg-white/80 border border-slate-200/70 overflow-hidden">
                                                <div class="px-4 py-3 border-b border-slate-100 bg-slate-50 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                                                    <div>
                                                        <span class="text-xs font-bold text-slate-700"><i class="ph ph-git-branch mr-1"></i>{{ teacherRepositoryHomeInfo.defaultBranch || 'main' }}</span>
                                                        <p class="text-[10px] text-slate-400 mt-1">实时读取 Gitea 仓库目录，点击文件夹进入、点击文件预览。</p>
                                                    </div>
                                                    <div class="flex flex-wrap items-center gap-1.5 text-[10px]">
                                                        <button
                                                            v-for="crumb in teacherRepoBreadcrumbs"
                                                            :key="crumb.path || 'root'"
                                                            @click="loadTeacherRepoBrowser(crumb.path)"
                                                            class="px-2 py-1 rounded-lg border transition-all"
                                                            :class="crumb.path === teacherRepoBrowserPath ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'"
                                                        >
                                                            {{ crumb.label }}
                                                        </button>
                                                    </div>
                                                </div>
                                                <div v-if="teacherRepoBrowserLoading" class="px-4 py-8 text-center text-xs text-slate-400">正在同步 Gitea 文件目录...</div>
                                                <div v-else-if="teacherRepoBrowserError" class="px-4 py-6 text-center text-xs text-rose-500">{{ teacherRepoBrowserError }}</div>
                                                <div v-else-if="teacherRepoBrowserEntries.length === 0" class="px-4 py-6 text-center text-xs text-slate-400">当前目录为空，等待首次 push 后刷新。</div>
                                                <div v-else class="overflow-x-auto">
                                                    <table class="w-full text-left text-[11px]">
                                                        <thead class="bg-slate-50 text-slate-500">
                                                            <tr>
                                                                <th class="px-4 py-2 font-bold">名称</th>
                                                                <th class="px-4 py-2 font-bold w-28">大小</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr
                                                                v-for="entry in teacherRepoBrowserEntries"
                                                                :key="entry.path || entry.name"
                                                                @click="openTeacherRepoEntry(entry)"
                                                                class="border-t border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                                                            >
                                                                <td class="px-4 py-2.5 font-medium text-slate-800">
                                                                    <span class="inline-flex items-center gap-2 min-w-0">
                                                                        <i :class="entry.type === 'dir' ? 'ph ph-folder text-amber-500' : 'ph ph-file-text text-slate-400'"></i>
                                                                        <span class="truncate">{{ entry.name }}</span>
                                                                    </span>
                                                                </td>
                                                                <td class="px-4 py-2.5 text-slate-500 font-mono">{{ entry.type === 'dir' ? '目录' : formatTeacherRepoFileSize(entry.size) }}</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div>
                                                <div v-if="teacherRepoBrowserBlob" class="border-t border-slate-200 bg-slate-950 text-slate-100">
                                                    <div class="px-4 py-2 border-b border-white/10 flex items-center justify-between gap-3">
                                                        <span class="text-[10px] font-bold truncate">{{ teacherRepoBrowserBlob.path }}</span>
                                                        <span class="text-[10px] text-slate-400 shrink-0">{{ formatTeacherRepoFileSize(teacherRepoBrowserBlob.size) }}</span>
                                                    </div>
                                                    <pre v-if="teacherRepoBrowserBlob.previewable" class="px-4 py-3 text-[11px] leading-relaxed overflow-x-auto whitespace-pre-wrap">{{ teacherRepoBrowserBlob.content }}</pre>
                                                    <div v-else class="px-4 py-4 text-[11px] text-slate-400">该文件为二进制或体积较大，暂不支持在线预览，请 clone 后查看。</div>
                                                </div>
                                            </div>

                                            <!-- README -->
                                            <section class="rounded-2xl bg-white/80 border border-slate-200/70 overflow-hidden">
                                                <h4 class="px-4 py-3 bg-slate-50 border-b border-slate-100 text-sm font-extrabold text-slate-900">README.md</h4>
                                                <pre class="p-5 text-sm leading-relaxed whitespace-pre-wrap text-slate-700">{{ teacherRepositoryHomeInfo.readme }}</pre>
                                            </section>

                                            <!-- 项目类图 -->
                                            <section class="rounded-2xl bg-white/80 border border-slate-200/70 overflow-hidden">
                                                <h4 class="px-4 py-3 bg-slate-50 border-b border-slate-100 text-sm font-extrabold text-slate-900">项目类图</h4>
                                                <div class="p-5">
                                                    <div class="rounded-xl bg-slate-950 text-slate-100 p-4 font-mono text-xs whitespace-pre-wrap">{{ teacherRepositoryHomeInfo.classDiagram }}</div>
                                                </div>
                                            </section>
                                        </div>

                                        <!-- 右栏侧边栏 -->
                                        <aside class="space-y-4">
                                            <!-- About + Clone地址 -->
                                            <section class="rounded-2xl bg-white/80 border border-slate-200/70 p-4">
                                                <h4 class="text-sm font-extrabold text-slate-900">About</h4>
                                                <p class="mt-2 text-xs text-slate-600 leading-relaxed">{{ teacherRepositoryHomeInfo.about }}</p>
                                                <div class="mt-4 grid gap-2 text-xs text-slate-500">
                                                    <span><i class="ph ph-users-three mr-1"></i>{{ teacherRepositoryHome.teamSummary?.totalMembers || 0 }} contributors</span>
                                                    <span v-if="teacherRepositoryHomeInfo.cloneUrlMockOnly"><i class="ph ph-lock-key mr-1"></i>演示 clone 地址，暂未接入真实 Gitea</span>
                                                </div>
                                                <!-- Clone 地址 -->
                                                <div v-if="teacherRepositoryHomeInfo.cloneUrl || teacherRepositoryHomeRepo.cloneUrl" class="mt-4">
                                                    <div class="flex items-center gap-2 mb-2">
                                                        <h5 class="text-xs font-extrabold text-slate-900">Clone (HTTPS)</h5>
                                                        <button @click="copyTeacherCloneUrl" class="px-2 py-1 rounded-lg bg-slate-100 text-[10px] font-bold text-slate-600 hover:bg-slate-200 transition-all">
                                                            <i :class="teacherRepoCopiedCloneUrl ? 'ph ph-check' : 'ph ph-copy'"></i>
                                                            {{ teacherRepoCopiedCloneUrl ? '已复制' : '复制' }}
                                                        </button>
                                                    </div>
                                                    <div class="rounded-xl bg-slate-950 text-slate-100 px-3 py-2 text-[11px] font-mono break-all leading-relaxed">{{ teacherRepositoryHomeInfo.cloneUrl || teacherRepositoryHomeRepo.cloneUrl }}</div>
                                                </div>
                                                <div v-if="teacherRepositoryHomeInfo.sshUrl || teacherRepositoryHomeRepo.sshUrl" class="mt-3">
                                                    <h5 class="text-xs font-extrabold text-slate-900 mb-2">Clone (SSH)</h5>
                                                    <div class="rounded-xl bg-slate-950 text-slate-100 px-3 py-2 text-[11px] font-mono break-all leading-relaxed">{{ teacherRepositoryHomeInfo.sshUrl || teacherRepositoryHomeRepo.sshUrl }}</div>
                                                </div>
                                            </section>

                                            <!-- Languages -->
                                            <section class="rounded-2xl bg-white/80 border border-slate-200/70 p-4">
                                                <h4 class="text-sm font-extrabold text-slate-900">Languages</h4>
                                                <div v-if="(teacherRepoBrowserLanguages.length ? teacherRepoBrowserLanguages : teacherRepositoryHomeLanguages).length" class="mt-3 h-2 rounded-full overflow-hidden flex bg-slate-100">
                                                    <span
                                                        v-for="lang in (teacherRepoBrowserLanguages.length ? teacherRepoBrowserLanguages : teacherRepositoryHomeLanguages)"
                                                        :key="lang.name"
                                                        class="h-full"
                                                        :style="{ width: lang.percent + '%', backgroundColor: lang.color || '#64748b' }"
                                                    ></span>
                                                </div>
                                                <div class="mt-3 grid gap-1">
                                                    <div
                                                        v-for="lang in (teacherRepoBrowserLanguages.length ? teacherRepoBrowserLanguages : teacherRepositoryHomeLanguages)"
                                                        :key="lang.name"
                                                        class="flex items-center justify-between text-xs"
                                                    >
                                                        <span class="font-bold text-slate-700">{{ lang.name }}</span>
                                                        <span class="text-slate-400">{{ lang.percent }}%</span>
                                                    </div>
                                                </div>
                                                <p v-if="!(teacherRepoBrowserLanguages.length || teacherRepositoryHomeLanguages.length)" class="mt-2 text-xs text-slate-400">等待 Gitea 同步语言统计。</p>
                                            </section>

                                            <!-- 教师评语与修改建议 -->
                                            <section class="rounded-2xl bg-white/80 border border-slate-200/70 p-4">
                                                <h4 class="text-sm font-extrabold text-slate-900">教师评语</h4>
                                                <textarea v-model="teacherFeedbackDraft.teacherComment" rows="4" class="mt-3 w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs outline-none focus:border-slate-900 resize-none" placeholder="写下对项目主页、架构和实现质量的评语"></textarea>
                                                <h4 class="text-sm font-extrabold text-slate-900 mt-4">修改建议</h4>
                                                <textarea v-model="teacherFeedbackDraft.revisionSuggestions" rows="4" class="mt-3 w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs outline-none focus:border-slate-900 resize-none" placeholder="写下需要学生继续修改的建议"></textarea>
                                                <p class="mt-3 text-[10px] text-slate-400">最后更新：{{ teacherRepositoryHome.teacherFeedbackUpdatedBy || '暂无' }} · {{ teacherRepositoryHome.teacherFeedbackUpdatedAt || '尚未更新' }}</p>
                                                <button @click="saveTeacherRepositoryFeedback" :disabled="teacherRepositoryLoading" class="mt-4 w-full px-4 py-2.5 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 disabled:opacity-50">保存教师反馈</button>
                                            </section>
                                        </aside>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </transition>
                </div>
            </transition>

        </div>
    `,
    setup(props, { emit }) {

        const mounted = ref(false);
        const activeModule = ref('portal'); // 'portal', 'assignment', 'training'
        const activeStage = ref('dev'); // 'plan', 'dev', 'review'
        const selectedTeam = ref(null);
        const activeDrawerTab = ref('milestone'); // 'milestone', 'collaboration', 'deliverables'
        const trainingProjects = ref([]);
        const selectedTrainingProject = ref(null);
        const trainingLoading = ref(false);
        const teacherReviewComment = ref('代码结构和测试记录已查看，请按审核结果推进。');
        const contributionDraft = ref({});
        const teacherRepositoryOpen = ref(false);
        const teacherRepositoryLoading = ref(false);
        const teacherRepositoryHome = ref(null);
        const teacherFeedbackDraft = ref({ teacherComment: '', revisionSuggestions: '' });

        // 仓库浏览器状态（与学生端 CodingSandbox 对齐）
        const teacherRepoBrowserPath = ref('');
        const teacherRepoBrowserEntries = ref([]);
        const teacherRepoBrowserLoading = ref(false);
        const teacherRepoBrowserBlob = ref(null);
        const teacherRepoBrowserError = ref('');
        const teacherRepoBrowserLanguages = ref([]);
        const teacherRepoCopiedCloneUrl = ref(false);

        onMounted(() => {
            setTimeout(() => {
                mounted.value = true;
            }, 50);
        });

        const pipelineStages = [
            { id: 'plan', name: '组队与开题 (1-3周)' },
            { id: 'dev', name: '开发过程监控 (4-12周)' },
            { id: 'review', name: '成果验收与联评 (13-16周)' }
        ];

        const drawerTabs = [
            { id: 'milestone', name: '里程碑评分' },
            { id: 'collaboration', name: '协作监控热力图' },
            { id: 'deliverables', name: '成果验收区' }
        ];

        // Mock Teams Data
        const teams = ref([
            {
                id: 'T-01',
                name: 'Alpha 架构组',
                projectTopic: '基于 Vue 3 的前端可视化搭建平台',
                stage: 'dev',
                isHot: true,
                health: 'good',
                score: 92,
                commits: 156,
                members: ['张伟', '李娜', '王强'],
                activityData: [20, 40, 60, 45, 80, 95, 75, 85, 90, 88, 70, 65, 85, 90, 92],
                milestones: [
                    { name: '需求分析与原型图', date: '10月10日', status: 'done', score: 95, desc: '需求文档详尽，原型交互逻辑清晰，顺利通过。' },
                    { name: '核心架构搭建', date: '11月01日', status: 'done', score: 90, desc: '基础脚手架已就绪，状态管理选型合理。' },
                    { name: '业务模块开发', date: '11月20日', status: 'doing', score: null, desc: '当前正在密集提交代码。' },
                    { name: '系统测试与优化', date: '12月05日', status: 'pending', score: null, desc: '待开始。' }
                ]
            },
            {
                id: 'T-02',
                name: 'Beta 数据流',
                projectTopic: '实时分布式日志分析大屏',
                stage: 'dev',
                isHot: false,
                health: 'warning',
                score: 75,
                commits: 42,
                members: ['刘洋', '陈杰'],
                activityData: [10, 20, 15, 30, 25, 40, 35, 30, 25, 20],
                milestones: [
                    { name: '需求分析与原型图', date: '10月12日', status: 'done', score: 80, desc: '原型略微简陋，需要补充边界情况。' },
                    { name: '核心架构搭建', date: '11月05日', status: 'doing', score: null, desc: '进度略有滞后，建议教师介入指导。' }
                ]
            },
            {
                id: 'T-03',
                name: 'Gamma 实验室',
                projectTopic: '校园二手交易跨平台小程序',
                stage: 'review',
                isHot: true,
                health: 'good',
                score: 88,
                commits: 210,
                members: ['赵云', '马超', '黄忠', '魏延'],
                activityData: [40, 50, 60, 70, 80, 85, 90, 95, 100, 80, 60, 40],
                milestones: [
                    { name: '需求分析与原型图', date: '09月20日', status: 'done', score: 85, desc: '通过。' },
                    { name: '核心架构搭建', date: '10月15日', status: 'done', score: 88, desc: '通过。' },
                    { name: '业务模块开发', date: '11月10日', status: 'done', score: 90, desc: '完成。' },
                    { name: '系统测试与优化', date: '11月25日', status: 'done', score: 89, desc: 'Bug 修复完毕。' }
                ]
            },
            {
                id: 'T-04',
                name: 'Delta 黑客派',
                projectTopic: '基于 WebRTC 的去中心化会议系统',
                stage: 'dev',
                isHot: false,
                health: 'danger',
                score: 55,
                commits: 12,
                members: ['周瑜', '鲁肃'],
                activityData: [5, 10, 5, 0, 0, 5, 10],
                milestones: [
                    { name: '需求分析与原型图', date: '10月15日', status: 'done', score: 60, desc: '勉强通过，技术栈不明确。' },
                    { name: '核心架构搭建', date: '11月10日', status: 'doing', score: null, desc: '遇到严重技术难点，停止提交代码超过 7 天。' }
                ]
            },
            {
                id: 'T-05',
                name: 'Epsilon 创想',
                projectTopic: 'AI 辅助编程副驾驶 (VSCode 插件)',
                stage: 'plan',
                isHot: false,
                health: 'good',
                score: 95,
                commits: 5,
                members: ['司马懿'],
                activityData: [5, 15, 25, 20],
                milestones: [
                    { name: '开题答辩', date: '12月01日', status: 'doing', score: null, desc: '正在准备 PPT。' }
                ]
            }
        ]);

        const filteredTeams = computed(() => {
            return teams.value.filter(t => t.stage === activeStage.value || activeStage.value === 'dev' && t.stage === 'review');
        });

        // 里程碑完成进度（用于卡片上的进度条）
        const milestoneProgress = (team) => {
            const list = team?.milestones || [];
            const done = list.filter(m => m.status === 'done').length;
            return { total: list.length, done, pct: list.length ? Math.round(done / list.length * 100) : 0 };
        };

        // 班级总览统计（基于全部团队）
        const teamStats = computed(() => {
            const list = teams.value;
            const total = list.length;
            const avg = total ? Math.round(list.reduce((a, t) => a + t.score, 0) / total) : 0;
            const risk = list.filter(t => t.health === 'danger').length;
            const commits = list.reduce((a, t) => a + t.commits, 0);
            return { total, avg, risk, commits };
        });

        // 过滤掉 Gitea 同步时误写入的系统账号幽灵成员
        // 匹配：纯英文用户名、或"xxx (未绑定 Gitea 用户)"格式、或已知系统账号前缀
        const GITEA_SYSTEM_PREFIXES = ['campus-admin', 'gitea-actions', 'teacher', 'admin', 'git', 'root', 'system', 'bot', 'ci'];
        const isPhantomMember = (member) => {
            const name = (member.name || '').trim();
            if (!name) return false;
            // 含有"未绑定 Gitea 用户"标记字符串的，直接过滤
            if (name.includes('未绑定 Gitea 用户')) return true;
            const nameLower = name.toLowerCase();
            // 名字以已知系统账号开头（兼容 "campus-admin" 和 "campus-admin (xxx)" 等变体）
            if (GITEA_SYSTEM_PREFIXES.some(prefix => nameLower === prefix || nameLower.startsWith(prefix + ' ') || nameLower.startsWith(prefix + '('))) return true;
            // 纯 ASCII 英文/数字/连字符（无汉字）视为未绑定的 Gitea 用户名
            return /^[A-Za-z0-9_\-]+$/.test(name);
        };
        const filteredMemberProgress = computed(() => {
            if (!selectedTrainingProject.value) return [];
            return (selectedTrainingProject.value.memberProgress || []).filter(m => !isPhantomMember(m));
        });

        const openTeamDetail = (team) => {
            selectedTeam.value = team;
            // 自动根据状态切换默认 tab
            if (activeStage.value === 'review') {
                activeDrawerTab.value = 'deliverables';
            } else {
                activeDrawerTab.value = 'milestone';
            }
        };

        const closeTeamDetail = () => {
            selectedTeam.value = null;
        };

        // Helper to generate heat map colors for Github style
        // 基于坐标的确定性取色，避免每次重渲染随机变色
        const getHeatColor = (col, row) => {
            const colors = ['#f1f5f9', '#c7d2fe', '#818cf8', '#4f46e5', '#312e81'];
            const seed = ((col * 31 + row * 17) % 97) / 97;
            // Bias towards lighter colors
            if (seed < 0.6) return colors[0];
            if (seed < 0.8) return colors[1];
            if (seed < 0.9) return colors[2];
            if (seed < 0.96) return colors[3];
            return colors[4];
        };

        // 成员贡献度：按序号递减的确定性权重归一化，保证各成员占比之和恒为 100%
        const memberShare = (mIdx, total) => {
            if (!total || total <= 0) return 0;
            const weights = Array.from({ length: total }, (_, i) => total - i);
            const sum = weights.reduce((a, b) => a + b, 0);
            return Math.round((weights[mIdx] / sum) * 100);
        };

        // 演示功能提示：避免按钮点击无响应
        const notifyFeature = (name) => {
            emit('show-toast', `${name}为演示功能，正式版即将开放`, 'info');
        };

        // 里程碑评分（演示数据本地生效）
        const milestoneScoreDraft = ref({});
        const confirmMilestoneScore = (ms, index) => {
            const key = selectedTeam.value?.id + '-' + index;
            const val = Number(milestoneScoreDraft.value[key]);
            if (Number.isNaN(val) || val < 0 || val > 100) {
                emit('show-toast', '请输入 0-100 之间的评分', 'warning');
                return;
            }
            ms.score = val;
            ms.status = 'done';
            emit('show-toast', `已记录「${ms.name}」评分：${val} 分`, 'success');
        };

        const syncContributionDraft = (project) => {
            const next = {};
            (project?.memberProgress || []).forEach((member) => {
                next[member.name] = {
                    score: Number(member.score || 0),
                    contribution: Number(member.contribution || 0)
                };
            });
            contributionDraft.value = next;
        };

        const replaceTrainingProject = (project) => {
            trainingProjects.value = trainingProjects.value.map((item) => item.id === project.id ? project : item);
            selectedTrainingProject.value = project;
            syncContributionDraft(project);
        };

        const loadTrainingProjects = async () => {
            trainingLoading.value = true;
            try {
                const projects = await teamGitApi.listProjects({ viewer: 'teacher' });
                trainingProjects.value = projects;
                if (!selectedTrainingProject.value || !projects.some((item) => item.id === selectedTrainingProject.value.id)) {
                    selectedTrainingProject.value = projects[0] || null;
                } else {
                    selectedTrainingProject.value = projects.find((item) => item.id === selectedTrainingProject.value.id);
                }
                if (selectedTrainingProject.value?.id) {
                    try {
                        const synced = await teamGitApi.refreshStatus(selectedTrainingProject.value.id, { actor: 'teacher' });
                        replaceTrainingProject(synced);
                    } catch (syncErr) {
                        emit('show-toast', syncErr?.message || 'Gitea 同步失败，已显示缓存数据', 'error');
                        syncContributionDraft(selectedTrainingProject.value);
                    }
                } else {
                    syncContributionDraft(selectedTrainingProject.value);
                }
            } catch (err) {
                emit('show-toast', err?.message || '编程团队实训数据同步失败', 'error');
            } finally {
                trainingLoading.value = false;
            }
        };

        const openTrainingModule = async () => {
            activeModule.value = 'training';
            if (trainingProjects.value.length === 0) {
                await loadTrainingProjects();
            }
        };

        const selectTrainingProject = async (project) => {
            selectedTrainingProject.value = project;
            syncContributionDraft(project);
            if (!project?.id) return;
            try {
                const synced = await teamGitApi.getProjectDetail(project.id, { viewer: 'teacher', sync: 1 });
                replaceTrainingProject(synced);
            } catch (err) {
                emit('show-toast', err?.message || '从 Gitea 同步团队详情失败', 'error');
            }
        };

        const teacherRepositoryHomeInfo = computed(() => teacherRepositoryHome.value || {});
        const teacherRepositoryHomeRepo = computed(() => teacherRepositoryHome.value?.repository || {});
        const teacherRepositoryHomeLanguages = computed(() => teacherRepositoryHome.value?.languageStats || []);

        const teacherRepoBreadcrumbs = computed(() => {
            const path = teacherRepoBrowserPath.value || '';
            const rootLabel = teacherRepositoryHome.value?.repoName || 'root';
            if (!path) return [{ label: rootLabel, path: '' }];
            const parts = path.split('/').filter(Boolean);
            const crumbs = [{ label: rootLabel, path: '' }];
            let accumulated = '';
            parts.forEach((part) => {
                accumulated = accumulated ? `${accumulated}/${part}` : part;
                crumbs.push({ label: part, path: accumulated });
            });
            return crumbs;
        });

        const resetTeacherRepoBrowser = () => {
            teacherRepoBrowserPath.value = '';
            teacherRepoBrowserEntries.value = [];
            teacherRepoBrowserBlob.value = null;
            teacherRepoBrowserLanguages.value = [];
            teacherRepoBrowserError.value = '';
        };

        const loadTeacherRepoBrowser = async (path = '', projectId) => {
            const id = projectId || selectedTrainingProject.value?.id;
            if (!id) return;
            teacherRepoBrowserLoading.value = true;
            teacherRepoBrowserError.value = '';
            teacherRepoBrowserBlob.value = null;
            try {
                const data = await teamGitApi.getRepositoryTree(id, {
                    path,
                    ref: teacherRepositoryHomeInfo.value.defaultBranch || teacherRepositoryHomeRepo.value.defaultBranch || 'main'
                });
                teacherRepoBrowserPath.value = data.path || '';
                teacherRepoBrowserEntries.value = data.entries || [];
            } catch (err) {
                teacherRepoBrowserEntries.value = [];
                teacherRepoBrowserError.value = err?.message || '文件目录加载失败';
            } finally {
                teacherRepoBrowserLoading.value = false;
            }
        };

        const loadTeacherRepoBlob = async (path, projectId) => {
            const id = projectId || selectedTrainingProject.value?.id;
            if (!id || !path) return;
            teacherRepoBrowserLoading.value = true;
            teacherRepoBrowserError.value = '';
            try {
                teacherRepoBrowserBlob.value = await teamGitApi.getRepositoryBlob(id, {
                    path,
                    ref: teacherRepositoryHomeInfo.value.defaultBranch || teacherRepositoryHomeRepo.value.defaultBranch || 'main'
                });
            } catch (err) {
                teacherRepoBrowserBlob.value = null;
                teacherRepoBrowserError.value = err?.message || '文件预览失败';
            } finally {
                teacherRepoBrowserLoading.value = false;
            }
        };

        const openTeacherRepoEntry = async (entry) => {
            if (!entry) return;
            if (entry.type === 'dir') {
                await loadTeacherRepoBrowser(entry.path || entry.name);
                return;
            }
            await loadTeacherRepoBlob(entry.path || entry.name);
        };

        const loadTeacherRepoLanguages = async (projectId) => {
            const id = projectId || selectedTrainingProject.value?.id;
            if (!id) return;
            try {
                teacherRepoBrowserLanguages.value = await teamGitApi.getRepositoryLanguages(id);
            } catch (err) {
                teacherRepoBrowserLanguages.value = [];
            }
        };

        const formatTeacherRepoFileSize = (size) => {
            const value = Number(size || 0);
            if (!value) return '-';
            if (value < 1024) return `${value} B`;
            if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
            return `${(value / (1024 * 1024)).toFixed(1)} MB`;
        };

        const copyTeacherCloneUrl = async () => {
            const url = teacherRepositoryHomeInfo.value.cloneUrl || teacherRepositoryHomeRepo.value.cloneUrl;
            if (!url) return;
            try {
                await navigator.clipboard.writeText(url);
                teacherRepoCopiedCloneUrl.value = true;
                setTimeout(() => { teacherRepoCopiedCloneUrl.value = false; }, 2000);
                emit('show-toast', 'Clone 地址已复制', 'success');
            } catch {
                emit('show-toast', '复制失败，请手动选择复制', 'error');
            }
        };

        const openTeacherRepositoryHome = async (project = selectedTrainingProject.value) => {
            if (!project) return;
            selectedTrainingProject.value = project;
            teacherRepositoryOpen.value = true;
            teacherRepositoryLoading.value = true;
            resetTeacherRepoBrowser();
            try {
                const home = await teamGitApi.getRepositoryHome(project.id);
                teacherRepositoryHome.value = home;
                teacherFeedbackDraft.value = {
                    teacherComment: home.teacherComment || '',
                    revisionSuggestions: home.revisionSuggestions || ''
                };
                await Promise.all([
                    loadTeacherRepoBrowser('', project.id),
                    loadTeacherRepoLanguages(project.id)
                ]);
            } catch (err) {
                emit('show-toast', err?.message || '仓库主页加载失败', 'error');
            } finally {
                teacherRepositoryLoading.value = false;
            }
        };

        const saveTeacherRepositoryFeedback = async () => {
            if (!selectedTrainingProject.value) return;
            teacherRepositoryLoading.value = true;
            try {
                const feedback = await teamGitApi.updateRepositoryFeedback(selectedTrainingProject.value.id, {
                    ...teacherFeedbackDraft.value,
                    actor: 'teacher'
                });
                teacherRepositoryHome.value = {
                    ...(teacherRepositoryHome.value || {}),
                    ...feedback
                };
                emit('show-toast', '教师评语和修改建议已同步到仓库主页', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '教师反馈保存失败', 'error');
            } finally {
                teacherRepositoryLoading.value = false;
            }
        };

        const createTeacherTrainingProject = async () => {
            trainingLoading.value = true;
            try {
                const project = await teamGitApi.createProject({
                    title: '教师端编程团队实训',
                    course: '软件工程综合实训',
                    teamName: `实训团队 ${trainingProjects.value.length + 1}`,
                    description: '由教师端管理员创建，用于管理团队任务、Git 协作进度、PR 审核与贡献评价。',
                    leaderId: '队长',
                    members: ['队长', '李明', '王磊'],
                    actor: 'teacher'
                });
                trainingProjects.value.unshift(project);
                selectTrainingProject(project);
                emit('show-toast', '已创建实训团队，学生端队长可继续完善项目介绍', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '分配实训团队失败', 'error');
            } finally {
                trainingLoading.value = false;
            }
        };

        const quickAssignTeacherTask = async (member) => {
            if (!selectedTrainingProject.value) return;
            const task = window.prompt(`给 ${member.name} 分配任务`, member.task || '');
            if (task === null || !task.trim()) return;
            const branch = window.prompt('任务分支名', member.branch || `feature/${member.id || 'task'}`);
            if (branch === null || !branch.trim()) return;
            try {
                const project = await teamGitApi.assignMemberTask(selectedTrainingProject.value.id, {
                    memberId: member.name,
                    task: task.trim(),
                    branch: branch.trim(),
                    actor: 'teacher'
                });
                replaceTrainingProject(project);
                emit('show-toast', '教师端任务分配已同步', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '任务分配失败', 'error');
            }
        };

        const sendTeacherReminder = async () => {
            if (!selectedTrainingProject.value) return;
            try {
                const project = await teamGitApi.remindMembers(selectedTrainingProject.value.id, {
                    message: '教师端提醒：请尽快完成本地提交、push 并创建 Pull Request，便于本周审核。',
                    actor: 'teacher'
                });
                replaceTrainingProject(project);
                emit('show-toast', '已提醒未提交成员', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '提醒发送失败', 'error');
            }
        };

        const teacherAuditPr = async (pr, action) => {
            if (!selectedTrainingProject.value) return;
            try {
                const project = await teamGitApi.reviewPullRequest(selectedTrainingProject.value.id, pr.number, {
                    action,
                    comment: teacherReviewComment.value,
                    actor: 'teacher'
                });
                replaceTrainingProject(project);
                emit('show-toast', action === 'teacher_approve' ? 'PR 已审核并合并' : '已要求学生继续修改 PR', 'success');
            } catch (err) {
                emit('show-toast', err?.message || 'PR 审核失败', 'error');
            }
        };

        const saveTeacherContribution = async () => {
            if (!selectedTrainingProject.value) return;
            const scores = (selectedTrainingProject.value.memberProgress || []).map((member) => ({
                memberId: member.name,
                score: Number(contributionDraft.value[member.name]?.score || 0),
                contribution: Number(contributionDraft.value[member.name]?.contribution || 0)
            }));
            try {
                const project = await teamGitApi.evaluateContribution(selectedTrainingProject.value.id, {
                    scores,
                    summary: '教师端管理员已完成团队贡献度评价。',
                    actor: 'teacher'
                });
                replaceTrainingProject(project);
                emit('show-toast', '团队贡献度评价已保存', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '贡献评价保存失败', 'error');
            }
        };

        return {
            mounted,
            activeModule,
            pipelineStages,
            activeStage,
            drawerTabs,
            activeDrawerTab,
            filteredTeams,
            milestoneProgress,
            teamStats,
            filteredMemberProgress,
            selectedTeam,
            openTeamDetail,
            closeTeamDetail,
            getHeatColor,
            memberShare,
            notifyFeature,
            milestoneScoreDraft,
            confirmMilestoneScore,
            trainingProjects,
            selectedTrainingProject,
            trainingLoading,
            teacherReviewComment,
            contributionDraft,
            teacherRepositoryOpen,
            teacherRepositoryLoading,
            teacherRepositoryHome,
            teacherFeedbackDraft,
            teacherRepositoryHomeInfo,
            teacherRepositoryHomeRepo,
            teacherRepositoryHomeLanguages,
            teacherRepoBrowserPath,
            teacherRepoBrowserEntries,
            teacherRepoBrowserLoading,
            teacherRepoBrowserBlob,
            teacherRepoBrowserError,
            teacherRepoBrowserLanguages,
            teacherRepoCopiedCloneUrl,
            teacherRepoBreadcrumbs,
            loadTeacherRepoBrowser,
            openTeacherRepoEntry,
            formatTeacherRepoFileSize,
            copyTeacherCloneUrl,
            openTrainingModule,
            loadTrainingProjects,
            selectTrainingProject,
            openTeacherRepositoryHome,
            saveTeacherRepositoryFeedback,
            createTeacherTrainingProject,
            quickAssignTeacherTask,
            sendTeacherReminder,
            teacherAuditPr,
            saveTeacherContribution
        }
    }
}
