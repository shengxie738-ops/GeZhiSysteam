// utils/journal-service.js
// 学纪事件服务：统一管理学习事件的写入与读取

const { request } = require('./request.js');

const EVENT_TYPES = {
  CHAT: 'chat',
  RAG: 'rag',
  MISTAKE: 'mistake',
  QUIZ: 'quiz',
  KNOWLEDGE_UPLOAD: 'knowledge_upload',
  FORUM: 'forum',
  PROFILE_UPDATE: 'profile_update'
};

/**
 * 创建学纪事件
 * @param {Object} event - { type, title, summary?, relatedIds?, tags?, scoreDelta? }
 */
function createEvent(event) {
  if (!event || !event.type || !event.title) return Promise.resolve(null);
  return request({
    url: '/journal/events',
    method: 'POST',
    data: event
  }).catch(err => {
    console.error('写入学纪事件失败:', err);
    // 降级：写入本地缓存
    cacheEventLocally(event);
    return null;
  });
}

/**
 * 获取学纪事件列表（分页）
 * @param {Object} params - { cursor?, limit? }
 */
function getEvents(params) {
  const qs = [];
  if (params && params.cursor) qs.push('cursor=' + params.cursor);
  if (params && params.limit) qs.push('limit=' + params.limit);
  const query = qs.length > 0 ? '?' + qs.join('&') : '';
  return request({
    url: '/journal/events' + query
  });
}

/**
 * 按日期获取学纪事件
 * @param {string} date - YYYY-MM-DD
 */
function getEventsByDay(date) {
  return request({
    url: '/journal/events/day?date=' + date
  });
}

/**
 * 获取最近 N 条事件（供首页展示）
 */
function getRecentEvents(limit) {
  return getEvents({ limit: limit || 5 });
}

/**
 * 获取画像概要
 */
function getProfileSummary() {
  return request({
    url: '/profile/summary'
  });
}

/**
 * 获取画像趋势
 * @param {string} range - '7d' | '30d'
 */
function getProfileTrends(range) {
  return request({
    url: '/profile/trends?range=' + (range || '7d')
  });
}

/**
 * 获取知识地图
 * @param {string} rootId
 * @param {number} depth
 */
function getKnowledgeMap(rootId, depth) {
  const qs = [];
  if (rootId) qs.push('rootId=' + rootId);
  if (depth) qs.push('depth=' + depth);
  const query = qs.length > 0 ? '?' + qs.join('&') : '';
  return request({
    url: '/profile/knowledge-map' + query
  });
}

// 本地缓存降级
function cacheEventLocally(event) {
  try {
    const cacheKey = 'local_journal_events';
    const events = wx.getStorageSync(cacheKey) || [];
    events.unshift({
      ...event,
      id: 'local_' + Date.now(),
      createdAt: new Date().toISOString()
    });
    // 最多保留50条
    wx.setStorageSync(cacheKey, events.slice(0, 50));
  } catch (e) {
    console.error('本地缓存学纪事件失败:', e);
  }
}

function getLocalEvents() {
  try {
    return wx.getStorageSync('local_journal_events') || [];
  } catch (e) {
    return [];
  }
}

module.exports = {
  EVENT_TYPES,
  createEvent,
  getEvents,
  getEventsByDay,
  getRecentEvents,
  getProfileSummary,
  getProfileTrends,
  getKnowledgeMap,
  getLocalEvents
};
