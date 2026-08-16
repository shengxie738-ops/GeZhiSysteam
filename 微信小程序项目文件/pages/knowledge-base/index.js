// pages/knowledge-base/index.js
const { request, uploadFile } = require('../../utils/request.js');
const { createEvent, EVENT_TYPES } = require('../../utils/journal-service.js');

Page({
  data: {
    repositories: [],
    allDocuments: [],
    documents: [],
    activeRepoId: '',
    showFolderDialog: false,
    newFolderName: '',
    loading: false
  },

  onShow() {
    const user = wx.getStorageSync('user');
    if (!user) {
      wx.reLaunch({
        url: '/pages/login/index'
      });
      return;
    }

    this.loadKnowledge(user.username);
  },

  loadKnowledge(userId) {
    this.setData({ loading: true });
    wx.showLoading({ title: '拉取数据中...' });

    request({
      url: `/user/knowledge?user_id=${userId}`
    }).then(res => {
      wx.hideLoading();
      this.setData({ loading: false });

      if (res && Array.isArray(res.repositories)) {
        // 数据适配
        const repos = res.repositories;
        const embeddedDocs = repos.reduce((list, repo) => {
          const repoDocs = Array.isArray(repo.documents) ? repo.documents : [];
          return list.concat(repoDocs.map(doc => ({
            ...doc,
            repository_id: doc.repository_id || doc.repositoryId || repo.id
          })));
        }, []);
        const docs = res.documents || embeddedDocs;

        // 将文件大小转换为 KB 展现
        const formattedDocs = docs.map(doc => ({
          ...doc,
          sizeKb: doc.size ? Math.round(doc.size / 1024) : 0
        }));

        this.setData({
          repositories: repos,
          allDocuments: formattedDocs
        });

        // 默认选择第一个分类文件夹
        if (repos.length > 0 && !this.data.activeRepoId) {
          this.setData({
            activeRepoId: repos[0].id
          });
        }
        
        this.filterDocuments();
      }
    }).catch(err => {
      wx.hideLoading();
      this.setData({ loading: false });
      console.error('加载专属知识库失败:', err);
    });
  },

  switchRepository(e) {
    const id = e.currentTarget.dataset.id;
    this.setData({
      activeRepoId: id
    }, () => {
      this.filterDocuments();
    });
  },

  filterDocuments() {
    const { allDocuments, activeRepoId } = this.data;
    const filtered = allDocuments.filter(item => String(item.repository_id) === String(activeRepoId));
    this.setData({
      documents: filtered
    });
  },

  goBack() {
    wx.navigateBack({
      delta: 1
    });
  },

  showCreateFolder() {
    this.setData({
      showFolderDialog: true,
      newFolderName: ''
    });
  },

  closeCreateFolder() {
    this.setData({
      showFolderDialog: false
    });
  },

  onFolderNameInput(e) {
    this.setData({
      newFolderName: e.detail.value
    });
  },

  submitCreateFolder() {
    const { newFolderName } = this.data;
    if (!newFolderName.trim()) return;

    const user = wx.getStorageSync('user');
    if (!user) return;

    wx.showLoading({ title: '新建分类中...' });

    request({
      url: '/user/knowledge/repositories',
      method: 'POST',
      data: {
        user_id: user.username,
        name: newFolderName.trim()
      }
    }).then(res => {
      wx.hideLoading();
      this.setData({ showFolderDialog: false });
      wx.showToast({ title: '分类新建成功', icon: 'success' });
      this.loadKnowledge(user.username);
    }).catch(err => {
      wx.hideLoading();
      wx.showToast({ title: err.message || '新建失败', icon: 'none' });
    });
  },

  deleteDocument(e) {
    const id = e.currentTarget.dataset.id;
    const name = e.currentTarget.dataset.name;
    const user = wx.getStorageSync('user');
    if (!user) return;

    const that = this;
    wx.showModal({
      title: '删除确认',
      content: `确定从专属课件库中移除《${name}》吗？这在 PC 端也会同步删除。`,
      success(modalRes) {
        if (modalRes.confirm) {
          wx.showLoading({ title: '正在移除...' });
          request({
            url: `/user/knowledge/documents/${id}?user_id=${user.username}`,
            method: 'DELETE'
          }).then(res => {
            wx.hideLoading();
            wx.showToast({ title: '课件移除成功', icon: 'success' });
            that.loadKnowledge(user.username);
          }).catch(err => {
            wx.hideLoading();
            wx.showToast({ title: err.message || '移除失败', icon: 'none' });
          });
        }
      }
    });
  },

  uploadDocument() {
    const { activeRepoId } = this.data;
    if (!activeRepoId) {
      wx.showToast({ title: '请先选择或新建一个课件分类', icon: 'none' });
      return;
    }

    const user = wx.getStorageSync('user');
    if (!user) return;

    const that = this;
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'doc', 'docx', 'txt'],
      success(res) {
        const file = res.tempFiles[0];
        wx.showLoading({ title: '上传并向量化中...' });

        uploadFile({
          targetPath: '/user/knowledge/upload',
          filePath: file.path,
          fileName: file.name,
          formData: {
            user_id: user.username,
            repository_id: activeRepoId
          }
        }).then(data => {
          wx.hideLoading();
          if (data && (data.status === 'success' || data.data || data.id || data.document_id)) {
            wx.showToast({ title: '课件向量化就绪', icon: 'success' });
            that.loadKnowledge(user.username);
            createEvent({
              type: EVENT_TYPES.KNOWLEDGE_UPLOAD,
              title: '上传课件: ' + (file.name || '未知文件'),
              summary: '课件已上传并向量化完成，可用于AI问答',
              tags: []
            });
          } else {
            wx.showToast({ title: (data && data.message) || '上传解析失败', icon: 'none' });
          }
        }).catch(() => {
          wx.hideLoading();
          wx.showToast({ title: '文件上传网络失败', icon: 'none' });
        });
      }
    });
  },

  preventBubble() {
    // 阻止事件冒泡
  }
})
