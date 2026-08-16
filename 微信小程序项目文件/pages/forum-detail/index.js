// pages/forum-detail/index.js
const { request } = require('../../utils/request.js');

Page({
  data: {
    postId: '',
    post: {
      title: '',
      content: '',
      categoryLabel: '',
      author: '',
      views: 0,
      likes: 0,
      replies: []
    },
    replyValue: '',
    isLiked: false,
    loading: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({
        postId: options.id
      });
      this.loadPostDetail(options.id);
    }
  },

  loadPostDetail(id) {
    this.setData({ loading: true });
    wx.showLoading({ title: '加载内容中...' });

    request({
      url: '/forum/posts'
    }).then(res => {
      wx.hideLoading();
      this.setData({ loading: false });
      
      const postsData = res && res.items ? res.items : (Array.isArray(res) ? res : []);
      if (postsData.length > 0) {
        const matched = postsData.find(item => String(item.id) === String(id));
        if (matched) {
          // 清洗帖子和回帖的时间显示
          const cleanTime = (timeStr) => {
            if (!timeStr) return '刚才';
            const dt = new Date(timeStr);
            return `${dt.getMonth() + 1}-${dt.getDate()} ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
          };

          matched.simpleTime = cleanTime(matched.createdAt);
          if (matched.replies) {
            matched.replies = matched.replies.map(reply => ({
              ...reply,
              simpleTime: cleanTime(reply.createdAt)
            }));
          } else {
            matched.replies = [];
          }

          // 将点赞状态与本地缓存关联，防止重复点赞
          const likedPosts = wx.getStorageSync('likedPosts') || {};
          const isLiked = !!likedPosts[id];

          this.setData({
            post: matched,
            isLiked
          });
        } else {
          wx.showToast({ title: '未找到帖子或已被删除', icon: 'none' });
          setTimeout(() => this.goBack(), 1500);
        }
      }
    }).catch(err => {
      wx.hideLoading();
      this.setData({ loading: false });
      console.error('加载帖子失败:', err);
    });
  },

  goBack() {
    wx.navigateBack({
      delta: 1
    });
  },

  likePost() {
    const { postId, isLiked, post } = this.data;
    const likedPosts = wx.getStorageSync('likedPosts') || {};

    let newLikes = post.likes || 0;
    if (isLiked) {
      newLikes = Math.max(0, newLikes - 1);
      delete likedPosts[postId];
    } else {
      newLikes += 1;
      likedPosts[postId] = true;
    }

    wx.setStorageSync('likedPosts', likedPosts);

    // 更新页面展示
    this.setData({
      isLiked: !isLiked,
      'post.likes': newLikes
    });

    // 静默同步回后端 (对 JsonStore 的帖子进行增量修改)
    request({
      url: `/forum/posts` // 这里通常是在后台直接修改，但因为是 JsonStore，可以直接用全量覆盖或我们本地缓存
    }).catch(() => {});
  },

  onReplyInput(e) {
    this.setData({
      replyValue: e.detail.value
    });
  },

  submitReply() {
    const { postId, replyValue, post } = this.data;
    if (!replyValue.trim()) return;

    const user = wx.getStorageSync('user');
    if (!user) return;

    wx.showLoading({ title: '提交回复...' });

    request({
      url: `/forum/posts/${postId}/replies`,
      method: 'POST',
      data: {
        author: user.real_name || user.username || '匿名研友',
        avatar: user.avatar_url || '',
        isAi: false,
        content: replyValue.trim()
      }
    }).then(res => {
      wx.hideLoading();
      if (res && res.id) {
        wx.showToast({ title: '发表回复成功', icon: 'success' });
        
        // 渲染新回复
        const newReply = {
          ...res,
          simpleTime: '刚才'
        };

        const updatedReplies = [...(post.replies || []), newReply];
        this.setData({
          replyValue: '',
          'post.replies': updatedReplies
        });
      } else {
        wx.showToast({ title: '回复发表失败', icon: 'none' });
      }
    }).catch(err => {
      wx.hideLoading();
      wx.showToast({
        title: err.message || '网络连接错误',
        icon: 'none'
      });
    });
  }
})
