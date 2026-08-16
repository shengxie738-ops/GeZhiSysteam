import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const auth = readFileSync(new URL('../js/hooks/useAuth.js', import.meta.url), 'utf8');
const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');

const workspace = auth.indexOf("id: 'workspace'");
const diagnosis = auth.indexOf("id: 'learning-diagnosis'");
const knowledge = auth.indexOf("id: 'knowledge'");
assert.ok(workspace >= 0 && diagnosis > workspace && knowledge > diagnosis);
assert.match(main, /StudentLearningDiagnosis/);
assert.match(index, /currentView === 'learning-diagnosis'/);
assert.match(index, /student-learning-diagnosis/);

console.log('learningDiagnosisNavigation tests passed');
