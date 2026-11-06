"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(pathname){
  const ctx=vm.createContext({});
  vm.runInContext(read(pathname).replace(/^\.pragma library\s*/,""),ctx);
  return ctx;
}
const V=policy("widgets/weather/StationMagickWheelViewportPolicy.js");
const A=policy("widgets/weather/StationMagickAnnualAtlasPolicy.js");
const near=(a,b,eps=1e-8)=>assert.ok(Math.abs(a-b)<eps,String(a)+" != "+String(b));

test("M7c full-viewport fit radius, compact-screen magnification and bounds",()=>{
  // The old canvas was ~90px tall below controls/detail; it now spans 220px.
  near(V.fitRadius(420,220),(.47*(220-8)));
  near(V.fitRadius(420,0),5);
  near(V.MIN_ZOOM,1);
  near(V.DEFAULT_ZOOM,1.6);
  near(V.MAX_ZOOM,8);
  assert.ok(2*V.fitRadius(420,220)*V.DEFAULT_ZOOM>300);
  assert.ok(2*V.fitRadius(420,90)<100,"old leftover-space dial was too small");
  assert.ok(V.fitRadius(220,420)<V.fitRadius(420,420));
});
test("zooming around cursor preserves the source point and inverse pick geometry",()=>{
  const width=420,height=220,r=V.fitRadius(width,height);
  const selected={x:235,y:135};
  let before=V.inversePoint(selected.x,selected.y,width,height,0,0,1.6);
  let z=V.zoomAt(1.6,0,0,1.25,selected.x,selected.y,width,height,r);
  assert.equal(z.zoom,2);
  const after=V.inversePoint(selected.x,selected.y,width,height,z.panX,z.panY,z.zoom);
  near(after.x,before.x);near(after.y,before.y);
  z=V.zoomAt(z.zoom,z.panX,z.panY,1/1.25,
    selected.x,selected.y,width,height,r);
  near(z.zoom,1.6);
  near(z.panX,0);near(z.panY,0);
  assert.ok(A.indexAtAngle(before.x,before.y,0,0,365)>=0);
});
test("fit, max-zoom, and pan limits prevent losing the wheel",()=>{
  const width=420,height=220,r=V.fitRadius(width,height);
  let z=V.zoomAt(1.6,0,0,10000,210,110,width,height,r);
  assert.equal(z.zoom,8);
  assert.ok(Math.abs(z.panX)<=V.panLimit(r,z.zoom));
  let bounded=V.boundedPan(9999,-9999,r,8);
  near(bounded.x,V.panLimit(r,8));
  near(bounded.y,-V.panLimit(r,8));
  z=V.zoomAt(8,0,0,0.000001,210,110,width,height,r);
  assert.equal(z.zoom,1);
  assert.equal(z.panX,0);assert.equal(z.panY,0);
  assert.equal(V.zoomAt(1,0,0,Number.NaN,0,0,width,height,r),null);
  assert.equal(V.inversePoint(1,1,10,10,0,0,0),null);
});
test("after panning, an inverse coordinate pick maps to the same calendar date",()=>{
  const count=366,width=420,height=220,r=V.fitRadius(width,height);
  const dateIdx=111,angle=A.angleFor(dateIdx,count);
  const localX=Math.cos(angle)*r*.75;
  const localY=Math.sin(angle)*r*.75;
  const zoom=3.2,panX=55,panY=-18;
  const screenX=width/2+panX+localX*zoom;
  const screenY=height/2+panY+localY*zoom;
  const inverse=V.inversePoint(screenX,screenY,width,height,panX,panY,zoom);
  near(inverse.x,localX);near(inverse.y,localY);
  assert.equal(A.indexAtAngle(inverse.x,inverse.y,0,0,count),dateIdx);
});
test("M7c QML keeps yearly Moon/Solar data, includes real zoom/pan/focus controls",()=>{
  const qml=read("widgets/weather/StationMagickAnnualCalendarPane.qml");
  const policy=read("widgets/weather/StationMagickWheelViewportPolicy.js");
  const host=read("widgets/weather/StationMagickLunarSolarPane.qml");
  const backend=read("scripts/weather/celestial_annual_calendar.py");
  assert.match(host,/StationMagickAnnualCalendarPane\s*\{/);
  assert.match(qml,/anchors\.top: topModes\.bottom/);
  assert.match(qml,/id: wheel[\s\S]*anchors\.bottom: parent\.bottom/);
  assert.match(qml,/ctx\.translate\(width\/2\+annualPane\.panX,height\/2\+annualPane\.panY\)/);
  assert.match(qml,/ctx\.scale\(annualPane\.wheelZoom,annualPane\.wheelZoom\)/);
  assert.match(qml,/onWheel: function\(wheelEvent\)/);
  assert.match(qml,/onPositionChanged: function\(mouse\)/);
  assert.match(qml,/annualPane\.panBy\(mouse\.x-lastX,mouse\.y-lastY\)/);
  assert.match(qml,/Viewport\.inversePoint\(/);
  assert.match(qml,/Viewport\.zoomAt\(/);
  assert.match(qml,/onDoubleClicked: annualPane\.fitWheel\(\)/);
  for(const label of ['"FIT"','"RESET"','"FOCUS"','"BACK"',
    '"CALCULATE YEAR"','"FORECAST"','"SOLAR YEAR"','"LUNAR YEAR"']){
    assert.ok(qml.includes(label),label);
  }
  assert.match(qml,/StationMagickForecastCalendarPane\s*\{/);
  assert.match(qml,/data\.solar_terms/);
  assert.match(qml,/data\.lunar_events/);
  assert.match(qml,/day\.illumination/);
  assert.match(backend,/almanac\.moon_phases\(kernel\)/);
  for(const forbidden of ["Process {","Timer {","FileView {","XMLHttpRequest",
          "Qt.openUrlExternally","Math.random(","Date.now()"]){
    assert.ok(!qml.includes(forbidden),"out of scope: "+forbidden);
    assert.ok(!policy.includes(forbidden),"out of scope: "+forbidden);
  }
});
