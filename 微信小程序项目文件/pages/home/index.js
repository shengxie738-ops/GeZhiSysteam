// pages/home/index.js
const { request } = require('../../utils/request.js');
const journalService = require('../../utils/journal-service.js');

Page({
  data: {
    profile: {
      knowledge: 50,
      cognitive: '渐进理解型',
      pace: 50,
      goal: '掌握核心数据结构与算法'
    },
    usernameDisplay: '同学',
    greetingText: '穷理致知 · 伴学相长',
    nudges: [],
    hasNewNudge: false,
    showNudgeModal: false,
    recentEvents: [],
    dashboard: {
      pendingCount: 0,
      submittedCount: 0,
      homeworkList: []
    }
  },

  onShow() {
    // 设置 tabBar 选中索引
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 0
      });
    }

    const user = wx.getStorageSync('user');
    if (!user) {
      wx.reLaunch({
        url: '/pages/login/index'
      });
      return;
    }

    this.setData({
      usernameDisplay: user.real_name || user.username || '同学'
    });

    this.setGreeting();
    this.loadStudentProfile(user.username);
    this.loadDashboard(user.username);
    this.loadNudges(user.username);
    this.loadRecentEvents();
  },

  setGreeting() {
    const hour = new Date().getHours();
    let greetingText = '晨光正好 · 宜读书';
    if (hour >= 12 && hour < 18) {
      greetingText = '午后小憩 · 宜格物';
    } else if (hour >= 18) {
      greetingText = '暮色沉沉 · 宜温故';
    }
    this.setData({ greetingText });
  },

  loadStudentProfile(userId) {
    return request({
      url: `/profile/${userId}`
    }).then(res => {
      // res 即为 StudentProfile 数据模型
      if (res && res.user_id) {
        this.setData({
          profile: res
        });
      }
    }).catch(err => {
      console.error('加载学情画像失败:', err);
    });
  },

  loadDashboard(userId) {
    return request({
      url: `/dashboard/student/${userId}`
    }).then(res => {
      const homeworkList = Array.isArray(res.homeworkList) ? res.homeworkList : [];
      this.setData({
        dashboard: {
          pendingCount: res.pendingCount || homeworkList.filter(item => item.status !== 'submitted' && !item.submitted).length,
          submittedCount: res.submittedCount || homeworkList.filter(item => item.status === 'submitted' || item.submitted).length,
          homeworkList: homeworkList.slice(0, 3).map(item => ({
            ...item,
            statusText: item.status === 'submitted' || item.submitted ? '已提交' : '待提交',
            subjectName: item.subjectName || item.subject || item.courseName || '课程任务'
          }))
        }
      });
    }).catch(err => {
      console.error('加载学生仪表盘失败:', err);
    });
  },

  loadNudges(userId) {
    // 拉取 PC 端发送的干预与提醒记录
    return request({
      url: '/analytics/interactions'
    }).then(res => {
      const interactions = res && res.items ? res.items : (Array.isArray(res) ? res : []);
      if (interactions.length > 0) {
        // 过滤出针对当前学生、类型为 nudge 的未读/运行中的干预任务
        // 也可以从 json_store 中过滤 studentId == userId 
        const studentNudges = interactions.filter(item => {
          const studentIds = Array.isArray(item.studentIds) ? item.studentIds.map(String) : [];
          const isTarget = item.targetLabel === 'all' || 
                           item.studentId === userId || 
                           studentIds.includes(String(userId)) ||
                           (item.payload && item.payload.studentId === userId);
          const isActive = !item.status ||
                           item.status === 'running' ||
                           item.status === 'pending' ||
                           item.unreadCount > 0 ||
                           item.pendingCount > 0;
          return item.type === 'nudge' && isTarget && isActive;
        });

        this.setData({
          nudges: studentNudges,
          hasNewNudge: studentNudges.length > 0
        });
      }
    }).catch(err => {
      console.error('拉取干预消息失败:', err);
    });
  },

  refreshProfile() {
    const user = wx.getStorageSync('user');
    if (user) {
      wx.showLoading({ title: '同步数据中...' });
      Promise.all([
        this.loadStudentProfile(user.username),
        this.loadDashboard(user.username),
        this.loadNudges(user.username)
      ]).then(() => {
        wx.hideLoading();
        wx.showToast({ title: '学情同步成功', icon: 'success' });
      }).catch(() => wx.hideLoading());
    }
  },

  loadRecentEvents() {
    journalService.getRecentEvents(3).then(res => {
      const items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
      this.setData({ recentEvents: items.slice(0, 3) });
    }).catch(() => {
      // 降级：使用本地缓存
      const local = journalService.getLocalEvents();
      if (local.length > 0) {
        this.setData({ recentEvents: local.slice(0, 3) });
      }
    });
  },

  showNudges() {
    this.setData({
      showNudgeModal: true,
      hasNewNudge: false // 点击后清除红点
    });
  },

  closeNudgeModal() {
    this.setData({
      showNudgeModal: false
    });
  },

  preventBubble() {
    // 阻止冒泡
  },

  // 导航方法
  navToForum() {
    wx.switchTab({
      url: '/pages/course/index'
    });
  },

  navToChat() {
    wx.switchTab({
      url: '/pages/chat/index'
    });
  },

  navToMistakes() {
    wx.navigateTo({
      url: '/pages/mistake-book/index'
    });
  },

  navToKnowledge() {
    wx.navigateTo({
      url: '/pages/knowledge-base/index'
    });
  },

  navToHomework() {
    wx.navigateTo({
      url: '/pages/homework/index'
    });
  },

  goToProfileDetail() {
    wx.switchTab({
      url: '/pages/profile/index'
    });
  },

  navToJournal() {
    wx.navigateTo({
      url: '/pages/journal/index'
    });
  },

  navToPortrait() {
    wx.navigateTo({
      url: '/pages/portrait/index'
    });
  },

  navToEvaluator() {
    wx.navigateTo({
      url: '/pages/evaluator/index'
    });
  },

  onEventTap(e) {
    const id = e.currentTarget.dataset.id;
    const type = e.currentTarget.dataset.type;
    if (type === 'chat' || type === 'rag') {
      wx.switchTab({ url: '/pages/chat/index' });
    } else if (type === 'mistake') {
      wx.navigateTo({ url: '/pages/mistake-book/index' });
    } else if (type === 'quiz') {
      wx.navigateTo({ url: '/pages/evaluator-result/index?attemptId=' + (e.currentTarget.dataset.related || '') });
    } else {
      wx.navigateTo({ url: '/pages/journal-detail/index?id=' + id });
    }
  }
})
