const { request } = require('../../utils/request.js');

Page({
  data: {
    homeworkList: [],
    loading: false,
    error: false
  },

  onLoad() {
    this.loadHomework();
  },

  onPullDownRefresh() {
    this.loadHomework(() => wx.stopPullDownRefresh());
  },

  loadHomework(cb) {
    const user = wx.getStorageSync('user');
    if (!user) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }

    this.setData({ loading: true, error: false });
    request({ url: '/homework/student/list' }).then(res => {
      const list = Array.isArray(res) ? res : (res && res.items ? res.items : []);
      const homeworkList = list.map(item => ({
        ...item,
        subjectName: item.subjectName || item.subject || item.courseName || '课程任务',
        questionCount: Array.isArray(item.questions) ? item.questions.length : (item.questionCount || 0),
        statusText: item.status === 'submitted' || item.submitted ? '已提交' : '待提交',
        statusClass: item.status === 'submitted' || item.submitted ? 'tag-bamboo' : (item.urgent ? 'tag-warning' : 'tag-seal')
      }));
      this.setData({ homeworkList, loading: false });
    }).catch(err => {
      console.error('加载作业列表失败:', err);
      this.setData({ loading: false, error: true });
    }).finally(() => {
      if (cb) cb();
    });
  },

  viewDetail(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) return;
    wx.navigateTo({ url: '/pages/homework-detail/index?id=' + encodeURIComponent(id) });
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  onRetryTap() {
    this.loadHomework();
  }
});
