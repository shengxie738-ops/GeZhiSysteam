import assert from 'node:assert/strict';

import {
  buildChatPayload,
  getHistoryPanelTitle,
  getChatStorageKey,
  shouldShowHistoryButton,
  mapHistoryRecordToMessage,
  normalizeAgentMode,
  sanitizeStoredMessagesForMode,
  stripReferenceSourceBlock,
} from '../js/utils/chatModes.js';

assert.equal(normalizeAgentMode('rag'), 'rag');
assert.equal(normalizeAgentMode('unknown'), 'tutor');
assert.equal(getChatStorageKey('alice', 'tutor'), 'messages:alice:tutor');
assert.equal(getChatStorageKey('alice', 'rag'), 'messages:alice:rag');
assert.equal(shouldShowHistoryButton('rag'), true);
assert.equal(shouldShowHistoryButton('tutor'), true);
assert.equal(getHistoryPanelTitle('rag'), '知识库检索历史记录');
assert.equal(getHistoryPanelTitle('tutor'), '引导式学习历史记录');

assert.deepEqual(
  buildChatPayload({
    message: 'hello',
    forceRAG: true,
    sessionId: 'alice',
    agentMode: 'rag',
    repositoryId: 'repo_a',
    agent: {
      id: 'agent_researcher',
      model: 'qwen3.6-plus',
      prompt: '你负责在本地知识库中进行 RAG 查询。',
    },
  }),
  {
    message: 'hello',
    force_rag: true,
    sessionId: 'alice',
    agent_mode: 'rag',
    repository_id: 'repo_a',
    agent_id: 'agent_researcher',
    agent_model: 'qwen3.6-plus',
    agent_prompt: '你负责在本地知识库中进行 RAG 查询。',
  },
);

assert.deepEqual(
  mapHistoryRecordToMessage({
    id: 12,
    role: 'assistant',
    sender_id: 'agent_researcher',
    content: 'answer',
    created_at: '2026-06-30 23:35:25',
  }),
  {
    id: 'db-12',
    senderType: 'agent',
    senderId: 'agent_researcher',
    content: 'answer',
    time: '2026-06-30 23:35:25',
    createdAt: '2026-06-30 23:35:25',
  },
);

assert.equal(
  stripReferenceSourceBlock('今天我们聊队列。\n\n【知识库引用来源】:\n- 2-线性表.pdf\n- 4-队列.pdf'),
  '今天我们聊队列。',
);

assert.equal(
  mapHistoryRecordToMessage({
    id: 13,
    role: 'assistant',
    sender_id: 'agent_tutor',
    agent_mode: 'tutor',
    content: '正文\n\n【知识库引用来源】:\n- 2-线性表.pdf\n- 3-栈.pdf',
    created_at: '2026-07-01 16:18:59',
  }).content,
  '正文',
);

assert.equal(
  mapHistoryRecordToMessage({
    id: 14,
    role: 'assistant',
    sender_id: 'agent_researcher',
    agent_mode: 'rag',
    content: '答案\n\n【知识库引用来源】:\n- 2-线性表.pdf',
    created_at: '2026-07-01 16:19:00',
  }).content,
  '答案\n\n【知识库引用来源】:\n- 2-线性表.pdf',
);

assert.deepEqual(
  sanitizeStoredMessagesForMode([
    { id: 1, content: '旧回答\n\n【知识库引用来源】:\n- 2-线性表.pdf' },
  ], 'tutor'),
  [
    { id: 1, content: '旧回答' },
  ],
);

assert.deepEqual(
  sanitizeStoredMessagesForMode([
    { id: 1, content: '检索回答\n\n【知识库引用来源】:\n- 2-线性表.pdf' },
  ], 'rag'),
  [
    { id: 1, content: '检索回答\n\n【知识库引用来源】:\n- 2-线性表.pdf' },
  ],
);

console.log('chatModes tests passed');
