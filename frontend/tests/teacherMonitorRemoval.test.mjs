import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const frontendRoot = new URL('../', import.meta.url);
const authHook = readFileSync(new URL('js/hooks/useAuth.js', frontendRoot), 'utf8');
const appTemplate = readFileSync(new URL('index.html', frontendRoot), 'utf8');
const codingSandbox = readFileSync(new URL('js/components/CodingSandbox.js', frontendRoot), 'utf8');

assert.doesNotMatch(authHook, /id:\s*['"]t_monitor['"]/);
assert.doesNotMatch(appTemplate, /currentView\s*===\s*['"]t_monitor['"]/);
assert.doesNotMatch(`${authHook}\n${appTemplate}\n${codingSandbox}`, /全息监控/);

console.log('teacher monitor removal static tests passed');
