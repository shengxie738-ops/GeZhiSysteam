// pages/splash/index.js
Page({
  onLoad() {
    // 延迟 1.5 秒自动检测是否已经登录
    this.timer = setTimeout(() => {
      const token = wx.getStorageSync('token');
      const user = wx.getStorageSync('user');
      if (token && user) {
        wx.switchTab({
          url: '/pages/home/index'
        });
      } else {
        wx.navigateTo({
          url: '/pages/login/index'
        });
      }
    }, 1500);
  },

  onUnload() {
    if (this.timer) {
      clearTimeout(this.timer);
    }
  },

  goToLogin() {
    if (this.timer) {
      clearTimeout(this.timer);
    }
    wx.navigateTo({
      url: '/pages/login/index'
    });
  }
})
