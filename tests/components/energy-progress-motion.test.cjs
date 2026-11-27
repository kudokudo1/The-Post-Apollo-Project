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
    assert.match(source,/const f=root.visualFrame, p=root.displayedFraction, mid=y\+h\/2/);
    assert.match(source,/c.translate\(edge,mid\)/);
    assert.doesNotMatch(source,/\b(?:MouseArea|TapHandler|Process|XMLHttpRequest|onLeftClicked)\b/);
    for(const key of ["omnitrix","tron","ki-blast","flamethrower"]) assert.ok(preview.includes('"'+key+'"'));
    assert.doesNotMatch(preview,/\b(?:Process|XMLHttpRequest)\b|import qs\.services/);
});

const profiles = vm.runInNewContext(fs.readFileSync(path.join(root,
    "components/EnergyVariantProfile.js"), "utf8") + "\n({profile,host});");

test("four personalities preserve bounded motion, distinct intensity and flash isolation", () => {
    const names=["ki-blast","flamethrower","tron","omnitrix"];
    const max=names.map(name=>{
        let dx=0,dy=0;
        for(let t=0;t<30;t+=.007) {
            const f=profiles.host(name,t,1,2,"running",false);
            assert.ok(Math.abs(f.dx)<=3.000001 && Math.abs(f.dy)<=2.000001);
            assert.equal(f.flash,0);
            dx=Math.max(dx,Math.abs(f.dx));dy=Math.max(dy,Math.abs(f.dy));
        }
        return {dx,dy};
    });
    for(let i=1;i<max.length;i++){
        assert.ok(max[i-1].dx>max[i].dx);
        assert.ok(max[i-1].dy>max[i].dy);
    }
    assert.ok(profiles.profile("omnitrix").brightness>profiles.profile("ki-blast").brightness);
    assert.ok(profiles.host("omnitrix",.52,1,1,"success",false).flash>.7);
    for(const name of names) {
        assert.equal(profiles.host(name,.52,1,1,"failure",false).flash,0);
        assert.equal(profiles.host(name,.52,1,1,"success",true).flash,0);
        assert.equal(profiles.host(name,.84,1,1,"success",false).flash,0);
        assert.equal(profiles.host(name,.52,1,1,"success",true).dx,0);
        if(name!=="omnitrix") assert.equal(profiles.host(name,.52,1,1,"success",false).flash,0);
    }
    assert.equal(profiles.host("tron",4,1,1,"running",false).fragments,0);
    assert.equal(profiles.host("omnitrix",4,1,1,"running",false).fragments,0);
    assert.ok(profiles.host("flamethrower",4,1,1,"running",false).fragments>0);
});

const material = vm.runInNewContext(fs.readFileSync(path.join(root,
    "components/EnergyFireMaterial.js"), "utf8") + "\n({geometry,grain,drawAsh,drawRemaining});",
    {Qt:{rgba:(r,g,b,a)=>({r,g,b,a})}});
test("material experiments preserve standard and partition the chassis", () => {
    for(const mode of ["standard","ash-trail","burn-away","unknown"]){
        for(let i=0;i<=100;i++){
            const g=material.geometry(mode,i/100,200,34);
            assert.ok(Math.abs(g.burned+g.remaining-200)<1e-9);
            assert.equal(g.ash,mode==="ash-trail");
            assert.equal(g.erosion,mode==="burn-away");
        }
    }
    assert.equal(material.geometry("burn-away",1,200,34).remaining,0);
    assert.equal(material.geometry("ash-trail",1,200,34).burned,200);
    assert.equal(material.geometry("burn-away",NaN,200,34).remaining,200);
    assert.equal(material.grain(12,3),material.grain(12,3));
});
test("burn-away terminal state draws no remaining structure; ash remains deposited", () => {
    const calls=[];
    const gradient={addColorStop(){}};
    const context=new Proxy({}, {get:(o,k)=>k==="createLinearGradient"
        ? ()=>gradient : (...a)=>{calls.push([k,...a]);}});
    material.drawRemaining(context,0,0,200,34,200,false,"orange");
    assert.equal(calls.length,0);
    material.drawRemaining(context,0,0,200,34,100,false,"orange");
    assert.ok(calls.some(c=>c[0]==="fill"));
    assert.ok(calls.filter(c=>c[0]==="moveTo"||c[0]==="lineTo").every(c=>c[1]>=100));
    calls.length=0;
    material.drawAsh(context,0,0,200,34,200,false);
    assert.ok(calls.some(c=>c[0]==="fillRect"&&c[1]===0&&c[3]===200));
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    assert.match(source,/property string fireMode: "standard"/);
    assert.match(source,/root.materialPeak=Math.max\(root.materialPeak,next\)/);
    assert.ok(preview.includes('fireMode:"ash-trail"')&&preview.includes('fireMode:"burn-away"'));
});
