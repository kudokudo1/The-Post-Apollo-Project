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
    assert.match(source,/c.translate\(centerX===undefined\?edge:centerX,mid\)/);
    assert.doesNotMatch(source,/\b(?:MouseArea|TapHandler|Process|XMLHttpRequest|onLeftClicked)\b/);
    for(const key of ["omnitrix","tron","ki-blast","flamethrower"]) assert.ok(preview.includes('"'+key+'"'));
    assert.doesNotMatch(preview,/\b(?:Process|XMLHttpRequest)\b|import qs\.services/);
});

const profiles = vm.runInNewContext(fs.readFileSync(path.join(root,
    "components/EnergyVariantProfile.js"), "utf8") + "\n({profile,host,barMotion,fireDrive});");

test("four personalities preserve bounded motion, distinct intensity and flash isolation", () => {
    const names=["ki-blast","flamethrower","omnitrix","tron"];
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

test("TRON advances monotonically without inventing completion", () => {
    let previous=0;
    for(let t=0;t<120;t+=.013) {
        const f=frame("running","indeterminate",0,t,0,false,"tron");
        assert.ok(f.fraction>=previous && f.fraction<=.96);
        assert.equal(f.clash,false);
        previous=f.fraction;
    }
    assert.equal(frame("running","measured",.43,12,0,false,"tron").fraction,.43);
});
test("Ki Blast clash remains complementary and defeat retreats to zero", () => {
    for(let t=0;t<60;t+=.013) {
        const f=frame("running","indeterminate",0,t,0,false,"ki-blast");
        assert.ok(f.clash && f.fraction>=.43 && f.fraction<1);
        assert.ok(Math.abs(f.enemyFraction+f.fraction-1)<1e-12);
    }
    let prev=.73;
    for(let t=0;t<.84;t+=.005) {
        const f=frame("failure","indeterminate",0,t,.73,false,"ki-blast");
        assert.ok(f.fraction<=prev+1e-12);
        assert.ok(Math.abs(f.enemyFraction+f.fraction-1)<1e-12);
        prev=f.fraction;
    }
    assert.equal(frame("failure","indeterminate",0,1,.73,false,"ki-blast").fraction,0);
    assert.equal(frame("failure","indeterminate",0,0,.73,true,"ki-blast").fraction,0);
    assert.equal(frame("success","indeterminate",0,.42,.73,false,"ki-blast").enemyFraction,0);
    assert.equal(frame("running","measured",.42,4,0,false,"ki-blast").fraction,.42);
    assert.equal(frame("failure","measured",0,1,.73,false,"flamethrower").fraction,.73);
});
test("Omnitrix has an expanding success pulse and non-fire heads are enlarged", () => {
    let prev=0;
    for(let t=.42;t<.82;t+=.005){
        const f=profiles.host("omnitrix",t,1,1,"success",false);
        assert.ok(f.flashSpread>=prev && f.flashSpread<=1);
        prev=f.flashSpread;
    }
    for(const name of ["omnitrix","tron","ki-blast"]) assert.ok(profiles.profile(name).headConsume>1);
    assert.equal(profiles.profile("flamethrower").headConsume,1);
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    assert.match(preview,/source.mapToItem\(flashOverlay/);
    assert.match(preview,/field.flashColor/);
    assert.match(preview,/createRadialGradient\(origin.x,origin.y/);
});

test("Ki Blast enemy heat grows through defeat and persists after impact", () => {
    const running=frame("running","measured",.68,4,0,false,"ki-blast");
    assert.ok(running.enemyHeat>0 && running.enemyHeat<.25);
    assert.equal(running.enemyOpacity,1);
    let previous=running.enemyHeat;
    for(let i=0;i<=144;i++){
        const f=frame("failure","measured",0,i/200,.68,false,"ki-blast");
        assert.ok(f.enemyHeat>=previous-1e-12 && f.enemyHeat<=1);
        assert.equal(f.enemyOpacity,1);
        previous=f.enemyHeat;
    }
    const hit=frame("failure","measured",0,.72,.68,false,"ki-blast");
    assert.equal(hit.fraction,0);
    assert.equal(hit.enemyFraction,1);
    assert.equal(hit.enemyHeat,1);
    assert.equal(hit.enemyOpacity,1);
    const fade=frame("failure","measured",0,.96,.68,false,"ki-blast");
    assert.equal(fade.enemyOpacity,1);
    const end=frame("failure","measured",0,1.08,.68,false,"ki-blast");
    assert.equal(end.enemyOpacity,1);
    assert.equal(end.clash,true);
    assert.equal(end.enemyFraction,1);
    const reduced=frame("failure","measured",0,0,.68,true,"ki-blast");
    assert.equal(reduced.enemyOpacity,1);
    assert.equal(reduced.enemyFraction,1);
    assert.equal(frame("idle","measured",0,0,.68,false,"ki-blast").enemyOpacity,0);
    for(const name of ["tron","omnitrix","flamethrower"])
        assert.equal(frame("failure","measured",0,.5,.68,false,name).enemyHeat,0);
});

const currents=vm.runInNewContext(fs.readFileSync(path.join(root,
    "components/EnergyBeamFlow.js"),"utf8")+"\n({flow,head,clashSizes,contact,airFlow,speedSample});");
test("full-lane currents advance in opposite directions, with faster TRON", () => {
    const w=900,h=40;
    const left=currents.flow("ki-blast","standard","player",w,h,0,false);
    const right=currents.flow("ki-blast","standard","enemy",w,h,0,false);
    const next=currents.flow("ki-blast","standard","player",w,h,.01,false);
    const nextRight=currents.flow("ki-blast","standard","enemy",w,h,.01,false);
    assert.ok(left.length>=20 && left.length<=32);
    assert.ok(next[0].x>left[0].x && nextRight[0].x<right[0].x);
    const tron=currents.flow("tron","standard","player",w,h,0,false);
    const tronNext=currents.flow("tron","standard","player",w,h,.01,false);
    assert.ok(tron.length>left.length && tron.length<=53);
    assert.ok(tronNext[0].x-tron[0].x>2*(next[0].x-left[0].x));
    assert.ok(tron.filter(r=>!r.wake).some(r=>r.x<w*.15));
    assert.ok(tron.filter(r=>!r.wake).some(r=>r.x>w*.8));
    assert.ok(tron.some(r=>r.wake && r.length>h));
    assert.ok(tron.filter(r=>r.wake).every(r=>r.x>=w-h*4.2-1e-9));
    assert.ok(tron.filter(r=>!r.wake).every(r=>r.alpha<=.24));
    assert.equal(JSON.stringify(currents.flow("tron","standard","player",w,h,0,true)),
        JSON.stringify(currents.flow("tron","standard","player",w,h,900,true)));
});
test("fire wake distribution distinguishes live fire from cooled material", () => {
    const w=800,h=40;
    const a=currents.flow("flamethrower","ash-trail","player",w,h,2,false);
    const b=currents.flow("flamethrower","burn-away","player",w,h,2,false);
    const standard=currents.flow("flamethrower","standard","player",w,h,2,false);
    assert.ok(a.length===b.length && a.length>0);
    assert.ok(a.every(r=>r.wake && r.x>=w-h*6-1e-9));
    assert.ok(b.every(r=>r.wake && r.x>=w-h*4.4-1e-9));
    assert.ok(Math.min(...a.map(r=>r.x))<Math.min(...b.map(r=>r.x)));
    assert.ok(standard.filter(r=>r.wake).length>standard.filter(r=>!r.wake).length);
    assert.ok(standard.some(r=>!r.wake && r.x<w-h*6.8));
    for(const variant of ["tron","ki-blast","flamethrower"]){
        assert.equal(currents.flow(variant,"standard","player",0,h,2,false).length,0);
        for(const r of currents.flow(variant,"standard","player",w,h,2,false)){
            assert.ok(Number.isFinite(r.x) && r.length>0 && r.y>=0 && r.y<=h);
        }
    }
});
test("TRON and Omnitrix core covers chamber height; clash lobes have separate contact planes",()=>{
    for(const variant of ["tron","omnitrix"]){
        for(const h of [12,24,42,80]){
            const g=currents.head(variant,h,1,800);
            assert.ok(g.ry>=h*.60 && g.ry<h*.80);
            assert.ok(g.solid<.55 && g.rx<h);
            assert.ok(g.rx>=h*.70);
        }
    }
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    assert.match(source,/compressed\(-1,ink/);
    assert.match(source,/compressed\(1,enemyInk/);
    assert.match(source,/shape.offset\*\.72/);
    assert.match(source,/if\(playerWins\)/);
    assert.doesNotMatch(source,/c.rect\(0,0,edge,height\)/);
    assert.match(source,/f.enemyHeat/);
    assert.match(source,/Flow.flow/);
});

test("dominant clash lobe grows while losing lobe shrinks",()=>{
    const a=currents.clashSizes(.2,.8), b=currents.clashSizes(.8,.15);
    assert.ok(a.enemy>a.player && b.player>b.enemy);
    assert.ok(a.enemy>b.enemy && a.player<b.player);
    assert.ok(currents.clashSizes(0,1).enemy>=1.8);
});
const pixel=vm.runInNewContext(fs.readFileSync(path.join(root,
    "components/EnergyPixelFire.js"),"utf8")+"\n({fire,velocity,lightMotion,falloff});");
test("pixel fire waves, emits detached embers and stays static in reduced motion",()=>{
    const a=pixel.fire(42,0,false), b=pixel.fire(42,.75,false);
    assert.ok(a.cells.length>40 && a.cells.length<200);
    assert.ok(a.embers.length===12 && a.embers.some(e=>e.x<-8));
    assert.ok(JSON.stringify(a.cells)!==JSON.stringify(b.cells));
    assert.ok(JSON.stringify(a.embers)!==JSON.stringify(b.embers));
    assert.equal(JSON.stringify(pixel.fire(42,0,true)),JSON.stringify(pixel.fire(42,99,true)));
    for(const cell of a.cells) assert.ok(Number.isInteger(cell.x)&&Number.isInteger(cell.y)&&cell.heat>=0&&cell.heat<=3);
    for(const ember of a.embers) assert.ok(ember.alpha>=0&&ember.alpha<=1);
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    assert.match(source,/PixelFire.fire/);
    assert.match(source,/c.globalAlpha=\.35/);
});

test("TRON local vibration is distinct from host and fire ignition has three strengths",()=>{
    const modes=["standard","ash-trail","burn-away"];
    const initial=modes.map(mode=>profiles.host("flamethrower",0,.12,1,"running",false,mode).power);
    assert.ok(initial[0]>=.85 && initial[0]>initial[1] && initial[1]>initial[2] && initial[2]>=.35);
    for(const mode of modes) {
        let prev=0;
        for(let i=0;i<=300;i++){
            const p=profiles.fireDrive(mode,i/100,.12);
            assert.ok(p>=prev && p<=1);prev=p;
        }
        assert.equal(prev,1);
        assert.equal(profiles.host("flamethrower",1,.12,1,"running",true,mode).power,0);
    }
    let local=0,host=0;
    for(let i=0;i<1000;i++){
        const t=i/100;
        local=Math.max(local,Math.abs(profiles.barMotion("tron",t,1,false).dx));
        host=Math.max(host,Math.abs(profiles.host("tron",t,1,1,"running",false).dx));
    }
    assert.ok(local>.9 && host<.19 && local>host*5);
    assert.equal(profiles.barMotion("tron",4,1,true).dx,0);
});
test("clash contact flattens only a shared cap and the winning sphere regains its curve",()=>{
    for(let i=0;i<=100;i++){
        const p=i/100, q=currents.contact(p,.15,42,800);
        for(const l of [q.left,q.right]){
            const chord=l.ry*Math.sqrt(Math.max(0,1-(l.offset/l.rx)**2));
            assert.ok(Math.abs(chord-q.chord)<1e-8);
            assert.ok(l.offset>0&&l.offset<l.rx);
        }
    }
    const q=currents.contact(.9,.15,42,800);
    assert.ok(q.left.offset/q.left.rx>.95);
    assert.ok(q.left.offset/q.left.rx>q.right.offset/q.right.rx);
    const r=currents.contact(.1,.8,42,800);
    assert.ok(r.right.offset/r.right.rx>.95);
});

test("wind-swept pixel flames and embers point backward",()=>{
    for(const mode of ["standard","ash-trail","burn-away"]){
        for(let t=0;t<3;t+=.125){
            const f=pixel.fire(42,t,false,mode);
            assert.ok(Math.min(...f.cells.map(c=>c.x))< -4);
            assert.ok(f.embers.every(e=>e.x<0));
            assert.ok(f.cells.every(c=>Number.isInteger(c.x)&&Number.isInteger(c.y)));
        }
    }
    const standard=pixel.fire(42,0,true,"standard");
    const erosion=pixel.fire(42,0,true,"burn-away");
    assert.ok(Math.min(...standard.cells.map(c=>c.x))<Math.min(...erosion.cells.map(c=>c.x)));
});
test("radiance is independent of core size and collision is overlapping",()=>{
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    const field=fs.readFileSync(path.join(root,"components/EnergyPressureField.qml"),"utf8");
    assert.match(source,/function radiate/);
    assert.match(source,/shape.offset\*\.72/);
    assert.match(source,/orb\(Math.max\(h\*\.14,tall\*\.55\)/);
    assert.doesNotMatch(source,/c.fillRect\(edge-1.25/);
    assert.match(source,/rx\*\(tron\?1.82:1.65\)/);
    assert.match(preview,/id: battlefieldLight/);
    assert.match(field,/clashLight: clashLight/);
});

test("rocket fire has a round head and a tapered tail; exterior speed stays local",()=>{
    for(const mode of ["standard","ash-trail","burn-away"]){
        const f=pixel.fire(42,0,true,mode);
        const countAt=x=>f.cells.filter(c=>c.x===x).length;
        const tip=Math.min(...f.cells.map(c=>c.x));
        assert.ok(countAt(0)>countAt(5));
        assert.ok(countAt(0)>countAt(tip));
        assert.ok(countAt(0)>=10);
    }
    for(const w of [120,800,2400]){
        const lines=currents.airFlow(w,40,.3,false);
        assert.equal(lines.length,14);
        for(const l of lines){
            assert.ok(l.x>=-Math.min(w,40*5.8)-1e-9);
            assert.ok(l.x+l.length<=1e-9);
            assert.ok(Math.abs(l.y)>20 && l.alpha>=0 && l.alpha<=1);
        }
    }
    assert.equal(currents.airFlow(800,40,1,true).length,0);
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    assert.match(source,/const contactWidth=/);
    assert.match(source,/const plume=/);
    assert.match(source,/Flow.airFlow/);
    assert.match(source,/mix\(hotWhite,red,heat\*\.82\)/);
    assert.match(preview,/id: battlefieldLight\s+anchors.fill: parent\s+z: 10/);
});

test("TRON exterior streaks vary within a bounded head-relative region",()=>{
    const a=currents.airFlow(2400,40,.28,false);
    const b=currents.airFlow(2400,40,1.2,false);
    assert.ok(new Set(a.map(l=>l.length)).size>10);
    assert.ok(new Set(a.map(l=>l.y)).size>10);
    assert.ok(JSON.stringify(a)!==JSON.stringify(b));
    assert.equal(JSON.stringify(a),JSON.stringify(currents.airFlow(2400,40,.28,false)));
    for(let t=0;t<5;t+=.013){
        for(const l of currents.airFlow(2400,40,t,false)){
            assert.ok(l.x>=-232-1e-9 && l.x+l.length<=1e-9);
            assert.ok(Math.abs(l.y)>20 && Math.abs(l.y)<40);
            assert.ok(l.alpha>=0&&l.alpha<=1);
        }
    }
    assert.ok(currents.head("omnitrix",40,1,800).rx>36);
});
test("local light is shared and bounded; fire light follows the pixel silhouette",()=>{
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    const field=fs.readFileSync(path.join(root,"components/EnergyPressureField.qml"),"utf8");
    assert.match(field,/property bool localLightingEnabled: true/);
    assert.match(field,/localLights.sort\(.*\).slice\(0,8\)/);
    assert.match(preview,/id: localRadiance\s+anchors.fill: parent\s+z: 11/);
    assert.match(preview,/source.mapToItem\(localRadiance/);
    assert.match(source,/Math.max\(\.\.\.flamePixels.cells.map/);
    assert.match(source,/edge\+root.flameTipOffset/);
    assert.match(source,/const halo=c.createRadialGradient/);
    assert.match(source,/heated.addColorStop\(0,tint\(Colors.yellow,.94\)\)/);
});

test("TRON streak density follows sampled forward advance, not time or completion",()=>{
    let speed=0,p=0;
    assert.equal(currents.airFlow(800,40,0,false,speed).length,0);
    for(let i=0;i<25;i++) {
        const next=p+.002;
        speed=currents.speedSample(p,next,.04,speed);p=next;
    }
    const slow=speed;
    const slowAir=currents.airFlow(800,40,1,false,slow).length;
    for(let i=0;i<25;i++) {
        const next=p+.012;
        speed=currents.speedSample(p,next,.04,speed);p=next;
    }
    const fast=speed;
    assert.ok(slow>0 && fast>slow && fast<=1);
    assert.ok(currents.airFlow(800,40,2,false,fast).length>slowAir);
    assert.ok(currents.flow("tron","standard","player",800,40,2,false,fast).length>
        currents.flow("tron","standard","player",800,40,2,false,slow).length);
    for(let i=0;i<40;i++) speed=currents.speedSample(p,p,.04,speed);
    assert.ok(speed<.001);
    assert.equal(currents.airFlow(800,40,3,false,speed).length,0);
    assert.equal(currents.speedSample(.8,.2,.1,0),0);
});
test("fire light uses the forward pixel and reflection overlays the material",()=>{
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    const field=fs.readFileSync(path.join(root,"components/EnergyPressureField.qml"),"utf8");
    assert.match(source,/readonly property real flameTipOffset/);
    assert.match(source,/const tip=edge\+root.flameTipOffset/);
    assert.match(source,/Flow.speedSample\(root.speedFraction,next/);
    assert.ok(source.indexOf("Material.drawAsh")<source.indexOf("fireHalo(tip-h*(.36"));
    assert.match(preview,/light.fire\?source.flameTipOffset/);
    assert.match(field,/ki-blast"\?\.38:fire\?\.36/);
});

test("flame brightness is integrated into the pixels rather than a foreground orb",()=>{
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    assert.match(source,/mix\(fireOrange\[cell.heat\],fireTip\[cell.heat\],k\*heat\)/);
    assert.doesNotMatch(source,/orb\(h\*\.65,h\*\.62/);
    assert.doesNotMatch(source,/orb\(h\*1.18,h\*1.10/);
});
test("battlefield light follows beam geometry and the winner bleeds into contact",()=>{
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    assert.match(source,/const penetration=Math.min/);
    assert.match(source,/tint\(winner,.60\*dominance\)/);
    assert.match(preview,/bloom\(start\+left\*\.53,origin.y/);
    assert.match(preview,/bloom\(split\+right\*\.47,origin.y/);
    assert.match(preview,/bloom\(split,origin.y,h\*3.2/);
    assert.doesNotMatch(preview,/const lo=Math.max\(0,\(split-blend\)/);
});

test("flame turbulence and illumination remain attached and vary continuously",()=>{
    for(const mode of ["standard","ash-trail","burn-away"]){
        const shapes=new Set();
        for(let i=0;i<120;i++){
            const t=i/30;
            const f=pixel.fire(34,t,false,mode,.5);
            shapes.add(JSON.stringify(f.cells));
            assert.ok(f.cells.length>40 && f.cells.length<=330);
            assert.ok(f.embers.every(e=>e.x<0));
            const light=pixel.lightMotion(t,.5,false);
            assert.ok(Math.abs(light.sway)<=.096);
            assert.ok(light.drag>=0 && light.drag<=.56);
            assert.ok(light.pulse>=.81 && light.pulse<=1.19);
            assert.ok(light.breath>=.86 && light.breath<=1.14);
            const next=pixel.lightMotion(t+.001,.5,false);
            assert.ok(Math.abs(next.pulse-light.pulse)<.004);
        }
        assert.ok(shapes.size>70);
        assert.equal(JSON.stringify(pixel.fire(34,0,true,mode,0)),JSON.stringify(pixel.fire(34,120,true,mode,1)));
    }
    let slow=0,fast=0;
    for(let i=0;i<30;i++){
        slow=pixel.velocity(0,.001,.033,800,34,slow);
        fast=pixel.velocity(0,.025,.033,800,34,fast);
    }
    assert.ok(fast>slow && fast<=1);
    assert.ok(pixel.lightMotion(1,fast,false).drag>pixel.lightMotion(1,slow,false).drag);
    assert.ok(pixel.lightMotion(1,fast,false).stretch>pixel.lightMotion(1,slow,false).stretch);
    assert.ok(pixel.velocity(0,.002,.033,1600,34,0)>pixel.velocity(0,.002,.033,800,34,0));
    for(let i=0;i<30;i++)fast=pixel.velocity(.4,.4,.033,800,34,fast);
    assert.ok(fast<.001);
    assert.equal(pixel.velocity(.8,.4,.033,800,34,0),0);
    assert.equal(pixel.lightMotion(2,1,true).drag,0);
    assert.equal(pixel.lightMotion(2,1,true).pulse,1);
    assert.equal(pixel.falloff(0),1);
    assert.equal(pixel.falloff(1),0);
    for(let i=1;i<=100;i++) assert.ok(pixel.falloff(i/100)<=pixel.falloff((i-1)/100));
    const source=fs.readFileSync(path.join(root,"components/EnergyProgressFace.qml"),"utf8");
    const preview=fs.readFileSync(path.join(root,"tests/fixtures/EnergyProgressPreview.qml"),"utf8");
    assert.match(source,/PixelFire.velocity\(root.speedFraction,front/);
    assert.match(source,/flame.stretch/);
    assert.match(preview,/source.flameMotion/);
    assert.match(preview,/flame.drag/);
});
