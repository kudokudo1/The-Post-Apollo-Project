const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const P=vm.createContext({});
vm.runInContext(fs.readFileSync(path.resolve(__dirname,"../../services/git/GitMapViewportPolicy.js"),"utf8"),P);
const m={schema:"post-apollo-git-map-index-v1",snapshot:"a".repeat(32),repoId:"b".repeat(64),
    total:100000,pageSize:128,shallow:false,maxLane:0,scope:"captured-local-ref-tips-and-head"};
const sha=i=>(i+1).toString(16).padStart(40,"0");
const plain=x=>JSON.parse(JSON.stringify(x));
function page(r,manifest=m) {
    const count=Math.min(128,manifest.total-r.start);
    return {schema:manifest.schema,snapshot:manifest.snapshot,repoId:manifest.repoId,
        total:manifest.total,start:r.start,end:r.start+count===manifest.total,frontier:[],
        rows:Array.from({length:count},(_,i)=>{
            const n=r.start+i;
            return {ordinal:n,sha:sha(n),lane:0,timestamp:n,author:"fixture",subject:"row",
                parents:n+1<manifest.total?[{position:0,sha:sha(n+1),ordinal:n+1,lane:0}]:[]};
        })};
}
let s=P.activate(null,m,24,480);
assert.equal(P.extent(s),2400000);
assert.equal(P.scroll(s,0),s,"unchanged geometry must not cause a new state");
let plan=P.requests(s);s=plan.state;
assert.equal(plan.requests[0].start,0);
const top=plan.requests[0];
assert.equal(P.requests(s).state,s,"no new requests must not republish state");
s=P.scroll(s,Infinity);
assert.equal(s.y,0);
s=P.scroll(s,999999999);
const bottomY=2399520;
assert.equal(s.y,bottomY);
assert.equal(P.bottomState(s),"LOADING END RANGE");
assert.equal(P.accept(s,top,page(top)),s,"obsolete top response must not move/load viewport");
plan=P.requests(s);s=plan.state;
assert.equal(plan.requests[0].start,Math.floor(99980/128)*128);
const bottom=plan.requests[0];
s=P.fail(s,bottom);
assert.equal(P.bottomState(s),"END RANGE UNAVAILABLE");
assert.equal(s.y,bottomY);
s=P.retry(s,bottom.start);
plan=P.requests(s);s=plan.state;
const retry=plan.requests[0];
assert.notEqual(retry.sequence,bottom.sequence);
assert.equal(P.accept(s,bottom,page(bottom)),s,"late failed request ignored");
let corrupt=page(retry);corrupt.rows[0].ordinal+=1;
s=P.accept(s,retry,corrupt);
assert.equal(P.bottomState(s),"END RANGE UNAVAILABLE");
s=P.retry(s,retry.start);
plan=P.requests(s);s=plan.state;
s=P.accept(s,plan.requests[0],page(plan.requests[0]));
assert.equal(P.bottomState(s),"END OF INDEXED LOCAL HISTORY");
assert.equal(s.y,bottomY);
assert.equal(P.rowAt(s,99999).sha,sha(99999));
assert.equal(P.rowAt(s,100000),null);
assert.equal(P.extent(s),2400000);
assert.equal(P.scroll(s,bottomY+999).y,bottomY);
assert.equal(P.scroll(s,-999).y,0);
const current=P.anchorOf(s);
const m2={...m,snapshot:"c".repeat(32),total:100001};
assert.equal(P.activate(s,m2,24,480,null),null);
assert.equal(P.activate(s,m2,24,480,{...m2,sha:sha(99981),ordinal:99981,offset:current.offset}),null);
const next=P.activate(s,m2,24,480,{...m2,sha:current.sha,ordinal:current.ordinal+1,offset:current.offset});
assert.equal(next.y,bottomY+24);
assert.equal(P.accept(next,retry,page(retry)),next);
const other={...m,repoId:"d".repeat(64)};
assert.equal(P.activate(s,other,24,480,{...other,sha:current.sha,ordinal:current.ordinal,offset:current.offset}),null);
const switched=P.activate(s,other,24,480,{top:true});
assert.equal(switched.y,0);
assert.equal(P.accept(switched,top,page(top)),switched);
let stress=P.activate(null,m,24,480);
for(let i=0;i<500;i++) {
    const y=i%2 ? (100000-i*19)*24 : i*137*24;
    stress=P.scroll(stress,y);
    const expected=stress.y;
    const work=P.requests(stress);stress=work.state;
    for(const req of Array.from(work.requests).reverse()) stress=P.accept(stress,req,page(req));
    assert.equal(stress.y,expected);
    assert.ok(Object.keys(stress.cache).length<=5);
    const range=P.visibleRange(stress);
    for(let n=range.first;n<range.stop;n++) assert.equal(P.rowAt(stress,n).sha,sha(n));
}
const short={...m,total:3,shallow:true};
let shallow=P.activate(null,short,24,480);
assert.equal(P.bottomState(shallow),"LOADING END RANGE");
plan=P.requests(shallow);shallow=P.accept(plan.state,plan.requests[0],page(plan.requests[0],short));
assert.equal(P.bottomState(shallow),"SHALLOW LOCAL BOUNDARY");
const empty=P.activate(null,{...m,total:0},24,480);
assert.equal(P.bottomState(empty),"EMPTY LOCAL HISTORY");
assert.equal(P.requests(empty).requests.length,0);
console.log("Git map viewport: 100k extent, fast jumps, errors, stale responses and anchor continuity PASS");
