import { computed, ref, watch, nextTick } from 'vue';
import { sendStreamingMessage, parsedHtmlCache } from '../api/streamChat.js';
import { buildVisualGuideSvg, createLocalVisualGuide, getVisualGuideSourceLabel, requestVisualGuideImage, resolveVisualGuideState } from '../api/visualGuide.js';
import { knowledgeApi } from '../api/knowledgeApi.js';
import { userApi } from '../api/userApi.js';
import request from '../utils/request.js';
import { getChatStorageKey, getHistoryPanelTitle, mapHistoryRecordToMessage, normalizeAgentMode, sanitizeStoredMessagesForMode, shouldShowHistoryButton } from '../utils/chatModes.js';
import { getKnowledgeFileStatusLabel, isSupportedKnowledgeFile } from '../utils/knowledgeFiles.js';

export function useChat(currentUser, showToast, agentResolver = null) {
    const inputText = ref('');
    const chatContainer = ref(null);
    const thinkingAgent = ref(null);
    const forceRAG = ref(false);
    const agentMode = ref('tutor');
    const historyLoading = ref(false);
    const historyError = ref('');
    const showHistoryPanel = ref(false);
    const highlightedMessageId = ref(null);
    let highlightTimer = null;
    const createEmptyVisualGuide = () => ({
        title: 'AI 引导图生成师',
        caption: '可将问题转为可视化图片。',
        center: '等待问题',
        nodes: [],
        edges: [],
        type: 'concept',
        source: 'empty',
        generatedAt: ''
    });
    const visualGuidePrompt = ref('');
    const visualGuideType = ref('concept');
    const visualGuideStatus = ref('ready');
    const visualGuideImage = ref(null);
    const showVisualGuideViewer = ref(false);
    const visualGuide = ref(createEmptyVisualGuide());
    const visualGuideCache = ref({});
    const visualGuideHistory = ref([]);
    let visualGuideRequestId = 0;

    const getSessionId = () => currentUser.value?.username || 'guest_user';
    const getAgentById = (id) => (typeof agentResolver === 'function' ? agentResolver(id) : null);
    const getActiveChatAgent = () => {
        const agentId = normalizeAgentMode(agentMode.value) === 'rag' ? 'agent_researcher' : 'agent_tutor';
        return getAgentById(agentId);
    };
    const getVisualGuideAgent = () => getAgentById('agent_visual_guide');
    const getArchitectureGuideAgent = () => getAgentById('agent_tutor');
    const readStoredMessages = (mode = agentMode.value) => {
        const normalizedMode = normalizeAgentMode(mode);
        const storageKey = getChatStorageKey(getSessionId(), normalizedMode);
        const stored = localStorage.getItem(storageKey) || (normalizedMode === 'tutor' ? localStorage.getItem('messages') : null);
        if (!stored) return [];
        try {
            return sanitizeStoredMessagesForMode(JSON.parse(stored), normalizedMode);
        } catch (error) {
            console.warn('[Chat] Failed to parse stored messages.', error);
            return [];
        }
    };

    const messages = ref(readStoredMessages('tutor'));

    const hydrateParsedMessages = () => {
        Object.keys(parsedHtmlCache).forEach(key => delete parsedHtmlCache[key]);
        messages.value.forEach(msg => {
            if (msg.senderType === 'agent') {
                parsedHtmlCache[msg.id] = (window.marked && window.marked.parse) ? window.marked.parse(msg.content) : msg.content;
            }
        });
    };

    const loadChatHistory = async (mode = agentMode.value) => {
        const normalizedMode = normalizeAgentMode(mode);
        const sessionId = getSessionId();
        agentMode.value = normalizedMode;
        forceRAG.value = normalizedMode === 'rag';

        messages.value = readStoredMessages(normalizedMode);
        hydrateParsedMessages();
        await nextTick();
        if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight;

        historyLoading.value = true;
        historyError.value = '';
        try {
            const resJson = await request(`/chat/history?session_id=${encodeURIComponent(sessionId)}&agent_mode=${encodeURIComponent(normalizedMode)}&limit=200`);
            if (resJson?.status === 'success' && Array.isArray(resJson.data)) {
                messages.value = resJson.data.map(mapHistoryRecordToMessage);
                hydrateParsedMessages();
                localStorage.setItem(getChatStorageKey(sessionId, normalizedMode), JSON.stringify(messages.value));
                await nextTick();
                if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
            }
        } catch (error) {
            historyError.value = '历史记录暂时无法同步，当前显示本地缓存。';
            console.info('[Chat] Backend history unavailable, using local cache.', error);
        } finally {
            historyLoading.value = false;
        }
    };

    const setAgentMode = (mode) => loadChatHistory(mode);
    const openHistoryPanel = async () => {
        if (!shouldShowHistoryButton(agentMode.value)) return;
        showHistoryPanel.value = true;
        await loadChatHistory(agentMode.value);
    };
    const closeHistoryPanel = () => {
        showHistoryPanel.value = false;
    };

    const jumpToHistoryMessage = async (message) => {
        if (!message?.id) return;
        const targetId = message.id;
        const exists = messages.value.some(item => item.id === targetId);
        if (!exists) {
            showToast('未找到对应的对话消息', 'warning');
            return;
        }

        showHistoryPanel.value = false;
        highlightedMessageId.value = targetId;
        if (highlightTimer) {
            clearTimeout(highlightTimer);
            highlightTimer = null;
        }

        await nextTick();
        const container = chatContainer.value;
        const targetIdStr = String(targetId);
        const candidates = container
            ? Array.from(container.querySelectorAll('[data-message-id]'))
            : [];
        const target = candidates.find(el => el.getAttribute('data-message-id') === targetIdStr);

        if (!target) {
            showToast('对话消息尚未渲染完成，请稍后重试', 'warning');
            return;
        }

        target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
        highlightTimer = setTimeout(() => {
            if (highlightedMessageId.value === targetId) {
                highlightedMessageId.value = null;
            }
            highlightTimer = null;
        }, 2600);
    };

    const resolveHistoryMessageDbId = (messageId) => {
        const raw = String(messageId || '');
        if (raw.startsWith('db-')) {
            const parsed = Number(raw.slice(3));
            return Number.isFinite(parsed) ? parsed : null;
        }
        const parsed = Number(raw);
        return Number.isFinite(parsed) ? parsed : null;
    };

    const deleteHistoryMessage = async (message) => {
        if (!message?.id) return;
        const preview = String(message.content || '').replace(/\s+/g, ' ').slice(0, 36);
        const confirmed = window.confirm(`确认删除这条历史记录？\n「${preview}${preview.length >= 36 ? '…' : ''}」`);
        if (!confirmed) return;

        const dbId = resolveHistoryMessageDbId(message.id);
        const sessionId = getSessionId();
        try {
            if (dbId != null) {
                const resJson = await request(
                    `/chat/history/${dbId}?session_id=${encodeURIComponent(sessionId)}`,
                    { method: 'DELETE' }
                );
                if (resJson?.status === 'error') {
                    throw new Error(resJson.message || '删除失败');
                }
            }
            messages.value = messages.value.filter(item => item.id !== message.id);
            if (parsedHtmlCache[message.id]) delete parsedHtmlCache[message.id];
            showToast('历史记录已删除', 'success');
        } catch (error) {
            // 后端不可用时仍允许清理本地缓存，避免按钮失效
            messages.value = messages.value.filter(item => item.id !== message.id);
            if (parsedHtmlCache[message.id]) delete parsedHtmlCache[message.id];
            historyError.value = '历史记录已从本地移除，云端同步可能未完成。';
            showToast(error.message || '已从本地删除', 'warning');
            console.info('[Chat] Delete history fallback to local cache.', error);
        }
    };

    const clearChatHistory = async (mode = agentMode.value) => {
        const normalizedMode = normalizeAgentMode(mode);
        if (messages.value.length === 0) {
            showToast('当前没有可清空的历史记录', 'info');
            return;
        }
        const label = normalizedMode === 'rag' ? '知识库检索' : '引导式学习';
        const confirmed = window.confirm(`确认清空全部「${label}」历史对话？此操作不可恢复。`);
        if (!confirmed) return;

        const sessionId = getSessionId();
        try {
            const resJson = await request(
                `/chat/history?session_id=${encodeURIComponent(sessionId)}&agent_mode=${encodeURIComponent(normalizedMode)}`,
                { method: 'DELETE' }
            );
            if (resJson?.status === 'error') {
                throw new Error(resJson.message || '清空失败');
            }
            messages.value = [];
            Object.keys(parsedHtmlCache).forEach(key => delete parsedHtmlCache[key]);
            localStorage.setItem(getChatStorageKey(sessionId, normalizedMode), '[]');
            showToast('历史记录已清空', 'success');
        } catch (error) {
            messages.value = [];
            Object.keys(parsedHtmlCache).forEach(key => delete parsedHtmlCache[key]);
            localStorage.setItem(getChatStorageKey(sessionId, normalizedMode), '[]');
            historyError.value = '历史记录已从本地清空，云端同步可能未完成。';
            showToast(error.message || '已从本地清空', 'warning');
            console.info('[Chat] Clear history fallback to local cache.', error);
        }
    };

    hydrateParsedMessages();

    const legacyFiles = ref([
        { id: 1, name: '软件杯竞赛指导书.pdf', size: '2.4 MB' },
        { id: 2, name: '大模型原理基础概念(必读).docx', size: '1.1 MB' }
    ]);

    const knowledgeRepositories = ref([]);
    const selectedRepositoryId = ref(localStorage.getItem(`knowledge_repo:${getSessionId()}`) || '');
    const newRepositoryName = ref('');
    const knowledgeLoading = ref(false);
    const knowledgeUploading = ref(false);
    const knowledgeDeletingId = ref('');
    const knowledgeRepositoryDeletingId = ref('');
    const knowledgeDatasetId = ref('');
    const courseKnowledgeBases = ref([]);
    const selectedCourseDatasetIds = ref([]);

    const formatFileSize = (bytes) => {
        const size = Number(bytes || 0);
        if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
        if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
        return `${size} B`;
    };

    const normalizeDocument = (doc) => ({
        id: doc.id,
        name: doc.filename,
        size: formatFileSize(doc.file_size),
        status: doc.status || 'parsing',
        repository_id: doc.repository_id,
        dataset_id: doc.dataset_id,
        rag_document_id: doc.rag_document_id,
        created_at: doc.created_at
    });

    const normalizeRepository = (repo) => ({
        ...repo,
        documents: Array.isArray(repo.documents) ? repo.documents.map(normalizeDocument) : [],
        document_count: Number(repo.document_count || repo.documents?.length || 0)
    });

    const selectedRepository = computed(() => (
        knowledgeRepositories.value.find(repo => repo.id === selectedRepositoryId.value) || null
    ));
    const files = computed(() => selectedRepository.value?.documents || []);

    const loadCourseKnowledgeBases = async () => {
        try {
            const resJson = await knowledgeApi.getCourseKnowledgeBases();
            const list = Array.isArray(resJson?.data) ? resJson.data : [];
            courseKnowledgeBases.value = list;
            if (selectedCourseDatasetIds.value.length === 0 && list.length > 0) {
                selectedCourseDatasetIds.value = list.map(item => item.id);
            }
        } catch (error) {
            console.info('[Knowledge] Course knowledge bases unavailable.', error);
        }
    };

    const toggleCourseDataset = (datasetId) => {
        const idx = selectedCourseDatasetIds.value.indexOf(datasetId);
        if (idx >= 0) {
            selectedCourseDatasetIds.value.splice(idx, 1);
        } else {
            selectedCourseDatasetIds.value.push(datasetId);
        }
    };

    const loadKnowledgeRepositories = async () => {
        const userId = getSessionId();
        if (!userId || userId === 'guest_user') return;
        knowledgeLoading.value = true;
        try {
            const resJson = await knowledgeApi.list(userId);
            const data = resJson?.data || {};
            knowledgeDatasetId.value = data.dataset_id || '';
            knowledgeRepositories.value = Array.isArray(data.repositories) ? data.repositories.map(normalizeRepository) : [];
            if (!knowledgeRepositories.value.some(repo => repo.id === selectedRepositoryId.value)) {
                selectedRepositoryId.value = knowledgeRepositories.value[0]?.id || '';
            }
            if (selectedRepositoryId.value) {
                localStorage.setItem(`knowledge_repo:${userId}`, selectedRepositoryId.value);
            } else {
                localStorage.removeItem(`knowledge_repo:${userId}`);
            }
        } catch (error) {
            console.info('[Knowledge] Backend unavailable.', error);
            showToast('知识库暂时无法同步', 'error');
        } finally {
            knowledgeLoading.value = false;
        }
    };

    const selectKnowledgeRepository = (repoId) => {
        selectedRepositoryId.value = repoId;
        if (repoId) {
            localStorage.setItem(`knowledge_repo:${getSessionId()}`, repoId);
        }
    };

    const createKnowledgeRepository = async () => {
        const name = newRepositoryName.value.trim();
        if (!name) return showToast('请输入仓库名称', 'error');
        knowledgeLoading.value = true;
        try {
            const resJson = await knowledgeApi.createRepository({ userId: getSessionId(), name });
            const repo = normalizeRepository(resJson.data);
            knowledgeRepositories.value.push(repo);
            selectKnowledgeRepository(repo.id);
            newRepositoryName.value = '';
            showToast('仓库已创建', 'success');
        } catch (error) {
            showToast(error.message || '仓库创建失败', 'error');
        } finally {
            knowledgeLoading.value = false;
        }
    };

    const toggleRAG = () => {
        const nextMode = forceRAG.value ? 'tutor' : 'rag';
        setAgentMode(nextMode);
        showToast(nextMode === 'rag' ? '已开启专属知识库检索模式' : '已切换回多智能体引导式学习模式', 'success');
    };

    const fillInput = (text) => {
        inputText.value = text;
    };

    const shouldTriggerVisualGuideGeneration = (prompt) => {
        const text = String(prompt || '').trim();
        if (!text) return false;
        const compactText = text.replace(/\s+/g, '');
        const questionPattern = /[?？]|(什么|为什么|为何|如何|怎么|怎样|讲解|解释|说明|请问|帮我|学习|制定|生成|画|图解|步骤|流程|原理|概念|架构|区别|对比|实现|分析)/;
        if (questionPattern.test(text)) return true;
        return compactText.length >= 18 && /(结构|算法|模型|系统|机制|场景|应用|关系|过程)/.test(text);
    };

    const visualGuideTypes = [
        { id: 'concept', label: '概念图', icon: 'ph-graph' },
        { id: 'steps', label: '步骤图', icon: 'ph-list-checks' }
    ];

    const getVisualGuideTypeMeta = (type) => visualGuideTypes.find(item => item.id === type) || visualGuideTypes[0];
    const canOpenVisualGuideViewer = computed(() => (
        visualGuideStatus.value !== 'generating' &&
        Boolean(visualGuidePrompt.value.trim()) &&
        Boolean(
            visualGuideImage.value?.renderedSvg ||
            visualGuideImage.value?.treeText ||
            visualGuideImage.value?.mermaid ||
            visualGuideImage.value?.svg ||
            visualGuideImage.value?.backgroundUrl ||
            visualGuideImage.value?.backgroundBase64 ||
            visualGuideImage.value?.imageUrl ||
            visualGuideImage.value?.imageBase64 ||
            visualGuide.value?.title
        )
    ));

    const generateVisualGuide = async (prompt = visualGuidePrompt.value, options = {}) => {
        const { reason = 'tab-demand', force = false } = options;
        const cleanPrompt = (prompt || visualGuidePrompt.value || '').trim();
        if (!cleanPrompt) return;

        // 1. 判断是否是新问题。如果 prompt 与缓存的当前问题不同，说明是全新查询，清空缓存并更新当前问题
        if (cleanPrompt !== visualGuidePrompt.value || reason === 'student-question') {
            visualGuideCache.value = {};
            visualGuidePrompt.value = cleanPrompt;
        }

        // 2. 检查是否有当前类型的缓存数据
        if (!force && visualGuideCache.value[visualGuideType.value]) {
            const cached = visualGuideCache.value[visualGuideType.value];
            visualGuideImage.value = cached.image;
            visualGuide.value = cached.guide;
            visualGuideStatus.value = cached.status;
            return;
        }

        const requestId = ++visualGuideRequestId;
        const sessionId = getSessionId();
        visualGuideStatus.value = 'generating';
        visualGuideImage.value = null;
        showVisualGuideViewer.value = false;

        let backendGuide = null;
        const architectureAgent = getArchitectureGuideAgent();
        try {
            backendGuide = await requestVisualGuideImage({
                prompt: cleanPrompt,
                guideType: visualGuideType.value,
                sessionId,
                imageModel: getVisualGuideAgent()?.model,
                textModel: architectureAgent?.model,
                architectureAgent
            });
        } catch (error) {
            console.info('[Mira] Visual guide backend unavailable, using local sketch mode.', error);
        }

        if (requestId !== visualGuideRequestId) return;

        const localGuide = createLocalVisualGuide(cleanPrompt, visualGuideType.value);
        const resolvedGuide = resolveVisualGuideState({ localGuide, backendGuide });
        const renderedImage = await renderArchitectureGuide(resolvedGuide.image);
        if (requestId !== visualGuideRequestId) return;

        visualGuideImage.value = renderedImage;
        visualGuide.value = resolvedGuide.guide;
        visualGuideStatus.value = resolvedGuide.status;

        // 3. 将本次成功渲染生成的数据放入缓存中
        visualGuideCache.value[visualGuideType.value] = {
            image: renderedImage,
            guide: resolvedGuide.guide,
            status: resolvedGuide.status
        };

        visualGuideHistory.value.unshift({
            id: Date.now(),
            type: visualGuideType.value,
            prompt: cleanPrompt,
            title: visualGuide.value.title,
            source: resolvedGuide.historySource,
            generatedAt: visualGuide.value.generatedAt
        });
        visualGuideHistory.value = visualGuideHistory.value.slice(0, 3);

        window.dispatchEvent?.(new CustomEvent('agent-log', {
            detail: {
                agent: 'Mira',
                content: resolvedGuide.logMessage,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            }
        }));
    };

    const switchVisualGuideType = (type) => {
        if (visualGuideType.value === type) return;
        visualGuideType.value = type;
        if (!visualGuidePrompt.value.trim()) return;
        generateVisualGuide(visualGuidePrompt.value, { reason: 'tab-demand' });
    };

    const regenerateVisualGuide = () => {
        if (!visualGuidePrompt.value.trim()) return;
        delete visualGuideCache.value[visualGuideType.value];
        generateVisualGuide(visualGuidePrompt.value, { reason: 'regenerate', force: true });
    };

    const openVisualGuideViewer = () => {
        if (!canOpenVisualGuideViewer.value) return;
        showVisualGuideViewer.value = true;
    };

    const closeVisualGuideViewer = () => {
        showVisualGuideViewer.value = false;
    };

    const selectVisualGuideHistory = (item) => {
        if (!item) return;
        visualGuideType.value = item.type;
        generateVisualGuide(item.prompt, { reason: 'history' });
    };

    const renderArchitectureGuide = async (image) => {
        if (!image?.mermaid || !window.mermaid?.render) return image;

        try {
            // 自动为未包裹双引号的节点文案加上双引号，防止尖括号(<br>)、空格等字符引发 Mermaid 语法解析报错
            const cleanedMermaid = image.mermaid.replace(/([a-zA-Z0-9_-]+)\[([^"\]\n\r]+)\]/g, '$1["$2"]');

            const renderId = `visual-guide-architecture-${Date.now()}-${Math.random().toString(36).slice(2)}`;
            const { svg } = await window.mermaid.render(renderId, cleanedMermaid);
            return { ...image, mermaid: cleanedMermaid, renderedSvg: svg };
        } catch (error) {
            console.info('[Mira] Mermaid architecture render failed.', error);
            return { ...image, renderError: error?.message || String(error) };
        }
    };

    const downloadTextArtifact = (content, filename, type = 'text/plain;charset=utf-8') => {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    };

    const downloadVisualGuide = () => {
        if (!visualGuidePrompt.value.trim()) return;
        if (visualGuideImage.value?.renderedSvg) {
            downloadTextArtifact(
                visualGuideImage.value.renderedSvg,
                `${visualGuide.value.center || 'prof-x-architecture'}.svg`,
                'image/svg+xml;charset=utf-8'
            );
            return;
        }

        if (visualGuideImage.value?.mermaid) {
            downloadTextArtifact(
                visualGuideImage.value.mermaid,
                `${visualGuide.value.center || 'prof-x-architecture'}.mmd`
            );
            return;
        }

        if (visualGuideImage.value?.treeText) {
            downloadTextArtifact(
                visualGuideImage.value.treeText,
                `${visualGuide.value.center || 'prof-x-architecture'}.txt`
            );
            return;
        }

        if (visualGuideImage.value?.svg) {
            const blob = new Blob([visualGuideImage.value.svg], { type: 'image/svg+xml;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `${visualGuide.value.center || 'mira-guide'}.svg`;
            link.click();
            URL.revokeObjectURL(link.href);
            return;
        }

        if (visualGuideImage.value?.imageUrl || visualGuideImage.value?.imageBase64) {
            const link = document.createElement('a');
            link.href = visualGuideImage.value.imageUrl || visualGuideImage.value.imageBase64;
            link.download = `${visualGuide.value.center || 'mira-guide'}.png`;
            link.click();
            return;
        }

        const svg = visualGuideImage.value?.svg || buildVisualGuideSvg(visualGuide.value, visualGuideType.value);
        const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${visualGuide.value.center || 'mira-guide'}.svg`;
        link.click();
        URL.revokeObjectURL(url);
    };

    const legacyTriggerFileInput = (isLoggedIn) => {
        if (!isLoggedIn) return showToast('请先登录后上传个人资料', 'error');
        const fileInput = document.getElementById('realFileInput');
        if (fileInput) fileInput.click();
    };

    const legacyHandleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        showToast('正在上传并解析文档...', 'success');
        const formData = new FormData();
        formData.append('user_id', getSessionId());
        formData.append('file', file);

        try {
            const resJson = await userApi.uploadFile(formData);

            if (resJson && resJson.status === 'success') {
                files.value.unshift({ id: Date.now(), name: file.name, size: (file.size / 1024 / 1024).toFixed(2) + ' MB' });
                showToast('私有知识库更新成功！', 'success');
            } else {
                showToast('上传失败: ' + (resJson?.message || '未知错误'), 'error');
            }
        } catch (err) {
            showToast('网络错误，上传失败', 'error');
        }
        event.target.value = '';
    };

    const triggerFileInput = (isLoggedIn) => {
        if (!isLoggedIn) return showToast('请先登录后上传个人资料', 'error');
        if (!selectedRepositoryId.value) return showToast('请先创建或选择一个仓库', 'error');
        const fileInput = document.getElementById('realFileInput');
        if (fileInput) fileInput.click();
    };

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        if (!isSupportedKnowledgeFile(file)) {
            showToast('当前知识库仅支持上传 PDF 文件', 'error');
            event.target.value = '';
            return;
        }
        if (!selectedRepositoryId.value) {
            showToast('请先选择仓库', 'error');
            event.target.value = '';
            return;
        }

        knowledgeUploading.value = true;
        showToast('正在上传并同步 RAGFlow...', 'success');
        try {
            await knowledgeApi.uploadDocument({
                userId: getSessionId(),
                repositoryId: selectedRepositoryId.value,
                file
            });
            await loadKnowledgeRepositories();
            showToast('文件已进入个人知识库', 'success');
        } catch (error) {
            showToast(error.message || '上传失败', 'error');
        } finally {
            knowledgeUploading.value = false;
            event.target.value = '';
        }
    };

    const deleteKnowledgeDocument = async (file) => {
        if (!file?.id) return;
        const confirmed = window.confirm(`确认从知识库删除「${file.name}」？`);
        if (!confirmed) return;

        knowledgeDeletingId.value = file.id;
        try {
            await knowledgeApi.deleteDocument({ userId: getSessionId(), documentId: file.id });
            await loadKnowledgeRepositories();
            showToast('文件已从 RAGFlow 同步删除', 'success');
        } catch (error) {
            showToast(error.message || '删除失败', 'error');
        } finally {
            knowledgeDeletingId.value = '';
        }
    };

    const deleteKnowledgeRepository = async (repo) => {
        if (!repo?.id) return;
        const confirmed = window.confirm(`确认删除资料仓库「${repo.name}」及其中的 ${repo.document_count || 0} 个文件？`);
        if (!confirmed) return;

        knowledgeRepositoryDeletingId.value = repo.id;
        try {
            await knowledgeApi.deleteRepository({ userId: getSessionId(), repositoryId: repo.id });
            if (selectedRepositoryId.value === repo.id) {
                selectedRepositoryId.value = '';
            }
            await loadKnowledgeRepositories();
            showToast('资料仓库已删除', 'success');
        } catch (error) {
            showToast(error.message || '仓库删除失败', 'error');
        } finally {
            knowledgeRepositoryDeletingId.value = '';
        }
    };

    loadKnowledgeRepositories();
    loadCourseKnowledgeBases();

    const sendMessage = () => {
        const sessionId = getSessionId();
        const prompt = inputText.value;
        if (!prompt.trim() || thinkingAgent.value) return;
        if (agentMode.value !== 'rag' && shouldTriggerVisualGuideGeneration(prompt)) {
            visualGuideType.value = 'concept';
            generateVisualGuide(prompt, { reason: 'student-question', force: true });
        }
        const repositoryId = agentMode.value === 'rag' ? selectedRepositoryId.value : '';
        const courseDatasetIds = agentMode.value === 'rag' ? [...selectedCourseDatasetIds.value] : null;
        sendStreamingMessage(prompt, messages, thinkingAgent, inputText, chatContainer, forceRAG.value, sessionId, agentMode.value, repositoryId, getActiveChatAgent(), courseDatasetIds, (modelId) => {
            showToast(`模型 ${modelId} 当前不可用，请更换模型`, 'error');
        });
    };

    watch(messages, (newVal) => {
        localStorage.setItem(getChatStorageKey(getSessionId(), agentMode.value), JSON.stringify(newVal));
    }, { deep: true });

    watch(() => currentUser.value?.username, () => {
        loadChatHistory(agentMode.value);
        selectedRepositoryId.value = localStorage.getItem(`knowledge_repo:${getSessionId()}`) || '';
        loadKnowledgeRepositories();
    });

    return {
        inputText,
        chatContainer,
        thinkingAgent,
        forceRAG,
        agentMode,
        historyLoading,
        historyError,
        showHistoryPanel,
        highlightedMessageId,
        historyPanelTitle: () => getHistoryPanelTitle(agentMode.value),
        messages,
        files,
        knowledgeRepositories,
        selectedRepositoryId,
        selectedRepository,
        newRepositoryName,
        knowledgeLoading,
        knowledgeUploading,
        knowledgeDeletingId,
        knowledgeRepositoryDeletingId,
        knowledgeDatasetId,
        courseKnowledgeBases,
        selectedCourseDatasetIds,
        loadCourseKnowledgeBases,
        toggleCourseDataset,
        loadKnowledgeRepositories,
        selectKnowledgeRepository,
        createKnowledgeRepository,
        deleteKnowledgeRepository,
        deleteKnowledgeDocument,
        getKnowledgeFileStatusLabel,
        visualGuidePrompt,
        visualGuideType,
        visualGuideTypes,
        visualGuideStatus,
        visualGuide,
        visualGuideImage,
        visualGuideHistory,
        showVisualGuideViewer,
        canOpenVisualGuideViewer,
        toggleRAG,
        setAgentMode,
        loadChatHistory,
        openHistoryPanel,
        closeHistoryPanel,
        jumpToHistoryMessage,
        deleteHistoryMessage,
        clearChatHistory,
        fillInput,
        getVisualGuideTypeMeta,
        getVisualGuideSourceLabel: () => visualGuidePrompt.value.trim() ? getVisualGuideSourceLabel(visualGuideImage.value) : '等待输入',
        getActiveChatAgent,
        switchVisualGuideType,
        regenerateVisualGuide,
        selectVisualGuideHistory,
        openVisualGuideViewer,
        closeVisualGuideViewer,
        downloadVisualGuide,
        triggerFileInput,
        handleFileUpload,
        sendMessage,
        parsedHtmlCache
    };
}
