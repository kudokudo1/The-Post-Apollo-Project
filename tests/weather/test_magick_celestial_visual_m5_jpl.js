"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const filename=process.env.MAGICK_M5_JSON_FILE;
const policyPath=path.resolve(__dirname,
    "../../widgets/weather/StationMagickCelestialVisualPolicy.js");
const ctx=vm.createContext({Date,Math,isFinite});
vm.runInContext(fs.readFileSync(policyPath,"utf8")
    .replace(/^\.pragma library\s*/m,""),ctx);

test("actual JPL-backed M4 JSON is accepted by M5 presentation policy",{
    skip:!filename
},()=>{
    const raw=JSON.parse(fs.readFileSync(filename,"utf8"));
    assert.equal(raw.provenance.engine,"skyfield");
    assert.equal(raw.provenance.ephemeris_id,"de440s.bsp");
    assert.ok(raw.provenance.ephemeris_sha256.length===64);
    const view=ctx.model(raw);
    assert.equal(view.ready,true,view.reason);
    assert.equal(view.sampleCount,raw.sample_count);
    assert.ok(view.sampleCount>=3);
    assert.equal(view.series.length,2);
    assert.equal(view.relationships.length,1);
    assert.ok(view.events.length>=1);
    for(let i=0;i<view.series.length;i++){
        for(let j=0;j<view.sampleCount;j++){
            const point=view.series[i].rows[j];
            assert.equal(point.longitude_deg,
                raw.series[i].samples[j].longitude_deg);
            assert.equal(point.unix_ms,view.times[j]);
        }
    }
    const focus=ctx.selectedIndex(view,-1,-1);
    const positions=ctx.wheelPositions(view,focus);
    assert.equal(positions.length,2);
    const range=ctx.rangeFor(view,ctx.windowFor(view,1,0.5),"motion");
    assert.ok(Number.isFinite(range.min));
    assert.ok(Number.isFinite(range.max));
    assert.ok(range.max>range.min);
    const pairRange=ctx.rangeFor(view,ctx.windowFor(view,1,0.5),"aspects");
    assert.ok(pairRange.max>pairRange.min);
});
