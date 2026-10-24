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
  const value = policy.frame(mode, width, height, 12, 9, 8);
  return [value.width, value.height];
}
assert.deepEqual(frame('compact', 2560, 1440), [432, 790]);
assert.deepEqual(frame('expanded', 2560, 1440), [1000, 900]);
assert.deepEqual(frame('fullscreen', 2560, 1440), [2536, 1341]);
assert.deepEqual(frame('fullscreen', 2560, 1600), [2536, 1341]);
assert.deepEqual(frame('expanded', 1360, 768), [1000, 751]);
assert.deepEqual(frame('fullscreen', 1360, 768), [1336, 751]);
assert.deepEqual(frame('compact', 320, 480), [296, 463]);
assert.deepEqual(frame('compact', 0, NaN), [432, 751]);
assert.deepEqual(frame('compact', 1360, 768), [432, 751]);

assert.equal(policy.leftMargin('compact', 900, 2560, 456), 672);
assert.equal(policy.leftMargin('expanded', 900, 1360, 1024), 336);
assert.equal(policy.leftMargin('fullscreen', 900, 1360, 1360), 0);
assert.equal(policy.topMargin('compact', 82, 1440, 792, 12), 70);
assert.equal(policy.topMargin('expanded', 82, 768, 768, 12), 0);
assert.equal(policy.topMargin('fullscreen', 82, 1440, 1440, 12), 0);

// The same mapped window must fit inside its output for all modes.
// The visible frame never extends below the 8px minimum bottom clearance.
// Large caps at Social's default 1355px minus 14px; short screens shrink.
for (const screen of [[2560, 1440], [1360, 768], [1024, 600], [320, 480]]) {
  for (const mode of ['compact', 'expanded', 'fullscreen']) {
    const [w, h] = frame(mode, ...screen);
    assert.ok(w + 24 <= screen[0], mode + ' window width overflow');
    assert.ok(9 + h + 8 <= screen[1], mode + ' window height overflow');
    assert.ok(screen[1] - (9 + h) >= 8, mode + ' missing bottom gap');
    if (mode === 'fullscreen')
      assert.equal(h, Math.min(1341, screen[1] - 17),
        'large height cap or minimum bottom clearance');
  }
}
assert.equal(1440 - (9 + frame('fullscreen', 2560, 1440)[1]), 90);
assert.equal(768 - (9 + frame('fullscreen', 1360, 768)[1]), 8);
assert.equal(policy.topMargin('expanded', 9, 768, 768, 9), 0);
assert.equal(policy.topMargin('compact', 9, 768, 768, 9), 0);

console.log('FinanceW M0 chassis policy: PASS');
