import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const api = read('../js/api/learningDiagnosis.js');
const hook = read('../js/hooks/useLearningDiagnosis.js');
const home = read('../js/components/StudentLearningDiagnosis.js');
const page = read('../js/components/LearningCodingPracticePage.js');

assert.match(api, /runTask/);
assert.match(api, /tasks\/\$\{taskId\}\/run/);
assert.match(api, /attempt/);

for (const token of ['lastExecution', 'runTaskCode', 'clearExecution']) {
    assert.match(hook, new RegExp(token));
}
assert.match(hook, /requestHint\([\s\S]*lastExecution\.value/);
assert.match(hook, /const clearExecution = \(\) => \{ lastExecution\.value = null; currentHint\.value = null; \};/);

for (const token of [
    ':execution="lastExecution"', '@run="runTaskCode"', '@reset="resetTaskCode"',
    'Learning diagnosis / Coding', 'displayTitle', 'problemDescription', 'publicTestCases',
    '运行代码', '提交并生成诊断', '实时诊断信号', '独立思考保护',
    '测试结果', '运行记录', 'Agent guide'
]) assert.match(`${home}\n${page}`, new RegExp(token));

assert.match(page, /\$emit\('run'/);
assert.match(page, /\$emit\('submit', \{ code: this\.code \}\)/);
assert.match(page, /\$emit\('reset'/);
assert.match(page, /grid-cols-1 xl:grid-cols-\[280px_minmax\(0,1fr\)_300px\]/);

console.log('learningDiagnosisCodingTask tests passed');
