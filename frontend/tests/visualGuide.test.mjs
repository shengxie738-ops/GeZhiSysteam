import assert from 'node:assert/strict';

import {
  createLocalVisualGuide,
  getVisualGuideSourceLabel,
  normalizeVisualGuidePayload,
  resolveVisualGuideState,
} from '../js/api/visualGuide.js';

const structuredGuide = normalizeVisualGuidePayload({
  status: 'success',
  svg: '<svg><text>先建立定义</text></svg>',
  provider: 'structured_svg',
  image_alt: '栈和队列 概念引导图',
  caption: 'Mira 已生成概念引导图。',
  nodes: ['先建立定义', '拆解组成部分'],
  metadata: { render_mode: 'structured_svg' },
});

assert.equal(structuredGuide.svg.includes('先建立定义'), true);
assert.equal(structuredGuide.provider, 'structured_svg');
assert.equal(structuredGuide.source, 'backend');

const hybridGuide = normalizeVisualGuidePayload({
  status: 'success',
  svg: '<svg></svg>',
  background_url: 'https://example.com/bg.png',
  provider: 'structured_svg+qwen',
});

assert.equal(hybridGuide.backgroundUrl, 'https://example.com/bg.png');
assert.equal(hybridGuide.provider, 'structured_svg+qwen');

const base64Guide = normalizeVisualGuidePayload({
  status: 'success',
  background_base64: 'abc123',
  svg: '<svg></svg>',
  provider: 'structured_svg+qwen',
});

assert.equal(base64Guide.backgroundBase64, 'data:image/png;base64,abc123');

const architectureGuide = normalizeVisualGuidePayload({
  status: 'success',
  provider: 'prof_x_text_architecture',
  diagram_type: 'mermaid',
  mermaid: 'flowchart TD\n  A[入口] --> B[服务层]',
  tree_text: 'frontend/\n  js/',
  caption: 'Prof. X 已生成代码架构图。',
  nodes: ['入口', '服务层'],
});

assert.equal(architectureGuide.provider, 'prof_x_text_architecture');
assert.equal(architectureGuide.source, 'backend-architecture');
assert.equal(architectureGuide.diagramType, 'mermaid');
assert.match(architectureGuide.mermaid, /flowchart TD/);
assert.match(architectureGuide.treeText, /frontend/);

const localConcept = createLocalVisualGuide('解释一下什么是 Transformer 架构', 'concept');
assert.equal(localConcept.title, '概念图：Transformer');
assert.equal(localConcept.center, 'Transformer');

const structuredState = resolveVisualGuideState({
  localGuide: localConcept,
  backendGuide: { provider: 'structured_svg', svg: '<svg></svg>', caption: 'Mira 已生成概念引导图。', nodes: ['A'], edges: ['B'] },
});
assert.equal(structuredState.status, 'ready');
assert.equal(structuredState.historySource, 'structured_svg');
assert.match(structuredState.logMessage, /精准 SVG 引导图/);

const hybridState = resolveVisualGuideState({
  localGuide: localConcept,
  backendGuide: { provider: 'structured_svg+qwen', svg: '<svg></svg>', backgroundUrl: 'https://example.com/bg.png' },
});
assert.equal(hybridState.status, 'ready');
assert.match(hybridState.logMessage, /千问背景/);

const localState = resolveVisualGuideState({ localGuide: localConcept, backendGuide: null });
assert.equal(localState.status, 'fallback');
assert.equal(localState.historySource, 'local');

const localSteps = createLocalVisualGuide('什么是栈和队列？', 'steps');
const stepsFallbackState = resolveVisualGuideState({ localGuide: localSteps, backendGuide: null });
assert.equal(stepsFallbackState.status, 'fallback');
assert.equal(stepsFallbackState.historySource, 'local_architecture');
assert.equal(stepsFallbackState.image.provider, 'local_text_architecture');
assert.match(stepsFallbackState.image.mermaid, /flowchart TD/);
assert.match(stepsFallbackState.image.mermaid, /栈和队列/);
assert.equal(getVisualGuideSourceLabel(stepsFallbackState.image), 'Prof.X代码架构图');

assert.equal(getVisualGuideSourceLabel({ svg: '<svg></svg>', backgroundUrl: 'https://example.com/bg.png' }), '精准引导图+千问背景');
assert.equal(getVisualGuideSourceLabel({ svg: '<svg></svg>' }), '精准引导图');
assert.equal(getVisualGuideSourceLabel({ provider: 'fallback_svg', svg: '<svg></svg>' }), '精准引导图');
assert.equal(getVisualGuideSourceLabel({ provider: 'prof_x_text_architecture', mermaid: 'flowchart TD' }), 'Prof.X代码架构图');
assert.equal(getVisualGuideSourceLabel({ provider: 'qwen' }), '千问AI图');
assert.equal(getVisualGuideSourceLabel(null), '本地草图');

console.log('visualGuide tests passed');
