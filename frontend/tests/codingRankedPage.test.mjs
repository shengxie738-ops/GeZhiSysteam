import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const html = readFileSync(new URL('index.html', frontendRoot), 'utf8');
const codingSandbox = readFileSync(new URL('js/components/CodingSandbox.js', frontendRoot), 'utf8');
const rankedApiSource = readFileSync(new URL('js/api/ranked.js', frontendRoot), 'utf8');

assert.match(
  codingSandbox,
  /codingMode === 'ranked'/,
  '竞技排位赛入口必须渲染独立 ranked 页面分支',
);

assert.match(
  codingSandbox,
  /rankedTabs/,
  '排位赛页面必须提供大厅、对战记录、错题本、赛季等 Figma 子视图导航',
);

for (const label of ['Ranked Arena', '排位赛大厅', '开始匹配', '排行榜', '对战记录', '错题管理', '赛季', '排位 AI 教练']) {
  assert.match(codingSandbox, new RegExp(label), `排位赛页面缺少核心模块文案：${label}`);
}

assert.match(
  codingSandbox,
  /startRankedMatch/,
  '排位赛页面必须提供开始匹配交互入口',
);

assert.match(
  codingSandbox,
  /<teleport v-else-if="codingMode === 'ranked'" to="body">[\s\S]*fixed inset-0 z-\[9999\]/,
  '排位赛页面应覆盖旧工作区以贴近 Figma 全屏设计',
);

assert.match(
  html,
  /:ranked-coach-config="getAgentInfo\('agent_ranked_coach'\)"/,
  'CodingSandbox 必须接收排位赛 AI 教练配置',
);

assert.match(codingSandbox, /rankedCoachConfig/, '排位页必须声明 rankedCoachConfig prop');
assert.match(codingSandbox, /import\s+\{\s*rankedApi\s*\}\s+from\s+['"]\.\.\/api\/ranked\.js['"]/, '排位页必须使用 ranked API wrapper');
assert.match(codingSandbox, /rankedApi\.getDashboard/, '排位页必须从后端加载 dashboard 数据');
assert.match(codingSandbox, /rankedApi\.askCoach/, '排位 AI 教练必须调用后端 AI 接口');
assert.match(codingSandbox, /rankedApi\.analyzeMistake/, '排位错题 AI 分析必须调用后端 AI 接口');
assert.match(codingSandbox, /agentModel:\s*rankedCoachConfig/, '排位 AI 请求必须使用 rankedCoachConfig 的模型');

assert.match(rankedApiSource, /submitMatch\(matchId,\s*payload\)/, 'ranked API must expose submitMatch(matchId, payload)');
assert.match(rankedApiSource, /\/ranked\/matches\/\$\{encodeURIComponent\(matchId\)\}\/submit/, 'submitMatch must call the ranked match submit endpoint');
assert.match(rankedApiSource, /deleteMistake\(mistakeId,\s*userId\)/, 'ranked API must expose deleteMistake(mistakeId, userId)');
assert.match(rankedApiSource, /method:\s*'DELETE'/, 'deleteMistake must use DELETE for backend soft delete');
assert.match(codingSandbox, /currentRankedMatchId/, 'ranked page must track the backend match id');
assert.match(codingSandbox, /rankedApi\.submitMatch/, 'ranked settlement must submit to backend');
assert.match(codingSandbox, /deleteRankedMistake/, 'ranked mistake page must provide a delete handler');
assert.match(codingSandbox, /rankedApi\.deleteMistake/, 'ranked mistake delete handler must call backend API');
assert.match(codingSandbox, /const\s+mistakeStats\s*=\s*computed/, 'ranked mistake stats must be computed from current mistakes');
assert.doesNotMatch(codingSandbox, /const\s+mistakeStats\s*=\s*\[/, 'ranked mistake stats must not remain a static array');

console.log('codingRankedPage tests passed');
