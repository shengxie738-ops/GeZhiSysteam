import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const studentForum = readFileSync(new URL('js/components/StudentForum.js', frontendRoot), 'utf8');

assert.match(studentForum, /import\s+\{\s*toBackendAssetUrl\s*\}\s+from\s+['"]\.\.\/config\/env\.js['"]/);
assert.match(studentForum, /return\s+toBackendAssetUrl\(path\);/);
assert.doesNotMatch(studentForum, /localhost:8000/);

console.log('studentForumAvatar tests passed');
