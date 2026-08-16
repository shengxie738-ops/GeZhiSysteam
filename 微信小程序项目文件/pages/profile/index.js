// pages/profile/index.js
const { request, uploadFile, BASE_URL } = require('../../utils/request.js');

Page({
  data: {
    user: {},
    profile: {
      knowledge: 50,
      pace: 50
    },
    mistakeCount: 0,
    levelText: '致知境',
    loading: false
  },

  onShow() {
    // 设置 tabBar 选中索引 (我的为索引 3)
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 3
      });
    }

    const user = wx.getStorageSync('user');
    if (!user) {
      wx.reLaunch({
        url: '/pages/login/index'
      });
      return;
    }

    // 拼装完整的头像路径
    if (user.avatar_url && !user.avatar_url.startsWith('http')) {
      user.avatar_url = `${BASE_URL}${user.avatar_url}`;
    }

    this.setData({
      user: user
    });

    this.loadProfile(user.username);
    this.loadMistakeCount(user.username);
  },

  loadProfile(userId) {
    request({
      url: `/profile/${userId}`
    }).then(res => {
      if (res && res.user_id) {
        this.setData({
          profile: res
        }, () => {
          this.calculateLevel();
        });
      }
    }).catch(err => {
      console.error('加载画像失败:', err);
    });
  },

  loadMistakeCount(userId) {
    request({
      url: `/exams/student/${userId}/mistakes`
    }).then(res => {
      if (res && res.mistakes) {
        this.setData({
          mistakeCount: res.mistakes.length
        });
      }
    }).catch(err => {
      console.error('加载错题数失败:', err);
    });
  },

  calculateLevel() {
    const k = this.data.profile.knowledge || 50;
    let levelText = '致知境';
    if (k >= 90) {
      levelText = '穷理境';
    } else if (k >= 80) {
      levelText = '致知境';
    } else if (k >= 70) {
      levelText = '诚意境';
    } else if (k >= 60) {
      levelText = '正心境';
    } else {
      levelText = '格物境';
    }
    this.setData({ levelText });
  },

  uploadAvatar() {
    const that = this;
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success(res) {
        const tempFilePath = res.tempFilePaths[0];
        wx.showLoading({ title: '头像上传中...' });
        
        uploadFile({
          targetPath: '/user/upload_avatar',
          filePath: tempFilePath,
          fileName: 'avatar.jpg',
          formData: {
            username: that.data.user.username
          }
        }).then(data => {
          wx.hideLoading();
          const avatarUrl = data && ((data.data && (data.data.avatarUrl || data.data.avatar_url)) || data.avatarUrl || data.avatar_url);
          if (avatarUrl) {
            const user = wx.getStorageSync('user');
            user.avatar_url = avatarUrl;
            user.avatarUrl = avatarUrl;
            wx.setStorageSync('user', user);

            that.setData({
              'user.avatar_url': avatarUrl.indexOf('http') === 0 ? avatarUrl : `${BASE_URL}${avatarUrl}`
            });
            wx.showToast({ title: '头像更新成功', icon: 'success' });
          } else {
            wx.showToast({ title: (data && (data.detail || data.message)) || '上传失败', icon: 'none' });
          }
        }).catch(() => {
          wx.hideLoading();
          wx.showToast({ title: '网络连接失败', icon: 'none' });
        });
      }
    });
  },

  handleLogout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出当前账号吗？',
      success(res) {
        if (res.confirm) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
          wx.showToast({ title: '已退出登录', icon: 'success' });
          setTimeout(() => {
            wx.reLaunch({
              url: '/pages/splash/index'
            });
          }, 1000);
        }
      }
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

  navToMistakes() {
    wx.navigateTo({
      url: '/pages/mistake-book/index'
    });
  },

  navToChat() {
    wx.switchTab({
      url: '/pages/chat/index'
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
  }
})
