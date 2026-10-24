import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../widgets/FinanceChassisPolicy.js', import.meta.url), 'utf8')
  .replace(/^\.pragma library\s*/, '');
const policy = {};
vm.runInNewContext(source, policy, { filename: 'FinanceChassisPolicy.js' });

assert.equal(policy.normalize('unsupported'), 'compact');
assert.equal(policy.step('compact', 1), 'expanded');
assert.equal(policy.step('expanded', 1), 'fullscreen');
assert.equal(policy.step('fullscreen', 1), 'fullscreen');
assert.equal(policy.step('fullscreen', -1), 'expanded');
assert.equal(policy.step('expanded', -1), 'compact');
assert.equal(policy.step('compact', -1), 'compact');
assert.equal(policy.step('unknown', 1), 'expanded');

function frame(mode, width, height) {
  const value = policy.frame(mode, width, height, 12);
  return [value.width, value.height];
}
assert.deepEqual(frame('compact', 2560, 1440), [432, 768]);
assert.deepEqual(frame('expanded', 2560, 1440), [1000, 900]);
assert.deepEqual(frame('fullscreen', 2560, 1440), [2536, 1416]);
assert.deepEqual(frame('expanded', 1360, 768), [1000, 744]);
assert.deepEqual(frame('fullscreen', 1360, 768), [1336, 744]);
assert.deepEqual(frame('compact', 320, 480), [296, 456]);
assert.deepEqual(frame('compact', 0, NaN), [432, 768]);

assert.equal(policy.leftMargin('compact', 900, 2560, 456), 672);
assert.equal(policy.leftMargin('expanded', 900, 1360, 1024), 336);
assert.equal(policy.leftMargin('fullscreen', 900, 1360, 1360), 0);
assert.equal(policy.topMargin('compact', 82, 1440, 792, 12), 70);
assert.equal(policy.topMargin('expanded', 82, 768, 768, 12), 0);
assert.equal(policy.topMargin('fullscreen', 82, 1440, 1440, 12), 0);

console.log('FinanceW M0 chassis policy: PASS');
