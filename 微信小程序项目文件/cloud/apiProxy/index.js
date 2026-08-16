const cloud = require('wx-server-sdk');
const FormData = require('form-data');
const got = require('got');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const API_BASE = 'https://gezhisystem.com/api';
const TIMEOUT_MS = 45000;
const MAX_GET_RETRIES = 1;

const ROUTES = {
  'student/login': { method: 'POST', path: '/student/login' },
  'student/mobile-login': { method: 'POST', path: '/student/mobile-login' },
  'profile/get': { method: 'GET', path: null },
  'profile/summary': { method: 'GET', path: '/profile/summary' },
  'profile/trends': { method: 'GET', path: '/profile/trends' },
  'profile/knowledge-map': { method: 'GET', path: '/profile/knowledge-map' },
  'profile/record-test': { method: 'POST', path: '/profile/record_test' },
  'analytics/interactions': { method: 'GET', path: '/analytics/interactions' },
  'chat/history': { method: 'GET', path: '/chat/history' },
  'chat/send': { method: 'POST', path: '/chat' },
  'chat/stream': { method: 'POST', path: '/chat/stream' },
  'journal/create': { method: 'POST', path: '/journal/events' },
  'journal/list': { method: 'GET', path: '/journal/events' },
  'journal/day': { method: 'GET', path: '/journal/events/day' },
  'knowledge/list': { method: 'GET', path: '/user/knowledge' },
  'knowledge/create-repo': { method: 'POST', path: '/user/knowledge/repositories' },
  'knowledge/delete-doc': { method: 'DELETE', path: null },
  'knowledge/upload': { method: 'POST', path: '/user/knowledge/upload' },
  'user/upload': { method: 'POST', path: '/user/upload' },
  'user/upload-avatar': { method: 'POST', path: '/user/upload_avatar' },
  'mistakes/list': { method: 'GET', path: null },
  'mistakes/ai-analysis': { method: 'POST', path: null },
  'mistakes/update': { method: 'PATCH', path: null },
  'mistakes/create': { method: 'POST', path: '/exams/mistakes' },
  'evaluator/quizzes': { method: 'GET', path: '/evaluator/quizzes' },
  'evaluator/start': { method: 'POST', path: '/evaluator/attempts' },
  'evaluator/detail': { method: 'GET', path: null },
  'evaluator/submit': { method: 'POST', path: null },
  'evaluator/result': { method: 'GET', path: null },
  'forum/posts': { method: 'GET', path: '/forum/posts' },
  'forum/reply': { method: 'POST', path: null },
  'forum/announcements': { method: 'GET', path: '/forum/announcements' },
  'forum/like-post': { method: 'PUT', path: null },
  'homework/list': { method: 'GET', path: '/homework/student/list' },
  'homework/detail': { method: 'GET', path: null },
  'homework/submit': { method: 'POST', path: null },
  'homework/diagnose': { method: 'POST', path: null },
  'dashboard/student': { method: 'GET', path: null },
  'ranked/dashboard': { method: 'GET', path: null },
  'ranked/start-match': { method: 'POST', path: '/ranked/matches/start' },
  'gitea/me': { method: 'GET', path: '/gitea/me' },
  'gitea/token': { method: 'POST', path: '/gitea/token' },
  'code-repositories': { method: 'GET', path: '/code-repositories' }
};

async function requestAPI(method, path, { body, query, token } = {}) {
  const headers = { Accept: 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const options = {
    method,
    headers,
    timeout: { request: TIMEOUT_MS },
    retry: { limit: method === 'GET' ? MAX_GET_RETRIES : 0 },
    throwHttpErrors: false
  };

  if (method === 'GET' || method === 'DELETE') {
    options.searchParams = compact(query);
  } else if (body !== undefined) {
    options.json = body;
  }

  try {
    const response = await got(`${API_BASE}${path}`, options);
    return {
      statusCode: response.statusCode,
      data: parseBody(response.body)
    };
  } catch (err) {
    console.error(`[apiProxy] ${method} ${path} failed:`, err);
    return {
      statusCode: 500,
      data: { detail: err.message || 'api proxy request failed' }
    };
  }
}

exports.main = async (event = {}) => {
  const { action, data = {} } = event;
  if (action === 'upload/file') {
    return uploadCloudFile(data);
  }

  const direct = data._path || event.path;
  const method = String(data._method || event.method || 'GET').toUpperCase();
  const token = data._token || event.token || data.token;

  if (direct) {
    const { _path, _method, _token, token: _ignoredToken, ...payload } = data;
    return dispatch(method, direct, payload, token);
  }

  const route = ROUTES[action];
  if (!route) {
    return { statusCode: 404, data: { detail: `Unknown action: ${action}` } };
  }

  const { token: _ignoredToken, ...params } = data;
  const routePath = route.path || buildDynamicPath(action, params);
  if (!routePath) {
    return { statusCode: 400, data: { detail: `Missing path parameter for ${action}` } };
  }

  return dispatch(route.method, routePath, params, token);
};

function dispatch(method, path, payload, token) {
  if (method === 'GET' || method === 'DELETE') {
    return requestAPI(method, path, { query: payload, token });
  }

  return requestAPI(method, path, { body: payload, token });
}

async function uploadCloudFile(data = {}) {
  const { fileID, fileName, fieldName = 'file', targetPath, token, ...fields } = data;
  if (!fileID || !targetPath) {
    return { statusCode: 400, data: { detail: 'fileID and targetPath are required' } };
  }

  try {
    const download = await cloud.downloadFile({ fileID });
    const form = new FormData();
    form.append(fieldName, download.fileContent, {
      filename: fileName || 'upload.bin'
    });

    Object.keys(fields).forEach((key) => {
      const value = fields[key];
      if (value !== undefined && value !== null) {
        form.append(key, value);
      }
    });

    const headers = form.getHeaders();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await got(`${API_BASE}${targetPath}`, {
      method: 'POST',
      headers,
      body: form,
      timeout: { request: TIMEOUT_MS },
      retry: { limit: 0 },
      throwHttpErrors: false
    });

    return {
      statusCode: response.statusCode,
      data: parseBody(response.body)
    };
  } catch (err) {
    console.error('[apiProxy] upload failed:', err);
    return {
      statusCode: 500,
      data: { detail: err.message || 'file upload failed' }
    };
  }
}

function buildDynamicPath(action, params) {
  switch (action) {
    case 'profile/get':
      return params.userId ? `/profile/${params.userId}` : '';
    case 'knowledge/delete-doc':
      return params.docId ? `/user/knowledge/documents/${params.docId}` : '';
    case 'mistakes/list':
      return params.userId ? `/exams/student/${params.userId}/mistakes` : '';
    case 'mistakes/ai-analysis':
      return params.mistakeId ? `/exams/mistakes/${params.mistakeId}/ai-analysis` : '';
    case 'mistakes/update':
      return params.mistakeId ? `/exams/mistakes/${params.mistakeId}` : '';
    case 'evaluator/detail':
      return params.attemptId ? `/evaluator/attempts/${params.attemptId}` : '';
    case 'evaluator/submit':
      return params.attemptId ? `/evaluator/attempts/${params.attemptId}/submit` : '';
    case 'evaluator/result':
      return params.attemptId ? `/evaluator/attempts/${params.attemptId}/result` : '';
    case 'forum/reply':
      return params.postId ? `/forum/posts/${params.postId}/replies` : '';
    case 'forum/like-post':
      return params.postId ? `/forum/posts/${params.postId}/like` : '';
    case 'homework/detail':
      return params.homeworkId ? `/homework/${params.homeworkId}` : '';
    case 'homework/submit':
      return params.homeworkId ? `/homework/${params.homeworkId}/submit` : '';
    case 'homework/diagnose':
      return params.homeworkId ? `/homework/${params.homeworkId}/diagnose` : '';
    case 'dashboard/student':
      return params.userId ? `/dashboard/student/${params.userId}` : '';
    case 'ranked/dashboard':
      return params.userId ? `/ranked/student/${params.userId}/dashboard` : '';
    default:
      return '';
  }
}

function parseBody(body) {
  if (!body) return null;
  try {
    return JSON.parse(body);
  } catch (err) {
    return body;
  }
}

function compact(input) {
  const output = {};
  Object.keys(input || {}).forEach((key) => {
    const value = input[key];
    if (value !== undefined && value !== null && value !== '') {
      output[key] = value;
    }
  });
  return output;
}
