// pages/course/index.js
const { request } = require('../../utils/request.js');

Page({
  data: {
    allPosts: [],
    posts: [],
    activeCategory: 'all',
    loading: false
  },

  onShow() {
    // 设置 tabBar 选中索引 (学术空间为索引 1)
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 1
      });
    }

    this.loadPosts();
  },

  loadPosts() {
    this.setData({ loading: true });
    request({
      url: '/forum/posts'
    }).then(res => {
      this.setData({ loading: false });
      const postsData = res && res.items ? res.items : (Array.isArray(res) ? res : []);
      if (postsData.length > 0) {
        // 对发帖时间做人性化清洗
        const cleaned = postsData.map(post => {
          let simpleTime = '更早';
          if (post.createdAt) {
            try {
              const dt = new Date(post.createdAt);
              const now = new Date();
              if (dt.toDateString() === now.toDateString()) {
                simpleTime = `今日 ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
              } else {
                simpleTime = `${dt.getMonth() + 1}-${dt.getDate()}`;
              }
            } catch (e) {}
          }
          return {
            ...post,
            simpleTime
          };
        });

        // 默认按创建时间倒序排列
        cleaned.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

        this.setData({
          allPosts: cleaned
        }, () => {
          this.filterPosts();
        });
      }
    }).catch(err => {
      this.setData({ loading: false });
      console.error('加载论坛帖子失败:', err);
    });
  },

  switchCategory(e) {
    const category = e.currentTarget.dataset.category;
    this.setData({
      activeCategory: category
    }, () => {
      this.filterPosts();
    });
  },

  filterPosts() {
    const { allPosts, activeCategory } = this.data;
    if (activeCategory === 'all') {
      this.setData({ posts: allPosts });
    } else {
      const filtered = allPosts.filter(item => item.category === activeCategory);
      this.setData({ posts: filtered });
    }
  },

  viewPostDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/forum-detail/index?id=${id}`
    });
  }
})
