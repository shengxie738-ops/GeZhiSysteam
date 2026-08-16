import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const studentHomework = readFileSync(new URL('js/components/StudentHomework.js', frontendRoot), 'utf8');

const suggestionBarMatch = studentHomework.match(
  /<section[^>]*data-testid="student-homework-alina-suggestion"[^>]*class="([^"]+)"[^>]*>/,
);

assert.ok(suggestionBarMatch, 'Alina homework suggestion bar should have a stable test id');

const className = suggestionBarMatch[1];

assert.match(className, /\bbg-white\/90\b/);
assert.match(className, /\bborder-white\/90\b/);
assert.doesNotMatch(className, /\bbg-indigo-500\/5\b/);

console.log('studentHomeworkSuggestionBar tests passed');
