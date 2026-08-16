const { getEvents, getLocalEvents } = require('../../utils/journal-service.js');

Page({
  data: {
    events: [],
    loading: false,
    loadingMore: false,
    error: false,
    errorMsg: '',
    cursor: '',
    hasMore: true,
    typeFilter: '',
    filterOptions: [
      { label: '全部', type: '' },
      { label: 'AI问答', type: 'chat' },
      { label: '错题训练', type: 'mistake' },
      { label: '测评', type: 'quiz' },
      { label: '资料上传', type: 'knowledge_upload' }
    ]
  },

  onLoad() {
    this.loadEvents(true);
  },

  onPullDownRefresh() {
    this.loadEvents(true, function () {
      wx.stopPullDownRefresh();
    });
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loadingMore) {
      this.loadEvents(false);
    }
  },

  loadEvents(refresh, cb) {
    var that = this;
    if (refresh) {
      that.setData({ loading: true, error: false, events: [], cursor: '', hasMore: true });
    } else {
      that.setData({ loadingMore: true });
    }
    var params = { limit: 20 };
    if (!refresh && that.data.cursor) params.cursor = that.data.cursor;
    if (that.data.typeFilter) params.type = that.data.typeFilter;

    getEvents(params).then(function (res) {
      var items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
      var merged = refresh ? items : that.data.events.concat(items);
      that.setData({
        events: merged,
        loading: false,
        loadingMore: false,
        cursor: (res && res.nextCursor) || '',
        hasMore: items.length >= 20
      });
    }).catch(function (err) {
      var local = getLocalEvents();
      if (local.length > 0 && refresh) {
        that.setData({ events: local, loading: false, loadingMore: false });
      } else {
        that.setData({
          error: true,
          errorMsg: (err && err.message) || '加载学纪失败',
          loading: false,
          loadingMore: false
        });
      }
    }).finally(function () {
      if (cb) cb();
    });
  },

  onFilterTap(e) {
    var type = e.currentTarget.dataset.type || '';
    this.setData({ typeFilter: type });
    this.loadEvents(true);
  },

  onEventTap(e) {
    var id = e.currentTarget.dataset.id;
    var type = e.currentTarget.dataset.type;
    var related = e.currentTarget.dataset.related || '';

    if (type === 'chat' || type === 'rag') {
      wx.switchTab({ url: '/pages/chat/index' });
    } else if (type === 'mistake') {
      wx.navigateTo({ url: '/pages/mistake-book/index' });
    } else if (type === 'quiz') {
      wx.navigateTo({ url: '/pages/evaluator-result/index?attemptId=' + related });
    } else if (type === 'knowledge_upload') {
      wx.navigateTo({ url: '/pages/knowledge-base/index' });
    } else {
      wx.navigateTo({ url: '/pages/journal-detail/index?id=' + id });
    }
  },

  onRetryTap() {
    this.loadEvents(true);
  },

  goToChat() {
    wx.switchTab({ url: '/pages/chat/index' });
  },

  goToQuiz() {
    wx.navigateTo({ url: '/pages/evaluator/index' });
  },

  goUpload() {
    wx.navigateTo({ url: '/pages/knowledge-base/index' });
  }
});
