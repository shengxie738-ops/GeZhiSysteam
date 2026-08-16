const { request } = require('../../utils/request.js');
Page({
  data: {
    quizzes: [],
    loading: false,
    error: false,
    tagFilter: '',
    difficultyFilter: 0,
    tags: ['数据结构', '算法', '高等数学', '操作系统', '计算机网络'],
    difficulties: [{ label: '全部', value: 0 }, { label: '入门', value: 1 }, { label: '基础', value: 2 }, { label: '进阶', value: 3 }, { label: '挑战', value: 4 }, { label: '极限', value: 5 }]
  },
  onLoad(options) {
    if (options && options.tag) this.setData({ tagFilter: decodeURIComponent(options.tag) });
    this.loadQuizzes();
  },
  onPullDownRefresh() {
    this.loadQuizzes(() => wx.stopPullDownRefresh());
  },
  loadQuizzes(cb) {
    this.setData({ loading: true, error: false });
    const qs = [];
    if (this.data.tagFilter) qs.push('tag=' + encodeURIComponent(this.data.tagFilter));
    if (this.data.difficultyFilter) qs.push('difficulty=' + this.data.difficultyFilter);
    const query = qs.length > 0 ? '?' + qs.join('&') : '';
    request({ url: '/evaluator/quizzes' + query }).then(res => {
      const items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
      this.setData({ quizzes: items, loading: false });
    }).catch(err => {
      this.setData({ error: true, loading: false });
    }).finally(() => { if (cb) cb(); });
  },
  onTagTap(e) {
    const tag = e.currentTarget.dataset.tag || '';
    this.setData({ tagFilter: tag === this.data.tagFilter ? '' : tag });
    this.loadQuizzes();
  },
  onDifficultyTap(e) {
    const val = parseInt(e.currentTarget.dataset.value) || 0;
    this.setData({ difficultyFilter: val === this.data.difficultyFilter ? 0 : val });
    this.loadQuizzes();
  },
  onStartQuiz(e) {
    const quizId = e.currentTarget.dataset.id;
    if (!quizId) return;
    wx.showLoading({ title: '创建测评...' });
    request({ url: '/evaluator/attempts', method: 'POST', data: { quizId } }).then(res => {
      wx.hideLoading();
      const attemptId = res && res.id;
      if (attemptId) {
        wx.navigateTo({ url: '/pages/evaluator-detail/index?attemptId=' + attemptId });
      }
    }).catch(err => {
      wx.hideLoading();
      wx.showToast({ title: err.message || '创建测评失败', icon: 'none' });
    });
  },
  onGoKnowledge() {
    wx.navigateTo({ url: '/pages/knowledge-base/index' });
  },
  onRetryTap() { this.loadQuizzes(); }
});
