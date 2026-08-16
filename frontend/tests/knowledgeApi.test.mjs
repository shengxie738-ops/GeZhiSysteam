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
    text: async () => JSON.stringify({ status: 'success', data: { id: 'repo_a' } }),
  };
};

const { knowledgeApi } = await import('../js/api/knowledgeApi.js');

await knowledgeApi.deleteRepository({ userId: 'student 01', repositoryId: 'repo/a' });

assert.equal(
  calls[0].url,
  'http://localhost:8516/api/user/knowledge/repositories/repo%2Fa?user_id=student%2001',
);
assert.equal(calls[0].config.method, 'DELETE');

console.log('knowledgeApi tests passed');
