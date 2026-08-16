// pages/login/index.js
const { request } = require('../../utils/request.js');

Page({
  data: {
    account: '',
    password: '',
    privacyAgreed: false,
    loading: false
  },

  onInputAccount(e) {
    this.setData({
      account: e.detail.value
    });
  },

  onInputPassword(e) {
    this.setData({
      password: e.detail.value
    });
  },

  togglePrivacyAgree() {
    this.setData({
      privacyAgreed: !this.data.privacyAgreed
    });
  },

  handleLogin() {
    const { account, password, privacyAgreed, loading } = this.data;
    if (loading) return;

    if (!account.trim()) {
      wx.showToast({
        title: '请输入学号或手机号',
        icon: 'none'
      });
      return;
    }

    if (!password) {
      wx.showToast({
        title: '请输入登录密码',
        icon: 'none'
      });
      return;
    }

    if (!privacyAgreed) {
      wx.showToast({
        title: '请先阅读并勾选用户协议与隐私政策',
        icon: 'none'
      });
      return;
    }

    this.setData({ loading: true });
    wx.showLoading({ title: '登录中...' });

    request({
      url: '/student/login',
      method: 'POST',
      data: {
        username: account.trim(),
        password: password,
        role: 'student'
      }
    }).then(res => {
      wx.hideLoading();
      this.setData({ loading: false });

      const authData = res && res.token ? res : (res && res.data ? res.data : null);
      if (authData && authData.token) {
        const user = normalizeUser(authData.user || {});
        wx.setStorageSync('token', authData.token);
        wx.setStorageSync('gezhi_token', authData.token);
        wx.setStorageSync('user', user);
        
        wx.showToast({
          title: '登录成功',
          icon: 'success',
          duration: 1000
        });

        setTimeout(() => {
          wx.switchTab({
            url: '/pages/home/index'
          });
        }, 1000);
      } else {
        wx.showToast({
          title: res.message || '登录失败，请检查账号密码',
          icon: 'none'
        });
      }
    }).catch(err => {
      wx.hideLoading();
      this.setData({ loading: false });
      wx.showToast({
        title: err.message || '网络请求错误',
        icon: 'none'
      });
    });
  }
})

function normalizeUser(user) {
  const username = user.username || user.studentId || user.student_id || user.mobile || '';
  const realName = user.realName || user.real_name || user.name || username;
  const studentId = user.studentId || user.student_id || username;
  const className = user.className || user.class_name || '';
  const avatarUrl = user.avatarUrl || user.avatar_url || '';

  return {
    ...user,
    username,
    realName,
    real_name: realName,
    studentId,
    student_id: studentId,
    className,
    class_name: className,
    avatarUrl,
    avatar_url: avatarUrl
  };
}
