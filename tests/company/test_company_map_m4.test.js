// Company Network M4: detached source/geometry tests (no live Qt/network).
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
function policy(p) {
    const context={};
    vm.runInNewContext(read(p).replace(/^\s*\.pragma library\s*/,""),context);
    return context;
}
const cities=policy("widgets/CompanyCities50.js");
const math=policy("widgets/CompanyStreetMath.js");

test("offline city data carries 1:50m public-domain provenance and three neighbors",()=>{
    assert.equal(cities.source.license,"PUBLIC DOMAIN");
    assert.equal(cities.source.revision,"ca96624a56bd078437bca8184e78163e5039ad19");
    assert.ok(cities.cities.length>=1200);
    const counts={USA:0,CAN:0,MEX:0};
    for(const row of cities.cities) {
        if(row[3] in counts)counts[row[3]]++;
        assert.ok(Number.isFinite(row[1])&&Number.isFinite(row[2]));
        assert.ok(row[1]>=-180 && row[1]<=180);
        assert.ok(row[2]>=-90 && row[2]<=90);
    }
    assert.ok(counts.USA>100);
    assert.ok(counts.CAN>40);
    assert.ok(counts.MEX>20);
});

test("web mercator lat/lon to screen and back works at street scale",()=>{
    const places=[[-76.61,39.29],[-99.133,19.433],[-79.38,43.65],[-0.12,51.5],[139.69,35.68]];
    for(const [lon,lat] of places) {
        for(const z of [5,10,12,17]) {
            const p=math.screen(lon,lat,850,560,z,lon,lat);
            assert.ok(Math.abs(p.x-425)<1e-6);
            assert.ok(Math.abs(p.y-280)<1e-6);
            const back=math.invert(p.x,p.y,850,560,z,lon,lat);
            assert.ok(Math.abs(back.lon-lon)<1e-6);
            assert.ok(Math.abs(back.lat-lat)<1e-6);
            const tile=math.world(lon,lat,z);
            assert.ok(tile.x>=0 && tile.y>=0);
        }
    }
});

test("zoom-to-cursor and pan have sane world bounds",()=>{
    const initial={lon:-76.61,lat:39.29,z:11};
    const before=math.invert(250,150,800,540,initial.z,initial.lon,initial.lat);
    const more=math.zoomAt(250,150,800,540,initial.z,initial.lon,initial.lat,1);
    assert.equal(more.zoom,12);
    const after=math.invert(250,150,800,540,more.zoom,more.lon,more.lat);
    assert.ok(Math.abs(before.lon-after.lon)<1e-5);
    assert.ok(Math.abs(before.lat-after.lat)<1e-5);
    const panned=math.pan(20,-15,800,540,11,initial.lon,initial.lat);
    assert.ok(Number.isFinite(panned.lon)&&Number.isFinite(panned.lat));
});

test("+ HUB opens form immediately and no longer silently returns",()=>{
    const pane=read("widgets/CompanyCoveragePane.qml");
    const editor=read("widgets/CompanyHubEditor.qml");
    assert.match(pane,/else root\.beginHubEntry\(\)/);
    assert.match(pane,/function beginHubEntry\(\)/);
    assert.doesNotMatch(pane,/if \(hubStore\.state !== "ready"\) return/);
    assert.match(editor,/function begin\(region\)/);
    assert.match(editor,/function setCoordinates\(lon, lat\)/);
    assert.match(editor,/PICK LOCATION ON MAP/);
    assert.match(editor,/onTriggered: editor\.pickLocationRequested\(\)/);
    assert.match(editor,/storeState !== "ready"/);
    assert.match(pane,/onPickLocationRequested/);
    assert.match(pane,/onRetryStoreRequested: hubStore\.refresh\(\)/);
});

test("cities and street view are inside widget, but network is explicitly gated",()=>{
    const pane=read("widgets/CompanyCoveragePane.qml");
    const street=read("widgets/CompanyStreetMap.qml");
    assert.match(pane,/CityData\.cities/);
    assert.match(pane,/id: cityRow/);
    assert.match(pane,/CITIES ON/);
    assert.match(pane,/CompanyStreetMap \{/);
    assert.match(pane,/streetConsentOpen=true/);
    assert.match(pane,/ENABLE ONLINE STREET DETAIL/);
    assert.match(pane,/onTriggered: root\.startStreetView\(\)/);
    assert.match(pane,/© OpenStreetMap contributors/);
    assert.match(street,/active: false/);
    assert.match(street,/if\(!active \|\| !visible/);
    assert.match(street,/CompanyStreetTiles\.py/);
    assert.match(street,/Mercator\.screen/);
    assert.match(street,/Mercator\.invert/);
    assert.match(street,/© OpenStreetMap contributors/);
    assert.doesNotMatch(pane,/http:\/\/|https:\/\//);
});

test("M4 preserves explicit no-coverage and no personal field contracts",()=>{
    const pane=read("widgets/CompanyCoveragePane.qml");
    assert.match(pane,/NO COMPANY COVERAGE VERIFIED/);
    assert.match(pane,/Orange pins/);
    assert.doesNotMatch(pane,/clientName|employeeId|apiToken/);
    const store=read("services/company/CompanyHubStore.qml");
    assert.match(store,/expectedRevision:saved\.revision/);
});
