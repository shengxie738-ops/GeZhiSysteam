import assert from 'node:assert/strict';

const storage = new Map();
globalThis.window = {
  localStorage: {
    getItem(key) {
      return storage.get(key) || null;
    },
    setItem(key, value) {
      storage.set(key, value);
    },
    removeItem(key) {
      storage.delete(key);
    },
  },
};
globalThis.localStorage = globalThis.window.localStorage;

const calls = [];
globalThis.fetch = async (url, config = {}) => {
  calls.push({ url, config });
  return {
    ok: true,
    status: 200,
    text: async () => JSON.stringify({ status: 'success' }),
  };
};

const { API_BASE_URL, API_ORIGIN, toBackendAssetUrl } = await import('../js/config/env.js');
const { userApi } = await import('../js/api/userApi.js');

assert.equal(API_ORIGIN, 'http://localhost:8516');
assert.equal(API_BASE_URL, 'http://localhost:8516/api');
assert.equal(
  toBackendAssetUrl('/static/avatars/student.png'),
  'http://localhost:8516/static/avatars/student.png',
);
assert.equal(
  toBackendAssetUrl('https://cdn.example.test/avatar.png'),
  'https://cdn.example.test/avatar.png',
);

await userApi.getUserInfo('student 01');
assert.equal(calls[0].url, 'http://localhost:8516/api/user/info/student%2001');

const avatarUrl = userApi.getAvatarUrl('/static/avatars/student.png');
assert.match(avatarUrl, /^http:\/\/localhost:8516\/static\/avatars\/student\.png\?t=\d+$/);

console.log('userCenterApi tests passed');
