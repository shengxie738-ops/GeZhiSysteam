const { request } = require('../../utils/request.js');
const { createEvent, EVENT_TYPES } = require('../../utils/journal-service.js');
Page({
  data: {
    attempt: null,
    questions: [],
    currentIndex: 0,
    answers: {},
    loading: false,
    submitting: false,
    error: false
  },
  onLoad(options) {
    if (options.attemptId) this.loadAttempt(options.attemptId);
  },
  loadAttempt(id) {
    this.setData({ loading: true, error: false });
    request({ url: '/evaluator/attempts/' + id }).then(res => {
      const questions = res.questions || [];
      this.setData({ attempt: res, questions, loading: false });
    }).catch(() => {
      this.setData({ error: true, loading: false });
    });
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
  onPrev() {
    if (this.data.currentIndex > 0) {
      this.setData({ currentIndex: this.data.currentIndex - 1 });
    }
  },
  onNext() {
    if (this.data.currentIndex < this.data.questions.length - 1) {
      this.setData({ currentIndex: this.data.currentIndex + 1 });
    }
  },
  onSubmit() {
    const unanswered = this.data.questions.filter(q => !this.data.answers[q.id]);
    if (unanswered.length > 0) {
      wx.showModal({
        title: '提示',
        content: '还有 ' + unanswered.length + ' 题未作答，确定提交吗？',
        success: (res) => {
          if (res.confirm) this.doSubmit();
        }
      });
    } else {
      this.doSubmit();
    }
  },
  doSubmit() {
    this.setData({ submitting: true });
    const attemptId = this.data.attempt.id;
    request({
      url: '/evaluator/attempts/' + attemptId + '/submit',
      method: 'POST',
      data: { answers: this.data.answers }
    }).then(res => {
      createEvent({
        type: EVENT_TYPES.QUIZ,
        title: '完成测评: ' + (this.data.attempt.title || '未知测评'),
        summary: '提交了 ' + this.data.questions.length + ' 道题',
        relatedIds: [attemptId],
        tags: this.data.attempt.topicTags || []
      });
      wx.redirectTo({ url: '/pages/evaluator-result/index?attemptId=' + attemptId });
    }).catch(err => {
      this.setData({ submitting: false });
      wx.showToast({ title: err.message || '提交失败', icon: 'none' });
    });
  },
  onRetryTap() {
    if (this.data.attempt) this.loadAttempt(this.data.attempt.id);
  }
});
