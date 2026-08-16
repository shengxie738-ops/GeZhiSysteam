import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
assert.match(index, /学习诊断/);
assert.match(index, /继续学习/);
assert.match(index, /currentView = 'learning-diagnosis'/);

console.log('learningDiagnosisDashboardEntry tests passed');
