import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const teacherManager = readFileSync(new URL('js/components/TeacherProjectManager.js', frontendRoot), 'utf8');

assert.match(teacherManager, /编程团队实训管理/);
assert.match(teacherManager, /仓库主页/);
assert.match(teacherManager, /教师评语/);
assert.match(teacherManager, /修改建议/);
assert.match(teacherManager, /teacherFeedbackUpdatedAt/);
assert.match(teacherManager, /updateRepositoryFeedback/);
assert.doesNotMatch(teacherManager, /打开 Gitea/);

console.log('teacher training repository static tests passed');
