// Native Quickshell/compositor testing remains a separate acceptance gate.
// This suite validates deterministic geometry/geography and the UI source wiring.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname,"../..");
function source(relative) {
    return fs.readFileSync(path.join(root,relative),"utf8");
}
function policy(relative) {
    const context={};
    const js=source(relative).replace(/^\s*\.pragma library\s*/,"");
    vm.runInNewContext(js,context,{filename:relative});
    return context;
}
const coverage=policy("widgets/CompanyCoveragePolicy.js");
const chassis=policy("widgets/CompanyChassisPolicy.js");

test("all states and DC exist exactly once and have region-specific capital markers",()=>{
    assert.equal(coverage.states.length,51);
    assert.equal(new Set(coverage.states.map(x=>x[0])).size,51);
    assert.equal(coverage.visibleStates("lower48","").length,49);
    assert.equal(coverage.visibleStates("alaska","").length,1);
    assert.equal(coverage.visibleStates("hawaii","").length,1);
    for(const record of coverage.states) {
        assert.equal(record.length,6);
        assert.ok(record[3]>=-180 && record[3]<=180);
        assert.ok(record[4]>=-90 && record[4]<=90);
        assert.ok(coverage.regions[record[5]]);
    }
});

test("search and marker selection are geometric only",()=>{
    const maryland=coverage.stateForCode("MD");
    assert.equal(maryland[1],"Maryland");
    assert.equal(coverage.visibleStates("lower48","annapolis").length,1);
    const p=coverage.project(maryland[3],maryland[4],800,500,
        "lower48",1,-96,37);
    assert.ok(p.valid && p.visible);
    const picked=coverage.nearestState("lower48",p.x,p.y,800,500,1,-96,37,4);
    assert.equal(picked[0],"MD");
    const projectedBack=coverage.unproject(p.x,p.y,800,500,"lower48",1,-96,37);
    assert.ok(Math.abs(projectedBack.lon-maryland[3])<1e-6);
    assert.ok(Math.abs(projectedBack.lat-maryland[4])<1e-6);
    assert.equal(coverage.nearestState("lower48",-100,-100,800,500,1,-96,37,4),null);
});

test("pan and zoom stay within the selected region, no infinite coordinates",()=>{
    for(const region of ["lower48","alaska","hawaii"]) {
        let v=coverage.defaultView(region);
        v=coverage.zoomAt(region,v.zoom,v.centerLon,v.centerLat,
            250,180,800,500,1);
        assert.ok(v.zoom>1);
        v=coverage.pan(region,v.zoom,v.centerLon,v.centerLat,9999,-9999,800,500);
        const limits=coverage.regions[region];
        assert.ok(v.centerLon>=limits.west && v.centerLon<=limits.east);
        assert.ok(v.centerLat>=limits.south && v.centerLat<=limits.north);
        assert.ok(v.zoom>=1 && v.zoom<=6);
    }
});

test("1000×700 Weather default and Finance-style compact/fullscreen steps",()=>{
    const standard=chassis.frame("standard",2560,1440,12,9,12);
    assert.equal(standard.width+24,1000);
    assert.equal(standard.height+9+12,700);
    const compact=chassis.frame("compact",2560,1440,12,9,12);
    assert.equal(compact.width+24,640);
    assert.equal(compact.height+9+12,490);
    const fullscreen=chassis.frame("fullscreen",2560,1440,12,9,12);
    assert.equal(fullscreen.width+24,2560);
    assert.equal(fullscreen.height+9+12,1440);
    assert.equal(chassis.step("standard",-1),"compact");
    assert.equal(chassis.step("standard",1),"fullscreen");
    assert.equal(chassis.step("fullscreen",1),"fullscreen");
    assert.equal(chassis.step("compact",-1),"compact");
});

test("smaller screens clamp geometry and placement",()=>{
    const narrow=chassis.frame("standard",800,600,12,9,12);
    assert.ok(narrow.width+24<=800);
    assert.ok(narrow.height+21<=600);
    assert.equal(chassis.leftMargin("fullscreen",500,800,800),0);
    assert.equal(chassis.topMargin("fullscreen",200,600,600,12),0);
    assert.ok(chassis.leftMargin("standard",9999,800,800)<=800);
});

test("decorated dock keeps white stars/yellow city and open magenta halo",()=>{
    const qml=source("modules/CompanyNetwork.qml");
    assert.match(qml,/text: "\. ݁₊⊹"/);
    assert.match(qml,/text: "🏙︎"/);
    assert.match(qml,/text: "๋࣭⭑"/);
    assert.match(qml,/openGlowColor: Colors\.magenta/);
    assert.match(qml,/normalContentGlowColor: Colors\.blue/);
    assert.match(qml,/openFillColor: Colors\.black/);
    assert.match(qml,/color: Colors\.white/);
    assert.match(qml,/color: Colors\.yellow/);
    assert.match(qml,/onLeftClicked: toggleRequested\(\)/);
});

test("city icon and star ornaments share one vertical text-cell frame in dock and header",()=>{
    const dock=source("modules/CompanyNetwork.qml");
    const widget=source("widgets/CompanyNetworkW.qml");
    // Mixed-size Noto glyphs previously used incompatible top/baseline
    // placement. Equal-height text cells with centered line boxes make
    // the stars and city share a common geometric center.
    const dockMark=dock.split("id: companyMark",2)[1]
        .split("onLeftClicked: toggleRequested()",1)[0];
    const headerMark=widget.split("id: headerCity",2)[1]
        .split("\n            GohuText {",1)[0];
    for(const [label,mark,id,height] of [
        ["dock",dockMark,"companyMark",30],
        ["header",headerMark,"headerCity",24]
    ]) {
        assert.match(mark,new RegExp("height: "+height));
        assert.equal((mark.match(/NotoText\s*\{/g)||[]).length,3,
            label+" keeps exactly three art layers");
        assert.equal((mark.match(new RegExp("height: "+id+"\\.height","g"))||[]).length,3,
            label+" shares one vertical box across the artwork");
        assert.equal((mark.match(/verticalAlignment: Text\.AlignVCenter/g)||[]).length,3,
            label+" centers each text line box");
        assert.doesNotMatch(mark,/NotoText\s*\{\s*anchors\.verticalCenter:/,
            label+" must not anchor child glyphs inside the Row");
        for(const glyph of ['". ݁₊⊹"','"🏙︎"','"๋࣭⭑"'])
            assert.ok(mark.includes("text: "+glyph),label+" preserves icon artwork");
        assert.match(mark,/color: Colors\.white/);
        assert.match(mark,/color: Colors\.yellow/);
    }
    assert.match(dock,/anchors\.centerIn: parent/);
    assert.match(widget,/anchors\.verticalCenter: parent\.verticalCenter/);
});

test("central yellow city sits 2px below the white ornaments without shifting their cells",()=>{
    const cases=[
        ["dock",source("modules/CompanyNetwork.qml"),"companyMark","cityGlyphCell","cityGlyph",24],
        ["header",source("widgets/CompanyNetworkW.qml"),"headerCity","headerCityGlyphCell","headerCityGlyph",18]
    ];
    for(const [label,sourceText,rowId,cellId,glyphId,fontSize] of cases) {
        const row=sourceText.split("id: "+rowId,2)[1];
        assert.ok(row,label+" Row still exists");
        const cityBlock=row.split("id: "+cellId,2)[1];
        assert.ok(cityBlock,label+" owns a city-only wrapper");
        assert.match(cityBlock,new RegExp("width: "+glyphId+"\\.implicitWidth"),
            label+" retains intrinsic city width");
        assert.match(cityBlock,new RegExp("height: "+rowId+"\\.height"),
            label+" leaves shared Row geometry unchanged");
        assert.match(cityBlock,new RegExp("id: "+glyphId+"\\s+y: 2"),
            label+" lowers only the yellow city 2px");
        assert.match(cityBlock,new RegExp("font\\.pixelSize: "+fontSize),
            label+" preserves city glyph size");
        assert.match(cityBlock,/text: "🏙︎"/);
        assert.match(cityBlock,/color: Colors\.yellow/);
        // Both white ornament glyphs remain direct Row children and
        // preserve their original centered text cells.
        const firstStar=row.indexOf('text: ". ݁₊⊹"');
        const lastStar=row.indexOf('text: "๋࣭⭑"');
        const cell=row.indexOf("id: "+cellId);
        assert.ok(firstStar>=0 && cell>firstStar && lastStar>cell,
            label+" preserves the three-glyph artwork order");
        assert.equal((row.match(/y: 2/g)||[]).length,1,
            label+" applies only one intentional pixel offset");
    }
});

test("coverage UI is interactive, reference-only and contains no company data writer",()=>{
    const pane=source("widgets/CompanyCoveragePane.qml");
    const widget=source("widgets/CompanyNetworkW.qml");
    assert.match(pane,/StationNaturalEarthLand110\.js/);
    assert.match(pane,/StationNaturalEarthContext110\.js/);
    assert.match(pane,/Geo\.nearestState/);
    assert.match(pane,/Geo\.zoomAt/);
    assert.match(pane,/Geo\.pan/);
    assert.match(pane,/TextInput \{/);
    assert.match(pane,/NO COMPANY/gi);
    assert.doesNotMatch(pane,/Process\s*\{|FileView\s*\{/);
    assert.match(widget,/CompanyChassisPolicy\.frame/);
    assert.match(widget,/CompanyCoveragePane/);
    assert.match(widget,/coverageLoaded = true/);
    assert.match(widget,/id: expandChassisButton/);
    assert.match(widget,/id: collapseChassisButton/);
    assert.match(widget,/Colors\.magenta/);
    assert.doesNotMatch(widget,/Process\s*\{|FileView\s*\{/);
});

test("shell remains mounted beside Tasks and is untouched by M1",()=>{
    const shell=source("shell.qml");
    const a=shell.indexOf("id: companyNetworkHost");
    const b=shell.indexOf("id: tasksHost");
    assert.ok(a>=0 && b>a);
    assert.match(shell,/onToggleRequested: companyNetworkWindow\.toggle\(\)/);
});
