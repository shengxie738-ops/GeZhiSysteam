import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const indexHtml = readFileSync(new URL('index.html', frontendRoot), 'utf8');
const useAuth = readFileSync(new URL('js/hooks/useAuth.js', frontendRoot), 'utf8');
const repositoryApi = readFileSync(new URL('js/api/repository.js', frontendRoot), 'utf8');

assert.match(useAuth, /id:\s*'academic-space'[\s\S]*name:\s*'学术空间'/);
assert.doesNotMatch(useAuth, /id:\s*'repository'[\s\S]*name:\s*'代码仓库'/);
assert.doesNotMatch(useAuth, /id:\s*'forum'[\s\S]*name:\s*'论坛'/);

assert.match(useAuth, /id:\s*'t_space'[\s\S]*name:\s*'空间管理'/);
assert.doesNotMatch(useAuth, /id:\s*'t_forum'[\s\S]*name:\s*'论坛管理'/);
assert.doesNotMatch(useAuth, /id:\s*'t_repository'[\s\S]*name:\s*'仓库审核'/);

assert.match(indexHtml, /<student-academic-space\s+v-if="currentView === 'academic-space'"/);
assert.match(indexHtml, /<teacher-space-manager\s+v-if="currentView === 't_space'"/);

const studentAcademicSpacePath = new URL('js/components/StudentAcademicSpace.js', frontendRoot);
const studentCodeRepositoryPath = new URL('js/components/StudentCodeRepository.js', frontendRoot);
const teacherSpaceManagerPath = new URL('js/components/TeacherSpaceManager.js', frontendRoot);
assert.equal(existsSync(studentAcademicSpacePath), true);
assert.equal(existsSync(studentCodeRepositoryPath), true);
assert.equal(existsSync(teacherSpaceManagerPath), true);

const studentAcademicSpace = readFileSync(studentAcademicSpacePath, 'utf8');
assert.match(studentAcademicSpace, /个人主页/);
assert.match(studentAcademicSpace, /代码仓库/);
assert.match(studentAcademicSpace, /代码拉取请求/);
assert.match(studentAcademicSpace, /论坛/);
assert.match(studentAcademicSpace, /收藏夹/);
assert.match(studentAcademicSpace, /StudentCodeRepository/);
assert.match(studentAcademicSpace, /StudentForum/);
assert.match(studentAcademicSpace, /getUserDisplayName/);
assert.match(studentAcademicSpace, /userApi\.getUserInfo\(currentUserId\.value\)/);
assert.match(studentAcademicSpace, /profileUser/);
assert.match(studentAcademicSpace, /looksLikeStudentId/);
assert.match(studentAcademicSpace, /\{\{ currentUserDisplayName \}\} 的个人主页/);
assert.doesNotMatch(studentAcademicSpace, /\{\{ currentUserId \}\} 的个人主页/);
assert.match(studentAcademicSpace, /max-w-\[1600px\] mx-auto grid grid-cols-1 xl:grid-cols-\[1fr_360px\] gap-5/);
assert.match(studentAcademicSpace, /max-w-\[1600px\] mx-auto flex flex-col gap-5/);
assert.match(studentAcademicSpace, /class="glass-panel-liquid p-5"/);
assert.match(studentAcademicSpace, /text-2xl font-bold text-slate-900/);
assert.match(studentAcademicSpace, /text-\[10px\] text-slate-500 font-bold mt-1/);

const studentCodeRepository = readFileSync(studentCodeRepositoryPath, 'utf8');
assert.doesNotMatch(studentCodeRepository, /downloadProject/);
assert.doesNotMatch(studentCodeRepository, /repositoryApi\.getDownload/);
assert.doesNotMatch(studentCodeRepository, /currentProject\.htmlUrl/);
assert.doesNotMatch(studentCodeRepository, /ph-download-simple/);
assert.doesNotMatch(studentCodeRepository, /ph-arrow-square-out/);
assert.match(studentCodeRepository, /openReport\(currentProject\)/);
assert.match(studentCodeRepository, /ph-flag/);

const teacherSpaceManager = readFileSync(teacherSpaceManagerPath, 'utf8');
assert.match(teacherSpaceManager, /空间管理/);
assert.match(teacherSpaceManager, /TeacherForumManager/);
assert.match(teacherSpaceManager, /TeacherRepositoryManager/);

assert.match(repositoryApi, /collaborators/);
assert.match(repositoryApi, /visibility/);

console.log('academicSpace tests passed');
