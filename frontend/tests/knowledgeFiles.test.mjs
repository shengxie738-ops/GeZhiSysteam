import assert from 'node:assert/strict';

import {
  ACCEPTED_KNOWLEDGE_FILE_EXTENSIONS,
  getKnowledgeFileExtension,
  getKnowledgeFileStatusLabel,
  isSupportedKnowledgeFile,
} from '../js/utils/knowledgeFiles.js';

assert.equal(getKnowledgeFileExtension({ name: 'lesson.PPTX' }), 'pptx');
assert.equal(getKnowledgeFileExtension({ name: 'scan.image.png' }), 'png');
assert.equal(isSupportedKnowledgeFile({ name: 'notes.pdf' }), true);
assert.equal(isSupportedKnowledgeFile({ name: 'diagram.jpg' }), false);
assert.equal(isSupportedKnowledgeFile({ name: 'slides.ppt' }), false);
assert.equal(isSupportedKnowledgeFile({ name: 'archive.zip' }), false);
assert.equal(ACCEPTED_KNOWLEDGE_FILE_EXTENSIONS, '.pdf');
assert.equal(ACCEPTED_KNOWLEDGE_FILE_EXTENSIONS.includes('.pdf'), true);
assert.equal(ACCEPTED_KNOWLEDGE_FILE_EXTENSIONS.includes('.pptx'), false);
assert.equal(ACCEPTED_KNOWLEDGE_FILE_EXTENSIONS.includes('.png'), false);
assert.equal(getKnowledgeFileStatusLabel('parsed'), '已同步');
assert.equal(getKnowledgeFileStatusLabel('failed'), '解析失败');
assert.equal(getKnowledgeFileStatusLabel('queued'), '待解析');
assert.equal(getKnowledgeFileStatusLabel('cancelled'), '已取消');
assert.equal(getKnowledgeFileStatusLabel('unknown'), '解析中');

console.log('knowledgeFiles tests passed');
