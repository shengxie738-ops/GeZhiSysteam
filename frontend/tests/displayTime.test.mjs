import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { formatDisplayDateTime } from '../js/utils/timeFormat.js';

assert.equal(
  formatDisplayDateTime('2026-07-01T09:30:00+08:00'),
  '2026年7月1日09点30分',
);
assert.equal(
  formatDisplayDateTime('2026-07-01 09:30:00'),
  '2026年7月1日09点30分',
);
assert.equal(
  formatDisplayDateTime('2026年7月1日09点30分'),
  '2026年7月1日09点30分',
);
assert.equal(formatDisplayDateTime('15:31'), '15:31');

const codingSandbox = readFileSync(new URL('../js/components/CodingSandbox.js', import.meta.url), 'utf8');
const mistakeBook = readFileSync(new URL('../js/components/StudentMistakeBook.js', import.meta.url), 'utf8');

assert.match(codingSandbox, /formatDisplayDateTime/, 'Coding sandbox should format all displayed backend times');
assert.match(mistakeBook, /formatDisplayDateTime/, 'Mistake book should format last wrong times before display');
assert.doesNotMatch(
  codingSandbox,
  /\{\{\s*(?:project\.repositoryCard\.updatedAt|file\.updatedAt|event\.time|pr\.updatedAt|item\.created_at)\s*\}\}/,
  'Known ISO-bearing fields must not be rendered raw in CodingSandbox templates',
);
assert.doesNotMatch(
  mistakeBook,
  /\{\{\s*(?:mistake\.lastWrongAt|activeMistake\.lastWrongAt)\s*\}\}/,
  'Mistake timestamps must not be rendered raw in StudentMistakeBook templates',
);

console.log('display time formatting tests passed');
