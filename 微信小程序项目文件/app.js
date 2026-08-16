const { request, BASE_URL } = require('./utils/request.js');
const { CLOUD_ENV_ID } = require('./utils/config.js');

App({
  onLaunch() {
    if (!wx.cloud) {
      console.error('请使用 2.2.3 或以上基础库以使用云能力');
    } else {
      wx.cloud.init({
        env: CLOUD_ENV_ID || undefined,
        traceUser: true
      });
    }
    console.log('格至教育系统移动端启动成功');
  },
  globalData: {
    userInfo: null,
    token: null,
    nudgeCount: 0,
    hasNewNudge: false
  },
  // 方便子页面可以直接调用全局的 request
  request,
  BASE_URL
})
