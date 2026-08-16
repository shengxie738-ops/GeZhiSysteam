const DISPLAY_NAME_KEYS = [
  'real_name',
  'realName',
  'full_name',
  'fullName',
  'display_name',
  'displayName',
  'name',
  'username',
];

function cleanText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

export function getUserDisplayName(user) {
  if (!user || typeof user !== 'object') {
    return '同学';
  }

  for (const key of DISPLAY_NAME_KEYS) {
    const value = cleanText(user[key]);
    if (value) return value;
  }

  return '同学';
}

export function getDashboardGreeting(now = new Date()) {
  const date = now instanceof Date ? now : new Date(now);
  const hour = date.getHours();

  if (!Number.isFinite(hour)) {
    return '早上好';
  }
  if (hour < 6) {
    return '请注意休息！';
  }
  if (hour < 12) {
    return '早上好';
  }
  if (hour < 18) {
    return '下午好';
  }
  return '晚上好';
}
