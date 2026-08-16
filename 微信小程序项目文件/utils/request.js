// utils/request.js

const {
  API_PROXY_FUNCTION,
  SERVER_BASE,
  TOKEN_KEY,
  USER_KEY,
  LEGACY_TOKEN_KEY
} = require('./config.js');

const BASE_URL = SERVER_BASE;

function unwrapApiResponse(body) {
  if (body && typeof body === 'object') {
    if (Object.prototype.hasOwnProperty.call(body, 'code')) {
      if (body.code !== 0 && body.code !== 200) {
        throw new Error(body.message || body.detail || '请求失败');
      }
      return body.data;
    }

    if (body.success === true) {
      return Object.prototype.hasOwnProperty.call(body, 'data') ? body.data : body;
    }

    if (body.success === false) {
      throw new Error(body.message || body.detail || '请求失败');
    }

    if (body.status === 'success') {
      return Object.prototype.hasOwnProperty.call(body, 'data') ? body.data : body;
    }

    if (body.status === 'error' || body.status === 'failed') {
      throw new Error(body.message || body.detail || body.error || '请求失败');
    }
  }

  return body;
}

function request(options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const parsed = parseUrl(options.url || '/');
  const token = wx.getStorageSync(TOKEN_KEY) || wx.getStorageSync(LEGACY_TOKEN_KEY);
  const data = {
    ...parsed.query,
    ...(options.data || {}),
    _method: method,
    _path: parsed.path,
    _token: token || undefined
  };

  return cloudProxyRequest(options, data);
}

function cloudProxyRequest(options, data) {
  return new Promise((resolve, reject) => {
    if (!wx.cloud || !wx.cloud.callFunction) {
      reject(new Error('云开发未初始化，请在微信开发者工具中开通并选择云环境'));
      return;
    }

    wx.cloud.callFunction({
      name: API_PROXY_FUNCTION,
      data: {
        action: options.action || '',
        data
      },
      success(res) {
        try {
          const result = res.result || {};
          const statusCode = result.statusCode || 200;
          const body = result.data;
          const apiCode = body && typeof body === 'object' ? body.code : undefined;
          const expired = statusCode === 401 || apiCode === 401 || (body && body.message === 'not authenticated');

          if (expired) {
            clearAuth();
            reject(new Error('登录已失效，请重新登录'));
            return;
          }

          if (statusCode >= 200 && statusCode < 300) {
            resolve(unwrapApiResponse(body));
            return;
          }

          reject(new Error(getErrorMessage(body, statusCode)));
        } catch (err) {
          reject(err);
        }
      },
      fail(err) {
        reject(new Error((err && err.errMsg) || '云函数调用失败，请检查云环境与 apiProxy 部署状态'));
      }
    });
  });
}

function uploadFile(options = {}) {
  const token = wx.getStorageSync(TOKEN_KEY) || wx.getStorageSync(LEGACY_TOKEN_KEY);

  return new Promise((resolve, reject) => {
    if (!wx.cloud || !wx.cloud.uploadFile || !wx.cloud.callFunction) {
      reject(new Error('云开发未初始化，无法上传文件'));
      return;
    }

    const cloudPath = buildCloudPath(options.fileName || options.name || 'upload.bin');
    wx.cloud.uploadFile({
      cloudPath,
      filePath: options.filePath,
      success(uploadRes) {
        wx.cloud.callFunction({
          name: API_PROXY_FUNCTION,
          data: {
            action: 'upload/file',
            data: {
              ...(options.formData || {}),
              fileID: uploadRes.fileID,
              fileName: options.fileName || options.name || cloudPath.split('/').pop(),
              fieldName: options.fieldName || 'file',
              targetPath: options.targetPath,
              token
            }
          },
          success(res) {
            const result = res.result || {};
            const statusCode = result.statusCode || 200;
            const body = result.data;
            if (statusCode >= 200 && statusCode < 300) {
              try {
                resolve(unwrapApiResponse(body));
              } catch (err) {
                reject(err);
              }
              return;
            }

            reject(new Error(getErrorMessage(body, statusCode)));
          },
          fail(err) {
            reject(new Error((err && err.errMsg) || '云函数上传转发失败'));
          },
          complete() {
            wx.cloud.deleteFile({ fileList: [uploadRes.fileID] });
          }
        });
      },
      fail(err) {
        reject(new Error((err && err.errMsg) || '文件上传到云存储失败'));
      }
    });
  });
}

function parseUrl(url) {
  const [path, queryString = ''] = String(url).split('?');
  const query = {};

  queryString.split('&').forEach((pair) => {
    if (!pair) return;
    const eqIndex = pair.indexOf('=');
    const rawKey = eqIndex >= 0 ? pair.slice(0, eqIndex) : pair;
    const rawValue = eqIndex >= 0 ? pair.slice(eqIndex + 1) : '';
    const key = decodeURIComponent(rawKey);
    query[key] = decodeURIComponent(rawValue.replace(/\+/g, ' '));
  });

  return { path, query };
}

function clearAuth() {
  wx.removeStorageSync(TOKEN_KEY);
  wx.removeStorageSync(LEGACY_TOKEN_KEY);
  wx.removeStorageSync(USER_KEY);
  wx.reLaunch({ url: '/pages/login/index' });
}

function getErrorMessage(body, statusCode) {
  if (body && typeof body === 'object') {
    return body.detail || body.message || body.error || `请求失败(${statusCode})`;
  }
  return body || `请求失败(${statusCode})`;
}

function buildCloudPath(fileName) {
  const safeName = String(fileName).replace(/[\\/:*?"<>|]/g, '_');
  return `tmp-upload/${Date.now()}-${Math.random().toString(16).slice(2)}-${safeName}`;
}

module.exports = {
  BASE_URL,
  uploadFile,
  request,
  unwrapApiResponse
};
