// Run the pure QML JavaScript geometry policy without Qt or a desktop.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const source = fs.readFileSync(path.join(__dirname, '../../widgets/ForestChassisPolicy.js'), 'utf8');
const scope = {};
vm.createContext(scope);
vm.runInContext(source, scope);
assert.strictEqual(scope.step(0, -1), 0);
assert.strictEqual(scope.step(0, 1), 1);
assert.strictEqual(scope.step(1, 1), 2);
assert.strictEqual(scope.step(2, 1), 3);
assert.strictEqual(scope.step(3, 1), 3);
const expected = [[480,340], [660,340], [660,540], [930,610]];
for (let i=0; i<4; i++) {
    const f = scope.frame(i, 1920, 1080, 12, 9, 8);
    assert.deepStrictEqual([f.width, f.height], expected[i]);
}
for (const [sw, sh] of [[1920,1080],[1366,768],[360,640],[200,250]]) {
    for (let i=0; i<4; i++) {
        const f = scope.frame(i,sw,sh,12,9,8);
        const windowWidth = f.width + 24;
        const windowHeight = f.height + 17;
        const top = scope.topMargin(sh,windowHeight);
        const left = scope.leftMargin(sw,windowWidth,sw/2);
        assert(f.width > 0 && f.height > 0);
        assert.strictEqual(top, 0, 'visible top edge must align with other menus');
        assert(left>=0);
        assert(top + windowHeight <= sh - 11, 'vertical overflow');
        assert(left + windowWidth <= sw, 'horizontal overflow');
    }
}
console.log('Forest V0 geometry: shared top edge, four stages and 16 viewport checks PASS');
