Page({
  data: {
    loading: false,
    error: false
  },
  onLoad() {
    this.setData({ loading: false, error: false });
  },
  onPullDownRefresh() {
    wx.stopPullDownRefresh();
  },
  goToPortrait() {
    wx.navigateBack();
  },
  onRetryTap() {
    this.setData({ loading: false, error: false });
  }
});
