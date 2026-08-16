import assert from 'node:assert/strict';

globalThis.window = {
  dispatchEvent() {},
};
globalThis.localStorage = {
  store: new Map(),
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

const backendProject = {
  id: 'target-23001020119-team-oj-review',
  status: 'active',
  project: {
    id: 'target-23001020119-team-oj-review',
    title: '课程 OJ 判题与错题回流平台',
    course: '编程团队实训',
    teamName: '栈帧小组',
    description: '面向程序设计课的判题、提交记录分析和错题本回流系统。',
    leaderId: '23001020119',
    createdBy: '23001020119',
    className: '23006',
  },
  repository: {
    repoName: 'oj-review',
    status: 'collaborating',
    statusLabel: '协作中',
    defaultBranch: 'main',
    taskBranch: 'feature/team-start',
    cloneUrl: 'https://gezhisystem.com/gitea/campus/oj-review.git',
    lastSyncedAt: '2026-07-05T12:00:00+08:00',
  },
  memberProgress: [
    { id: '23001020119', name: '谢渝', role: '队长', progress: 92, contribution: 36 },
    { id: '23001020131', name: '江景珩', role: '队员', progress: 78, contribution: 27 },
  ],
  pullRequests: [
    { id: 'pr-3', number: 3, status: 'open', statusLabel: 'PR 待审核' },
  ],
  recentCommits: [],
  gitEvents: [],
  teamSummary: {
    totalMembers: 2,
    openPullRequests: 0,
    contributionRanking: [
      {
        id: '23001020119',
        name: 'Captain',
        studentId: '23001020119',
        role: 'leader',
        task: 'api integration',
        commitCount: 9,
        prCount: 2,
        mergedPrCount: 1,
        contribution: 36,
        score: 96,
        source: 'gitea',
      },
    ],
  },
  updatedAt: '2026-07-05T12:00:00+08:00',
};

globalThis.fetch = async (url) => {
  assert.match(String(url), /\/team-git\/projects/);
  return {
    ok: true,
    status: 200,
    async text() {
      return JSON.stringify({ code: 200, message: 'ok', data: [backendProject] });
    },
  };
};

const { teamGitApi } = await import('../js/api/teamGit.js');

const projects = await teamGitApi.listProjects({ viewer: '23001020119', scope: 'my' });
assert.equal(projects.length, 1);
assert.equal(projects[0].repositoryCard.subjectCategory, '编程团队实训');
assert.equal(projects[0].repositoryCard.repoName, 'oj-review');
assert.equal(projects[0].repositoryCard.repositoryStatus, '协作中');
assert.equal(projects[0].repositoryCard.leader, '23001020119');
assert.ok(projects[0].repositoryCard.members.includes('谢渝'));
assert.equal(projects[0].repositoryCard.updatedAt, '2026年7月5日12点00分');
assert.equal(projects[0].repository.lastSyncedAt, '2026年7月5日12点00分');
assert.equal(projects[0].workflowSteps.length, 6);
assert.equal(projects[0].teamSummary.totalMembers, 2);
assert.equal(projects[0].teamSummary.contributionRanking[0].commitCount, 9);
assert.equal(projects[0].teamSummary.contributionRanking[0].prCount, 2);
assert.equal(projects[0].teamSummary.contributionRanking[0].role, 'leader');
assert.equal(projects[0].teamSummary.contributionRanking[0].source, 'gitea');

console.log('teamGitApi backend shape tests passed');
