Page({
  data: {
    event: null,
    loading: true,
    error: false
  },

  onLoad(options) {
    if (options.id) {
      this.loadEvent(options.id);
    }
  },

  loadEvent(id) {
    var that = this;
    var journalService = require('../../utils/journal-service.js');
    journalService.getEvents({ limit: 100 }).then(function (res) {
      var items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
      var found = null;
      for (var i = 0; i < items.length; i++) {
        if (items[i].id === id) {
          found = items[i];
          break;
        }
      }
      if (found) {
        that.setData({ event: found, loading: false });
      } else {
        that.setData({ error: true, loading: false });
      }
    }).catch(function () {
      that.setData({ error: true, loading: false });
    });
  },

  goToRelated(e) {
    var type = e.currentTarget.dataset.type;
    var related = e.currentTarget.dataset.related || '';
    if (type === 'chat' || type === 'rag') {
      wx.switchTab({ url: '/pages/chat/index' });
    } else if (type === 'mistake') {
      wx.navigateTo({ url: '/pages/mistake-book/index' });
    } else if (type === 'quiz') {
      wx.navigateTo({ url: '/pages/evaluator-result/index?attemptId=' + related });
    }
  },

  goBack() {
    wx.navigateBack();
  }
});
