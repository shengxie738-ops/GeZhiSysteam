import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const api = read('../js/api/learningDiagnosis.js');
const hook = read('../js/hooks/useLearningDiagnosis.js');
const request = read('../js/utils/request.js');
const home = read('../js/components/StudentLearningDiagnosis.js');
const task = read('../js/components/LearningDiagnosisTaskPage.js');
const evidence = read('../js/components/LearningDiagnosisEvidenceModal.js');
const version = read('../js/components/LearningDiagnosisVersionPage.js');
const textWorkspace = read('../js/components/LearningTextTaskWorkspace.js');

for (const route of [
    '/learning-diagnosis/sessions',
    '/refresh',
    '/path',
    '/hints',
    '/submit',
    '/snapshots/'
]) assert.match(api, new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));

assert.match(api, /include_git_evidence:\s*false/);
assert.match(api, /learning-diagnosis\/latest/);
assert.match(api, /updateGoal/);
assert.match(api, /toggleGitEvidence/);
assert.match(hook, /currentHintLevel/);
assert.match(hook, /activePage/);
assert.match(hook, /loadLatestSession/);
assert.match(hook, /pathHistory/);
assert.match(hook, /loadPathHistory/);
assert.match(hook, /const openVersion = async \(\) => \{ await loadPathHistory\(\); activePage\.value = 'version'; \};/);
assert.match(home, /:paths="pathHistory"/);
assert.match(home, /:current-path="path"/);
assert.match(hook, /goalModalOpen/);
assert.match(hook, /openTaskByType/);
assert.match(hook, /updateGoal/);
assert.match(hook, /goalModalOpen/);
assert.match(hook, /openTaskByType/);
assert.match(hook, /updateGoal/);
assert.match(home, /masteryScore/);
assert.match(home, /practiceScore/);
assert.match(home, /confidence/);
assert.match(home, /grid-cols-1 xl:grid-cols-2/);
assert.match(home, /诊断证据/);
assert.match(home, /当前结论/);
assert.match(home, /当前目标/);
assert.match(home, /toggleGit/);
assert.match(home, /更换目标/);
assert.match(home, /learning-diagnosis-goal-modal/);
assert.match(home, /progress-ring/);
assert.match(home, /更换目标/);
assert.match(home, /learning-diagnosis-goal-modal/);
assert.match(home, /progress-ring/);
assert.match(home, /Git 证据默认关闭/);
assert.match(home, /LearningDiagnosisEvidenceModal/);
assert.match(home, /evidence.map|v-for="\(item, index\) in displayEvidence/);
assert.match(home, /evidence-summary/);
assert.match(home, /selectedMetricKey/);
assert.match(home, /metric-expanded/);
assert.match(home, /@mouseleave=.*collapseMetric/);
assert.match(home, /metrics-grid/);
assert.match(home, /position:absolute/);
assert.match(home, /collapseMetric/);
assert.match(home, /height:190px/);
assert.match(home, /metric-flow/);
assert.doesNotMatch(home, /<learning-diagnosis-metric-detail/);
assert.match(home, /metric\.value \+ '%'/);
assert.match(request, /无法连接学习诊断服务/);
assert.match(hook, /return null/);
assert.match(task, /INDEPENDENT_RETEST/);
assert.match(task, /Level 1/);
assert.match(evidence, /provenance/);
assert.match(version, /added_tasks/);
assert.match(version, /change_reason_codes/);
assert.match(version, /版本记录/);
assert.match(version, /动态学习路径/);
assert.match(version, /const triggerLabels = \{[^}]*REMEDIATION_COMPLETED: '补救任务完成'[^}]*\};/);
assert.match(version, /selectedVersion/);
assert.match(version, /changeFilter/);
assert.match(version, /stageFilter/);
assert.match(version, /searchText/);
assert.match(version, /filteredTasks/);
assert.match(version, /任务标题/);
assert.match(version, /调整依据/);
assert.match(version, /新增任务/);
assert.match(version, /保留任务/);
assert.match(version, /移除任务/);
for (const page of ['../js/components/LearningDiagnosisGoalModal.js','../js/components/LearningKnowledgeReviewPage.js','../js/components/LearningGuidedPracticePage.js','../js/components/LearningCodingPracticePage.js','../js/components/LearningIndependentRetestPage.js']) {
    const source = read(page);
    assert.match(source, /Learning diagnosis/);
    assert.match(source, /submit|complete|hint/);
}
assert.match(textWorkspace, /v-model="answer"/);
assert.match(textWorkspace, /\$emit\('submit', \{ answer: this\.answer \}\)/);
const independentRetest = read('../js/components/LearningIndependentRetestPage.js');
assert.match(independentRetest, /v-model="answer"/);
assert.match(independentRetest, /\{ answer \}/);
assert.match(hook, /Git 证据关闭失败/);
assert.match(hook, /gitEnabled\.value = true/);

for (const page of [
    '../js/components/LearningDiagnosisGoalModal.js',
    '../js/components/LearningKnowledgeReviewPage.js',
    '../js/components/LearningGuidedPracticePage.js',
    '../js/components/LearningCodingPracticePage.js',
    '../js/components/LearningIndependentRetestPage.js'
]) {
    const source = read(page);
    assert.match(source, /Learning diagnosis/);
    assert.match(source, /submit|complete|hint/);
}

console.log('learningDiagnosis tests passed');
