import request from '../utils/request.js';
import { API_BASE_URL } from '../config/env.js';

const API_BASE = globalThis.window?.REPOSITORY_API_BASE_URL || globalThis.localStorage?.getItem?.('repositoryApiBaseUrl') || API_BASE_URL;

const mockCodeRepositories = {
    value: [
        {
            id: 'algo-visual-lab',
            title: '算法可视化实验室',
            slug: 'algo-visual-lab',
            description: '把排序、图遍历、最短路径做成可交互演示，适合数据结构课程复习。',
            author: '谢生',
            avatar: './assets/agents/codeninja.png',
            language: 'Vue',
            course: '数据结构',
            tags: ['算法', '可视化', '课程项目'],
            collaborators: ['李心悦', '王明'],
            visibility: 'public',
            status: 'active',
            recommendScore: 92,
            giteaOwner: 'campus',
            giteaRepo: 'algo-visual-lab',
            htmlUrl: 'https://gezhisystem.com/gitea/campus/algo-visual-lab',
            cloneUrl: 'https://gezhisystem.com/gitea/campus/algo-visual-lab.git',
            sshUrl: 'ssh://git@gezhisystem.com:2222/campus/algo-visual-lab.git',
            defaultBranch: 'main',
            archiveUrl: 'https://gezhisystem.com/gitea/campus/algo-visual-lab/archive/main.zip',
            readme: '# 算法可视化实验室\n\n面向《数据结构》课程的交互式算法展示项目。\n\n## 功能\n\n- 排序过程逐帧演示\n- BFS / DFS 路径追踪\n- Dijkstra 最短路径对比',
            createdAt: '2026-06-28T09:30:00+08:00',
            updatedAt: '2026-07-01T10:12:00+08:00'
        },
        {
            id: 'mini-compiler-notes',
            title: 'Mini Compiler Notes',
            slug: 'mini-compiler-notes',
            description: '从词法分析到简单中间代码生成的编译原理课程项目。',
            author: '李心悦',
            avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Aneka',
            language: 'Python',
            course: '编译原理',
            tags: ['编译器', 'Python', '实验报告'],
            collaborators: ['赵雷'],
            visibility: 'public',
            status: 'active',
            recommendScore: 81,
            giteaOwner: 'campus',
            giteaRepo: 'mini-compiler-notes',
            htmlUrl: 'https://gezhisystem.com/gitea/campus/mini-compiler-notes',
            cloneUrl: 'https://gezhisystem.com/gitea/campus/mini-compiler-notes.git',
            sshUrl: 'ssh://git@gezhisystem.com:2222/campus/mini-compiler-notes.git',
            defaultBranch: 'main',
            archiveUrl: 'https://gezhisystem.com/gitea/campus/mini-compiler-notes/archive/main.zip',
            readme: '# Mini Compiler Notes\n\n一个用于课程实验的迷你编译器。',
            createdAt: '2026-06-25T19:20:00+08:00',
            updatedAt: '2026-06-30T21:00:00+08:00'
        },
        {
            id: 'rag-course-assistant',
            title: '课程 RAG 助教插件',
            slug: 'rag-course-assistant',
            description: '把课程 PDF 切片、检索、引用来源展示整合成轻量插件。',
            author: '王明',
            avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=Jude',
            language: 'TypeScript',
            course: '人工智能技术',
            tags: ['RAG', 'AI', '知识库'],
            collaborators: ['谢生'],
            visibility: 'public',
            status: 'active',
            recommendScore: 88,
            giteaOwner: 'campus',
            giteaRepo: 'rag-course-assistant',
            htmlUrl: 'https://gezhisystem.com/gitea/campus/rag-course-assistant',
            cloneUrl: 'https://gezhisystem.com/gitea/campus/rag-course-assistant.git',
            sshUrl: 'ssh://git@gezhisystem.com:2222/campus/rag-course-assistant.git',
            defaultBranch: 'main',
            archiveUrl: 'https://gezhisystem.com/gitea/campus/rag-course-assistant/archive/main.zip',
            readme: '# 课程 RAG 助教插件\n\n用于课程知识库检索、引用来源整理和学生侧问答辅助。',
            createdAt: '2026-06-20T15:45:00+08:00',
            updatedAt: '2026-07-01T08:10:00+08:00'
        }
    ]
};

const mockRepositoryStars = {
    value: [
        { id: 'algo-visual-lab:谢生', projectId: 'algo-visual-lab', userId: '谢生', active: true },
        { id: 'algo-visual-lab:李心悦', projectId: 'algo-visual-lab', userId: '李心悦', active: true },
        { id: 'rag-course-assistant:谢生', projectId: 'rag-course-assistant', userId: '谢生', active: true }
    ]
};

const mockRepositoryFavorites = {
    value: [
        { id: 'algo-visual-lab:王明', projectId: 'algo-visual-lab', userId: '王明', active: true },
        { id: 'mini-compiler-notes:谢生', projectId: 'mini-compiler-notes', userId: '谢生', active: true }
    ]
};

const mockRepositoryReports = {
    value: [
        {
            id: 'repo-report-1',
            projectId: 'mini-compiler-notes',
            projectTitle: 'Mini Compiler Notes',
            projectAuthor: '李心悦',
            reporter: '赵雷',
            reason: '版权风险',
            description: '怀疑 README 中引用了未授权实验讲义。',
            status: 'pending',
            createdAt: '2026-07-01T09:40:00+08:00',
            auditedAt: '',
            auditor: '',
            note: ''
        }
    ]
};

function storageUserId() {
    try {
        const user = JSON.parse(globalThis.localStorage?.getItem?.('currentUser') || 'null');
        return user?.username || '';
    } catch {
        return '';
    }
}

function normalizeSlug(value) {
    return String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9._-]+/g, '-')
        .replace(/-{2,}/g, '-')
        .replace(/^[-._]+|[-._]+$/g, '') || 'project';
}

function ensureUniqueSlug(slug) {
    const exists = mockCodeRepositories.value.some((item) => item.slug === slug || item.id === slug);
    return exists ? `${slug}-${Math.random().toString(16).slice(2, 8)}` : slug;
}

function relationKey(projectId, userId) {
    return `${projectId}:${userId || 'anonymous'}`;
}

function countActive(collection, projectId) {
    return collection.value.filter((item) => item.projectId === projectId && item.active).length;
}

function hasActive(collection, projectId, userId) {
    return collection.value.some((item) => item.projectId === projectId && item.userId === userId && item.active);
}

function enrichProject(project, userId = storageUserId()) {
    return {
        ...project,
        webhookConfigured: Boolean(project.webhookConfigured),
        giteaSyncStatus: project.giteaSyncStatus || (project.webhookConfigured ? 'connected' : 'fallback'),
        lastSyncedAt: project.lastSyncedAt || project.updatedAt || project.createdAt || '',
        recentCommits: Array.isArray(project.recentCommits) ? project.recentCommits : [],
        pullRequests: Array.isArray(project.pullRequests) ? project.pullRequests : [],
        gitEvents: Array.isArray(project.gitEvents) ? project.gitEvents : [],
        aiGitCoachFeedback: Array.isArray(project.aiGitCoachFeedback) ? project.aiGitCoachFeedback : [],
        starCount: countActive(mockRepositoryStars, project.id),
        favoriteCount: countActive(mockRepositoryFavorites, project.id),
        isStarred: hasActive(mockRepositoryStars, project.id, userId),
        isFavorited: hasActive(mockRepositoryFavorites, project.id, userId)
    };
}

function wrapStandardDTO(data) {
    return { code: 200, message: 'ok', data };
}

function handleResponseDTO(json) {
    if (json && json.code === 200) return json.data;
    throw new Error(json?.message || '仓库接口请求失败');
}

async function requestJson(path, options = {}, mockFn) {
    const useMockFirst = globalThis.localStorage?.getItem?.('repositoryMockFirst') === 'true';
    if (useMockFirst && typeof mockFn === 'function') {
        return handleResponseDTO(wrapStandardDTO(await mockFn()));
    }

    try {
        const json = await request(`${API_BASE}${path}`, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
        });
        return handleResponseDTO(json);
    } catch (error) {
        if (typeof mockFn === 'function') {
            return handleResponseDTO(wrapStandardDTO(await mockFn(error)));
        }
        throw error;
    }
}

function toggleRelation(collection, projectId, userId) {
    const key = relationKey(projectId, userId);
    const existing = collection.value.find((item) => item.id === key);
    if (existing) {
        existing.active = !existing.active;
    } else {
        collection.value.push({ id: key, projectId, userId, active: true });
    }
    return enrichProject(mockCodeRepositories.value.find((item) => item.id === projectId), userId);
}

export const repositoryApi = {
    getRepositories(params = {}) {
        const query = new URLSearchParams(params).toString();
        return requestJson(`/code-repositories${query ? `?${query}` : ''}`, {}, () => {
            let result = mockCodeRepositories.value.filter((item) => item.status === 'active');
            if (params.q) {
                const keyword = String(params.q).toLowerCase();
                result = result.filter((item) =>
                    item.title.toLowerCase().includes(keyword) ||
                    item.description.toLowerCase().includes(keyword) ||
                    item.tags.join(' ').toLowerCase().includes(keyword)
                );
            }
            if (params.language) {
                result = result.filter((item) => item.language === params.language);
            }
            if (params.tag) {
                result = result.filter((item) => item.tags.includes(params.tag));
            }
            const enriched = result.map((item) => enrichProject(item, params.userId || storageUserId()));
            if (params.sort === 'stars') {
                enriched.sort((a, b) => b.starCount - a.starCount);
            } else if (params.sort === 'favorites') {
                enriched.sort((a, b) => b.favoriteCount - a.favoriteCount);
            } else if (params.sort === 'relevant') {
                enriched.sort((a, b) => ((b.recommendScore || 0) + b.favoriteCount * 5 + b.starCount * 2) - ((a.recommendScore || 0) + a.favoriteCount * 5 + a.starCount * 2));
            } else if (params.sort === 'recommended') {
                enriched.sort((a, b) => b.recommendScore - a.recommendScore);
            } else {
                enriched.sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
            }
            return enriched;
        });
    },

    createRepository(payload) {
        return requestJson('/code-repositories', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const slug = ensureUniqueSlug(normalizeSlug(payload.slug || payload.title));
            const project = {
                id: slug,
                title: payload.title || '未命名项目',
                slug,
                description: payload.description || '',
                author: payload.author || storageUserId() || '匿名同学',
                avatar: payload.avatar || `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(payload.author || slug)}`,
                language: payload.language || 'Other',
                course: payload.course || '',
                tags: payload.tags || [],
                collaborators: payload.collaborators || [],
                visibility: payload.private ? 'private' : 'public',
                status: 'active',
                recommendScore: payload.recommendScore || 0,
                giteaOwner: 'campus',
                giteaRepo: slug,
                htmlUrl: `https://gezhisystem.com/gitea/campus/${slug}`,
                cloneUrl: `https://gezhisystem.com/gitea/campus/${slug}.git`,
                sshUrl: `ssh://git@gezhisystem.com:2222/campus/${slug}.git`,
                defaultBranch: 'main',
                archiveUrl: `https://gezhisystem.com/gitea/campus/${slug}/archive/main.zip`,
                readme: payload.readme || `# ${payload.title || slug}\n\n${payload.description || '这个项目还没有补充 README。'}\n\n## Clone\n\n\`\`\`bash\ngit clone https://gezhisystem.com/gitea/campus/${slug}.git\n\`\`\``,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };
            mockCodeRepositories.value.unshift(project);
            return enrichProject(project, payload.author || storageUserId());
        });
    },

    getRepository(projectId, userId = storageUserId()) {
        return requestJson(`/code-repositories/${projectId}`, {}, () => {
            const project = mockCodeRepositories.value.find((item) => item.id === projectId);
            if (!project) throw new Error('项目不存在');
            return enrichProject(project, userId);
        });
    },

    getDownload(projectId) {
        return requestJson(`/code-repositories/${projectId}/download`, {}, () => {
            const project = mockCodeRepositories.value.find((item) => item.id === projectId);
            if (!project) throw new Error('项目不存在');
            return { downloadUrl: project.archiveUrl, archiveUrl: project.archiveUrl, branch: project.defaultBranch || 'main' };
        });
    },

    getRepositoryTree(projectId, { path = '', ref = '' } = {}) {
        const query = new URLSearchParams();
        if (path) query.set('path', path);
        if (ref) query.set('ref', ref);
        const suffix = query.toString() ? `?${query.toString()}` : '';
        return requestJson(`/code-repositories/${projectId}/tree${suffix}`, {}, () => {
            const rootEntries = [
                { name: 'README.md', path: 'README.md', type: 'file', sha: 'mock-readme', size: 128 },
                { name: 'src', path: 'src', type: 'dir', sha: 'mock-src', size: 0 }
            ];
            const nestedEntries = [
                { name: 'main.py', path: 'src/main.py', type: 'file', sha: 'mock-main', size: 256 }
            ];
            const normalizedPath = String(path || '').trim().replace(/^\/+|\/+$/g, '');
            return {
                projectId,
                path: normalizedPath,
                ref: ref || 'main',
                entries: normalizedPath === 'src' ? nestedEntries : rootEntries
            };
        });
    },

    getRepositoryBlob(projectId, { path = '', ref = '' } = {}) {
        const query = new URLSearchParams();
        query.set('path', path);
        if (ref) query.set('ref', ref);
        return requestJson(`/code-repositories/${projectId}/blob?${query.toString()}`, {}, () => ({
            projectId,
            ref: ref || 'main',
            path,
            name: String(path || '').split('/').pop() || 'file',
            encoding: 'text',
            content: `# Mock preview\n\n${path}\n`,
            size: 64,
            previewable: true
        }));
    },

    getRepositoryLanguages(projectId) {
        return requestJson(`/code-repositories/${projectId}/languages`, {}, () => ([
            { name: 'Vue', bytes: 4500, percent: 45 },
            { name: 'Python', bytes: 3500, percent: 35 },
            { name: 'JavaScript', bytes: 2000, percent: 20 }
        ]));
    },

    toggleStar(projectId, userId = storageUserId() || 'anonymous') {
        return requestJson(`/code-repositories/${projectId}/star`, {
            method: 'POST',
            body: JSON.stringify({ userId })
        }, () => {
            const project = toggleRelation(mockRepositoryStars, projectId, userId);
            return {
                projectId,
                starCount: project.starCount,
                favoriteCount: project.favoriteCount,
                isStarred: project.isStarred,
                isFavorited: project.isFavorited
            };
        });
    },

    toggleFavorite(projectId, userId = storageUserId() || 'anonymous') {
        return requestJson(`/code-repositories/${projectId}/favorite`, {
            method: 'POST',
            body: JSON.stringify({ userId })
        }, () => {
            const project = toggleRelation(mockRepositoryFavorites, projectId, userId);
            return {
                projectId,
                starCount: project.starCount,
                favoriteCount: project.favoriteCount,
                isStarred: project.isStarred,
                isFavorited: project.isFavorited
            };
        });
    },

    reportRepository(projectId, payload) {
        return requestJson(`/code-repositories/${projectId}/reports`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const project = mockCodeRepositories.value.find((item) => item.id === projectId);
            if (!project) throw new Error('项目不存在');
            const report = {
                id: `repo-report-${Date.now()}`,
                projectId,
                projectTitle: project.title,
                projectAuthor: project.author,
                reporter: payload.reporter || storageUserId() || '匿名同学',
                reason: payload.reason || '违规内容',
                description: payload.description || '',
                status: 'pending',
                createdAt: new Date().toISOString(),
                auditedAt: '',
                auditor: '',
                note: ''
            };
            mockRepositoryReports.value.unshift(report);
            return report;
        });
    },

    getReports(params = {}) {
        const query = new URLSearchParams(params).toString();
        return requestJson(`/code-repositories/reports${query ? `?${query}` : ''}`, {}, () => {
            let result = [...mockRepositoryReports.value];
            if (params.status) {
                result = result.filter((item) => item.status === params.status);
            }
            return result;
        });
    },

    auditReport(reportId, payload) {
        return requestJson(`/code-repositories/reports/${reportId}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        }, () => {
            const report = mockRepositoryReports.value.find((item) => item.id === reportId);
            if (!report) throw new Error('举报不存在');
            report.status = payload.action === 'approve_delete' ? 'approved' : 'rejected';
            report.auditor = payload.teacherId || 'teacher';
            report.note = payload.note || '';
            report.auditedAt = new Date().toISOString();
            if (payload.action === 'approve_delete') {
                const project = mockCodeRepositories.value.find((item) => item.id === report.projectId);
                if (project) {
                    project.status = 'removed';
                    project.removedAt = report.auditedAt;
                    project.removeReason = report.note || report.reason;
                }
            }
            return report;
        });
    },

    deleteRepository(projectId, payload = {}) {
        return requestJson(`/code-repositories/${projectId}`, {
            method: 'DELETE',
            body: JSON.stringify(payload)
        }, () => {
            const project = mockCodeRepositories.value.find((item) => item.id === projectId);
            if (!project) throw new Error('项目不存在');
            project.status = 'removed';
            project.removedAt = new Date().toISOString();
            project.removeReason = payload.reason || '教师审核删除';
            return project;
        });
    },

    getUserRepositoryProfile(userId) {
        return requestJson(`/users/${encodeURIComponent(userId)}/code-repositories`, {}, () => {
            const activeProjects = mockCodeRepositories.value.filter((item) => item.status === 'active');
            const starredIds = new Set(mockRepositoryStars.value.filter((item) => item.userId === userId && item.active).map((item) => item.projectId));
            const favoriteIds = new Set(mockRepositoryFavorites.value.filter((item) => item.userId === userId && item.active).map((item) => item.projectId));
            return {
                userId,
                ownProjects: activeProjects.filter((item) => item.author === userId).map((item) => enrichProject(item, userId)),
                collaboratingProjects: activeProjects.filter((item) => (item.collaborators || []).includes(userId)).map((item) => enrichProject(item, userId)),
                starredProjects: activeProjects.filter((item) => starredIds.has(item.id)).map((item) => enrichProject(item, userId)),
                favoriteProjects: activeProjects.filter((item) => favoriteIds.has(item.id)).map((item) => enrichProject(item, userId))
            };
        });
    }
};

export default repositoryApi;

async function parseGiteaResponse(response) {
    const payload = await response.json();
    if (!response.ok) {
        const message = payload?.message || payload?.detail || `Gitea 接口请求失败 (${response.status})`;
        throw new Error(message);
    }
    return payload.data ?? payload;
}

export async function fetchGiteaIdentity() {
    const token = globalThis.localStorage?.getItem?.('token') || globalThis.localStorage?.getItem?.('authToken') || '';
    const response = await fetch(`${API_BASE}/gitea/me`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    return parseGiteaResponse(response);
}

export async function rotateGiteaToken() {
    const token = globalThis.localStorage?.getItem?.('token') || globalThis.localStorage?.getItem?.('authToken') || '';
    const response = await fetch(`${API_BASE}/gitea/token`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    return parseGiteaResponse(response);
}
