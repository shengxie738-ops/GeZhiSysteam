import { mockAnnouncements, mockHotTopics, mockPosts, mockAiReplyLogs } from '../data/mockData.js';
import request from '../utils/request.js';

const API_BASE = window.FORUM_API_BASE_URL || localStorage.getItem('forumApiBaseUrl') || '';

async function requestJson(path, options = {}, mockFn) {
    const useMockFirst = localStorage.getItem('forumMockFirst') === 'true';

    const wrapStandardDTO = (data) => ({
        code: 200,
        message: 'ok',
        data: data
    });

    const handleResponseDTO = (json) => {
        if (json && json.code === 200) {
            return json.data;
        } else {
            console.error('[Forum API 业务异常]', json?.message || '未知错误');
            throw new Error(json?.message || 'API 请求失败');
        }
    };

    if (useMockFirst && typeof mockFn === 'function') {
        const mockData = await mockFn();
        const mockDTO = wrapStandardDTO(mockData);
        return handleResponseDTO(mockDTO);
    }

    try {
        const json = await request(`${API_BASE}${path}`, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
        });
        return handleResponseDTO(json);
    } catch (error) {
        if (typeof mockFn === 'function') {
            const mockData = await mockFn(error);
            const mockDTO = wrapStandardDTO(mockData);
            return handleResponseDTO(mockDTO);
        }
        throw error;
    }
}

export const forumApi = {
    // 获取帖子列表
    getPosts() {
        return requestJson('/forum/posts', {}, () => {
            return mockPosts.value;
        });
    },

    // 获取最新未答疑的课程答疑帖子（无教师回复的 qna 帖子）
    getUnansweredQna(limit = 5) {
        return requestJson(`/forum/unanswered-qna?limit=${limit}`, {}, null);
    },

    // 创建新帖子
    createPost(payload) {
        return requestJson('/forum/posts', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const newPost = {
                id: `post-${Date.now()}`,
                title: payload.title,
                content: payload.content,
                author: payload.author || '匿名学习者',
                authorUsername: payload.authorUsername,
                avatar: payload.avatar || 'https://api.dicebear.com/7.x/notionists/svg?seed=default',
                category: payload.category || 'qna',
                categoryLabel: payload.category === 'qna' ? '课程答疑' : (payload.category === 'competition' ? '竞赛交流' : (payload.category === 'experience' ? '经验分享' : '日常闲聊')),
                tags: payload.tags || ['交流'],
                likes: 0,
                isLiked: false,
                views: 1,
                createdAt: '刚刚',
                replies: []
            };
            mockPosts.value.unshift(newPost);
            return newPost;
        });
    },

    // 创建回帖
    createReply(postId, payload) {
        return requestJson(`/forum/posts/${postId}/replies`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const post = mockPosts.value.find(p => p.id === postId);
            if (!post) throw new Error('帖子不存在');
            const newReply = {
                id: `reply-${Date.now()}`,
                author: payload.author || '匿名回复者',
                avatar: payload.avatar || 'https://api.dicebear.com/7.x/notionists/svg?seed=default',
                isAi: payload.isAi || false,
                content: payload.content,
                createdAt: '刚刚',
                likes: 0
            };
            post.replies.push(newReply);

            // 如果是 AI 自动回复，同时录入 AI 导师回帖日志供教师监管
            if (payload.isAi) {
                mockAiReplyLogs.value.unshift({
                    id: `log-${Date.now()}`,
                    postId: post.id,
                    postTitle: post.title,
                    replyId: newReply.id,
                    agentName: payload.author || 'Prof. X',
                    content: payload.content,
                    time: '刚刚',
                    status: 'pending_audit'
                });
            }
            return newReply;
        });
    },

    // 删除帖子
    deletePost(postId) {
        return requestJson(`/forum/posts/${postId}`, {
            method: 'DELETE'
        }, () => {
            const index = mockPosts.value.findIndex(p => p.id === postId);
            if (index !== -1) {
                mockPosts.value.splice(index, 1);
            }
            return { success: true };
        });
    },

    // 设置帖子置顶加精
    setPostPin(postId, isPinned) {
        return requestJson(`/forum/posts/${postId}/pin?pinned=${isPinned}`, {
            method: 'PUT'
        }, () => {
            const post = mockPosts.value.find(p => p.id === postId);
            if (post) {
                // 如果是置顶加精，可以同步添加到公告栏
                if (isPinned) {
                    const exists = mockAnnouncements.value.some(a => a.id === `ann-post-${post.id}`);
                    if (!exists) {
                        mockAnnouncements.value.unshift({
                            id: `ann-post-${post.id}`,
                            title: `【精华】${post.title}`,
                            date: '置顶'
                        });
                    }
                } else {
                    const annIndex = mockAnnouncements.value.findIndex(a => a.id === `ann-post-${post.id}`);
                    if (annIndex !== -1) {
                        mockAnnouncements.value.splice(annIndex, 1);
                    }
                }
            }
            return { success: true };
        });
    },

    // 获取置顶公告
    getAnnouncements() {
        return requestJson('/forum/announcements', {}, () => {
            return mockAnnouncements.value;
        });
    },

    // 教师发布新公告
    publishAnnouncement(payload) {
        return requestJson('/forum/announcements', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const newAnn = {
                id: `ann-${Date.now()}`,
                title: payload.title,
                date: '刚刚'
            };
            mockAnnouncements.value.unshift(newAnn);

            // 同时自动在论坛的“课程答疑”分类里生成一篇公告贴
            const newPost = {
                id: `post-ann-${Date.now()}`,
                title: payload.title,
                content: payload.content || '系统重要公告，请同学们仔细阅读。',
                author: '系统管理员(教师)',
                avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Admin',
                category: 'qna',
                categoryLabel: '课程答疑',
                tags: ['系统公告'],
                likes: 0,
                isLiked: false,
                views: 1,
                createdAt: '刚刚',
                replies: []
            };
            mockPosts.value.unshift(newPost);
            return newAnn;
        });
    },

    // 获取热词话题
    getHotTopics() {
        return requestJson('/forum/hottopics', {}, () => {
            return mockHotTopics.value;
        });
    },

    // 教师配置调整话题权重
    updateHotTopicWeight(tag, change) {
        return requestJson(`/forum/hottopics/weight`, {
            method: 'PUT',
            body: JSON.stringify({ tag, change })
        }, () => {
            const topic = mockHotTopics.value.find(h => h.tag === tag);
            if (topic) {
                topic.count = Math.max(0, topic.count + change);
            }
            return mockHotTopics.value;
        });
    },

    // 添加新话题
    addHotTopic(tag) {
        return requestJson('/forum/hottopics', {
            method: 'POST',
            body: JSON.stringify({ tag })
        }, () => {
            const exists = mockHotTopics.value.some(h => h.tag === tag);
            if (!exists) {
                mockHotTopics.value.push({ tag, count: 10 });
            }
            return mockHotTopics.value;
        });
    },

    // 删除话题
    deleteHotTopic(tag) {
        return requestJson(`/forum/hottopics?tag=${encodeURIComponent(tag)}`, {
            method: 'DELETE'
        }, () => {
            const index = mockHotTopics.value.findIndex(h => h.tag === tag);
            if (index !== -1) {
                mockHotTopics.value.splice(index, 1);
            }
            return mockHotTopics.value;
        });
    },

    // 获取 AI 导师回复日志
    getAiReplyLogs() {
        return requestJson('/forum/ai-replies/logs', {}, () => {
            return mockAiReplyLogs.value;
        });
    },

    // 教师审核/编辑 AI 导师回帖
    auditAiReply(logId, payload) {
        return requestJson(`/forum/ai-replies/logs/${logId}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        }, () => {
            const log = mockAiReplyLogs.value.find(l => l.id === logId);
            if (log) {
                log.status = payload.status || log.status;
                if (payload.content) {
                    log.content = payload.content;
                    
                    // 同步修改帖子中真实的那个 AI 回复
                    const post = mockPosts.value.find(p => p.id === log.postId);
                    if (post) {
                        const reply = post.replies.find(r => r.id === log.replyId);
                        if (reply) {
                            reply.content = payload.content;
                        }
                    }
                }
            }
            return { success: true };
        });
    }
};
