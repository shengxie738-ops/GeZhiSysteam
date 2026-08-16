import request from '../utils/request.js';
import { formatCurrentDisplayDateTime, formatDisplayDateTime } from '../utils/timeFormat.js';

const API_BASE = globalThis.window?.TEAM_GIT_API_BASE_URL || globalThis.localStorage?.getItem?.('teamGitApiBaseUrl') || '';
const TIME_FIELD_KEYS = new Set(['createdAt', 'updatedAt', 'lastSyncedAt', 'lastCommitAt', 'lastReminderAt', 'created_at', 'time']);

function nowLabel() {
    return formatCurrentDisplayDateTime();
}

function normalizeDisplayTimes(value) {
    if (Array.isArray(value)) {
        value.forEach(normalizeDisplayTimes);
        return value;
    }
    if (!value || typeof value !== 'object') return value;
    Object.entries(value).forEach(([key, item]) => {
        if (typeof item === 'string' && TIME_FIELD_KEYS.has(key)) {
            value[key] = formatDisplayDateTime(item);
        } else if (item && typeof item === 'object') {
            normalizeDisplayTimes(item);
        }
    });
    return value;
}

function normalizeSlug(value) {
    return String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9._-]+/g, '-')
        .replace(/-{2,}/g, '-')
        .replace(/^[-._]+|[-._]+$/g, '') || 'member';
}

function createMockProject(projectId = 'huffman-coding-team') {
    const repo = {
        repoName: projectId,
        giteaOwner: 'campus',
        htmlUrl: `https://gezhisystem.com/gitea/campus/${projectId}`,
        cloneUrl: `https://gezhisystem.com/gitea/campus/${projectId}.git`,
        sshUrl: `ssh://git@gezhisystem.com:2222/campus/${projectId}.git`,
        defaultBranch: 'main',
        taskBranch: 'feature/huffman-compress',
        status: 'collaborating',
        statusLabel: '协作中',
        webhookConfigured: false,
        lastSyncedAt: '2026-07-02T15:30:00+08:00'
    };
    return {
        id: projectId,
        project: {
            id: projectId,
            title: '哈夫曼压缩与解压引擎',
            course: '数据结构与算法',
            teamName: '极客先锋队',
            description: '基于哈夫曼树完成文本压缩、解压、CLI 集成与测试用例集跑通。',
            leaderId: '张华',
            createdBy: '张华',
            className: '计科 2301'
        },
        repository: repo,
        memberProgress: [
            {
                id: 'liming',
                name: '李明',
                role: '学生',
                task: '编写文本二进制流压缩与解压引擎',
                branch: 'feature/huffman-compress',
                cloneStatus: 'done',
                commitCount: 3,
                pushStatus: 'detected',
                prStatus: 'needs_pr',
                mergeStatus: 'pending',
                statusLabel: 'PR 待创建',
                lastCommitAt: '15:31',
                score: 82,
                contribution: 28,
                progress: 58
            },
            {
                id: 'zhanghua',
                name: '张华',
                role: '队长',
                task: '哈夫曼树节点结构与建树算法设计',
                branch: 'feature/huffman-tree',
                cloneStatus: 'done',
                commitCount: 5,
                pushStatus: 'detected',
                prStatus: 'open',
                mergeStatus: 'pending',
                statusLabel: 'PR 待审核',
                lastCommitAt: '15:26',
                score: 90,
                contribution: 32,
                progress: 74
            },
            {
                id: 'wanglei',
                name: '王磊',
                role: '学生',
                task: '哈夫曼二进制编码生成与字典构建',
                branch: 'feature/code-map',
                cloneStatus: 'done',
                commitCount: 4,
                pushStatus: 'detected',
                prStatus: 'merged',
                mergeStatus: 'merged',
                statusLabel: '已完成',
                lastCommitAt: '15:18',
                score: 94,
                contribution: 35,
                progress: 100
            },
            {
                id: 'alina',
                name: 'Alina AI',
                role: 'AI 协作体',
                task: '集成 CLI 命令行系统与测试用例集跑通',
                branch: 'feature/cli-tests',
                cloneStatus: 'pending',
                commitCount: 0,
                pushStatus: 'pending',
                prStatus: 'not_created',
                mergeStatus: 'pending',
                statusLabel: '未开始',
                lastCommitAt: '-',
                score: 0,
                contribution: 5,
                progress: 8
            }
        ],
        pullRequests: [
            {
                id: 'pr-2',
                number: 2,
                title: 'feat: 完成哈夫曼树建树模块',
                creator: '张华',
                sourceBranch: 'feature/huffman-tree',
                targetBranch: 'main',
                status: 'open',
                statusLabel: 'PR 待审核',
                createdAt: '15:23',
                updatedAt: '15:28',
                url: `${repo.htmlUrl}/pulls/2`
            },
            {
                id: 'pr-1',
                number: 1,
                title: 'feat: 编码字典构建逻辑',
                creator: '王磊',
                sourceBranch: 'feature/code-map',
                targetBranch: 'main',
                status: 'merged',
                statusLabel: '已合并',
                createdAt: '15:04',
                updatedAt: '15:18',
                url: `${repo.htmlUrl}/pulls/1`
            },
            {
                id: 'pr-0',
                number: 0,
                title: 'docs: 初始实验说明草稿',
                creator: 'Alina AI',
                sourceBranch: 'feature/cli-tests',
                targetBranch: 'main',
                status: 'closed',
                statusLabel: '已关闭',
                createdAt: '14:48',
                updatedAt: '14:52',
                url: `${repo.htmlUrl}/pulls/0`
            }
        ],
        recentCommits: [
            { id: 'c-1', author: '李明', branch: 'feature/huffman-compress', message: 'feat: 完成哈夫曼压缩核心逻辑', time: '15:31' },
            { id: 'c-2', author: '张华', branch: 'feature/huffman-tree', message: 'test: 补充建树边界用例', time: '15:26' },
            { id: 'c-3', author: '王磊', branch: 'feature/code-map', message: 'fix: 修复单字符编码边界', time: '15:16' }
        ],
        gitEvents: [
            { id: 'e-1', type: 'push', actor: '李明', text: '李明 推送了 feature/huffman-compress 分支', time: '15:31' },
            { id: 'e-2', type: 'pull_request', actor: '张华', text: '张华 创建了 Pull Request #2', time: '15:23' },
            { id: 'e-3', type: 'merge', actor: '老师', text: '老师合并了 feature/code-map -> main', time: '15:18' },
            { id: 'e-4', type: 'commit', actor: '系统', text: '系统检测到 2 次新提交', time: '15:16' }
        ],
        chatMessages: [
            { id: 1, sender: '张华', content: '我这边的建树算法逻辑已经跑通了。', time: '15:21' },
            { id: 2, sender: '王磊', content: '我的递归字典构建代码在深度比较大时报错了，可能是边界条件没写对。', time: '15:25' }
        ],
        teacherEvaluation: { summary: '', auditor: '', updatedAt: '' },
        updatedAt: nowLabel()
    };
}

const mockProjects = { value: new Map() };

function getMockProject(projectId = 'huffman-coding-team') {
    if (!mockProjects.value.has(projectId)) {
        mockProjects.value.set(projectId, createMockProject(projectId));
    }
    return mockProjects.value.get(projectId);
}

function listMockProjects(viewer = '老师') {
    if (mockProjects.value.size === 0) {
        getMockProject();
    }
    return Array.from(mockProjects.value.values()).map((project) => enrich(project, viewer));
}

function cloneData(data) {
    return JSON.parse(JSON.stringify(data));
}

function statusLabel(status) {
    return {
        not_created: '未创建',
        created: '已创建',
        waiting_upload: '等待上传',
        collaborating: '协作中',
        completed: '已完成'
    }[status] || status || '未知';
}

function languageStats(project) {
    const text = `${project.project?.title || ''} ${project.project?.course || ''}`;
    if (text.includes('Vue') || text.includes('前端')) {
        return [
            { name: 'Vue', percent: 42, color: '#41b883' },
            { name: 'TypeScript', percent: 35, color: '#3178c6' },
            { name: 'Python', percent: 23, color: '#3572A5' }
        ];
    }
    return [
        { name: 'Python', percent: 46, color: '#3572A5' },
        { name: 'JavaScript', percent: 28, color: '#f1e05a' },
        { name: 'Markdown', percent: 26, color: '#083fa1' }
    ];
}

function defaultRepositoryFiles(project) {
    const updatedAt = project.updatedAt || nowLabel();
    return [
        { name: 'backend', type: 'dir', lastCommit: 'feat: 完成后端核心接口', updatedAt },
        { name: 'frontend', type: 'dir', lastCommit: 'feat: 完成仓库主页界面', updatedAt },
        { name: 'docs', type: 'dir', lastCommit: 'docs: 补充项目说明与类图', updatedAt },
        { name: 'README.md', type: 'file', lastCommit: 'docs: 初始化项目 README', updatedAt },
        { name: 'class-diagram.md', type: 'file', lastCommit: 'docs: 添加类图说明', updatedAt }
    ];
}

function defaultRepositoryHome(project) {
    const repo = project.repository || {};
    const projectInfo = project.project || {};
    const repoName = repo.repoName || project.id || 'team-repository';
    const description = projectInfo.description || '团队尚未补充项目介绍。';
    return {
        namespace: repo.giteaOwner || 'campus',
        repoName,
        visibility: 'private',
        course: projectInfo.course || '编程团队实训',
        about: description,
        readme: `# ${projectInfo.title || repoName}\n\n${description}\n\n## 团队协作说明\n\n当前 clone 地址为演示数据，后续接入真实 Gitea 后会替换为真实 cloneUrl。`,
        classDiagram: 'Controller -> Service -> Repository -> DomainRecord',
        teacherComment: '',
        revisionSuggestions: '',
        teacherFeedbackUpdatedAt: '',
        teacherFeedbackUpdatedBy: '',
        cloneUrlMockOnly: true,
        defaultBranch: repo.defaultBranch || 'main',
        cloneUrl: repo.cloneUrl || '',
        sshUrl: repo.sshUrl || '',
        updatedAt: project.updatedAt || nowLabel(),
        languageStats: languageStats(project),
        files: defaultRepositoryFiles(project)
    };
}

function ensureRepositoryHome(project) {
    const explicitCloneUrlMockOnly = project.repositoryHome?.cloneUrlMockOnly;
    const defaults = defaultRepositoryHome(project);
    if (!project.repositoryHome || typeof project.repositoryHome !== 'object') {
        project.repositoryHome = defaults;
        return project.repositoryHome;
    }
    project.repositoryHome = { ...defaults, ...project.repositoryHome };
    project.repositoryHome.repoName = project.repository?.repoName || project.repositoryHome.repoName;
    project.repositoryHome.cloneUrl = project.repository?.cloneUrl || project.repositoryHome.cloneUrl;
    project.repositoryHome.sshUrl = project.repository?.sshUrl || project.repositoryHome.sshUrl;
    project.repositoryHome.defaultBranch = project.repository?.defaultBranch || project.repositoryHome.defaultBranch;
    if (typeof explicitCloneUrlMockOnly === 'boolean') {
        project.repositoryHome.cloneUrlMockOnly = explicitCloneUrlMockOnly;
    } else {
        const cloneUrl = String(project.repositoryHome.cloneUrl || project.repository?.cloneUrl || '');
        project.repositoryHome.cloneUrlMockOnly = !cloneUrl || /(git\.gezhi\.local|git\.gezhisystem\.com|localhost|127\.0\.0\.1)/i.test(cloneUrl);
    }
    return project.repositoryHome;
}

function repositoryCard(project) {
    const repo = project.repository || {};
    const info = project.project || {};
    const members = project.memberProgress || [];
    const openPr = (project.pullRequests || []).find((item) => item.status === 'open');
    const pendingPr = (project.pullRequests || []).find((item) => ['needs_pr', 'pending'].includes(item.status));
    return {
        subjectCategory: info.course || '编程团队实训',
        repoName: repo.repoName || project.id,
        title: info.title || repo.repoName || project.id,
        description: info.description || '',
        leader: info.leaderName || members.find((member) => member.role === '队长')?.name || info.leaderId || info.createdBy || '',
        members: members.map((member) => member.name).filter(Boolean),
        repositoryStatus: repo.statusLabel || statusLabel(repo.status),
        updatedAt: project.updatedAt || repo.lastSyncedAt || '',
        prStatus: openPr?.statusLabel || pendingPr?.statusLabel || (project.pullRequests?.length ? 'PR 已同步' : '暂无 PR')
    };
}

function memberKey(name) {
    return String(name || '').replace(' (你)', '').trim();
}

function findMember(project, userId = '李明') {
    const key = memberKey(userId);
    project.memberProgress = project.memberProgress || [];
    let member = project.memberProgress.find((item) => {
        return memberKey(item.name) === key || memberKey(item.id) === key || memberKey(item.studentId) === key;
    });
    if (!member) {
        member = {
            id: normalizeSlug(key),
            name: key || '匿名成员',
            role: '学生',
            task: project.project.title,
            branch: project.repository.taskBranch,
            cloneStatus: 'pending',
            commitCount: 0,
            pushStatus: 'pending',
            prStatus: 'not_created',
            mergeStatus: 'pending',
            statusLabel: '未开始',
            lastCommitAt: '-',
            score: 0,
            contribution: 0,
            progress: 0
        };
        project.memberProgress.push(member);
    }
    return member;
}

function workflowSteps(repo, member = null) {
    const cloneDone = member?.cloneStatus === 'done';
    const pushDone = ['detected', 'done'].includes(member?.pushStatus);
    const prOpen = ['open', 'merged'].includes(member?.prStatus);
    const merged = member?.mergeStatus === 'merged';
    const htmlUrl = String(repo.htmlUrl || '').replace(/\/$/, '');
    return [
        {
            id: 'clone',
            title: '拉取代码',
            description: '复制仓库地址，在本地终端完成项目初始化。',
            command: `git clone ${repo.cloneUrl}`,
            status: cloneDone ? 'done' : 'current',
            statusLabel: cloneDone ? '已拉取' : '待确认',
            nextHint: '拉取后点击“我已完成拉取”。'
        },
        {
            id: 'branch',
            title: '创建功能分支',
            description: '进入项目目录，为当前任务建立独立分支。',
            command: `cd ${repo.repoName}\ngit checkout -b ${repo.taskBranch}`,
            status: pushDone || prOpen || merged ? 'done' : (cloneDone ? 'current' : 'locked'),
            statusLabel: cloneDone ? '已准备' : '等待 clone',
            nextHint: '分支创建后即可提交代码。'
        },
        {
            id: 'commit',
            title: '提交代码',
            description: '把本地改动提交到任务分支，commit message 要说明实现内容。',
            command: 'git add .\ngit commit -m "feat: 完成哈夫曼压缩核心逻辑"',
            status: pushDone || prOpen || merged ? 'done' : (cloneDone ? 'current' : 'locked'),
            statusLabel: pushDone ? '已提交' : '待提交',
            nextHint: '提交后推送到 Gitea。'
        },
        {
            id: 'push',
            title: '推送代码',
            description: '推送任务分支，系统后续通过 Gitea Webhook 检测 push。',
            command: `git push -u origin ${repo.taskBranch}`,
            status: pushDone || prOpen || merged ? 'done' : (cloneDone ? 'current' : 'locked'),
            statusLabel: pushDone ? '已检测' : '等待系统检测',
            nextHint: 'push 后刷新状态，等待系统检测。'
        },
        {
            id: 'pull_request',
            title: '发起 Pull Request',
            description: '进入 Gitea 原生 PR 页面，把任务分支合并到主分支。',
            command: `${htmlUrl}/pulls/new?head=${repo.taskBranch}&base=${repo.defaultBranch}`,
            status: prOpen || merged ? 'done' : (pushDone ? 'current' : 'locked'),
            statusLabel: prOpen ? 'PR 已创建' : 'PR 待创建',
            nextHint: '创建 PR 后等待老师或队长审核。'
        },
        {
            id: 'merge',
            title: '等待审核合并',
            description: '老师或队长在 Gitea 审核并合并后，页面同步任务完成状态。',
            command: `git pull origin ${repo.defaultBranch}`,
            status: merged ? 'done' : (prOpen ? 'current' : 'locked'),
            statusLabel: merged ? '已合并' : '等待审核',
            nextHint: '合并后团队进度与得分会自动更新。'
        }
    ];
}

function teamSummary(project) {
    const members = project.memberProgress || [];
    const prs = project.pullRequests || [];
    const completedMembers = members.filter((item) => item.mergeStatus === 'merged').length;
    const pushedMembers = members.filter((item) => ['detected', 'done'].includes(item.pushStatus)).length;
    const unsubmittedMembers = members.filter((item) => !['detected', 'done'].includes(item.pushStatus)).length;
    const openPullRequests = prs.filter((item) => item.status === 'open').length;
    const averageProgress = Math.round(members.reduce((sum, item) => sum + Number(item.progress || 0), 0) / Math.max(members.length, 1));
    const contributionRanking = [...members]
        .map((item) => ({
            id: item.id || item.studentId || item.name,
            name: item.name,
            studentId: item.studentId || item.id || '',
            role: item.role || '',
            task: item.task || '',
            progress: Number(item.progress || 0),
            commitCount: Number(item.commitCount || 0),
            prCount: Number(item.prCount || 0),
            mergedPrCount: Number(item.mergedPrCount || 0),
            contribution: Number(item.contribution || 0),
            score: Number(item.score || 0),
            source: item.source || project.repository?.prSource || 'local'
        }))
        .sort((a, b) => b.contribution - a.contribution);
    return {
        totalMembers: members.length,
        completedMembers,
        pushedMembers,
        unsubmittedMembers,
        openPullRequests,
        averageProgress,
        contributionRanking
    };
}

function mergeTeamSummary(project, computed) {
    const backend = project.teamSummary && typeof project.teamSummary === 'object' ? project.teamSummary : null;
    if (!backend) return computed;
    return {
        ...computed,
        ...backend,
        contributionRanking: Array.isArray(backend.contributionRanking) && backend.contributionRanking.length > 0
            ? backend.contributionRanking.map((item) => ({
                id: item.id || item.studentId || item.name,
                name: item.name,
                studentId: item.studentId || item.id || '',
                role: item.role || '',
                task: item.task || '',
                progress: Number(item.progress || 0),
                commitCount: Number(item.commitCount || 0),
                prCount: Number(item.prCount || 0),
                mergedPrCount: Number(item.mergedPrCount || 0),
                contribution: Number(item.contribution || 0),
                score: Number(item.score || 0),
                source: item.source || backend.source || 'backend'
            }))
            : computed.contributionRanking
    };
}

function currentUserProgress(project, viewer = '李明') {
    const member = findMember(project, viewer);
    let nextHint = '先复制 clone 命令并在本地拉取仓库。';
    if (member.mergeStatus === 'merged') {
        nextHint = '任务已完成，等待教师汇总评分。';
    } else if (member.prStatus === 'open') {
        nextHint = '等待老师或队长审核 PR。';
    } else if (['detected', 'done'].includes(member.pushStatus)) {
        nextHint = '系统已检测到 push，请前往 Gitea 创建 Pull Request。';
    } else if (member.cloneStatus === 'done') {
        nextHint = '完成提交并推送后，等待系统检测 push 事件。';
    }
    return {
        userId: viewer,
        member,
        nextHint,
        score: member.score || 0
    };
}

function enrich(project, viewer = '李明') {
    const copy = cloneData(project);
    copy.memberProgress = copy.memberProgress || [];
    copy.pullRequests = copy.pullRequests || [];
    const member = findMember(copy, viewer);
    copy.repository = copy.repository || {};
    copy.repository.statusLabel = statusLabel(copy.repository.status);
    ensureRepositoryHome(copy);
    copy.repositoryCard = repositoryCard(copy);
    copy.workflowSteps = workflowSteps(copy.repository, member);
    copy.currentUserProgress = currentUserProgress(copy, viewer);
    const computedSummary = teamSummary(copy);
    copy.teamSummary = mergeTeamSummary(copy, computedSummary);
    return normalizeDisplayTimes(copy);
}

function appendEvent(project, type, actor, text) {
    project.gitEvents.unshift({
        id: `event-${Date.now()}-${type}`,
        type,
        actor,
        text,
        time: nowLabel()
    });
}

function createMockCollaborationProject(payload = {}) {
    const title = payload.title || '团队协作实训项目';
    const teamName = payload.teamName || `${payload.actor || payload.leaderId || '队长'}的小组`;
    const leaderId = payload.leaderId || payload.actor || '队长';
    const projectId = normalizeSlug(payload.id || payload.projectId || payload.slug || `${teamName}-${title}`);
    const repo = {
        repoName: normalizeSlug(payload.repoName || projectId),
        giteaOwner: 'campus',
        htmlUrl: `https://gezhisystem.com/gitea/campus/${normalizeSlug(payload.repoName || projectId)}`,
        cloneUrl: `https://gezhisystem.com/gitea/campus/${normalizeSlug(payload.repoName || projectId)}.git`,
        sshUrl: `ssh://git@gezhisystem.com:2222/campus/${normalizeSlug(payload.repoName || projectId)}.git`,
        defaultBranch: 'main',
        taskBranch: 'feature/team-start',
        status: 'not_created',
        statusLabel: '未创建',
        webhookConfigured: false,
        lastSyncedAt: nowLabel()
    };
    const memberNames = Array.isArray(payload.members) && payload.members.length > 0
        ? payload.members.map((item) => typeof item === 'string' ? item : item.name || item.memberId).filter(Boolean)
        : [leaderId, '李明', '王磊'];
    if (!memberNames.includes(leaderId)) memberNames.unshift(leaderId);
    const tasks = Array.isArray(payload.tasks) ? payload.tasks : [];
    const members = memberNames.map((name) => {
        const task = tasks.find((item) => [item.memberId, item.member, item.assignee, item.name].includes(name));
        return {
            id: normalizeSlug(name),
            name,
            role: name === leaderId ? '队长' : '学生',
            task: task?.task || task?.title || title,
            branch: task?.branch || `feature/${normalizeSlug(name)}`,
            cloneStatus: 'pending',
            commitCount: 0,
            pushStatus: 'pending',
            prStatus: 'not_created',
            mergeStatus: 'pending',
            statusLabel: '未开始',
            lastCommitAt: '-',
            score: 0,
            contribution: 0,
            progress: name === leaderId ? 12 : 0,
            reminderCount: 0,
            lastReminderAt: ''
        };
    });
    const project = {
        id: projectId,
        project: {
            id: projectId,
            title,
            course: payload.course || '编程团队实训',
            teamName,
            description: payload.description || '队长尚未补充项目介绍。',
            leaderId,
            teacherId: payload.teacherId || '',
            className: payload.className || payload.class_name || '计科 2301',
            status: 'active',
            createdBy: payload.actor || leaderId,
            createdAt: nowLabel()
        },
        repository: repo,
        memberProgress: members,
        pullRequests: [],
        recentCommits: [],
        gitEvents: [],
        chatMessages: [
            { id: 1, sender: payload.actor || leaderId, content: `团队项目「${title}」已创建，请各成员按照任务分支推进。`, time: nowLabel() }
        ],
        reminders: [],
        teacherEvaluation: { summary: '', auditor: '', updatedAt: '' },
        updatedAt: nowLabel()
    };
    ensureRepositoryHome(project);
    appendEvent(project, 'project_created', payload.actor || leaderId, `${payload.actor || leaderId} 创建了团队协作项目 ${title}`);
    mockProjects.value.set(projectId, project);
    return project;
}

function wrapStandardDTO(data) {
    return { code: 200, message: 'ok', data };
}

function handleResponseDTO(json) {
    if (json && json.code === 200) return normalizeDisplayTimes(json.data);
    throw new Error(json?.message || '团队协作 Git 接口请求失败');
}

async function requestJson(path, options = {}, mockFn, { allowMockFallback = true } = {}) {
    const useMockFirst = globalThis.localStorage?.getItem?.('teamGitMockFirst') === 'true';
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
        if (allowMockFallback && typeof mockFn === 'function') {
            return handleResponseDTO(wrapStandardDTO(await mockFn(error)));
        }
        throw error;
    }
}

const MOCK_CLASS_STUDENTS = [
    { username: 'zhanghua', name: '张华', studentId: '20230001', className: '计科 2301', source: 'mock' },
    { username: 'liming', name: '李明', studentId: '20230002', className: '计科 2301', source: 'mock' },
    { username: 'wanglei', name: '王磊', studentId: '20230003', className: '计科 2301', source: 'mock' },
    { username: 'zhaolei', name: '赵雷', studentId: '20230004', className: '计科 2301', source: 'mock' },
    { username: 'chensisi', name: '陈思思', studentId: '20230005', className: '计科 2301', source: 'mock' }
];

export const teamGitApi = {
    listProjects(params = {}) {
        const query = new URLSearchParams(params).toString();
        return requestJson(`/team-git/projects${query ? `?${query}` : ''}`, {}, () => {
            return listMockProjects(params.viewer || '老师');
        }, { allowMockFallback: false }).then((projects) => {
            return (projects || []).map((project) => enrich(project, params.viewer || '李明'));
        }).then((home) => normalizeDisplayTimes(home));
    },

    createProject(payload = {}) {
        return requestJson('/team-git/projects', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            return enrich(createMockCollaborationProject(payload), payload.actor || payload.leaderId || '队长');
        });
    },

    deleteProject(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}`, {
            method: 'DELETE',
            body: JSON.stringify(payload)
        }, () => {
            const deleted = mockProjects.value.delete(projectId);
            return { id: projectId, deleted };
        });
    },

    getProjectDetail(projectId = 'huffman-coding-team', params = {}) {
        const query = new URLSearchParams();
        Object.entries(params || {}).forEach(([key, value]) => {
            if (value === undefined || value === null || value === '') return;
            query.set(key, String(value));
        });
        const suffix = query.toString() ? `?${query.toString()}` : '';
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}${suffix}`, {}, () => {
            return getMockProject(projectId);
        }, { allowMockFallback: false }).then((detail) => enrich(detail, params.viewer || '李明'));
    },

    getRepositoryHome(projectId = 'huffman-coding-team', params = {}) {
        const query = new URLSearchParams(params).toString();
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/repository-home${query ? `?${query}` : ''}`, {}, () => {
            const project = getMockProject(projectId);
            const home = ensureRepositoryHome(project);
            return {
                ...cloneData(home),
                project: cloneData(project.project),
                repository: cloneData(project.repository),
                memberProgress: cloneData(project.memberProgress),
                pullRequests: cloneData(project.pullRequests),
                teamSummary: teamSummary(project)
            };
        }, { allowMockFallback: false }).then((home) => {
            if (home && home.repositoryHome) {
                const { repositoryHome, ...rest } = home;
                return {
                    ...repositoryHome,
                    ...rest
                };
            }
            return home;
        }).then((home) => normalizeDisplayTimes(home));
    },

    getRepositoryTree(projectId = 'huffman-coding-team', { path = '', ref = '' } = {}) {
        const query = new URLSearchParams();
        if (path) query.set('path', path);
        if (ref) query.set('ref', ref);
        const suffix = query.toString() ? `?${query.toString()}` : '';
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/tree${suffix}`, {}, () => {
            const project = getMockProject(projectId);
            const home = ensureRepositoryHome(project);
            const rootEntries = (home.files || []).map((file) => ({
                name: file.name,
                path: file.name,
                type: file.type === 'dir' ? 'dir' : 'file',
                sha: `mock-${file.name}`,
                size: file.type === 'dir' ? 0 : 128
            }));
            const normalizedPath = String(path || '').trim().replace(/^\/+|\/+$/g, '');
            const nestedEntries = normalizedPath === 'backend'
                ? [{ name: 'main.py', path: 'backend/main.py', type: 'file', sha: 'mock-main', size: 256 }]
                : normalizedPath === 'frontend'
                    ? [{ name: 'app.ts', path: 'frontend/app.ts', type: 'file', sha: 'mock-app', size: 320 }]
                    : [];
            return {
                projectId,
                path: normalizedPath,
                ref: ref || home.defaultBranch || 'main',
                entries: nestedEntries.length ? nestedEntries : rootEntries
            };
        }, { allowMockFallback: false });
    },

    getBranches(projectId = 'huffman-coding-team') {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/branches`, {}, () => [
            { name: 'main', commitSha: 'mock-main', protected: false, default: true }
        ], { allowMockFallback: false });
    },

    getRepositoryBlob(projectId = 'huffman-coding-team', { path = '', ref = '' } = {}) {
        const query = new URLSearchParams();
        query.set('path', path);
        if (ref) query.set('ref', ref);
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/blob?${query.toString()}`, {}, () => {
            const project = getMockProject(projectId);
            const home = ensureRepositoryHome(project);
            const fileName = String(path || '').split('/').pop() || 'file';
            const readme = home.readme || `# ${home.repoName || projectId}\n\n演示文件预览。`;
            return {
                projectId,
                ref: ref || home.defaultBranch || 'main',
                path,
                name: fileName,
                encoding: 'text',
                content: fileName.toLowerCase().includes('readme') ? readme : `# Mock preview\n\n${path}\n`,
                size: 128,
                previewable: true
            };
        }, { allowMockFallback: false });
    },

    getRepositoryLanguages(projectId = 'huffman-coding-team') {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/languages`, {}, () => {
            const project = getMockProject(projectId);
            const home = ensureRepositoryHome(project);
            return (home.languageStats || []).map((item) => ({
                name: item.name,
                bytes: Math.round(Number(item.percent || 0) * 100),
                percent: Number(item.percent || 0)
            }));
        }, { allowMockFallback: false });
    },

    updateRepositoryFeedback(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/repository-feedback`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            const home = ensureRepositoryHome(project);
            home.teacherComment = payload.teacherComment || '';
            home.revisionSuggestions = payload.revisionSuggestions || '';
            home.teacherFeedbackUpdatedAt = nowLabel();
            home.teacherFeedbackUpdatedBy = payload.actor || payload.teacherId || 'teacher';
            home.updatedAt = home.teacherFeedbackUpdatedAt;
            appendEvent(project, 'repository_feedback_updated', home.teacherFeedbackUpdatedBy, '教师更新了仓库主页评语与修改建议');
            return normalizeDisplayTimes(cloneData(home));
        }).then((home) => normalizeDisplayTimes(home));
    },

    searchMembers(params = {}) {
        const query = new URLSearchParams(params).toString();
        return requestJson(`/team-git/members/search${query ? `?${query}` : ''}`, {}, () => {
            const keyword = String(params.keyword || '').trim();
            const lowered = keyword.toLowerCase();
            const className = params.className || params.class_name || '';
            if (!keyword) return [];
            return MOCK_CLASS_STUDENTS.filter((item) => {
                const inClass = !className || item.className === className;
                const matched = item.studentId.includes(keyword) || item.name.includes(keyword) || item.username.includes(lowered);
                return inClass && matched;
            }).slice(0, 8);
        });
    },

    updateProject(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}`, {
            method: 'PATCH',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            project.project = { ...project.project, ...payload };
            appendEvent(project, 'project_updated', payload.actor || '队长', `${payload.actor || '队长'} 更新了项目资料`);
            return enrich(project, payload.actor || '队长');
        });
    },

    createRepository(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/repository`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            project.repository.status = 'created';
            project.repository.statusLabel = '已创建';
            project.repository.webhookConfigured = true;
            project.repository.lastSyncedAt = nowLabel();
            ensureRepositoryHome(project);
            appendEvent(project, 'repository_created', payload.actor || '老师', `${payload.actor || '老师'} 创建了 Gitea 仓库 ${project.repository.repoName}`);
            return enrich(project, payload.actor || 'teacher');
        });
    },

    bindRepository(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/repository/bind`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            project.repository = {
                ...project.repository,
                repoName: payload.repoName || project.repository.repoName,
                htmlUrl: payload.htmlUrl || project.repository.htmlUrl,
                cloneUrl: payload.cloneUrl || project.repository.cloneUrl,
                sshUrl: payload.sshUrl || project.repository.sshUrl,
                status: 'created',
                statusLabel: '已创建',
                lastSyncedAt: nowLabel()
            };
            ensureRepositoryHome(project);
            appendEvent(project, 'repository_bound', payload.actor || '老师', `${payload.actor || '老师'} 绑定了已有仓库 ${project.repository.repoName}`);
            return enrich(project, payload.actor || 'teacher');
        });
    },

    assignMemberTask(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/tasks`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            const member = findMember(project, payload.memberId || payload.member || payload.assignee);
            member.task = payload.task || payload.title || member.task;
            member.branch = payload.branch || member.branch;
            member.statusLabel = '已分配';
            member.progress = Math.max(Number(member.progress || 0), 10);
            appendEvent(project, 'task_assigned', payload.actor || '队长', `${payload.actor || '队长'} 将「${member.task}」分配给 ${member.name}`);
            return enrich(project, payload.actor || '队长');
        }, { allowMockFallback: false });
    },

    remindMembers(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/reminders`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            const ids = Array.isArray(payload.memberIds) && payload.memberIds.length > 0
                ? payload.memberIds
                : project.memberProgress
                    .filter((member) => member.pushStatus !== 'detected' || ['not_created', 'needs_pr'].includes(member.prStatus))
                    .map((member) => member.name);
            const message = payload.message || '请尽快完成本地提交、push 并创建 Pull Request。';
            project.reminders = project.reminders || [];
            ids.forEach((memberId) => {
                const member = findMember(project, memberId);
                member.reminderCount = Number(member.reminderCount || 0) + 1;
                member.lastReminderAt = nowLabel();
                project.reminders.unshift({
                    id: `reminder-${Date.now()}-${normalizeSlug(memberId)}`,
                    memberId: member.id,
                    memberName: member.name,
                    message,
                    actor: payload.actor || '队长',
                    createdAt: nowLabel(),
                    status: 'sent'
                });
                project.chatMessages.push({ id: Date.now(), sender: payload.actor || '队长', content: `@${member.name} ${message}`, time: nowLabel() });
            });
            appendEvent(project, 'member_reminded', payload.actor || '队长', `${payload.actor || '队长'} 提醒了 ${ids.length} 位未提交成员`);
            return enrich(project, payload.actor || '队长');
        });
    },

    confirmClone(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/clone-confirmation`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            const userId = payload.userId || '李明';
            const member = findMember(project, userId);
            member.cloneStatus = 'done';
            member.statusLabel = member.pushStatus === 'detected' ? member.statusLabel : '已拉取';
            member.progress = Math.max(Number(member.progress || 0), 35);
            appendEvent(project, 'clone_confirmed', userId, `${userId} 已确认完成 clone 拉取`);
            return enrich(project, userId);
        });
    },

    refreshStatus(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/refresh`, {
            method: 'POST',
            body: JSON.stringify(payload || {})
        }, () => {
            const project = getMockProject(projectId);
            project.repository.lastSyncedAt = nowLabel();
            project.repository.syncError = '';
            appendEvent(project, 'gitea_synced', payload.actor || '系统', `${payload.actor || '系统'} 从 Gitea 同步了 PR/提交/任务`);
            return enrich(project, payload.actor || '李明');
        }, { allowMockFallback: false });
    },

    reviewPullRequest(projectId = 'huffman-coding-team', prNumber, payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/pull-requests/${encodeURIComponent(prNumber)}/review`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            let pr = project.pullRequests.find((item) => Number(item.number) === Number(prNumber));
            if (!pr) {
                pr = {
                    id: `pr-${prNumber}`,
                    number: Number(prNumber),
                    title: `Pull Request #${prNumber}`,
                    creator: payload.creator || '李明',
                    sourceBranch: payload.sourceBranch || project.repository.taskBranch,
                    targetBranch: project.repository.defaultBranch,
                    status: 'open',
                    statusLabel: 'PR 待审核',
                    createdAt: nowLabel(),
                    updatedAt: nowLabel(),
                    url: `${project.repository.htmlUrl}/pulls/${prNumber}`
                };
                project.pullRequests.unshift(pr);
            }
            if (['leader_approve', 'recommend_merge'].includes(payload.action)) {
                pr.leaderReviewStatus = 'recommended';
                pr.leaderReviewer = payload.actor || '队长';
                pr.statusLabel = '队长建议合并';
                appendEvent(project, 'pr_recommended', payload.actor || '队长', `${payload.actor || '队长'} 初审 PR #${prNumber} 并建议合并`);
            } else if (['teacher_approve', 'teacher_merge', 'merge', 'approve_merge', 'leader_merge'].includes(payload.action)) {
                if (['approve_merge', 'leader_merge'].includes(payload.action)) {
                    pr.leaderReviewStatus = 'approved';
                    pr.leaderReviewer = payload.actor || '队长';
                } else {
                    pr.teacherReviewStatus = 'approved';
                    pr.teacherReviewer = payload.actor || '老师';
                }
                pr.status = 'merged';
                pr.statusLabel = '已合并';
                const member = findMember(project, pr.creator);
                member.prStatus = 'merged';
                member.mergeStatus = 'merged';
                member.statusLabel = '已完成';
                member.progress = 100;
                member.score = Math.max(Number(member.score || 0), 96);
                appendEvent(project, 'pr_merged', payload.actor || '审核人', `${payload.actor || '审核人'} 审核并合并 PR #${prNumber}`);
            } else {
                pr.statusLabel = payload.action === 'teacher_reject' ? '教师要求修改' : '队长要求修改';
                pr.reviewComment = payload.comment || '';
                appendEvent(project, 'pr_changes_requested', payload.actor || '审核人', `${payload.actor || '审核人'} 要求 PR #${prNumber} 修改`);
            }
            pr.reviewComment = payload.comment || pr.reviewComment || '';
            pr.updatedAt = nowLabel();
            return enrich(project, payload.actor || '审核人');
        }, { allowMockFallback: false });
    },

    evaluateContribution(projectId = 'huffman-coding-team', payload = {}) {
        return requestJson(`/team-git/projects/${encodeURIComponent(projectId)}/contribution-evaluation`, {
            method: 'POST',
            body: JSON.stringify(payload)
        }, () => {
            const project = getMockProject(projectId);
            (payload.scores || []).forEach((item) => {
                const member = findMember(project, item.memberId || item.name);
                if (item.score !== undefined) member.score = Number(item.score || 0);
                if (item.contribution !== undefined) member.contribution = Number(item.contribution || 0);
                if (item.comment !== undefined) member.teacherComment = item.comment || '';
            });
            project.teacherEvaluation = {
                summary: payload.summary || '',
                auditor: payload.actor || payload.teacherId || '老师',
                updatedAt: nowLabel()
            };
            appendEvent(project, 'contribution_evaluated', payload.actor || '老师', `${payload.actor || '老师'} 评价了团队贡献度`);
            return enrich(project, payload.actor || '老师');
        });
    }
};

export default teamGitApi;
