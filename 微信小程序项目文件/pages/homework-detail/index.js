const { request } = require('../../utils/request.js');

Page({
  data: {
    homeworkId: '',
    homework: null,
    questions: [],
    answers: {},
    loading: false,
    error: false,
    submitting: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ homeworkId: decodeURIComponent(options.id) });
      this.loadDetail(decodeURIComponent(options.id));
    }
  },

  loadDetail(id) {
    this.setData({ loading: true, error: false });
    request({ url: '/homework/' + encodeURIComponent(id) }).then(res => {
      const questions = Array.isArray(res.questions) ? res.questions.map((q, index) => this.normalizeQuestion(q, index)) : [];
      this.setData({
        homework: {
          ...res,
          subjectName: res.subjectName || res.subject || res.courseName || '课程任务',
          statusText: res.status === 'submitted' || res.submitted ? '已提交' : '待提交'
        },
        questions,
        answers: res.submittedAnswers || {},
        loading: false
      });
    }).catch(err => {
      console.error('加载作业详情失败:', err);
      this.setData({ loading: false, error: true });
    });
  },

  normalizeQuestion(question, index) {
    const type = question.type === 'blank' ? 'fill' : question.type;
    const rawOptions = Array.isArray(question.options) ? question.options : [];
    const options = rawOptions.map((option, optionIndex) => {
      if (typeof option === 'object') {
        return {
          key: option.key || String.fromCharCode(65 + optionIndex),
          text: option.text || option.label || option.value || ''
        };
      }
      return {
        key: String.fromCharCode(65 + optionIndex),
        text: option
      };
    });

    return {
      ...question,
      id: question.id || 'q' + (index + 1),
      type,
      content: question.content || question.title || question.desc || '未命名题目',
      options
    };
  },

  onOptionTap(e) {
    const qid = e.currentTarget.dataset.qid;
    const value = e.currentTarget.dataset.value;
    this.setData({ ['answers.' + qid]: value });
  },

  onInputAnswer(e) {
    const qid = e.currentTarget.dataset.qid;
    this.setData({ ['answers.' + qid]: e.detail.value });
  },

  onSubmit() {
    if (this.data.submitting || !this.data.homework) return;
    const unanswered = this.data.questions.filter(q => this.data.answers[q.id] === undefined || this.data.answers[q.id] === '');
    if (unanswered.length > 0) {
      wx.showModal({
        title: '确认提交',
        content: '还有 ' + unanswered.length + ' 题未作答，仍要提交吗？',
        success: (res) => {
          if (res.confirm) this.doSubmit();
        }
      });
      return;
    }
    this.doSubmit();
  },

  doSubmit() {
    const homeworkId = this.data.homeworkId;
    this.setData({ submitting: true });
    request({
      url: '/homework/' + encodeURIComponent(homeworkId) + '/submit',
      method: 'POST',
      data: {
        homeworkId,
        answers: this.data.answers
      }
    }).then(() => {
      wx.showToast({ title: '提交成功', icon: 'success' });
      this.setData({
        submitting: false,
        'homework.statusText': '已提交',
        'homework.status': 'submitted'
      });
    }).catch(err => {
      this.setData({ submitting: false });
      wx.showToast({ title: err.message || '提交失败', icon: 'none' });
    });
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  onRetryTap() {
    if (this.data.homeworkId) this.loadDetail(this.data.homeworkId);
  }
});
