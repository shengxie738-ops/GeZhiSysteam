import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const studentExamCenter = readFileSync(new URL('js/components/StudentExamCenter.js', frontendRoot), 'utf8');

assert.match(
  studentExamCenter,
  /const pendingExam\s*=\s*ref\(null\)/,
  '进入考试前应先保存待确认考试，而不是直接创建 attempt',
);

assert.match(
  studentExamCenter,
  /@click="requestExamEntry\(exam\)"/,
  '考试列表的“进入考试”按钮必须先打开确认框',
);

assert.match(
  studentExamCenter,
  /确定进入考试？/,
  '确认框必须明确询问是否进入考试',
);

assert.match(
  studentExamCenter,
  /requestFullscreen\(\)/,
  '确认进入后必须请求浏览器全屏',
);

for (const eventName of ['copy', 'cut', 'paste', 'contextmenu', 'visibilitychange', 'fullscreenchange', 'blur']) {
  assert.match(
    studentExamCenter,
    new RegExp(`addEventListener\\('${eventName}'`),
    `考试中必须监听 ${eventName} 事件`,
  );
}

assert.match(
  studentExamCenter,
  /event\.preventDefault\(\)/,
  '复制、粘贴、右键等受限操作必须被阻止',
);

assert.match(
  studentExamCenter,
  /autoSubmitForSecurity/,
  '切屏、失焦或退出全屏必须触发自动交卷流程',
);

assert.match(
  studentExamCenter,
  /submitReason:\s*reason/,
  '自动交卷必须向提交接口携带触发原因',
);

console.log('studentExamSecurity tests passed');
