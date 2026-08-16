const { request } = require('../../utils/request.js');
const journalService = require('../../utils/journal-service.js');
Page({
  data: {
    abilityProfile: null,
    dimensions: [],
    trends: [],
    trendRange: '7d',
    loading: false,
    error: false
  },
  onLoad() {
    this.loadAll();
  },
  onPullDownRefresh() {
    this.loadAll(() => wx.stopPullDownRefresh());
  },
  loadAll(cb) {
    this.setData({ loading: true, error: false });
    const user = wx.getStorageSync('user');
    if (!user) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    const userId = user.username || user.studentId || user.student_id;
    Promise.all([
      request({ url: '/analytics/students/me?user_id=' + encodeURIComponent(userId) }).catch(() => null),
      journalService.getProfileTrends(this.data.trendRange).catch(() => null)
    ]).then(([ability, trends]) => {
      this.setData({
        abilityProfile: ability,
        dimensions: this.buildDimensions(ability),
        trends: (trends && trends.knowledge) || [],
        loading: false
      });
    }).catch(() => {
      this.setData({ error: true, loading: false });
    }).finally(() => { if (cb) cb(); });
  },

  buildDimensions(ability) {
    const indicators = (ability && ability.radarIndicators) || [];
    const values = (ability && ability.radarValues) || [];
    const classValues = (ability && ability.classRadarValues) || [];
    const evidence = (ability && ability.radarEvidence) || {};

    return indicators.map((item, index) => {
      const name = item.name || '能力维度';
      const score = Number(values[index] || 0);
      const classScore = Number(classValues[index] || 0);
      const diff = score - classScore;
      const info = evidence[name] || {};
      let statusText = '接近均值';
      let statusClass = 'tag-dark';
      if (diff >= 8) {
        statusText = '领先 ' + diff + ' 分';
        statusClass = 'tag-bamboo';
      } else if (diff <= -8) {
        statusText = '低于 ' + Math.abs(diff) + ' 分';
        statusClass = 'tag-warning';
      }

      return {
        id: name + index,
        name,
        score,
        classScore,
        diff,
        statusText,
        statusClass,
        label: info.label || '暂无证据说明',
        source: info.source || '',
        sampleCount: info.sampleCount || 0
      };
    });
  },

  onRangeTap(e) {
    const range = e.currentTarget.dataset.range;
    this.setData({ trendRange: range });
    journalService.getProfileTrends(range).then(res => {
      this.setData({ trends: (res && res.knowledge) || [] });
    }).catch(() => {});
  },
  goToHomework() {
    wx.navigateTo({ url: '/pages/homework/index' });
  },
  goToChat() {
    wx.switchTab({ url: '/pages/chat/index' });
  },
  goToMistakes() {
    wx.navigateTo({ url: '/pages/mistake-book/index' });
  },
  onRetryTap() {
    this.loadAll();
  }
});
