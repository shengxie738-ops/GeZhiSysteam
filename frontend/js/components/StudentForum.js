import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { forumApi } from '../api/forum.js';
import { toBackendAssetUrl } from '../config/env.js';
import { formatTime } from '../utils/helpers.js';

export default {
    name: 'StudentForum',
    props: {
        currentUser: { type: Object, default: null },
        currentUserDisplayName: { type: String, default: '' }
    },
    emits: ['show-toast'],
    setup(props, { emit }) {
        // 帖子分类配置
        const categories = [
            { id: 'all', name: '全部话题', icon: 'ph-chat-circle-dots' },
            { id: 'qna', name: '课程答疑', icon: 'ph-graduation-cap' },
            { id: 'competition', name: '竞赛交流', icon: 'ph-trophy' },
            { id: 'experience', name: '经验分享', icon: 'ph-lightbulb-filament' },
            { id: 'chat', name: '日常闲聊', icon: 'ph-smiley' }
        ];

        const activeCategory = ref('all');
        const sortBy = ref('latest'); // 'latest' (最新) | 'hot' (最热)
        const currentPost = ref(null); // 当前查看的帖子详情，若为 null 则展示列表

        // 发帖表单状态
        const isWritingPost = ref(false);
        const newPost = ref({
            title: '',
            content: '',
            category: 'qna',
            tags: ''
        });

        // 回帖状态
        const newReplyContent = ref('');
        const isAiTyping = ref(false);

        // 数据存储
        const announcements = ref([]);
        const hotTopics = ref([]);
        const posts = ref([]);

        // 加载全部论坛数据
        const loadForumData = async () => {
            try {
                const [postsData, annsData, topicsData] = await Promise.all([
                    forumApi.getPosts(),
                    forumApi.getAnnouncements(),
                    forumApi.getHotTopics()
                ]);
                posts.value = postsData;
                announcements.value = annsData;
                hotTopics.value = topicsData;

                // 如果当前在看某篇帖子，更新它的详情数据
                if (currentPost.value) {
                    const latestPost = postsData.find(p => p.id === currentPost.value.id);
                    if (latestPost) {
                        currentPost.value = latestPost;
                    } else {
                        currentPost.value = null; // 帖子已被教师删除
                    }
                }
            } catch (err) {
                emit('show-toast', '论坛数据加载失败', 'error');
            }
        };

        // 过滤和排序后的帖子列表
        const filteredPosts = computed(() => {
            let result = [...posts.value];
            
            // 按分类过滤
            if (activeCategory.value !== 'all') {
                result = result.filter(p => p.category === activeCategory.value);
            }
            
            // 排序
            if (sortBy.value === 'latest') {
                result.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
            } else if (sortBy.value === 'hot') {
                result.sort((a, b) => b.likes - a.likes);
            }
            
            return result;
        });

        // 选中热议话题时，直接在列表过滤
        const selectHotTopic = (tag) => {
            activeCategory.value = 'all';
            emit('show-toast', `已为您聚焦话题: #${tag}`, 'success');
        };

        // 帖子点赞交互
        const toggleLike = async (post, event) => {
            if (event) event.stopPropagation();
            try {
                const updatedPost = await forumApi.likePost(post.id);
                if (updatedPost) {
                    post.likes = updatedPost.likes;
                    post.isLiked = true;
                }
            } catch (err) {
                emit('show-toast', '点赞失败', 'error');
            }
        };

        // 评论点赞交互
        const likeReply = async (post, reply) => {
            try {
                const updatedReply = await forumApi.likeReply(post.id, reply.id);
                if (updatedReply) {
                    reply.likes = updatedReply.likes;
                    emit('show-toast', '点赞成功', 'success');
                }
            } catch (err) {
                emit('show-toast', '点赞失败', 'error');
            }
        };

        // 查看帖子详情
        const viewPost = async (post) => {
            currentPost.value = post;
            try {
                const updatedPost = await forumApi.viewPost(post.id);
                if (updatedPost) {
                    post.views = updatedPost.views;
                }
            } catch (err) {}
            nextTick(() => {
                processCodeBlocks();
            });
        };

        // 返回帖子列表
        const backToList = () => {
            currentPost.value = null;
        };

        // 触发发帖表单折叠
        const toggleWritingForm = () => {
            isWritingPost.value = !isWritingPost.value;
        };

        // 发帖实现
        const createPost = async () => {
            const title = newPost.value.title.trim();
            const content = newPost.value.content.trim();
            if (!title || !content) {
                emit('show-toast', '请填写标题和内容', 'error');
                return;
            }

            const tagArray = newPost.value.tags
                ? newPost.value.tags.replace(/，/g, ',').split(',').map(t => t.trim()).filter(Boolean)
                : ['交流'];

            try {
                const postObj = await forumApi.createPost({
                    title,
                    content,
                    author: props.currentUserDisplayName || props.currentUser?.username || '求知者',
                    authorUsername: props.currentUser?.username,
                    avatar: props.currentUser?.avatar_url || `https://api.dicebear.com/7.x/notionists/svg?seed=${props.currentUser?.username || 'default'}`,
                    category: newPost.value.category,
                    tags: tagArray
                });

                // 重置表单
                newPost.value.title = '';
                newPost.value.content = '';
                newPost.value.tags = '';
                isWritingPost.value = false;

                emit('show-toast', '帖子发表成功！', 'success');
                await loadForumData();

                // 如果是在“课程答疑”下发帖，触发 AI 导师秒回机制
                if (postObj.category === 'qna') {
                    // AI 自动回帖功能已被移除 (依据方案 A)
                }
            } catch (err) {
                emit('show-toast', '发帖失败', 'error');
            }
        };


        // 提交回复
        const createReply = async () => {
            const content = newReplyContent.value.trim();
            if (!content) {
                emit('show-toast', '请输入回复内容', 'error');
                return;
            }

            try {
                await forumApi.createReply(currentPost.value.id, {
                    author: props.currentUserDisplayName || props.currentUser?.username || '探求者',
                    avatar: props.currentUser?.avatar_url || '',
                    content,
                    isAi: false
                });
                newReplyContent.value = '';
                emit('show-toast', '回帖成功！', 'success');
                await loadForumData();

                nextTick(() => {
                    processCodeBlocks();
                });
            } catch (err) {
                emit('show-toast', '回帖失败', 'error');
            }
        };

        // 解析并附带“导入代码沙箱”的按钮
        const processCodeBlocks = () => {
            const pres = document.querySelectorAll('.ai-reply-card pre, .post-detail-content pre');
            pres.forEach(pre => {
                if (pre.querySelector('.forum-code-actions')) return;

                pre.classList.add('relative', 'group', 'overflow-visible');
                
                const actionBar = document.createElement('div');
                actionBar.className = 'forum-code-actions absolute right-2.5 top-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-all duration-300 z-30 select-none';
                
                const copyBtn = document.createElement('button');
                copyBtn.className = 'px-2 py-1 bg-slate-950/80 text-white rounded text-[10px] font-bold flex items-center gap-1 hover:bg-slate-800 border border-slate-700 transition-all active:scale-95';
                copyBtn.innerHTML = '<i class="ph ph-copy"></i> 复制';
                copyBtn.onclick = (e) => {
                    e.stopPropagation();
                    const code = pre.querySelector('code')?.innerText || pre.innerText;
                    navigator.clipboard.writeText(code).then(() => {
                        emit('show-toast', '代码已复制到剪贴板', 'success');
                    });
                };
                
                const importBtn = document.createElement('button');
                importBtn.className = 'px-2 py-1 bg-violet-600 text-white rounded text-[10px] font-bold flex items-center gap-1 hover:bg-violet-700 border border-violet-500 transition-all active:scale-95';
                importBtn.innerHTML = '<i class="ph ph-arrow-square-out"></i> 导入沙箱';
                importBtn.onclick = (e) => {
                    e.stopPropagation();
                    const code = pre.querySelector('code')?.innerText || pre.innerText;
                    importToSandbox(code);
                };
                
                actionBar.appendChild(copyBtn);
                actionBar.appendChild(importBtn);
                pre.appendChild(actionBar);
            });
        };

        // 一键导入沙箱并跳转逻辑
        const importToSandbox = (code) => {
            emit('show-toast', '正在将算法代码载入编程实战沙箱...', 'info');
            
            // 派发全局自定义事件，使 main.js 能够截获，并把视图切换到 coding 编程沙箱
            window.dispatchEvent(new CustomEvent('switch-view', { detail: 'coding' }));
            
            // 延时分发代码，确保沙箱组件挂载完成
            setTimeout(() => {
                window.dispatchEvent(new CustomEvent('import-code', { detail: code }));
            }, 250);
        };

        // 智能导师快速答疑专线交互
        const quickAskText = ref('');
        const sendQuickAsk = () => {
            const text = quickAskText.value.trim();
            if (!text) return;
            
            emit('show-toast', '正在向 Prof. X 智能体专线提问...', 'info');
            quickAskText.value = '';

            setTimeout(async () => {
                emit('show-toast', 'Prof. X 为您在学术答疑板块创建了一个新帖！', 'success');
                
                try {
                    const postObj = await forumApi.createPost({
                        title: `关于「${text}」的智能答疑帖`,
                        content: `我对「${text}」这一概念的算法实现有些不解，请问在真实项目中应当如何处理这一模型？`,
                        author: props.currentUserDisplayName || props.currentUser?.username || '求知者',
                        authorUsername: props.currentUser?.username,
                        avatar: props.currentUser?.avatar_url || '',
                        category: 'qna',
                        tags: ['AI提问', '算法求助']
                    });

                    await loadForumData();
                    // AI 自动回帖功能已被移除 (依据方案 A)
                } catch (err) {
                    console.error("快速发帖失败:", err);
                }
            }, 1000);
        };

        // 个人删帖交互
        const deleteMyPost = async (postId) => {
            if (!confirm('确定要删除这篇帖子吗？该操作不可恢复。')) return;
            try {
                await forumApi.deletePost(postId);
                emit('show-toast', '帖子已删除', 'success');
                if (currentPost.value && currentPost.value.id === postId) {
                    backToList();
                }
                await loadForumData();
            } catch (err) {
                emit('show-toast', '删除失败', 'error');
            }
        };

        // 监听 currentPost 详情状态的渲染
        watch(currentPost, (newVal) => {
            if (newVal) {
                nextTick(() => {
                    processCodeBlocks();
                });
            }
        });

        onMounted(() => {
            loadForumData();
            // 定期拉取，实现教师端发布新公告或修改 AI 内容的即时同步
            const timer = setInterval(loadForumData, 15000);
            onBeforeUnmount(() => clearInterval(timer));
        });

        // 格式化详情正文的 Markdown (用于简单渲染，带 marked)
        const formatMarkdown = (text) => {
            let parsed = text;
            if (window.marked && typeof window.marked.parse === 'function') {
                parsed = window.marked.parse(text);
            } else {
                // 换行简单转换
                parsed = text.replace(/\n/g, '<br>');
            }
            if (window.DOMPurify && typeof window.DOMPurify.sanitize === 'function') {
                return window.DOMPurify.sanitize(parsed);
            }
            return parsed;
        };

        // ==================== 头像 URL 处理 ====================
        const getFullAvatarUrl = (path, author) => {
            if (!path) return `https://api.dicebear.com/7.x/notionists/svg?seed=${author || 'guest'}`;
            // 将 localhost / 127.0.0.1 的绝对 URL 转为相对路径
            const localMatch = path.match(/^https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?(\/.*)$/);
            if (localMatch) path = localMatch[1];
            if (path.startsWith('http') || path.startsWith('data:')) return path;
            return toBackendAssetUrl(path);
        };

        // 图片加载失败时使用 dicebear 兜底
        const onAvatarError = (e, author) => {
            e.target.src = `https://api.dicebear.com/7.x/notionists/svg?seed=${author || 'guest'}`;
        };

        return {
            getFullAvatarUrl,
            onAvatarError,
            categories,
            activeCategory,
            sortBy,
            currentPost,
            isWritingPost,
            newPost,
            newReplyContent,
            isAiTyping,
            announcements,
            hotTopics,
            filteredPosts,
            selectHotTopic,
            toggleLike,
            likeReply,
            viewPost,
            backToList,
            toggleWritingForm,
            createPost,
            createReply,
            quickAskText,
            sendQuickAsk,
            formatMarkdown,
            formatTime,
            deleteMyPost
        };
    },
    template: `
        <div class="w-full h-full p-4 lg:p-6 flex flex-col overflow-hidden select-none relative bg-slate-50">
            <!-- 头部导航区 (仅在详情页显示) -->
            <div v-if="currentPost" class="flex items-center mb-4 w-full border-b border-slate-200 pb-3 shrink-0 select-none">
                <button @click="backToList" 
                        class="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1.5 font-semibold transition-all">
                    <i class="ph ph-arrow-left"></i> 返回论坛列表
                </button>
            </div>

            <!-- 主三栏式面板结构 -->
            <div class="flex-1 min-h-0 flex gap-5 overflow-hidden">
                
                <!-- ==================== 1. 左侧栏: 板块分类筛选 (Width: 20%) ==================== -->
                <aside class="w-[20%] flex flex-col gap-4 shrink-0 h-full">
                    <div class="glass-panel-liquid p-4 flex flex-col gap-2 h-full">
                        <div class="text-xs font-bold text-slate-400 mb-2 px-2 flex items-center gap-1">
                            <i class="ph ph-squares-four"></i> 社区板块
                        </div>
                        <button v-for="cat in categories" :key="cat.id"
                                @click="activeCategory = cat.id; backToList();"
                                class="w-full text-left py-3 px-4 rounded-xl text-xs font-semibold flex items-center justify-between transition-all"
                                :class="activeCategory === cat.id 
                                     ? 'bg-primary text-white shadow-md' 
                                     : 'bg-white/40 text-slate-600 hover:bg-white/90 border border-transparent hover:border-slate-100'">
                            <span class="flex items-center gap-2">
                                <i :class="cat.icon" class="text-sm"></i>
                                {{ cat.name }}
                            </span>
                            <span v-if="activeCategory === cat.id" class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        </button>
                    </div>
                </aside>

                <!-- ==================== 2. 中间栏: 帖子列表与详情 (Width: 55%) ==================== -->
                <main class="flex-1 min-w-0 h-full flex flex-col gap-4">
                    
                    <!-- 详情视图 -->
                    <div v-if="currentPost" class="glass-panel-liquid flex-1 p-6 flex flex-col overflow-hidden">
                        <!-- 详情内容区 (可滚动) -->
                        <div class="flex-1 overflow-y-auto pr-1 no-scrollbar flex flex-col gap-6">
                            <!-- 发帖人信息 -->
                            <div class="flex items-center justify-between border-b border-slate-100 pb-4">
                                <div class="flex items-center gap-3">
                                    <img :src="getFullAvatarUrl(currentPost.avatar, currentPost.author)" @error="onAvatarError($event, currentPost.author)" class="w-10 h-10 rounded-full border border-slate-200 bg-white shrink-0">
                                    <div>
                                        <div class="text-xs font-bold text-slate-800">{{ currentPost.author }}</div>
                                        <div class="text-[10px] text-slate-600 mt-0.5">发表于 {{ formatTime(currentPost.createdAt) }}</div>
                                    </div>
                                </div>
                                <div class="flex items-center gap-2">
                                    <button v-if="currentUser?.username && ((currentPost.authorUsername && currentPost.authorUsername === currentUser.username) || (!currentPost.authorUsername && currentPost.author === currentUser.username))" @click="deleteMyPost(currentPost.id)" class="text-[10px] font-bold px-2.5 py-1 rounded-full bg-rose-50 text-rose-500 border border-rose-100 hover:bg-rose-500 hover:text-white transition-all flex items-center gap-1">
                                        <i class="ph ph-trash"></i> 删除
                                    </button>
                                    <span class="text-[10px] font-bold px-2.5 py-1 rounded-full bg-[#1c2b38]/5 text-primary border border-slate-100">
                                        {{ currentPost.categoryLabel }}
                                    </span>
                                </div>
                            </div>

                            <!-- 帖子主要文本 -->
                            <div class="post-detail-content">
                                <h1 class="text-xl font-extrabold text-slate-900 mb-3" style="font-family: 'Noto Serif SC', serif;">
                                    {{ currentPost.title }}
                                </h1>
                                <div class="flex gap-1.5 mb-5 flex-wrap">
                                    <span v-for="tag in currentPost.tags" :key="tag" 
                                          class="text-[9px] font-bold px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full border border-slate-200">
                                        #{{ tag }}
                                    </span>
                                </div>
                                <div class="text-xs text-slate-700 leading-relaxed markdown-body" v-html="formatMarkdown(currentPost.content)"></div>
                            </div>

                            <!-- 回帖区域 (列表) -->
                            <div class="mt-6 flex flex-col gap-4">
                                <h3 class="text-xs font-bold text-slate-500 border-b border-slate-100 pb-2 flex items-center gap-1">
                                    <i class="ph ph-chat-teardrop"></i> 全部回复 ({{ currentPost.replies.length }})
                                </h3>

                                <div v-if="currentPost.replies.length === 0" class="text-center py-6 text-slate-400 text-xs italic">
                                    暂无回复，发表第一条观点支持作者吧！
                                </div>

                                <div v-for="reply in currentPost.replies" :key="reply.id"
                                     class="p-4 rounded-2xl flex flex-col gap-2.5 transition-all"
                                     :class="reply.isAi 
                                          ? 'bg-indigo-50/70 border border-indigo-100/60 shadow-[0_4px_12px_rgba(99,102,241,0.04)] ai-reply-card' 
                                          : 'bg-white/40 border border-slate-100/60'">
                                    <div class="flex items-center justify-between">
                                        <div class="flex items-center gap-2">
                                            <img :src="getFullAvatarUrl(reply.avatar, reply.author)" @error="onAvatarError($event, reply.author)" class="w-8 h-8 rounded-full border bg-white shrink-0"
                                                 :class="reply.isAi ? 'border-indigo-300 ring-2 ring-indigo-500/10' : 'border-slate-200'">
                                            <div>
                                                <div class="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                                                    {{ reply.author }}
                                                    <span v-if="reply.isAi" 
                                                          class="text-[8px] bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-bold px-1.5 py-0.2 rounded flex items-center gap-0.5 animate-pulse">
                                                        <i class="ph ph-sparkle"></i> AI 导师
                                                    </span>
                                                </div>
                                                <div class="text-[9px] text-slate-600">回复于 {{ formatTime(reply.createdAt) }}</div>
                                            </div>
                                        </div>
                                        <button @click="likeReply(currentPost, reply)" 
                                                class="text-[10px] text-slate-400 hover:text-rose-500 font-semibold flex items-center gap-1 transition-all">
                                            <i class="ph ph-heart"></i> {{ reply.likes }}
                                        </button>
                                    </div>
                                    <div class="text-xs text-slate-600 leading-relaxed markdown-body" v-html="formatMarkdown(reply.content)"></div>
                                </div>

                                <!-- AI正在输入动画 -->
                                <div v-if="isAiTyping" class="p-4 rounded-2xl bg-indigo-50/70 border border-indigo-100/60 flex items-start gap-3">
                                    <div class="w-8 h-8 rounded-full border border-indigo-300 ring-2 ring-indigo-500/10 bg-white flex items-center justify-center shrink-0 text-indigo-500 text-base shadow-sm animate-pulse">
                                        <i class="ph ph-robot"></i>
                                    </div>
                                    <div class="flex flex-col gap-2">
                                        <span class="text-xs font-bold text-indigo-600 flex items-center gap-1.5">
                                            Prof. X (AI导师) <span class="text-[9px] text-slate-400 font-normal">正在极速生成专业诊断...</span>
                                        </span>
                                        <div class="flex gap-1.5 mt-1">
                                            <span class="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 0s"></span>
                                            <span class="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 0.15s"></span>
                                            <span class="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 0.3s"></span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 底部快捷跟帖 -->
                        <div class="border-t border-slate-100 pt-4 mt-4 flex items-center gap-2 select-none">
                            <input v-model="newReplyContent" @keyup.enter="createReply"
                                   placeholder="输入您的跟帖见解或学术追问，支持 Markdown 代码..."
                                   class="liquid-glass-input flex-1 px-4 py-2 text-xs outline-none focus:ring-0">
                            <button @click="createReply" 
                                    class="liquid-glass-btn px-4 py-2 rounded-xl text-xs font-bold active:scale-95 flex items-center gap-1 shadow-md">
                                <i class="ph ph-paper-plane-right"></i> 回复
                            </button>
                        </div>
                    </div>

                    <!-- 列表主视图 -->
                    <div v-else class="flex-1 flex flex-col min-h-0 gap-4">
                        <!-- 发帖及排序控制 -->
                        <div class="glass-panel-liquid p-4 shrink-0 flex flex-col gap-3">
                            <div class="flex items-center justify-between">
                                <!-- 最新/最热排序切换 -->
                                <div class="flex border border-slate-200/60 rounded-xl overflow-hidden p-0.5 bg-white/40 select-none">
                                    <button @click="sortBy = 'latest'" 
                                            class="px-3.5 py-1.5 rounded-lg text-[10px] font-bold transition-all flex items-center gap-1"
                                            :class="sortBy === 'latest' ? 'bg-primary text-white shadow-sm' : 'text-slate-500 hover:text-slate-800'">
                                        <i class="ph ph-clock"></i> 最新发表
                                    </button>
                                    <button @click="sortBy = 'hot'" 
                                            class="px-3.5 py-1.5 rounded-lg text-[10px] font-bold transition-all flex items-center gap-1"
                                            :class="sortBy === 'hot' ? 'bg-primary text-white shadow-sm' : 'text-slate-500 hover:text-slate-800'">
                                        <i class="ph ph-flame"></i> 热门排行
                                    </button>
                                </div>

                                <!-- 开启/收起发帖框 -->
                                <button @click="toggleWritingForm" 
                                        class="liquid-glass-btn px-4.5 py-2 rounded-xl text-xs font-bold active:scale-95 transition-all shadow-md flex items-center gap-1.5">
                                    <i :class="isWritingPost ? 'ph-x-circle' : 'ph-plus-circle'" class="text-sm"></i>
                                    {{ isWritingPost ? '取消发布' : '分享新帖' }}
                                </button>
                            </div>

                            <!-- 展开的发布新帖表单 -->
                            <transition name="fade">
                                <div v-if="isWritingPost" class="border-t border-slate-100 pt-4 flex flex-col gap-3">
                                    <div class="flex gap-2">
                                        <input v-model="newPost.title" placeholder="输入帖子标题，说明你的核心问题（如：单链表反转如何实现）..." 
                                               class="liquid-glass-input flex-1 px-4 py-2.5 text-xs outline-none">
                                        
                                        <select v-model="newPost.category" 
                                                class="bg-white border border-slate-200 text-slate-700 text-xs rounded-xl py-1 px-3 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all font-semibold select-none">
                                            <option value="qna">课程答疑</option>
                                            <option value="competition">竞赛交流</option>
                                            <option value="experience">经验分享</option>
                                            <option value="chat">日常闲聊</option>
                                        </select>
                                    </div>
                                    <textarea v-model="newPost.content" rows="4" 
                                              placeholder="详细描述您遇到的疑惑或分享的心得（支持 Markdown 代码块格式）..." 
                                              class="liquid-glass-input w-full px-4 py-3 text-xs outline-none resize-none"></textarea>
                                    
                                    <div class="flex gap-2 items-center justify-between">
                                        <input v-model="newPost.tags" placeholder="标签标签（用英文逗号分隔，如: Vue3, Proxy）..." 
                                               class="liquid-glass-input w-[65%] px-4 py-2 text-[10px] outline-none">
                                        
                                        <button @click="createPost" 
                                                class="liquid-glass-btn px-5 py-2.5 rounded-xl text-xs font-bold active:scale-95 flex items-center gap-1.5 shadow-md self-end">
                                            <i class="ph ph-paper-plane-tilt"></i> 确认发表帖子
                                        </button>
                                    </div>
                                </div>
                            </transition>
                        </div>

                        <!-- 帖子列表循环区 -->
                        <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col gap-4">
                            <div v-if="filteredPosts.length === 0" class="glass-panel-liquid p-8 text-center text-slate-400 italic text-xs">
                                暂时没有该板块的讨论帖子，来发第一条讨论帖吧！
                            </div>

                            <div v-for="post in filteredPosts" :key="post.id"
                                 @click="viewPost(post)"
                                 class="glass-panel-liquid p-5 cursor-pointer shrink-0 flex flex-col gap-3 border border-white/60 hover:shadow-lg transition-all hover:-translate-y-0.5 group">
                                
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center gap-3">
                                        <img :src="getFullAvatarUrl(post.avatar, post.author)" @error="onAvatarError($event, post.author)" class="w-8 h-8 rounded-full border border-slate-200 bg-white shrink-0">
                                        <div class="flex flex-col">
                                            <div class="flex items-center gap-2">
                                                <span class="text-xs font-bold text-slate-800">{{ post.author }}</span>
                                                <span class="text-[10px] text-slate-500 font-mono">{{ formatTime(post.createdAt) }}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <button v-if="currentUser?.username && ((post.authorUsername && post.authorUsername === currentUser.username) || (!post.authorUsername && post.author === currentUser.username))" @click.stop="deleteMyPost(post.id)" class="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-rose-50 text-rose-500 border-rose-200 shadow-sm flex items-center gap-1 hover:bg-rose-500 hover:text-white transition-all group-hover:border-rose-300">
                                            <i class="ph ph-trash"></i> 删除
                                        </button>
                                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-slate-50 text-slate-500 border-slate-200 shadow-sm flex items-center gap-1 group-hover:border-primary/30 group-hover:text-primary transition-colors">
                                            {{ post.categoryLabel || post.category }}
                                        </span>
                                    </div>
                                </div>
                                <h3 class="text-base font-extrabold text-slate-900 leading-snug mt-1" style="font-family: 'Noto Serif SC', serif;">
                                    {{ post.title }}
                                </h3>
                                <p class="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                                    {{ typeof post.content === 'string' ? post.content.replace(/<[^>]+>/g, '').substring(0, 150) : '' }}
                                </p>
                                <div class="flex items-center justify-between mt-1">
                                    <div class="flex items-center gap-1.5 flex-wrap">
                                        <span v-for="tag in post.tags" :key="tag" 
                                              class="text-[9px] font-bold px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded border border-slate-200/60">
                                            #{{ tag }}
                                        </span>
                                    </div>
                                    <div class="flex items-center gap-3 text-[11px] text-slate-500 font-semibold font-mono">
                                        <span class="flex items-center gap-1 hover:text-rose-500 transition-colors" @click.stop="toggleLike(post, $event)">
                                            <i class="ph" :class="post.isLiked ? 'ph-heart-fill text-rose-500' : 'ph-heart'"></i> {{ post.likes }}
                                        </span>
                                        <span class="flex items-center gap-1">
                                            <i class="ph ph-chat-teardrop"></i> {{ post.replies ? post.replies.length : 0 }}
                                        </span>
                                        <span class="flex items-center gap-1">
                                            <i class="ph ph-eye"></i> {{ post.views }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>

                <!-- ==================== 3. 右侧栏: 公告与热点 (Width: 25%) ==================== -->
                <aside class="w-[25%] flex flex-col gap-4 shrink-0 h-full overflow-y-auto no-scrollbar">
                    
                    <!-- 置顶公告 -->
                    <div class="glass-panel-liquid p-5 flex flex-col gap-4 shrink-0">
                        <div class="text-xs font-bold text-slate-400 flex items-center gap-1 border-b border-slate-100 pb-2">
                            <i class="ph ph-megaphone text-sm"></i> 置顶公告
                        </div>
                        <div class="flex flex-col gap-3">
                            <div v-for="ann in announcements" :key="ann.id" 
                                 class="flex flex-col gap-1 border border-rose-100 bg-rose-50/30 p-3 rounded-xl relative group">
                                <span v-if="ann.isPinned" class="absolute right-3 top-3 text-[9px] text-rose-400 font-mono italic">pinned</span>
                                <div class="flex items-center gap-1.5 text-[9px] font-bold text-rose-500">
                                    <span class="w-1 h-1 rounded-full bg-rose-500"></span> 官方
                                    <span class="text-slate-400 font-normal font-mono ml-auto mr-8">{{ formatTime(ann.createdAt) }}</span>
                                </div>
                                <div class="text-xs text-slate-700 font-semibold leading-relaxed mt-1">
                                    {{ ann.title }}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 今日热议话题 -->
                    <div class="glass-panel-liquid p-5 flex flex-col gap-3 shrink-0">
                        <div class="text-xs font-bold text-slate-400 flex items-center gap-1 border-b border-slate-100 pb-2">
                            <i class="ph ph-flame text-sm text-[#b91c1c]"></i> 今日热议
                        </div>
                        <div class="flex flex-col gap-2">
                            <div v-for="(topic, index) in hotTopics" :key="topic.tag"
                                 @click="selectHotTopic(topic.tag)"
                                 class="flex items-center justify-between p-2 rounded-xl bg-white/20 border border-white/60 hover:bg-white/70 transition-all cursor-pointer">
                                <div class="flex items-center gap-2">
                                    <span class="w-4 h-4 rounded-md bg-slate-900/5 text-slate-600 font-mono text-[10px] font-bold flex items-center justify-center select-none">
                                        {{ index + 1 }}
                                    </span>
                                    <span class="text-[11px] font-bold text-slate-700"># {{ topic.tag }}</span>
                                </div>
                                <span class="text-[9px] text-slate-600 font-mono">{{ topic.count }} 讨论</span>
                            </div>
                        </div>
                    </div>

                    <!-- AI 导师专线 -->
                    <div class="glass-panel-liquid p-5 flex flex-col gap-3 shrink-0">
                        <div class="text-xs font-bold text-slate-600 flex items-center justify-between border-b border-slate-100 pb-2">
                            <span class="flex items-center gap-1"><i class="ph ph-robot text-sm text-primary"></i> 智能导师专线</span>
                            <span class="flex items-center gap-1 text-[9px] text-emerald-600 font-bold shrink-0">
                                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Prof.X 在线
                            </span>
                        </div>
                        
                        <div class="flex items-start gap-2.5 p-2 bg-indigo-50/50 border border-indigo-100/50 rounded-xl mb-1">
                            <img src="https://api.dicebear.com/7.x/notionists/svg?seed=ProfX" class="w-7 h-7 rounded-full border border-indigo-200 bg-white shrink-0">
                            <div class="text-[10px] text-slate-500 leading-relaxed font-semibold">
                                我是 Prof.X，随时为您解答任何数据结构、算法架构、Vue 3 或 AI 原理的编程疑问。
                            </div>
                        </div>

                        <!-- 快速输入问答 -->
                        <div class="flex flex-col gap-1.5 mt-2 select-none">
                            <input v-model="quickAskText" @keyup.enter="sendQuickAsk"
                                   placeholder="输入您的学术疑问进行极速提问..." 
                                   class="liquid-glass-input px-3 py-2 text-[10px] outline-none">
                            <button @click="sendQuickAsk"
                                    class="liquid-glass-btn py-2 rounded-xl text-[10px] font-bold active:scale-95 flex items-center justify-center gap-1 shadow">
                                <i class="ph ph-magic-wand"></i> 一键呼唤 AI 导师
                            </button>
                        </div>
                    </div>
                </aside>

            </div>
        </div>
    `
};
