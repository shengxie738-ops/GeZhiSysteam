import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const studentForum = readFileSync(new URL('js/components/StudentForum.js', frontendRoot), 'utf8');

assert.match(
  studentForum,
  /class="[^"]*glass-panel-liquid[^"]*cursor-pointer[^"]*shrink-0[^"]*"/,
  '论坛帖子卡片必须禁用 flex-shrink，话题多时应滚动列表而不是压扁卡片',
);

console.log('studentForumLayout tests passed');
