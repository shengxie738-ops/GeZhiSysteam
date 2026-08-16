import assert from 'node:assert/strict';

globalThis.window = {};
globalThis.localStorage = {
  getItem(key) {
    return key === 'repositoryMockFirst' ? 'true' : null;
  },
  setItem() {},
  removeItem() {},
};
globalThis.fetch = async () => {
  throw new Error('network disabled for repository API tests');
};

const { repositoryApi } = await import('../js/api/repository.js');

const before = await repositoryApi.getRepositories();
assert.ok(before.length >= 3);

const created = await repositoryApi.createRepository({
  title: '校园导航小程序',
  slug: 'campus-miniapp',
  description: '面向新生的校园服务导航',
  author: 'tester',
  language: 'Vue',
  course: '软件工程',
  tags: ['小程序', '校园服务'],
  private: true,
  collaborators: ['alice', 'charlie'],
});

assert.equal(created.slug, 'campus-miniapp');
assert.equal(created.cloneUrl, 'https://gezhisystem.com/gitea/campus/campus-miniapp.git');
assert.equal(created.visibility, 'private');
assert.deepEqual(created.collaborators, ['alice', 'charlie']);

const detail = await repositoryApi.getRepository(created.id);
assert.equal(detail.title, '校园导航小程序');
assert.match(detail.readme, /校园导航小程序/);

const star = await repositoryApi.toggleStar(created.id, 'bob');
assert.equal(star.isStarred, true);
assert.equal(star.starCount, 1);

const favorite = await repositoryApi.toggleFavorite(created.id, 'bob');
assert.equal(favorite.isFavorited, true);
assert.equal(favorite.favoriteCount, 1);

const report = await repositoryApi.reportRepository(created.id, {
  reporter: 'bob',
  reason: '疑似违规',
  description: '测试举报流程',
});
assert.equal(report.projectId, created.id);
assert.equal(report.status, 'pending');

const reports = await repositoryApi.getReports();
assert.ok(reports.some((item) => item.id === report.id));

const audit = await repositoryApi.auditReport(report.id, {
  action: 'approve_delete',
  teacherId: 'teacher-a',
  note: '测试删除',
});
assert.equal(audit.status, 'approved');

const removed = await repositoryApi.getRepository(created.id);
assert.equal(removed.status, 'removed');

const profile = await repositoryApi.getUserRepositoryProfile('bob');
assert.ok(profile.starredProjects.every((item) => item.id !== created.id));

console.log('repositoryApi tests passed');
