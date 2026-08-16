Component({
  data: {
    selected: 0,
    list: [
      {
        pagePath: "/pages/home/index",
        text: "首页",
        icon: "⌂"
      },
      {
        pagePath: "/pages/course/index",
        text: "学术空间",
        icon: "☰"
      },
      {
        pagePath: "/pages/chat/index",
        text: "AI导师",
        icon: "◎"
      },
      {
        pagePath: "/pages/profile/index",
        text: "我的",
        icon: "⊙"
      }
    ]
  },
  methods: {
    switchTab(e) {
      const data = e.currentTarget.dataset
      const url = data.path
      wx.switchTab({ url })
      this.setData({
        selected: data.index
      })
    }
  }
})
