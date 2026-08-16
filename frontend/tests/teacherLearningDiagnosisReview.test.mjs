import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const apiPath = new URL('js/api/teacherLearningDiagnosis.js', frontendRoot);
const componentPath = new URL('js/components/TeacherLearningDiagnosisReview.js', frontendRoot);
const centerPath = new URL('js/components/TeacherAnalyticsCenter.js', frontendRoot);
const authPath = new URL('js/hooks/useAuth.js', frontendRoot);
const mainPath = new URL('js/main.js', frontendRoot);
const indexPath = new URL('index.html', frontendRoot);

for (const path of [apiPath, componentPath, centerPath, authPath, mainPath, indexPath]) {
    assert.ok(existsSync(path), `${path.pathname} should exist`);
}

const api = readFileSync(apiPath, 'utf8');
const component = readFileSync(componentPath, 'utf8');
const center = readFileSync(centerPath, 'utf8');
const auth = readFileSync(authPath, 'utf8');
const main = readFileSync(mainPath, 'utf8');
const index = readFileSync(indexPath, 'utf8');

assert.match(api, /teacherLearningDiagnosisApi/);
assert.match(api, /\/teacher\/learning-diagnosis/);
assert.match(api, /watch-flags/);
assert.match(api, /OBSERVING/);

assert.doesNotMatch(component, /learningDiagnosisApi/);
assert.match(component, /normalizeReview/);
assert.match(component, /studentId/);
assert.match(component, /comment: content/);
assert.match(component, /markReviewed/);
assert.match(component, /toggleWatch/);
assert.match(component, /审查队列/);
assert.match(component, /审查完成度/);
assert.match(component, /教师备注/);
assert.match(component, /仅保存到教师审查模块/);
assert.match(component, /不向学生端推送任务/);

assert.match(center, /diagnosis-review/);
assert.match(center, /TeacherLearningDiagnosisReview/);
assert.match(center, /forwardDiagnosisToast/);
assert.match(center, /学习诊断审查/);

assert.match(auth, /t_diagnosis_review/);
assert.match(auth, /诊断审查/);
assert.match(main, /TeacherLearningDiagnosisReview/);
assert.match(index, /teacher-learning-diagnosis-review/);
assert.match(index, /t_diagnosis_review/);

console.log('teacherLearningDiagnosisReview static tests passed');
