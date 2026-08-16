export const CHAT_AGENT_MODES = {
    tutor: {
        id: 'tutor',
        label: '引导式学习',
        defaultAgentId: 'agent_tutor'
    },
    rag: {
        id: 'rag',
        label: '知识库检索',
        defaultAgentId: 'agent_researcher'
    }
};

export function normalizeAgentMode(mode) {
    return mode === 'rag' ? 'rag' : 'tutor';
}

export function getChatStorageKey(sessionId = 'guest_user', agentMode = 'tutor') {
    const userId = sessionId || 'guest_user';
    return `messages:${userId}:${normalizeAgentMode(agentMode)}`;
}

export function shouldShowHistoryButton(agentMode = 'tutor') {
    return ['tutor', 'rag'].includes(normalizeAgentMode(agentMode));
}

export function getHistoryPanelTitle(agentMode = 'tutor') {
    return normalizeAgentMode(agentMode) === 'rag' ? '知识库检索历史记录' : '引导式学习历史记录';
}

export function buildChatPayload({ message, forceRAG = false, sessionId = 'guest_user', agentMode = 'tutor', repositoryId = '', agent = null, courseDatasetIds = null }) {
    const normalizedMode = normalizeAgentMode(agentMode);
    const payload = {
        message,
        force_rag: forceRAG || normalizedMode === 'rag',
        sessionId,
        agent_mode: normalizedMode,
        agent_id: agent?.id,
        agent_model: agent?.model,
        agent_prompt: agent?.prompt
    };
    if (repositoryId) {
        payload.repository_id = repositoryId;
    }
    if (courseDatasetIds && Array.isArray(courseDatasetIds) && courseDatasetIds.length > 0) {
        payload.course_dataset_ids = courseDatasetIds;
    }
    Object.keys(payload).forEach(key => payload[key] === undefined && delete payload[key]);
    return payload;
}

export function formatChatTimestamp(date = new Date()) {
    return new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    }).format(date).replaceAll('/', '-');
}

const REFERENCE_SOURCE_PATTERN = /\n{0,2}【(?:数据结构)?知识库引用来源】[:：][ \t]*(?:\n[ \t]*[-•][ \t]*[^\n]+)*/g;

export function stripReferenceSourceBlock(text = '') {
    return String(text || '').replace(REFERENCE_SOURCE_PATTERN, '').trim();
}

export function sanitizeMessageContentForMode(content = '', agentMode = 'tutor') {
    const rawContent = content || '';
    return normalizeAgentMode(agentMode) === 'rag' ? rawContent : stripReferenceSourceBlock(rawContent);
}

export function sanitizeStoredMessagesForMode(messages = [], agentMode = 'tutor') {
    if (!Array.isArray(messages)) return [];
    return messages.map(message => {
        if (!message || typeof message !== 'object') return message;
        return {
            ...message,
            content: sanitizeMessageContentForMode(message.content, agentMode)
        };
    });
}

export function mapHistoryRecordToMessage(record) {
    const role = record?.role || 'assistant';
    const createdAt = record?.created_at || '';
    const agentMode = normalizeAgentMode(record?.agent_mode);
    const rawContent = record?.content || '';
    const content = sanitizeMessageContentForMode(rawContent, agentMode);
    return {
        id: `db-${record?.id}`,
        senderType: role === 'user' ? 'user' : 'agent',
        senderId: role === 'user' ? undefined : (record?.sender_id || 'agent_tutor'),
        content,
        time: createdAt,
        createdAt
    };
}
