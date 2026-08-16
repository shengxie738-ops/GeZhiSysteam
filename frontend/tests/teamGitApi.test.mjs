import assert from 'node:assert/strict';

globalThis.window = {};
globalThis.localStorage = {
  store: new Map([['teamGitMockFirst', 'true']]),
  getItem(key) {
    return this.store.get(key) || null;
  },
  setItem(key, value) {
    this.store.set(key, value);
  },
  removeItem(key) {
    this.store.delete(key);
  },
};
globalThis.fetch = async () => {
  throw new Error('network disabled for team git API tests');
};

const { teamGitApi } = await import('../js/api/teamGit.js');

const detail = await teamGitApi.getProjectDetail('huffman-coding-team', { viewer: '李明' });
assert.equal(detail.project.title, '哈夫曼压缩与解压引擎');
assert.equal(detail.repository.repoName, 'huffman-coding-team');
assert.equal(detail.repositoryCard.subjectCategory, '数据结构与算法');
assert.equal(detail.repositoryCard.repoName, 'huffman-coding-team');
assert.equal(detail.repositoryCard.leader, '张华');
assert.ok(detail.repositoryCard.members.includes('李明'));
assert.equal(detail.repositoryCard.repositoryStatus, '协作中');
assert.match(detail.repositoryCard.prStatus, /待审核|待创建/);
assert.equal(detail.workflowSteps.length, 6);
assert.ok(detail.workflowSteps.every((step) => step.command.includes('git ') || step.command.includes('/pulls/new')));
assert.ok(detail.memberProgress.some((member) => member.name === '王磊' && member.mergeStatus === 'merged'));

const home = await teamGitApi.getRepositoryHome('huffman-coding-team');
assert.equal(home.repoName, 'huffman-coding-team');
assert.equal(home.visibility, 'private');
assert.equal(home.cloneUrlMockOnly, true);
assert.ok(home.files.some((file) => file.name === 'README.md'));
assert.ok(home.classDiagram.includes('Controller'));

const tree = await teamGitApi.getRepositoryTree('huffman-coding-team');
assert.equal(tree.ref, 'main');
assert.ok(tree.entries.some((entry) => entry.name === 'README.md'));

const blob = await teamGitApi.getRepositoryBlob('huffman-coding-team', { path: 'README.md' });
assert.equal(blob.path, 'README.md');
assert.ok(blob.previewable);

const languages = await teamGitApi.getRepositoryLanguages('huffman-coding-team');
assert.ok(languages.some((lang) => lang.name === 'Python'));

const feedback = await teamGitApi.updateRepositoryFeedback('huffman-coding-team', {
  teacherComment: '结构清晰。',
  revisionSuggestions: '补充单元测试。',
  actor: 'teacher-a'
});
assert.equal(feedback.teacherComment, '结构清晰。');
assert.equal(feedback.revisionSuggestions, '补充单元测试。');
assert.equal(feedback.teacherFeedbackUpdatedBy, 'teacher-a');
assert.ok(feedback.teacherFeedbackUpdatedAt);

const members = await teamGitApi.searchMembers({ keyword: '20230004', className: '计科 2301' });
assert.ok(members.some((member) => member.studentId === '20230004' && member.source === 'mock'));

const cloneResult = await teamGitApi.confirmClone('huffman-coding-team', { userId: '赵雷' });
const zhaoleiAfterClone = cloneResult.memberProgress.find((member) => member.name === '赵雷');
assert.equal(zhaoleiAfterClone.cloneStatus, 'done');
assert.match(cloneResult.currentUserProgress.nextHint, /等待系统检测 push/);

const created = await teamGitApi.createRepository('huffman-coding-team', { actor: 'teacher-a' });
assert.equal(created.repository.status, 'created');
assert.match(created.repository.cloneUrl, /huffman-coding-team\.git$/);

const deletableProject = await teamGitApi.createProject({
  id: 'delete-me-team-repo',
  title: 'Delete Me Team Repo',
  repoName: 'delete-me-team-repo',
  members: ['delete-leader', 'delete-member'],
  actor: 'delete-leader',
});
assert.equal(deletableProject.id, 'delete-me-team-repo');
const deleteResult = await teamGitApi.deleteProject('delete-me-team-repo', { actor: 'delete-leader' });
assert.equal(deleteResult.deleted, true);
const projectsAfterDelete = await teamGitApi.listProjects({ viewer: 'delete-leader', scope: 'my' });
assert.ok(!projectsAfterDelete.some((project) => project.id === 'delete-me-team-repo'));

const refreshed = await teamGitApi.refreshStatus('huffman-coding-team', { actor: 'teacher-a' });
assert.ok(refreshed.repository.lastSyncedAt);
assert.ok(refreshed.gitEvents.some((event) => event.type === 'gitea_synced' || event.type === 'status_refreshed'));

console.log('teamGitApi tests passed');
