// Run from repository root: node --test tests/components/energy-progress-motion.test.cjs
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const motion = vm.runInNewContext(fs.readFileSync(path.join(root,
    "components/EnergyProgressMotion.js"), "utf8") + "\n({frame});");
const frame = motion.frame;

test("indeterminate struggle recoils and never reaches completion on time alone", () => {
    let prev = 0, recoil = false;
    for (let t=0;t<120;t+=.013) {
        const f=frame("running","indeterminate",0,t,0,false);
        assert.ok(f.fraction>=0 && f.fraction<=.96);
        assert.ok(Math.abs(f.dx)<=2 && Math.abs(f.dy)<=.46);
        if (t<3.7 && f.fraction<prev) recoil=true;
        prev=f.fraction;
    }
    assert.ok(recoil);
    assert.ok(frame("running","indeterminate",0,18,0,false).brightness >
        frame("running","indeterminate",0,.5,0,false).brightness);
});
test("measured and timed fill are exact; nonfinite input is bounded", () => {
    for(let i=0;i<=100;i++) for(const mode of ["measured","timed"]) {
        const p=i/100;
        assert.equal(frame("running",mode,p,4,0,false).fraction,p);
    }
    assert.equal(frame("running","measured",NaN,0,0,false).fraction,0);
    assert.equal(frame("running","measured",2,0,0,false).fraction,1);
});
test("success is externally signaled; ready and failure are distinct", () => {
    assert.equal(frame("success","indeterminate",0,0,.42,false).fraction,.42);
    assert.equal(frame("success","indeterminate",0,.42,.42,false).fraction,1);
    assert.equal(frame("success","indeterminate",0,1,.42,false).headVisible,false);
    assert.equal(frame("failure","indeterminate",0,99,.42,false).fraction,.42);
    assert.equal(frame("ready","timed",0,99,0,false).fraction,1);
    assert.equal(frame("idle","indeterminate",0,99,0,false).fraction,0);
    assert.equal(frame("queued","indeterminate",0,99,0,false).fraction,0);
});
test("reduced motion uses a static activity cue and instant verified completion", () => {
    for(const t of [0,2,30,600]) {
        const f=frame("running","indeterminate",0,t,0,true);
        assert.equal(f.fraction,.35); assert.equal(f.dx,0); assert.equal(f.dy,0);
    }
    assert.equal(frame("success","indeterminate",0,0,.42,true).fraction,1);
});
test("native renderer owns no operation or input; gallery has all four variants", () => {
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    assert.match(source,/const f=root.visualFrame, p=f.fraction, mid=y\+h\/2/);
    assert.match(source,/c.translate\(edge,mid\)/);
    assert.doesNotMatch(source,/\b(?:MouseArea|TapHandler|Process|XMLHttpRequest|onLeftClicked)\b/);
    for(const key of ["omnitrix","tron","ki-blast","flamethrower"]) assert.ok(preview.includes('"'+key+'"'));
    assert.doesNotMatch(preview,/\b(?:Process|XMLHttpRequest)\b|import qs\.services/);
});
