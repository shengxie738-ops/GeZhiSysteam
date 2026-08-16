import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const mainJs = readFileSync(new URL('js/main.js', frontendRoot), 'utf8');

const handlerMatch = mainJs.match(/const handlePreviewOrLearn = \(res\) => \{[\s\S]*?\n        \};/);

assert.ok(handlerMatch, 'handlePreviewOrLearn handler should exist');

const handlerSource = handlerMatch[0];

assert.match(handlerSource, /coursesState\.activeNodeDetails\.value\s*=\s*null/);
assert.doesNotMatch(handlerSource, /(?<!coursesState\.)\bactiveNodeDetails\.value/);

console.log('pathway preview static tests passed');
