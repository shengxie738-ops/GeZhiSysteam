import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const hook = read('../js/hooks/useLearningDiagnosis.js');
const home = read('../js/components/StudentLearningDiagnosis.js');
const request = read('../js/utils/request.js');
const goalModal = read('../js/components/LearningDiagnosisGoalModal.js');

// Initial loading and a completed 404 are different UI states.
assert.match(hook, /const initializing = ref\(true\)/);
assert.match(hook, /finally\s*\{\s*initializing\.value = false;\s*\}/);
assert.match(hook, /err\?\.status (?:===|!==) 404/);
assert.match(request, /error\.status = response\.status/);
assert.match(home, /v-if="initializing"/);
assert.match(home, /正在恢复诊断数据/);

// A student with no session still receives the complete interactive dashboard.
assert.doesNotMatch(home, /<div v-if="session" class="grid/);
assert.match(home, /尚未设置学习目标/);
assert.match(home, /制定学习目标/);
assert.match(home, /等待设置目标/);
assert.match(home, /:title="session \? '更换学习目标' : '制定学习目标'"/);
assert.match(goalModal, /\{\{ title \}\}/);
assert.match(home, /v-for="stage in emptyPathStages"/);
assert.match(home, /待生成/);

// The first goal creates a session; later goals update the existing session.
assert.match(hook, /session\.value\s*\?\s*learningDiagnosisApi\.updateGoal/);
assert.match(hook, /:\s*learningDiagnosisApi\.createSession/);

// Git and version history are unavailable until a real session exists.
assert.match(home, /:disabled="!session"[^>]*@click="toggleGit"/);
assert.match(home, /:disabled="!session"[^>]*@click="openVersion"/);

console.log('learningDiagnosisEmptyState tests passed');
