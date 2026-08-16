import assert from 'node:assert/strict';
import { ref } from 'vue';

globalThis.localStorage = {
  getItem() {
    return null;
  },
  setItem() {},
};

globalThis.window = {
  location: {
    origin: 'http://127.0.0.1:5173',
    href: 'http://127.0.0.1:5173/app/index.html',
  },
};

const { useCourses } = await import('../js/hooks/useCourses.js');

const coursesState = useCourses(ref([]), ref('pathway'), () => {});

globalThis.fetch = async () => ({
  ok: true,
  headers: {
    get(name) {
      return name.toLowerCase() === 'content-type' ? 'text/html' : null;
    },
  },
});

await coursesState.previewFile({
  name: '13-uncertainty.ppt',
  type: 'ppt',
  path: 'courses/AI_technology/13-uncertainty.ppt',
});

assert.equal(coursesState.previewMode.value, 'office');
assert.match(coursesState.previewFileUrl.value, /^https:\/\/view\.officeapps\.live\.com\//);
assert.doesNotMatch(coursesState.previewFileUrl.value, /13-uncertainty\.pdf$/);
assert.equal(
  new URL(coursesState.previewFileUrl.value).searchParams.get('src'),
  'http://127.0.0.1:5173/app/courses/AI_technology/13-uncertainty.ppt',
);

console.log('course preview tests passed');
