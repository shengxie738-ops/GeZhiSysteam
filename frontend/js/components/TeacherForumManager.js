import { ref, computed, onMounted } from 'vue';
import { forumApi } from '../api/forum.js';
import { formatTime } from '../utils/helpers.js';
import { toBackendAssetUrl } from '../config/env.js';

export default {
    name: 'TeacherForumManager',
    emits: ['show-toast'],
    setup(_, { emit }) {
        const loading = ref(true);
        const activeTab = ref('posts'); // posts, announcements, ai_audit, topics
        const postsList = ref([]);
        const announcementList = ref([]);
        const hotTopicsList = ref([]);
        const aiReplyLogsList = ref([]);

        // 帖子筛选与状态
        const filterCategory = ref('all');
        const searchKeyword = ref('');

        // 置顶公告表单
        const isSavingAnn = ref(false);
        const annForm = ref({
            title: '【重要】关于2026年数据结构与算法期末综合实训评审的补充说明',
            content: '本次期末综合实训着重考核同学们在真实大工程环境下的代码协作与多分支合并能力。CodeNinja 与 Alina 智能体诊断分将占总体评估分值的 40%，教师组阅卷评分占 60%。请各小组务必于11月15日23:59前将项目压缩包提报至作业管理舱，并保证能通过编程沙箱的全部单元测试用例。'
        });

        // AI 导师编辑抽屉/弹窗状态
        const activeAuditLog = ref(null);
        const auditedContent = ref('');
        const isSavingAudit = ref(false);

        // 新增话题表单
        const newTopicTag = ref('');

        // 加载数据
        const loadAllData = async () => {
            loading.value = true;
            try {
                const [posts, anns, topics, aiLogs] = await Promise.all([
                    forumApi.getPosts(),
                    forumApi.getAnnouncements(),
                    forumApi.getHotTopics(),
                    forumApi.getAiReplyLogs()
                ]);
                postsList.value = posts;
                announcementList.value = anns;
                hotTopicsList.value = topics;
                aiReplyLogsList.value = aiLogs;
            } catch (err) {
                emit('show-toast', '论坛管理数据加载失败', 'error');
            } finally {
                loading.value = false;
            }
        };

        // 过滤帖子
        const filteredPosts = computed(() => {
            let result = [...postsList.value];
            if (filterCategory.value !== 'all') {
                result = result.filter(p => p.category === filterCategory.value);
            }
            if (searchKeyword.value.trim()) {
                const kw = searchKeyword.value.toLowerCase().trim();
                result = result.filter(p => 
                    p.title.toLowerCase().includes(kw) || 
                    p.author.toLowerCase().includes(kw) ||
                    p.content.toLowerCase().includes(kw)
                );
            }
            return result;
        });

        // 教师删除帖子
        const handleDeletePost = async (postId) => {
            if (!confirm('确定要彻底删除该篇帖子吗？该操作不可逆！')) return;
            try {
                await forumApi.deletePost(postId);
                emit('show-toast', '帖子已成功移除并扣除相关积分', 'success');
                // 同步更新本地状态
                postsList.value = postsList.value.filter(p => p.id !== postId);
            } catch (err) {
                emit('show-toast', '删除帖子失败', 'error');
            }
        };

        // 教师置顶加精/取消置顶帖子
        const handleTogglePin = async (post) => {
            const currentPinned = announcementList.value.some(a => a.id === `ann-post-${post.id}`);
            const nextPinned = !currentPinned;
            try {
                await forumApi.setPostPin(post.id, nextPinned);
                emit('show-toast', nextPinned ? '该贴已推荐加精，并同步生成置顶公告栏通知' : '已撤销该帖的加精与置顶状态', 'success');
                await loadAllData();
            } catch (err) {
                emit('show-toast', '置顶设置失败', 'error');
            }
        };

        // 教师发布新置顶公告
        const handlePublishAnn = async () => {
            if (!annForm.value.title.trim()) {
                emit('show-toast', '公告标题不能为空', 'error');
                return;
            }
            isSavingAnn.value = true;
            try {
                await forumApi.publishAnnouncement({
                    title: annForm.value.title,
                    content: annForm.value.content
                });
                emit('show-toast', '置顶公告已同步发布至学术广场', 'success');
                annForm.value.title = '';
                annForm.value.content = '';
                activeTab.value = 'posts'; // 跳回主面板查看生成的公告贴
                await loadAllData();
            } catch (err) {
                emit('show-toast', '公告发布失败', 'error');
            } finally {
                isSavingAnn.value = false;
            }
        };

        // 打开 AI 审核编辑
        const openAuditDrawer = (log) => {
            activeAuditLog.value = log;
            auditedContent.value = log.content;
        };

        // 关闭 AI 审核
        const closeAuditDrawer = () => {
            activeAuditLog.value = null;
        };

        // 保存编辑后的 AI 回答
        const handleSaveAudit = async () => {
            if (!auditedContent.value.trim()) {
                emit('show-toast', '回答内容不能为空', 'error');
                return;
            }
            isSavingAudit.value = true;
            try {
                await forumApi.auditAiReply(activeAuditLog.value.id, {
                    content: auditedContent.value,
                    status: 'approved'
                });
                emit('show-toast', 'AI 解答已审核校准，并实时更新至论坛跟帖区', 'success');
                closeAuditDrawer();
                await loadAllData();
            } catch (err) {
                emit('show-toast', '校准失败', 'error');
            } finally {
                isSavingAudit.value = false;
            }
        };

        // 调节话题权重
        const handleUpdateTopicWeight = async (tag, change) => {
            try {
                await forumApi.updateHotTopicWeight(tag, change);
                // 同步本地
                const topic = hotTopicsList.value.find(h => h.tag === tag);
                if (topic) {
                    topic.count = Math.max(0, topic.count + change);
                }
                emit('show-toast', '话题热度权重已调整', 'success');
            } catch (err) {
                emit('show-toast', '调整权重失败', 'error');
            }
        };

        // 新增话题
        const handleAddTopic = async () => {
            const tag = newTopicTag.value.trim();
            if (!tag) return;
            try {
                await forumApi.addHotTopic(tag);
                emit('show-toast', `已成功推荐并创建热议話題: #${tag}`, 'success');
                newTopicTag.value = '';
                await loadAllData();
            } catch (err) {
                emit('show-toast', '创建话题失败', 'error');
            }
        };

        // 删除话题
        const handleDeleteTopic = async (tag) => {
            try {
                await forumApi.deleteHotTopic(tag);
                emit('show-toast', '该话题已移出热议榜', 'success');
                hotTopicsList.value = hotTopicsList.value.filter(h => h.tag !== tag);
            } catch (err) {
                emit('show-toast', '移出话题失败', 'error');
            }
        };

        onMounted(loadAllData);

        // 简易渲染 Markdown 预览
        const formatMarkdown = (text) => {
            let parsed = text;
            if (window.marked && typeof window.marked.parse === 'function') {
                parsed = window.marked.parse(text);
            } else {
                parsed = text.replace(/\n/g, '<br>');
            }
            if (window.DOMPurify && typeof window.DOMPurify.sanitize === 'function') {
                return window.DOMPurify.sanitize(parsed);
            }
            return parsed;
        };

        // ─── 课程答疑 Tab 状态与逻辑 ────────────────────────────
        const activeQnaPost = ref(null);       // 当前选中的帖子
        const teacherReplyContent = ref('');   // 教师回复输入
        const isSubmittingReply = ref(false);  // 提交中状态

        // 头像兜底：无 avatar 时用 dicebear 生成基于 author 的默认头像
        const getFullAvatarUrl = (path, author) => {
            if (!path) return `https://api.dicebear.com/7.x/notionists/svg?seed=${author || 'guest'}`;
            const localMatch = path.match(/^https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?(\/.*)$/);
            if (localMatch) path = localMatch[1];
            if (path.startsWith('http') || path.startsWith('data:')) return path;
            return toBackendAssetUrl(path);
        };

        // 从 postsList 过滤课程答疑帖，按时间降序
        const qnaPosts = computed(() => {
            return postsList.value
                .filter(p => p.category === 'qna')
                .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        });

        // 判定帖子是否已被教师答疑
        const isPostAnsweredByTeacher = (post) => {
            return (post.replies || []).some(r =>
                (r.author || '').includes('教师') || (r.author || '').includes('老师')
            );
        };

        // 判定回复是否来自教师
        const isTeacherReply = (reply) => {
            const author = reply.author || '';
            return author.includes('教师') || author.includes('老师');
        };

        // 获取当前教师姓氏
        const teacherSurname = computed(() => {
            const userStr = localStorage.getItem('currentUser');
            if (!userStr) return '老';
            try {
                const user = JSON.parse(userStr);
                const name = user.real_name || user.username || '';
                if (!name) return '老';
                if (/^[\u4e00-\u9fa5]/.test(name)) return name.charAt(0);
                return name;
            } catch {
                return '老';
            }
        });

        // 选中帖子查看详情
        const selectQnaPost = (post) => {
            activeQnaPost.value = post;
            teacherReplyContent.value = '';
        };

        // 教师提交答疑回复
        const submitTeacherReply = async () => {
            if (!teacherReplyContent.value.trim() || !activeQnaPost.value) {
                emit('show-toast', '请输入回复内容', 'warning');
                return;
            }
            isSubmittingReply.value = true;
            try {
                const teacherName = `${teacherSurname.value}老师(教师)`;
                const userStr = localStorage.getItem('currentUser');
                let avatar = '';
                if (userStr) {
                    try { avatar = JSON.parse(userStr).avatar_url || ''; } catch {}
                }
                await forumApi.createReply(activeQnaPost.value.id, {
                    author: teacherName,
                    avatar: avatar,
                    isAi: false,
                    content: teacherReplyContent.value
                });
                emit('show-toast', '答疑回复已发布至论坛', 'success');
                teacherReplyContent.value = '';
                await loadAllData();
                // 重新选中该帖以更新详情
                const updated = postsList.value.find(p => p.id === activeQnaPost.value.id);
                if (updated) activeQnaPost.value = updated;
            } catch (err) {
                emit('show-toast', '回复失败，请重试', 'error');
            } finally {
                isSubmittingReply.value = false;
            }
        };

        return {
            loading,
            activeTab,
            postsList,
            announcementList,
            hotTopicsList,
            aiReplyLogsList,
            filterCategory,
            searchKeyword,
            filteredPosts,
            handleDeletePost,
            handleTogglePin,
            isSavingAnn,
            annForm,
            handlePublishAnn,
            activeAuditLog,
            auditedContent,
            isSavingAudit,
            openAuditDrawer,
            closeAuditDrawer,
            handleSaveAudit,
            newTopicTag,
            handleAddTopic,
            handleDeleteTopic,
            handleUpdateTopicWeight,
            formatMarkdown,
            loadAllData,
            formatTime,
            // 课程答疑
            activeQnaPost,
            teacherReplyContent,
            isSubmittingReply,
            qnaPosts,
            isPostAnsweredByTeacher,
            isTeacherReply,
            selectQnaPost,
            submitTeacherReply,
            getFullAvatarUrl
        };
    },
    template: `
        <section class="absolute inset-0 overflow-y-auto p-6 lg:p-8 select-none">
            <div class="max-w-7xl mx-auto flex flex-col gap-6">
                <!-- 页头 -->
                <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
                    <div>
                        <h2 class="text-2xl font-bold text-slate-800" style="font-family: 'Noto Serif SC', serif;">学术论坛管理中心</h2>
                        <p class="text-sm text-slate-500 mt-1">置顶重要大纲通知、管理净化班级发帖内容，并实时监控/校正 AI 导师的学术响应内容。</p>
                    </div>
                </div>

                <!-- 导航 Tab 条 -->
                <div class="flex gap-2">
                    <button @click="activeTab = 'posts'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'posts' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white/70 text-slate-600 border-white hover:bg-white'">
                        帖子审查台
                    </button>
                    <button @click="activeTab = 'qna'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'qna' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white/70 text-slate-600 border-white hover:bg-white'">
                        课程答疑
                    </button>
                    <button @click="activeTab = 'announcements'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'announcements' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white/70 text-slate-600 border-white hover:bg-white'">
                        置顶公告发布
                    </button>
                    <button @click="activeTab = 'ai_audit'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'ai_audit' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white/70 text-slate-600 border-white hover:bg-white'">
                        AI 导师监控
                    </button>
                    <button @click="activeTab = 'topics'" class="px-4 py-2 rounded-xl text-xs font-bold border transition-all"
                        :class="activeTab === 'topics' ? 'bg-[#1c2b38] text-white border-[#1c2b38]' : 'bg-white/70 text-slate-600 border-white hover:bg-white'">
                        话题权重配置
                    </button>
                </div>

                <div v-if="loading" class="glass-panel-liquid p-8 text-xs text-slate-500">正在同步论坛运行指标...</div>

                <template v-else>
                    <!-- ==================== 1. 帖子审查台 ==================== -->
                    <div v-show="activeTab === 'posts'" class="flex flex-col gap-6">
                        <!-- 搜索与板块过滤 -->
                        <div class="glass-panel-liquid p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
                            <div class="flex gap-2 w-full md:w-auto">
                                <select v-model="filterCategory" class="bg-white/80 border border-slate-200 text-slate-700 font-semibold text-xs px-3 py-2 rounded-xl shadow-sm focus:outline-none">
                                    <option value="all">全部板块话题</option>
                                    <option value="qna">课程答疑</option>
                                    <option value="competition">竞赛交流</option>
                                    <option value="experience">经验分享</option>
                                    <option value="chat">日常闲聊</option>
                                </select>
                            </div>
                            <div class="relative w-full md:w-80">
                                <input v-model="searchKeyword" placeholder="检索帖子标题、发帖人、内容..." 
                                       class="w-full bg-white/60 border border-slate-200 text-slate-800 text-xs rounded-xl pl-9 pr-4 py-2.5 outline-none focus:border-[#1c2b38] transition-all" />
                                <i class="ph ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
                            </div>
                        </div>

                        <!-- 帖子列表 -->
                        <div class="flex flex-col gap-4">
                            <div v-if="filteredPosts.length === 0" class="glass-panel-liquid p-8 text-center text-slate-400 italic text-xs">
                                未匹配到任何发帖内容。
                            </div>
                            
                            <div v-for="post in filteredPosts" :key="post.id"
                                 class="glass-panel-liquid p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/60 hover:shadow-md transition-all">
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 mb-2 flex-wrap">
                                        <span class="text-xs px-2.5 py-0.5 rounded-full font-bold bg-[#1c2b38]/5 text-primary">
                                            {{ post.categoryLabel }}
                                        </span>
                                        <span v-for="tag in post.tags" :key="tag" class="text-[9px] font-bold px-2 py-0.2 bg-slate-100 text-slate-500 rounded border border-slate-200">
                                            #{{ tag }}
                                        </span>
                                        <span v-if="announcementList.some(a => a.id === 'ann-post-' + post.id)" class="text-[9px] font-bold px-2 py-0.2 bg-red-50 text-red-600 rounded border border-red-200">
                                            置顶置精
                                        </span>
                                    </div>
                                    <h3 class="text-sm font-extrabold text-slate-800 leading-snug mb-1">{{ post.title }}</h3>
                                    <p class="text-[10px] text-slate-600">
                                        作者: <span class="font-bold text-slate-800">{{ post.author }}</span> | 发表于: {{ formatTime(post.createdAt) }} | 浏览量: {{ post.views }} | 点赞数: {{ post.likes }} | 回复数: {{ post.replies.length }}
                                    </p>
                                </div>
                                <div class="flex gap-2.5 shrink-0 self-end md:self-center">
                                    <button @click="handleTogglePin(post)" 
                                            class="px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all"
                                            :class="announcementList.some(a => a.id === 'ann-post-' + post.id)
                                                ? 'bg-red-50 text-red-600 border-red-200 hover:bg-red-100'
                                                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'">
                                        <i class="ph ph-push-pin mr-1"></i>
                                        {{ announcementList.some(a => a.id === 'ann-post-' + post.id) ? '取消置顶' : '置顶加精' }}
                                    </button>
                                    <button @click="handleDeletePost(post.id)" 
                                            class="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg text-[10px] transition-all">
                                        <i class="ph ph-trash mr-1"></i>
                                        删除违规
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- ==================== 1.5 课程答疑 ==================== -->
                    <div v-show="activeTab === 'qna'" class="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6">
                        <!-- 左侧：帖子列表 -->
                        <div class="glass-panel-liquid p-4 flex flex-col gap-3 max-h-[calc(100vh-220px)] overflow-y-auto">
                            <div v-if="qnaPosts.length === 0" class="p-8 text-center text-slate-400 italic text-xs">
                                暂无课程答疑帖子。
                            </div>
                            <div v-for="post in qnaPosts" :key="post.id"
                                 @click="selectQnaPost(post)"
                                 class="p-4 rounded-xl cursor-pointer border transition-all"
                                 :class="activeQnaPost?.id === post.id ? 'bg-slate-50 border-[#1c2b38] shadow-sm' : 'border-transparent hover:bg-slate-50/50'">
                                <div class="flex items-center justify-between gap-2 mb-2">
                                    <span class="text-[9px] font-bold px-2 py-0.2 rounded"
                                          :class="isPostAnsweredByTeacher(post) ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-amber-50 text-amber-600 border border-amber-100'">
                                        {{ isPostAnsweredByTeacher(post) ? '已答疑' : '未答疑' }}
                                    </span>
                                    <span class="text-[10px] text-slate-400 font-mono">{{ formatTime(post.createdAt) }}</span>
                                </div>
                                <h4 class="text-xs font-bold text-slate-800 leading-snug line-clamp-2">{{ post.title }}</h4>
                                <p class="text-[10px] text-slate-500 mt-1.5">
                                    作者: <span class="font-semibold">{{ post.author }}</span> · 回复: {{ (post.replies || []).length }} · 浏览: {{ post.views }}
                                </p>
                            </div>
                        </div>

                        <!-- 右侧：详情与回复 -->
                        <div class="glass-panel-liquid p-6 flex flex-col gap-5 max-h-[calc(100vh-220px)] overflow-y-auto">
                            <div v-if="!activeQnaPost" class="flex-1 flex items-center justify-center text-xs text-slate-400">
                                <div class="text-center">
                                    <i class="ph ph-graduation-cap text-3xl text-slate-300"></i>
                                    <p class="mt-3">请从左侧选择一篇帖子查看详情并进行答疑</p>
                                </div>
                            </div>
                            <template v-else>
                                <!-- 帖子详情 -->
                                <div class="pb-4 border-b border-slate-200/60">
                                    <div class="flex items-center gap-2 mb-3 flex-wrap">
                                        <span v-for="tag in activeQnaPost.tags" :key="tag" class="text-[9px] font-bold px-2 py-0.2 bg-slate-100 text-slate-500 rounded border border-slate-200">
                                            #{{ tag }}
                                        </span>
                                        <span class="text-[9px] font-bold px-2 py-0.2 rounded"
                                              :class="isPostAnsweredByTeacher(activeQnaPost) ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-amber-50 text-amber-600 border border-amber-100'">
                                            {{ isPostAnsweredByTeacher(activeQnaPost) ? '已答疑' : '未答疑' }}
                                        </span>
                                    </div>
                                    <h3 class="text-base font-bold text-slate-800 leading-snug mb-2">{{ activeQnaPost.title }}</h3>
                                    <p class="text-[10px] text-slate-500">
                                        作者: <span class="font-bold text-slate-700">{{ activeQnaPost.author }}</span> | 发表于: {{ formatTime(activeQnaPost.createdAt) }} | 浏览: {{ activeQnaPost.views }} | 点赞: {{ activeQnaPost.likes }}
                                    </p>
                                    <div class="mt-3 text-xs text-slate-700 leading-relaxed" v-html="formatMarkdown(activeQnaPost.content || '')"></div>
                                </div>

                                <!-- 回复列表 -->
                                <div class="flex flex-col gap-3">
                                    <h4 class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                        <i class="ph ph-chat-circle-dots"></i> 全部回复 ({{ (activeQnaPost.replies || []).length }})
                                    </h4>
                                    <div v-if="(activeQnaPost.replies || []).length === 0" class="text-[11px] text-slate-400 italic py-2">
                                        暂无回复，快来抢答~
                                    </div>
                                    <div v-for="reply in (activeQnaPost.replies || [])" :key="reply.id"
                                         class="p-3.5 rounded-xl border transition-all"
                                         :class="isTeacherReply(reply) ? 'bg-[#1c2b38]/5 border-[#1c2b38]/20' : 'bg-slate-50/60 border-slate-100'">
                                        <div class="flex items-center justify-between gap-2 mb-1.5">
                                            <div class="flex items-center gap-2">
                                                <img :src="getFullAvatarUrl(reply.avatar, reply.author)" class="w-6 h-6 rounded-full border border-slate-200 bg-white shrink-0" />
                                                <span class="text-xs font-bold" :class="isTeacherReply(reply) ? 'text-[#1c2b38]' : 'text-slate-700'">{{ reply.author }}</span>
                                                <span v-if="isTeacherReply(reply)" class="text-[8px] font-bold px-1.5 py-0.5 bg-[#1c2b38] text-white rounded">教师</span>
                                                <span v-if="reply.isAi" class="text-[8px] font-bold px-1.5 py-0.5 bg-indigo-100 text-indigo-600 rounded">AI</span>
                                            </div>
                                            <span class="text-[10px] text-slate-400 font-mono">{{ formatTime(reply.createdAt) }}</span>
                                        </div>
                                        <p class="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{{ reply.content }}</p>
                                    </div>
                                </div>

                                <!-- 教师回复输入框 -->
                                <div class="pt-4 border-t border-slate-200/60">
                                    <label class="block text-xs font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                                        <i class="ph ph-pen-nib text-[#1c2b38]"></i> 教师答疑回复
                                    </label>
                                    <textarea v-model="teacherReplyContent" placeholder="输入答疑内容，提交后将显示在学生论坛该帖子下方..." rows="3"
                                              class="w-full bg-white/60 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38] resize-none"></textarea>
                                    <button @click="submitTeacherReply" :disabled="isSubmittingReply"
                                            class="mt-2 px-5 py-2.5 bg-[#1c2b38] hover:bg-[#253645] active:scale-95 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50">
                                        <i v-if="isSubmittingReply" class="ph ph-spinner animate-spin"></i>
                                        <i v-else class="ph ph-paper-plane-tilt"></i>
                                        发布答疑
                                    </button>
                                </div>
                            </template>
                        </div>
                    </div>

                    <!-- ==================== 2. 置顶公告发布 ==================== -->
                    <form v-show="activeTab === 'announcements'" @submit.prevent="handlePublishAnn" 
                          class="glass-panel-liquid p-6 w-full max-w-2xl mx-auto flex flex-col gap-5">
                        <h3 class="text-base font-bold text-slate-800 flex items-center gap-1.5">
                            <i class="ph ph-megaphone text-lg text-primary"></i> 撰写发布置顶公告
                        </h3>
                        <div class="flex flex-col gap-4">
                            <div>
                                <label class="block text-xs font-semibold text-slate-600 mb-1">公告标题</label>
                                <input v-model="annForm.title" required placeholder="如: 【公告】关于大作业多智能体诊断说明"
                                       class="w-full bg-white/60 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38]" />
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-600 mb-1">公告正文（支持 Markdown）</label>
                                <textarea v-model="annForm.content" required rows="6" placeholder="输入公告要点内容，支持代码及列表..."
                                          class="w-full bg-white/40 border border-slate-200 text-slate-800 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-[#1c2b38]/10 focus:border-[#1c2b38] resize-none font-mono"></textarea>
                            </div>
                        </div>
                        <button type="submit" :disabled="isSavingAnn" class="self-end px-5 py-2.5 bg-[#1c2b38] hover:bg-[#253645] text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm transition-all">
                            <i v-if="isSavingAnn" class="ph ph-spinner animate-spin"></i>
                            <i v-else class="ph ph-paper-plane-tilt"></i>
                            广播置顶下发
                        </button>
                    </form>

                    <!-- ==================== 3. AI 导师监管 ==================== -->
                    <div v-show="activeTab === 'ai_audit'" class="flex flex-col gap-6">
                        <div class="glass-panel-liquid p-5">
                            <h3 class="text-base font-bold text-slate-800 mb-1">Prof. X 及 CodeNinja 自动响应审计</h3>
                            <p class="text-xs text-slate-500">查看 AI 导师在答疑板块下的历史自动回复日志。为了保证学术严谨性，教师可以直接在此编辑并纠错，修改后学生论坛将同步渲染校正后的内容。</p>
                        </div>

                        <div class="grid grid-cols-1 gap-4">
                            <div v-for="log in aiReplyLogsList" :key="log.id" 
                                 class="glass-panel-liquid p-5 flex flex-col gap-3.5 border border-white/60">
                                <div class="flex justify-between items-center pb-2 border-b border-slate-100">
                                    <div>
                                        <span class="text-xs font-bold text-slate-800 flex items-center gap-1">
                                            <i class="ph ph-robot text-primary"></i> {{ log.agentName }} 自动响应
                                        </span>
                                        <p class="text-[10px] text-slate-600 mt-0.5">针对帖子: <span class="font-semibold text-slate-800">《{{ log.postTitle }}》</span></p>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <span class="text-[9px] px-2 py-0.5 rounded-full font-bold"
                                              :class="log.status === 'approved' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-amber-50 text-amber-600 border-amber-100'">
                                            {{ log.status === 'approved' ? '已校准/已审' : '待审查' }}
                                        </span>
                                        <span class="text-slate-600 text-[10px] font-mono">{{ log.time }}</span>
                                    </div>
                                </div>
                                <div class="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs overflow-x-auto max-h-[150px] whitespace-pre-wrap">
                                    {{ log.content }}
                                </div>
                                <div class="flex justify-end gap-2">
                                    <button @click="openAuditDrawer(log)" class="px-4 py-2 bg-[#1c2b38] hover:bg-[#253645] text-white font-bold rounded-xl text-xs transition-colors flex items-center gap-1">
                                        <i class="ph ph-pencil-simple-line"></i> 审核并校准内容
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- ==================== 4. 话题权重配置 ==================== -->
                    <div v-show="activeTab === 'topics'" class="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6">
                        <!-- 权重排行表 -->
                        <div class="glass-panel-liquid p-6">
                            <div class="flex justify-between items-center mb-5">
                                <h3 class="text-base font-bold text-slate-800">今日热议话题热度管理</h3>
                                <div class="flex items-center gap-2">
                                    <input v-model="newTopicTag" placeholder="输入话题新标签..." 
                                           class="bg-white/80 border border-slate-200 text-slate-800 text-xs px-3 py-1.5 rounded-xl outline-none" />
                                    <button @click="handleAddTopic" class="px-3.5 py-1.5 bg-[#1c2b38] text-white font-bold rounded-xl text-xs flex items-center gap-0.5"><i class="ph ph-plus"></i> 添加</button>
                                </div>
                            </div>

                            <table class="w-full text-left text-xs border-collapse">
                                <thead class="text-slate-600 font-semibold border-b border-slate-200">
                                    <tr>
                                        <th class="py-3 px-2">热议话题标签</th>
                                        <th class="py-3 px-2 text-center">当前热度统计值</th>
                                        <th class="py-3 px-2 text-center">热度干预</th>
                                        <th class="py-3 px-2 text-center">操作</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="topic in hotTopicsList" :key="topic.tag" class="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                                        <td class="py-3 px-2 font-bold text-slate-800">#{{ topic.tag }}</td>
                                        <td class="py-3 px-2 text-center font-mono font-bold text-[#1c2b38]" style="font-family: 'Barlow Condensed', sans-serif;">{{ topic.count }} 次讨论</td>
                                        <td class="py-3 px-2 text-center">
                                            <div class="inline-flex gap-1">
                                                <button @click="handleUpdateTopicWeight(topic.tag, 10)" class="w-6 h-6 rounded bg-slate-100 hover:bg-slate-200 flex items-center justify-center font-bold text-slate-600">+</button>
                                                <button @click="handleUpdateTopicWeight(topic.tag, -10)" class="w-6 h-6 rounded bg-slate-100 hover:bg-slate-200 flex items-center justify-center font-bold text-slate-600">-</button>
                                            </div>
                                        </td>
                                        <td class="py-3 px-2 text-center">
                                            <button @click="handleDeleteTopic(topic.tag)" class="text-xs text-red-500 hover:underline">移出热榜</button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <!-- 侧栏说明 -->
                        <aside class="glass-panel-liquid p-5 flex flex-col gap-4">
                            <h4 class="text-xs font-bold text-slate-800">热榜分流说明</h4>
                            <p class="text-xs text-slate-500 leading-relaxed">热议话题排行决定了学生端论坛右侧“今日热议”栏目的展示顺序与标签露出强度。</p>
                            <p class="text-xs text-slate-500 leading-relaxed">若有竞赛发布、大课改革或核心高难度 Checkpoint 分布，教师可手动向该标签注入“+10”权重进行快速聚焦与导流，促进学生在相应板块下进行充分研讨。</p>
                        </aside>
                    </div>
                </template>
            </div>

            <!-- AI 导师回帖校准弹窗 (Modal) -->
            <transition name="fade">
                <div v-if="activeAuditLog" v-cloak
                     class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm">
                    <div class="bg-white rounded-3xl shadow-float w-full max-w-xl overflow-hidden border border-slate-200 flex flex-col max-h-[85vh]">
                        <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <h3 class="text-base font-bold text-slate-800 flex items-center gap-1.5">
                                <i class="ph ph-sparkle text-[#b91c1c]"></i> 校准 AI 导师解答内容
                            </h3>
                            <button @click="closeAuditDrawer" class="text-slate-400 hover:text-slate-700"><i class="ph ph-x text-lg"></i></button>
                        </div>
                        <div class="p-6 overflow-y-auto flex-1 flex flex-col gap-4">
                            <div>
                                <span class="text-xs font-semibold text-slate-600">原贴问题</span>
                                <p class="text-xs font-bold text-slate-700 mt-1">《{{ activeAuditLog.postTitle }}》</p>
                            </div>
                            <div class="flex-1 flex flex-col">
                                <label class="block text-xs font-semibold text-slate-600 mb-1.5">审核校准文本（支持 Markdown）</label>
                                <textarea v-model="auditedContent" rows="10" 
                                          class="w-full flex-1 bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-xl p-3 outline-none focus:ring-2 focus:ring-[#1c2b38]/20 font-mono resize-none"></textarea>
                            </div>
                        </div>
                        <div class="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end gap-3 shrink-0">
                            <button @click="closeAuditDrawer" class="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50">取消</button>
                            <button @click="handleSaveAudit" :disabled="isSavingAudit" class="px-5 py-2.5 bg-[#1c2b38] hover:bg-[#253645] text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm">
                                <i v-if="isSavingAudit" class="ph ph-spinner animate-spin"></i>
                                <i v-else class="ph ph-check"></i>
                                审核并发布更新
                            </button>
                        </div>
                    </div>
                </div>
            </transition>
        </section>
    `
};
