"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policySource=read("widgets/weather/StationCosmosHelioScaleMotionPolicy.js");
const qml=read("widgets/weather/StationCosmosHeliocentricPane.qml");
const atlasSource=read("widgets/weather/StationCosmosSolarOverviewPolicy.js");
const helioSource=read("widgets/weather/StationCosmosHeliocentricPolicy.js");
const network=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const context=vm.createContext({});
vm.runInContext(policySource.replace(/^\.pragma library\s*/m,""),context);
const M=context;
const sha="abcdef0123".repeat(6)+"abcd";
const times=Array.from({length:31},(_,i)=>Date.parse("2026-11-06T00:00:00Z")+i*12*3600000);

function fixture(index=15) {
    const body="earth";
    const atlas={
        format:M.ATLAS_FORMAT,origin:"heliocentric",origin_body:"sun",
        position_model:"geometric",frame:M.FRAME,epoch:"exact-m4-grid",
        units:"AU",source:"same-JPL-kernel-as-M4",
        sample_count:times.length,times_unix_ms:times.slice(),
        series:[{body,vectors_au:times.map((_,i)=>
            [1+i*0.01,0.12+i*0.02,0.005])}]
    };
    const payload={
        solar_overview:atlas,
        provenance:{ephemeris_id:"de440s.bsp",ephemeris_sha256:sha},
        query:{solar_overview_bodies:[body]}
    };
    const scene={
        ready:true,atlas:true,origin:"sun",
        frame:M.FRAME,positionModel:"geometric",
        source:"de440s.bsp",hash:sha.slice(0,10),timeMs:times[index],
        maxAu:40,points:[{body,x_au:1+index*0.01,
            y_au:0.12+index*0.02,z_au:0.005}]
    };
    return {payload,scene,index,body};
}

test("V5b AU rings are calibrated to real radial domain, not screen pixels",()=>{
    const four=JSON.parse(JSON.stringify(M.rings(4)));
    assert.deepEqual(four.map(x=>x.au),[1,2,3,4]);
    assert.deepEqual(four.map(x=>x.fraction),[0.25,0.5,0.75,1]);
    assert.deepEqual(M.rings(40).map(x=>x.au),[10,20,30,40]);
    assert.deepEqual(M.rings(0.05).map(x=>x.label),[
        "0.013 AU","0.025 AU","0.038 AU","0.050 AU"
    ]);
    assert.equal(M.rings(0).length,0);
    assert.equal(M.rings(Infinity).length,0);
    assert.equal(M.rings(-1).length,0);
    // Same AU grid at a different camera magnification: only its label
    // placement moves, not which AU number each ring represents.
    const ticks1=M.ringCallouts(40,{cx:156,cy:120,r:96},
        {left:12,top:10,right:388,bottom:220},false);
    const ticks2=M.ringCallouts(40,{cx:156,cy:120,r:200},
        {left:12,top:10,right:388,bottom:220},false);
    assert.ok(ticks1.length>=1);
    assert.ok(ticks2.length>=1);
    assert.ok(ticks1.every(x=>M.rings(40).some(y=>y.au===x.au)));
    assert.ok(ticks2.every(x=>M.rings(40).some(y=>y.au===x.au)));
    assert.equal(M.ringCallouts(40,{cx:9999,cy:120,r:96},
        {left:12,top:10,right:388,bottom:220},false).length,0);
});

test("V5b selected body has bounded past, current and future true UTC samples",()=>{
    const {payload,scene,index,body}=fixture();
    const before=JSON.stringify(payload);
    const trace=M.sampleWindow(payload,scene,body,index,12);
    assert.equal(trace.ready,true,trace.reason);
    assert.equal(trace.body,body);
    assert.equal(trace.frame,"true-ecliptic-of-date");
    assert.equal(trace.start,3);
    assert.equal(trace.end,27);
    assert.equal(trace.samples.length,25);
    assert.equal(trace.samples[0].kind,"past");
    assert.equal(trace.samples[12].kind,"now");
    assert.equal(trace.samples.at(-1).kind,"future");
    assert.equal(trace.samples[12].unix_ms,scene.timeMs);
    assert.deepEqual(Array.from(trace.samples[12]&&[
        trace.samples[12].x_au,trace.samples[12].y_au,
        trace.samples[12].z_au]),[1.15,0.42,0.005]);
    assert.equal(JSON.stringify(payload),before,"source immutable");
    assert.ok(!("orbit" in trace),"no fabricated orbital curve");
    assert.ok(!("interpolated" in trace));
});

test("V5b handles timeline endpoints without extra or synthetic samples",()=>{
    for(const index of [0,1,29,30]) {
        const {payload,scene,body}=fixture(index);
        const trace=M.sampleWindow(payload,scene,body,index,12);
        assert.equal(trace.ready,true);
        assert.equal(trace.samples.filter(p=>p.kind==="now").length,1);
        assert.equal(trace.samples.length,
            Math.min(30,index+12)-Math.max(0,index-12)+1);
        assert.ok(trace.samples.every(x=>times.includes(x.unix_ms)));
    }
});

test("V5b refuses stale source, wrong frames, missing body and corrupt XYZ",()=>{
    function invalid(edit) {
        const {payload,scene,index,body}=fixture();
        edit(payload,scene);
        return M.sampleWindow(payload,scene,body,index,12).ready;
    }
    assert.equal(invalid((p,s)=>{s.ready=false}),false);
    assert.equal(invalid((p,s)=>{s.positionModel="apparent"}),false);
    assert.equal(invalid((p,s)=>{s.frame="j2000"}),false);
    assert.equal(invalid((p,s)=>{s.source="other.bsp"}),false);
    assert.equal(invalid((p,s)=>{s.timeMs+=3600000}),false);
    assert.equal(invalid(p=>{p.provenance.ephemeris_sha256="0".repeat(64)}),false);
    assert.equal(invalid(p=>{p.solar_overview.origin="earth"}),false);
    assert.equal(invalid(p=>{p.solar_overview.position_model="apparent"}),false);
    assert.equal(invalid(p=>{p.solar_overview.frame="j2000"}),false);
    assert.equal(invalid(p=>{p.query.solar_overview_bodies=["mars"]}),false);
    assert.equal(invalid(p=>{p.solar_overview.series[0].body="mars"}),false);
    assert.equal(invalid(p=>{p.solar_overview.times_unix_ms[3]+=3600000}),false);
    assert.equal(invalid(p=>{p.solar_overview.times_unix_ms[3]=null}),false);
    assert.equal(invalid(p=>{p.solar_overview.series[0].vectors_au[7]=[0,0,0]}),false);
    assert.equal(invalid(p=>{p.solar_overview.series[0].vectors_au[7]=[1,NaN,3]}),false);
    assert.equal(invalid(p=>{p.solar_overview.series[0].vectors_au[7]=[1,2]}),false);
    const valid=fixture();
    assert.equal(M.sampleWindow(valid.payload,valid.scene,"sun",15,12).ready,false);
    assert.equal(M.sampleWindow(valid.payload,valid.scene,"earth",15,25).ready,false);
    assert.equal(M.sampleWindow(valid.payload,valid.scene,"earth",-1,12).ready,false);
});

test("V5b QML uses only discrete exact JPL samples and existing camera transform",()=>{
    assert.match(qml,/import "StationCosmosHelioScaleMotionPolicy\.js" as Motion/);
    assert.match(qml,/Motion\.rings\(spatial\.radialDomainAu\)/);
    assert.match(qml,/Motion\.ringCallouts\(spatial\.radialDomainAu,g,/);
    assert.match(qml,/Motion\.sampleWindow\(spatial\.visualData,spatial\.scene,/);
    assert.match(qml,/spatial\.selectedBody,spatial\.focusIndex,12\)/);
    assert.match(qml,/Helio\.position\(spatial\.scene,sample,w,h,/);
    assert.match(qml,/spatial\.cameraPanX,spatial\.cameraPanY\)/);
    assert.match(qml,/sample\.kind==="now"\)continue/);
    assert.match(qml,/JPL UTC SAMPLES \/\/ NO INTERPOLATED ORBIT/);
    const discrete=qml.slice(qml.indexOf("// V5b // Display ONLY"),
        qml.indexOf("// V5a: two-pass painting"));
    assert.ok(discrete.includes("ctx.arc(p.x,p.y,2.2"));
    assert.ok(!discrete.includes("ctx.lineTo("),
        "never join discrete ephemeris samples into a claimed orbit");
    assert.match(qml,/Helio\.visibleHit\(/);
    assert.match(qml,/Helio\.zoomAt\(/);
    assert.match(qml,/Helio\.focusPan\(/);
    assert.match(qml,/Labels\.layout\(/);
    assert.match(qml,/Labels\.plaque\(/);
    assert.match(network,/id: compactNetworkToolbar/);
    assert.match(helioSource,/function cameraOrigin\(/);
    assert.match(atlasSource,/source:"same-JPL-kernel-as-M4"/);
    for(const src of [policySource,qml]){
        for(const invalid of ["Process {","Timer {","XMLHttpRequest",
            "new WebSocket","Qt.callLater","curl ","fetch("])
            assert.ok(!src.includes(invalid),invalid);
    }
});
