import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const workspaceUrl = new URL('../js/components/LearningTextTaskWorkspace.js', import.meta.url);

assert.equal(existsSync(workspaceUrl), true, 'LearningTextTaskWorkspace.js should exist');

const workspace = read('../js/components/LearningTextTaskWorkspace.js');
const review = read('../js/components/LearningKnowledgeReviewPage.js');
const guided = read('../js/components/LearningGuidedPracticePage.js');
const hook = read('../js/hooks/useLearningDiagnosis.js');
const home = read('../js/components/StudentLearningDiagnosis.js');

for (const token of [
    'answerMode', 'wordCount', 'criteriaProgress', 'structurePrompts',
    'displayTitle', '补救练习', '专项练习',
    'Agent guide', '完成标准', '提交并生成诊断'
]) assert.match(workspace, new RegExp(token));

for (const source of [review, guided]) {
    assert.match(source, /LearningTextTaskWorkspace/);
    assert.match(source, /learning-text-task-workspace/);
    assert.match(source, /@back/);
    assert.match(source, /@hint/);
    assert.match(source, /@submit/);
}

assert.match(review, /mode="review"/);
assert.match(guided, /mode="guided"/);
assert.match(hook, /currentHint/);
assert.match(hook, /currentHint\.value = result/);
assert.match(hook, /currentHint\.value = null/);
assert.match(home, /:hint="currentHint"/);

console.log('learningDiagnosisTextTasks tests passed');
