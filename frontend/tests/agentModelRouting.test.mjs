import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const html = readFileSync(new URL('index.html', frontendRoot), 'utf8');
const agentsHook = readFileSync(new URL('js/hooks/useAgents.js', frontendRoot), 'utf8');
const mockData = readFileSync(new URL('js/data/mockData.js', frontendRoot), 'utf8');
const chatModes = readFileSync(new URL('js/utils/chatModes.js', frontendRoot), 'utf8');
const streamChat = readFileSync(new URL('js/api/streamChat.js', frontendRoot), 'utf8');
const visualGuide = readFileSync(new URL('js/api/visualGuide.js', frontendRoot), 'utf8');
const useChat = readFileSync(new URL('js/hooks/useChat.js', frontendRoot), 'utf8');
const main = readFileSync(new URL('js/main.js', frontendRoot), 'utf8');
const aiModelsUrl = new URL('js/config/aiModels.js', frontendRoot);
const aiModelsModule = await import(aiModelsUrl.href);

assert.equal(existsSync(aiModelsUrl), true, 'AI model configuration module should exist');

const aiModels = readFileSync(aiModelsUrl, 'utf8');

for (const model of [
  'qwen3.7-plus',
  'qwen3.7-max',
  'qwen3.8-max',
  'qwen3.7-flash',
  'qwen3.6-plus',
  'qwen3.6-max-preview',
  'qwen3.5-plus',
  'deepseek-v4-pro',
  'deepseek-v4-flash',
  'glm-5.2',
  'glm-5.1',
  'kimi-k2.7-code',
  'kimi-k2.6',
  'glm-4.5-air',
  'glm-4.6v',
]) {
  assert.match(aiModels, new RegExp(model.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
}

for (const removedModel of ['spark Ultra-32K', 'spark Lite', 'spark-x', 'mimo-v2.5', 'glm-4.7']) {
  assert.doesNotMatch(aiModels, new RegExp(`id:\\s*'${removedModel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}'`));
}

for (const imageModel of [
  'qwen-image-2.0',
  'qwen-image-2.0-pro',
  'qwen-image-max',
  'z-image-turbo',
]) {
  assert.match(aiModels, new RegExp(imageModel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
}

for (const legacyModel of ['GPT-4-Turbo', 'Claude-3.5-Sonnet', 'Gemini-1.5-Pro']) {
  assert.doesNotMatch(html, new RegExp(legacyModel));
  assert.doesNotMatch(mockData, new RegExp(legacyModel));
}

assert.match(aiModels, /export const DEFAULT_IMAGE_MODEL = 'qwen-image-2\.0-pro';/);
assert.doesNotMatch(aiModels, /spark-api-open\.xf-yun\.com/);
assert.doesNotMatch(aiModels, /xiaomimimo\.com/);
assert.doesNotMatch(aiModels, /apiModel:\s*'4\.0Ultra'/);
assert.doesNotMatch(aiModels, /apiModel:\s*'lite'/);
assert.doesNotMatch(aiModels, /apiModel:\s*'generalv3\.5'/);
assert.match(mockData, /name: 'Mira'/);
assert.match(mockData, /role: 'AI引导图生成师'/);
assert.match(mockData, /icon: 'ph-flow-arrow'/);
assert.match(mockData, /avatarShellClass: 'bg-white shadow-\[0_10px_24px_rgba\(28,43,56,0\.10\)\] border border-white\/80'/);
assert.match(mockData, /iconTextClass: 'text-\[#1c2b38\] text-\[18px\]'/);
assert.match(mockData, /modelCategory: 'image'/);
assert.match(mockData, /model: 'qwen-image-2\.0-pro'/);
assert.match(mockData, /把左侧问题转译成概念图与步骤图。/);
assert.match(mockData, /id: 'agent_ranked_coach'/);
assert.match(mockData, /name: '排位赛AI教练'/);
assert.match(mockData, /role: '排位诊断与冲分策略教练'/);

assert.match(agentsHook, /import\s+\{\s*DEFAULT_AGENT_MODEL,\s*DEFAULT_IMAGE_MODEL,\s*IMAGE_MODEL_OPTIONS,\s*TEXT_MODEL_OPTIONS,\s*mergeModelOptions\s*\}\s+from\s+['"]\.\.\/config\/aiModels\.js['"]/);
assert.match(agentsHook, /import\s+request\s+from\s+['"]\.\.\/utils\/request\.js['"]/);
assert.match(agentsHook, /import\s+\{\s*agentApi\s*\}\s+from\s+['"]\.\.\/api\/agents\.js['"]/);
assert.match(agentsHook, /const\s+updateAgentModel\s*=\s*async\s*\(agent,\s*modelId\)\s*=>/);
assert.match(agentsHook, /const\s+getAgentModelOptions\s*=\s*\(agent\)\s*=>/);
assert.match(agentsHook, /agentApi\.getAgents\(\)/);
assert.match(agentsHook, /agentApi\.saveAgentConfig/);
assert.match(agentsHook, /request\(['"]\/ai\/models['"]\)/);
assert.match(agentsHook, /imageModelOptions\.value/);
assert.match(agentsHook, /textModelOptions\.value/);
assert.match(agentsHook, /apiModel:\s*model\.api_model\s*\|\|\s*model\.apiModel\s*\|\|\s*''/);
assert.match(agentsHook, /showToast\(`Agent \[\$\{agent\.name\}\] 已切换至 \$\{modelId\}`,\s*'success'\)/);
assert.match(html, /@change="updateAgentModel\(agent,\s*\$event\.target\.value\)"/);
assert.match(html, /v-for="model in getAgentModelOptions\(agent\)"/);
assert.match(html, /v-for="model in activeAgentModelOptions"/);
assert.match(html, /agent\.avatarShellClass/);
assert.match(html, /class="ph"/);
assert.equal((html.match(/v-if="toast\.show"/g) || []).length, 1, 'should render a single global toast container');

assert.match(chatModes, /agent_id:\s*agent\?\.id/);
assert.match(chatModes, /agent_model:\s*agent\?\.model/);
assert.match(chatModes, /agent_prompt:\s*agent\?\.prompt/);
assert.match(streamChat, /buildChatPayload\(\{[^}]*agent/s);
assert.match(useChat, /agentResolver/);
assert.match(useChat, /getActiveChatAgent/);
assert.match(main, /useChat\(auth\.currentUser,\s*showToast,\s*agentsState\.getAgentInfo\)/);
assert.match(visualGuide, /imageModel/);
assert.match(visualGuide, /image_model:\s*imageModel/);
assert.match(streamChat, /data\.type === 'model_unavailable'/);
assert.match(streamChat, /onModelUnavailable\(data\.model\)/);
assert.match(streamChat, /typeof onModelUnavailable === 'function'/);
assert.match(useChat, /showToast\(`模型 \$\{modelId\} 当前不可用，请更换模型`, 'error'\)/);

const mergedTextModels = aiModelsModule.mergeModelOptions(
  [{ id: 'kimi-k2.7-code', label: 'kimi-k2.7-code from backend' }],
  aiModelsModule.TEXT_MODEL_OPTIONS,
);
assert.equal(
  mergedTextModels.some((model) => model.id === 'glm-4.6v'),
  true,
  'backend model responses should not remove local fallback Zhipu models',
);
assert.equal(
  mergedTextModels.find((model) => model.id === 'kimi-k2.7-code')?.label,
  'kimi-k2.7-code from backend',
  'backend model metadata should win for models it returns',
);

console.log('agentModelRouting tests passed');
