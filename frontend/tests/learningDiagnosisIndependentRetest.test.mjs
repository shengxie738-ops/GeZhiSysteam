import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const page = readFileSync(new URL('../js/components/LearningIndependentRetestPage.js', import.meta.url), 'utf8');

for (const token of [
  'INDEPENDENT RETEST', '独立复测 · 多边界场景变式题', '理解题意', '编写代码', '独立复测', '更新诊断',
  '普通场景 NORMAL', '边界场景 BOUNDARY', '异常场景 EXCEPTION', 'solution.py', '运行验证',
  '提交独立复测', '测试结果', '运行记录', 'INDEPENDENT AGENT', 'Prof. X · 复测监考官',
  '提示已锁定', '独立性保护', '结果将作为独立证据参与掌握度计算', 'grid-cols-1 xl:grid-cols-[315px_minmax(0,1fr)_358px]'
]) assert.match(page, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));

assert.match(page, /props:\s*\{\s*task:/);
assert.match(page, /test_summary/);
assert.match(page, /test_cases/);
console.log('learningDiagnosisIndependentRetest tests passed');
