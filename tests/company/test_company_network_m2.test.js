// Company Network M2, offline-only geographic and UI contract tests.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
function source(file) {
    return fs.readFileSync(path.join(root,file),"utf8");
}
function jsPolicy(file) {
    const context = {};
    vm.runInNewContext(source(file).replace(/^\s*\.pragma library\s*/, ""),context,{filename:file});
    return context;
}
const geo = jsPolicy("widgets/CompanyCoveragePolicy.js");
const lakes = jsPolicy("widgets/CompanyNaturalEarthLakes110.js");

test("USA map context contains Canada/Mexico and full Great Lakes latitude",()=>{
    const usa = geo.regions.lower48;
    assert.ok(usa.north>=55 && usa.south<=18);
    assert.ok(usa.west<=-129 && usa.east>=-60);
    assert.equal(geo.visibleStates("lower48","").length,49);
    assert.equal(geo.visibleCountries("lower48","").length,2);
    assert.equal(geo.visibleCountries("lower48","Canada")[0][0],"CAN");
    assert.equal(geo.visibleCountries("lower48","Mexico")[0][0],"MEX");
});

test("North America and global views retain all 50 states plus DC",()=>{
    assert.equal(geo.visibleStates("northAmerica","").length,51);
    assert.equal(geo.visibleStates("global","").length,51);
    assert.equal(geo.visibleStates("alaska","").length,1);
    assert.equal(geo.visibleStates("hawaii","").length,1);
    assert.deepEqual(Object.keys(geo.regions).sort(),
        ["alaska","global","hawaii","lower48","northAmerica"].sort());
    assert.equal(geo.regions.global.west,-180);
    assert.equal(geo.regions.global.east,180);
    assert.equal(geo.regions.global.south,-90);
    assert.equal(geo.regions.global.north,90);
    assert.equal(geo.regions.northAmerica.north>=80,true);
});

test("Canada/Mexico capital markers can be selected without confusing California",()=>{
    const ca = geo.countryForCode("CAN");
    const mx = geo.countryForCode("MEX");
    assert.equal(ca[1],"Canada");
    assert.equal(mx[1],"Mexico");
    assert.equal(geo.stateForCode("CA")[1],"California");
    const p=geo.project(ca[3],ca[4],600,380,"lower48",1,-94.5,36.5);
    assert.ok(p.visible);
    const picked=geo.nearestCountry("lower48",p.x,p.y,
        600,380,1,-94.5,36.5,4);
    assert.equal(picked[0],"CAN");
    assert.equal(geo.visibleCountries("global","Ottawa").length,1);
});

test("public-domain 110m lake layer contains the five Great Lakes",()=>{
    assert.equal(lakes.source.license,"PUBLIC DOMAIN");
    assert.equal(lakes.source.revision,"ca96624a56bd078437bca8184e78163e5039ad19");
    const names=lakes.lakes.map(x=>x.name);
    for(const expected of ["Lake Superior","Lake Michigan","Lake Huron",
                            "Lake Erie","Lake Ontario"])
        assert.ok(names.includes(expected),expected);
    for(const lake of lakes.lakes) {
        assert.ok(lake.rings.length>0,lake.name);
        for(const ring of lake.rings)
            assert.ok(ring.length>=3,lake.name);
    }
});

test("world, North America and US projections are reversible",()=>{
    const cases=[
        ["lower48",-75,45],
        ["northAmerica",-150,65],
        ["global",110,-20],
        ["global",-80,42]
    ];
    for(const [region,lon,lat] of cases) {
        const v=geo.defaultView(region);
        const p=geo.project(lon,lat,800,500,region,v.zoom,v.centerLon,v.centerLat);
        assert.ok(p.valid && p.visible,region);
        const round=geo.unproject(p.x,p.y,800,500,region,v.zoom,v.centerLon,v.centerLat);
        assert.ok(Math.abs(lon-round.lon)<1e-7,region);
        assert.ok(Math.abs(lat-round.lat)<1e-7,region);
        const next=geo.zoomAt(region,1,v.centerLon,v.centerLat,400,250,800,500,1);
        assert.ok(next.zoom>1 && next.zoom<=6,region);
    }
});

test("country and state reference layers remain separate from coverage facts",()=>{
    const qml=source("widgets/CompanyCoveragePane.qml");
    assert.match(qml,/CompanyNaturalEarthLakes110\.js/);
    assert.match(qml,/Lakes\.lakes/);
    assert.match(qml,/Context\.admin0Lines/);
    assert.match(qml,/Context\.admin1Lines/);
    assert.match(qml,/NO COMPANY COVERAGE VERIFIED/);
    assert.match(qml,/id: serviceDropdown/);
    assert.match(qml,/model: Geo\.serviceFamilies/);
    assert.match(qml,/onTriggered: root\.selectService\(modelData\)/);
    assert.match(qml,/id:"global"/);
    assert.match(qml,/id:"northAmerica"/);
    assert.match(qml,/Geo\.nearestCountry/);
    assert.match(qml,/root\.chooseCountry/);
    assert.doesNotMatch(qml,/Process\s*\{|FileView\s*\{/);
});

test("existing Company widget and Tasks dock ownership remain unchanged",()=>{
    const shell=source("shell.qml");
    assert.ok(shell.indexOf("id: companyNetworkHost")>=0);
    assert.ok(shell.indexOf("id: companyNetworkHost")<shell.indexOf("id: tasksHost"));
    const widget=source("widgets/CompanyNetworkW.qml");
    assert.match(widget,/CompanyCoveragePane/);
    assert.match(widget,/CompanyChassisPolicy\.frame/);
});
