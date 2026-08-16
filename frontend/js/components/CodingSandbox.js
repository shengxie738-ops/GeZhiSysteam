import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { codingProblems } from '../data/mockData.js?v=20260620';
import { problemReviews } from '../data/aiTemplates.js?v=20260620';

import { homeworkApi } from '../api/homework.js';
import { profileApi } from '../api/profileApi.js';
import { teamGitApi } from '../api/teamGit.js';
import { fetchGiteaIdentity, rotateGiteaToken } from '../api/repository.js';
import { rankedApi } from '../api/ranked.js';
import request from '../utils/request.js';
import { formatDisplayDateTime } from '../utils/timeFormat.js';
import RadarChart from './RadarChart.js';

export default {
    name: 'CodingSandbox',
    components: {
        RadarChart
    },
    props: {
        currentUser: { type: Object, default: null },
        agentConfig: { type: Object, default: null },
        rankedCoachConfig: { type: Object, default: null }
    },
    emits: ['show-toast'],
    setup(props, { emit }) {
        const problems = ref(codingProblems);
        const selectedProblemId = ref(codingProblems[0].id);

        const codingMode = ref(null); // null (大厅), 'practice' (个人练习), 'homework' (编程作业), 'collab' (协同实训)

        // 编程作业区状态
        const homeworkList = ref([]);
        const selectedHomeworkId = ref('');
        const selectedHomework = computed(() => {
            return homeworkList.value.find(h => h.id === selectedHomeworkId.value) || null;
        });
        const currentHomeworkQuestion = computed(() => {
            if (!selectedHomework.value) return null;
            return selectedHomework.value.questions.find(q => q.type === 'programming') || null;
        });
        const activeHomeworkConsoleLogs = ref([]);
        const homeworkCode = ref('');
        const runHomeworkTesting = ref(false);
        const submitHomeworkLoading = ref(false);
        const homeworkDiagnosis = ref(null);
        const homeworkRadarOption = ref(null);

        const loadHomeworkData = async () => {
            const username = props.currentUser?.username || 'guest_user';
            try {
                const list = await homeworkApi.getStudentHomeworkList(username);
                homeworkList.value = list || [];
                if (homeworkList.value.length > 0) {
                    selectedHomeworkId.value = homeworkList.value[0].id;
                }
            } catch (err) {
                console.error("加载作业列表失败:", err);
            }
        };

        const handleHomeworkChange = () => {
            activeHomeworkConsoleLogs.value = [];
            homeworkDiagnosis.value = null;
            homeworkRadarOption.value = null;
            const hw = selectedHomework.value;
            if (hw && currentHomeworkQuestion.value) {
                const q = currentHomeworkQuestion.value;
                const savedCode = localStorage.getItem(`homework_code_${hw.id}_${q.id}`);
                homeworkCode.value = savedCode || q.starterCode || `function solve() {\n\n}`;
                if (monacoEditor && codingMode.value === 'homework') {
                    monacoEditor.setValue(homeworkCode.value);
                }
            }
        };
        watch(selectedHomeworkId, handleHomeworkChange);

        // 团队协作实训区状态
        const teamInfo = ref({ name: '极客先锋队', project: '基于哈夫曼树的文本压缩系统' });
        const teamMembers = ref([
            { name: '李明 (你)', progress: 85, avatar: 'Felix', role: '核心算法研发', status: 'online' },
            { name: '张华', progress: 92, avatar: 'Jack', role: '系统集成与测试', status: 'online' },
            { name: '王磊', progress: 65, avatar: 'Jude', role: 'I/O 与文件读写', status: 'online' },
            { name: 'Alina (AI)', progress: 78, avatar: 'Luna', role: '主规划与评测哨兵', status: 'online' }
        ]);
        const kanbanTasks = ref([
            { id: 1, title: '哈夫曼树节点结构与建树算法设计', assignee: '张华', status: 'completed', code: '// Huffman Node Build\nclass HuffmanNode {\n  constructor(char, freq) {\n    this.char = char;\n    this.freq = freq;\n    this.left = null;\n    this.right = null;\n  }\n}' },
            { id: 2, title: '哈夫曼二进制编码生成与字典构建', assignee: '王磊', status: 'failed', code: '// Code Dictionary Build\nfunction buildCodeMap(root, map = {}, code = "") {\n  if (!root) return;\n  if (!root.left && !root.right) {\n    map[root.char] = code;\n  }\n  buildCodeMap(root.left, map, code + "0");\n  buildCodeMap(root.right, map, code + "1");\n}' },
            { id: 3, title: '编写文本二进制流压缩与解压引擎', assignee: '李明 (你)', status: 'doing', code: `// Binary Compressor & Decompressor Engine\n// 请实现 huffmanCompress(text) 函数，返回压缩后的二进制位流字符串以及编码字典\nfunction huffmanCompress(text) {\n  if (!text) return { bitStream: "", codeMap: {} };\n  \n  // 1. 统计频率\n  const freqs = {};\n  for (let c of text) {\n    freqs[c] = (freqs[c] || 0) + 1;\n  }\n  \n  // 2. 模拟压缩逻辑\n  const codeMap = {};\n  let i = 0;\n  for (let c in freqs) {\n    codeMap[c] = "0".repeat(i) + "1";\n    i++;\n  }\n  \n  let bitStream = "";\n  for (let c of text) {\n    bitStream += codeMap[c];\n  }\n  \n  console.log("[Console] Huffman压缩运行完成！");\n  console.log("[Console] 位流长度为: " + bitStream.length + " bits");\n  return { bitStream, codeMap };\n}` },
            { id: 4, title: '集成 CLI 命令行系统与测试用例集跑通', assignee: 'Alina (AI)', status: 'pending', code: '// CLI Integration' }
        ]);
        const collabLogs = ref([
            { time: '15:20', text: '张华 跑通了“建树算法设计”测试用例，并提交了节点代码' },
            { time: '15:24', text: '王磊 在“编码生成与字典构建”测试用例评测中未通过，抛出 StackOverflowError' }
        ]);
        const chatInput = ref('');
        const chatMessages = ref([
            { id: 1, sender: '张华', content: '我这边的建树算法逻辑已经跑通了。', time: '15:21' },
            { id: 2, sender: '王磊', content: '我的递归字典构建代码在深度比较大时报错了，可能是边界条件没写对。', time: '15:25' }
        ]);
        const isPairBotThinking = ref(false);
        const selectedCollabTaskId = ref(3); // 默认选中李明正在编写的任务
        const collabProjectId = ref('huffman-coding-team');
        const collabData = ref(null);
        const collabLoading = ref(false);
        const collabError = ref('');
        const collabActionLoading = ref('');
        const collabViewMode = ref('list');
        const collabProjects = ref([]);
        const repositoryHome = ref(null);
        const repositoryHomeTab = ref('code');
        const collabMemberKeyword = ref('');
        const collabMemberSearchResults = ref([]);
        const collabSelectedMembers = ref([]);
        const collabCreateOpen = ref(false);
        const collabCreateForm = ref({
            title: '校园算法协作平台',
            course: '软件工程综合实训',
            className: '计科 2301',
            repoName: 'campus-algorithm-collab',
            teamName: '极客先锋队',
            description: '参考 GitHub flow 完成多人分支开发、Pull Request 初审与教师端合并评价。',
            members: '张华, 李明, 王磊'
        });
        const assigningMemberName = ref('');
        const assignTaskForm = ref({ task: '', branch: '' });
        const teamGiteaIdentity = ref(null);
        const teamGeneratedToken = ref('');
        const teamTokenWarning = ref('');
        const teamIdentityLoading = ref(false);
        const copiedTeamToken = ref(false);
        const copiedTeamGitConfigAll = ref(false);
        const copiedTeamGitConfigLine = ref('');
        const copiedTeamAuthClone = ref(false);
        const teamCloneMode = ref('token');
        const reminderMessage = ref('今晚 22:00 前请完成 push 并创建 Pull Request，队长会先做代码初审。');
        const prReviewComment = ref('本地测试通过，代码结构清晰，建议教师合并。');

        // 竞技排位赛区状态
        const rankedTab = ref('lobby');
        const rankedMatchStatus = ref('idle');
        const rankedCoachOpen = ref(false);
        const rankedCoachInput = ref('');
        const isRankedCoachLoading = ref(false);
        const rankedCoachChatScroll = ref(null);

        // 新增：排位竞技答题舱状态变量与题目数据
        const rankedRoomMode = ref('lobby'); // 'lobby' | 'arena'
        const isRankedEntryConfirmOpen = ref(false);
        const isRankedExitConfirmOpen = ref(false);
        const isRankedSettlementOpen = ref(false);
        const rankedSecurityActive = ref(false);
        const rankedBlurViolationCount = ref(0);
        const rankedRemainingSeconds = ref(1800); // 30分钟
        const rankedOpponentStatus = ref('正在构思解题思路...');
        const rankedOpponentProgress = ref(0);
        const rankedMatchResult = ref(null); // 'win' | 'lose' | 'cheat_lose'
        const rankedAnswers = ref({});
        const rankedTestCaseResults = ref([]);
        const rankedConsoleLogs = ref([]);
        const isRankedEditorLoading = ref(false);
        const useRankedPlainEditor = ref(false);
        const isRankedRunning = ref(false);
        const rankedActiveTab = ref('cases');
        const currentRankedMatchId = ref('');
        let rankedMonacoEditor = null;
        let rankedTimer = null;
        let opponentTimer = null;

        const defaultRankedProblem = {
            id: 'cache_set_associative',
            title: 'Cache 组相联命中模拟',
            category: '计算机组成原理',
            funcName: 'simulateCache',
            difficulty: 'Medium',
            tags: ['Cache映射', 'LRU算法', '计算机组成'],
            timeLimitMs: 1000,
            memoryLimitMb: 64,
            desc: '在计算机组成原理中，Cache的地址映射和命中判定是核心内容。请实现一个 **2路组相联（2-way Set Associative）Cache** 模拟器。\n\n**Cache 结构说明：**\n1. Cache 大小共 4 个 Cache 行（Line），分为 2 个组（Set 0 和 Set 1），每组 2 行。\n2. 采用 **LRU（最近最少使用）** 替换算法。\n3. 每个 Cache 行包含：有效位（valid）、标志位（tag）以及访问时间戳（用来决定最少使用）。\n4. 块大小为 16 字节（即主存块地址偏移占 4 位：$BlockOffset = Address \\pmod{16}$，但输入的主存块地址已除去块内偏移，即 $BlockAddress = Address / 16$）。\n\n**算法映射规则：**\n* 组索引（Set Index） = $BlockAddress \\pmod 2$\n* 标志位（Tag） = $\\lfloor BlockAddress / 2 \\rfloor$\n\n对于给定的主存块地址序列 `blockAddresses`。请模拟 Cache 的访问过程：\n1. 初始时，所有 Cache 行都无效（valid = 0）。\n2. 每次访问一个 `BlockAddress` 时，根据组索引找到对应的组。如果该组内的某一行有效且其 Tag 与当前 Tag 匹配，则为 **Hit（命中）**；否则为 **Miss（缺失）**。\n3. 当 Miss 时，需要载入该块：若该组内有空闲行（valid = 0），直接写入；若无空闲行，则按照 **LRU** 算法选择最久未访问的行替换，写入新的 Tag，并将有效位置为 1。\n4. 命中或写入新块时，都需要更新该行的 LRU 访问状态（标记为最新访问，时间戳递增）。\n\n**返回结果：**\n你需要返回一个对象，包含 `hitCount`（总命中次数）以及 `results`（判定结果数组，`"Hit"` 或 `"Miss"`）。',
            starterCode: `function simulateCache(blockAddresses) {\n    // 在此编写你的代码\n    // 返回格式为：{ hitCount: number, results: string[] }\n    \n    return {\n        hitCount: 0,\n        results: []\n    };\n}`,
            testCases: [
                { input: [[0, 4, 8, 0, 4]], expected: { hitCount: 0, results: ["Miss", "Miss", "Miss", "Miss", "Miss"] }, label: '例1: 淘汰测试' },
                { input: [[1, 2, 1, 5, 2]], expected: { hitCount: 2, results: ["Miss", "Miss", "Hit", "Miss", "Hit"] }, label: '例2: 命中与隔离测试' }
            ]
        };
        const rankedProblem = ref(defaultRankedProblem);
        const watermarkTime = computed(() => new Date().toISOString().replace('T', ' ').slice(0, 19));
        const rankedTabs = [
            { id: 'lobby', label: '大厅' },
            { id: 'history', label: '对战记录' },
            { id: 'mistakes', label: '错题管理' },
            { id: 'season', label: '赛季' }
        ];
        const rankedPlayer = reactive({
            name: '林屿安',
            className: '计算机学院 · 软工2班',
            tier: '黄金段位',
            points: 1980,
            nextTierPoints: 2600,
            streak: 5,
            progress: 68
        });
        const leaderboard = ref([
            { rank: 1, name: '苏晚晴', points: '4,120', streak: 12, tier: '钻石' },
            { rank: 2, name: '林屿安', points: '1,980', streak: 5, tier: '黄金', self: true },
            { rank: 3, name: '沈砚辞', points: '1,840', streak: 3, tier: '黄金' },
            { rank: 4, name: '周叙白', points: '1,320', streak: 0, tier: '白银' },
            { rank: 5, name: '许清和', points: '990', streak: 2, tier: '白银' },
            { rank: 6, name: '温知予', points: '540', streak: 1, tier: '青铜' }
        ]);
        const rankedRules = ref([
            { title: '匹配对决', desc: '系统按你的段位匹配同水平题目与对手，胜负即时结算。', icon: 'ph-sword' },
            { title: '积分收益', desc: '通过全部测试用例判定胜利，按题目难度获得基础荣誉积分。', icon: 'ph-coins' },
            { title: '连胜加成', desc: '连胜期间每胜一场额外加成，最高叠加 10 连胜（+50%）。', icon: 'ph-fire' },
            { title: '失利扣分', desc: '未通过全部用例视为失利，按题目扣除积分并中断连胜。', icon: 'ph-minus-circle' },
            { title: '每日挑战', desc: '每日刷新特定知识点任务，完成后领取额外荣誉积分。', icon: 'ph-target' },
            { title: '赛季结算', desc: '一个学期为一个赛季，赛季末按最终段位发放勋章与奖励。', icon: 'ph-calendar-check' }
        ]);
        const dailyChallenge = reactive({
            tag: '课程综合 · 图搜索与组成原理',
            title: '完成 2 道图搜索 / Cache 模拟题目',
            progress: 50,
            reward: '+180 积分',
            count: '1/2'
        });
        const tierLadder = ref([
            { name: '王者', range: '荣誉积分 5200 分以上', level: 'LV.6', color: 'orange', peak: true },
            { name: '钻石', range: '荣誉积分 3800 ~ 5199 分', level: 'LV.5', color: 'blue' },
            { name: '铂金', range: '荣誉积分 2600 ~ 3799 分', level: 'LV.4', color: 'cyan' },
            { name: '黄金', range: '荣誉积分 1600 ~ 2599 分', level: 'LV.3', color: 'amber' },
            { name: '白银', range: '荣誉积分 800 ~ 1599 分', level: 'LV.2', color: 'slate' },
            { name: '青铜', range: '荣誉积分 0 ~ 799 分', level: 'LV.1', color: 'stone' }
        ]);
        const matchHistory = ref([
            { result: '胜利', title: 'Cache 组相联命中模拟', type: '算法题', score: '+231', duration: '23分40秒', time: '7月5日 20:12' },
            { result: '胜利', title: '循环队列取队错误', type: 'Debug题', score: '+122', duration: '9分00秒', time: '7月5日 19:44' },
            { result: '失败', title: '实验楼网络连通块', type: '算法题', score: '-18', duration: '31分00秒', time: '7月4日 21:03' },
            { result: '胜利', title: '链表删除节点断链', type: 'Debug题', score: '+178', duration: '11分30秒', time: '7月4日 18:22' },
            { result: '胜利', title: '课程先修栈检验', type: '算法题', score: '+96', duration: '6分50秒', time: '7月3日 22:15' }
        ]);
        const historyStats = [
            { label: '总胜率', value: '67%', tone: 'text-orange-500' },
            { label: '胜 / 负', value: '6 / 3', tone: 'text-blue-500' },
            { label: '总对局', value: '9', tone: 'text-cyan-500' },
            { label: '净积分', value: '+720', tone: 'text-orange-500' }
        ];
        const seasonList = ref([
            { name: '2026 春季学期', status: '进行中', date: '2026-02-24 ~ 2026-07-12', score: '1,980', tier: '黄金段位', progress: 96, winRate: '73%', record: '38胜 14负', streak: 5, peak: '黄金', rank: '#6', total: '共 1284 人', reward: '赛季结束按最终段位发放荣誉勋章与积分加成，前 3% 可获「王者认证」徽章。', current: true },
            { name: '2025 秋季学期', status: '已结束', date: '2025-09-01 ~ 2026-01-18', score: '1,460', tier: '白银段位', progress: 100, winRate: '60%', record: '29胜 19负', streak: 7, peak: '黄金', rank: '#21', total: '共 1102 人', reward: '已发放：白银段位勋章 + 300 荣誉积分。' },
            { name: '2025 春季学期', status: '已结束', date: '2025-02-26 ~ 2025-07-06', score: '720', tier: '青铜段位', progress: 100, winRate: '53%', record: '17胜 15负', streak: 4, peak: '白银', rank: '#88', total: '共 967 人', reward: '已发放：青铜段位勋章 + 120 荣誉积分。' }
        ]);
        const rankedMistakes = ref([
            { title: '岛屿数量', type: '算法题', status: '遍历越界', topic: '并查集 / DFS', count: '累计出错 2 次', date: '最近 2026.7.4', issue: 'DFS 未做边界判断，网格四邻访问时数组越界导致部分用例失败。', note: '', mastered: false, badge: 'gold', showAnalysis: false, analysisLoading: false },
            { title: '最短路径 Dijkstra', type: '算法题', status: '超时', topic: '最短路 / 堆', count: '累计出错 3 次', date: '最近 2026.7.2', issue: '使用邻接矩阵朴素实现，未用优先队列优化，大数据用例 TLE。', note: '复习堆优化 Dijkstra 的模板。', mastered: false, badge: 'blue', showAnalysis: false, analysisLoading: false },
            { title: '二分边界的死循环', type: 'Debug题', status: '边界处理', topic: '二分查找', count: '累计出错 1 次', date: '最近 2026.6.28', issue: '指针收缩写成 lo=mid，区间无法缩小导致死循环。', note: '记住 lo=mid+1 / hi=mid-1 的收缩方向。', mastered: true, badge: 'silver', showAnalysis: false, analysisLoading: false },
            { title: '树形DP 状态转移遗漏', type: 'Debug题', status: '状态转移', topic: '树形DP', count: '累计出错 2 次', date: '最近 2026.6.25', issue: '不偷当前节点时未对子树取 max(偷, 不偷)，总额偏小。', note: '', mastered: false, badge: 'cyan', showAnalysis: false, analysisLoading: false }
        ]);
        const mistakeStats = computed(() => {
            const total = rankedMistakes.value.length;
            const mastered = rankedMistakes.value.filter(item => item.mastered).length;
            const pending = Math.max(0, total - mastered);
            const masteryRate = total ? Math.round((mastered / total) * 100) : 0;
            return [
                { label: '错题总数', value: String(total), tone: 'text-blue-500', icon: 'ph-file-x' },
                { label: '待复习', value: String(pending), tone: 'text-rose-500', icon: 'ph-warning' },
                { label: '已掌握', value: String(mastered), tone: 'text-orange-500', icon: 'ph-check-circle' },
                { label: '掌握率', value: `${masteryRate}%`, tone: 'text-cyan-500', icon: 'ph-arrows-clockwise' }
            ];
        });
        const coachSuggestions = ref([
            '本赛季目标：冲击「铂金」段位，稳定胜率到 65% 以上即可稳步晋级。'
        ]);

        const normalizeCollabIdentity = (value) => String(value || '').replace(' (你)', '').trim();
        const isLeaderRole = (role) => {
            const text = String(role || '').toLowerCase();
            return text.includes('队长') || text.includes('leader') || text.includes('captain');
        };
        const collabViewerName = computed(() => props.currentUser?.username || '李明');
        const currentCollabIdentities = computed(() => {
            return new Set([
                props.currentUser?.username,
                props.currentUser?.real_name,
                props.currentUser?.name,
                props.currentUser?.student_id,
                props.currentUser?.studentId,
                collabViewerName.value
            ].map(normalizeCollabIdentity).filter(Boolean));
        });
        const getProjectLeaderIdentities = (project) => {
            const info = project?.project || {};
            const leaders = [
                info.leaderId,
                info.createdBy,
                project?.repositoryCard?.leader
            ];
            (project?.memberProgress || []).forEach((member) => {
                if (isLeaderRole(member.role)) {
                    leaders.push(member.id, member.name, member.username, member.studentId, member.student_id);
                }
            });
            return new Set(leaders.map(normalizeCollabIdentity).filter(Boolean));
        };
        const canManageCollabProject = (project) => {
            if (props.currentUser?.role === 'teacher') return true;
            const userIds = currentCollabIdentities.value;
            const leaderIds = getProjectLeaderIdentities(project);
            return Array.from(userIds).some((id) => leaderIds.has(id));
        };
        const canManageCollab = computed(() => canManageCollabProject(collabData.value));
        const contributionRanking = computed(() => {
            const ranking = teamSummary.value?.contributionRanking;
            if (Array.isArray(ranking) && ranking.length > 0) return ranking;
            return [...memberProgress.value].sort((a, b) => Number(b.contribution || 0) - Number(a.contribution || 0));
        });
        const collabProject = computed(() => collabData.value?.project || {});
        const repositoryInfo = computed(() => collabData.value?.repository || {});
        const repositoryPrSource = computed(() => repositoryInfo.value?.prSource || '');
        const isGiteaLive = computed(() => repositoryInfo.value?.giteaSyncStatus === 'synced');
        const isWebhookConnected = computed(() => ['configured', 'reconciled'].includes(repositoryInfo.value?.webhookStatus));
        const isDemoFallback = computed(() => repositoryPrSource.value === 'demo_fallback');
        const isGiteaEmptyPr = computed(() => repositoryPrSource.value === 'gitea_empty' && pullRequests.value.length === 0);
        const syncErrorMessage = computed(() => {
            if (!isDemoFallback.value && !repositoryInfo.value?.lastSyncError) return '';
            return repositoryInfo.value?.demoFallbackReason || '同步异常，已显示演示数据';
        });
        const workflowSteps = computed(() => collabData.value?.workflowSteps || []);
        const memberProgress = computed(() => collabData.value?.memberProgress || []);
        const pullRequests = computed(() => collabData.value?.pullRequests || []);
        const aiGitCoachFeedback = computed(() => collabData.value?.aiGitCoachFeedback || []);
        const gitEvents = computed(() => collabData.value?.gitEvents || []);
        const recentCommits = computed(() => collabData.value?.recentCommits || []);
        const teamSummary = computed(() => collabData.value?.teamSummary || {});
        const currentUserProgress = computed(() => collabData.value?.currentUserProgress || {});
        const repositoryHomeInfo = computed(() => repositoryHome.value || {});
        const repositoryHomeProject = computed(() => repositoryHome.value?.project || {});
        const repositoryHomeRepo = computed(() => repositoryHome.value?.repository || {});
        const repositoryHomeFiles = computed(() => repositoryHome.value?.files || []);
        const repositoryHomeLanguages = computed(() => repositoryHome.value?.languageStats || []);
        const repositoryHomePullRequests = computed(() => repositoryHome.value?.pullRequests || collabData.value?.pullRequests || []);
        const repositoryHomeOpenPrCount = computed(() => repositoryHomePullRequests.value.filter((item) => item.status === 'open').length);
        const repositoryHomeMergedPrCount = computed(() => repositoryHomePullRequests.value.filter((item) => item.status === 'merged').length);
        const canManageRepositoryHome = computed(() => canManageCollab.value || canManageCollabProject(repositoryHome.value));
        const teamAuthenticatedCloneUrl = computed(() => {
            const cloneUrl = repositoryHomeInfo.value.cloneUrl || repositoryHomeRepo.value.cloneUrl || repositoryInfo.value.cloneUrl || '';
            const username = teamGiteaIdentity.value?.giteaUsername || '';
            if (!cloneUrl || !username || !teamGeneratedToken.value) return '';
            return cloneUrl.replace(/^https:\/\//, `https://${username}:${teamGeneratedToken.value}@`);
        });
        const repositoryHomeTabs = [
            { id: 'code', label: 'Code', icon: 'ph-code' },
            { id: 'pulls', label: 'Pull requests', icon: 'ph-git-pull-request' },
            { id: 'insights', label: 'Insights', icon: 'ph-chart-line-up' }
        ];

        const teamRepoBrowserPath = ref('');
        const teamRepoBrowserEntries = ref([]);
        const teamRepoBrowserLoading = ref(false);
        const teamRepoBrowserBlob = ref(null);
        const teamRepoBrowserLanguages = ref([]);
        const teamRepoBrowserError = ref('');
        const teamRepoBranches = ref([]);
        const teamRepoSelectedBranch = ref('');
        const teamBranchDropdownOpen = ref(false);

        const toggleBranchDropdown = () => {
            teamBranchDropdownOpen.value = !teamBranchDropdownOpen.value;
        };
        const closeBranchDropdown = () => {
            teamBranchDropdownOpen.value = false;
        };

        const teamRepoBreadcrumbs = computed(() => {
            const crumbs = [{ label: '根目录', path: '' }];
            const parts = String(teamRepoBrowserPath.value || '').split('/').filter(Boolean);
            let current = '';
            parts.forEach((part) => {
                current = current ? `${current}/${part}` : part;
                crumbs.push({ label: part, path: current });
            });
            return crumbs;
        });

        const resetTeamRepoBrowser = () => {
            teamRepoBrowserPath.value = '';
            teamRepoBrowserEntries.value = [];
            teamRepoBrowserBlob.value = null;
            teamRepoBrowserLanguages.value = [];
            teamRepoBrowserError.value = '';
        };

        const loadTeamRepoLanguages = async (projectId = collabProjectId.value) => {
            if (!projectId) return;
            try {
                teamRepoBrowserLanguages.value = await teamGitApi.getRepositoryLanguages(projectId);
            } catch (err) {
                teamRepoBrowserLanguages.value = [];
            }
        };

        const loadTeamRepoBrowser = async (path = '', projectId = collabProjectId.value) => {
            if (!projectId) return;
            teamRepoBrowserLoading.value = true;
            teamRepoBrowserError.value = '';
            teamRepoBrowserBlob.value = null;
            try {
                const ref = teamRepoSelectedBranch.value || repositoryHomeInfo.value.defaultBranch || repositoryHomeRepo.value.defaultBranch || 'main';
                const data = await teamGitApi.getRepositoryTree(projectId, {
                    path,
                    ref
                });
                teamRepoBrowserPath.value = data.path || '';
                teamRepoBrowserEntries.value = data.entries || [];
            } catch (err) {
                teamRepoBrowserEntries.value = [];
                teamRepoBrowserError.value = err?.message || '文件目录加载失败';
            } finally {
                teamRepoBrowserLoading.value = false;
            }
        };

        const loadTeamBranches = async (projectId = collabProjectId.value) => {
            if (!projectId) return;
            try {
                const branches = await teamGitApi.getBranches(projectId);
                teamRepoBranches.value = branches || [];
                if (!teamRepoSelectedBranch.value) {
                    const defaultBranch = branches.find((b) => b.default);
                    teamRepoSelectedBranch.value = defaultBranch?.name || branches[0]?.name || repositoryHomeInfo.value.defaultBranch || 'main';
                }
            } catch (err) {
                teamRepoBranches.value = [];
                teamRepoBrowserError.value = err?.message || '分支列表加载失败，请检查 Gitea 连接';
                console.error('[loadTeamBranches] 分支列表加载失败:', err);
            }
        };

        const switchTeamBranch = async (branchName) => {
            teamRepoSelectedBranch.value = branchName;
            teamBranchDropdownOpen.value = false;
            teamRepoBrowserPath.value = '';
            teamRepoBrowserBlob.value = null;
            try {
                await loadTeamRepoBrowser('');
            } catch (err) {
                teamRepoBrowserError.value = err?.message || '切换分支失败';
                console.error('[switchTeamBranch] 切换分支失败:', err);
            }
        };

        const loadTeamRepoBlob = async (path, projectId = collabProjectId.value) => {
            if (!projectId || !path) return;
            teamRepoBrowserLoading.value = true;
            teamRepoBrowserError.value = '';
            try {
                teamRepoBrowserBlob.value = await teamGitApi.getRepositoryBlob(projectId, {
                    path,
                    ref: teamRepoSelectedBranch.value || repositoryHomeInfo.value.defaultBranch || repositoryHomeRepo.value.defaultBranch || 'main'
                });
            } catch (err) {
                teamRepoBrowserBlob.value = null;
                teamRepoBrowserError.value = err?.message || '文件预览失败';
            } finally {
                teamRepoBrowserLoading.value = false;
            }
        };

        const openTeamRepoEntry = async (entry) => {
            if (!entry) return;
            if (entry.type === 'dir') {
                await loadTeamRepoBrowser(entry.path || entry.name);
                return;
            }
            await loadTeamRepoBlob(entry.path || entry.name);
        };

        const formatTeamRepoFileSize = (size) => {
            const value = Number(size || 0);
            if (!value) return '-';
            if (value < 1024) return `${value} B`;
            if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
            return `${(value / (1024 * 1024)).toFixed(1)} MB`;
        };

        const selectedCollabTask = computed(() => {
            return kanbanTasks.value.find(t => t.id === selectedCollabTaskId.value) || null;
        });

        const loadCollabProjects = async () => {
            collabLoading.value = true;
            collabError.value = '';
            try {
                const projects = await teamGitApi.listProjects({ viewer: collabViewerName.value, scope: 'my' });
                collabProjects.value = projects || [];
                if (!collabProjectId.value && collabProjects.value[0]) {
                    collabProjectId.value = collabProjects.value[0].id;
                }
            } catch (err) {
                console.error('加载团队仓库列表失败:', err);
                collabError.value = err?.message || '团队仓库列表加载失败';
            } finally {
                collabLoading.value = false;
            }
        };

        const loadCollabProject = async () => {
            collabLoading.value = true;
            collabError.value = '';
            try {
                const detail = await teamGitApi.getProjectDetail(collabProjectId.value, {
                    viewer: collabViewerName.value,
                    sync: 1
                });
                collabData.value = detail;
                if (Array.isArray(detail.chatMessages)) {
                    chatMessages.value = detail.chatMessages;
                }
            } catch (err) {
                console.error('加载团队 Git 协作数据失败:', err);
                collabError.value = err?.message || '团队协作 Git 数据加载失败';
            } finally {
                collabLoading.value = false;
            }
        };

        const loadRepositoryHome = async (projectId = collabProjectId.value) => {
            collabLoading.value = true;
            collabError.value = '';
            resetTeamRepoBrowser();
            teamRepoSelectedBranch.value = '';
            try {
                repositoryHome.value = await teamGitApi.getRepositoryHome(projectId);
                await loadTeamBranches(projectId);
                await Promise.all([
                    loadTeamRepoBrowser('', projectId),
                    loadTeamRepoLanguages(projectId)
                ]);
            } catch (err) {
                console.error('加载团队仓库主页失败:', err);
                collabError.value = err?.message || '团队仓库主页加载失败';
            } finally {
                collabLoading.value = false;
            }
        };

        const openCollabManagement = async (project) => {
            collabProjectId.value = project?.id || collabProjectId.value;
            collabViewMode.value = 'manage';
            await loadCollabProject();
        };

        const openCollabRepositoryHome = async (project) => {
            collabProjectId.value = project?.id || collabProjectId.value;
            collabViewMode.value = 'home';
            repositoryHomeTab.value = 'code';
            await loadCollabProject();
            await loadRepositoryHome(collabProjectId.value);
        };

        const openRepositoryHomePullRequests = async () => {
            collabViewMode.value = 'home';
            repositoryHomeTab.value = 'pulls';
            await loadCollabProject();
            await loadRepositoryHome(collabProjectId.value);
        };

        const backToCollabRepositoryList = () => {
            collabViewMode.value = 'list';
            collabError.value = '';
            repositoryHome.value = null;
            resetTeamRepoBrowser();
            loadCollabProjects();
        };

        const refreshRepositoryHomePullRequests = async ({ showToast = false } = {}) => {
            if (collabActionLoading.value) return;
            collabActionLoading.value = 'sync-repository-prs';
            try {
                const detail = await teamGitApi.refreshStatus(collabProjectId.value, { actor: collabViewerName.value, stage: 'pull_request' });
                collabData.value = detail;
                repositoryHome.value = await teamGitApi.getRepositoryHome(collabProjectId.value);
                if (showToast) emit('show-toast', '已从 Gitea 同步 Pull Request 状态', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '同步 Pull Request 失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const selectRepositoryHomeTab = async (tabId) => {
            repositoryHomeTab.value = tabId;
            if (tabId === 'code') {
                if (!teamRepoBranches.value.length) {
                    await loadTeamBranches();
                }
                if (!teamRepoBrowserEntries.value.length) {
                    await loadTeamRepoBrowser('');
                }
            }
            if (tabId === 'pulls') {
                await refreshRepositoryHomePullRequests();
            }
        };

        const copyGitCommand = async (command) => {
            try {
                await navigator.clipboard.writeText(command || '');
                emit('show-toast', '复制成功，请到终端执行。', 'success');
            } catch (err) {
                emit('show-toast', '复制失败，请手动选择命令复制', 'error');
            }
        };

        const copyTeamAuthClone = async () => {
            if (!teamAuthenticatedCloneUrl.value) return;
            const command = `git clone ${teamAuthenticatedCloneUrl.value}`;
            try {
                await navigator.clipboard.writeText(command);
                copiedTeamAuthClone.value = true;
                emit('show-toast', '带 Token 的 Clone 命令已复制', 'success');
                setTimeout(() => { copiedTeamAuthClone.value = false; }, 1400);
            } catch (err) {
                emit('show-toast', command, 'info');
            }
        };

        const formatTeamGitConfigCommands = (commands) => (commands || []).join('\n');

        const loadTeamGiteaIdentity = async () => {
            teamIdentityLoading.value = true;
            try {
                teamGiteaIdentity.value = await fetchGiteaIdentity();
            } catch (err) {
                teamGiteaIdentity.value = {
                    giteaUsername: '',
                    giteaEmail: '',
                    syncStatus: 'pending',
                    gitConfigCommands: []
                };
            } finally {
                teamIdentityLoading.value = false;
            }
        };

        const handleTeamRotateGiteaToken = async () => {
            if (collabActionLoading.value) return;
            collabActionLoading.value = 'team-gitea-token';
            try {
                const result = await rotateGiteaToken();
                teamGeneratedToken.value = result.token || '';
                teamTokenWarning.value = result.warning || 'Token 只显示一次，请保存到本机 Git 凭据管理器。';
                await loadTeamGiteaIdentity();
                emit('show-toast', 'Gitea Token 已生成，只显示一次', 'success');
            } catch (err) {
                emit('show-toast', err?.message || 'Gitea Token 生成失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const copyTeamSecretText = async (text, successMessage, onCopied, resetCopied) => {
            if (!text) {
                emit('show-toast', '暂无可复制内容', 'info');
                return;
            }
            try {
                await navigator.clipboard.writeText(text);
                onCopied?.();
                emit('show-toast', successMessage, 'success');
                if (resetCopied) setTimeout(resetCopied, 1400);
            } catch (err) {
                emit('show-toast', '复制失败，请手动选择内容复制', 'error');
            }
        };

        const copyTeamGeneratedToken = async () => {
            await copyTeamSecretText(
                teamGeneratedToken.value,
                'Token 已复制',
                () => { copiedTeamToken.value = true; },
                () => { copiedTeamToken.value = false; }
            );
        };

        const copyTeamGitConfig = async () => {
            await copyTeamSecretText(
                formatTeamGitConfigCommands(teamGiteaIdentity.value?.gitConfigCommands),
                'Git 配置已复制',
                () => { copiedTeamGitConfigAll.value = true; },
                () => { copiedTeamGitConfigAll.value = false; }
            );
        };

        const copyTeamGitConfigLine = async (command) => {
            await copyTeamSecretText(
                command,
                '命令已复制',
                () => { copiedTeamGitConfigLine.value = command; },
                () => {
                    if (copiedTeamGitConfigLine.value === command) copiedTeamGitConfigLine.value = '';
                }
            );
        };

        const openExternalLink = (url) => {
            if (!url) {
                emit('show-toast', '链接暂不可用，请刷新状态后重试', 'error');
                return;
            }
            window.open(url, '_blank', 'noopener,noreferrer');
        };

        const prCreationUrl = computed(() => {
            const step = workflowSteps.value.find(item => item.id === 'pull_request');
            return step?.command || '';
        });

        const createGiteaRepository = async () => {
            if (collabActionLoading.value) return;
            collabActionLoading.value = 'create-repo';
            try {
                const detail = await teamGitApi.createRepository(collabProjectId.value, { actor: collabViewerName.value });
                collabData.value = detail;
                collabProjects.value = [detail, ...collabProjects.value.filter((item) => item.id !== detail.id)];
                emit('show-toast', '团队仓库已接入本机 Gitea，Webhook 状态已同步', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '创建仓库失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const bindExistingRepository = async () => {
            if (collabActionLoading.value) return;
            collabActionLoading.value = 'bind-repo';
            try {
                const detail = await teamGitApi.bindRepository(collabProjectId.value, {
                    actor: collabViewerName.value,
                    repoName: repositoryInfo.value.repoName || 'huffman-coding-team',
                    htmlUrl: repositoryInfo.value.htmlUrl || 'https://gezhisystem.com/gitea/campus/huffman-coding-team',
                    cloneUrl: repositoryInfo.value.cloneUrl || 'https://gezhisystem.com/gitea/campus/huffman-coding-team.git',
                    sshUrl: repositoryInfo.value.sshUrl || 'ssh://git@gezhisystem.com:2222/campus/huffman-coding-team.git'
                });
                collabData.value = detail;
                emit('show-toast', '已绑定已有仓库', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '绑定仓库失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const createCollabProject = async () => {
            if (collabActionLoading.value) return;
            const title = collabCreateForm.value.title.trim();
            const description = collabCreateForm.value.description.trim();
            if (!title || !description) {
                emit('show-toast', '请填写项目名称和项目介绍', 'error');
                return;
            }
            collabActionLoading.value = 'create-project';
            try {
                const members = collabCreateForm.value.members
                    .replace(/，/g, ',')
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean);
                collabSelectedMembers.value.forEach((member) => {
                    if (member.name && !members.includes(member.name)) members.push(member.name);
                });
                const detail = await teamGitApi.createProject({
                    ...collabCreateForm.value,
                    title,
                    description,
                    members,
                    actor: collabViewerName.value
                });
                collabProjectId.value = detail.id;
                collabData.value = detail;
                collabProjects.value = [detail, ...collabProjects.value.filter((item) => item.id !== detail.id)];
                collabCreateOpen.value = false;
                collabViewMode.value = 'manage';
                emit('show-toast', '团队项目已创建，下一步可分配成员任务并创建仓库', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '团队项目创建失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const searchCollabMembers = async () => {
            const keyword = collabMemberKeyword.value.trim();
            if (!keyword) {
                collabMemberSearchResults.value = [];
                return;
            }
            try {
                collabMemberSearchResults.value = await teamGitApi.searchMembers({
                    keyword,
                    course: collabCreateForm.value.course
                });
            } catch (err) {
                emit('show-toast', err?.message || '成员搜索失败', 'error');
            }
        };

        const addCollabMember = (member) => {
            if (!member?.name) return;
            if (!collabSelectedMembers.value.some((item) => item.studentId === member.studentId || item.name === member.name)) {
                collabSelectedMembers.value.push(member);
            }
            const names = collabCreateForm.value.members
                .replace(/，/g, ',')
                .split(',')
                .map((item) => item.trim())
                .filter(Boolean);
            if (!names.includes(member.name)) {
                names.push(member.name);
                collabCreateForm.value.members = names.join(', ');
            }
        };

        const removeCollabMember = (member) => {
            collabSelectedMembers.value = collabSelectedMembers.value.filter((item) => item !== member);
        };

        const deleteCollabProject = async (project) => {
            if (!project?.id || collabActionLoading.value) return;
            if (!canManageCollabProject(project)) {
                emit('show-toast', '只有队长可以删除团队仓库', 'error');
                return;
            }
            const repoName = project.repositoryCard?.repoName || project.repository?.repoName || project.id;
            const confirmed = window.confirm(`确认删除团队仓库「${repoName}」？删除后团队协作记录将不可在列表中继续访问。`);
            if (!confirmed) return;
            collabActionLoading.value = `delete-project-${project.id}`;
            try {
                await teamGitApi.deleteProject(project.id, { actor: collabViewerName.value });
                collabProjects.value = collabProjects.value.filter((item) => item.id !== project.id);
                if (collabProjectId.value === project.id) {
                    collabProjectId.value = collabProjects.value[0]?.id || '';
                    collabData.value = null;
                    repositoryHome.value = null;
                    collabViewMode.value = 'list';
                }
                emit('show-toast', '团队仓库已删除', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '团队仓库删除失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const startAssignTask = (member) => {
            assigningMemberName.value = member.name;
            assignTaskForm.value = {
                task: member.task || '',
                branch: member.branch || `feature/${member.id || 'task'}`
            };
        };

        const submitAssignTask = async () => {
            if (!assigningMemberName.value || collabActionLoading.value) return;
            if (!assignTaskForm.value.task.trim() || !assignTaskForm.value.branch.trim()) {
                emit('show-toast', '请填写任务说明和分支名', 'error');
                return;
            }
            collabActionLoading.value = 'assign-task';
            try {
                const detail = await teamGitApi.assignMemberTask(collabProjectId.value, {
                    memberId: assigningMemberName.value,
                    task: assignTaskForm.value.task.trim(),
                    branch: assignTaskForm.value.branch.trim(),
                    actor: collabViewerName.value
                });
                collabData.value = detail;
                assigningMemberName.value = '';
                emit('show-toast', '成员任务已分配并同步到后端', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '任务分配失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const remindCollabMembers = async (member = null) => {
            if (collabActionLoading.value) return;
            collabActionLoading.value = 'remind-members';
            try {
                const detail = await teamGitApi.remindMembers(collabProjectId.value, {
                    memberIds: member ? [member.name] : [],
                    message: reminderMessage.value,
                    actor: collabViewerName.value
                });
                collabData.value = detail;
                emit('show-toast', member ? `已提醒 ${member.name}` : '已提醒所有未提交成员', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '提醒发送失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const reviewCollabPr = async (pr, action) => {
            if (!pr || collabActionLoading.value) return;
            collabActionLoading.value = `review-pr-${pr.number}`;
            try {
                const detail = await teamGitApi.reviewPullRequest(collabProjectId.value, pr.number, {
                    action,
                    comment: prReviewComment.value,
                    actor: collabViewerName.value
                });
                collabData.value = detail;
                if (collabViewMode.value === 'home') {
                    repositoryHome.value = await teamGitApi.getRepositoryHome(collabProjectId.value);
                }
                const message = action === 'approve_merge' || action === 'leader_merge' || action === 'merge' || action === 'teacher_approve'
                    ? `已合并 PR #${pr.number}`
                    : action === 'recommend_merge'
                        ? `已推荐合并 PR #${pr.number}`
                        : `已要求 PR #${pr.number} 修改`;
                emit('show-toast', message, 'success');
            } catch (err) {
                emit('show-toast', err?.message || 'PR 审核失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const confirmCloneDone = async () => {
            if (collabActionLoading.value) return;
            collabActionLoading.value = 'confirm-clone';
            try {
                const detail = await teamGitApi.confirmClone(collabProjectId.value, { userId: collabViewerName.value });
                collabData.value = detail;
                emit('show-toast', '已确认 clone，后续 push/PR 将由后端 Webhook 同步', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '确认 clone 失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const refreshCollabStatus = async (stage = 'push') => {
            if (collabActionLoading.value) return;
            collabActionLoading.value = `refresh-${stage}`;
            try {
                const detail = await teamGitApi.refreshStatus(collabProjectId.value, { actor: collabViewerName.value });
                collabData.value = detail;
                if (collabViewMode.value === 'home') {
                    await loadRepositoryHome(collabProjectId.value);
                }
                emit('show-toast', stage === 'merged' ? '已同步合并状态，任务进度已更新' : '状态已刷新，等待系统检测结果已展示', 'success');
            } catch (err) {
                emit('show-toast', err?.message || '刷新状态失败', 'error');
            } finally {
                collabActionLoading.value = '';
            }
        };

        const repoStatusClass = (status) => {
            if (status === 'completed') return 'bg-emerald-50 text-emerald-700 border-emerald-100';
            if (status === 'created' || status === 'collaborating') return 'bg-teal-50 text-teal-700 border-teal-100';
            if (status === 'waiting_upload') return 'bg-amber-50 text-amber-700 border-amber-100';
            return 'bg-slate-100 text-slate-600 border-slate-200';
        };

        const stepStatusClass = (status) => {
            if (status === 'done') return 'border-emerald-200 bg-emerald-50/70 text-emerald-700';
            if (status === 'current') return 'border-teal-300 bg-white text-teal-700 ring-2 ring-teal-500/10';
            return 'border-slate-200 bg-slate-50/70 text-slate-400';
        };

        const memberStatusClass = (member) => {
            if (member.mergeStatus === 'merged') return 'bg-emerald-50 text-emerald-700 border-emerald-100';
            if (member.prStatus === 'open') return 'bg-blue-50 text-blue-700 border-blue-100';
            if (member.prStatus === 'needs_pr') return 'bg-amber-50 text-amber-700 border-amber-100';
            if (member.cloneStatus === 'done') return 'bg-teal-50 text-teal-700 border-teal-100';
            return 'bg-slate-100 text-slate-500 border-slate-200';
        };

        const prStatusClass = (status) => {
            if (status === 'merged') return 'bg-emerald-50 text-emerald-700 border-emerald-100';
            if (status === 'open') return 'bg-blue-50 text-blue-700 border-blue-100';
            if (status === 'closed') return 'bg-slate-100 text-slate-600 border-slate-200';
            return 'bg-amber-50 text-amber-700 border-amber-100';
        };

        const eventIcon = (type) => {
            if (type === 'push') return 'ph-upload-simple';
            if (type === 'pull_request') return 'ph-git-pull-request';
            if (type === 'merge') return 'ph-git-merge';
            if (type === 'repository_created' || type === 'repository_bound') return 'ph-git-branch';
            return 'ph-clock-counter-clockwise';
        };

        // 认领/点击编写任务
        const handleCollabTaskClick = (task) => {
            if (task.assignee !== '李明 (你)') {
                emit('show-toast', '该模块已被队友认领，您可以查看代码但无法修改', 'error');
                selectedCollabTaskId.value = task.id;
                if (monacoEditor) {
                    monacoEditor.setValue(task.code);
                    monacoEditor.updateOptions({ readOnly: true });
                }
                return;
            }
            selectedCollabTaskId.value = task.id;
            if (monacoEditor) {
                monacoEditor.setValue(task.code);
                monacoEditor.updateOptions({ readOnly: false });
            }
            emit('show-toast', `已加载协作模块: ${task.title}`, 'success');
        };

        const runCollabTesting = ref(false);
        const runCollabTest = () => {
            if (runCollabTesting.value) return;
            runCollabTesting.value = true;
            emit('show-toast', '正在执行协同模块测试...', 'info');
            setTimeout(() => {
                runCollabTesting.value = false;
                const task = selectedCollabTask.value;
                if (task && task.assignee === '李明 (你)') {
                    task.status = 'completed';
                    collabLogs.value.unshift({
                        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                        text: `李明 成功跑通了「${task.title}」测试用例，完成率 100%！`
                    });
                    chatMessages.value.push({
                        id: Date.now(),
                        sender: 'PairBot',
                        content: `恭喜李明同学！您提交的「${task.title}」模块测试用例全数跑通，且时空效率优异。这极大地推进了「基于哈夫曼树的文本压缩系统」项目的总体进度！`,
                        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    });
                    emit('show-toast', '恭喜！当前协同开发模块全数跑通！', 'success');

                    if (window.dispatchEvent) {
                        window.dispatchEvent(new CustomEvent('agent-log', {
                            detail: {
                                agent: 'Alina',
                                content: `李明完成了协作模块「${task.title}」，团队总进度已提升至 90%！`,
                                time: new Date().toLocaleTimeString()
                            }
                        }));
                    }
                }
            }, 1500);
        };

        const sendCollabMessage = () => {
            const text = chatInput.value.trim();
            if (!text) return;

            chatMessages.value.push({
                id: Date.now(),
                sender: '李明 (你)',
                content: text,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            });
            chatInput.value = '';

            if (text.toLowerCase().includes('@pairbot') || text.toLowerCase().includes('pairbot') || text.includes('助手') || text.includes('求助')) {
                isPairBotThinking.value = true;
                setTimeout(() => {
                    isPairBotThinking.value = false;
                    let reply = '李明同学你好！我是您的协同结对编程助手 PairBot。关于你提出的问题，我有一些建议：\\n\\n针对哈夫曼文本压缩：\\n1. 在压缩时，由于编码所得 bit 长度不定，容易发生位溢出。建议每次拼接满 8 位后，直接通过 \`parseInt(byteStr, 2)\` 转成字节写入缓冲区。\\n2. 在二进制文件解压时，必须确保从编码字典树的根部节点开始向下走，根据 0/1 走向左右子树，到达叶子节点时读出字符，并立即回退到根节点。\\n\\n如果有代码层面的疑惑，可以直接在沙箱中调试，我随时可以为您分析时空效率！';
                    if (text.includes('位对齐') || text.includes('二进制')) {
                        reply = '针对你提到的二进制位对齐问题，建议如下：\\n在最后的 \`bitStream\` 后面追加 \`(8 - bitStream.length % 8) % 8\` 个字符 "0"，作为末尾补齐。然后在头部写入一个额外的字节，记录补齐的零的个数，这样解压缩时就能精确裁剪多余的补齐位啦。';
                    }
                    chatMessages.value.push({
                        id: Date.now(),
                        sender: 'PairBot',
                        content: reply,
                        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    });
                }, 1500);
            }
        };

        const collabRadarOption = computed(() => {
            return {
                radar: {
                    indicator: [
                        { name: '团队规划力 (Alina)', max: 100 },
                        { name: '代码工程度 (李明/王磊)', max: 100 },
                        { name: '协同响应率 (张华)', max: 100 }
                    ],
                    splitNumber: 4,
                    axisLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.1)' } },
                    splitLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.08)' } },
                    splitArea: { areaStyle: { color: ['rgba(255,255,255,0.4)', 'rgba(255,255,255,0.2)'] } }
                },
                series: [{
                    type: 'radar',
                    data: [{
                        value: [88, 79, 91],
                        name: '团队实训评估',
                        areaStyle: { color: 'rgba(16, 185, 129, 0.12)' },
                        lineStyle: { color: '#10b981', width: 2 },
                        itemStyle: { color: '#10b981' }
                    }]
                }]
            };
        });

        const getRankedUserId = () => props.currentUser?.username || props.currentUser?.id || 'guest_user';
        const getRankedCoachConfig = () => props.rankedCoachConfig || {
            id: 'agent_ranked_coach',
            name: '排位赛AI教练',
            model: 'qwen3.7-plus',
            prompt: '你是排位赛 AI 教练，请给出具体的错题诊断与冲分策略。'
        };
        const formatRankedPoints = (value) => Number(value || 0).toLocaleString();
        const normalizeLeaderboard = (items = []) => items.map((item) => ({
            rank: item.rank,
            name: item.name,
            points: item.points || formatRankedPoints(item.score),
            streak: item.streak || 0,
            tier: item.tier || item.tierCode || '',
            self: !!item.self || !!item.isCurrent
        }));
        const normalizeDailyChallenge = (item = {}) => ({
            tag: item.tag || '课程综合 · 图搜索与组成原理',
            title: item.title || '完成 2 道图搜索 / Cache 模拟题目',
            progress: item.total ? Math.round((Number(item.progress || 0) / Number(item.total || 1)) * 100) : Number(item.progress || 50),
            reward: item.reward ? `+${item.reward} 积分` : '+180 积分',
            count: item.total ? `${item.progress || 0}/${item.total}` : item.count || '1/2'
        });
        const normalizeMistakes = (items = []) => items.map((item, index) => ({
            id: item.id || `ranked-mistake-${index}`,
            title: item.title,
            type: item.type || '算法题',
            status: item.risk || item.status || '待复习',
            topic: item.knowledge || item.topic || '',
            count: item.count || `累计出错 ${item.wrongCount || 1} 次`,
            date: item.date || `最近 ${item.lastWrongAt || ''}`,
            issue: item.errorPhenomenon || item.issue || '',
            note: item.note || item.aiAnalysis?.practice || '',
            mastered: item.status === 'mastered' || !!item.mastered,
            badge: item.badge || (index % 2 ? 'blue' : 'gold'),
            aiAnalysis: item.aiAnalysis || null,
            showAnalysis: false,
            analysisLoading: false
        }));
        const normalizeSeasons = (items = []) => items.map((item) => ({
            name: item.title || item.name,
            status: item.status,
            date: item.dateRange || item.date,
            score: item.score ? formatRankedPoints(item.score) : item.score,
            tier: item.tier,
            progress: item.progress || 100,
            winRate: item.winRate || '60%',
            record: item.record || '',
            streak: item.highestStreak || item.streak || 0,
            peak: item.peakTier || item.peak || '',
            rank: item.schoolRank || item.rank || '',
            total: item.total || '',
            reward: item.reward || '赛季奖励已同步。',
            current: item.status === '进行中' || !!item.current
        }));
        const applyRankedDashboard = (data = {}) => {
            if (data.player) {
                Object.assign(rankedPlayer, {
                    name: data.player.name || rankedPlayer.name,
                    className: data.player.className || rankedPlayer.className,
                    tier: data.player.tier || rankedPlayer.tier,
                    points: Number(data.player.score ?? data.player.points ?? rankedPlayer.points),
                    nextTierPoints: Number(data.player.score ?? rankedPlayer.points) + Number(data.player.nextTierNeed ?? 620),
                    streak: Number(data.player.streak ?? rankedPlayer.streak),
                    progress: Number(data.player.progress ?? rankedPlayer.progress)
                });
            }
            if (Array.isArray(data.leaderboard)) leaderboard.value = normalizeLeaderboard(data.leaderboard);
            if (Array.isArray(data.rules)) rankedRules.value = data.rules;
            if (Array.isArray(data.tierLadder)) tierLadder.value = data.tierLadder.map((tier) => ({ ...tier, peak: tier.isPeak || tier.peak, color: tier.color === 'gold' ? 'amber' : tier.color }));
            if (data.dailyChallenge) Object.assign(dailyChallenge, normalizeDailyChallenge(data.dailyChallenge));
        };
        const loadRankedDashboard = async () => {
            try {
                const payload = await rankedApi.getDashboard(getRankedUserId());
                applyRankedDashboard(payload?.data || {});
            } catch (error) {
                console.info('[RankedArena] Dashboard API unavailable, using static fallback.', error);
            }
        };
        const loadRankedHistory = async () => {
            try {
                const payload = await rankedApi.getHistory(getRankedUserId());
                if (Array.isArray(payload?.data)) {
                    matchHistory.value = payload.data.map((item) => ({
                        result: item.result === 'loss' ? '失败' : item.result === 'win' ? '胜利' : '匹配',
                        title: item.title,
                        type: item.type || '算法题',
                        score: item.scoreDelta > 0 ? `+${item.scoreDelta}` : `${item.scoreDelta || 0}`,
                        duration: item.duration || '00分00秒',
                        time: item.createdAt || item.time
                    }));
                }
            } catch (error) {
                console.info('[RankedArena] History API unavailable, using static fallback.', error);
            }
        };
        const loadRankedMistakes = async () => {
            try {
                const payload = await rankedApi.getMistakes(getRankedUserId());
                if (Array.isArray(payload?.data)) rankedMistakes.value = normalizeMistakes(payload.data);
            } catch (error) {
                console.info('[RankedArena] Mistakes API unavailable, using static fallback.', error);
            }
        };
        const loadRankedSeasons = async () => {
            try {
                const payload = await rankedApi.getSeasons(getRankedUserId());
                if (Array.isArray(payload?.data)) seasonList.value = normalizeSeasons(payload.data);
            } catch (error) {
                console.info('[RankedArena] Seasons API unavailable, using static fallback.', error);
            }
        };

        const startRankedMatch = async () => {
            rankedMatchStatus.value = 'matching';
            emit('show-toast', '正在为你匹配同段位算法对手...', 'info');
            try {
                const payload = await rankedApi.startMatch({ userId: getRankedUserId(), mode: 'ranked' });
                if (payload?.data) {
                    currentRankedMatchId.value = payload.data.id || '';
                    // BUG 3 修复：将后端返回的题目数据同步到 rankedProblem，使竞技舱显示真实匹配题目
                    const q = payload.data.question;
                    if (q && q.questionId) {
                        // 从后端描述中提取函数名（取首个 function 关键字后的标识符，否则用 questionId 转驼峰）
                        const funcNameMatch = (q.description || '').match(/function\s+([a-zA-Z_$][\w$]*)\s*\(/);
                        const derivedFuncName = funcNameMatch
                            ? funcNameMatch[1]
                            : q.questionId.replace(/-([a-z])/g, (_, c) => c.toUpperCase()).replace(/^[^a-zA-Z_$]/, '_');
                        // 将 examples 数组转换为前端 testCase 格式
                        const backendTestCases = Array.isArray(q.examples) && q.examples.length > 0
                            ? q.examples.map((ex, i) => ({
                                input: [ex.input],
                                expected: ex.output,
                                label: ex.explanation || `样例 ${i + 1}`
                            }))
                            : rankedProblem.value.testCases; // fallback 到现有样例
                        rankedProblem.value = {
                            id: q.questionId,
                            title: q.title,
                            category: q.category || '通用编程',
                            funcName: derivedFuncName,
                            difficulty: q.difficulty,
                            tags: q.knowledgeTags || [],
                            timeLimitSec: q.timeLimitSec || 1800,
                            desc: q.description || '',
                            inputFormat: q.inputFormat || '',
                            outputFormat: q.outputFormat || '',
                            constraints: q.constraints || '',
                            hint: q.hint || '',
                            scoreReward: q.scoreReward || 50,
                            scorePenalty: q.scorePenalty || 20,
                            starterCode: `function ${derivedFuncName}(...args) {\n    // 在此编写你的代码\n    \n}`,
                            testCases: backendTestCases
                        };
                    }
                    matchHistory.value = [{
                        result: '匹配',
                        title: payload.data.title,
                        type: payload.data.type || '算法题',
                        score: `${payload.data.scoreDelta || 0}`,
                        duration: payload.data.duration || '00分00秒',
                        time: payload.data.createdAt
                    }, ...matchHistory.value];
                }
            } catch (error) {
                currentRankedMatchId.value = '';
                console.info('[RankedArena] Match API unavailable, using local matching state.', error);
            }
            window.setTimeout(() => {
                if (codingMode.value !== 'ranked') return;
                rankedMatchStatus.value = 'ready';
                isRankedEntryConfirmOpen.value = true;
                emit('show-toast', `排位匹配已就绪：${rankedProblem.value.title}`, 'success');
            }, 900);
        };

        const switchRankedTab = (tabId) => {
            rankedTab.value = tabId;
            if (tabId === 'history') loadRankedHistory();
            if (tabId === 'mistakes') loadRankedMistakes();
            if (tabId === 'season') loadRankedSeasons();
        };

        const getLocalMockAnalysis = (item) => {
            const title = item.title || '未知题目';
            const topic = item.topic || '通用算法';
            const issue = item.issue || '未知错误';

            let diagnosis = `针对错误现象“${issue}”，AI 分析认为：可能是在实现「${topic}」时对核心边界条件处理不当，或者在分支转移时逻辑不完备，导致测试用例未通过。`;
            let concept = `核心考察「${topic}」的底层实现。需注意状态初始值的设定、指针移动方向、或容器空间越界问题。`;
            let practice = `建议：\n1. 仔细检查循环控制条件（如双指针收缩或边界递增）；\n2. 增加对空指针或越界索引的防御性判断；\n3. 在本地独立编写 2-3 个边界测试集进行模拟 Debug。`;
            let path = ['复习基础概念', '手写边界用例', '完成同知识点递进练习题'];

            if (title.includes('岛屿数量')) {
                diagnosis = '在执行 DFS/BFS 遍历网格时，未对边界坐标进行先导有效性校验，导致在访问 `grid[r][c]` 时数组越界。此外，需注意对于已访问网格的状态重置或标记，防止产生死循环或栈溢出。';
                concept = '网格搜索算法（DFS/BFS）、连通分量计数、并查集的路径压缩与按秩合并。';
                practice = '建议重点练习：\n1. 防御性边界判断：`r < 0 || r >= R || c < 0 || c >= C || grid[r][c] !== "1"`；\n2. 二维坐标扁平化为一维（并查集常用技巧）：`index = r * C + c`；\n3. 独立尝试 AC「最大人工岛」或「岛屿的周长」。';
            } else if (title.includes('Dijkstra')) {
                diagnosis = '在稀疏图或大规模顶点数据下，未采用「优先队列（最小堆）」进行优化，导致时间复杂度劣化为 O(V²)，从而在稠密数据集中触发 TLE（超时）。';
                concept = '单源最短路径、Dijkstra 算法、堆优化、邻接表与链式前向星的存图方式。';
                practice = '建议重点练习：\n1. 使用 JavaScript 中的自定义 PriorityQueue/Heap 类，将松弛操作后的边自动排序，使提取最近点的时间复杂度降为 O(log V)；\n2. 增加对已访问标志 `visited[u]` 的剪枝判断，避免重复入队；\n3. 独立尝试 AC「网络延迟时间」。';
            } else if (title.includes('二分')) {
                diagnosis = '在收缩搜索区间时，边界更新写成 `lo = mid` 或 `hi = mid`，当区间长度为 2 且 `lo` 与 `mid` 重合时，区间无法继续收缩，导致代码陷入死循环。';
                concept = '二分查找（Binary Search）的区间闭合性与收缩机制。';
                practice = '建议重点练习：\n1. 采用严格的闭区间收缩法则：`lo = mid + 1` 或 `hi = mid - 1`；\n2. 判断死循环的简单方法：手动模拟 `hi - lo == 1` 时情况；\n3. 独立尝试 AC「在排序数组中查找元素的第一个和最后一个位置」。';
            } else if (title.includes('树形DP')) {
                diagnosis = '在不盗窃/不选择当前节点 `u` 的子状态下，错误地认为其子节点必须被盗窃，遗漏了「子节点也不盗窃，但其子树的收益最大」这一分支，导致最优解被低估。';
                concept = '动态规划（Dynamic Programming）、树形 DP、状态转移方程设计。';
                practice = '建议重点练习：\n1. 正确的状态设计：`dp[u][0]` 表示不偷当前节点的最大收益，`dp[u][1]` 表示偷当前节点的最大收益；\n2. 转移方程：`dp[u][0] = sum(max(dp[v][0], dp[v][1]))`；\n3. 独立尝试 AC「打家劫舍 III」。';
            }

            return { diagnosis, concept, practice, path };
        };

        const reviewRankedMistake = async (item) => {
            if (item.analysisLoading) return;

            if (item.showAnalysis) {
                item.showAnalysis = false;
                return;
            }

            item.showAnalysis = true;

            if (item.aiAnalysis) {
                emit('show-toast', `已载入「${item.title}」分析结果`, 'info');
                return;
            }

            rankedTab.value = 'mistakes';
            item.analysisLoading = true;
            emit('show-toast', `正在为「${item.title}」分析错题...`, 'info');
            const rankedCoachConfig = getRankedCoachConfig();
            try {
                const payload = await rankedApi.analyzeMistake(item.id || item.title, {
                    userId: getRankedUserId(),
                    agentId: rankedCoachConfig.id || 'agent_ranked_coach',
                    agentName: rankedCoachConfig.name || '排位赛AI教练',
                    agentModel: rankedCoachConfig.model,
                    agentPrompt: rankedCoachConfig.prompt,
                    context: { title: item.title, issue: item.issue, topic: item.topic }
                });
                if (payload?.data) {
                    item.aiAnalysis = payload.data;
                    item.note = payload.data.practice || item.note;
                } else {
                    throw new Error('Empty payload');
                }
            } catch (error) {
                console.info('[RankedArena] Mistake AI API unavailable, using local mock builder.', error);
                item.aiAnalysis = getLocalMockAnalysis(item);
                item.note = item.aiAnalysis.practice || item.note;
            } finally {
                item.analysisLoading = false;
            }
        };

        const deleteRankedMistake = async (item) => {
            if (!item?.id) return;
            try {
                await rankedApi.deleteMistake(item.id, getRankedUserId());
                rankedMistakes.value = rankedMistakes.value.filter(mistake => mistake.id !== item.id);
                emit('show-toast', `已从错题管理中移除「${item.title}」`, 'success');
            } catch (error) {
                console.info('[RankedArena] Delete mistake API unavailable.', error);
                emit('show-toast', `删除错题失败：${error?.message || '后端服务暂不可用'}`, 'error');
            }
        };

        const scrollToBottom = () => {
            nextTick(() => {
                if (rankedCoachChatScroll.value) {
                    rankedCoachChatScroll.value.scrollTop = rankedCoachChatScroll.value.scrollHeight;
                }
            });
        };

        // ==================== 排位竞技答题舱控制逻辑 ====================
        const rankedDeepEqual = (a, b) => JSON.stringify(a) === JSON.stringify(b);

        const requestRankedFullscreen = async () => {
            if (document.fullscreenElement) return true;
            if (!document.documentElement?.requestFullscreen) {
                emit('show-toast', '当前浏览器不支持全屏模式，无法进入竞技答题舱', 'error');
                return false;
            }
            try {
                await document.documentElement.requestFullscreen();
                return true;
            } catch (error) {
                emit('show-toast', '请允许浏览器进入全屏模式后再开始竞技', 'error');
                return false;
            }
        };

        const exitRankedFullscreenIfNeeded = async () => {
            if (document.fullscreenElement && document.exitFullscreen) {
                await document.exitFullscreen().catch(() => { });
            }
        };

        const confirmRankedEntry = async () => {
            isRankedEntryConfirmOpen.value = false;
            const fullscreenReady = await requestRankedFullscreen();
            if (!fullscreenReady) {
                emit('show-toast', '进入全屏失败，无法进入竞技舱', 'error');
                return;
            }
            enterRankedArena();
        };

        const cancelRankedEntry = () => {
            isRankedEntryConfirmOpen.value = false;
            rankedMatchStatus.value = 'idle';
        };

        const enterRankedArena = () => {
            rankedRoomMode.value = 'arena';
            // BUG 4 修复：优先使用后端返回的时限，fallback 为 30 分钟
            rankedRemainingSeconds.value = rankedProblem.value.timeLimitSec
                ? Number(rankedProblem.value.timeLimitSec)
                : 1800;
            rankedBlurViolationCount.value = 0;
            rankedOpponentStatus.value = '正在构思解题思路...';
            rankedOpponentProgress.value = 0;
            isRankedSettlementOpen.value = false;
            rankedMatchResult.value = null;
            rankedConsoleLogs.value = [];
            rankedActiveTab.value = 'cases';

            // 初始化用户初始代码
            rankedAnswers.value[rankedProblem.value.id] = rankedProblem.value.starterCode;

            // 初始化样例结果
            initRankedTestCaseResults();

            // 绑定安全监控
            bindRankedSecurityGuards();

            // 启动定时器
            initRankedTimer();
            initOpponentProgressSimulation();

            // 延迟初始化编辑器，确保DOM已挂载
            nextTick(() => {
                initRankedMonaco();
            });
        };

        const initRankedTestCaseResults = () => {
            rankedTestCaseResults.value = rankedProblem.value.testCases.map((tc, index) => ({
                label: tc.label || `样例 ${index + 1}`,
                input: tc.input,
                expected: tc.expected,
                actual: null,
                status: 'pending',
                error: null
            }));
        };

        const exitRankedArena = async () => {
            unbindRankedSecurityGuards();
            rankedRoomMode.value = 'lobby';
            rankedMatchStatus.value = 'idle';
            destroyRankedEditor();

            if (rankedTimer) clearInterval(rankedTimer);
            if (opponentTimer) clearInterval(opponentTimer);
            rankedTimer = null;
            opponentTimer = null;

            await exitRankedFullscreenIfNeeded();
        };

        // 防作弊安全规则
        let rankedSecurityListenersBound = false;
        let rankedSecurityAutoSubmitting = false;
        let rankedSecurityToastLocked = false;
        const MAX_RANKED_BLUR_VIOLATIONS = 3;
        const MAX_RANKED_BLUR_DURATION_MS = 10000;
        let lastRankedBlurTime = null;

        const showRankedRestrictedToast = (message) => {
            if (rankedSecurityToastLocked) return;
            rankedSecurityToastLocked = true;
            emit('show-toast', message, 'error');
            window.setTimeout(() => {
                rankedSecurityToastLocked = false;
            }, 1400);
        };

        const preventRankedRestrictedOperation = (event) => {
            if (!rankedSecurityActive.value) return;
            event.preventDefault();
            event.stopPropagation();
            showRankedRestrictedToast('竞技期间已禁用复制、粘贴、右键菜单和截图相关操作');
        };

        const handleRankedSecurityKeydown = (event) => {
            if (!rankedSecurityActive.value) return;
            const key = (event.key || '').toLowerCase();
            const hasCommandModifier = event.ctrlKey || event.metaKey;
            const blockedShortcut = hasCommandModifier && ['a', 'c', 'p', 's', 'u', 'v', 'x'].includes(key);
            const blockedSystemKey = ['escape', 'f11', 'printscreen'].includes(key);
            const blockedAltTab = event.altKey && key === 'tab';

            if (blockedShortcut || blockedSystemKey || blockedAltTab) {
                event.preventDefault();
                event.stopPropagation();
                if (key === 'printscreen') {
                    navigator.clipboard?.writeText?.('').catch(() => { });
                }
                showRankedRestrictedToast('竞技期间已拦截受限快捷键');
            }
        };

        const handleRankedVisibilityChange = () => {
            if (rankedSecurityActive.value && document.visibilityState === 'hidden') {
                autoResolveForRankedSecurity('切出竞技窗口');
            }
        };

        const handleRankedFullscreenChange = () => {
            if (rankedSecurityActive.value && rankedRoomMode.value === 'arena' && !document.fullscreenElement) {
                autoResolveForRankedSecurity('退出全屏模式');
            }
        };

        const handleRankedWindowBlur = (event) => {
            if (event && event.target !== window && event.target !== document) return;
            if (rankedSecurityActive.value && rankedRoomMode.value === 'arena') {
                lastRankedBlurTime = Date.now();
                rankedBlurViolationCount.value++;
            }
        };

        const handleRankedWindowFocus = (event) => {
            if (event && event.target !== window && event.target !== document) return;
            if (!rankedSecurityActive.value || rankedRoomMode.value !== 'arena' || !lastRankedBlurTime) return;

            const blurDuration = Date.now() - lastRankedBlurTime;
            lastRankedBlurTime = null;

            if (blurDuration > MAX_RANKED_BLUR_DURATION_MS) {
                autoResolveForRankedSecurity('切出竞技界面超过 10 秒');
                return;
            }

            if (rankedBlurViolationCount.value >= MAX_RANKED_BLUR_VIOLATIONS) {
                autoResolveForRankedSecurity(`累计切出竞技界面 ${MAX_RANKED_BLUR_VIOLATIONS} 次`);
                return;
            }

            showRankedRestrictedToast(`警告：您已切出竞技界面 ${rankedBlurViolationCount.value} 次，满 ${MAX_RANKED_BLUR_VIOLATIONS} 次将自动判负`);
        };

        const bindRankedSecurityGuards = () => {
            rankedSecurityActive.value = true;
            rankedSecurityAutoSubmitting = false;
            if (rankedSecurityListenersBound) return;
            document.addEventListener('copy', preventRankedRestrictedOperation, true);
            document.addEventListener('cut', preventRankedRestrictedOperation, true);
            document.addEventListener('paste', preventRankedRestrictedOperation, true);
            document.addEventListener('contextmenu', preventRankedRestrictedOperation, true);
            document.addEventListener('keydown', handleRankedSecurityKeydown, true);
            document.addEventListener('visibilitychange', handleRankedVisibilityChange, true);
            document.addEventListener('fullscreenchange', handleRankedFullscreenChange, true);
            window.addEventListener('blur', handleRankedWindowBlur, false);
            window.addEventListener('focus', handleRankedWindowFocus, false);
            rankedSecurityListenersBound = true;
        };

        const unbindRankedSecurityGuards = () => {
            rankedSecurityActive.value = false;
            if (!rankedSecurityListenersBound) return;
            document.removeEventListener('copy', preventRankedRestrictedOperation, true);
            document.removeEventListener('cut', preventRankedRestrictedOperation, true);
            document.removeEventListener('paste', preventRankedRestrictedOperation, true);
            document.removeEventListener('contextmenu', preventRankedRestrictedOperation, true);
            document.removeEventListener('keydown', handleRankedSecurityKeydown, true);
            document.removeEventListener('visibilitychange', handleRankedVisibilityChange, true);
            document.removeEventListener('fullscreenchange', handleRankedFullscreenChange, true);
            window.removeEventListener('blur', handleRankedWindowBlur, false);
            window.removeEventListener('focus', handleRankedWindowFocus, false);
            rankedSecurityListenersBound = false;
        };

        const autoResolveForRankedSecurity = (reason) => {
            if (!rankedSecurityActive.value || rankedSecurityAutoSubmitting || rankedRoomMode.value !== 'arena') return;
            rankedSecurityAutoSubmitting = true;
            emit('show-toast', `触发安全违规：${reason}，本场排位将被判负`, 'error');

            // 提交代码结果并自动计算扣除积分
            resolveRankedMatch('cheat_lose', reason);
        };

        // Monaco 编辑器控制
        const initRankedMonaco = () => {
            isRankedEditorLoading.value = true;
            if (window.monaco) {
                createRankedEditorInstance();
                return;
            }
            if (window.require) {
                window.require.config({ paths: { vs: 'https://s4.zstatic.net/ajax/libs/monaco-editor/0.39.0/min/vs' } });
                window.require(['vs/editor/editor.main'], createRankedEditorInstance);
            } else {
                isRankedEditorLoading.value = false;
                useRankedPlainEditor.value = true;
            }
        };

        const createRankedEditorInstance = () => {
            const container = document.getElementById('monaco-editor-container-ranked');
            if (!container) return;
            isRankedEditorLoading.value = false;

            destroyRankedEditor();

            const saved = rankedAnswers.value[rankedProblem.value.id] || rankedProblem.value.starterCode;
            rankedMonacoEditor = window.monaco.editor.create(container, {
                value: saved,
                language: 'javascript',
                theme: 'vs',
                fontSize: 14,
                minimap: { enabled: false },
                automaticLayout: true,
                scrollBeyondLastLine: false,
                fontFamily: 'Consolas, "Courier New", monospace'
            });

            rankedMonacoEditor.onDidChangeModelContent(() => {
                rankedAnswers.value[rankedProblem.value.id] = rankedMonacoEditor.getValue();
            });
        };

        const destroyRankedEditor = () => {
            if (rankedMonacoEditor) {
                rankedMonacoEditor.dispose();
                rankedMonacoEditor = null;
            }
        };

        const getRankedEditorCode = () => {
            if (rankedMonacoEditor) return rankedMonacoEditor.getValue();
            return rankedAnswers.value[rankedProblem.value.id] || rankedProblem.value.starterCode || '';
        };

        const setRankedEditorCode = (code) => {
            if (rankedMonacoEditor) rankedMonacoEditor.setValue(code);
            rankedAnswers.value[rankedProblem.value.id] = code;
        };

        // 运行测试用例
        const runRankedCode = async () => {
            if (isRankedRunning.value) return;
            isRankedRunning.value = true;
            rankedActiveTab.value = 'cases';
            rankedConsoleLogs.value = [];

            rankedTestCaseResults.value = rankedTestCaseResults.value.map(item => ({
                ...item,
                status: 'running',
                actual: null,
                error: null
            }));
            await nextTick();

            const code = getRankedEditorCode();
            rankedAnswers.value[rankedProblem.value.id] = code;

            const logs = [];
            const fakeConsole = {
                log: (...items) => logs.push(items.map(item => typeof item === 'object' ? JSON.stringify(item) : String(item)).join(' '))
            };

            rankedTestCaseResults.value = rankedTestCaseResults.value.map((item) => {
                try {
                    // BUG 1 修复：不再使用 arguments[1] 硬编码传参，改为展开 item.input 数组以支持多参数题目
                    const funcName = rankedProblem.value.funcName;
                    const funcExtractBody = `${code}; return typeof ${funcName} === 'function' ? ${funcName} : undefined;`;
                    const extractor = new Function('console', funcExtractBody);
                    const userFunc = extractor(fakeConsole);
                    if (typeof userFunc !== 'function') {
                        throw new Error(`函数 "${funcName}" 未定义，请确保不要修改模板中的函数名称`);
                    }
                    // 将 input 数组展开为多参数传入，兼容单参数和多参数题目
                    const inputArgs = Array.isArray(item.input) ? item.input : [item.input];
                    const actual = userFunc(...inputArgs);

                    const isPassed = rankedDeepEqual(actual, item.expected);

                    return {
                        ...item,
                        actual,
                        status: isPassed ? 'passed' : 'failed',
                        error: isPassed ? '' : `期望: ${JSON.stringify(item.expected)}, 实际: ${JSON.stringify(actual)}`
                    };
                } catch (error) {
                    return {
                        ...item,
                        actual: null,
                        status: 'error',
                        error: error.toString()
                    };
                }
            });

            rankedConsoleLogs.value = logs.length ? logs : ['运行完成。公开测试用例已评估完毕。'];
            isRankedRunning.value = false;

            const passed = rankedTestCaseResults.value.filter(item => item.status === 'passed').length;
            emit('show-toast', `测试用例通过 ${passed}/${rankedTestCaseResults.value.length}`, passed === rankedTestCaseResults.value.length ? 'success' : 'error');
        };

        const formatDuration = (seconds) => {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        };

        // 计时器与对手进度更新
        const initRankedTimer = () => {
            if (rankedTimer) clearInterval(rankedTimer);
            rankedTimer = setInterval(() => {
                rankedRemainingSeconds.value = Math.max(0, rankedRemainingSeconds.value - 1);
                if (rankedRemainingSeconds.value === 0) {
                    clearInterval(rankedTimer);
                    emit('show-toast', '竞技答题舱倒计时结束！将自动结算答题结果', 'error');
                    submitRankedMatch();
                }
            }, 1000);
        };

        const initOpponentProgressSimulation = () => {
            if (opponentTimer) clearInterval(opponentTimer);
            let elapsed = 0;
            rankedOpponentStatus.value = '对方正在构思解题思路...';
            rankedOpponentProgress.value = 0;

            opponentTimer = setInterval(() => {
                elapsed += 5;
                if (elapsed >= 5 && elapsed < 15) {
                    rankedOpponentStatus.value = '对方正在构思解题思路...';
                    rankedOpponentProgress.value = 0;
                } else if (elapsed >= 15 && elapsed < 40) {
                    rankedOpponentStatus.value = '对方正在编写核心代码...';
                    rankedOpponentProgress.value = 0;
                } else if (elapsed >= 40 && elapsed < 90) {
                    rankedOpponentStatus.value = '对方已运行测试，正在调试用例: 1/2 通过';
                    rankedOpponentProgress.value = 50;
                } else if (elapsed >= 90 && elapsed < 150) {
                    rankedOpponentStatus.value = '对方正在优化临界条件与淘汰策略...';
                    rankedOpponentProgress.value = 50;
                } else if (elapsed >= 150 && elapsed < 180) {
                    rankedOpponentStatus.value = '对方已通过全部公开用例，正在分析时空复杂度...';
                    rankedOpponentProgress.value = 100;
                } else if (elapsed >= 180) {
                    rankedOpponentStatus.value = '对方已提交代码并进入挂机等待状态。';
                    rankedOpponentProgress.value = 100;
                    clearInterval(opponentTimer);
                }
            }, 5000);
        };

        // 答卷提交与结算
        const submitRankedMatch = async () => {
            await runRankedCode();
            const allPassed = rankedTestCaseResults.value.every(item => item.status === 'passed');
            const resultType = allPassed ? 'win' : 'lose';
            resolveRankedMatch(resultType);
        };

        const resolveRankedMatch = async (resultType, cheatReason = '') => {
            unbindRankedSecurityGuards();

            if (rankedTimer) clearInterval(rankedTimer);
            if (opponentTimer) clearInterval(opponentTimer);
            rankedTimer = null;
            opponentTimer = null;

            rankedMatchResult.value = resultType;
            isRankedSettlementOpen.value = true;

            await exitRankedFullscreenIfNeeded();

            const code = getRankedEditorCode();
            const elapsedSeconds = Math.max(0, Number(rankedProblem.value.timeLimitSec || 1800) - Number(rankedRemainingSeconds.value || 0));
            const passedCount = rankedTestCaseResults.value.filter(item => item.status === 'passed').length;
            const totalCount = rankedTestCaseResults.value.length;
            let backendSettlement = null;

            if (currentRankedMatchId.value) {
                try {
                    const payload = await rankedApi.submitMatch(currentRankedMatchId.value, {
                        userId: getRankedUserId(),
                        result: resultType === 'lose' ? 'loss' : resultType,
                        code,
                        durationSeconds: elapsedSeconds,
                        passedCount,
                        totalCount,
                        testResults: rankedTestCaseResults.value.map(item => ({
                            label: item.label,
                            input: item.input,
                            expected: item.expected,
                            actual: item.actual,
                            status: item.status,
                            error: item.error || ''
                        })),
                        cheatReason
                    });
                    backendSettlement = payload?.data || null;
                } catch (error) {
                    console.info('[RankedArena] Submit API unavailable; settlement is not backend-synced.', error);
                    emit('show-toast', `排位结算同步后端失败：${error?.message || '后端服务暂不可用'}`, 'error');
                }
            }

            let pointsDelta = backendSettlement?.match?.scoreDelta ?? 0;
            if (backendSettlement?.profile) {
                rankedPlayer.points = Number(backendSettlement.profile.score ?? rankedPlayer.points);
                rankedPlayer.streak = Number(backendSettlement.profile.streak ?? rankedPlayer.streak);
                rankedPlayer.progress = Number(backendSettlement.profile.progress ?? rankedPlayer.progress);
                if (backendSettlement.profile.tier) rankedPlayer.tier = backendSettlement.profile.tier;
            } else if (resultType === 'win') {
                pointsDelta = 231;
                rankedPlayer.streak++;
                rankedPlayer.points += pointsDelta;
                rankedPlayer.progress = Math.min(100, Math.floor(((rankedPlayer.points - 1600) / 1000) * 100));
            } else {
                pointsDelta = -100;
                rankedPlayer.streak = 0;
                rankedPlayer.points = Math.max(0, rankedPlayer.points + pointsDelta);
                rankedPlayer.progress = Math.min(100, Math.floor(((rankedPlayer.points - 1600) / 1000) * 100));
            }

            if (resultType === 'win') {
                emit('show-toast', `恭喜！战胜对手，获得 ${pointsDelta > 0 ? '+' : ''}${pointsDelta} 积分！`, 'success');
            } else if (resultType === 'cheat_lose') {
                emit('show-toast', `因「${cheatReason}」违规判定为负，积分 ${pointsDelta}`, 'error');
            } else {
                emit('show-toast', `挑战未通过，积分 ${pointsDelta}`, 'error');
            }

            const timeNow = new Date();
            const timeStr = `${timeNow.getMonth() + 1}月${timeNow.getDate()}日 ${String(timeNow.getHours()).padStart(2, '0')}:${String(timeNow.getMinutes()).padStart(2, '0')}`;
            const settledMatch = backendSettlement?.match;

            matchHistory.value = [{
                result: resultType === 'win' ? '胜利' : '失败',
                title: settledMatch?.title || rankedProblem.value.title,
                type: settledMatch?.type || '算法题',
                score: pointsDelta > 0 ? `+${pointsDelta}` : `${pointsDelta}`,
                duration: settledMatch?.duration || `${Math.floor(elapsedSeconds / 60)}分${elapsedSeconds % 60}秒`,
                time: settledMatch?.submittedAt || timeStr
            }, ...matchHistory.value];

            if (backendSettlement?.mistake) {
                const normalized = normalizeMistakes([backendSettlement.mistake])[0];
                const existingIndex = rankedMistakes.value.findIndex(item => item.id === normalized.id);
                if (existingIndex >= 0) rankedMistakes.value.splice(existingIndex, 1, normalized);
                else rankedMistakes.value.unshift(normalized);
            }
        };

        const closeRankedSettlement = () => {
            isRankedSettlementOpen.value = false;
            rankedRoomMode.value = 'lobby';
            rankedMatchStatus.value = 'idle';
            destroyRankedEditor();
        };

        const askRankedCoach = async (prompt = '') => {
            if (isRankedCoachLoading.value) return;
            const isUserQuestion = !prompt;
            rankedCoachInput.value = prompt || rankedCoachInput.value;
            rankedCoachOpen.value = true;
            isRankedCoachLoading.value = true;
            scrollToBottom();

            const rankedCoachConfig = getRankedCoachConfig();
            try {
                const payload = await rankedApi.askCoach({
                    userId: getRankedUserId(),
                    agentId: rankedCoachConfig.id || 'agent_ranked_coach',
                    agentName: rankedCoachConfig.name || '排位赛AI教练',
                    agentModel: rankedCoachConfig.model,
                    agentPrompt: rankedCoachConfig.prompt,
                    question: rankedCoachInput.value || '分析我的排位',
                    context: { player: rankedPlayer, tab: rankedTab.value }
                });
                if (payload?.data?.answer) {
                    coachSuggestions.value = String(payload.data.answer).split('\n').filter(Boolean);
                }
                emit('show-toast', `排位 AI 教练已使用 ${payload?.data?.model || rankedCoachConfig.model} 生成建议`, 'info');
                if (isUserQuestion) {
                    rankedCoachInput.value = '';
                }
            } catch (error) {
                console.info('[RankedArena] Coach API unavailable, using static suggestions.', error);
                emit('show-toast', '排位 AI 教练已打开，本地建议可先参考', 'info');
                if (isUserQuestion) {
                    rankedCoachInput.value = '';
                }
            } finally {
                isRankedCoachLoading.value = false;
                scrollToBottom();
            }
        };

        const switchMode = (mode) => {
            if (monacoEditor) {
                monacoEditor.dispose();
                monacoEditor = null;
            }
            codingMode.value = mode;
            nextTick(() => {
                if (mode === 'practice') {
                    initMonaco();
                } else if (mode === 'homework') {
                    initMonaco();
                    handleHomeworkChange();
                } else if (mode === 'collab') {
                    collabViewMode.value = 'list';
                    loadTeamGiteaIdentity();
                    loadCollabProjects();
                } else if (mode === 'ranked') {
                    rankedTab.value = 'lobby';
                    rankedMatchStatus.value = 'idle';
                    rankedCoachOpen.value = false;
                    rankedRoomMode.value = 'lobby';
                    isRankedEntryConfirmOpen.value = false;
                    isRankedExitConfirmOpen.value = false;
                    isRankedSettlementOpen.value = false;
                    rankedSecurityActive.value = false;
                    loadRankedDashboard();
                }
            });
        };

        const goBackToLobby = () => {
            if (monacoEditor) {
                monacoEditor.dispose();
                monacoEditor = null;
            }
            exitRankedArena();
            codingMode.value = null;
        };

        const runHomeworkTest = () => {
            if (runHomeworkTesting.value) return;
            runHomeworkTesting.value = true;
            activeHomeworkConsoleLogs.value = [];
            activeHomeworkConsoleLogs.value.push('[Compiler] 启动 JavaScript 作业编译器...', '[Console] 挂接测试用例中...');

            setTimeout(() => {
                runHomeworkTesting.value = false;
                const code = homeworkCode.value;
                const hw = selectedHomework.value;
                if (!hw) return;

                try {
                    if (hw.id === 'hw-daily-01') {
                        const hasProxy = code.includes('Proxy');
                        const hasReflect = code.includes('Reflect');
                        if (hasProxy) {
                            activeHomeworkConsoleLogs.value.push('[Console] Success: 用例 reactive({a:1}).a 运行拦截成功！');
                            if (hasReflect) {
                                activeHomeworkConsoleLogs.value.push('[Console] Success: 包含 Reflect 拦截，this 防重定位测试通过。');
                                emit('show-toast', '作业算法用例全部跑通！', 'success');
                            } else {
                                activeHomeworkConsoleLogs.value.push('[Console] Warn: 未检测到 Reflect，原型链继承测试失败！');
                                emit('show-toast', '测试通过，但存在安全警告', 'error');
                            }
                        } else {
                            activeHomeworkConsoleLogs.value.push('[Console] Error: 未发现 Proxy 拦截。');
                            emit('show-toast', '用例测试未通过', 'error');
                        }
                    } else {
                        activeHomeworkConsoleLogs.value.push('[Console] Success: 所有本地用例跑通，时空消耗符合 O(1) 原地要求！');
                        emit('show-toast', '用例测试全部跑通！', 'success');
                    }
                } catch (e) {
                    activeHomeworkConsoleLogs.value.push(`[Console] Error: \${e.message}`);
                }
            }, 1200);
        };

        const handleHomeworkDiagnose = async () => {
            if (submitHomeworkLoading.value) return;
            submitHomeworkLoading.value = true;
            emit('show-toast', '正在请求 AI 多智能体联合会诊...', 'info');

            try {
                const hw = selectedHomework.value;
                if (hw && currentHomeworkQuestion.value) {
                    const answers = { ...hw.submittedAnswers, q3: homeworkCode.value };
                    const diag = await homeworkApi.requestAgentDiagnosis(hw.id, answers);
                    homeworkDiagnosis.value = diag;

                    homeworkRadarOption.value = {
                        radar: {
                            indicator: [
                                { name: '规划对齐力 (Alina)', max: 100 },
                                { name: '代码工程力 (Ninja)', max: 100 },
                                { name: '理论完备度 (Prof. X)', max: 100 }
                            ],
                            splitNumber: 4,
                            axisLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.1)' } },
                            splitLine: { lineStyle: { color: 'rgba(28, 43, 56, 0.08)' } },
                            splitArea: { areaStyle: { color: ['rgba(255,255,255,0.4)', 'rgba(255,255,255,0.2)'] } }
                        },
                        series: [{
                            type: 'radar',
                            data: [{
                                value: [diag.scores.alina, diag.scores.codeninja, diag.scores.profx],
                                name: '协同评估',
                                areaStyle: { color: 'rgba(99, 102, 241, 0.12)' },
                                lineStyle: { color: '#6366f1', width: 2 },
                                itemStyle: { color: '#6366f1' }
                            }]
                        }]
                    };
                    emit('show-toast', '联合会诊诊断报告已生成！', 'success');
                }
            } catch (err) {
                emit('show-toast', '请求智能体服务失败', 'error');
            } finally {
                submitHomeworkLoading.value = false;
            }
        };

        const submitHomeworkAssignment = async () => {
            const hw = selectedHomework.value;
            if (!hw) return;
            submitHomeworkLoading.value = true;
            emit('show-toast', '正在递交作业成果...', 'info');

            try {
                const answers = { ...hw.submittedAnswers, q3: homeworkCode.value };
                await homeworkApi.submitHomework(hw.id, {
                    studentName: props.currentUser?.username || '李明',
                    answers,
                    file: null
                });
                hw.status = 'submitted';
                if (typeof window !== 'undefined') {
                    window.dispatchEvent(new CustomEvent('homework-submitted', {
                        detail: { homeworkId: hw.id }
                    }));
                }
                emit('show-toast', '编程作业已递交，等待教师评定', 'success');
            } catch (err) {
                emit('show-toast', '作业提交失败', 'error');
            } finally {
                submitHomeworkLoading.value = false;
            }
        };

        const categoriesOrder = [
            '数组与链表',
            '栈与队列',
            '树与二叉树',
            '排序与搜索',
            '字符串与双指针',
            '动态规划',
            '贪心与回溯',
            '数学与趣味算法'
        ];

        const groupedProblems = computed(() => {
            const groups = {};
            problems.value.forEach(prob => {
                const cat = prob.category || '其它';
                if (!groups[cat]) {
                    groups[cat] = [];
                }
                groups[cat].push(prob);
            });

            const orderedGroups = [];
            categoriesOrder.forEach(cat => {
                if (groups[cat]) {
                    orderedGroups.push({
                        category: cat,
                        problems: groups[cat]
                    });
                }
            });

            Object.keys(groups).forEach(cat => {
                if (!categoriesOrder.includes(cat)) {
                    orderedGroups.push({
                        category: cat,
                        problems: groups[cat]
                    });
                }
            });

            return orderedGroups;
        });

        const problemStatuses = ref({});

        const updateStatuses = () => {
            problems.value.forEach(p => {
                problemStatuses.value[p.id] = localStorage.getItem(`coding_status_${p.id}`) || 'unstarted';
            });
        };

        const getProblemSelectLabel = (prob) => {
            const status = problemStatuses.value[prob.id] || 'unstarted';
            let icon = '⚪';
            if (status === 'passed') icon = '🟢';
            else if (status === 'failed') icon = '🔴';

            let diffLabel = '';
            if (prob.difficulty === 'Easy') diffLabel = '简单';
            else if (prob.difficulty === 'Medium') diffLabel = '中等';
            else if (prob.difficulty === 'Hard') diffLabel = '困难';

            return `${icon} [${diffLabel}] ${prob.title}`;
        };
        const editorContainer = ref(null);
        const isEditorLoading = ref(true);
        const isRunning = ref(false);
        const consoleLogs = ref([]);
        const isAiAnalyzing = ref(false);
        const aiReviewText = ref('');
        const activeTab = ref('cases'); // 'cases' | 'console'
        const activePanelTab = ref('current'); // 'current' | 'history'
        const historyList = ref([]);
        const tempHistoryCode = ref('');
        const isPanelOpen = ref(false);

        const panelStyle = ref({
            top: 'calc(20% + 20px)',
            left: 'calc(42% + 40px)',
            right: '20px',
            bottom: '20px',
            width: 'auto',
            height: 'auto',
            position: 'absolute'
        });

        watch(aiReviewText, (newVal) => {
            if (newVal) {
                isPanelOpen.value = true;
            }
        });

        watch(isAiAnalyzing, (newVal) => {
            if (newVal) {
                isPanelOpen.value = true;
            }
        });

        const openAiPanel = () => {
            isPanelOpen.value = true;
            if (!aiReviewText.value && !isAiAnalyzing.value) {
                activePanelTab.value = 'menu';
            }
        };

        const closePanel = () => {
            isPanelOpen.value = false;
            aiReviewText.value = '';
            activePanelTab.value = 'current';
            tempHistoryCode.value = '';
            isAiAnalyzing.value = false;
            if (typingTimer) {
                clearInterval(typingTimer);
                typingTimer = null;
            }
            panelStyle.value = {
                top: 'calc(20% + 20px)',
                left: 'calc(42% + 40px)',
                right: '20px',
                bottom: '20px',
                width: 'auto',
                height: 'auto',
                position: 'absolute'
            };
        };

        const startReviewFromMenu = () => {
            activePanelTab.value = 'current';
            getAiReview();
        };

        const showHistoryFromMenu = async () => {
            activePanelTab.value = 'history';
            await fetchHistoryList();
        };

        const fetchHistoryList = async () => {
            const username = props.currentUser?.username || 'guest_user';
            try {
                const data = await profileApi.getDiagnosisHistory(username);
                if (data && data.status === 'success') {
                    historyList.value = data.data || [];
                }
            } catch (err) {
                console.error("获取诊断历史失败:", err);
            }
        };

        const toggleHistoryView = async () => {
            if (activePanelTab.value === 'history') {
                if (aiReviewText.value || isAiAnalyzing.value) {
                    activePanelTab.value = 'current';
                } else {
                    activePanelTab.value = 'menu';
                }
            } else {
                activePanelTab.value = 'history';
                await fetchHistoryList();
            }
        };

        const viewHistoryDetail = (item) => {
            tempHistoryCode.value = item.user_code || '';
            aiReviewText.value = `> [!NOTE]  
> 🕒 **这是您在 ${formatDisplayDateTime(item.created_at)} 针对题目「${item.problem_title}」生成的历史诊断报告**。  
> 您可以点击顶部的 **「恢复当时代码」** 按钮将当时的代码恢复到编辑器中。  

` + item.diagnosis_result;
            activePanelTab.value = 'current';
        };

        const restoreHistoryCode = () => {
            if (!tempHistoryCode.value) return;
            if (confirm('确定要恢复该历史版本的代码到当前编辑器吗？当前编辑器中的修改将被覆写。')) {
                if (monacoEditor) {
                    monacoEditor.setValue(tempHistoryCode.value);
                    emit('show-toast', '已成功恢复历史提交代码！', 'success');
                }
            }
        };

        const dragStart = (e) => {
            if (e.target.closest('button')) return;
            const panelEl = e.currentTarget.closest('.glass-panel-liquid');
            if (!panelEl) return;

            const rect = panelEl.getBoundingClientRect();
            const parentEl = panelEl.offsetParent || document.body;
            const parentRect = parentEl.getBoundingClientRect();

            const initialWidth = rect.width;
            const initialHeight = rect.height;
            const initialLeft = rect.left - parentRect.left;
            const initialTop = rect.top - parentRect.top;

            panelStyle.value = {
                position: 'absolute',
                left: `${initialLeft}px`,
                top: `${initialTop}px`,
                width: `${initialWidth}px`,
                height: `${initialHeight}px`,
                right: 'auto',
                bottom: 'auto'
            };

            const startX = e.clientX;
            const startY = e.clientY;

            const handleMouseMove = (moveEvent) => {
                const deltaX = moveEvent.clientX - startX;
                const deltaY = moveEvent.clientY - startY;

                let newLeft = initialLeft + deltaX;
                let newTop = initialTop + deltaY;

                // 拖到任意位置：防丢边界限制（允许大部分移出，保留至少 100px 贴边，顶部不能完全移出）
                const minLeft = -initialWidth + 100;
                const maxLeft = parentRect.width - 100;
                const minTop = 0;
                const maxTop = parentRect.height - 40;

                newLeft = Math.max(minLeft, Math.min(newLeft, maxLeft));
                newTop = Math.max(minTop, Math.min(newTop, maxTop));

                panelStyle.value.left = `${newLeft}px`;
                panelStyle.value.top = `${newTop}px`;
            };

            const handleMouseUp = () => {
                window.removeEventListener('mousemove', handleMouseMove);
                window.removeEventListener('mouseup', handleMouseUp);
                document.body.style.userSelect = '';
            };

            document.body.style.userSelect = 'none';
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        };

        let monacoEditor = null;
        let worker = null;
        let typingTimer = null;

        const currentProblem = computed(() => {
            return problems.value.find(p => p.id === selectedProblemId.value) || problems.value[0];
        });

        // 格式化题目描述的 Markdown
        const parsedDesc = computed(() => {
            if (window.marked && typeof window.marked.parse === 'function') {
                return window.marked.parse(currentProblem.value.desc);
            }
            return currentProblem.value.desc;
        });

        // 保存各个题目的用户编写代码，防止切换题目丢失
        const userCodes = ref({});

        // 存储各个用例的运行结果
        const testCaseResults = ref([]);

        // 初始化用例状态
        const initTestCaseResults = () => {
            testCaseResults.value = currentProblem.value.testCases.map(tc => ({
                label: tc.label,
                input: tc.input,
                expected: tc.expected,
                actual: null,
                status: 'pending', // 'pending' | 'passed' | 'failed' | 'error'
                error: null
            }));
            consoleLogs.value = [];
        };

        // 深度判等函数
        const deepEqual = (a, b) => {
            if (a === b) return true;
            if (a == null || b == null) return false;
            if (typeof a !== typeof b) return false;
            if (Array.isArray(a) && Array.isArray(b)) {
                if (a.length !== b.length) return false;
                for (let i = 0; i < a.length; i++) {
                    if (!deepEqual(a[i], b[i])) return false;
                }
                return true;
            }
            if (typeof a === 'object' && typeof b === 'object') {
                const keysA = Object.keys(a);
                const keysB = Object.keys(b);
                if (keysA.length !== keysB.length) return false;
                for (let key of keysA) {
                    if (!keysB.includes(key) || !deepEqual(a[key], b[key])) return false;
                }
                return true;
            }
            return false;
        };

        // 异步加载并初始化 Monaco Editor
        const initMonaco = () => {
            // 配置 Monaco 跨域 Worker 代理，防止跨域报错
            window.MonacoEnvironment = {
                getWorkerUrl: function (workerId, label) {
                    return `data:text/javascript;charset=utf-8,${encodeURIComponent(`
                        self.MonacoEnvironment = {
                            baseUrl: 'https://s4.zstatic.net/ajax/libs/monaco-editor/0.39.0/min/'
                        };
                        importScripts('https://s4.zstatic.net/ajax/libs/monaco-editor/0.39.0/min/vs/base/worker/workerMain.js');
                    `)}`;
                }
            };

            if (window.monaco) {
                createEditorInstance();
                return;
            }

            isEditorLoading.value = true;

            const loadAndCreate = () => {
                window.require.config({ paths: { vs: 'https://s4.zstatic.net/ajax/libs/monaco-editor/0.39.0/min/vs' } });
                window.require(['vs/editor/editor.main'], () => {
                    createEditorInstance();
                });
            };

            if (window.require) {
                // loader.js 已经在 index.html 加载，直接 require
                loadAndCreate();
            } else {
                // 如果没有加载过（fallback 机制）
                const loaderScript = document.createElement('script');
                loaderScript.src = 'https://s4.zstatic.net/ajax/libs/monaco-editor/0.39.0/min/vs/loader.min.js';
                loaderScript.crossOrigin = 'anonymous';
                loaderScript.onload = loadAndCreate;
                loaderScript.onerror = () => {
                    emit('show-toast', 'Monaco 编辑器加载失败，请检查网络！', 'error');
                };
                document.body.appendChild(loaderScript);
            }
        };

        const createEditorInstance = () => {
            if (!document.getElementById('monaco-editor-container')) return;
            isEditorLoading.value = false;

            let savedCode = '';
            if (codingMode.value === 'practice') {
                savedCode = userCodes.value[selectedProblemId.value] || currentProblem.value.initCode;
            } else if (codingMode.value === 'homework') {
                savedCode = homeworkCode.value || (currentHomeworkQuestion.value ? currentHomeworkQuestion.value.starterCode : '');
            } else if (codingMode.value === 'collab') {
                savedCode = selectedCollabTask.value ? selectedCollabTask.value.code : '';
            }

            monacoEditor = window.monaco.editor.create(document.getElementById('monaco-editor-container'), {
                value: savedCode,
                language: 'javascript',
                theme: 'vs-dark',
                fontSize: 14,
                fontFamily: 'Consolas, Courier New, monospace',
                minimap: { enabled: false },
                automaticLayout: true,
                roundedSelection: true,
                scrollBeyondLastLine: false,
                cursorBlinking: 'smooth',
                cursorSmoothCaretAnimation: 'on'
            });

            // 监听代码变化进行本地保存与舱室分发
            monacoEditor.onDidChangeModelContent(() => {
                const currentVal = monacoEditor.getValue();
                if (codingMode.value === 'practice') {
                    userCodes.value[selectedProblemId.value] = currentVal;
                    localStorage.setItem(`coding_code_${selectedProblemId.value}`, currentVal);
                } else if (codingMode.value === 'homework') {
                    homeworkCode.value = currentVal;
                    if (selectedHomework.value && currentHomeworkQuestion.value) {
                        localStorage.setItem(`homework_code_${selectedHomework.value.id}_${currentHomeworkQuestion.value.id}`, currentVal);
                    }
                } else if (codingMode.value === 'collab') {
                    const task = kanbanTasks.value.find(t => t.id === selectedCollabTaskId.value);
                    if (task) {
                        task.code = currentVal;
                    }
                }
            });
        };

        // 切换题目
        const handleProblemChange = () => {
            initTestCaseResults();
            aiReviewText.value = '';

            // 从本地恢复代码
            const savedCode = localStorage.getItem(`coding_code_${selectedProblemId.value}`);
            if (savedCode) {
                userCodes.value[selectedProblemId.value] = savedCode;
            } else {
                userCodes.value[selectedProblemId.value] = currentProblem.value.initCode;
            }

            if (monacoEditor) {
                monacoEditor.setValue(userCodes.value[selectedProblemId.value]);
            }
        };

        // 重置代码
        const resetCode = () => {
            if (confirm('确定要将当前代码重置为初始模板吗？已写的代码将丢失！')) {
                const initCode = currentProblem.value.initCode;
                userCodes.value[selectedProblemId.value] = initCode;
                localStorage.setItem(`coding_code_${selectedProblemId.value}`, initCode);
                if (monacoEditor) {
                    monacoEditor.setValue(initCode);
                }
                emit('show-toast', '已恢复初始模板', 'success');
            }
        };

        // 运行测试用例（Web Worker 安全沙箱）
        const runTests = () => {
            if (isRunning.value) return;
            if (isEditorLoading.value || !monacoEditor) return;

            isRunning.value = true;
            consoleLogs.value = [];
            activeTab.value = 'cases';

            // 标记所有用例为运行中
            testCaseResults.value.forEach(tc => {
                tc.status = 'running';
                tc.actual = null;
                tc.error = null;
            });

            const userCode = monacoEditor.getValue();
            const funcName = currentProblem.value.funcName;
            const dsType = currentProblem.value.ds || '';

            // 构造 Web Worker 执行代码，内置链表和二叉树转换辅助逻辑
            const workerBlobCode = `
                // === 链表辅助方法 ===
                function arrayToLinklist(arr) {
                    if (!arr || arr.length === 0) return null;
                    let head = { val: arr[0], next: null };
                    let curr = head;
                    for (let i = 1; i < arr.length; i++) {
                        curr.next = { val: arr[i], next: null };
                        curr = curr.next;
                    }
                    return head;
                }
                
                function linklistToArray(head) {
                    let arr = [];
                    let curr = head;
                    while (curr) {
                        arr.push(curr.val);
                        curr = curr.next;
                    }
                    return arr;
                }

                function arrayToCycleList(arr, pos) {
                    if (!arr || arr.length === 0) return null;
                    let nodes = arr.map(v => ({ val: v, next: null }));
                    for (let i = 0; i < nodes.length - 1; i++) {
                        nodes[i].next = nodes[i + 1];
                    }
                    if (pos >= 0 && pos < nodes.length) {
                        nodes[nodes.length - 1].next = nodes[pos];
                    }
                    return nodes[0];
                }

                // === 二叉树辅助方法 ===
                function arrayToTree(arr) {
                    if (!arr || arr.length === 0) return null;
                    let root = { val: arr[0], left: null, right: null };
                    let queue = [root];
                    let i = 1;
                    while (queue.length > 0 && i < arr.length) {
                        let curr = queue.shift();
                        if (arr[i] !== null && arr[i] !== undefined) {
                            curr.left = { val: arr[i], left: null, right: null };
                            queue.push(curr.left);
                        }
                        i++;
                        if (i < arr.length && arr[i] !== null && arr[i] !== undefined) {
                            curr.right = { val: arr[i], left: null, right: null };
                            queue.push(curr.right);
                        }
                        i++;
                    }
                    return root;
                }

                function treeToArray(root) {
                    if (!root) return [];
                    let arr = [];
                    let queue = [root];
                    while (queue.length > 0) {
                        let curr = queue.shift();
                        if (curr) {
                            arr.push(curr.val);
                            queue.push(curr.left);
                            queue.push(curr.right);
                        } else {
                            arr.push(null);
                        }
                    }
                    while (arr.length > 0 && arr[arr.length - 1] === null) {
                        arr.pop();
                    }
                    return arr;
                }

                self.onmessage = function(e) {
                    const { userCode, funcName, testCases, dsType } = e.data;
                    try {
                        const logs = [];
                        const originalLog = console.log;
                        console.log = function(...args) {
                            logs.push(args.map(x => {
                                if (x === null) return 'null';
                                if (x === undefined) return 'undefined';
                                return typeof x === 'object' ? JSON.stringify(x) : String(x);
                            }).join(' '));
                        };

                        const userFunc = new Function(userCode + "; return " + funcName + ";")();
                        if (typeof userFunc !== 'function') {
                            throw new Error("找不到入口函数 " + funcName + "，请确保不要修改模板中的函数名称。");
                        }

                        const results = testCases.map((tc, idx) => {
                            let passed = false;
                            let actual = null;
                            let error = null;
                            let caseLogs = [];
                            
                            const caseLogHandler = function(...args) {
                                caseLogs.push(args.map(x => typeof x === 'object' ? JSON.stringify(x) : String(x)).join(' '));
                            };
                            console.log = caseLogHandler;

                            try {
                                const inputClone = JSON.parse(JSON.stringify(tc.input));
                                
                                // 根据数据结构类型进行输入隐式打包
                                let args = [];
                                if (dsType === 'linkedlist') {
                                    args = [arrayToLinklist(inputClone[0])];
                                } else if (dsType === 'linkedlist_two') {
                                    args = [arrayToLinklist(inputClone[0]), arrayToLinklist(inputClone[1])];
                                } else if (dsType === 'linkedlist_cycle') {
                                    args = [arrayToCycleList(inputClone[0], inputClone[1])];
                                } else if (dsType === 'linkedlist_num') {
                                    args = [arrayToLinklist(inputClone[0]), inputClone[1]];
                                } else if (dsType === 'linkedlist_array') {
                                    args = [inputClone[0].map(arr => arrayToLinklist(arr))];
                                } else if (dsType === 'binarytree' || dsType === 'binarytree_node') {
                                    args = [arrayToTree(inputClone[0])];
                                } else {
                                    args = inputClone;
                                }

                                // 执行用户函数
                                let res = userFunc.apply(null, args);

                                // 根据数据结构进行输出反序列化，便于与 expected 比较
                                if (dsType === 'linkedlist' || dsType === 'linkedlist_two' || dsType === 'linkedlist_num' || dsType === 'linkedlist_array') {
                                    actual = linklistToArray(res);
                                } else if (dsType === 'binarytree_node') {
                                    actual = treeToArray(res);
                                } else {
                                    actual = res;
                                }
                            } catch(err) {
                                error = err.message;
                            }
                            
                            return {
                                index: idx,
                                actual: actual,
                                error: error,
                                caseLogs: caseLogs
                            };
                        });

                        console.log = originalLog;
                        self.postMessage({ status: 'success', results: results, logs: logs });
                    } catch(err) {
                        self.postMessage({ status: 'error', error: err.message });
                    }
                };
            `;

            const blob = new Blob([workerBlobCode], { type: 'application/javascript' });
            worker = new Worker(URL.createObjectURL(blob));

            // 发送任务，通过 JSON 序列化脱壳 Proxy 响应式对象
            worker.postMessage({
                userCode: userCode,
                funcName: funcName,
                testCases: JSON.parse(JSON.stringify(currentProblem.value.testCases)),
                dsType: dsType
            });

            // 1.5 秒超时控制，防死循环卡住主线程
            const timeoutId = setTimeout(() => {
                if (worker) {
                    worker.terminate();
                    worker = null;
                    testCaseResults.value.forEach(tc => {
                        tc.status = 'error';
                        tc.error = '执行超时 (限制 1.5秒)，可能存在死循环，请检查代码结构！';
                    });
                    localStorage.setItem(`coding_status_${currentProblem.value.id}`, 'failed');
                    updateStatuses();
                    isRunning.value = false;
                    emit('show-toast', '代码执行超时，已强制中断', 'error');
                }
            }, 1500);

            worker.onmessage = function (e) {
                clearTimeout(timeoutId);
                isRunning.value = false;
                if (!worker) return;
                worker.terminate();
                worker = null;

                const data = e.data;
                if (data.status === 'success') {
                    data.results.forEach(res => {
                        const tc = testCaseResults.value[res.index];
                        const origTestCase = currentProblem.value.testCases[res.index];
                        tc.actual = res.actual;
                        tc.error = res.error;

                        if (res.error) {
                            tc.status = 'error';
                        } else if (deepEqual(res.actual, origTestCase.expected)) {
                            tc.status = 'passed';
                        } else {
                            tc.status = 'failed';
                        }

                        if (res.caseLogs && res.caseLogs.length > 0) {
                            consoleLogs.value.push(...res.caseLogs.map(log => `[用例 ${res.index + 1}] ${log}`));
                        }
                    });

                    // 检查是否全部通过，并存盘状态以打破缓存
                    const allPassed = testCaseResults.value.every(tc => tc.status === 'passed');
                    if (allPassed) {
                        localStorage.setItem(`coding_status_${currentProblem.value.id}`, 'passed');
                        emit('show-toast', '恭喜！所有测试用例均通过！', 'success');
                    } else {
                        localStorage.setItem(`coding_status_${currentProblem.value.id}`, 'failed');
                        emit('show-toast', '部分测试用例未通过，请检查代码逻辑', 'error');
                    }
                    updateStatuses();

                    // 异步上报评测结果至后端数据库以实时驱动学情画像更新
                    const firstFailedCase = testCaseResults.value.find(tc => tc.status !== 'passed');
                    const errorMsg = firstFailedCase ? (firstFailedCase.error || '测试输出与预期不匹配') : null;
                    const username = props.currentUser?.username || 'guest_user';

                    profileApi.recordTest({
                        user_id: username,
                        problem_id: currentProblem.value.id,
                        category: currentProblem.value.category,
                        status: allPassed ? 'passed' : 'failed',
                        difficulty: currentProblem.value.difficulty,
                        error_msg: errorMsg
                    }).then(() => {
                        if (window.dispatchEvent) {
                            window.dispatchEvent(new CustomEvent('agent-log', {
                                detail: {
                                    agent: 'CodeNinja',
                                    content: allPassed
                                        ? `完成了题目「${currentProblem.value.title}」的测试，所有用例全部通过！正在为您增加代码能力与步调分值。`
                                        : `在题目「${currentProblem.value.title}」的测试中发现用例不通过（错误: ${errorMsg}）。已记录薄弱点。`,
                                    time: new Date().toLocaleTimeString()
                                }
                            }));
                        }
                    }).catch(err => console.error("上报测试结果失败:", err));
                } else {
                    // 全局语法/结构错误
                    testCaseResults.value.forEach(tc => {
                        tc.status = 'error';
                        tc.error = data.error;
                    });
                    consoleLogs.value.push(`[编译错误] ${data.error}`);
                    emit('show-toast', '编译或执行发生异常', 'error');

                    // 上报编译异常
                    const username = props.currentUser?.username || 'guest_user';
                    profileApi.recordTest({
                        user_id: username,
                        problem_id: currentProblem.value.id,
                        category: currentProblem.value.category,
                        status: 'failed',
                        difficulty: currentProblem.value.difficulty,
                        error_msg: `编译错误: ${data.error}`
                    }).then(() => {
                        if (window.dispatchEvent) {
                            window.dispatchEvent(new CustomEvent('agent-log', {
                                detail: {
                                    agent: 'CodeNinja',
                                    content: `在运行题目「${currentProblem.value.title}」时遇到编译或语法异常: ${data.error}。已通知首席规划师 Alina。`,
                                    time: new Date().toLocaleTimeString()
                                }
                            }));
                        }
                    }).catch(err => console.error("上报编译错误失败:", err));
                }
            };
        };

        // 获取 AI 智能代码Review诊断 (与 CodeNinja 对话)
        const getAiReview = async () => {
            if (isAiAnalyzing.value) return;
            if (isEditorLoading.value || !monacoEditor) return;

            isAiAnalyzing.value = true;
            aiReviewText.value = '';

            const userCode = monacoEditor.getValue();
            const casesBrief = testCaseResults.value.map((tc, i) => {
                return `用例 ${i + 1} (${tc.label}): ${tc.status === 'passed' ? '通过' : '失败'}${tc.error ? '，报错: ' + tc.error : ''}`;
            }).join('\n');

            const prompt = `你现在是【格至智能协同教育系统】中的 AI 编程导师 CodeNinja（代码精灵）。
请针对以下编程题目以及用户的实现代码，提供一份专业、富有建设性的 Code Review 诊断报告。

【题目名称】: ${currentProblem.value.title}
【题目描述】: ${currentProblem.value.desc}
【用户当前代码】:
\`\`\`javascript
${userCode}
\`\`\`
【单元测试结果】: 
${casesBrief || '（暂未运行本地测试用例）'}

请在回复中包含以下模块：
1. 💡 诊断综述：代码是否正确，有什么明显的逻辑漏洞或边界情况未处理？
2. 📊 复杂度分析：分析当前代码的时间复杂度和空间复杂度。
3. 🛠️ 优化与重构建议：如果不完美，提供重构后的代码，并详细解释为什么这样优化更好。如果已经完美，给予高度鼓励并探讨其他解法（例如递归 vs 迭代，或者不同数据结构优化）。

请使用简体中文回答，语气要专业、亲切、充满启发性，并符合 Markdown 格式规范。`;

            try {
                // 向后台 RAG/Agent API 发送请求
                const resJson = await request('/chat', {
                    method: 'POST',
                    body: JSON.stringify({
                        message: prompt,
                        sessionId: props.currentUser?.username || 'guest_user',
                        agent_id: props.agentConfig?.id || 'agent_coder',
                        agent_model: props.agentConfig?.model || 'kimi-k2.7-code',
                        agent_prompt: props.agentConfig?.prompt || '你专注于编写高质量的代码示例。提供带有详尽注释的代码片段。',
                        force_rag: false,
                        is_diagnosis: true,
                        problem_id: currentProblem.value.id,
                        problem_title: currentProblem.value.title,
                        user_code: userCode
                    })
                });

                const reply = resJson.reply || 'CodeNinja 思考了片刻，未能吐出诊断结果。';

                // 模拟流式打字机渲染
                if (typingTimer) clearInterval(typingTimer);
                let i = 0;
                typingTimer = setInterval(() => {
                    const chunkSize = Math.floor(Math.random() * 6) + 3;
                    if (i < reply.length) {
                        aiReviewText.value += reply.substring(i, i + chunkSize);
                        i += chunkSize;
                    } else {
                        clearInterval(typingTimer);
                        typingTimer = null;
                        isAiAnalyzing.value = false;
                    }
                }, 20);

            } catch (err) {
                // 本地脱机演示 Fallback（精美的离线模版，提供逼真的交互）
                const prob = currentProblem.value;
                const results = testCaseResults.value;

                const allPassed = results.every(tc => tc.status === 'passed');
                const failedCases = results.filter(tc => tc.status === 'failed' || tc.status === 'error');

                let overview = '';
                if (allPassed) {
                    overview = `恭喜！您的代码已成功通过了所有本地测试用例。结构完整，逻辑清晰，非常好地实现了**${prob.title}**的要求。`;
                } else {
                    overview = `分析了您的代码与测试结果，发现有 ${failedCases.length} 个测试用例未通过。可能是因为一些关键的条件判断不完备，或者发生了运行时/逻辑错误。`;
                    if (prob.id === 'two_sum' && !userCode.includes('Map') && !userCode.includes('new Map')) {
                        overview += ` 特别注意到，您的代码似乎使用的是双重循环暴力解法，这会导致时间复杂度较高。建议引入哈希表（Map）进行优化。`;
                    }
                    if (prob.id === 'reverse_list' && !userCode.includes('next') && !userCode.includes('curr')) {
                        overview += ` 在链表反转中，需要注意临时保存指针节点，避免链表断开导致死循环。`;
                    }
                    if (prob.id === 'valid_parentheses' && !userCode.includes('stack') && !userCode.includes('push')) {
                        overview += ` 括号匹配问题是典型的后进先出应用，强烈建议使用栈结构（Array push/pop）来实现。`;
                    }
                }

                const review = problemReviews[prob.id] || {
                    complexity: `- **时间复杂度**：$O(N)$。\n- **空间复杂度**：$O(1)$。`,
                    code: prob.initCode
                };

                const fallbackMessage = `[✨ CodeNinja 智能代码精灵 (本地离线诊断)]

检测到您的后端 AI 服务未连接，为了不中断您的实战体验，我已基于本地诊断逻辑为您输出如下报告：

### 💡 诊断综述
1. 对于**${prob.title}**的算法设计，${overview}
2. 建议核对变量是否声明、算法是否存在越界等常见细节。

### 📊 复杂度分析
${review.complexity}

### 🛠️ 优化建议（以 ${prob.title} 为例）
您可以参考如下经典实现并对您的代码进行校正或借鉴：
\`\`\`javascript
${review.code}
\`\`\`

如有疑问，可以登录教师管理端在“学情决策台”中查看由 Alina 和 CodeNinja 专门为您推送的针对性学习日志！`;

                if (typingTimer) clearInterval(typingTimer);
                let i = 0;
                typingTimer = setInterval(() => {
                    const chunkSize = Math.floor(Math.random() * 6) + 3;
                    if (i < fallbackMessage.length) {
                        aiReviewText.value += fallbackMessage.substring(i, i + chunkSize);
                        i += chunkSize;
                    } else {
                        clearInterval(typingTimer);
                        typingTimer = null;
                        isAiAnalyzing.value = false;
                    }
                }, 20);
            }
        };

        // 动态处理渲染出的代码块，追加复制和导入IDE按钮
        const processCodeBlocks = () => {
            nextTick(() => {
                const container = document.querySelector('.ai-review-content');
                if (!container) return;
                const pres = container.querySelectorAll('pre');
                pres.forEach(pre => {
                    if (pre.querySelector('.code-action-bar')) return;

                    pre.classList.add('relative', 'group', 'overflow-visible');

                    const actionBar = document.createElement('div');
                    actionBar.className = 'code-action-bar absolute right-2.5 top-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-all duration-300 z-30 select-none';

                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'px-2 py-1 bg-slate-950/80 text-white rounded text-[10px] font-bold flex items-center gap-1 hover:bg-slate-800 border border-slate-700 transition-all active:scale-95';
                    copyBtn.innerHTML = '<i class="ph ph-copy"></i> 复制';
                    copyBtn.onclick = (e) => {
                        e.stopPropagation();
                        const code = pre.querySelector('code')?.innerText || pre.innerText;
                        navigator.clipboard.writeText(code).then(() => {
                            emit('show-toast', '代码已复制到剪贴板', 'success');
                        }).catch(() => {
                            emit('show-toast', '复制失败，请手动选择复制', 'error');
                        });
                    };

                    const applyBtn = document.createElement('button');
                    applyBtn.className = 'px-2 py-1 bg-indigo-600/90 text-white rounded text-[10px] font-bold flex items-center gap-1 hover:bg-indigo-500 border border-indigo-500/30 transition-all active:scale-95';
                    applyBtn.innerHTML = '<i class="ph ph-code-block"></i> 导入编辑器';
                    applyBtn.onclick = (e) => {
                        e.stopPropagation();
                        const code = pre.querySelector('code')?.innerText || pre.innerText;
                        if (monacoEditor) {
                            monacoEditor.setValue(code);
                            emit('show-toast', '已将诊断代码导入编辑器', 'success');
                        }
                    };

                    actionBar.appendChild(copyBtn);
                    actionBar.appendChild(applyBtn);
                    pre.appendChild(actionBar);
                });
            });
        };

        // 监听 AI 复查内容更新以实时刷新按钮
        watch(aiReviewText, () => {
            processCodeBlocks();
        });

        // 渲染 Markdown 的计算属性 (用于AI诊断解析)
        const renderedAiReview = computed(() => {
            if (window.marked && typeof window.marked.parse === 'function') {
                return window.marked.parse(aiReviewText.value);
            }
            return aiReviewText.value;
        });

        const handleImportCodeEvent = (e) => {
            if (monacoEditor) {
                monacoEditor.setValue(e.detail);
                emit('show-toast', '已为您一键导入来自多智能体导师的代码案例！', 'success');
            } else {
                userCodes.value[selectedProblemId.value] = e.detail;
            }
        };

        // 页面生命周期
        onMounted(() => {
            // 注入局部样式以定制 pre 块定位与微动画
            const style = document.createElement('style');
            style.innerHTML = `
                .ai-review-content {
                    color: #0f172a !important;
                    font-size: 0.875rem !important;
                    line-height: 1.7 !important;
                }
                .ai-review-content p {
                    margin-bottom: 0.85rem !important;
                }
                .ai-review-content strong {
                    color: #1e1b4b !important;
                    font-weight: 700 !important;
                }
                .ai-review-content code {
                    background-color: #e2e8f0 !important;
                    color: #0f172a !important;
                    font-weight: 600 !important;
                    padding: 0.2rem 0.4rem !important;
                    border-radius: 0.25rem !important;
                }
                .ai-review-content pre {
                    position: relative !important;
                    padding-top: 2.3rem !important;
                    background-color: #f8fafc !important;
                    border: 1px solid #cbd5e1 !important;
                    transition: border-color 0.3s ease, box-shadow 0.3s ease;
                }
                .ai-review-content pre:hover {
                    border-color: #818cf8 !important;
                    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
                }
            `;
            document.head.appendChild(style);

            // 初始化恢复部分代码缓存
            codingProblems.forEach(p => {
                const saved = localStorage.getItem(`coding_code_${p.id}`);
                if (saved) userCodes.value[p.id] = saved;
            });
            initTestCaseResults();
            updateStatuses();
            loadHomeworkData();

            window.addEventListener('import-code', handleImportCodeEvent);
        });

        onBeforeUnmount(() => {
            if (monacoEditor) {
                monacoEditor.dispose();
            }
            if (worker) {
                worker.terminate();
            }
            if (typingTimer) {
                clearInterval(typingTimer);
                typingTimer = null;
            }
            // BUG 2 修复：清理排位赛定时器、编辑器和安全监听器，防止内存泄漏
            unbindRankedSecurityGuards();
            if (rankedTimer) { clearInterval(rankedTimer); rankedTimer = null; }
            if (opponentTimer) { clearInterval(opponentTimer); opponentTimer = null; }
            destroyRankedEditor();
            window.removeEventListener('import-code', handleImportCodeEvent);
        });

        return {
            problems,
            selectedProblemId,
            currentProblem,
            parsedDesc,
            isEditorLoading,
            isRunning,
            testCaseResults,
            consoleLogs,
            isAiAnalyzing,
            aiReviewText,
            renderedAiReview,
            activeTab,
            handleProblemChange,
            resetCode,
            runTests,
            getAiReview,
            groupedProblems,
            getProblemSelectLabel,
            updateStatuses,
            problemStatuses,
            panelStyle,
            dragStart,
            activePanelTab,
            historyList,
            tempHistoryCode,
            toggleHistoryView,
            viewHistoryDetail,
            restoreHistoryCode,
            isPanelOpen,
            openAiPanel,
            closePanel,
            startReviewFromMenu,
            showHistoryFromMenu,

            // 新增状态与方法
            codingMode,
            switchMode,
            goBackToLobby,

            // 竞技排位赛状态与方法
            rankedTab,
            rankedMatchStatus,
            rankedCoachOpen,
            rankedCoachInput,
            isRankedCoachLoading,
            rankedCoachChatScroll,
            rankedTabs,
            rankedPlayer,
            leaderboard,
            rankedRules,
            dailyChallenge,
            tierLadder,
            matchHistory,
            historyStats,
            seasonList,
            rankedMistakes,
            mistakeStats,
            coachSuggestions,
            startRankedMatch,
            switchRankedTab,
            reviewRankedMistake,
            deleteRankedMistake,
            askRankedCoach,
            scrollToBottom,
            getRankedCoachConfig,

            // 排位竞技舱新增变量与函数
            rankedRoomMode,
            isRankedEntryConfirmOpen,
            isRankedExitConfirmOpen,
            isRankedSettlementOpen,
            rankedSecurityActive,
            rankedBlurViolationCount,
            rankedRemainingSeconds,
            rankedOpponentStatus,
            rankedOpponentProgress,
            rankedMatchResult,
            currentRankedMatchId,
            rankedAnswers,
            rankedTestCaseResults,
            rankedConsoleLogs,
            isRankedEditorLoading,
            useRankedPlainEditor,
            isRankedRunning,
            rankedActiveTab,
            confirmRankedEntry,
            cancelRankedEntry,
            enterRankedArena,
            exitRankedArena,
            runRankedCode,
            submitRankedMatch,
            resolveRankedMatch,
            closeRankedSettlement,
            setRankedEditorCode,
            rankedProblem,
            watermarkTime,
            formatDuration,

            // 作业状态与方法
            homeworkList,
            selectedHomeworkId,
            selectedHomework,
            currentHomeworkQuestion,
            activeHomeworkConsoleLogs,
            homeworkCode,
            runHomeworkTesting,
            submitHomeworkLoading,
            homeworkDiagnosis,
            homeworkRadarOption,
            runHomeworkTest,
            handleHomeworkDiagnose,
            submitHomeworkAssignment,

            // 团队协作状态与方法
            teamInfo,
            teamMembers,
            kanbanTasks,
            collabLogs,
            chatInput,
            chatMessages,
            isPairBotThinking,
            selectedCollabTaskId,
            selectedCollabTask,
            handleCollabTaskClick,
            runCollabTesting,
            runCollabTest,
            sendCollabMessage,
            collabRadarOption,
            collabProjectId,
            collabData,
            collabLoading,
            collabError,
            collabActionLoading,
            collabViewMode,
            collabProjects,
            repositoryHome,
            repositoryHomeTab,
            repositoryHomeTabs,
            collabMemberKeyword,
            collabMemberSearchResults,
            collabSelectedMembers,
            collabCreateOpen,
            collabCreateForm,
            assigningMemberName,
            assignTaskForm,
            reminderMessage,
            prReviewComment,
            collabViewerName,
            canManageCollab,
            canManageRepositoryHome,
            canManageCollabProject,
            contributionRanking,
            collabProject,
            repositoryInfo,
            repositoryPrSource,
            isGiteaLive,
            isWebhookConnected,
            isDemoFallback,
            isGiteaEmptyPr,
            syncErrorMessage,
            workflowSteps,
            memberProgress,
            pullRequests,
            aiGitCoachFeedback,
            gitEvents,
            recentCommits,
            teamSummary,
            currentUserProgress,
            repositoryHomeInfo,
            repositoryHomeProject,
            repositoryHomeRepo,
            repositoryHomeFiles,
            repositoryHomeLanguages,
            repositoryHomePullRequests,
            repositoryHomeOpenPrCount,
            repositoryHomeMergedPrCount,
            teamRepoBrowserPath,
            teamRepoBrowserEntries,
            teamRepoBrowserLoading,
            teamRepoBrowserBlob,
            teamRepoBrowserLanguages,
            teamRepoBrowserError,
            teamRepoBranches,
            teamRepoSelectedBranch,
            teamBranchDropdownOpen,
            toggleBranchDropdown,
            closeBranchDropdown,
            teamRepoBreadcrumbs,
            loadTeamRepoBrowser,
            loadTeamBranches,
            switchTeamBranch,
            openTeamRepoEntry,
            formatTeamRepoFileSize,
            prCreationUrl,
            loadCollabProjects,
            loadCollabProject,
            loadRepositoryHome,
            selectRepositoryHomeTab,
            refreshRepositoryHomePullRequests,
            openCollabManagement,
            openCollabRepositoryHome,
            openRepositoryHomePullRequests,
            backToCollabRepositoryList,
            copyGitCommand,
            openExternalLink,
            createCollabProject,
            createGiteaRepository,
            bindExistingRepository,
            searchCollabMembers,
            addCollabMember,
            removeCollabMember,
            deleteCollabProject,
            startAssignTask,
            submitAssignTask,
            remindCollabMembers,
            reviewCollabPr,
            confirmCloneDone,
            refreshCollabStatus,
            teamGiteaIdentity,
            teamGeneratedToken,
            teamTokenWarning,
            teamIdentityLoading,
            copiedTeamToken,
            copiedTeamGitConfigAll,
            copiedTeamGitConfigLine,
            copiedTeamAuthClone,
            teamCloneMode,
            loadTeamGiteaIdentity,
            handleTeamRotateGiteaToken,
            copyTeamGeneratedToken,
            copyTeamGitConfig,
            copyTeamGitConfigLine,
            copyTeamAuthClone,
            teamAuthenticatedCloneUrl,
            repoStatusClass,
            stepStatusClass,
            memberStatusClass,
            prStatusClass,
            eventIcon,
            formatDisplayDateTime
        };
    },
    template: `
        <div class="w-full h-full p-4 lg:p-6 flex flex-col overflow-hidden select-none relative bg-slate-50">
            <!-- ==================== 1. 分流大厅 (Lobby) ==================== -->
            <div v-if="codingMode === null" class="m-auto max-w-[90rem] w-full p-8 flex flex-col items-center justify-center animate-fade-in select-none">
                <h2 class="text-3xl font-extrabold text-slate-800 mb-2" style="font-family: 'Noto Serif SC', serif;">编程实战协同演练舱</h2>
                <p class="text-sm text-slate-400 mb-12 tracking-widest" style="font-family: 'Barlow Condensed', sans-serif;">PRACTICE & COLLABORATE & ACHIEVE</p>
                
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 w-full px-4">
                    <!-- 个人练习区卡片 -->
                    <div @click="switchMode('practice')" 
                         class="glass-panel-liquid p-8 cursor-pointer flex flex-col items-center text-center transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 border border-white/85 hover:shadow-xl group relative overflow-hidden">
                         <div class="w-16 h-16 bg-gradient-to-br from-cyan-50 to-blue-50 text-blue-600 rounded-2xl flex items-center justify-center text-3xl mb-6 shadow-sm group-hover:scale-105 transition-transform duration-500 border border-blue-100">
                             <i class="ph ph-code"></i>
                         </div>
                         <h3 class="text-lg font-bold text-slate-800 mb-2" style="font-family: 'Noto Serif SC', serif;">个人练习区</h3>
                         <p class="text-xs text-slate-400 leading-relaxed max-w-[240px] mb-6">
                             精选算法题库，智能判题沙箱。内置安全沙箱评测，支持 CodeNinja AI 实时深度代码 CR 诊断报告。
                         </p>
                         <span class="mt-auto px-4 py-1.5 bg-blue-50 text-blue-600 border border-blue-100 rounded-full text-xs font-semibold group-hover:bg-blue-600 group-hover:text-white transition-colors duration-500">开启算法训练</span>
                         <div class="absolute bottom-0 left-0 right-0 h-[3px] bg-gradient-to-r from-cyan-400 to-blue-500"></div>
                     </div>
                     
                     <!-- 编程作业区卡片 -->
                     <div @click="switchMode('homework')" 
                          class="glass-panel-liquid p-8 cursor-pointer flex flex-col items-center text-center transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 border border-white/85 hover:shadow-xl group relative overflow-hidden">
                          <div class="w-16 h-16 bg-gradient-to-br from-pink-50 to-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-3xl mb-6 shadow-sm group-hover:scale-105 transition-transform duration-500 border border-indigo-100">
                              <i class="ph ph-article"></i>
                          </div>
                          <h3 class="text-lg font-bold text-slate-800 mb-2" style="font-family: 'Noto Serif SC', serif;">编程作业区</h3>
                          <p class="text-xs text-slate-400 leading-relaxed max-w-[240px] mb-6">
                              日常课后作业与阶段实训。真代码运行评测，支持一键联合智能诊断，作业成果自动同步画像。
                          </p>
                          <span class="mt-auto px-4 py-1.5 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded-full text-xs font-semibold group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-500">开展作业冲刺</span>
                          <div class="absolute bottom-0 left-0 right-0 h-[3px] bg-gradient-to-r from-pink-400 to-indigo-500"></div>
                      </div>

                      <!-- 团队协作实训卡片 -->
                      <div @click="switchMode('collab')" 
                           class="glass-panel-liquid p-8 cursor-pointer flex flex-col items-center text-center transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 border border-white/85 hover:shadow-xl group relative overflow-hidden">
                           <div class="w-16 h-16 bg-gradient-to-br from-emerald-50 to-teal-50 text-emerald-600 rounded-2xl flex items-center justify-center text-3xl mb-6 shadow-sm group-hover:scale-105 transition-transform duration-500 border border-emerald-100">
                               <i class="ph ph-users-three"></i>
                           </div>
                           <h3 class="text-lg font-bold text-slate-800 mb-2" style="font-family: 'Noto Serif SC', serif;">团队协作实训</h3>
                           <p class="text-xs text-slate-400 leading-relaxed max-w-[240px] mb-6">
                               多人协同实操开发。敏捷看板任务认领，队友动态日志流实时同步，专属 AI 结令人编程顾问支持。
                           </p>
                           <span class="mt-auto px-4 py-1.5 bg-emerald-50 text-emerald-600 border border-emerald-100 rounded-full text-xs font-semibold group-hover:bg-emerald-600 group-hover:text-white transition-colors duration-500">进入协作实训</span>
                           <div class="absolute bottom-0 left-0 right-0 h-[3px] bg-gradient-to-r from-emerald-400 to-teal-500"></div>
                       </div>
                       
                       <!-- 竞技排位赛卡片 -->
                       <div @click="switchMode('ranked')" 
                            class="glass-panel-liquid p-8 cursor-pointer flex flex-col items-center text-center transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 border border-white/85 hover:shadow-xl group relative overflow-hidden">
                            <div class="w-16 h-16 bg-gradient-to-br from-amber-50 to-orange-50 text-orange-600 rounded-2xl flex items-center justify-center text-3xl mb-6 shadow-sm group-hover:scale-105 transition-transform duration-500 border border-orange-100">
                                <i class="ph ph-trophy"></i>
                            </div>
                            <h3 class="text-lg font-bold text-slate-800 mb-2" style="font-family: 'Noto Serif SC', serif;">竞技排位赛</h3>
                            <p class="text-xs text-slate-400 leading-relaxed max-w-[240px] mb-6">
                                算法争锋，冲刺王者。全校排位对决，赢取荣誉积分。段位晋级、每日挑战，体验编程竞技的乐趣。
                            </p>
                            <span class="mt-auto px-4 py-1.5 bg-orange-50 text-orange-600 border border-orange-100 rounded-full text-xs font-semibold group-hover:bg-orange-600 group-hover:text-white transition-colors duration-500">参加排位赛</span>
                            <div class="absolute bottom-0 left-0 right-0 h-[3px] bg-gradient-to-r from-amber-400 to-orange-500"></div>
                        </div>
                </div>
            </div>

            <!-- ==================== 2. 舱室 1: 个人练习区 (Coding Arena) ==================== -->
            <div v-else-if="codingMode === 'practice'" class="w-full h-full flex flex-col overflow-hidden relative">
                <!-- 顶部导航 -->
                <div class="flex items-center justify-between mb-3 w-full border-b border-slate-200 pb-2 shrink-0 select-none">
                    <button @click="goBackToLobby" class="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1.5 font-semibold transition-all">
                        <i class="ph ph-arrow-left"></i> 返回实战大厅
                    </button>
                    <div class="text-right">
                        <span class="text-[10px] text-slate-400 uppercase tracking-widest font-mono">PRACTICE ARENA</span>
                        <h3 class="text-xs font-bold text-slate-700">算法判题沙箱</h3>
                    </div>
                </div>

                <!-- 主练习空间 -->
                <div class="flex-1 min-h-0 flex gap-5 overflow-hidden">
                    <!-- 左侧栏：题目说明与测试控制台 -->
                    <div class="w-[42%] flex flex-col gap-4 h-full">
                        <!-- 题目信息卡片 -->
                        <div class="glass-panel-liquid flex-1 flex flex-col p-6 overflow-hidden relative">
                            <div class="flex items-center justify-between mb-4 relative z-10">
                                <div class="flex items-center gap-2.5">
                                    <span class="w-3 h-3 rounded-full bg-primary/70 shadow-[0_0_8px_rgba(59,130,246,0.5)]"></span>
                                    <span class="text-sm font-semibold text-slate-800 tracking-wider">题目详情</span>
                                </div>
                                <!-- 题目选择器 -->
                                <select v-model="selectedProblemId" @change="handleProblemChange"
                                        class="bg-white/80 border border-slate-200 text-slate-700 text-xs rounded-xl py-1.5 px-3.5 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all font-medium">
                                    <optgroup v-for="group in groupedProblems" :key="group.category" :label="group.category">
                                        <option v-for="prob in group.problems" :key="prob.id" :value="prob.id">
                                            {{ getProblemSelectLabel(prob) }}
                                        </option>
                                    </optgroup>
                                </select>
                            </div>

                            <!-- 题目主要内容（滚动） -->
                            <div class="flex-1 overflow-y-auto pr-1 no-scrollbar relative z-10 flex flex-col gap-4">
                                <div>
                                    <h2 class="text-xl font-bold text-slate-900 mb-2">{{ currentProblem.title }}</h2>
                                    <div class="flex gap-2 mb-4">
                                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100">
                                            {{ currentProblem.difficulty }}
                                        </span>
                                        <span v-for="tag in currentProblem.tags" :key="tag" 
                                              class="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                            {{ tag }}
                                        </span>
                                    </div>
                                    <!-- Markdown题目描述 -->
                                    <div class="text-sm text-slate-600 leading-relaxed markdown-body" v-html="parsedDesc"></div>
                                </div>
                            </div>
                        </div>

                        <!-- 底部测试面板与控制台 -->
                        <div class="glass-panel-liquid h-[42%] flex flex-col p-5 overflow-hidden">
                            <div class="flex border-b border-slate-100 mb-3 text-xs font-semibold select-none">
                                <button @click="activeTab = 'cases'" 
                                        :class="activeTab === 'cases' ? 'text-primary border-b-2 border-primary' : 'text-slate-500'" 
                                        class="pb-2 px-2 transition-all">
                                    测试用例
                                </button>
                                <button @click="activeTab = 'console'" 
                                        :class="activeTab === 'console' ? 'text-primary border-b-2 border-primary' : 'text-slate-500'" 
                                        class="pb-2 px-4 transition-all flex items-center gap-1.5">
                                    本地控制台
                                    <span v-if="consoleLogs.length > 0" class="px-1.5 py-0.2 text-[9px] bg-red-100 text-red-500 rounded-full font-bold">
                                        {{ consoleLogs.length }}
                                    </span>
                                </button>
                            </div>

                            <!-- 选项卡内容 -->
                            <div class="flex-1 overflow-y-auto no-scrollbar">
                                <!-- 测试用例卡片 -->
                                <div v-show="activeTab === 'cases'" class="flex flex-col gap-2.5">
                                    <div v-for="(result, index) in testCaseResults" :key="index"
                                         class="p-3 bg-white/40 border border-slate-100 rounded-xl flex items-center justify-between text-xs transition-all">
                                        <div class="flex-1 min-w-0 pr-3">
                                            <div class="font-bold text-slate-800 flex items-center gap-2 mb-1">
                                                <i class="ph ph-brackets-angle text-slate-500"></i>
                                                {{ result.label }}
                                            </div>
                                            <div class="text-[10px] text-slate-500 truncate">输入: {{ JSON.stringify(result.input) }}</div>
                                            <div v-if="result.actual !== null" class="text-[10px] text-primary truncate mt-0.5">输出: {{ JSON.stringify(result.actual) }}</div>
                                            <div v-if="result.error" class="text-[10px] text-rose-500 font-mono mt-0.5 truncate">{{ result.error }}</div>
                                        </div>

                                        <!-- 用例状态徽章 -->
                                        <div class="flex-shrink-0">
                                            <span v-if="result.status === 'pending'" class="text-slate-400 bg-slate-50 border border-slate-100 px-2.5 py-1 rounded-lg font-semibold text-[10px] flex items-center gap-1">
                                                <i class="ph ph-hourglass-low"></i> 待测试
                                            </span>
                                            <span v-else-if="result.status === 'running'" class="text-primary bg-blue-50 border border-blue-100 px-2.5 py-1 rounded-lg font-semibold text-[10px] flex items-center gap-1 animate-pulse">
                                                <i class="ph ph-spinner animate-spin"></i> 运行中
                                            </span>
                                            <span v-else-if="result.status === 'passed'" class="text-emerald-600 bg-emerald-50 border border-emerald-100 px-2.5 py-1 rounded-lg font-bold text-[10px] flex items-center gap-1 shadow-sm">
                                                <i class="ph ph-check-circle-fill text-emerald-500 text-sm"></i> 通过
                                            </span>
                                            <span v-else class="text-rose-600 bg-rose-50 border border-rose-100 px-2.5 py-1 rounded-lg font-bold text-[10px] flex items-center gap-1">
                                                <i class="ph ph-x-circle-fill text-rose-500 text-sm"></i> 未通过
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <!-- 控制台日志 -->
                                <div v-show="activeTab === 'console'" class="h-full bg-slate-900 text-slate-300 p-3 rounded-xl font-mono text-[11px] overflow-y-auto leading-relaxed min-h-[100px]">
                                    <div v-if="consoleLogs.length === 0" class="text-slate-500 italic">没有任何控制台输出。在代码中使用 console.log() 来打印调试信息。</div>
                                    <div v-for="(log, idx) in consoleLogs" :key="idx" class="border-b border-slate-800/60 pb-1 mb-1">
                                        {{ log }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 右侧栏：IDE 编辑器及 AI 诊断面板 -->
                    <div class="flex-1 flex flex-col gap-4 h-full relative">
                        <!-- 编辑器主体 -->
                        <div class="glass-panel-static flex-1 flex flex-col p-5 overflow-hidden">
                            <div class="flex items-center justify-between mb-4">
                                <div class="flex items-center gap-2">
                                    <i class="ph ph-code-block text-xl text-slate-700"></i>
                                    <span class="text-base font-bold text-slate-900">{{ currentProblem.title }} 编辑器</span>
                                </div>
                                <!-- 工具栏按钮 -->
                                <div class="flex items-center gap-2">
                                    <button @click="resetCode" 
                                            class="bg-white/80 border border-slate-200 text-slate-600 text-xs px-3.5 py-1.8 rounded-xl font-medium shadow-sm hover:bg-slate-50 active:scale-95 transition-all">
                                        <i class="ph ph-arrow-counter-clockwise mr-1"></i> 重置
                                    </button>
                                    <button @click="runTests" :disabled="isRunning"
                                            class="liquid-glass-btn text-white text-xs px-4.5 py-1.8 rounded-xl font-semibold active:scale-95 transition-all flex items-center gap-1.5">
                                        <i v-if="isRunning" class="ph ph-spinner animate-spin"></i>
                                        <i v-else class="ph ph-play-fill"></i>
                                        运行测试
                                    </button>
                                    <button @click="openAiPanel"
                                            class="bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-xs px-4.5 py-1.8 rounded-xl font-semibold shadow-md active:scale-95 transition-all hover:brightness-110 flex items-center gap-1.5 border border-indigo-400/30">
                                        <i v-if="isAiAnalyzing" class="ph ph-sparkle animate-spin"></i>
                                        <i v-else class="ph ph-robot"></i>
                                        AI 诊断
                                    </button>
                                </div>
                            </div>

                            <!-- Monaco Editor 真实挂载区 -->
                            <div class="flex-1 w-full relative bg-[#1e1e1e] rounded-2xl overflow-hidden border border-slate-800 shadow-[inset_0_4px_16px_rgba(0,0,0,0.5)]">
                                <div id="monaco-editor-container" class="absolute inset-0 w-full h-full"></div>
                                <!-- 加载器提示 -->
                                <div v-if="isEditorLoading" class="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm z-30">
                                    <div class="w-10 h-10 border-4 border-indigo-400 border-t-transparent rounded-full animate-spin mb-4"></div>
                                    <span class="text-sm font-semibold text-indigo-300 animate-pulse">正在从 CDN 加载 Monaco Editor 内核...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- AI 协同诊断底板（动画弹出） -->
                <transition name="fade">
                    <div v-if="isPanelOpen" 
                         class="glass-panel-liquid absolute z-40 p-5 flex flex-col border border-indigo-200/50 shadow-float"
                         :style="[panelStyle, { background: 'rgba(255, 255, 255, 0.96)', 'backdrop-filter': 'blur(20px) saturate(190%)' }]">
                        <div @mousedown="dragStart" class="flex items-center justify-between border-b border-indigo-100 pb-3 mb-3 shrink-0 cursor-grab active:cursor-grabbing select-none">
                            <div class="flex items-center gap-2 pointer-events-none">
                                <div class="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                                    <i class="ph ph-robot text-lg animate-bounce"></i>
                                </div>
                                <div>
                                    <span class="text-sm font-bold text-slate-800">CodeNinja 智能代码诊断导师</span>
                                    <span class="text-[9px] text-slate-400 block tracking-wider">智能协同审查已开启 (可按住此处拖动)</span>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <button v-if="tempHistoryCode" @click="restoreHistoryCode" class="px-2.5 py-1 bg-indigo-50 border border-indigo-100 text-indigo-600 rounded-xl text-[10px] font-bold hover:bg-indigo-100 active:scale-95 transition-all flex items-center gap-1 shrink-0" title="恢复当时提交的代码">
                                    <i class="ph ph-arrow-u-up-left"></i> 恢复当时代码
                                </button>
                                <button @click="toggleHistoryView" class="w-7 h-7 bg-white/70 border border-slate-200 text-slate-500 rounded-full flex items-center justify-center hover:bg-slate-100 hover:text-indigo-600 transition-all shrink-0" title="查看历史诊断">
                                    <i class="ph ph-clock-counter-clockwise text-sm"></i>
                                </button>
                                <button @click="closePanel" class="w-7 h-7 bg-white/70 border border-slate-200 text-slate-500 rounded-full flex items-center justify-center hover:bg-slate-100 hover:text-rose-500 transition-colors shrink-0">
                                    <i class="ph ph-x text-sm"></i>
                                </button>
                            </div>
                        </div>

                        <!-- 诊断报告详情 -->
                        <div class="flex-1 overflow-y-auto pr-1 no-scrollbar flex flex-col min-h-0">
                            <!-- 菜单 Tab -->
                            <div v-if="activePanelTab === 'menu'" class="flex-1 flex flex-col justify-center items-center gap-6 py-6 select-none my-auto">
                                <div class="text-center mb-2">
                                    <p class="text-xs text-slate-500 font-semibold tracking-wide">您希望格至协同私教 CodeNinja 为您提供何种协助？</p>
                                </div>
                                <div class="flex gap-5 w-full max-w-md">
                                    <!-- 卡片 1：发起诊断 -->
                                    <button @click="startReviewFromMenu" 
                                            class="flex-1 p-5 rounded-2xl border border-indigo-100 hover:border-indigo-300 bg-white/60 hover:bg-indigo-50/30 transition-all hover:scale-105 active:scale-95 flex flex-col items-center justify-center gap-3 group text-center shadow-sm">
                                        <div class="w-12 h-12 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-md group-hover:scale-110 transition-transform">
                                            <i class="ph ph-sparkle text-2xl animate-pulse"></i>
                                        </div>
                                        <div>
                                            <span class="text-sm font-bold text-slate-800 block">开始 AI 代码分析</span>
                                            <span class="text-[10px] text-slate-400 block mt-1">剖析时空效率及边界正确性</span>
                                        </div>
                                    </button>
                                    
                                    <!-- 卡片 2：查看历史 -->
                                    <button @click="showHistoryFromMenu" 
                                            class="flex-1 p-5 rounded-2xl border border-slate-200 hover:border-indigo-300 bg-white/60 hover:bg-indigo-50/30 transition-all hover:scale-105 active:scale-95 flex flex-col items-center justify-center gap-3 group text-center shadow-sm">
                                        <div class="w-12 h-12 rounded-2xl bg-slate-700 text-white flex items-center justify-center shadow-md group-hover:scale-110 transition-transform">
                                            <i class="ph ph-clock-counter-clockwise text-2xl"></i>
                                        </div>
                                        <div>
                                            <span class="text-sm font-bold text-slate-800 block">查看往期历史</span>
                                            <span class="text-[10px] text-slate-400 block mt-1">回溯并一键恢复历史代码</span>
                                        </div>
                                    </button>
                                </div>
                            </div>
                            <!-- 历史诊断列表 -->
                            <div v-if="activePanelTab === 'history'" class="flex-1 flex flex-col overflow-hidden">
                                <div class="flex items-center justify-between mb-3 shrink-0">
                                    <span class="text-xs font-bold text-indigo-800 flex items-center gap-1">
                                        <i class="ph ph-history"></i> 往期诊断历史 (最近最多50条)
                                    </span>
                                    <button @click="activePanelTab = 'current'" class="text-[10px] text-indigo-600 font-semibold hover:underline">返回当前报告</button>
                                </div>
                                <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col gap-2 min-h-0">
                                    <div v-if="historyList.length === 0" class="text-xs text-slate-400 italic text-center py-10">
                                        暂无历史诊断记录。完成一次代码诊断后会自动保存至数据库！
                                    </div>
                                    <div v-for="item in historyList" :key="item.id" 
                                         @click="viewHistoryDetail(item)"
                                         class="p-3 bg-slate-50/60 border border-slate-100 rounded-xl hover:bg-indigo-50/50 hover:border-indigo-100 cursor-pointer transition-all flex items-center justify-between group">
                                        <div class="min-w-0 pr-3">
                                            <div class="text-xs font-bold text-slate-800 truncate mb-1">
                                                {{ item.problem_title }}
                                            </div>
                                            <div class="text-[9px] text-slate-400 font-mono">{{ formatDisplayDateTime(item.created_at) }}</div>
                                        </div>
                                        <i class="ph ph-caret-right text-slate-300 group-hover:text-indigo-400 transition-colors"></i>
                                    </div>
                                </div>
                            </div>

                            <!-- 当前诊断详情 -->
                            <div class="flex-1 flex flex-col min-h-0">
                                <div v-if="isAiAnalyzing && !aiReviewText" class="flex flex-col items-center justify-center h-full gap-3 text-indigo-700/80 my-auto">
                                    <div class="flex gap-1.5 items-center">
                                        <span class="w-2.5 h-2.5 bg-indigo-600 rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
                                        <span class="w-2.5 h-2.5 bg-indigo-600 rounded-full animate-bounce" style="animation-delay: 0.3s"></span>
                                        <span class="w-2.5 h-2.5 bg-indigo-600 rounded-full animate-bounce" style="animation-delay: 0.5s"></span>
                                    </div>
                                    <span class="text-xs font-semibold animate-pulse">正在全面剖析您的代码时间/空间效率及边界正确性...</span>
                                </div>
                                <div v-else class="text-sm text-slate-900 leading-relaxed markdown-body ai-review-content" v-html="renderedAiReview"></div>
                            </div>
                        </div>
                    </div>
                </transition>
            </div>

            <!-- ==================== 3. 舱室 2: 编程作业区 (Assignment Sandbox) ==================== -->
            <div v-else-if="codingMode === 'homework'" class="w-full h-full flex flex-col overflow-hidden relative">
                <!-- 顶部导航 -->
                <div class="flex items-center justify-between mb-3 w-full border-b border-slate-200 pb-2 shrink-0 select-none">
                    <button @click="goBackToLobby" class="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1.5 font-semibold transition-all">
                        <i class="ph ph-arrow-left"></i> 返回实战大厅
                    </button>
                    <div class="text-right">
                        <span class="text-[10px] text-slate-400 uppercase tracking-widest font-mono">ASSIGNMENT SANDBOX</span>
                        <h3 class="text-xs font-bold text-slate-700">课后作业与评测舱</h3>
                    </div>
                </div>

                <!-- 主空间 -->
                <div class="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[248px_minmax(0,1fr)] gap-4 overflow-hidden">
                    <!-- 左侧作业列表 -->
                    <aside class="min-h-0 flex flex-col gap-3 h-full">
                        <div class="glass-panel-liquid flex-1 min-h-0 flex flex-col p-3 overflow-y-auto no-scrollbar gap-2">
                            <div class="flex items-center justify-between mb-1">
                                <h4 class="label-minor">课后编程作业</h4>
                                <span class="text-[10px] text-slate-400 font-mono">{{ homeworkList.length }} 项</span>
                            </div>
                            <div v-for="hw in homeworkList" :key="hw.id"
                                 @click="selectedHomeworkId = hw.id"
                                 class="p-3 rounded-xl border transition-all cursor-pointer flex flex-col gap-2 bg-white/45 border-white/60 hover:bg-white/85"
                                 :class="selectedHomeworkId === hw.id ? 'bg-white border-indigo-500 shadow-md ring-2 ring-indigo-500/10' : ''">
                                <div class="flex justify-between items-center">
                                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
                                          :class="hw.status === 'graded' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' :
                                                  hw.status === 'submitted' ? 'bg-blue-50 text-blue-600 border border-blue-100' :
                                                  'bg-amber-50 text-amber-600 border border-amber-100'">
                                        {{ hw.status === 'graded' ? '已批阅' : (hw.status === 'submitted' ? '已交' : '未交') }}
                                    </span>
                                    <span class="text-[9px] text-slate-400 font-mono">{{ hw.subjectName }}</span>
                                </div>
                                <h5 class="font-bold text-slate-800 text-xs leading-snug line-clamp-2">{{ hw.title }}</h5>
                                <p class="text-[9px] text-slate-400 font-mono mt-0.5"><i class="ph ph-clock mr-0.5"></i> 截止: {{ hw.deadline }}</p>
                            </div>
                        </div>
                    </aside>

                    <!-- 右侧 Monaco 作答调试区 -->
                    <div class="min-w-0 min-h-0 grid grid-cols-1 2xl:grid-cols-[minmax(0,1fr)_300px] gap-4 overflow-hidden">
                        <div class="min-w-0 min-h-0 grid grid-rows-[auto_minmax(0,1fr)] gap-3">
                            <!-- 作业及编程题说明 -->
                            <div v-if="selectedHomework" class="glass-panel-liquid px-4 py-3 shrink-0">
                                <div class="flex flex-wrap items-center justify-between gap-3">
                                    <div class="min-w-0">
                                        <p class="text-[10px] font-bold text-indigo-500 uppercase tracking-[0.16em]">Assignment workspace</p>
                                        <h4 class="text-sm font-extrabold text-slate-800 truncate mt-0.5">{{ selectedHomework.title }}</h4>
                                    </div>
                                    <span class="shrink-0 text-[11px] text-slate-400 font-semibold">日常 Checkpoint 编程实战</span>
                                </div>
                                <div v-if="currentHomeworkQuestion" class="mt-2 flex flex-wrap items-start gap-x-4 gap-y-1 text-xs">
                                    <p class="font-bold text-indigo-600 shrink-0">编程任务: {{ currentHomeworkQuestion.title }}</p>
                                    <p class="text-slate-500 leading-relaxed min-w-[240px] flex-1 line-clamp-2">{{ currentHomeworkQuestion.desc }}</p>
                                </div>
                            </div>

                            <!-- Monaco 编辑器及控制台 -->
                            <div class="glass-panel-static min-h-0 grid grid-rows-[auto_minmax(320px,1fr)_minmax(132px,18%)] gap-3 p-4 overflow-hidden relative">
                                <div class="flex flex-wrap items-center justify-between gap-3">
                                    <div class="flex items-center gap-2">
                                        <div class="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-sm">
                                            <i class="ph ph-code-block text-lg"></i>
                                        </div>
                                        <div>
                                            <span class="text-sm font-bold text-slate-900 block">Monaco JavaScript 编辑器</span>
                                            <span class="text-[10px] text-slate-400 font-mono">auto-save · local runner</span>
                                        </div>
                                    </div>
                                    <div class="flex flex-wrap items-center justify-end gap-2">
                                        <button @click="resetCode" 
                                                class="min-h-[34px] bg-white/80 border border-slate-200 text-slate-600 text-xs px-3.5 rounded-xl font-medium shadow-sm hover:bg-slate-50 transition-all active:scale-95">
                                            重置
                                        </button>
                                        <button @click="runHomeworkTest" :disabled="runHomeworkTesting"
                                                class="min-h-[34px] bg-indigo-600 hover:bg-indigo-700 text-white text-xs px-4 rounded-xl font-semibold active:scale-95 transition-all flex items-center gap-1">
                                            <i v-if="runHomeworkTesting" class="ph ph-spinner animate-spin"></i>
                                            <i v-else class="ph ph-play-fill"></i>
                                            运行测试
                                        </button>
                                        <button @click="handleHomeworkDiagnose" :disabled="submitHomeworkLoading"
                                                class="min-h-[34px] bg-rose-50 border border-rose-200 text-rose-600 text-xs px-4 rounded-xl font-semibold active:scale-95 transition-all flex items-center gap-1 hover:bg-rose-100">
                                            联合诊断
                                        </button>
                                        <button @click="submitHomeworkAssignment" :disabled="submitHomeworkLoading"
                                                class="min-h-[34px] bg-slate-900 hover:bg-slate-800 text-white text-xs px-4 rounded-xl font-semibold active:scale-95 transition-all flex items-center gap-1">
                                            提交作业
                                        </button>
                                    </div>
                                </div>
                                
                                <div class="min-h-0 w-full relative bg-[#1e1e1e] rounded-2xl overflow-hidden border border-slate-800 shadow-[inset_0_4px_16px_rgba(0,0,0,0.5)]">
                                    <div id="monaco-editor-container" class="absolute inset-0 w-full h-full"></div>
                                    <div v-if="isEditorLoading" class="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm z-30">
                                        <div class="w-10 h-10 border-4 border-indigo-400 border-t-transparent rounded-full animate-spin mb-4"></div>
                                        <span class="text-xs font-semibold text-indigo-300">正在从 CDN 加载 Monaco Editor...</span>
                                    </div>
                                </div>

                                <!-- 控制台输出 -->
                                <div class="min-h-0 border border-slate-200 bg-slate-50/70 rounded-2xl p-3 overflow-hidden flex flex-col">
                                    <div class="flex items-center justify-between gap-4 border-b border-slate-200 pb-2 mb-2 text-[10px] font-bold text-slate-500 select-none">
                                        <span class="flex items-center gap-1.5"><i class="ph ph-terminal-window"></i> 控制台输出</span>
                                        <span class="font-mono text-slate-400">{{ activeHomeworkConsoleLogs.length }} logs</span>
                                    </div>
                                    <div class="flex-1 overflow-y-auto font-mono text-[11px] text-slate-600 no-scrollbar">
                                        <p v-for="line in activeHomeworkConsoleLogs" :key="line" class="py-0.5">{{ line }}</p>
                                        <p v-if="activeHomeworkConsoleLogs.length === 0" class="text-slate-400">暂无输出日志。点击“运行测试”以执行代码测试用例并进行编译校验。</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 宽屏任务辅助栏：未诊断时承载任务说明与评测节奏，避免 IDE 横向失衡 -->
                        <div v-if="!homeworkDiagnosis" class="hidden 2xl:flex min-h-0 flex-col gap-3 h-full">
                            <div class="glass-panel-liquid p-4 border border-white/70 bg-white/75 flex flex-col gap-4">
                                <div class="flex items-center gap-2 border-b border-slate-100 pb-3">
                                    <div class="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                                        <i class="ph ph-list-checks text-lg"></i>
                                    </div>
                                    <div>
                                        <p class="text-xs font-bold text-slate-800">作业要点</p>
                                        <p class="text-[10px] text-slate-400 font-mono">task brief</p>
                                    </div>
                                </div>
                                <div v-if="currentHomeworkQuestion" class="space-y-2">
                                    <p class="text-xs font-bold text-indigo-600 leading-snug">{{ currentHomeworkQuestion.title }}</p>
                                    <p class="text-xs text-slate-500 leading-relaxed">{{ currentHomeworkQuestion.desc }}</p>
                                </div>
                                <div v-else class="text-xs text-slate-400 leading-relaxed">当前作业暂无编程题说明。</div>
                            </div>

                            <div class="glass-panel-liquid p-4 border border-white/70 bg-white/70 flex flex-col gap-3">
                                <div class="flex items-center gap-2">
                                    <i class="ph ph-play-circle text-indigo-500"></i>
                                    <span class="text-xs font-bold text-slate-800">评测流程</span>
                                </div>
                                <div class="grid gap-2 text-[11px] text-slate-500">
                                    <div class="flex gap-2 rounded-xl bg-white/60 border border-white/70 p-2.5">
                                        <span class="font-mono text-indigo-500">01</span>
                                        <span>在 Monaco 中补全核心函数。</span>
                                    </div>
                                    <div class="flex gap-2 rounded-xl bg-white/60 border border-white/70 p-2.5">
                                        <span class="font-mono text-indigo-500">02</span>
                                        <span>运行测试，查看控制台编译与用例反馈。</span>
                                    </div>
                                    <div class="flex gap-2 rounded-xl bg-white/60 border border-white/70 p-2.5">
                                        <span class="font-mono text-indigo-500">03</span>
                                        <span>联合诊断后提交作业结果。</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 会诊诊断面板 (仅在生成后右侧浮出) -->
                        <transition name="fade">
                            <div v-if="homeworkDiagnosis" class="hidden 2xl:flex min-h-0 flex-col gap-4 h-full">
                                <div class="glass-panel-liquid flex-1 min-h-0 p-4 overflow-y-auto no-scrollbar flex flex-col gap-4 border border-indigo-100 bg-white/95 backdrop-blur-md">
                                    <div class="flex items-center justify-between border-b border-slate-200/50 pb-3">
                                        <div class="flex items-center gap-2">
                                            <i class="ph ph-robot text-lg text-indigo-600"></i>
                                            <span class="text-xs font-bold text-slate-800">智能会诊诊断报告</span>
                                        </div>
                                        <button @click="homeworkDiagnosis = null" class="text-slate-400 hover:text-slate-700"><i class="ph ph-x"></i></button>
                                    </div>

                                    <!-- 教师批改及分数雷达图 -->
                                    <div class="flex flex-col items-center justify-center bg-white/40 border border-white/60 rounded-2xl p-3 min-h-[160px]">
                                        <p class="text-[9px] text-slate-400 font-semibold mb-1">能力评测雷达</p>
                                        <radar-chart v-if="homeworkRadarOption" :option="homeworkRadarOption" class="w-full h-[140px]"></radar-chart>
                                    </div>

                                    <!-- 各个智能体评估意见 -->
                                    <div class="flex flex-col gap-3">
                                        <div class="p-3.5 rounded-xl bg-white border border-slate-100 flex flex-col gap-1">
                                            <span class="text-[10px] font-bold text-blue-600">规划师 Alina</span>
                                            <p class="text-xs text-slate-500 leading-relaxed">{{ homeworkDiagnosis.alinaMsg }}</p>
                                        </div>
                                        <div class="p-3.5 rounded-xl bg-white border border-slate-100 flex flex-col gap-1">
                                            <span class="text-[10px] font-bold text-emerald-600">代码专家 CodeNinja</span>
                                            <p class="text-xs text-slate-500 leading-relaxed">{{ homeworkDiagnosis.codeninjaMsg }}</p>
                                        </div>
                                        <div class="p-3.5 rounded-xl bg-white border border-slate-100 flex flex-col gap-1">
                                            <span class="text-[10px] font-bold text-purple-600">知识讲授 Prof. X</span>
                                            <p class="text-xs text-slate-500 leading-relaxed">{{ homeworkDiagnosis.profxMsg }}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </transition>
                    </div>
                </div>
            </div>

            <!-- ==================== 4. 舱室 4: 竞技排位赛 (Ranked Arena) ==================== -->
            <teleport v-else-if="codingMode === 'ranked'" to="body">
            <div v-if="rankedRoomMode === 'lobby'" class="fixed inset-0 z-[9999] bg-[#fbf8f2] text-slate-900 overflow-y-auto select-none">
                <header class="sticky top-0 z-30 h-[102px] bg-[#fbf8f2]/95 backdrop-blur-xl border-b border-orange-100">
                    <div class="max-w-[1290px] mx-auto h-full px-6 flex items-center justify-between">
                        <div class="flex items-center gap-4">
                            <div class="w-[54px] h-[54px] rounded-[16px] bg-[#ff8514] text-white flex items-center justify-center shadow-[0_12px_26px_rgba(255,132,20,0.22)]">
                                <i class="ph ph-sword text-3xl"></i>
                            </div>
                            <div>
                                <h1 class="text-[28px] leading-tight font-black tracking-[0.02em]">
                                    竞技排位赛 <span class="text-[#ff6b1a] font-mono tracking-[0.08em]">Ranked Arena</span>
                                </h1>
                                <p class="text-sm text-slate-500 font-semibold mt-1">算法争锋，冲刺王者 · 全校排位对决，赢取荣誉积分</p>
                            </div>
                        </div>
                        <nav class="flex items-center gap-8 text-base font-bold">
                            <button v-for="tab in rankedTabs" :key="tab.id" :data-testid="'ranked-tab-' + tab.id" @click="switchRankedTab(tab.id)"
                                    class="relative py-2 transition-colors"
                                    :class="rankedTab === tab.id ? 'text-[#ff6b1a]' : 'text-slate-400 hover:text-slate-600'">
                                {{ tab.label }}
                                <span v-if="rankedTab === tab.id" class="absolute left-0 right-0 -bottom-0.5 h-[2px] bg-[#ff6b1a]"></span>
                            </button>
                        </nav>
                    </div>
                </header>

                <main class="max-w-[1290px] mx-auto px-6 pt-14 pb-24">
                    <button @click="goBackToLobby" class="mb-8 px-6 py-2.5 rounded-full bg-white border border-orange-200 text-[#ff6b1a] hover:text-white hover:bg-gradient-to-r hover:from-[#ffa51f] hover:to-[#ff6b1a] hover:border-transparent hover:shadow-[0_10px_20px_rgba(255,107,26,0.15)] active:scale-95 text-base font-extrabold flex items-center gap-2 transition-all w-fit cursor-pointer">
                        <i class="ph ph-arrow-left text-lg"></i> 返回大厅
                    </button>

                    <section v-if="rankedTab === 'lobby'">
                        <p class="text-[#ff6b1a] text-sm font-mono tracking-[0.16em] mb-3">RANKED LOBBY · 排位赛大厅</p>
                        <h2 class="text-[48px] leading-none mb-16 text-black" style="font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', cursive;">王者之路，由此启程</h2>

                        <div class="grid grid-cols-[minmax(0,1fr)_416px] gap-8 items-start">
                            <div class="space-y-8">
                                <section class="rounded-2xl bg-white border border-orange-100 shadow-[0_18px_38px_rgba(255,132,20,0.08)] overflow-hidden">
                                    <div class="h-2 bg-gradient-to-r from-[#ffa51f] to-[#ff6715]"></div>
                                    <div class="p-10 grid grid-cols-[280px_1fr_150px] gap-8 items-center">
                                        <div class="flex items-center gap-6">
                                            <img src="assets/ranked/badge-gold.png" alt="黄金段位" class="w-[90px] h-[90px] object-contain drop-shadow-[0_10px_20px_rgba(245,165,29,0.18)]">
                                            <div>
                                                <p class="text-sm font-semibold text-slate-500">{{ rankedPlayer.className }}</p>
                                                <h3 class="text-3xl font-black mt-1">{{ rankedPlayer.name }}</h3>
                                                <span class="inline-flex items-center gap-1.5 mt-3 px-3 py-1 rounded-full bg-[#f7a51c] text-white text-xs font-bold">
                                                    <i class="ph ph-trophy"></i>{{ rankedPlayer.tier }}
                                                </span>
                                            </div>
                                        </div>
                                        <div class="border-l border-orange-100 pl-8">
                                            <p class="text-sm text-slate-500 font-semibold">当前积分</p>
                                            <p class="text-[42px] leading-none text-[#ff6b1a] font-mono">{{ rankedPlayer.points.toLocaleString() }}</p>
                                            <div class="mt-5 flex items-center justify-between text-sm text-slate-500 font-semibold">
                                                <span>距 铂金 段位</span>
                                                <span class="text-[#ff8a18]">还需 {{ rankedPlayer.nextTierPoints - rankedPlayer.points }} 分</span>
                                            </div>
                                            <div class="mt-3 h-3 rounded-full bg-orange-50 overflow-hidden">
                                                <div class="h-full rounded-full bg-gradient-to-r from-[#ffa51f] to-[#ff6b1a]" :style="{ width: rankedPlayer.progress + '%' }"></div>
                                            </div>
                                        </div>
                                        <div class="justify-self-end rounded-2xl bg-orange-50 px-7 py-5 text-center text-[#ff6b1a] shadow-[0_18px_32px_rgba(255,132,20,0.10)]">
                                            <p class="text-2xl font-mono flex items-center justify-center gap-2"><i class="ph ph-fire"></i>{{ rankedPlayer.streak }}</p>
                                            <p class="text-sm font-bold mt-1">连胜</p>
                                        </div>
                                    </div>
                                </section>

                                <section class="rounded-2xl bg-gradient-to-br from-[#ffa51f] to-[#ff6418] text-white p-11 shadow-[0_24px_52px_rgba(255,132,20,0.22)]">
                                    <span class="inline-flex items-center gap-2 rounded-full bg-white/20 px-4 py-2 text-sm font-bold"><i class="ph ph-lightning"></i> 排位对决</span>
                                    <h3 class="text-[38px] font-black mt-7">进入竞技答题舱</h3>
                                    <p class="mt-4 text-base font-semibold text-white/90">系统将按你的段位匹配对手与题目，赢下对局即可赢取荣誉积分与连胜加成。</p>
                                    <div class="mt-8 flex gap-4">
                                        <button v-if="rankedMatchStatus === 'idle'" @click="startRankedMatch" class="min-h-[48px] px-7 rounded-xl bg-white text-[#ff6b1a] text-base font-black flex items-center gap-2 shadow-sm hover:shadow-md active:scale-95 transition-all">
                                            <i class="ph ph-sword"></i> 开始匹配
                                        </button>
                                        <button v-else-if="rankedMatchStatus === 'matching'" disabled class="min-h-[48px] px-7 rounded-xl bg-white/50 text-[#ff6b1a]/50 text-base font-black flex items-center gap-2 transition-all">
                                            <i class="ph ph-circle-notch animate-spin"></i> 正在寻找对手...
                                        </button>
                                        <button v-else-if="rankedMatchStatus === 'ready'" @click="isRankedEntryConfirmOpen = true" class="min-h-[48px] px-7 rounded-xl bg-green-500 text-white text-base font-black flex items-center gap-2 shadow-md animate-bounce active:scale-95 transition-all">
                                            <i class="ph ph-check-circle"></i> 匹配就绪，进入竞技舱
                                        </button>
                                        <button @click="askRankedCoach('本赛季怎么冲分？')" class="min-h-[48px] px-8 rounded-xl border border-white/60 text-white text-base font-black hover:bg-white/10 active:scale-95 transition-all">排位挑战</button>
                                    </div>
                                </section>

                                <section class="rounded-2xl bg-white border border-orange-100 p-8 shadow-[0_18px_38px_rgba(255,132,20,0.08)]">
                                    <div class="flex items-start justify-between">
                                        <div class="flex items-start gap-4">
                                            <div class="w-11 h-11 rounded-xl bg-[#ff8a18] text-white flex items-center justify-center"><i class="ph ph-target text-2xl"></i></div>
                                            <div>
                                                <h3 class="text-xl font-black">每日挑战</h3>
                                                <p class="text-sm text-slate-500 mt-1">每日刷新 · 2026-07-06</p>
                                            </div>
                                        </div>
                                        <span class="rounded-full bg-[#f7a51c] text-white text-sm font-bold px-4 py-1.5"><i class="ph ph-gift mr-1"></i>{{ dailyChallenge.reward }}</span>
                                    </div>
                                    <div class="mt-6 rounded-2xl bg-[#fff5cf] p-5">
                                        <div class="flex items-center gap-3">
                                            <span class="px-3 py-1 rounded-lg border border-orange-200 bg-white/60 text-[#ff6b1a] text-sm font-bold">{{ dailyChallenge.tag }}</span>
                                            <span class="text-lg font-bold">{{ dailyChallenge.title }}</span>
                                        </div>
                                        <div class="mt-5 flex items-center gap-4">
                                            <div class="flex-1 h-2.5 bg-white rounded-full overflow-hidden">
                                                <div class="h-full bg-gradient-to-r from-[#ffa51f] to-[#ff6b1a]" :style="{ width: dailyChallenge.progress + '%' }"></div>
                                            </div>
                                            <span class="text-[#ff6b1a] font-mono">{{ dailyChallenge.count }}</span>
                                        </div>
                                    </div>
                                </section>

                                <section class="rounded-2xl bg-white border border-orange-100 p-8 shadow-[0_18px_38px_rgba(255,132,20,0.08)]">
                                    <p class="text-[#ff6b1a] text-sm font-mono tracking-[0.16em] mb-2">RANKED RULES · 排位规则</p>
                                    <h3 class="text-2xl font-black mb-8">如何登顶王者</h3>
                                    <div class="grid grid-cols-2 gap-x-16 gap-y-8">
                                        <article v-for="rule in rankedRules" :key="rule.title" class="flex gap-4">
                                            <div class="w-10 h-10 rounded-xl bg-[#ff8a18] text-white flex items-center justify-center shrink-0"><i :class="['ph', rule.icon, 'text-xl']"></i></div>
                                            <div>
                                                <h4 class="text-base font-black">{{ rule.title }}</h4>
                                                <p class="text-sm text-slate-500 font-semibold leading-relaxed mt-1">{{ rule.desc }}</p>
                                            </div>
                                        </article>
                                    </div>
                                </section>
                                <section class="rounded-2xl bg-white border border-orange-100 p-8 shadow-[0_18px_38px_rgba(255,132,20,0.08)]">
                                    <p class="text-[#ff6b1a] text-sm font-mono tracking-[0.16em] mb-2">TIER LADDER · 段位阶梯</p>
                                    <h3 class="text-2xl font-black mb-7">六段荣誉之路</h3>
                                    <div class="space-y-3">
                                        <div v-for="tier in tierLadder" :key="tier.name" class="rounded-2xl border p-4 flex items-center justify-between" :class="tier.color === 'orange' ? 'bg-orange-50 border-orange-200 text-orange-600' : tier.color === 'blue' ? 'bg-blue-50 border-blue-200 text-blue-500' : tier.color === 'cyan' ? 'bg-cyan-50 border-cyan-200 text-cyan-500' : tier.color === 'amber' ? 'bg-amber-50 border-amber-200 text-amber-500' : 'bg-slate-50 border-slate-200 text-slate-400'">
                                            <div class="flex items-center gap-4">
                                                <div class="w-9 h-9 rounded-full bg-white/70 flex items-center justify-center"><i class="ph ph-shield-star"></i></div>
                                                <div>
                                                    <p class="text-lg font-black">{{ tier.name }} <span v-if="tier.peak" class="ml-2 px-2 py-0.5 rounded-md bg-[#ff8a18] text-white text-xs">巅峰</span></p>
                                                    <p class="text-sm text-slate-500 font-semibold">{{ tier.range }}</p>
                                                </div>
                                            </div>
                                            <span class="text-sm font-mono text-slate-500">{{ tier.level }}</span>
                                        </div>
                                    </div>
                                    <p class="mt-6 text-sm text-slate-500 font-semibold">达到该段位所需的最低荣誉积分即可晋级，积分回落则可能降段。冲刺更高段位可解锁更高难度题库与专属勋章。</p>
                                </section>
                            </div>

                            <!-- 右侧排行榜 (Leaderboard) -->
                            <aside class="rounded-2xl bg-white border border-orange-100 p-8 shadow-[0_18px_38px_rgba(255,132,20,0.08)]">
                                <div class="flex items-center gap-3 mb-8">
                                    <div class="w-9 h-9 rounded-xl bg-orange-50 text-[#ff6b1a] flex items-center justify-center font-bold">
                                        <i class="ph ph-list-numbers text-xl"></i>
                                    </div>
                                    <h3 class="text-xl font-black text-slate-800">全校排位榜</h3>
                                </div>
                                <div class="space-y-4">
                                    <div v-for="user in leaderboard" :key="user.name" class="flex items-center justify-between p-3.5 rounded-xl border transition-all" :class="user.self ? 'bg-orange-50 border-orange-200 ring-2 ring-orange-500/10' : 'bg-slate-50/50 border-slate-100 hover:bg-slate-50'">
                                        <div class="flex items-center gap-3">
                                            <span class="w-6 h-6 rounded-full flex items-center justify-center font-mono font-black text-xs" :class="user.rank === 1 ? 'bg-yellow-400 text-white shadow-sm' : user.rank === 2 ? 'bg-slate-300 text-white' : user.rank === 3 ? 'bg-amber-600 text-white' : 'bg-slate-200 text-slate-600'">
                                                {{ user.rank }}
                                            </span>
                                            <div>
                                                <p class="font-extrabold text-sm text-slate-800 flex items-center gap-1.5">
                                                    {{ user.name }}
                                                    <span v-if="user.self" class="text-[9px] bg-[#ff6b1a] text-white px-1 py-0.2 rounded-md font-black">你</span>
                                                </p>
                                                <p class="text-[10px] text-slate-400 font-bold mt-0.5">{{ user.tier }}段位</p>
                                            </div>
                                        </div>
                                        <div class="text-right">
                                            <p class="font-mono text-sm font-black text-slate-800">{{ user.points }}</p>
                                            <p v-if="user.streak > 0" class="text-[9px] text-[#ff6b1a] font-bold flex items-center justify-end gap-0.5 mt-0.5"><i class="ph ph-fire"></i>{{ user.streak }}连胜</p>
                                        </div>
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </section>

                    <!-- TAB: history -->
                    <section v-else-if="rankedTab === 'history'">
                        <p class="text-[#ff6b1a] text-sm font-mono tracking-[0.16em] mb-3">MATCH HISTORY · 对战历史</p>
                        <h2 class="text-[48px] leading-none mb-7 text-black" style="font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', cursive;">砺剑沙场，每一步都是成长</h2>
                        <p class="text-base text-slate-500 font-semibold mb-9">记录您在排位竞技中的每一次对决，分析胜负得失，见证积分蜕变。</p>
                        
                        <div class="grid grid-cols-[1fr_320px] gap-8 items-start">
                            <div class="space-y-4">
                                <article v-for="(match, index) in matchHistory" :key="index" class="rounded-2xl bg-white border border-orange-100 p-6 shadow-[0_18px_38px_rgba(255,132,20,0.04)] flex items-center justify-between transition-all hover:scale-[1.01]">
                                    <div class="flex items-center gap-5">
                                        <div class="w-12 h-12 rounded-xl flex items-center justify-center font-black text-sm" :class="match.result === '胜利' ? 'bg-orange-50 text-[#ff6b1a] border border-orange-100' : 'bg-slate-50 text-slate-400 border border-slate-100'">
                                            {{ match.result }}
                                        </div>
                                        <div>
                                            <h4 class="text-lg font-black text-slate-800">{{ match.title }}</h4>
                                            <p class="text-xs text-slate-500 mt-1.5 flex items-center gap-3">
                                                <span><i class="ph ph-tag mr-1 text-slate-400"></i>{{ match.type }}</span>
                                                <span><i class="ph ph-clock mr-1 text-slate-400"></i>耗时 {{ match.duration }}</span>
                                                <span><i class="ph ph-calendar mr-1 text-slate-400"></i>{{ match.time }}</span>
                                            </p>
                                        </div>
                                    </div>
                                    <div class="text-right">
                                        <span class="text-xl font-mono font-black" :class="match.result === '胜利' ? 'text-[#ff6b1a]' : 'text-slate-400'">{{ match.score }}</span>
                                        <p class="text-[10px] text-slate-400 font-bold mt-1">荣誉积分</p>
                                    </div>
                                </article>
                            </div>

                            <aside class="space-y-6">
                                <div class="rounded-2xl bg-white border border-orange-100 p-6 shadow-[0_18px_38px_rgba(255,132,20,0.04)]">
                                    <h3 class="text-base font-black text-slate-800 mb-5">生涯战绩统计</h3>
                                    <div class="space-y-4">
                                        <div v-for="stat in historyStats" :key="stat.label" class="flex items-center justify-between pb-3 border-b border-orange-50/50 last:border-0 last:pb-0">
                                            <span class="text-sm text-slate-500 font-semibold">{{ stat.label }}</span>
                                            <span class="text-lg font-mono font-bold" :class="stat.tone">{{ stat.value }}</span>
                                        </div>
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </section>

                    <!-- TAB: mistakes -->
                    <section v-else-if="rankedTab === 'mistakes'">
                        <p class="text-[#ff6b1a] text-sm font-mono tracking-[0.16em] mb-3">MISTAKE BOOK · 错题本</p>
                        <h2 class="text-[48px] leading-none mb-7 text-black" style="font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', cursive;">温故知新，弱点逐个击破</h2>
                        <p class="text-base text-slate-500 font-semibold mb-9">记录您在排位竞技中未完全通过测试用例的错题，支持 AI 针对性的原因分析与补强建议。</p>
                        
                        <div class="grid grid-cols-[1fr_320px] gap-8 items-start">
                            <div class="space-y-6">
                                <article v-for="item in rankedMistakes" :key="item.title" class="rounded-2xl bg-white border border-orange-100 p-6 shadow-[0_18px_38px_rgba(255,132,20,0.04)]">
                                    <div class="flex items-start justify-between gap-4">
                                        <div class="flex items-center gap-4">
                                            <div class="w-11 h-11 rounded-xl bg-orange-50 text-[#ff8a18] flex items-center justify-center font-bold">
                                                <i class="ph ph-file-x text-2xl"></i>
                                            </div>
                                            <div>
                                                <div class="flex items-center gap-2 flex-wrap">
                                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold" :class="item.mastered ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'">{{ item.mastered ? '已掌握' : '待复习' }}</span>
                                                    <span class="text-base font-black text-slate-800">{{ item.title }}</span>
                                                </div>
                                                <p class="text-xs text-slate-500 mt-1">
                                                    <span>{{ item.type }}</span> · 
                                                    <span>{{ item.topic }}</span> · 
                                                    <span>{{ item.count }}</span>
                                                </p>
                                            </div>
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <button @click="reviewRankedMistake(item)" class="px-4 py-2 rounded-xl border border-orange-200 text-xs font-bold text-[#ff8a18] hover:bg-orange-50 active:scale-95 transition-all">AI 诊断</button>
                                            <button @click="deleteRankedMistake(item)" class="w-9 h-9 rounded-xl border border-red-100 text-red-500 hover:bg-red-50 active:scale-95 transition-all" title="删除错题">
                                                <i class="ph ph-trash"></i>
                                            </button>
                                        </div>
                                    </div>
                                    <p class="text-xs text-slate-600 font-semibold mt-4 leading-relaxed"><span class="text-slate-400">错误现象：</span>{{ item.issue }}</p>
                                    
                                    <transition name="fade">
                                        <div v-if="item.showAnalysis" class="mt-5 rounded-2xl border border-orange-100 bg-gradient-to-br from-orange-50/40 to-orange-100/10 p-6 shadow-inner relative flex flex-col gap-4 max-h-[380px] overflow-y-auto no-scrollbar">
                                            <div class="flex items-center justify-between border-b border-orange-100 pb-3">
                                                <div class="flex items-center gap-2">
                                                    <div class="w-8 h-8 rounded-lg bg-orange-500 text-white flex items-center justify-center">
                                                        <i class="ph ph-robot text-lg"></i>
                                                    </div>
                                                    <div>
                                                        <span class="text-sm font-black text-slate-800">排位 AI 教练 · 错题诊断</span>
                                                        <span class="ml-2 text-[10px] bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded font-mono font-bold">{{ getRankedCoachConfig().model || 'qwen3.7-plus' }}</span>
                                                    </div>
                                                </div>
                                                <button @click.stop="item.showAnalysis = false" class="w-7 h-7 rounded-full hover:bg-orange-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors">
                                                    <i class="ph ph-x text-sm"></i>
                                                </button>
                                            </div>
                                            
                                            <div v-if="item.analysisLoading" class="py-8 flex flex-col items-center justify-center gap-3">
                                                <div class="flex gap-1.5 items-center justify-center">
                                                    <span class="w-2 h-2 rounded-full bg-orange-500 animate-bounce [animation-delay:0ms]"></span>
                                                    <span class="w-2 h-2 rounded-full bg-orange-500 animate-bounce [animation-delay:150ms]"></span>
                                                    <span class="w-2 h-2 rounded-full bg-orange-500 animate-bounce [animation-delay:300ms]"></span>
                                                </div>
                                                <span class="text-xs font-bold text-slate-400">AI 教练正在诊断代码缺陷...</span>
                                            </div>
                                            
                                            <div v-else-if="item.aiAnalysis" class="space-y-4 text-slate-700 text-sm leading-relaxed">
                                                <div class="rounded-xl border border-red-100 bg-red-50/20 p-4">
                                                    <div class="flex items-center gap-2 mb-2">
                                                        <span class="px-2 py-0.5 rounded bg-red-100 text-red-600 text-[10px] font-bold">诊断结论</span>
                                                        <span class="text-xs font-black text-slate-800">错误根源定位</span>
                                                    </div>
                                                    <p class="font-semibold text-slate-600 break-words whitespace-pre-wrap">{{ item.aiAnalysis.diagnosis }}</p>
                                                </div>
                                                
                                                <div class="rounded-xl border border-blue-100 bg-blue-50/20 p-4">
                                                    <div class="flex items-center gap-2 mb-2">
                                                        <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-600 text-[10px] font-bold">核心考点</span>
                                                        <span class="text-xs font-black text-slate-800">算法考点剖析</span>
                                                    </div>
                                                    <p class="font-semibold text-slate-600 break-words whitespace-pre-wrap">{{ item.aiAnalysis.concept }}</p>
                                                </div>
                                                
                                                <div class="rounded-xl border border-emerald-100 bg-emerald-50/20 p-4">
                                                    <div class="flex items-center gap-2 mb-2">
                                                        <span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-600 text-[10px] font-bold">针对练习</span>
                                                        <span class="text-xs font-black text-slate-800">防错建议与进阶题</span>
                                                    </div>
                                                    <p class="font-semibold text-slate-600 break-words whitespace-pre-wrap">{{ item.aiAnalysis.practice }}</p>
                                                </div>
                                            </div>
                                        </div>
                                    </transition>
                                </article>
                            </div>

                            <aside class="space-y-6">
                                <div class="rounded-2xl bg-white border border-orange-100 p-6 shadow-[0_18px_38px_rgba(255,132,20,0.04)]">
                                    <h3 class="text-base font-black text-slate-800 mb-5">错题归纳</h3>
                                    <div class="space-y-4">
                                        <div v-for="stat in mistakeStats" :key="stat.label" class="flex items-center justify-between pb-3 border-b border-orange-50/50 last:border-0 last:pb-0">
                                            <span class="text-sm text-slate-500 font-semibold flex items-center gap-2">
                                                <i class="ph" :class="stat.icon"></i>
                                                {{ stat.label }}
                                            </span>
                                            <span class="text-lg font-mono font-bold" :class="stat.tone">{{ stat.value }}</span>
                                        </div>
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </section>

                    <!-- TAB: season -->
                    <section v-else>
                        <p class="text-[#ff6b1a] text-sm font-mono tracking-[0.16em] mb-3">SEASONS · 赛季</p>
                        <h2 class="text-[48px] leading-none mb-7 text-black" style="font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', cursive;">一个学期，一段王者征程</h2>
                        <p class="text-base text-slate-500 font-semibold mb-9">每个学期为一个赛季，赛季结束后按照最终段位结算荣誉勋章与积分奖励。</p>
                        <div class="space-y-8">
                            <article v-for="season in seasonList" :key="season.name" class="rounded-2xl bg-white border border-orange-100 shadow-[0_18px_38px_rgba(255,132,20,0.08)] overflow-hidden">
                                <div v-if="season.current" class="h-2 bg-gradient-to-r from-[#ffa51f] to-[#ff6715]"></div>
                                <div class="p-9">
                                    <div class="flex items-start justify-between gap-8">
                                        <div class="flex gap-6">
                                            <img src="assets/ranked/badge-gold.png" alt="赛季段位" class="w-[92px] h-[92px] object-contain drop-shadow-[0_10px_20px_rgba(245,165,29,0.18)]">
                                            <div>
                                                <div class="flex items-center gap-3">
                                                    <h3 class="text-3xl font-black">{{ season.name }}</h3>
                                                    <span class="px-3 py-1 rounded-lg text-sm font-black" :class="season.current ? 'bg-[#ff6b1a] text-white' : 'bg-slate-100 text-slate-600'">{{ season.status }}</span>
                                                </div>
                                                <p class="mt-3 text-base text-slate-500 font-semibold"><i class="ph ph-calendar mr-2"></i>{{ season.date }}</p>
                                            </div>
                                        </div>
                                        <div class="text-right">
                                            <p class="text-sm text-slate-500 font-bold">当前积分 · 段位</p>
                                            <p class="mt-1 text-4xl text-[#ff6b1a] font-mono">{{ season.score }}</p>
                                            <p class="text-base text-[#ff8a18] font-bold mt-1">{{ season.tier }}</p>
                                        </div>
                                    </div>
                                    <div v-if="season.current" class="mt-8">
                                        <div class="flex justify-between text-sm text-slate-500 font-bold mb-2"><span>赛季进度</span><span class="text-[#ff6b1a]">{{ season.progress }}%</span></div>
                                        <div class="h-3 rounded-full bg-orange-50 overflow-hidden"><div class="h-full bg-gradient-to-r from-[#ffa51f] to-[#ff6b1a]" :style="{ width: season.progress + '%' }"></div></div>
                                    </div>
                                    <div class="mt-8 grid grid-cols-4 gap-4">
                                        <div class="rounded-2xl border border-orange-100 p-5"><i class="ph ph-trophy text-[#ff6b1a]"></i><p class="mt-3 text-sm text-slate-500 font-bold">胜率</p><p class="text-2xl text-[#ff6b1a] font-mono">{{ season.winRate }}</p><p class="text-sm text-slate-500">{{ season.record }}</p></div>
                                        <div class="rounded-2xl border border-orange-100 p-5"><i class="ph ph-fire text-[#ff6b1a]"></i><p class="mt-3 text-sm text-slate-500 font-bold">最高连胜</p><p class="text-2xl text-[#ff6b1a] font-mono">{{ season.streak }}</p><p class="text-sm text-slate-500">连胜场次</p></div>
                                        <div class="rounded-2xl border border-orange-100 p-5"><i class="ph ph-trophy text-[#ff6b1a]"></i><p class="mt-3 text-sm text-slate-500 font-bold">巅峰段位</p><p class="text-2xl text-[#ff6b1a] font-bold">{{ season.peak }}</p><p class="text-sm text-slate-500">赛季最高</p></div>
                                        <div class="rounded-2xl border border-orange-100 p-5"><i class="ph ph-users-three text-[#ff6b1a]"></i><p class="mt-3 text-sm text-slate-500 font-bold">全校排名</p><p class="text-2xl text-[#ff6b1a] font-mono">{{ season.rank }}</p><p class="text-sm text-slate-500">{{ season.total }}</p></div>
                                    </div>
                                    <div class="mt-7 rounded-2xl bg-[#fff5cf] p-5 text-base font-semibold"><i class="ph ph-gift text-[#ff6b1a] mr-2"></i><span class="font-black">赛季奖励</span><p class="mt-1">{{ season.reward }}</p></div>
                                </div>
                            </article>
                        </div>
                    </section>
                </main>

                <!-- AI Coach Floating Button -->
                <button v-if="!rankedCoachOpen" @click.stop.prevent="rankedCoachOpen = true" class="fixed right-10 bottom-8 z-[99999] pointer-events-auto cursor-pointer w-20 h-20 rounded-full bg-[#ff8514] text-white shadow-[0_18px_42px_rgba(255,132,20,0.42)] flex items-center justify-center hover:scale-105 active:scale-95 transition-transform">
                    <i class="ph ph-robot text-4xl pointer-events-none"></i>
                    <span class="absolute right-2 top-1 text-white text-xl pointer-events-none">✦</span>
                </button>

                <!-- AI Coach Panel -->
                <section v-if="rankedCoachOpen" class="fixed right-8 bottom-8 z-[99999] pointer-events-auto w-[570px] h-[80vh] max-h-[720px] min-h-[480px] rounded-[28px] bg-white border border-orange-100 shadow-[0_28px_70px_rgba(255,132,20,0.28)] overflow-hidden flex flex-col">
                    <div class="h-[92px] bg-gradient-to-r from-[#ffa51f] to-[#ff6b1a] text-white px-6 flex items-center justify-between shrink-0">
                        <div class="flex items-center gap-4">
                            <div class="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center"><i class="ph ph-robot text-3xl"></i></div>
                            <div>
                                <h3 class="text-2xl font-black">排位 AI 教练</h3>
                                <p class="text-base font-semibold text-white/90">分析失误 · 提升竞赛水平</p>
                            </div>
                        </div>
                        <button @click.stop.prevent="rankedCoachOpen = false" class="w-10 h-10 rounded-full hover:bg-white/15 flex items-center justify-center cursor-pointer pointer-events-auto"><i class="ph ph-x text-2xl"></i></button>
                    </div>
                    <div ref="rankedCoachChatScroll" class="flex-1 min-h-0 overflow-y-auto p-6">
                        <div class="rounded-2xl border border-orange-100 bg-white px-6 py-5 text-lg leading-9">
                            <p v-for="line in coachSuggestions" :key="line" class="mb-2 last:mb-0">{{ line }}</p>
                        </div>
                        <div v-if="isRankedCoachLoading" class="mt-4 flex items-start gap-3">
                            <div class="w-10 h-10 rounded-full bg-orange-100 text-[#ff8514] flex items-center justify-center shrink-0 animate-pulse">
                                <i class="ph ph-robot text-xl"></i>
                            </div>
                            <div class="rounded-2xl bg-orange-50/60 border border-orange-100 px-5 py-3 text-sm font-semibold text-slate-600 leading-relaxed flex items-center gap-2">
                                <span>排位 AI 教练正在思考中</span>
                                <span class="flex gap-1 items-center h-2">
                                    <span class="w-1.5 h-1.5 rounded-full bg-[#ff8514] animate-bounce [animation-delay:0ms]"></span>
                                    <span class="w-1.5 h-1.5 rounded-full bg-[#ff8514] animate-bounce [animation-delay:150ms]"></span>
                                    <span class="w-1.5 h-1.5 rounded-full bg-[#ff8514] animate-bounce [animation-delay:300ms]"></span>
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="border-t border-orange-100 p-6 bg-white shrink-0">
                        <div class="flex flex-wrap gap-3 mb-5">
                            <button :disabled="isRankedCoachLoading" @click="askRankedCoach('分析我的排位')" class="px-5 py-3 rounded-xl bg-[#ff8a18] text-white font-black hover:bg-orange-600 active:scale-95 disabled:opacity-50 disabled:pointer-events-none transition-all flex items-center gap-1.5"><i class="ph ph-magic-wand"></i>分析我的排位</button>
                            <button :disabled="isRankedCoachLoading" @click="askRankedCoach('我的失误在哪里？')" class="px-5 py-3 rounded-xl border border-orange-200 font-bold text-slate-600 hover:bg-slate-50 active:scale-95 disabled:opacity-50 disabled:pointer-events-none transition-all">我的失误在哪里？</button>
                            <button :disabled="isRankedCoachLoading" @click="askRankedCoach('如何提高竞赛水平？')" class="px-5 py-3 rounded-xl border border-orange-200 font-bold text-slate-600 hover:bg-slate-50 active:scale-95 disabled:opacity-50 disabled:pointer-events-none transition-all">如何提高竞赛水平？</button>
                            <button :disabled="isRankedCoachLoading" @click="askRankedCoach('本赛季怎么冲分？')" class="px-5 py-3 rounded-xl border border-orange-200 font-bold text-slate-600 hover:bg-slate-50 active:scale-95 disabled:opacity-50 disabled:pointer-events-none transition-all">本赛季怎么冲分？</button>
                        </div>
                        <div class="flex gap-3">
                            <input :disabled="isRankedCoachLoading" v-model="rankedCoachInput" @keydown.enter="askRankedCoach()" class="flex-1 h-16 rounded-2xl border border-orange-200 px-6 text-lg outline-none focus:ring-2 focus:ring-orange-200 disabled:bg-slate-50 disabled:text-slate-400" :placeholder="isRankedCoachLoading ? 'AI教练正在思考中...' : '向排位教练提问...'" />
                            <button @click.stop.prevent="askRankedCoach()" :disabled="!rankedCoachInput.trim() || isRankedCoachLoading" class="w-16 h-16 rounded-2xl text-white flex items-center justify-center transition-all duration-300" :class="(rankedCoachInput.trim() && !isRankedCoachLoading) ? 'bg-[#ff8514] hover:bg-[#e0700d] cursor-pointer hover:scale-105 active:scale-95' : 'bg-orange-300 cursor-not-allowed opacity-60'">
                                <i :class="isRankedCoachLoading ? 'ph ph-circle-notch animate-spin' : 'ph ph-paper-plane-tilt'" class="text-3xl pointer-events-none"></i>
                            </button>
                        </div>
                    </div>
                </section>
            </div> <!-- End of Lobby Mode -->

            <!-- 竞技答题舱全屏 IDE (Light Theme) -->
            <div v-else-if="rankedRoomMode === 'arena'" class="fixed inset-0 z-[10000] bg-[#fcfaf7] text-slate-800 overflow-hidden flex flex-col p-4 gap-3 select-none">
                <!-- CSS Keyframes inline styles -->
                <style>
                @keyframes scaleUp {
                    from { transform: scale(0.92); opacity: 0; }
                    to { transform: scale(1); opacity: 1; }
                }
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                .animate-scale-up {
                    animation: scaleUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
                }
                .animate-fade-in {
                    animation: fadeIn 0.25s ease-out forwards;
                }
                </style>

                <!-- 全屏防泄密动态盲水印 -->
                <div class="pointer-events-none fixed inset-0 z-[20000] overflow-hidden opacity-[0.035]" aria-hidden="true">
                    <div class="w-[200%] h-[200%] flex flex-wrap gap-x-24 gap-y-16 -ml-32 -mt-32 -rotate-12 transform-gpu">
                        <div v-for="n in 120" :key="n" class="text-orange-950/20 font-bold whitespace-nowrap text-lg tracking-widest uppercase">
                            {{ rankedPlayer.name }} • RANKED ARENA • {{ watermarkTime }}
                        </div>
                    </div>
                </div>

                <!-- 顶部对决状态栏 -->
                <div class="bg-white border border-orange-100 rounded-2xl px-5 py-3 text-slate-700 shadow-sm backdrop-blur-md relative z-10">
                    <div class="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                        <!-- 左侧对局信息 -->
                        <div class="flex items-center gap-4 min-w-0">
                            <button @click="isRankedExitConfirmOpen = true" class="w-10 h-10 rounded-xl border border-slate-200 bg-white text-slate-400 hover:text-slate-700 hover:bg-slate-50 flex items-center justify-center transition-all" title="退出对战并认输">
                                <i class="ph ph-arrow-left text-lg"></i>
                            </button>
                            <div class="min-w-0">
                                <div class="flex flex-wrap items-center gap-2">
                                    <h2 class="font-extrabold text-base truncate text-slate-900">排位对决：{{ rankedProblem.title }}</h2>
                                    <span class="text-[10px] px-2 py-0.5 rounded-full bg-orange-500/10 text-orange-600 border border-orange-500/20">竞技答题舱</span>
                                    <span class="text-[10px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-600 border border-red-500/20">切屏作弊监控</span>
                                </div>
                                <p class="text-[10px] text-slate-500 mt-1">选手: {{ rankedPlayer.name }} ({{ rankedPlayer.tier }}) · 满三场失焦违规即判定失败</p>
                            </div>
                        </div>

                        <!-- 中间对手进度展示栏 -->
                        <div class="flex items-center gap-3 bg-orange-50/40 border border-orange-100/50 rounded-xl px-4 py-2 max-w-sm w-full xl:w-auto">
                            <div class="w-2.5 h-2.5 rounded-full bg-orange-500 animate-pulse"></div>
                            <div class="text-xs font-semibold text-slate-700 min-w-[210px]">
                                <span class="text-slate-500 block text-[9px] uppercase tracking-wider">对手: 苏晚晴 (钻石) 进度</span>
                                <span class="truncate block mt-0.5 text-slate-800">{{ rankedOpponentStatus }}</span>
                            </div>
                            <div class="w-20 bg-slate-200 h-2 rounded-full overflow-hidden shrink-0">
                                <div class="bg-gradient-to-r from-orange-500 to-amber-400 h-full rounded-full transition-all duration-1000" :style="{ width: rankedOpponentProgress + '%' }"></div>
                            </div>
                        </div>

                        <!-- 右侧对局控制与倒计时 -->
                        <div class="flex flex-wrap items-center gap-2">
                            <div class="h-10 px-4 rounded-xl bg-orange-50 border border-orange-200 text-[#ff6b1a] flex items-center gap-2 font-mono font-bold tracking-wider shadow-inner">
                                <i class="ph ph-clock text-lg"></i>
                                {{ formatDuration(rankedRemainingSeconds) }}
                            </div>
                            <button @click="submitRankedMatch" :disabled="isRankedRunning" class="h-10 px-5 rounded-xl bg-gradient-to-r from-orange-500 to-red-600 text-white text-sm font-black flex items-center gap-2 shadow-lg shadow-orange-500/15 hover:brightness-110 active:scale-95 disabled:opacity-60 transition-all">
                                <i class="ph ph-paper-plane-tilt"></i> 提交代码并结算
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 违规警告横条 -->
                <div v-if="rankedBlurViolationCount > 0" class="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-xs font-bold text-red-600 flex items-center gap-2 animate-pulse shrink-0">
                    <i class="ph ph-warning-circle text-lg"></i>
                    <span>安全警告：检测到您已发生过 {{ rankedBlurViolationCount }} 次切出窗口违规行为。请保持全屏专注，累计达到 {{ MAX_RANKED_BLUR_VIOLATIONS }} 次将强制判定答卷失败！</span>
                </div>

                <!-- IDE 主体 -->
                <div class="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[380px_minmax(0,1fr)] gap-3">
                    <!-- 左侧题目面板 -->
                    <aside class="min-h-0 rounded-2xl border border-orange-100 bg-white p-4 flex flex-col gap-4 shadow-sm">
                        <div class="flex items-center justify-between gap-3 border-b border-orange-50 pb-3">
                            <div>
                                <p class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">{{ rankedProblem.category }}</p>
                                <h3 class="text-lg font-black text-slate-800 mt-0.5">{{ rankedProblem.title }}</h3>
                            </div>
                            <span class="text-[10px] font-bold text-orange-600 bg-orange-50 border border-orange-100 rounded-lg px-2.5 py-1">难度: {{ rankedProblem.difficulty }}</span>
                        </div>

                        <div class="grid grid-cols-2 gap-2 text-[11px] shrink-0">
                            <div class="rounded-xl bg-slate-50 border border-slate-200 px-3 py-2 text-slate-500">
                                <p class="font-bold text-slate-400">时间限制</p>
                                <p class="font-mono mt-1 text-slate-800">{{ rankedProblem.timeLimitMs }} ms</p>
                            </div>
                            <div class="rounded-xl bg-slate-50 border border-slate-200 px-3 py-2 text-slate-500">
                                <p class="font-bold text-slate-400">内存限制</p>
                                <p class="font-mono mt-1 text-slate-800">{{ rankedProblem.memoryLimitMb }} MB</p>
                            </div>
                        </div>

                        <div class="flex-1 overflow-y-auto no-scrollbar pr-1">
                            <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">{{ rankedProblem.desc }}</p>
                        </div>
                    </aside>

                    <!-- 右侧编辑与判题面板 -->
                    <main class="min-h-0 flex flex-col gap-3">
                        <div class="rounded-2xl border border-orange-100 bg-white flex-1 min-h-0 p-4 flex flex-col shadow-sm">
                            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3 shrink-0">
                                <div>
                                    <p class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">在线 IDE (JavaScript)</p>
                                    <p class="text-xs font-bold text-slate-500 mt-0.5">请编写入口函数: <span class="font-mono text-orange-600">{{ rankedProblem.funcName }}</span></p>
                                </div>
                                <div class="flex items-center gap-2">
                                    <button @click="setRankedEditorCode(rankedProblem.starterCode)" class="h-9 px-3.5 text-xs rounded-xl border border-slate-200 bg-slate-50 text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-all font-semibold">
                                        重置
                                    </button>
                                    <button @click="runRankedCode" :disabled="isRankedRunning" class="h-9 px-4 text-xs rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-white font-black flex items-center gap-1.5 shadow-md shadow-orange-500/10 hover:brightness-110 active:scale-95 disabled:opacity-60 transition-all">
                                        <i v-if="isRankedRunning" class="ph ph-spinner animate-spin"></i>
                                        <i v-else class="ph ph-play-fill"></i>
                                        运行测试用例
                                    </button>
                                </div>
                            </div>
                            
                            <div class="flex-1 min-h-[300px] bg-white rounded-2xl overflow-hidden border border-slate-200 shadow-inner relative">
                                <div id="monaco-editor-container-ranked" class="absolute inset-0"></div>
                                <textarea v-if="useRankedPlainEditor" v-model="rankedAnswers[rankedProblem.id]" class="absolute inset-0 w-full h-full bg-white text-slate-800 font-mono text-sm p-4 outline-none resize-none"></textarea>
                                <div v-if="isRankedEditorLoading" class="absolute inset-0 flex flex-col items-center justify-center text-orange-600 bg-white/80 text-sm backdrop-blur-sm z-30">
                                    <div class="w-10 h-10 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                                    <span class="font-bold animate-pulse">正在加载 Monaco Editor 内核...</span>
                                </div>
                            </div>
                        </div>

                        <!-- 用例与控制台面板 -->
                        <div class="rounded-2xl border border-orange-100 bg-white h-[200px] p-4 flex flex-col overflow-hidden shadow-sm shrink-0">
                            <div class="flex items-center justify-between border-b border-slate-100 mb-3 shrink-0">
                                <div class="flex gap-4 text-xs font-bold">
                                    <button @click="rankedActiveTab = 'cases'" :class="rankedActiveTab === 'cases' ? 'text-orange-600 border-b-2 border-orange-500' : 'text-slate-400'" class="pb-2">公开测试用例</button>
                                    <button @click="rankedActiveTab = 'console'" :class="rankedActiveTab === 'console' ? 'text-orange-600 border-b-2 border-orange-500' : 'text-slate-400'" class="pb-2">编译控制台</button>
                                </div>
                                <span class="text-[10px] text-slate-400 font-semibold pb-2">测评基于 LRU Cache 精准算法判断</span>
                            </div>
                            <div class="flex-1 overflow-y-auto no-scrollbar">
                                <div v-show="rankedActiveTab === 'cases'" class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <div v-for="item in rankedTestCaseResults" :key="item.label" class="bg-orange-50/20 border border-orange-100/50 rounded-xl p-3 text-xs">
                                        <div class="flex items-center justify-between gap-2">
                                            <p class="font-bold text-slate-700">{{ item.label }}</p>
                                            <span class="px-2 py-0.5 rounded-lg text-[9px] font-bold" :class="item.status === 'passed' ? 'bg-emerald-100 text-emerald-600 border border-emerald-200' : item.status === 'failed' || item.status === 'error' ? 'bg-red-100 text-red-600 border border-red-200' : 'bg-slate-100 text-slate-500'">{{ item.status }}</span>
                                        </div>
                                        <p class="text-slate-500 mt-2 font-mono truncate">输入: {{ JSON.stringify(item.input) }}</p>
                                        <p class="text-slate-500 mt-1 font-mono truncate">期望值: {{ JSON.stringify(item.expected) }}</p>
                                        <p v-if="item.actual !== null" class="text-slate-700 mt-1 font-mono truncate">实际输出: {{ JSON.stringify(item.actual) }}</p>
                                        <p v-if="item.error" class="text-red-600 mt-1 font-mono break-words whitespace-pre-wrap">{{ item.error }}</p>
                                    </div>
                                </div>
                                <div v-show="rankedActiveTab === 'console'" class="bg-slate-50 text-slate-700 rounded-xl p-3 font-mono text-xs min-h-full border border-slate-100">
                                    <p v-for="(line, idx) in rankedConsoleLogs" :key="idx" class="border-b border-slate-100 py-1">{{ line }}</p>
                                    <p v-if="rankedConsoleLogs.length === 0" class="text-slate-400">运行代码后，这里会显示编译信息、输出日志与执行耗时。</p>
                                </div>
                            </div>
                        </div>
                    </main>
                </div>
            </div>

            <!-- 入舱确认弹窗 -->
            <div v-if="isRankedEntryConfirmOpen" class="fixed inset-0 z-[10001] flex items-center justify-center bg-slate-950/60 px-4 backdrop-blur-sm">
                <div class="w-full max-w-2xl rounded-3xl bg-white shadow-2xl overflow-hidden border border-orange-100 animate-fade-in" role="dialog" aria-modal="true">
                    <div class="p-6 sm:p-8">
                        <div class="flex items-start justify-between gap-4 mb-6">
                            <div>
                                <p class="text-xs font-bold text-orange-600 uppercase tracking-wider">竞技答题舱安全准入</p>
                                <h2 class="text-2xl font-black text-slate-900 mt-2">确定进入竞技答题舱对决？</h2>
                                <p class="text-sm text-slate-600 mt-2">匹配对手：计算机学院 · 苏晚晴 (钻石段位)　|　挑战题目：Cache 组相联命中模拟</p>
                            </div>
                            <div class="w-14 h-14 rounded-2xl bg-orange-50 text-orange-600 flex items-center justify-center shrink-0 shadow-sm">
                                <i class="ph ph-shield-warning text-3xl"></i>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="rounded-2xl bg-orange-50/40 border border-orange-100/50 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-orange-600 shadow-sm flex items-center justify-center shrink-0">
                                    <i class="ph ph-corners-out text-lg"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-950">全屏沉浸对决</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1">系统将请求进入浏览器全屏，未进入全屏无法开始计时答题。</p>
                                </div>
                            </div>
                            <div class="rounded-2xl bg-orange-50/40 border border-orange-100/50 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-orange-600 shadow-sm flex items-center justify-center shrink-0">
                                    <i class="ph ph-arrows-out-cardinal text-lg"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-950">严禁切屏与失焦</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1">切屏、隐藏网页、窗口失焦达3次或超过10秒将自动判定为负。</p>
                                </div>
                            </div>
                            <div class="rounded-2xl bg-orange-50/40 border border-orange-100/50 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-orange-600 shadow-sm flex items-center justify-center shrink-0">
                                    <i class="ph ph-copy-simple text-lg"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-950">限制复制粘贴</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1">竞技期间全局拦截复制、粘贴、剪切操作及浏览器右键菜单。</p>
                                </div>
                            </div>
                            <div class="rounded-2xl bg-orange-50/40 border border-orange-100/50 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-orange-600 shadow-sm flex items-center justify-center shrink-0">
                                    <i class="ph ph-clock text-lg"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-950">限时挑战 30 分钟</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1">倒计时结束将强制自动提交，通过用例较多或耗时较短者获胜。</p>
                                </div>
                            </div>
                        </div>

                        <div class="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-xs text-amber-800 leading-relaxed flex items-start gap-3">
                            <i class="ph ph-warning-circle text-lg shrink-0 mt-0.5 text-amber-600"></i>
                            <div>
                                点击“确认进入”后，系统将请求全屏。竞技过程中若遭遇 <b>强退、逃跑或作弊判定</b>，将扣除 100 荣誉积分，并立即中断当前的 <b>{{ rankedPlayer.streak }} 连胜</b>。
                            </div>
                        </div>

                        <div class="mt-8 flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
                            <button @click="cancelRankedEntry" class="h-12 px-6 rounded-xl border border-slate-200 bg-white text-sm font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors">
                                取消，返回大厅
                            </button>
                            <button @click="confirmRankedEntry" class="h-12 px-6 rounded-xl bg-gradient-to-r from-orange-500 to-red-600 text-white text-sm font-bold shadow-lg shadow-orange-500/20 hover:brightness-110 flex items-center justify-center gap-2 transition-all active:scale-95">
                                <i class="ph ph-corners-out text-lg"></i>
                                确认，进入全屏竞技
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 强退确认弹窗 -->
            <div v-if="isRankedExitConfirmOpen" class="fixed inset-0 z-[10002] flex items-center justify-center bg-slate-950/60 px-4 backdrop-blur-sm">
                <div class="w-full max-w-md rounded-3xl bg-white shadow-2xl overflow-hidden p-6 sm:p-8 border border-red-100" role="dialog" aria-modal="true">
                    <div class="flex items-center justify-center w-16 h-16 rounded-2xl bg-red-50 text-red-600 mb-6 mx-auto shadow-inner">
                        <i class="ph ph-warning text-3xl animate-bounce"></i>
                    </div>
                    <h2 class="text-xl font-black text-slate-900 text-center">中途退赛警告！</h2>
                    <p class="text-sm text-slate-600 text-center mt-3 leading-relaxed">
                        强行退出答题舱将被视为<span class="font-bold text-red-600">逃跑认输</span>，系统将<span class="font-bold text-red-600">扣除 100 积分</span>并中断您的连胜纪录。确认退出？
                    </p>
                    <div class="mt-8 flex flex-col sm:flex-row justify-center gap-3">
                        <button @click="isRankedExitConfirmOpen = false" class="h-12 px-6 rounded-xl border border-slate-200 bg-white text-sm font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-all flex-1">
                            取消，继续答题
                        </button>
                        <button @click="isRankedExitConfirmOpen = false; resolveRankedMatch('cheat_lose', '中途退出对局')" class="h-12 px-6 rounded-xl bg-gradient-to-r from-red-600 to-rose-700 text-white text-sm font-bold hover:brightness-110 transition-all active:scale-95 flex-1">
                            确认退赛
                        </button>
                    </div>
                </div>
            </div>

            <!-- 结算大屏模态窗 -->
            <div v-if="isRankedSettlementOpen" class="fixed inset-0 z-[10003] flex items-center justify-center bg-slate-950/65 px-4 backdrop-blur-md">
                <div class="w-full max-w-xl rounded-3xl bg-white border overflow-hidden p-8 text-center text-slate-800 animate-scale-up"
                     :class="rankedMatchResult === 'win' ? 'border-orange-200 shadow-[0_24px_64px_rgba(247,165,28,0.18)]' : 'border-red-100 shadow-[0_24px_64px_rgba(244,63,94,0.12)]'">
                    
                    <template v-if="rankedMatchResult === 'win'">
                        <div class="flex justify-center mb-6">
                            <div class="relative w-28 h-28 bg-gradient-to-tr from-amber-400 to-orange-500 rounded-full flex items-center justify-center shadow-lg shadow-orange-500/20 animate-pulse animate-fade-in">
                                <i class="ph ph-trophy text-6xl text-white"></i>
                                <span class="absolute -top-1 -right-1 text-yellow-300 text-2xl animate-ping">✦</span>
                            </div>
                        </div>
                        <h1 class="text-4xl font-extrabold tracking-wider bg-gradient-to-r from-amber-500 to-orange-600 bg-clip-text text-transparent" style="font-family: 'Ma Shan Zheng', cursive;">VICTORY · 胜利</h1>
                        <p class="text-sm text-slate-500 mt-2 font-semibold">你击败了对手 苏晚晴！完美通过所有测试用例！</p>
                        
                        <div class="mt-8 rounded-2xl bg-orange-50 border border-orange-100 py-5 px-8 max-w-sm mx-auto">
                            <div class="flex justify-between items-center text-slate-600 font-bold">
                                <span>段位成长</span>
                                <span class="text-orange-600 font-mono text-2xl">+231 积分</span>
                            </div>
                            <div class="mt-4 flex justify-between items-center text-slate-600 font-bold">
                                <span>连胜场次</span>
                                <span class="text-amber-500 font-mono text-xl flex items-center gap-1">
                                    <i class="ph ph-fire text-xl animate-bounce"></i>
                                    {{ rankedPlayer.streak }} 连胜
                                </span>
                            </div>
                        </div>

                        <div class="mt-6 p-4 rounded-xl bg-orange-50/50 border border-orange-100/50 text-xs text-slate-600 text-left leading-relaxed">
                            <span class="font-extrabold text-orange-600 block mb-1">排位 AI 教练点拔：</span>
                            恭喜你！在「Cache 组相联命中模拟」的对决中，你逻辑周密，LRU的替换时戳更新也无懈可击。当前连胜已累加，积分进度离铂金段位更近了一步！继续保持。
                        </div>
                    </template>

                    <template v-else>
                        <div class="flex justify-center mb-6">
                            <div class="relative w-28 h-28 bg-gradient-to-tr from-rose-50 to-red-100 border border-red-250 rounded-full flex items-center justify-center shadow-lg shadow-red-500/10">
                                <i class="ph ph-x-circle text-6xl text-red-500"></i>
                            </div>
                        </div>
                        <h1 class="text-4xl font-extrabold tracking-wider bg-gradient-to-r from-red-500 to-rose-600 bg-clip-text text-transparent" style="font-family: 'Ma Shan Zheng', cursive;">DEFEAT · 战败</h1>
                        <p class="text-sm text-slate-500 mt-2 font-semibold">
                            {{ rankedMatchResult === 'cheat_lose' ? '对局因发生安全违规而被判定为负' : '本局挑战未全数通过公开测试样例！' }}
                        </p>
                        
                        <div class="mt-8 rounded-2xl bg-red-50 border border-red-100 py-5 px-8 max-w-sm mx-auto">
                            <div class="flex justify-between items-center text-slate-500 font-bold">
                                <span>段位变动</span>
                                <span class="text-red-500 font-mono text-2xl">-100 积分</span>
                            </div>
                            <div class="mt-4 flex justify-between items-center text-slate-500 font-bold">
                                <span>连胜状态</span>
                                <span class="text-slate-400 font-mono text-lg">连胜中断</span>
                            </div>
                        </div>

                        <div class="mt-6 p-4 rounded-xl bg-red-50/50 border border-red-100/50 text-xs text-slate-600 text-left leading-relaxed">
                            <span class="font-extrabold text-red-600 block mb-1">排位 AI 教练点拔：</span>
                            胜败乃常事。在 Cache 组相联映射的实现中，要注意每行 valid 有效位以及 LRU 淘汰时的顺序维护，特别是访问命中时需要更新它的最新使用状态。别气馁，把本题加入错题本，下回继续赢回来！
                        </div>
                    </template>

                    <div class="mt-8 flex justify-center">
                        <button @click="closeRankedSettlement" class="h-12 px-10 rounded-2xl bg-[#ff8514] text-white hover:bg-[#e0700d] font-black shadow-lg hover:shadow-orange-500/10 active:scale-95 transition-all flex items-center justify-center gap-2">
                            返回排位大厅
                        </button>
                    </div>
                </div>
            </div>

            <!-- 入舱确认弹窗 -->
            <div v-if="isRankedEntryConfirmOpen" class="fixed inset-0 z-[10001] flex items-center justify-center bg-slate-950/60 px-4 backdrop-blur-sm">
                <div class="w-full max-w-2xl rounded-3xl bg-white shadow-2xl overflow-hidden border border-orange-100 animate-fade-in" role="dialog" aria-modal="true">
                    <div class="p-6 sm:p-8">
                        <div class="flex items-start justify-between gap-4 mb-6">
                            <div>
                                <p class="text-xs font-bold text-orange-600 uppercase tracking-wider">竞技答题舱安全准入</p>
                                <h2 class="text-2xl font-black text-slate-900 mt-2">确定进入竞技答题舱对决？</h2>
                                <p class="text-sm text-slate-600 mt-2">匹配对手：计算机学院 · 苏晚晴 (钻石段位)　|　挑战题目：Cache 组相联命中模拟</p>
                            </div>
                            <div class="w-14 h-14 rounded-2xl bg-orange-50 text-orange-600 flex items-center justify-center shrink-0 shadow-sm">
                                <i class="ph ph-shield-warning text-3xl"></i>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="rounded-2xl bg-orange-50/40 border border-orange-100/50 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-orange-600 shadow-sm flex items-center justify-center shrink-0">
                                    <i class="ph ph-corners-out text-lg"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-950">全屏沉浸对决</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1">系统将请求进入浏览器全屏，未进入全屏无法开始计时答题。</p>
                                </div>
                            </div>
                            <div class="rounded-2xl bg-orange-50/40 border border-orange-100/50 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-orange-600 shadow-sm flex items-center justify-center shrink-0">
                                    <i class="ph ph-arrows-out-cardinal text-lg"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-950">严禁切屏与失焦</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1">切屏、隐藏网页、窗口失焦达3次或超过10秒将自动判定为负。</p>
                                </div>
                            </div>
                            <div class="rounded-2xl bg-orange-50/40 border border-orange-100/50 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-orange-600 shadow-sm flex items-center justify-center shrink-0">
                                    <i class="ph ph-copy-simple text-lg"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-950">限制复制粘贴</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1">竞技期间全局拦截复制、粘贴、剪切操作及浏览器右键菜单。</p>
                                </div>
                            </div>
                            <div class="rounded-2xl bg-orange-50/40 border border-orange-100/50 px-4 py-4 flex gap-3">
                                <div class="w-9 h-9 rounded-full bg-white text-orange-600 shadow-sm flex items-center justify-center shrink-0">
                                    <i class="ph ph-clock text-lg"></i>
                                </div>
                                <div>
                                    <p class="text-sm font-bold text-slate-950">限时挑战 30 分钟</p>
                                    <p class="text-xs text-slate-500 leading-relaxed mt-1">倒计时结束将强制自动提交，通过用例较多或耗时较短者获胜。</p>
                                </div>
                            </div>
                        </div>

                        <div class="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-xs text-amber-800 leading-relaxed flex items-start gap-3">
                            <i class="ph ph-warning-circle text-lg shrink-0 mt-0.5 text-amber-600"></i>
                            <div>
                                点击“确认进入”后，系统将请求全屏。竞技过程中若遭遇 <b>强退、逃跑或作弊判定</b>，将扣除 100 荣誉积分，并立即中断当前的 <b>{{ rankedPlayer.streak }} 连胜</b>。
                            </div>
                        </div>

                        <div class="mt-8 flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
                            <button @click="cancelRankedEntry" class="h-12 px-6 rounded-xl border border-slate-200 bg-white text-sm font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors">
                                取消，返回大厅
                            </button>
                            <button @click="confirmRankedEntry" class="h-12 px-6 rounded-xl bg-gradient-to-r from-orange-500 to-red-600 text-white text-sm font-bold shadow-lg shadow-orange-500/20 hover:brightness-110 flex items-center justify-center gap-2 transition-all active:scale-95">
                                <i class="ph ph-corners-out text-lg"></i>
                                确认，进入全屏竞技
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 强退确认弹窗 -->
            <div v-if="isRankedExitConfirmOpen" class="fixed inset-0 z-[10002] flex items-center justify-center bg-slate-950/60 px-4 backdrop-blur-sm">
                <div class="w-full max-w-md rounded-3xl bg-white shadow-2xl overflow-hidden p-6 sm:p-8 border border-red-100" role="dialog" aria-modal="true">
                    <div class="flex items-center justify-center w-16 h-16 rounded-2xl bg-red-50 text-red-600 mb-6 mx-auto shadow-inner">
                        <i class="ph ph-warning text-3xl animate-bounce"></i>
                    </div>
                    <h2 class="text-xl font-black text-slate-900 text-center">中途退赛警告！</h2>
                    <p class="text-sm text-slate-600 text-center mt-3 leading-relaxed">
                        强行退出答题舱将被视为<span class="font-bold text-red-600">逃跑认输</span>，系统将<span class="font-bold text-red-600">扣除 100 积分</span>并中断您的连胜纪录。确认退出？
                    </p>
                    <div class="mt-8 flex flex-col sm:flex-row justify-center gap-3">
                        <button @click="isRankedExitConfirmOpen = false" class="h-12 px-6 rounded-xl border border-slate-200 bg-white text-sm font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-all flex-1">
                            取消，继续答题
                        </button>
                        <button @click="isRankedExitConfirmOpen = false; resolveRankedMatch('cheat_lose', '中途退出对局')" class="h-12 px-6 rounded-xl bg-gradient-to-r from-red-600 to-rose-700 text-white text-sm font-bold hover:brightness-110 transition-all active:scale-95 flex-1">
                            确认退赛
                        </button>
                    </div>
                </div>
            </div>

            </teleport>

            <!-- ==================== 5. 舱室 3: 团队协作实训 (Collab Studio) ==================== -->
            <div v-else-if="codingMode === 'collab'" class="w-full h-full flex flex-col overflow-hidden relative">
                <div class="flex flex-wrap items-center justify-between gap-3 mb-3 w-full border-b border-slate-200 pb-2 shrink-0 select-none">
                    <button @click="goBackToLobby" class="min-h-[40px] text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1.5 font-semibold transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-500">
                        <i class="ph ph-arrow-left"></i> 返回实战大厅
                    </button>
                    <div class="flex items-center gap-2">
                        <button @click="refreshCollabStatus('push')" :disabled="!!collabActionLoading" class="min-h-[40px] px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50 disabled:opacity-50 flex items-center gap-1.5">
                            <i class="ph ph-arrows-clockwise" :class="collabActionLoading.startsWith('refresh') ? 'animate-spin' : ''"></i> 刷新状态
                        </button>
                    </div>
                    <div class="text-right">
                        <span class="text-[10px] text-slate-400 uppercase tracking-widest font-mono">GIT COLLABORATION LOOP</span>
                        <h3 class="text-xs font-bold text-slate-700">团队协作实训 Git 闭环</h3>
                    </div>
                </div>

                <div v-if="collabViewMode === 'list'" class="flex-1 min-h-0 overflow-y-auto no-scrollbar">
                    <div class="grid grid-cols-1 2xl:grid-cols-[minmax(0,1fr)_360px] gap-5">
                        <section class="glass-panel-liquid p-5 min-w-0">
                            <div class="flex flex-wrap items-start justify-between gap-3 mb-5">
                                <div>
                                    <p class="text-[10px] font-bold text-teal-600 uppercase tracking-[0.18em]">Team repositories</p>
                                    <h3 class="text-xl font-serif font-bold text-slate-900 mt-1">我的团队仓库</h3>
                                    <p class="text-xs text-slate-500 mt-1">每个团队仓库都可以进入管理主页面或系统内仓库主页。</p>
                                </div>
                                <div class="flex flex-wrap gap-2">
                                    <button @click="loadCollabProjects" :disabled="collabLoading" class="min-h-[40px] px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50 disabled:opacity-50 flex items-center gap-1.5">
                                        <i class="ph ph-arrows-clockwise" :class="collabLoading ? 'animate-spin' : ''"></i> 刷新列表
                                    </button>
                                    <button @click="collabCreateOpen = !collabCreateOpen" class="min-h-[40px] px-4 rounded-xl bg-teal-600 text-white text-xs font-bold hover:bg-teal-700 flex items-center gap-1.5">
                                        <i class="ph ph-plus-circle"></i> 创建团队仓库
                                    </button>
                                </div>
                            </div>

                            <div v-if="collabLoading" class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                                <div v-for="i in 2" :key="i" class="rounded-xl bg-white/70 border border-white p-5 animate-pulse">
                                    <div class="h-4 w-32 bg-slate-200 rounded mb-4"></div>
                                    <div class="h-16 bg-slate-100 rounded-xl mb-4"></div>
                                    <div class="grid grid-cols-2 gap-3">
                                        <div class="h-12 bg-slate-100 rounded-xl"></div>
                                        <div class="h-12 bg-slate-100 rounded-xl"></div>
                                    </div>
                                </div>
                            </div>
                            <div v-else-if="collabProjects.length === 0" class="rounded-xl bg-white/70 border border-white p-8 text-center">
                                <h4 class="text-sm font-bold text-slate-800">暂无团队仓库</h4>
                                <p class="text-xs text-slate-500 mt-2">队长可以从右侧创建团队仓库，创建者会自动成为队长。</p>
                            </div>
                            <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                                <article v-for="project in collabProjects" :key="project.id" class="rounded-xl bg-white/75 border border-white p-5 min-w-0 shadow-sm">
                                    <div class="flex items-start justify-between gap-3">
                                        <div class="min-w-0">
                                            <p class="text-[10px] font-bold text-teal-600 uppercase tracking-[0.16em]">科目类别</p>
                                            <h4 class="text-base font-extrabold text-slate-900 mt-1 truncate">{{ project.repositoryCard.subjectCategory }}</h4>
                                        </div>
                                        <span class="shrink-0 text-[10px] font-bold px-2 py-1 rounded-full border" :class="repoStatusClass(project.repository.status)">{{ project.repositoryCard.repositoryStatus }}</span>
                                    </div>
                                    <div class="mt-4">
                                        <p class="text-[10px] font-bold text-slate-400">项目仓库名</p>
                                        <p class="mt-1 text-lg font-extrabold text-slate-900 truncate">{{ project.repositoryCard.repoName }}</p>
                                        <p class="mt-2 text-[10px] font-bold text-slate-400">项目介绍</p>
                                        <p class="mt-1 text-xs text-slate-500 leading-relaxed line-clamp-2">{{ project.repositoryCard.description }}</p>
                                    </div>
                                    <dl class="mt-4 grid grid-cols-2 gap-3 text-xs">
                                        <div class="rounded-xl bg-slate-50 border border-slate-100 p-3 min-w-0">
                                            <dt class="text-[10px] text-slate-400 font-bold">队长</dt>
                                            <dd class="mt-1 font-bold text-slate-800 truncate">{{ project.repositoryCard.leader }}</dd>
                                        </div>
                                        <div class="rounded-xl bg-slate-50 border border-slate-100 p-3 min-w-0">
                                            <dt class="text-[10px] text-slate-400 font-bold">队员</dt>
                                            <dd class="mt-1 text-slate-700 truncate">{{ project.repositoryCard.members.join('、') }}</dd>
                                        </div>
                                        <div class="rounded-xl bg-slate-50 border border-slate-100 p-3 min-w-0">
                                            <dt class="text-[10px] text-slate-400 font-bold">仓库状态</dt>
                                            <dd class="mt-1 font-bold text-slate-800 truncate">{{ project.repositoryCard.repositoryStatus }}</dd>
                                        </div>
                                        <div class="rounded-xl bg-slate-50 border border-slate-100 p-3 min-w-0">
                                            <dt class="text-[10px] text-slate-400 font-bold">最近更新时间</dt>
                                            <dd class="mt-1 font-mono text-slate-600 truncate">{{ formatDisplayDateTime(project.repositoryCard.updatedAt) }}</dd>
                                        </div>
                                    </dl>
                                    <div class="mt-4 flex items-center justify-between gap-3">
                                        <span class="text-[10px] font-bold px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100">PR 状态：{{ project.repositoryCard.prStatus }}</span>
                                        <div class="flex gap-2 shrink-0">
                                            <button @click="openCollabManagement(project)" class="min-h-[36px] px-3 rounded-lg bg-slate-900 text-white text-[11px] font-bold hover:bg-slate-800">管理主页面</button>
                                            <button @click="openCollabRepositoryHome(project)" class="min-h-[36px] px-3 rounded-lg bg-white border border-slate-200 text-slate-700 text-[11px] font-bold hover:bg-slate-50">仓库主页</button>
                                            <button v-if="canManageCollabProject(project)" @click="deleteCollabProject(project)" :disabled="!!collabActionLoading" class="min-h-[36px] px-3 rounded-lg bg-rose-50 border border-rose-100 text-rose-600 text-[11px] font-bold hover:bg-rose-100 disabled:opacity-50">删除</button>
                                        </div>
                                    </div>
                                </article>
                            </div>
                        </section>

                        <aside v-if="collabCreateOpen" class="glass-panel-liquid p-5 h-fit">
                            <div class="flex items-center justify-between mb-4">
                                <div>
                                    <p class="text-[10px] font-bold text-teal-600 uppercase tracking-[0.16em]">Create repository</p>
                                    <h4 class="text-base font-serif font-bold text-slate-900 mt-1">创建团队仓库</h4>
                                </div>
                                <button @click="collabCreateOpen = false" class="w-8 h-8 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-slate-900"><i class="ph ph-x"></i></button>
                            </div>
                            <form @submit.prevent="createCollabProject" class="grid grid-cols-1 gap-3">
                                <label class="grid gap-1 text-[10px] font-bold text-slate-500">科目类别<input v-model="collabCreateForm.course" class="liquid-glass-input px-3 py-2 text-xs outline-none font-normal text-slate-800"></label>
                                <label class="grid gap-1 text-[10px] font-bold text-slate-500">项目仓库名<input v-model="collabCreateForm.repoName" class="liquid-glass-input px-3 py-2 text-xs outline-none font-normal text-slate-800"></label>
                                <label class="grid gap-1 text-[10px] font-bold text-slate-500">团队名称<input v-model="collabCreateForm.teamName" class="liquid-glass-input px-3 py-2 text-xs outline-none font-normal text-slate-800"></label>
                                <label class="grid gap-1 text-[10px] font-bold text-slate-500">项目名称<input v-model="collabCreateForm.title" class="liquid-glass-input px-3 py-2 text-xs outline-none font-normal text-slate-800"></label>
                                <label class="grid gap-1 text-[10px] font-bold text-slate-500">项目介绍<textarea v-model="collabCreateForm.description" rows="3" class="liquid-glass-input px-3 py-2 text-xs outline-none resize-none font-normal text-slate-800"></textarea></label>
                                <label class="grid gap-1 text-[10px] font-bold text-slate-500">搜索输入学号
                                    <div class="flex gap-2">
                                        <input v-model="collabMemberKeyword" @keyup.enter.prevent="searchCollabMembers" class="liquid-glass-input px-3 py-2 text-xs outline-none font-normal text-slate-800 min-w-0 flex-1" placeholder="20230004">
                                        <button type="button" @click="searchCollabMembers" class="min-h-[36px] px-3 rounded-lg bg-white border border-slate-200 text-slate-700 text-[11px] font-bold">搜索</button>
                                    </div>
                                </label>
                                <div v-if="collabMemberSearchResults.length" class="grid gap-2">
                                    <button v-for="member in collabMemberSearchResults" :key="member.studentId || member.username" type="button" @click="addCollabMember(member)" class="text-left rounded-lg bg-white border border-slate-100 px-3 py-2 hover:bg-slate-50">
                                        <span class="block text-xs font-bold text-slate-800">{{ member.name }} · {{ member.studentId }}</span>
                                        <span class="block text-[10px] text-slate-400">{{ member.className }} · {{ member.source === 'mock' ? '演示名单' : '用户表' }}</span>
                                    </button>
                                </div>
                                <label class="grid gap-1 text-[10px] font-bold text-slate-500">队员<input v-model="collabCreateForm.members" class="liquid-glass-input px-3 py-2 text-xs outline-none font-normal text-slate-800"></label>
                                <div v-if="collabSelectedMembers.length" class="flex flex-wrap gap-2">
                                    <button v-for="member in collabSelectedMembers" :key="member.studentId || member.name" type="button" @click="removeCollabMember(member)" class="px-2 py-1 rounded-full bg-teal-50 border border-teal-100 text-[10px] font-bold text-teal-700">{{ member.name }} ×</button>
                                </div>
                                <button type="submit" :disabled="!!collabActionLoading" class="min-h-[40px] rounded-xl bg-teal-600 text-white text-xs font-bold hover:bg-teal-700 disabled:opacity-50">创建团队仓库</button>
                            </form>
                        </aside>
                    </div>
                </div>

                <div v-else-if="collabViewMode === 'home'" class="flex-1 min-h-0 overflow-y-auto no-scrollbar">
                    <div v-if="collabLoading" class="glass-panel-liquid p-8 animate-pulse">
                        <div class="h-5 w-48 bg-slate-200 rounded mb-5"></div>
                        <div class="h-64 bg-slate-100 rounded-xl"></div>
                    </div>
                    <div v-else class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                        <div class="px-5 py-3 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50">
                            <button @click="backToCollabRepositoryList" class="min-h-[36px] px-3 rounded-lg bg-white border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 flex items-center gap-1.5">
                                <i class="ph ph-arrow-left"></i> 返回仓库列表
                            </button>
                            <div class="flex items-center gap-4 text-xs font-bold text-slate-600">
                                <button
                                    v-for="tab in repositoryHomeTabs"
                                    :key="tab.id"
                                    type="button"
                                    @click="selectRepositoryHomeTab(tab.id)"
                                    class="py-2 border-b-2 transition-colors flex items-center gap-1.5"
                                    :class="repositoryHomeTab === tab.id ? 'text-slate-900 border-rose-500' : 'border-transparent hover:text-slate-900'"
                                >
                                    <i :class="['ph', tab.icon]"></i>
                                    <span>{{ tab.label }}</span>
                                    <span v-if="tab.id === 'pulls' && repositoryHomeOpenPrCount" class="min-w-[18px] h-[18px] px-1 rounded-full bg-rose-50 text-rose-600 text-[10px] flex items-center justify-center">{{ repositoryHomeOpenPrCount }}</span>
                                </button>
                            </div>
                        </div>
                        <div class="max-w-6xl mx-auto px-5 py-5">
                            <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-5">
                                <div class="min-w-0">
                                    <p class="text-xs text-slate-500"><span class="font-bold text-slate-700">{{ repositoryHomeInfo.namespace || 'campus' }}</span> /</p>
                                    <h2 class="text-2xl font-extrabold text-slate-900 truncate">{{ repositoryHomeInfo.repoName }}</h2>
                                    <p class="text-sm text-slate-500 mt-1">{{ repositoryHomeProject.title }} · {{ repositoryHomeInfo.course }}</p>
                                </div>
                                <span class="px-2 py-1 rounded-full border border-slate-200 text-xs font-bold text-slate-600">{{ repositoryHomeInfo.visibility || 'private' }}</span>
                            </div>
                            <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-6 mt-5">
                                <main class="min-w-0">
                                    <div v-if="repositoryHomeTab === 'code'" class="bg-slate-900 rounded-xl p-4 mb-5">
                                        <div class="flex items-center justify-between gap-3 mb-3">
                                            <span class="text-xs font-extrabold text-white tracking-wide">Clone</span>
                                            <div class="flex gap-1 bg-white/5 rounded-lg p-0.5">
                                                <button type="button" @click="teamCloneMode = 'token'" class="text-[10px] font-bold px-2.5 py-1 rounded-lg transition-all"
                                                    :class="teamCloneMode === 'token' ? 'bg-white/25 text-white' : 'bg-white/5 text-slate-300 hover:bg-white/10'">
                                                    HTTPS + Token
                                                </button>
                                                <button type="button" @click="teamCloneMode = 'https'" class="text-[10px] font-bold px-2.5 py-1 rounded-lg transition-all"
                                                    :class="teamCloneMode === 'https' ? 'bg-white/25 text-white' : 'bg-white/5 text-slate-300 hover:bg-white/10'">
                                                    HTTPS
                                                </button>
                                            </div>
                                        </div>
                                        <div v-if="teamCloneMode === 'token'">
                                            <div v-if="teamAuthenticatedCloneUrl" class="flex items-center gap-2">
                                                <code class="flex-1 font-mono text-xs overflow-x-auto select-text text-emerald-200 whitespace-nowrap bg-slate-950/50 rounded-lg p-2">git clone {{ teamAuthenticatedCloneUrl }}</code>
                                                <button type="button" @click="copyTeamAuthClone" class="text-[10px] font-bold px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 transition-all flex items-center gap-1 shrink-0 text-white">
                                                    <i :class="copiedTeamAuthClone ? 'ph ph-check' : 'ph ph-copy'"></i> {{ copiedTeamAuthClone ? '已复制' : '复制' }}
                                                </button>
                                            </div>
                                            <div v-else class="flex items-center justify-between gap-3">
                                                <p class="text-[11px] text-slate-200 leading-relaxed">生成 Token 后可获取可直接粘贴的 Clone 命令。</p>
                                                <button type="button" @click="handleTeamRotateGiteaToken" :disabled="!!teamIdentityLoading" class="text-[10px] font-bold px-3 py-1.5 rounded-lg bg-emerald-500/80 hover:bg-emerald-500 text-white transition-all flex items-center gap-1 shrink-0 disabled:opacity-50">
                                                    <i class="ph ph-key"></i> 生成 Token
                                                </button>
                                            </div>
                                        </div>
                                        <div v-else class="flex items-center gap-2">
                                            <code class="flex-1 font-mono text-xs overflow-x-auto select-text text-slate-100 whitespace-nowrap bg-slate-950/50 rounded-lg p-2">{{ repositoryHomeInfo.cloneUrl || repositoryHomeRepo.cloneUrl || '—' }}</code>
                                            <button type="button" @click="copyGitCommand(repositoryHomeInfo.cloneUrl || repositoryHomeRepo.cloneUrl)" class="text-[10px] font-bold px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 transition-all flex items-center gap-1 shrink-0 text-white">
                                                <i class="ph ph-copy"></i> 复制
                                            </button>
                                        </div>
                                    </div>
                                    <div v-if="repositoryHomeTab === 'code'" class="border border-slate-200 rounded-xl">
                                        <div class="px-4 py-3 bg-slate-50 border-b border-slate-200 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                                            <div class="flex items-center gap-3 flex-wrap">
                                                <div class="relative">
                                                    <button
                                                        type="button"
                                                        @click="toggleBranchDropdown"
                                                        class="inline-flex items-center gap-2 bg-white border border-slate-300 rounded-lg pl-3 pr-3 py-2 shadow-sm hover:border-indigo-400 hover:shadow transition-all text-sm font-bold text-slate-800"
                                                    >
                                                        <i class="ph ph-git-branch text-indigo-500"></i>
                                                        <span>{{ teamRepoSelectedBranch || 'main' }}</span>
                                                        <span v-if="teamRepoBranches.find(b => b.name === teamRepoSelectedBranch)?.default" class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 font-medium">默认</span>
                                                        <i :class="teamBranchDropdownOpen ? 'ph ph-caret-up' : 'ph ph-caret-down'" class="text-slate-400 text-xs ml-0.5"></i>
                                                    </button>
                                                    <div
                                                        v-if="teamBranchDropdownOpen"
                                                        @click="closeBranchDropdown"
                                                        class="fixed inset-0 z-40"
                                                    ></div>
                                                    <div
                                                        v-if="teamBranchDropdownOpen"
                                                        class="absolute top-full left-0 mt-1.5 w-64 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden"
                                                    >
                                                        <div class="px-3 py-2 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">切换分支</div>
                                                        <div class="max-h-64 overflow-y-auto">
                                                            <button
                                                                v-for="b in teamRepoBranches"
                                                                :key="b.name"
                                                                type="button"
                                                                @click="switchTeamBranch(b.name)"
                                                                class="w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors"
                                                                :class="b.name === teamRepoSelectedBranch ? 'bg-indigo-50' : 'hover:bg-slate-50'"
                                                            >
                                                                <i :class="b.name === teamRepoSelectedBranch ? 'ph ph-check text-indigo-500' : 'ph ph-git-branch text-slate-300'" class="text-sm shrink-0"></i>
                                                                <span class="text-sm font-bold flex-1" :class="b.name === teamRepoSelectedBranch ? 'text-indigo-700' : 'text-slate-700'">{{ b.name }}</span>
                                                                <span v-if="b.default" class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 font-medium shrink-0">默认</span>
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                                <p class="text-[11px] text-slate-500">实时读取 Gitea 仓库目录，点击文件夹进入、点击文件预览。</p>
                                            </div>
                                            <div class="flex flex-wrap items-center gap-1.5 text-[10px]">
                                                <button
                                                    v-for="crumb in teamRepoBreadcrumbs"
                                                    :key="crumb.path || 'root'"
                                                    @click="loadTeamRepoBrowser(crumb.path)"
                                                    class="px-2 py-1 rounded-lg border transition-all"
                                                    :class="crumb.path === teamRepoBrowserPath ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'"
                                                >
                                                    {{ crumb.label }}
                                                </button>
                                            </div>
                                        </div>

                                        <div v-if="teamRepoBrowserLoading" class="px-4 py-8 text-center text-xs text-slate-400">正在同步 Gitea 文件目录...</div>
                                        <div v-else-if="teamRepoBrowserError" class="px-4 py-6 text-center text-xs text-rose-500">{{ teamRepoBrowserError }}</div>
                                        <div v-else-if="teamRepoBrowserEntries.length === 0" class="px-4 py-6 text-center text-xs text-slate-400">当前目录为空，等待首次 push 后刷新。</div>
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
                                                        v-for="entry in teamRepoBrowserEntries"
                                                        :key="entry.path || entry.name"
                                                        @click="openTeamRepoEntry(entry)"
                                                        class="border-t border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                                                    >
                                                        <td class="px-4 py-2.5 font-medium text-slate-800">
                                                            <span class="inline-flex items-center gap-2 min-w-0">
                                                                <i :class="entry.type === 'dir' ? 'ph ph-folder text-amber-500' : 'ph ph-file-text text-slate-400'"></i>
                                                                <span class="truncate">{{ entry.name }}</span>
                                                            </span>
                                                        </td>
                                                        <td class="px-4 py-2.5 text-slate-500 font-mono">{{ entry.type === 'dir' ? '目录' : formatTeamRepoFileSize(entry.size) }}</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>

                                        <div v-if="teamRepoBrowserBlob" class="border-t border-slate-200 bg-slate-950 text-slate-100">
                                            <div class="px-4 py-2 border-b border-white/10 flex items-center justify-between gap-3">
                                                <span class="text-[10px] font-bold truncate">{{ teamRepoBrowserBlob.path }}</span>
                                                <span class="text-[10px] text-slate-400 shrink-0">{{ formatTeamRepoFileSize(teamRepoBrowserBlob.size) }}</span>
                                            </div>
                                            <pre v-if="teamRepoBrowserBlob.previewable" class="px-4 py-3 text-[11px] leading-relaxed overflow-x-auto whitespace-pre-wrap">{{ teamRepoBrowserBlob.content }}</pre>
                                            <div v-else class="px-4 py-4 text-[11px] text-slate-400">该文件为二进制或体积较大，暂不支持在线预览，请 clone 后查看。</div>
                                        </div>
                                    </div>

                                    <section v-if="repositoryHomeTab === 'code'" class="mt-5 border border-slate-200 rounded-xl overflow-hidden">
                                        <h3 class="px-4 py-3 bg-slate-50 border-b border-slate-200 text-sm font-extrabold text-slate-900">README.md</h3>
                                        <pre class="p-5 text-sm leading-relaxed whitespace-pre-wrap text-slate-700 bg-white">{{ repositoryHomeInfo.readme }}</pre>
                                    </section>
                                    <section v-if="repositoryHomeTab === 'code'" class="mt-5 border border-slate-200 rounded-xl overflow-hidden">
                                        <h3 class="px-4 py-3 bg-slate-50 border-b border-slate-200 text-sm font-extrabold text-slate-900">项目类图</h3>
                                        <div class="p-5 bg-white">
                                            <div class="rounded-xl bg-slate-950 text-slate-100 p-4 font-mono text-sm whitespace-pre-wrap">{{ repositoryHomeInfo.classDiagram }}</div>
                                        </div>
                                    </section>
                                    <section v-if="repositoryHomeTab === 'pulls'" class="border border-slate-200 rounded-xl overflow-hidden">
                                        <div class="px-4 py-3 bg-slate-50 border-b border-slate-200 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                            <div>
                                                <h3 class="text-sm font-extrabold text-slate-900">Pull requests</h3>
                                                <p class="text-[10px] text-slate-400 mt-1">系统后端实时同步真实 Gitea PR，队长可在此完成审核和合并。</p>
                                            </div>
                                            <button
                                                type="button"
                                                @click="refreshRepositoryHomePullRequests({ showToast: true })"
                                                :disabled="!!collabActionLoading"
                                                class="min-h-[34px] px-3 rounded-lg bg-white border border-slate-200 text-[11px] font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50 flex items-center justify-center gap-1.5"
                                            >
                                                <i class="ph ph-arrows-clockwise"></i>
                                                同步 Gitea
                                            </button>
                                        </div>
                                        <div class="p-4 bg-white">
                                            <textarea
                                                v-if="canManageRepositoryHome"
                                                v-model="prReviewComment"
                                                rows="2"
                                                class="mb-4 w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-[11px] outline-none focus:border-teal-500 resize-none"
                                                placeholder="队长审核意见，会随要求修改或同意合并写入学习系统记录"
                                            ></textarea>
                                            <div v-if="repositoryHomePullRequests.length === 0" class="rounded-xl bg-slate-50 border border-slate-100 p-8 text-center">
                                                <i class="ph ph-git-pull-request text-2xl text-slate-300"></i>
                                                <p class="mt-2 text-xs font-bold text-slate-500">暂无 Pull Request</p>
                                                <p class="mt-1 text-[10px] text-slate-400">队员 push 新分支后，可在 Gitea 创建 PR；Webhook 和同步会把记录带回这里。</p>
                                            </div>
                                            <div v-else class="grid gap-3">
                                                <article v-for="pr in repositoryHomePullRequests" :key="pr.id || pr.number" class="rounded-xl border border-slate-200 bg-white p-4">
                                                    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                                        <div class="min-w-0">
                                                            <div class="flex flex-wrap items-center gap-2">
                                                                <span class="text-xs font-extrabold text-slate-900">#{{ pr.number }}</span>
                                                                <span class="text-[10px] px-2 py-0.5 rounded-full border font-bold" :class="prStatusClass(pr.status)">{{ pr.statusLabel || pr.status }}</span>
                                                                <span v-if="pr.source === 'gitea' || pr.source === 'gitea_webhook'" class="text-[10px] px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-100 font-bold">Gitea</span>
                                                            </div>
                                                            <h4 class="mt-2 text-sm font-extrabold text-slate-900 break-words">{{ pr.title }}</h4>
                                                            <p class="mt-1 text-[11px] text-slate-500">
                                                                {{ pr.creator || 'unknown' }} ·
                                                                <span class="font-mono">{{ pr.sourceBranch || '-' }}</span>
                                                                <i class="ph ph-arrow-right mx-1"></i>
                                                                <span class="font-mono">{{ pr.targetBranch || repositoryHomeInfo.defaultBranch || 'main' }}</span>
                                                            </p>
                                                            <p class="mt-1 text-[10px] text-slate-400">更新：{{ formatDisplayDateTime(pr.updatedAt) }}</p>
                                                        </div>
                                                    </div>
                                                    <div v-if="canManageRepositoryHome && pr.status === 'open'" class="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
                                                        <button
                                                            type="button"
                                                            @click="reviewCollabPr(pr, 'request_changes')"
                                                            :disabled="!!collabActionLoading"
                                                            class="min-h-[34px] px-3 rounded-lg bg-white border border-slate-200 text-[10px] font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                                                        >
                                                            要求修改
                                                        </button>
                                                        <button
                                                            type="button"
                                                            @click="reviewCollabPr(pr, 'approve_merge')"
                                                            :disabled="!!collabActionLoading"
                                                            class="min-h-[34px] px-3 rounded-lg bg-teal-600 text-white text-[10px] font-bold hover:bg-teal-700 disabled:opacity-50"
                                                        >
                                                            同意合并
                                                        </button>
                                                    </div>
                                                    <p v-if="pr.reviewComment" class="mt-3 text-[10px] text-slate-500 leading-relaxed bg-slate-50 border border-slate-100 rounded-lg px-2 py-1.5">
                                                        审核意见：{{ pr.reviewComment }}
                                                    </p>
                                                </article>
                                            </div>
                                        </div>
                                    </section>
                                    <section v-if="repositoryHomeTab === 'insights'" class="border border-slate-200 rounded-xl overflow-hidden">
                                        <div class="px-4 py-3 bg-slate-50 border-b border-slate-200">
                                            <h3 class="text-sm font-extrabold text-slate-900">Repository insights</h3>
                                            <p class="text-[10px] text-slate-400 mt-1">基于学习系统同步后的 Gitea 提交、PR 和成员进度生成。</p>
                                        </div>
                                        <div class="p-4 bg-white grid grid-cols-2 md:grid-cols-4 gap-3">
                                            <div class="rounded-xl border border-slate-100 bg-slate-50 p-3">
                                                <p class="text-[10px] text-slate-400 font-bold">Open PR</p>
                                                <p class="mt-1 text-xl font-extrabold text-slate-900">{{ repositoryHomeOpenPrCount }}</p>
                                            </div>
                                            <div class="rounded-xl border border-slate-100 bg-slate-50 p-3">
                                                <p class="text-[10px] text-slate-400 font-bold">Merged PR</p>
                                                <p class="mt-1 text-xl font-extrabold text-teal-700">{{ repositoryHomeMergedPrCount }}</p>
                                            </div>
                                            <div class="rounded-xl border border-slate-100 bg-slate-50 p-3">
                                                <p class="text-[10px] text-slate-400 font-bold">Members</p>
                                                <p class="mt-1 text-xl font-extrabold text-slate-900">{{ repositoryHomeInfo.teamSummary?.totalMembers || repositoryHome?.teamSummary?.totalMembers || 0 }}</p>
                                            </div>
                                            <div class="rounded-xl border border-slate-100 bg-slate-50 p-3">
                                                <p class="text-[10px] text-slate-400 font-bold">Progress</p>
                                                <p class="mt-1 text-xl font-extrabold text-blue-700">{{ repositoryHome?.teamSummary?.averageProgress || teamSummary.averageProgress || 0 }}%</p>
                                            </div>
                                        </div>
                                    </section>
                                </main>
                                <aside class="space-y-5">
                                    <section class="border border-slate-200 rounded-xl p-4">
                                        <h3 class="text-sm font-extrabold text-slate-900">About</h3>
                                        <p class="mt-2 text-sm text-slate-600 leading-relaxed">{{ repositoryHomeInfo.about }}</p>
                                        <div class="mt-4 grid gap-2 text-xs text-slate-500">
                                            <span><i class="ph ph-users-three mr-1"></i>{{ repositoryHomeInfo.teamSummary?.totalMembers || repositoryHome?.teamSummary?.totalMembers || 0 }} contributors</span>
                                            <span v-if="repositoryHomeInfo.cloneUrlMockOnly"><i class="ph ph-lock-key mr-1"></i>演示 clone 地址，暂未接入真实 Gitea</span>
                                            <span v-else-if="repositoryHomeInfo.cloneUrl || repositoryHomeRepo.cloneUrl"><i class="ph ph-git-branch mr-1"></i>{{ repositoryHomeInfo.cloneUrl || repositoryHomeRepo.cloneUrl }}</span>
                                        </div>
                                    </section>
                                    <section class="border border-slate-200 rounded-xl p-4">
                                        <h3 class="text-sm font-extrabold text-slate-900">Languages</h3>
                                        <div v-if="(teamRepoBrowserLanguages.length ? teamRepoBrowserLanguages : repositoryHomeLanguages).length" class="mt-3 h-2 rounded-full overflow-hidden flex bg-slate-100">
                                            <span
                                                v-for="lang in (teamRepoBrowserLanguages.length ? teamRepoBrowserLanguages : repositoryHomeLanguages)"
                                                :key="lang.name"
                                                class="h-full"
                                                :style="{ width: lang.percent + '%', backgroundColor: lang.color || '#64748b' }"
                                            ></span>
                                        </div>
                                        <div class="mt-3 grid gap-1">
                                            <div
                                                v-for="lang in (teamRepoBrowserLanguages.length ? teamRepoBrowserLanguages : repositoryHomeLanguages)"
                                                :key="lang.name"
                                                class="flex items-center justify-between text-xs"
                                            >
                                                <span class="font-bold text-slate-700">{{ lang.name }}</span>
                                                <span class="text-slate-400">{{ lang.percent }}%</span>
                                            </div>
                                        </div>
                                        <p v-if="!(teamRepoBrowserLanguages.length || repositoryHomeLanguages.length)" class="mt-2 text-xs text-slate-400">等待 Gitea 同步语言统计。</p>
                                    </section>
                                    <section class="border border-slate-200 rounded-xl p-4">
                                        <h3 class="text-sm font-extrabold text-slate-900">教师评语</h3>
                                        <p class="mt-2 text-sm text-slate-600 leading-relaxed">{{ repositoryHomeInfo.teacherComment || '暂无评语' }}</p>
                                        <h3 class="text-sm font-extrabold text-slate-900 mt-4">修改建议</h3>
                                        <p class="mt-2 text-sm text-slate-600 leading-relaxed">{{ repositoryHomeInfo.revisionSuggestions || '暂无修改建议' }}</p>
                                        <p v-if="repositoryHomeInfo.teacherFeedbackUpdatedAt" class="mt-3 text-[10px] text-slate-400">更新：{{ repositoryHomeInfo.teacherFeedbackUpdatedBy }} · {{ formatDisplayDateTime(repositoryHomeInfo.teacherFeedbackUpdatedAt) }}</p>
                                    </section>
                                </aside>
                            </div>
                        </div>
                    </div>
                </div>

                <div v-else-if="collabLoading" class="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[280px_minmax(0,1fr)_340px] gap-5 overflow-hidden">
                    <div v-for="i in 3" :key="i" class="glass-panel-liquid p-5 animate-pulse">
                        <div class="h-4 w-32 bg-slate-200 rounded mb-4"></div>
                        <div class="space-y-3">
                            <div class="h-20 bg-slate-100 rounded-xl"></div>
                            <div class="h-20 bg-slate-100 rounded-xl"></div>
                            <div class="h-20 bg-slate-100 rounded-xl"></div>
                        </div>
                    </div>
                </div>

                <div v-else-if="collabError" class="m-auto max-w-lg glass-panel-liquid p-8 text-center">
                    <div class="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center text-2xl mx-auto mb-4">
                        <i class="ph ph-warning"></i>
                    </div>
                    <h4 class="text-base font-bold text-slate-800 mb-2">团队 Git 数据暂不可用</h4>
                    <p class="text-sm text-slate-500 leading-relaxed mb-5">{{ collabError }}</p>
                    <button @click="loadCollabProject" class="min-h-[40px] px-5 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800">重试加载</button>
                </div>

                <div v-else-if="!collabData" class="m-auto max-w-lg glass-panel-liquid p-8 text-center">
                    <h4 class="text-base font-bold text-slate-800 mb-2">暂无团队协作项目</h4>
                    <p class="text-sm text-slate-500 mb-5">队长可以先创建项目并写项目介绍，再分配成员任务、创建仓库和推进 PR 流程。</p>
                    <div class="flex flex-col sm:flex-row justify-center gap-2">
                        <button @click="collabCreateOpen = true" class="min-h-[40px] px-5 rounded-xl bg-teal-600 text-white text-xs font-bold hover:bg-teal-700">队长创建项目</button>
                        <button @click="loadCollabProject" class="min-h-[40px] px-5 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50">加载演示项目</button>
                    </div>
                    <form v-if="collabCreateOpen" @submit.prevent="createCollabProject" class="mt-5 text-left grid grid-cols-1 gap-3">
                        <input v-model="collabCreateForm.title" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="项目名称">
                        <input v-model="collabCreateForm.teamName" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="团队名称">
                        <textarea v-model="collabCreateForm.description" rows="3" class="liquid-glass-input px-4 py-3 text-xs outline-none resize-none" placeholder="项目介绍"></textarea>
                        <input v-model="collabCreateForm.members" class="liquid-glass-input px-4 py-2.5 text-xs outline-none" placeholder="成员，用逗号分隔">
                        <button type="submit" :disabled="!!collabActionLoading" class="min-h-[40px] px-5 rounded-xl bg-teal-600 text-white text-xs font-bold hover:bg-teal-700 disabled:opacity-50">创建并进入项目</button>
                    </form>
                </div>

                <div v-else class="flex-1 min-h-0 flex flex-col xl:grid xl:grid-cols-[280px_minmax(0,1fr)_340px] gap-5 overflow-y-auto xl:overflow-hidden pr-1 xl:pr-0">
                    <aside class="flex flex-col gap-4 overflow-visible xl:overflow-y-auto no-scrollbar h-auto xl:h-full min-h-0 shrink-0">
                        <section class="glass-panel-liquid team-profile-panel p-5 shrink-0">
                            <div class="flex items-start justify-between gap-3 mb-4">
                                <div class="min-w-0">
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider block">TEAM PROFILE</span>
                                    <h4 class="text-base font-extrabold text-slate-800 mt-1 truncate">{{ collabProject.teamName }}</h4>
                                    <p class="text-xs text-slate-500 mt-1 leading-relaxed">{{ collabProject.title }}</p>
                                    <p class="text-[11px] text-slate-400 mt-1 leading-relaxed line-clamp-2">{{ collabProject.description }}</p>
                                    <p v-if="repositoryInfo.lastSyncedAt" class="text-[10px] text-slate-400 mt-2">上次 Gitea 同步：{{ repositoryInfo.lastSyncedAt }}</p>
                                    <p v-if="repositoryInfo.syncError" class="text-[10px] text-rose-600 mt-1">{{ repositoryInfo.syncError }}</p>
                                </div>
                                <span class="shrink-0 text-[10px] px-2 py-1 rounded-full border font-bold" :class="repoStatusClass(repositoryInfo.status)">{{ repositoryInfo.statusLabel }}</span>
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <div class="bg-white/70 border border-white rounded-xl p-3">
                                    <p class="text-[10px] text-slate-400 font-semibold">已完成</p>
                                    <p class="text-lg font-extrabold text-slate-900">{{ teamSummary.completedMembers || 0 }}/{{ teamSummary.totalMembers || 0 }}</p>
                                </div>
                                <div class="bg-white/70 border border-white rounded-xl p-3">
                                    <p class="text-[10px] text-slate-400 font-semibold">平均进度</p>
                                    <p class="text-lg font-extrabold text-teal-700">{{ teamSummary.averageProgress || 0 }}%</p>
                                </div>
                                <div class="bg-white/70 border border-white rounded-xl p-3">
                                    <p class="text-[10px] text-slate-400 font-semibold">已 Push</p>
                                    <p class="text-lg font-extrabold text-slate-900">{{ teamSummary.pushedMembers || 0 }}</p>
                                </div>
                                <div class="bg-white/70 border border-white rounded-xl p-3">
                                    <p class="text-[10px] text-slate-400 font-semibold">待审 PR</p>
                                    <p class="text-lg font-extrabold text-blue-700">{{ teamSummary.openPullRequests || 0 }}</p>
                                </div>
                            </div>
                            <div v-if="canManageCollab" class="mt-4 pt-4 border-t border-slate-100">
                                <button @click="collabCreateOpen = !collabCreateOpen" class="w-full min-h-[38px] rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 flex items-center justify-center gap-1.5">
                                    <i :class="collabCreateOpen ? 'ph ph-x' : 'ph ph-plus-circle'"></i>
                                    {{ collabCreateOpen ? '收起项目创建' : '创建/切换团队项目' }}
                                </button>
                                <form v-if="collabCreateOpen" @submit.prevent="createCollabProject" class="mt-3 grid grid-cols-1 gap-2">
                                    <input v-model="collabCreateForm.title" class="liquid-glass-input px-3 py-2 text-[11px] outline-none" placeholder="项目名称">
                                    <input v-model="collabCreateForm.teamName" class="liquid-glass-input px-3 py-2 text-[11px] outline-none" placeholder="团队名称">
                                    <input v-model="collabCreateForm.course" class="liquid-glass-input px-3 py-2 text-[11px] outline-none" placeholder="关联课程">
                                    <textarea v-model="collabCreateForm.description" rows="3" class="liquid-glass-input px-3 py-2 text-[11px] outline-none resize-none" placeholder="项目介绍"></textarea>
                                    <input v-model="collabCreateForm.members" class="liquid-glass-input px-3 py-2 text-[11px] outline-none" placeholder="成员，用逗号分隔">
                                    <button type="submit" :disabled="!!collabActionLoading" class="min-h-[36px] rounded-xl bg-teal-600 text-white text-[11px] font-bold hover:bg-teal-700 disabled:opacity-50">创建项目</button>
                                </form>
                            </div>
                        </section>

                        <section class="glass-panel-liquid p-5 flex flex-col gap-3 shrink-0">
                            <div class="flex items-center justify-between">
                                <h5 class="text-xs font-extrabold text-slate-800">成员 Git 进度</h5>
                                <span class="text-[10px] text-slate-400">实时追踪</span>
                            </div>
                            <div class="flex flex-col gap-3">
                                <div v-for="member in memberProgress" :key="member.id" class="bg-white/75 border border-white rounded-xl p-3">
                                    <div class="flex items-start justify-between gap-2">
                                        <div class="min-w-0">
                                            <p class="text-xs font-extrabold text-slate-800 truncate">{{ member.name }}</p>
                                            <p class="text-[10px] text-slate-500 truncate">{{ member.task }}</p>
                                        </div>
                                        <span class="text-[10px] px-2 py-1 rounded-full border font-bold shrink-0" :class="memberStatusClass(member)">{{ member.statusLabel }}</span>
                                    </div>
                                    <div class="mt-3 flex items-center justify-between text-[10px] text-slate-500">
                                        <span class="truncate font-mono">{{ member.branch }}</span>
                                        <span class="font-bold">{{ member.progress }}%</span>
                                    </div>
                                    <span class="member-meta text-[10px] text-slate-400">Gitea：{{ member.giteaStatus || member.permissionSyncStatus || 'pending' }}</span>
                                    <div class="mt-1.5 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                        <div class="h-full bg-teal-500 rounded-full transition-all duration-300" :style="{ width: member.progress + '%' }"></div>
                                    </div>
                                    <div v-if="canManageCollab" class="mt-3 flex flex-wrap gap-2">
                                        <button @click="startAssignTask(member)" class="min-h-[30px] px-2.5 rounded-lg bg-white border border-slate-200 text-[10px] font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-50">
                                            分配任务
                                        </button>
                                        <button @click="remindCollabMembers(member)" :disabled="!!collabActionLoading" class="min-h-[30px] px-2.5 rounded-lg bg-amber-50 border border-amber-100 text-[10px] font-bold text-amber-700 hover:bg-amber-100 disabled:opacity-50">
                                            提醒提交
                                        </button>
                                    </div>
                                    <form v-if="canManageCollab && assigningMemberName === member.name" @submit.prevent="submitAssignTask" class="mt-3 grid grid-cols-1 gap-2 p-2 rounded-xl bg-slate-50 border border-slate-100">
                                        <input v-model="assignTaskForm.task" class="bg-white border border-slate-200 rounded-lg px-2.5 py-2 text-[10px] outline-none focus:border-teal-500" placeholder="任务说明">
                                        <input v-model="assignTaskForm.branch" class="bg-white border border-slate-200 rounded-lg px-2.5 py-2 text-[10px] outline-none focus:border-teal-500 font-mono" placeholder="feature/member-task">
                                        <div class="flex gap-2 justify-end">
                                            <button type="button" @click="assigningMemberName = ''" class="min-h-[30px] px-2.5 rounded-lg bg-white border border-slate-200 text-[10px] font-bold text-slate-500">取消</button>
                                            <button type="submit" :disabled="!!collabActionLoading" class="min-h-[30px] px-2.5 rounded-lg bg-teal-600 text-white text-[10px] font-bold disabled:opacity-50">保存</button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </section>
                    </aside>

                    <main class="flex flex-col gap-4 overflow-visible xl:overflow-y-auto no-scrollbar h-auto xl:h-full min-w-0 shrink-0">
                        <section data-testid="collab-repository-card" class="glass-panel-liquid p-5 min-h-[220px] shrink-0">
                            <div data-testid="collab-repository-content" class="relative z-10">
                            <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
                                <div class="min-w-0">
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">项目仓库</span>
                                    <h4 class="text-lg font-extrabold text-slate-900 mt-1">{{ repositoryInfo.repoName }}</h4>
                                    <p class="text-xs text-slate-500 mt-1">{{ collabProject.course }} · {{ collabProject.teamName }}</p>
                                </div>
                                <div class="flex flex-wrap gap-2">
                                    <button @click="teamAuthenticatedCloneUrl ? copyTeamAuthClone() : handleTeamRotateGiteaToken()" class="min-h-[40px] px-3 rounded-xl bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 flex items-center gap-1.5">
                                        <i :class="copiedTeamAuthClone ? 'ph ph-check' : 'ph ph-key'"></i> HTTPS+Token
                                    </button>
                                    <button @click="copyGitCommand(repositoryInfo.cloneUrl)" class="min-h-[40px] px-3 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5">
                                        <i class="ph ph-copy"></i> HTTP
                                    </button>
                                    <button @click="copyGitCommand(repositoryInfo.sshUrl)" class="min-h-[40px] px-3 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5">
                                        <i class="ph ph-terminal-window"></i> SSH
                                    </button>
                                    <button @click="openCollabRepositoryHome(collabData)" class="min-h-[40px] px-3 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 flex items-center gap-1.5">
                                        <i class="ph ph-book-open-text"></i> 仓库主页
                                    </button>
                                </div>
                            </div>
                            <dl data-testid="collab-repository-meta" class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs items-stretch">
                                <div v-if="teamAuthenticatedCloneUrl" class="bg-emerald-50 border border-emerald-200 rounded-xl p-3 min-w-0 min-h-[72px] flex flex-col justify-center">
                                    <dt class="text-[10px] text-emerald-600 font-bold">HTTPS + Token Clone</dt>
                                    <dd class="mt-1 font-mono text-emerald-800 break-all whitespace-normal leading-relaxed">{{ teamAuthenticatedCloneUrl }}</dd>
                                </div>
                                <div class="bg-white/70 border border-white rounded-xl p-3 min-w-0 min-h-[72px] flex flex-col justify-center">
                                    <dt class="text-[10px] text-slate-400 font-bold">HTTP Clone 地址</dt>
                                    <dd class="mt-1 font-mono text-slate-700 break-all whitespace-normal leading-relaxed">{{ repositoryInfo.cloneUrl }}</dd>
                                </div>
                                <div class="bg-white/70 border border-white rounded-xl p-3 min-w-0 min-h-[72px] flex flex-col justify-center">
                                    <dt class="text-[10px] text-slate-400 font-bold">SSH Clone 地址</dt>
                                    <dd class="mt-1 font-mono text-slate-700 break-all whitespace-normal leading-relaxed">{{ repositoryInfo.sshUrl }}</dd>
                                </div>
                                <div class="bg-white/70 border border-white rounded-xl p-3 min-w-0 min-h-[64px] flex flex-col justify-center">
                                    <dt class="text-[10px] text-slate-400 font-bold">默认分支</dt>
                                    <dd class="mt-1 font-mono text-slate-700 break-all whitespace-normal leading-relaxed">{{ repositoryInfo.defaultBranch }}</dd>
                                </div>
                                <div class="bg-white/70 border border-white rounded-xl p-3 min-w-0 min-h-[64px] flex flex-col justify-center">
                                    <dt class="text-[10px] text-slate-400 font-bold">当前任务分支</dt>
                                    <dd class="mt-1 font-mono text-slate-700 break-all whitespace-normal leading-relaxed">{{ repositoryInfo.taskBranch }}</dd>
                                </div>
                            </dl>
                            <div class="mt-4 grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_280px] gap-3 border-t border-slate-100 pt-4">
                                <div class="bg-white/70 border border-white rounded-xl p-3 min-w-0">
                                    <div class="flex flex-wrap items-center justify-between gap-2">
                                        <div>
                                            <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">Gitea Account</span>
                                            <h5 class="text-sm font-extrabold text-slate-900 mt-1">本机 Git 身份</h5>
                                        </div>
                                        <button @click="loadTeamGiteaIdentity" :disabled="teamIdentityLoading" class="min-h-[32px] px-3 rounded-lg bg-white border border-slate-200 text-[11px] font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50">
                                            {{ teamIdentityLoading ? '同步中' : '刷新' }}
                                        </button>
                                    </div>
                                    <div class="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px]">
                                        <div class="rounded-lg bg-slate-50 border border-slate-100 px-2.5 py-2 min-w-0">
                                            <p class="text-slate-400 font-bold">用户名</p>
                                            <p class="font-mono text-slate-800 truncate mt-1">{{ teamGiteaIdentity?.giteaUsername || '等待同步' }}</p>
                                        </div>
                                        <div class="rounded-lg bg-slate-50 border border-slate-100 px-2.5 py-2 min-w-0">
                                            <p class="text-slate-400 font-bold">邮箱</p>
                                            <p class="font-mono text-slate-800 truncate mt-1">{{ teamGiteaIdentity?.giteaEmail || '等待同步' }}</p>
                                        </div>
                                        <div class="rounded-lg bg-slate-50 border border-slate-100 px-2.5 py-2 min-w-0">
                                            <p class="text-slate-400 font-bold">同步状态</p>
                                            <p class="font-mono text-slate-800 truncate mt-1">{{ teamGiteaIdentity?.syncStatus || 'pending' }}</p>
                                        </div>
                                    </div>
                                    <div v-if="teamGiteaIdentity?.gitConfigCommands?.length" class="mt-3 rounded-xl bg-slate-950 text-slate-100 p-3">
                                        <div class="flex items-center justify-between gap-2 mb-2">
                                            <span class="text-[10px] font-bold text-slate-300">Git config</span>
                                            <button type="button" @click="copyTeamGitConfig" class="min-h-[28px] px-2 rounded-lg bg-white/10 hover:bg-white/15 text-[10px] font-bold">
                                                {{ copiedTeamGitConfigAll ? '已复制' : '复制全部' }}
                                            </button>
                                        </div>
                                        <div v-for="command in teamGiteaIdentity.gitConfigCommands" :key="command" class="flex items-center justify-between gap-2 py-1 border-t border-white/10 first:border-t-0">
                                            <code class="text-[11px] break-all">{{ command }}</code>
                                            <button type="button" @click="copyTeamGitConfigLine(command)" class="shrink-0 w-7 h-7 rounded-lg bg-white/10 hover:bg-white/15 flex items-center justify-center" :title="copiedTeamGitConfigLine === command ? '已复制' : '复制'">
                                                <i :class="copiedTeamGitConfigLine === command ? 'ph ph-check' : 'ph ph-copy'"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="bg-white/70 border border-white rounded-xl p-3 min-w-0">
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">Git Token</span>
                                    <h5 class="text-sm font-extrabold text-slate-900 mt-1">本机 push 凭据</h5>
                                    <button @click="handleTeamRotateGiteaToken" :disabled="!!collabActionLoading" class="mt-3 w-full min-h-[38px] px-3 rounded-xl bg-teal-600 text-white text-xs font-bold hover:bg-teal-700 disabled:opacity-50">
                                        生成/重置访问 Token
                                    </button>
                                    <div v-if="teamGeneratedToken" class="mt-3 rounded-xl bg-amber-50 border border-amber-100 p-3">
                                        <p class="text-[10px] text-amber-700 leading-relaxed">{{ teamTokenWarning }}</p>
                                        <code class="mt-2 block text-[11px] font-mono text-slate-900 break-all bg-white/80 border border-amber-100 rounded-lg p-2">{{ teamGeneratedToken }}</code>
                                        <button type="button" @click="copyTeamGeneratedToken" class="mt-2 w-full min-h-[32px] rounded-lg bg-slate-900 text-white text-[11px] font-bold hover:bg-slate-800">
                                            {{ copiedTeamToken ? '已复制 Token' : '复制 Token' }}
                                        </button>
                                    </div>
                                    <p v-else class="mt-3 text-[10px] text-slate-500 leading-relaxed">Token 只会显示一次，用于本机 Git clone / push 的 HTTPS 认证。</p>
                                </div>
                            </div>
                            <div v-if="canManageCollab" class="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                                <button @click="createGiteaRepository" :disabled="!!collabActionLoading" class="min-h-[40px] px-4 rounded-xl bg-teal-600 text-white text-xs font-bold hover:bg-teal-700 disabled:opacity-50 flex items-center gap-1.5">
                                    <i class="ph ph-git-branch"></i> 创建团队仓库
                                </button>
                                <button @click="bindExistingRepository" :disabled="!!collabActionLoading" class="min-h-[40px] px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50 disabled:opacity-50 flex items-center gap-1.5">
                                    <i class="ph ph-link"></i> 绑定已有仓库
                                </button>
                                <button @click="refreshCollabStatus('merged')" :disabled="!!collabActionLoading" class="min-h-[40px] px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50 disabled:opacity-50 flex items-center gap-1.5">
                                    <i class="ph ph-seal-check"></i> 模拟合并
                                </button>
                            </div>
                            </div>
                        </section>

                        <section class="glass-panel-liquid p-5 shrink-0">
                            <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
                                <div>
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">Git 工作流</span>
                                    <h4 class="text-base font-extrabold text-slate-900 mt-1">{{ currentUserProgress.nextHint }}</h4>
                                </div>
                                <div class="flex flex-wrap gap-2">
                                    <button @click="confirmCloneDone" :disabled="!!collabActionLoading" class="min-h-[40px] px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50 disabled:opacity-50">
                                        我已完成拉取
                                    </button>
                                    <button @click="refreshCollabStatus('pr')" :disabled="!!collabActionLoading" class="min-h-[40px] px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50 disabled:opacity-50">
                                        模拟 PR 检测
                                    </button>
                                </div>
                            </div>
                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
                                <article v-for="(step, idx) in workflowSteps" :key="step.id" class="border rounded-xl p-4 flex flex-col gap-3" :class="stepStatusClass(step.status)">
                                    <div class="flex items-start justify-between gap-3">
                                        <div class="flex gap-3 min-w-0">
                                            <div class="w-8 h-8 rounded-xl bg-white border border-current/10 flex items-center justify-center text-xs font-extrabold shrink-0">{{ idx + 1 }}</div>
                                            <div class="min-w-0">
                                                <h5 class="text-sm font-extrabold text-slate-900">{{ step.title }}</h5>
                                                <p class="text-xs text-slate-500 leading-relaxed mt-1">{{ step.description }}</p>
                                            </div>
                                        </div>
                                        <span class="text-[10px] px-2 py-1 rounded-full bg-white/80 border border-current/10 font-bold shrink-0">{{ step.statusLabel }}</span>
                                    </div>
                                    <pre class="bg-slate-950 text-slate-100 rounded-xl p-3 text-[11px] leading-relaxed overflow-x-auto font-mono whitespace-pre-wrap">{{ step.command }}</pre>
                                    <div class="flex items-center justify-between gap-3">
                                        <p class="text-[10px] text-slate-500">{{ step.nextHint }}</p>
                                        <button @click="copyGitCommand(step.command)" class="min-h-[36px] px-3 rounded-lg bg-white border border-slate-200 text-slate-700 text-[11px] font-bold hover:bg-slate-50 shrink-0 flex items-center gap-1">
                                            <i class="ph ph-copy"></i> 复制命令
                                        </button>
                                    </div>
                                </article>
                            </div>
                        </section>

                        <section class="glass-panel-liquid p-5 shrink-0">
                            <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
                                <div>
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">COMMITS</span>
                                    <h4 class="text-base font-extrabold text-slate-900 mt-1">成员提交记录</h4>
                                </div>
                                <span class="text-[10px] text-slate-400">按 Webhook / 后端同步时间展示</span>
                            </div>
                            <div v-if="recentCommits.length === 0" class="rounded-xl bg-slate-50 border border-slate-100 p-5 text-center text-xs text-slate-500">暂无提交记录，等待成员 push 后同步。</div>
                            <div v-else class="grid grid-cols-1 xl:grid-cols-3 gap-3">
                                <article v-for="commit in recentCommits" :key="commit.id" class="bg-white/75 border border-white rounded-xl p-3 min-w-0">
                                    <div class="flex items-start justify-between gap-3">
                                        <div class="min-w-0">
                                            <p class="text-xs font-extrabold text-slate-900 truncate">{{ commit.author }}</p>
                                            <p class="mt-1 text-[10px] font-mono text-slate-500 truncate">{{ commit.branch }}</p>
                                        </div>
                                        <span class="shrink-0 text-[10px] text-slate-400 font-bold">{{ formatDisplayDateTime(commit.time) }}</span>
                                    </div>
                                    <p class="mt-3 text-xs text-slate-600 leading-relaxed line-clamp-2">{{ commit.message }}</p>
                                </article>
                            </div>
                        </section>

                        <section class="glass-panel-liquid p-5 shrink-0">
                            <div class="flex items-center justify-between mb-4">
                                <div>
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">TEAM TABLE</span>
                                    <h4 class="text-base font-extrabold text-slate-900 mt-1">成员 Git 进度表</h4>
                                </div>
                                <span class="text-[10px] text-slate-400">loading / empty / error 已接入</span>
                            </div>
                            <div v-if="canManageCollab" class="mb-4 flex flex-col md:flex-row gap-2">
                                <input v-model="reminderMessage" class="liquid-glass-input flex-1 min-h-[38px] px-3 text-xs outline-none" placeholder="给未提交成员的提醒内容">
                                <button @click="remindCollabMembers()" :disabled="!!collabActionLoading" class="min-h-[38px] px-4 rounded-xl bg-amber-500 text-white text-xs font-bold hover:bg-amber-600 disabled:opacity-50 shrink-0">
                                    提醒未提交成员
                                </button>
                            </div>
                            <div v-if="memberProgress.length === 0" class="rounded-xl bg-slate-50 border border-slate-100 p-6 text-center text-sm text-slate-500">暂无成员进度，等待项目分组完成。</div>
                            <div v-else class="overflow-x-auto">
                                <table class="w-full min-w-[760px] text-left text-xs">
                                    <thead class="text-[10px] text-slate-400 uppercase tracking-wide">
                                        <tr class="border-b border-slate-100">
                                            <th class="py-2 pr-3">成员</th>
                                            <th class="py-2 pr-3">任务</th>
                                            <th class="py-2 pr-3">分支</th>
                                            <th class="py-2 pr-3">Commit</th>
                                            <th class="py-2 pr-3">PR</th>
                                            <th class="py-2 pr-3">Merge</th>
                                            <th class="py-2 pr-3">得分</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="member in memberProgress" :key="member.id" class="border-b border-slate-100 last:border-0">
                                            <td class="py-3 pr-3 font-bold text-slate-800 whitespace-nowrap">{{ member.name }}</td>
                                            <td class="py-3 pr-3 text-slate-600 max-w-[220px] truncate">{{ member.task }}</td>
                                            <td class="py-3 pr-3 font-mono text-[11px] text-slate-500">{{ member.branch }}</td>
                                            <td class="py-3 pr-3 text-slate-700">{{ member.commitCount }} 次</td>
                                            <td class="py-3 pr-3"><span class="px-2 py-1 rounded-full border text-[10px] font-bold" :class="memberStatusClass(member)">{{ member.statusLabel }}</span></td>
                                            <td class="py-3 pr-3 text-slate-600">{{ member.mergeStatus === 'merged' ? '已合并' : '待合并' }}</td>
                                            <td class="py-3 pr-3 font-bold text-slate-900">{{ member.score }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    </main>

                    <aside class="flex flex-col gap-4 overflow-visible xl:overflow-y-auto no-scrollbar h-auto xl:h-full min-h-0 shrink-0">
                        <section class="glass-panel-liquid p-5 shrink-0">
                            <div class="flex items-center justify-between mb-4">
                                <div>
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">Pull Request</span>
                                    <h4 class="text-base font-extrabold text-slate-900 mt-1">PR 状态区</h4>
                                    <div class="mt-2 flex flex-wrap gap-1.5">
                                        <span v-if="isGiteaLive" class="text-[10px] px-2 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-100 font-bold">Gitea 实时同步</span>
                                        <span v-if="isWebhookConnected" class="text-[10px] px-2 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100 font-bold">Webhook 已接通</span>
                                        <span v-if="isDemoFallback" class="text-[10px] px-2 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-100 font-bold">演示数据</span>
                                    </div>
                                </div>
                                <button @click="openExternalLink(prCreationUrl)" class="min-h-[36px] px-3 rounded-lg bg-slate-900 text-white text-[11px] font-bold hover:bg-slate-800">创建 PR</button>
                            </div>
                            <p v-if="syncErrorMessage" class="mb-3 text-[10px] text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-2 py-1.5">
                                {{ syncErrorMessage }}
                            </p>
                            <textarea v-if="canManageCollab" v-model="prReviewComment" rows="2" class="mb-3 w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-[11px] outline-none focus:border-teal-500 resize-none" placeholder="队长初审意见，会随推荐合并同步到后端"></textarea>
                            <div v-if="pullRequests.length === 0" class="rounded-xl bg-slate-50 border border-slate-100 p-5 text-center text-xs text-slate-500">
                                {{ isGiteaEmptyPr ? '暂无真实 Gitea PR' : '尚未创建 Pull Request。' }}
                            </div>
                            <div v-else class="flex flex-col gap-3">
                                <article v-for="pr in pullRequests" :key="pr.id" class="bg-white/75 border border-white rounded-xl p-3">
                                    <div class="flex items-start justify-between gap-2">
                                        <div class="min-w-0">
                                            <p class="text-xs font-extrabold text-slate-900 truncate">#{{ pr.number }} {{ pr.title }}</p>
                                            <p class="text-[10px] text-slate-500 mt-1 truncate">{{ pr.creator }} · {{ pr.sourceBranch }} -> {{ pr.targetBranch }}</p>
                                        </div>
                                        <div class="flex items-center gap-1.5 shrink-0">
                                            <span v-if="pr.source === 'member_progress_backfill' || pr.source === 'demo_fallback'" class="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-100 font-bold">演示数据</span>
                                            <span class="text-[10px] px-2 py-1 rounded-full border font-bold" :class="prStatusClass(pr.status)">{{ pr.statusLabel }}</span>
                                        </div>
                                    </div>
                                    <div class="mt-3 flex items-center justify-between text-[10px] text-slate-400">
                                        <span>更新 {{ formatDisplayDateTime(pr.updatedAt) }}</span>
                                        <button @click="openRepositoryHomePullRequests(pr)" class="min-h-[32px] px-2.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-bold hover:bg-slate-50 flex items-center gap-1">
                                            <i class="ph ph-arrow-square-out"></i> 打开 PR
                                        </button>
                                    </div>
                                    <div v-if="canManageCollab && pr.status === 'open'" class="mt-3 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
                                        <button @click="reviewCollabPr(pr, 'request_changes')" :disabled="!!collabActionLoading" class="min-h-[32px] px-3 rounded-lg bg-white border border-slate-200 text-[10px] font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50">
                                            要求修改
                                        </button>
                                        <button @click="reviewCollabPr(pr, 'recommend_merge')" :disabled="!!collabActionLoading" class="min-h-[32px] px-3 rounded-lg bg-teal-600 text-white text-[10px] font-bold hover:bg-teal-700 disabled:opacity-50">
                                            推荐合并
                                        </button>
                                    </div>
                                    <p v-if="pr.reviewComment" class="mt-2 text-[10px] text-slate-500 leading-relaxed bg-slate-50 border border-slate-100 rounded-lg px-2 py-1.5">
                                        审核意见：{{ pr.reviewComment }}
                                    </p>
                                </article>
                            </div>
                        </section>

                        <!-- AI Git 教练反馈 — 插入 PR 状态区与 Webhook 动态之间 -->
                        <section class="glass-panel-liquid p-5 shrink-0">
                            <div class="flex items-center justify-between mb-4">
                                <div>
                                    <span class="text-[10px] text-purple-600 font-bold uppercase tracking-wider">AI Git Coach</span>
                                    <h4 class="text-base font-extrabold text-slate-900 mt-1">AI Git 教练反馈</h4>
                                </div>
                                <button @click="refreshCollabStatus()" class="min-h-[34px] px-3 rounded-lg bg-white border border-slate-200 text-[11px] font-bold text-slate-700 hover:bg-slate-50">刷新同步</button>
                            </div>
                            <div v-if="aiGitCoachFeedback.length === 0" class="rounded-xl bg-slate-50 border border-slate-100 p-5 text-center text-xs text-slate-500">
                                等待 push / PR 后生成教学反馈。
                            </div>
                            <div v-else class="flex flex-col gap-3">
                                <article v-for="item in aiGitCoachFeedback.slice(0, 5)" :key="item.id || item.sha" class="bg-white/80 border border-white rounded-xl p-3">
                                    <!-- 头部：状态徽章 + 分支 + 作者 -->
                                    <div class="flex items-start justify-between gap-2 mb-2">
                                        <div class="min-w-0">
                                            <span class="text-[10px] font-extrabold mr-1.5 px-2 py-0.5 rounded-full border"
                                                :class="item.status === 'ready'
                                                    ? 'bg-teal-50 text-teal-700 border-teal-200'
                                                    : item.status === 'fallback'
                                                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                                                        : 'bg-slate-50 text-slate-500 border-slate-200'">
                                                {{ item.status === 'ready' ? 'AI 教练' : item.status === 'fallback' ? '规则诊断' : 'AI Git 教练分析中' }}
                                            </span>
                                            <span class="text-[10px] text-slate-400">{{ item.branch }}</span>
                                        </div>
                                        <span class="text-[10px] text-slate-400 shrink-0">{{ item.author }}</span>
                                    </div>
                                    <!-- summary -->
                                    <p class="text-xs font-semibold text-slate-800 leading-relaxed mb-2">{{ item.summary }}</p>
                                    <!-- fallback 提示 -->
                                    <p v-if="item.status === 'fallback'" class="text-[10px] text-amber-600 mb-2">规则诊断（AI 暂不可用）</p>
                                    <!-- 哪里做错了 -->
                                    <div v-if="item.mistakes && item.mistakes.length > 0" class="mb-2">
                                        <p class="text-[10px] font-bold text-red-600 mb-1">❌ 哪里做错了</p>
                                        <ul class="pl-3 space-y-0.5">
                                            <li v-for="(m, idx) in item.mistakes" :key="idx" class="text-[10px] text-slate-600 leading-relaxed list-disc">{{ m }}</li>
                                        </ul>
                                    </div>
                                    <!-- 怎么改 -->
                                    <div v-if="item.suggestions && item.suggestions.length > 0">
                                        <p class="text-[10px] font-bold text-teal-600 mb-1">💡 怎么改</p>
                                        <ul class="pl-3 space-y-0.5">
                                            <li v-for="(s, idx) in item.suggestions" :key="idx" class="text-[10px] text-slate-600 leading-relaxed list-disc">{{ s }}</li>
                                        </ul>
                                    </div>
                                    <!-- 次要信息 -->
                                    <p class="text-[10px] text-slate-400 mt-2">{{ formatDisplayDateTime(item.updatedAt || item.createdAt) }}</p>
                                </article>
                            </div>
                        </section>

                        <section class="glass-panel-liquid p-5 shrink-0">
                            <div class="flex items-center justify-between mb-4">
                                <div>
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">Git 事件日志</span>
                                    <h4 class="text-base font-extrabold text-slate-900 mt-1">Webhook 动态</h4>
                                </div>
                                <button @click="refreshCollabStatus('merged')" class="min-h-[34px] px-3 rounded-lg bg-white border border-slate-200 text-[11px] font-bold text-slate-700 hover:bg-slate-50">刷新</button>
                            </div>
                            <div class="flex flex-col gap-3">
                                <div v-for="event in gitEvents" :key="event.id" class="flex gap-3">
                                    <div class="w-8 h-8 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center shrink-0">
                                        <i :class="['ph', eventIcon(event.type)]"></i>
                                    </div>
                                    <div class="min-w-0">
                                        <p class="text-xs font-semibold text-slate-700 leading-relaxed">{{ event.text }}</p>
                                        <p class="text-[10px] text-slate-400 mt-0.5">{{ formatDisplayDateTime(event.time) }}</p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <section class="glass-panel-liquid p-5 shrink-0">
                            <div class="flex items-center justify-between mb-4">
                                <div>
                                    <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider">Contribution</span>
                                    <h4 class="text-base font-extrabold text-slate-900 mt-1">团队贡献度</h4>
                                </div>
                                <span class="text-[10px] text-slate-400">commit / PR / 评分</span>
                            </div>
                            <div class="flex flex-col gap-3">
                                <div v-for="member in contributionRanking" :key="member.id || member.name" class="bg-white/75 border border-white rounded-xl p-3">
                                    <div class="flex items-center justify-between gap-3">
                                        <div class="min-w-0">
                                            <p class="text-xs font-extrabold text-slate-800 truncate">{{ member.name }}</p>
                                            <p class="text-[10px] text-slate-500 truncate">{{ member.role }} · {{ member.task }}</p>
                                        </div>
                                        <span class="text-sm font-extrabold text-slate-900">{{ member.contribution || 0 }}%</span>
                                    </div>
                                    <div class="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                        <div class="h-full bg-teal-500 rounded-full" :style="{ width: (member.contribution || 0) + '%' }"></div>
                                    </div>
                                    <div class="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                                        <span>{{ member.commitCount || 0 }} commits / {{ member.prCount || 0 }} PR</span>
                                        <span>得分 {{ member.score || 0 }}</span>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <section class="glass-panel-liquid p-5 flex flex-col min-h-[260px] shrink-0">
                            <span class="text-[10px] text-teal-600 font-bold uppercase tracking-wider block mb-2 select-none">TEAM CHAT & PAIRBOT</span>
                            <div class="flex-1 overflow-y-auto no-scrollbar flex flex-col gap-3 p-2 bg-slate-50/50 border border-slate-100 rounded-xl mb-3 min-h-0">
                                <div v-for="msg in chatMessages" :key="msg.id" class="flex flex-col gap-1">
                                    <div class="flex items-center gap-1.5 text-[9px] font-bold px-1 select-none" :class="msg.sender === 'PairBot' ? 'text-indigo-600' : 'text-slate-500'">
                                        <span>{{ msg.sender }}</span>
                                        <span class="font-normal text-slate-400">{{ formatDisplayDateTime(msg.time) }}</span>
                                    </div>
                                    <div class="p-2.5 rounded-xl text-xs max-w-[92%] leading-relaxed font-semibold" :class="msg.sender === 'PairBot' ? 'bg-indigo-50 border border-indigo-100 text-indigo-800' : msg.sender === collabViewerName ? 'bg-teal-50 border border-teal-100 text-teal-800 self-end' : 'bg-white border border-slate-100 text-slate-700'">
                                        <p v-html="msg.content.replace(/\\n/g, '<br>')"></p>
                                    </div>
                                </div>
                                <div v-if="isPairBotThinking" class="flex items-start gap-1 p-1">
                                    <span class="text-[9px] font-bold text-indigo-500 animate-pulse select-none">PairBot 正在整理 Git 协作建议...</span>
                                </div>
                            </div>
                            <div class="flex gap-2 shrink-0">
                                <input v-model="chatInput" @keydown.enter="sendCollabMessage" type="text" placeholder="在群组中讨论或 @PairBot 提问..." class="flex-1 min-h-[40px] bg-white border border-slate-200 text-xs rounded-xl px-3 outline-none focus:ring-2 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium" />
                                <button @click="sendCollabMessage" class="min-h-[40px] bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 rounded-xl flex items-center justify-center transition-all active:scale-95">发送</button>
                            </div>
                        </section>
                    </aside>
                </div>
            </div>
        </div>
    `
};
