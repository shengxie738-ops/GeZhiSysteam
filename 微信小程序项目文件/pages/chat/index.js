// pages/chat/index.js
const { request, uploadFile } = require('../../utils/request.js');
const { createEvent, EVENT_TYPES } = require('../../utils/journal-service.js');

Page({
  data: {
    messages: [],
    inputValue: '',
    agentMode: 'tutor', // tutor | rag
    thinking: false,
    thinkingAgent: 'Alina',
    lastMessageId: 'msg-welcome'
  },

  onShow() {
    // 设置 tabBar 选中索引 (AI导师为索引 2)
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 2
      });
    }

    const user = wx.getStorageSync('user');
    if (!user) {
      wx.reLaunch({
        url: '/pages/login/index'
      });
      return;
    }

    // 每次进入页面时加载对应的会话历史
    this.loadHistory(user.username, this.data.agentMode);
  },

  loadHistory(userId, mode) {
    request({
      url: `/chat/history?session_id=${userId}&agent_mode=${mode}&limit=50`
    }).then(res => {
      const historyData = res && res.items ? res.items : (Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : []));
      if (historyData.length > 0) {
        // 后端聊天历史记录结构为 { id, role, content, sender_id, created_at }
        // 映射为小程序前端格式
        const list = historyData.map(item => {
          let senderName = '智能导师';
          let senderType = 'agent_planner';
          let senderAvatar = '☖';

          if (item.sender_id === 'agent_tutor' || item.sender_id === 'agent_researcher') {
            senderName = mode === 'rag' ? 'DataBot [专属知识库]' : 'Alina [主规划师]';
            senderAvatar = mode === 'rag' ? '📂' : '☖';
          } else if (item.sender_id === 'agent_ninja') {
            senderName = 'CodeNinja [沙箱专家]';
            senderType = 'agent_ninja';
            senderAvatar = '🥷';
          } else if (item.sender_id === 'agent_profx') {
            senderName = 'Prof. X [概念导师]';
            senderType = 'agent_profx';
            senderAvatar = '🎓';
          } else if (item.sender_id === 'agent_databot') {
            senderName = 'DataBot [课件专家]';
            senderType = 'agent_databot';
            senderAvatar = '📂';
          }

          // 清理引用文本并提取出单独的引用展示栏
          const { content, references } = this.parseReferences(item.content);

          return {
            id: item.id || Date.now() + Math.random(),
            role: item.role,
            content: content,
            references: references,
            senderName,
            senderType,
            senderAvatar
          };
        });

        this.setData({
          messages: list
        }, () => {
          this.scrollToBottom();
        });
      }
    }).catch(err => {
      console.error('加载会话历史失败:', err);
    });
  },

  parseReferences(content) {
    if (!content) return { content: '', references: [] };
    
    // 后端引用格式一般为：\n\n【知识库引用来源】:\n- xxxx.pdf
    const pattern = /\n*【(?:数据结构)?知识库引用来源】[:：][\s\S]*/;
    const match = content.match(pattern);
    
    let cleanedContent = content;
    let references = [];
    
    if (match) {
      cleanedContent = content.replace(pattern, '').trim();
      const refBlock = match[0];
      const lines = refBlock.split('\n');
      lines.forEach(line => {
        if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
          references.push(line.replace(/^[-•]\s*/, '').trim());
        }
      });
    }
    
    return {
      content: cleanedContent,
      references
    };
  },

  switchAgentMode(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setAgentMode(mode);
  },

  toggleAgentMode() {
    const mode = this.data.agentMode === 'rag' ? 'tutor' : 'rag';
    this.setAgentMode(mode);
  },

  setAgentMode(mode) {
    if (mode === this.data.agentMode) return;

    this.setData({
      agentMode: mode
    });

    const user = wx.getStorageSync('user');
    if (user) {
      this.loadHistory(user.username, mode);
    }
    
    wx.showToast({
      title: mode === 'rag' ? '已启用专属 RAG 知识库检索' : '已启用多智能体协同辅导',
      icon: 'none'
    });
  },

  onInput(e) {
    this.setData({
      inputValue: e.detail.value
    });
  },

  sendMessage() {
    const { inputValue, agentMode, thinking } = this.data;
    if (thinking || !inputValue.trim()) return;

    const user = wx.getStorageSync('user');
    if (!user) return;

    const userMsgId = 'user-' + Date.now();
    const userMsg = {
      id: userMsgId,
      role: 'user',
      content: inputValue.trim()
    };

    // 先在前端 append 用户的气泡并开启思考提示
    const messages = [...this.data.messages, userMsg];
    
    this.setData({
      messages,
      inputValue: '',
      thinking: true,
      thinkingAgent: agentMode === 'rag' ? 'DataBot' : 'Alina',
      lastMessageId: 'msg-thinking'
    }, () => {
      this.scrollToBottom();
    });

    // 发起与后端 API /api/chat 的对话交互
    request({
      url: '/chat',
      method: 'POST',
      data: {
        message: userMsg.content,
        agent_mode: agentMode,
        sessionId: user.username,
        thread_id: user.username
      }
    }).then(res => {
      // 方案A返回解包后为 { reply, references, suggestedQuestions }
      const replyText = res.reply || '智能助教暂时无法回答。';
      const parsed = this.parseReferences(replyText);
      const content = parsed.content;
      const references = res.references && res.references.length ? res.references : parsed.references;

      let senderName = agentMode === 'rag' ? 'DataBot [专属知识库]' : 'Alina [主规划师]';
      let senderType = 'agent_planner';
      let senderAvatar = agentMode === 'rag' ? '📂' : '☖';

      // 提取回复开头的标签，识别具体的协同助教
      if (replyText.includes('【系统提示：大模型连接失败')) {
        senderName = 'DataBot [课件检索]';
        senderType = 'agent_databot';
        senderAvatar = '📂';
      }

      const agentMsg = {
        id: 'agent-' + Date.now(),
        role: 'assistant',
        content: content,
        references: references,
        senderName,
        senderType,
        senderAvatar
      };

      this.setData({
        messages: [...this.data.messages, agentMsg],
        thinking: false,
        lastMessageId: 'msg-' + agentMsg.id
      }, () => {
        this.scrollToBottom();
        // 写入学纪事件
        createEvent({
          type: agentMode === 'rag' ? EVENT_TYPES.RAG : EVENT_TYPES.CHAT,
          title: 'AI问答: ' + (userMsg.content.length > 20 ? userMsg.content.slice(0, 20) + '...' : userMsg.content),
          summary: content.length > 50 ? content.slice(0, 50) + '...' : content,
          tags: []
        });
      });
    }).catch(err => {
      this.setData({ thinking: false });
      wx.showToast({
        title: err.message || '导师连接超时',
        icon: 'none'
      });
    });
  },

  uploadMessageFile() {
    const that = this;
    const user = wx.getStorageSync('user');
    if (!user) return;

    // 小程序特有：直接选择微信中收到的聊天文件进行上传向量化
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'doc', 'docx', 'txt'],
      success(res) {
        const file = res.tempFiles[0];
        wx.showLoading({ title: '课件解析向量化中...' });

        uploadFile({
          targetPath: '/user/upload',
          filePath: file.path,
          fileName: file.name,
          formData: {
            user_id: user.username
          }
        }).then(data => {
          wx.hideLoading();
          if (data && (data.status === 'success' || data.dataset_id || data.data || data.id)) {
            // 上传向量化成功后，在前端渲染一条系统消息
            const systemMsg = {
              id: 'sys-' + Date.now(),
              role: 'assistant',
              content: `📢 专属课件《${file.name}》已上传成功并向量化解析完毕！已自动为您切换到【RAG课件检索模式】。您现在可以直接针对此文档的内容进行提问了。`,
              senderName: '系统通知',
              senderType: 'agent_databot',
              senderAvatar: '📂'
            };

            that.setData({
              agentMode: 'rag',
              messages: [...that.data.messages, systemMsg],
              lastMessageId: 'msg-' + systemMsg.id
            }, () => {
              that.scrollToBottom();
            });

            wx.showToast({ title: '课件向量化成功', icon: 'success' });
          } else {
            wx.showToast({ title: (data && data.message) || '课件处理失败', icon: 'none' });
          }
        }).catch(() => {
          wx.hideLoading();
          wx.showToast({ title: '上传网络失败', icon: 'none' });
        });
      }
    });
  },

  onSuggestTap(e) {
    const question = e.currentTarget.dataset.question;
    if (question) {
      this.setData({ inputValue: question }, () => {
        this.sendMessage();
      });
    }
  },

  scrollToBottom() {
    const list = this.data.messages;
    if (list.length > 0) {
      const last = list[list.length - 1];
      this.setData({
        lastMessageId: 'msg-' + last.id
      });
    }
  }
})
