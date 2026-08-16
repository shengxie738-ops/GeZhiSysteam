import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const read = (path) => readFileSync(resolve(root, path), 'utf8');

const auth = read('js/hooks/useAuth.js');
const main = read('js/main.js');
const index = read('index.html');
const component = read('js/components/TeacherAiLessonPrep.js');
const api = read('js/api/teacherLessonPrep.js');

assert.match(auth, /id:\s*['"]t_lesson_prep['"]/);
assert.match(auth, /name:\s*['"]AI备课['"]/);
const studentMenuBlock = auth.slice(auth.indexOf('const studentMenus'), auth.indexOf('const teacherMenus'));
assert.doesNotMatch(studentMenuBlock, /t_lesson_prep|AI备课/);

assert.match(main, /import TeacherAiLessonPrep from ['"].\/components\/TeacherAiLessonPrep\.js['"]/);
assert.match(main, /TeacherAiLessonPrep,/);
assert.match(index, /<teacher-ai-lesson-prep/);
assert.match(index, /currentView === ['"]t_lesson_prep['"]/);

for (const route of ['/teacher/lesson-prep/config', '/teacher/lesson-prep/resources', '/teacher/lesson-prep/search', '/teacher/lesson-prep/summarize', '/teacher/lesson-prep/generate', '/teacher/lesson-prep/drafts']) {
    assert.ok(api.includes(route), `missing API route: ${route}`);
}
assert.match(api, /apiRequest/);
assert.doesNotMatch(api, /API[_ -]?KEY|open\.bigmodel\.cn|glm.*Bearer/i);

for (const text of ['AI备课中心', '课件资源', '生成教案', '总结课件', '保存草稿', '命中课件依据', 'glm-4.5-air']) {
    assert.ok(component.includes(text), `missing component text: ${text}`);
}
assert.match(component, /teacherLessonPrepApi\.listResources/);
assert.match(component, /teacherLessonPrepApi\.generate/);
assert.match(component, /teacherLessonPrepApi\.saveDraft/);
assert.match(component, /MAX_SELECTED_RESOURCES\s*=\s*10/);
assert.match(component, /const\s+expandedCourses\s*=\s*ref\(/);
assert.match(component, /ai_ready/);
assert.match(component, /AI_LESSON_PREP_API_KEY/);
assert.match(component, /const\s+groupedResources\s*=\s*computed\(/);
assert.match(component, /const\s+toggleCourse\s*=\s*\(/);
assert.match(component, /group\.course/);
assert.match(component, /group\.items\.length/);
assert.match(component, /ph-caret-(?:down|right)/);
assert.match(component, /const\s+resetLesson\s*=\s*async\s*\(\)/);
assert.match(component, /if\s*\(!activeDraftId\.value\)/);
assert.match(component, /新建空白设计/);
assert.match(component, /min-h-0\s+flex-1\s+overflow-y-auto\s+p-3/);
assert.match(component, /class="min-h-0\s+xl:relative"/);
assert.match(component, /<aside class="[^"]*xl:absolute[^"]*xl:inset-0[^"]*xl:overflow-hidden/);
assert.doesNotMatch(component, /xl:h-\[calc\(100vh-190px\)\]/);
assert.doesNotMatch(component, /<main class="[^"]*overflow-y-auto/);
assert.doesNotMatch(component, /<aside class="[^"]*gap-4[^"]*overflow-y-auto/);
assert.doesNotMatch(component, /😀|🚀|✨|📚|🤖/u);
assert.doesNotMatch(component, /id:\s*['"]ppt['"]\s*,\s*label:\s*['"]PPT['"]/);
assert.doesNotMatch(component, /grid-cols-4/);
assert.match(component, /grid-cols-3/);
assert.match(component, /PPT\/PPTX/);

assert.ok(api.includes('/teacher/lesson-prep/export-docx'), 'missing API route: /teacher/lesson-prep/export-docx');
assert.match(api, /isStream:\s*true/);
assert.match(api, /import\s*\{[^}]*\brequest\b[^}]*\}\s*from\s*['"]\.\.\/utils\/request\.js['"]/);

for (const text of ['导出Word', 'data-testid="lesson-prep-export-docx"']) {
    assert.ok(component.includes(text), `missing component text: ${text}`);
}
assert.match(component, /const\s+exporting\s*=\s*ref\(false\)/);
assert.match(component, /const\s+exportWord\s*=\s*async\s*\(\)/);
assert.match(component, /teacherLessonPrepApi\.exportDocx/);
assert.match(component, /:disabled="exporting\s*\|\|\s*!hasLessonContent"/);
assert.match(component, /URL\.createObjectURL/);
assert.match(component, /ph-file-doc/);

// 导出 payload 必须与后端 LessonPlanExportRequest(StrictRequestModel, extra=forbid) 契约对齐
assert.match(component, /const\s+clipText\s*=\s*\(value,\s*max\)\s*=>/);
assert.match(component, /title:\s*clipText\(lesson\.title,\s*200\)/);
assert.match(component, /duration_minutes:\s*Math\.min\(600,\s*Math\.max\(1,\s*Number\(lesson\.durationMinutes\)\s*\|\|\s*45\)\)/);
assert.match(component, /content:\s*clipText\(item\.content,\s*4000\)\s*\|\|\s*'—'/);
assert.match(component, /summary:\s*String\(summary\.value\s*\|\|\s*''\)\.slice\(0,\s*8000\)/);
assert.match(component, /name:\s*clipText\(item\.name,\s*200\)/);
assert.match(component, /page:\s*Math\.max\(0,\s*Math\.round\(Number\(item\.page\)\s*\|\|\s*0\)\)/);
assert.match(component, /excerpt:\s*clipText\(item\.excerpt,\s*4000\)/);
{
    const exportBlock = component.slice(component.indexOf('const exportWord'), component.indexOf('const resetLesson'));
    const citationKeys = exportBlock.slice(exportBlock.indexOf('citations: citations.value.map'), exportBlock.indexOf('})).slice(0, 50)'));
    assert.ok(!/resourceId|course:|score/.test(citationKeys), '导出 citations 不得携带 resourceId/course/score 多余键');
}

console.log('teacher AI lesson prep static tests passed');
