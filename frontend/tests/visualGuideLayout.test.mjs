import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const useChat = readFileSync(new URL('../js/hooks/useChat.js', import.meta.url), 'utf8');

assert.match(html, /class="visual-guide-image-shell"/);
assert.match(html, /等待输入学习问题/);
assert.match(html, /AI 引导图生成师可将问题转为可视化图片/);
assert.match(html, /在左侧文本台输入问题后，Mira 会生成概念图；点击步骤图可生成结构化步骤图。/);
assert.match(html, /暂无生成历史/);
assert.match(html, /class="visual-guide-bg-layer"/);
assert.match(html, /class="visual-guide-svg-layer"/);
assert.match(html, /class="visual-guide-image-shell architecture-guide-shell"/);
assert.match(html, /class="architecture-guide-svg-layer"/);
assert.match(html, /class="architecture-tree-text"/);
assert.match(html, /class="visual-guide-expand-btn"/);
assert.match(html, /@click="openVisualGuideViewer"/);
assert.match(html, /v-if="showVisualGuideViewer"/);
assert.match(html, /class="visual-guide-viewer-modal"/);
assert.match(html, /class="visual-guide-viewer-canvas"/);
assert.match(html, /visualGuideImage\.svg/);
assert.match(html, /visualGuideImage\.renderedSvg/);
assert.match(html, /visualGuideImage\?\.renderError/);
assert.match(html, /visualGuideImage\.treeText/);
assert.match(html, /visualGuideImage\.mermaid/);
assert.match(html, /@click="closeVisualGuideViewer"/);
assert.match(html, /visualGuideImage\.backgroundUrl \|\| visualGuideImage\.backgroundBase64/);
assert.match(html, /Prof\. X 正在生成代码架构图/);
assert.match(html, /步骤图使用文本模型，不调用生图模型/);
assert.doesNotMatch(html, /visualGuideImage\.alt"\s+class="absolute inset-0 w-full h-full object-cover"/);
assert.match(html, /v-if="!visualGuideImage && visualGuidePrompt\.trim\(\)"/);
const switchVisualGuideTypeBody = useChat.match(/const switchVisualGuideType = \(type\) => \{([\s\S]*?)\n    \};/)?.[1] || '';
assert.match(switchVisualGuideTypeBody, /visualGuideType\.value = type;/);
assert.match(switchVisualGuideTypeBody, /generateVisualGuide\(visualGuidePrompt\.value,\s*\{\s*reason:\s*'tab-demand'\s*\}\);/);

console.log('visualGuideLayout tests passed');
