import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const appHtml = readFileSync(new URL('index.html', frontendRoot), 'utf8');
const mistakeBook = readFileSync(new URL('js/components/StudentMistakeBook.js', frontendRoot), 'utf8');
const examApi = readFileSync(new URL('js/api/examCenter.js', frontendRoot), 'utf8');
const mockData = readFileSync(new URL('js/data/mockData.js', frontendRoot), 'utf8');

assert.match(
  mockData,
  /id:\s*'agent_mistake_analyst'/,
  'Agent workshop should include the dedicated mistake analyst agent',
);

assert.match(
  mockData,
  /name:\s*'错题分析师'/,
  'Mistake analyst agent should be visible as 错题分析师',
);

assert.match(
  appHtml,
  /:mistake-agent-config="getAgentInfo\('agent_mistake_analyst'\)"/,
  'Mistake book page must receive the mistake analyst agent config from the workshop',
);

assert.doesNotMatch(
  examApi,
  /requestJson\(`\/exams\/mistakes\/\$\{encodeURIComponent\(mistakeId\)\}\/ai-analysis`[\s\S]*buildMockAiAnalysis/,
  'AI mistake analysis must not silently fall back to mock text when the backend is unavailable',
);

assert.match(
  mistakeBook,
  /formatAiPath/,
  'AI review path should be rendered through a formatter so non-array model output cannot break the UI',
);

assert.match(
  mistakeBook,
  /mistakeAgentConfig/,
  'Mistake book should accept a dedicated mistake analyst agent config',
);

for (const field of ['agentId', 'agentName', 'agentModel', 'agentPrompt']) {
  assert.match(
    mistakeBook,
    new RegExp(`${field}:`),
    `AI mistake analysis request should include ${field}`,
  );
}

assert.match(
  mistakeBook,
  /whitespace-pre-line/,
  'AI analysis text blocks must preserve model line breaks and expand vertically',
);

assert.match(
  mistakeBook,
  /break-words/,
  'AI analysis text blocks must break long model output instead of overflowing the card',
);

assert.match(
  mistakeBook,
  /items-stretch/,
  'AI analysis grid cards should stretch to the generated content height',
);

console.log('studentMistakeBookAi tests passed');
