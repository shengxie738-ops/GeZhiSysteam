import assert from 'node:assert/strict';

import {
  getDashboardGreeting,
  getUserDisplayName,
} from '../js/utils/dashboardGreeting.js';

assert.equal(getUserDisplayName({ username: '23001020119', real_name: '黎明' }), '黎明');
assert.equal(getUserDisplayName({ username: '23001020119', realName: '李华' }), '李华');
assert.equal(getUserDisplayName({ username: '23001020119', fullName: '王芳' }), '王芳');
assert.equal(getUserDisplayName({ username: '23001020119' }), '23001020119');
assert.equal(getUserDisplayName(null), '同学');

assert.equal(getDashboardGreeting(new Date('2026-07-04T00:30:00')), '请注意休息！');
assert.equal(getDashboardGreeting(new Date('2026-07-04T06:00:00')), '早上好');
assert.equal(getDashboardGreeting(new Date('2026-07-04T12:00:00')), '下午好');
assert.equal(getDashboardGreeting(new Date('2026-07-04T18:00:00')), '晚上好');
assert.equal(getDashboardGreeting(new Date('2026-07-04T23:59:59')), '晚上好');

console.log('dashboardGreeting tests passed');
