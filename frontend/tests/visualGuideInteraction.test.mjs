import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../js/hooks/useChat.js', import.meta.url), 'utf8');

assert.match(source, /const visualGuidePrompt = ref\(''\);/);
assert.match(source, /const visualGuideHistory = ref\(\[\]\);/);
assert.doesNotMatch(source, /const visualGuidePrompt = ref\('.*Transformer.*'\);/);
assert.match(source, /const shouldTriggerVisualGuideGeneration = \(prompt\) => \{/);

const switchMatch = source.match(/const switchVisualGuideType = \(type\) => \{([\s\S]*?)\n    \};/);
assert.ok(switchMatch, 'switchVisualGuideType definition should exist');
assert.match(switchMatch[1], /visualGuideType\.value = type;/);
assert.match(switchMatch[1], /if \(!visualGuidePrompt\.value\.trim\(\)\) return;/);
assert.match(switchMatch[1], /generateVisualGuide\(visualGuidePrompt\.value,\s*\{\s*reason:\s*'tab-demand'\s*\}\);/);

const regenerateMatch = source.match(/const regenerateVisualGuide = \(\) => \{([\s\S]*?)\n    \};/);
assert.ok(regenerateMatch, 'regenerateVisualGuide definition should exist');
assert.match(regenerateMatch[1], /if \(!visualGuidePrompt\.value\.trim\(\)\) return;/);
assert.match(regenerateMatch[1], /generateVisualGuide\(visualGuidePrompt\.value,\s*\{\s*reason:\s*'regenerate',\s*force:\s*true\s*\}\);/);

const sendMatch = source.match(/const sendMessage = \(\) => \{([\s\S]*?)\n    \};/);
assert.ok(sendMatch, 'sendMessage definition should exist');
assert.match(sendMatch[1], /agentMode\.value !== 'rag' && shouldTriggerVisualGuideGeneration\(prompt\)/);
assert.match(sendMatch[1], /visualGuideType\.value = 'concept';/);
assert.match(sendMatch[1], /generateVisualGuide\(prompt,\s*\{\s*reason:\s*'student-question',\s*force:\s*true\s*\}\);/);

console.log('visualGuideInteraction tests passed');
