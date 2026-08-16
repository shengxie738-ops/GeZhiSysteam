// pages/mistake-book/index.js
const { request } = require('../../utils/request.js');
const { createEvent, EVENT_TYPES } = require('../../utils/journal-service.js');

Page({
  data: {
    mistakes: [],
    summary: {
      total: 0,
      unresolved: 0,
      mastered: 0
    },
    activeDiagnosisId: '', // 当前展开 AI 诊断的错题 ID
    showTestModal: false,
    selectedOption: '',
    isCorrect: false,
    quizCategory: '数据结构链表操作',
    currentTestMistakeId: '',
    currentQuiz: {
      question: '单链表 L 变为空表的条件是什么？',
      options: [
        { key: 'A', text: 'L == NULL' },
        { key: 'B', text: 'L->next == NULL' },
        { key: 'C', text: 'L->next == L' },
        { key: 'D', text: 'L != NULL' }
      ],
      answer: 'B'
    }
  },

  onShow() {
    const user = wx.getStorageSync('user');
    if (!user) {
      wx.reLaunch({
        url: '/pages/login/index'
      });
      return;
    }

    this.loadMistakes(user.username);
  },

  loadMistakes(userId) {
    wx.showLoading({ title: '加载错题中...' });
    request({
      url: `/exams/student/${userId}/mistakes`
    }).then(res => {
      wx.hideLoading();
      if (res && Array.isArray(res.mistakes)) {
        this.setData({
          mistakes: res.mistakes,
          summary: {
            total: res.summary.total || 0,
            unresolved: res.summary.unresolved || 0,
            mastered: (res.summary.total - res.summary.unresolved) || 0
          }
        });
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('加载错题集失败:', err);
    });
  },

  goBack() {
    wx.navigateBack({
      delta: 1
    });
  },

  requestAiDiagnosis(e) {
    const id = e.currentTarget.dataset.id;
    const index = e.currentTarget.dataset.index;
    const item = this.data.mistakes[index];

    if (this.data.activeDiagnosisId === id) {
      this.setData({ activeDiagnosisId: '' });
      return;
    }

    // 如果该错题已经有诊断结果，直接展开
    if (item.aiAnalysis) {
      this.setData({ activeDiagnosisId: id });
      return;
    }

    wx.showLoading({ title: 'AI 诊断生成中...' });

    request({
      url: `/exams/mistakes/${id}/ai-analysis`,
      method: 'POST',
      data: {}
    }).then(res => {
      wx.hideLoading();
      if (res && res.diagnosis) {
        // 更新本地数组中该错题的诊断字段
        const mistakes = [...this.data.mistakes];
        mistakes[index].aiAnalysis = res;
        this.setData({
          mistakes,
          activeDiagnosisId: id
        });
      }
    }).catch(err => {
      wx.hideLoading();
      wx.showToast({ title: '诊断生成失败', icon: 'none' });
    });
  },

  toggleMastery(e) {
    const id = e.currentTarget.dataset.id;
    const mastered = e.currentTarget.dataset.mastered;
    const user = wx.getStorageSync('user');

    wx.showLoading({ title: '同步状态...' });

    request({
      url: `/exams/mistakes/${id}`,
      method: 'PATCH',
      data: {
        mastered: !mastered
      }
    }).then(res => {
      wx.hideLoading();
      wx.showToast({ title: !mastered ? '标记已掌握' : '已取消掌握', icon: 'success' });
      if (!mastered) {
        // 掌握时写入学纪事件
        const title = e.currentTarget.dataset.title || '错题';
        createEvent({
          type: EVENT_TYPES.MISTAKE,
          title: '掌握错题: ' + (title.length > 20 ? title.slice(0, 20) + '...' : title),
          summary: '已标记掌握，画像将同步更新',
          relatedIds: [id],
          tags: []
        });
      }
      if (user) {
        this.loadMistakes(user.username);
      }
    }).catch(err => {
      wx.hideLoading();
      wx.showToast({ title: '同步失败', icon: 'none' });
    });
  },

  startMiniTest(e) {
    const id = e.currentTarget.dataset.id;
    const title = e.currentTarget.dataset.title || '';
    
    // 根据题干关键字，动态切换自测题，使自测看起来更有针对性！
    let currentQuiz = {
      question: '单链表 L 变为空表的条件是什么？',
      options: [
        { key: 'A', text: 'L == NULL' },
        { key: 'B', text: 'L->next == NULL' },
        { key: 'C', text: 'L->next == L' },
        { key: 'D', text: 'L != NULL' }
      ],
      answer: 'B'
    };
    let quizCategory = '链表基本性质';

    if (title.includes('Vue') || title.includes('Proxy') || title.includes('响应式')) {
      currentQuiz = {
        question: '为什么在 Proxy 中要配合使用 Reflect？',
        options: [
          { key: 'A', text: 'Reflect 性能比直接操作属性更高' },
          { key: 'B', text: 'Reflect 的语法比 Proxy 更简洁' },
          { key: 'C', text: 'Reflect 可以确保 getter/setter 的 receiver 指向代理对象' },
          { key: 'D', text: '不使用 Reflect 会导致 Proxy 无法拦截 deleteProperty' }
        ],
        answer: 'C'
      };
      quizCategory = 'Vue3 响应式原理';
    } else if (title.includes('二叉树') || title.includes('树') || title.includes('遍历')) {
      currentQuiz = {
        question: '一棵完全二叉树有 501 个叶子节点，则其总节点数不可能为多少？',
        options: [
          { key: 'A', text: '1001' },
          { key: 'B', text: '1002' },
          { key: 'C', text: '1000' },
          { key: 'D', text: '都不可能' }
        ],
        answer: 'C'
      };
      quizCategory = '完全二叉树性质';
    }

    this.setData({
      currentTestMistakeId: id,
      quizCategory,
      currentQuiz,
      selectedOption: '',
      showTestModal: true
    });
  },

  selectOption(e) {
    if (this.data.selectedOption) return; // 只能选一次
    
    const key = e.currentTarget.dataset.key;
    const isCorrect = key === this.data.currentQuiz.answer;
    
    this.setData({
      selectedOption: key,
      isCorrect
    });

    const user = wx.getStorageSync('user');
    if (!user) return;

    // 1. 将自测正误结果记录回个人画像中，随学随新
    request({
      url: '/profile/record_test',
      method: 'POST',
      data: {
        user_id: user.username,
        problem_id: `mistake_test_${this.data.currentTestMistakeId}`,
        category: this.data.quizCategory,
        status: isCorrect ? 'passed' : 'failed',
        difficulty: 'Easy',
        error_msg: isCorrect ? null : `微信自测答错，选项为 ${key}`
      }
    }).then(res => {
      // 2. 如果自测正确，自动将其标记为已攻克！
      if (isCorrect) {
        return request({
          url: `/exams/mistakes/${this.data.currentTestMistakeId}`,
          method: 'PATCH',
          data: {
            mastered: true
          }
        });
      }
    }).then(() => {
      if (isCorrect) {
        this.loadMistakes(user.username);
      }
    }).catch(err => {
      console.error('自测联动画像更新失败:', err);
    });
  },

  closeTestModal() {
    this.setData({
      showTestModal: false
    });
  },

  preventBubble() {
    // 阻止事件冒泡
  }
})
