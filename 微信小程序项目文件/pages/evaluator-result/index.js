const { request } = require('../../utils/request.js');
Page({
  data: {
    result: null,
    loading: false,
    error: false
  },
  onLoad(options) {
    if (options.attemptId) this.loadResult(options.attemptId);
  },
  loadResult(id) {
    this.setData({ loading: true, error: false });
    request({ url: '/evaluator/attempts/' + id + '/result' }).then(res => {
      const total = res.totalQuestions || (res.questions ? res.questions.length : 0);
      const correct = res.correctCount || 0;
      const result = {
        ...res,
        correctRate: total ? Math.round(correct / total * 100) : 0,
        questions: res.questions || []
      };
      this.setData({ result, loading: false });
    }).catch(() => {
      this.setData({ error: true, loading: false });
    });
  },
  addToMistakes(e) {
    const qid = e.currentTarget.dataset.qid;
    const question = e.currentTarget.dataset.question;
    const answer = e.currentTarget.dataset.answer;
    wx.showLoading({ title: '加入错题本...' });
    request({
      url: '/exams/mistakes',
      method: 'POST',
      data: { question, answer, source: 'quiz', quizId: this.data.result.quizId }
    }).then(() => {
      wx.hideLoading();
      wx.showToast({ title: '已加入错题本', icon: 'success' });
    }).catch(() => {
      wx.hideLoading();
      wx.showToast({ title: '加入失败', icon: 'none' });
    });
  },
  askAI(e) {
    const question = e.currentTarget.dataset.question || '';
    wx.setStorageSync('pendingQuestion', question);
    wx.switchTab({ url: '/pages/chat/index' });
  },
  goToMistakes() {
    wx.navigateTo({ url: '/pages/mistake-book/index' });
  },
  backToList() {
    wx.navigateBack({ delta: 2 });
  },
  onRetryTap() {
    if (this.data.result) this.loadResult(this.data.result.attemptId || this.data.result.id);
  }
});
