"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const filename=process.env.MAGICK_M5C_JSON_FILE;
const pairId=process.env.MAGICK_M5C_PAIR;
const root=path.resolve(__dirname,"../..");
const makeCtx=(file)=>{
  const ctx=vm.createContext({Date,Math,isFinite,JSON});
  vm.runInContext(fs.readFileSync(path.join(root,file),"utf8")
      .replace(/^\.pragma library\s*/m,""),ctx);
  return ctx;
};
const Query=makeCtx("services/weather/CelestialVisualQueryPolicy.js");
const Visual=makeCtx("widgets/weather/StationMagickCelestialVisualPolicy.js");

test("real JPL 90-day M4 output matches M5c pair and M5 presentation",{
    skip:!(filename && pairId)
},()=>{
    const payload=JSON.parse(fs.readFileSync(filename,"utf8"));
    const req=Query.requestFor("2026-11-03",0,pairId,90);
    assert.ok(req,"preset recognized");
    assert.equal(Query.matchesResult(payload,req),true);
    assert.equal(payload.provenance.ephemeris_id,"de440s.bsp");
    assert.equal(payload.query.step_hours,12);
    assert.equal(payload.query.include_events,true);
    assert.equal(payload.sample_count,181);
    assert.deepEqual(payload.query.bodies,JSON.parse(JSON.stringify(req.bodies.slice().sort())));
    const visual=Visual.model(payload);
    assert.equal(visual.ready,true,visual.reason);
    assert.equal(visual.sampleCount,payload.sample_count);
    assert.equal(visual.series.length,2);
    assert.equal(visual.relationships.length,1);
    assert.equal(visual.events.length,payload.event_markers.length);
    for(let i=0;i<visual.series.length;i++){
        assert.ok(visual.series[i].rows.every(point=>
            point.longitude_deg>=0 && point.longitude_deg<360 &&
            Number.isFinite(point.longitude_rate_deg_per_day)));
    }
    const falsified={...payload,query:{...payload.query,
        start_utc:"2026-01-01T00:00:00.000000Z"}};
    assert.equal(Query.matchesResult(falsified,req),false);
});
