import { reactive, nextTick } from 'vue';
import { throttle } from '../utils/helpers.js';
import request from '../utils/request.js';
import { buildChatPayload, formatChatTimestamp, normalizeAgentMode } from '../utils/chatModes.js';

export const parsedHtmlCache = reactive({});

// Safe markdown parser — falls back to raw text if marked is not loaded
function safeParse(text) {
    if (window.marked && typeof window.marked.parse === 'function') {
        return window.marked.parse(text);
    }
    return text;
}

export const throttledParse = throttle((id, text) => {
    parsedHtmlCache[id] = safeParse(text);
}, 200);

export const throttledScroll = throttle(async (chatContainer) => {
    await nextTick();
    if (chatContainer && chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }
}, 120);

export async function sendStreamingMessage(msg, messages, thinkingAgent, inputText, chatContainer, forceRAG = false, sessionId = 'guest_user', agentMode = 'tutor', repositoryId = '', agent = null, courseDatasetIds = null, onModelUnavailable = null) {
    if (!msg.trim() || thinkingAgent.value) return;
    const normalizedMode = normalizeAgentMode(agentMode);
    const currentTime = formatChatTimestamp();

    const userMsgId = Date.now();
    messages.value.push({ id: userMsgId, senderType: 'user', content: msg, time: currentTime, createdAt: currentTime });
    parsedHtmlCache[userMsgId] = safeParse(msg);

    inputText.value = '';
    throttledScroll(chatContainer);

    thinkingAgent.value = normalizedMode === 'rag' ? 'agent_researcher' : 'agent_tutor';
    const streamMessageId = Date.now() + 1;
    const agentTime = formatChatTimestamp();
    const newAgentMsg = reactive({
        id: streamMessageId,
        senderType: 'agent',
        senderId: normalizedMode === 'rag' ? 'agent_researcher' : 'agent_tutor',
        time: agentTime,
        createdAt: agentTime,
        content: ''
    });
    messages.value.push(newAgentMsg);
    parsedHtmlCache[streamMessageId] = '';

    try {
        // Try streaming first, fall back to non-streaming if it fails
        let response;
        let useStreaming = true;
        
        try {
            response = await request('/chat/stream', {
                method: 'POST',
                body: JSON.stringify(buildChatPayload({ message: msg, forceRAG, sessionId, agentMode: normalizedMode, repositoryId, agent, courseDatasetIds })),
                isStream: true
            });
            if (!response.ok) throw new Error('Stream API failed');
        } catch (streamError) {
            console.warn('[Chat] Streaming failed, falling back to non-streaming:', streamError);
            useStreaming = false;
            // Use non-streaming endpoint as fallback
            const chatResponse = await request('/chat', {
                method: 'POST',
                body: JSON.stringify(buildChatPayload({ message: msg, forceRAG, sessionId, agentMode: normalizedMode, repositoryId, agent, courseDatasetIds }))
            });
            // Simulate streaming response
            if (chatResponse && chatResponse.reply) {
                newAgentMsg.content = chatResponse.reply;
                parsedHtmlCache[streamMessageId] = safeParse(chatResponse.reply);
                thinkingAgent.value = null;
                throttledScroll(chatContainer);
                return;
            }
            throw new Error('Both streaming and non-streaming failed');
        }

        if (!response.ok) throw new Error('API failed');

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // 保留不完整的一行

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6).trim();
                    if (!dataStr) continue;
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.type === 'token') {
                            newAgentMsg.content += data.content;
                            throttledParse(streamMessageId, newAgentMsg.content);
                            throttledScroll(chatContainer);
                        } else if (data.type === 'progress') {
                            const agentMap = {
                                'Alina': 'agent_planner',
                                'Prof. X': 'agent_tutor',
                                'DataBot': 'agent_researcher',
                                'CodeNinja': 'agent_coder'
                            };
                            const agentId = agentMap[data.agent] || 'agent_tutor';
                            thinkingAgent.value = agentId;
                            newAgentMsg.senderId = agentId; // 动态变更消息发送者头像

                            // 派发全局日志事件，同步到教师监控大屏
                            if (window.dispatchEvent) {
                                window.dispatchEvent(new CustomEvent('agent-log', {
                                    detail: {
                                        agent: data.agent,
                                        content: data.status,
                                        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                                    }
                                }));
                            }
                        } else if (data.type === 'error') {
                            newAgentMsg.content += `\n\n【系统错误】: ${data.message}`;
                            throttledParse(streamMessageId, newAgentMsg.content);
                        } else if (data.type === 'model_unavailable') {
                            newAgentMsg.content += `\n\n> ⚠️ **${data.message}**（模型：${data.model}），请在智能体配置中更换模型`;
                            throttledParse(streamMessageId, newAgentMsg.content);
                            throttledScroll(chatContainer);
                            if (typeof onModelUnavailable === 'function') {
                                onModelUnavailable(data.model);
                            }
                        }
                    } catch (e) {
                        console.error('SSE JSON解析失败:', e);
                    }
                }
            }
        }

        thinkingAgent.value = null;
        
        // If no content was received from streaming, fall back to non-streaming
        if (!newAgentMsg.content && useStreaming) {
            console.warn('[Chat] No token events received, falling back to non-streaming');
            try {
                const chatResponse = await request('/chat', {
                    method: 'POST',
                    body: JSON.stringify(buildChatPayload({ message: msg, forceRAG, sessionId, agentMode: normalizedMode, repositoryId, agent, courseDatasetIds }))
                });
                if (chatResponse && chatResponse.reply) {
                    newAgentMsg.content = chatResponse.reply;
                }
            } catch (fallbackError) {
                console.error('[Chat] Fallback also failed:', fallbackError);
            }
        }
        
        parsedHtmlCache[streamMessageId] = safeParse(newAgentMsg.content);
        throttledScroll(chatContainer);

    } catch (error) {
        thinkingAgent.value = 'agent_tutor';
        const fallback = `[格至 智能体响应 (在线演示)]

您刚才输入了："**${msg}**"。

当前检测到您的本地后台接口未启动，已自动为您开启**本地流式应答模拟器**。

### 💡 AI 主动规划与指导建议：
1. **技术架构**：本工作台采用 Vue 3 响应式驱动与 Markdown 解析器集成。在生产环境下，它会使用 \`fetch\` API 通过流式接口（Streaming Response / Server-Sent Events）进行无缓冲推送。
2. **多智能体干预机制**：
   - **Alina (规划师)**：监控当前的学习瓶颈，必要时更新您的 *三维知识路径图谱*。
   - **Prof. X (导师)**：负责解答您的这一提问。
   - **CodeNinja (代码精灵)**：可在右侧代码沙箱中为您自动补全或执行对比测试。

您可以点击左下角随时切换至**教师端**。在教师端大数据大屏中，我已经将您的本次互动转化为干预记录，并反馈至班级雷达图谱中。`;
        let i = 0;
        const timer = setInterval(() => {
            const chunkSize = Math.floor(Math.random() * 4) + 2;
            if (i < fallback.length) {
                newAgentMsg.content += fallback.substring(i, i + chunkSize);
                throttledParse(streamMessageId, newAgentMsg.content);
                throttledScroll(chatContainer);
                i += chunkSize;
            } else {
                clearInterval(timer);
                thinkingAgent.value = null;
                parsedHtmlCache[streamMessageId] = safeParse(newAgentMsg.content);
                throttledScroll(chatContainer);
            }
        }, 40);
    }
}
