"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=name=>fs.readFileSync(path.join(root,name),"utf8");
const radio=read("widgets/weather/StationRadio.qml");
const media=read("widgets/weather/StationMediaSubjectPane.qml");
const header=read("widgets/weather/StationMediaHeader.qml");
const hub=read("widgets/weather/StationNewsHub.qml");
const services=read("widgets/weather/StationMediaServicesPane.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const workspace=read("widgets/weather/StationWorkspaceSurface.qml");
const navigation=read("widgets/weather/StationSubjectNavigationPolicy.js");
const policySrc=read("widgets/weather/StationMediaSubjectPanelPolicy.js");
const geometrySrc=read("widgets/weather/StationSubjectHeaderGeometry.js");
const catSrc=read("widgets/weather/StationNewsCatalogPolicy.js");
const p=vm.createContext({});
const g=vm.createContext({Math,Number,isFinite});
const cat=vm.createContext({});
vm.runInContext(policySrc.replace(/^\.pragma library\s*/m,""),p);
vm.runInContext(geometrySrc.replace(/^\.pragma library\s*/m,""),g);
vm.runInContext(catSrc.replace(/^\.pragma library\s*/m,""),cat);

test("M1 RADIO search and transport are fixed above and below the only scrollable list",()=>{
    const top=radio.indexOf('id: fixedSearch');
    const middle=radio.indexOf('id: radioScroll');
    const results=radio.indexOf('id: content');
    const bottom=radio.indexOf('id: fixedTransport');
    assert.ok(0<top && top<middle && middle<results && results<bottom);
    assert.match(radio,/id: fixedSearch[\s\S]*?anchors\.top: parent\.top/);
    assert.match(radio,/id: radioScroll[\\s\\S]*?anchors\\.top: savedStrips\\.bottom[\\s\\S]*?anchors\\.bottom: fixedTransport\\.top/);
    assert.match(radio,/StationRadioSavedStrips\\s*\\{/);
    assert.match(radio,/id: fixedTransport[\s\S]*?anchors\.bottom: parent\.bottom/);
    const pinnedTop=radio.slice(top,middle);
    const middleText=radio.slice(results,bottom);
    const pinnedBottom=radio.slice(bottom);
    for(const s of ['id: presetRow','id: queryRow','id: queryInput','label: "NEXT 50"'])
        assert.ok(pinnedTop.includes(s),s);
    for(const s of ['STATIONS // BROWSE','model: stationRadio.browseItems'])
        assert.ok(middleText.includes(s),s);
    for(const label of ["SELECT","LOAD","ENTER","PLAY","PAUSE","STOP"])
        assert.ok(pinnedBottom.includes('label: "'+label+'"'),label);
    assert.ok(pinnedBottom.includes('onClicked: stationRadio.selectHighlighted()'));
    assert.ok(pinnedBottom.includes('onClicked: stationRadio.loadSelection()'));
    assert.ok(pinnedBottom.includes('onClicked: stationRadio.enterHighlighted()'));
    assert.ok(pinnedBottom.includes('onClicked: stationRadio.playbackAction("play")'));
    assert.ok(pinnedBottom.includes('onClicked: stationRadio.playbackAction("pause")'));
    assert.ok(pinnedBottom.includes('onClicked: stationRadio.playbackAction("stop")'));
    assert.ok(pinnedBottom.includes("controller.playbackState.toUpperCase()"));
    assert.ok(pinnedBottom.includes("controller.ownsPlayback"));
    assert.equal((radio.match(/stationRadio\.sectionVisible\("/g)||[]).length,19);
    assert.equal((radio.match(/id: radioScroll/g)||[]).length,1);
    assert.ok(radio.includes('readonly property bool compactOverview: subjectRoute === "media/overview"'));
    assert.match(radio,/visible: !stationRadio\.compactOverview/);
});

test("M1 all MEDIA screens share the same C44 fixed title/tab/divider geometry",()=>{
    assert.equal(g.titleTop(),6);
    assert.equal(g.tabsTop(),28);
    assert.equal(g.ruleTop(),60);
    assert.equal(g.contentTop(),65);
    assert.match(media,/StationMediaHeader\s*\{/);
    assert.match(media,/anchors\.top: mediaHeader\.bottom/);
    assert.match(media,/anchors\.bottom: parent\.bottom/);
    assert.match(header,/height: HeaderGeometry\.contentTop\(\)/);
    assert.match(header,/anchors\.topMargin: HeaderGeometry\.titleToTabs/);
    assert.match(header,/height: HeaderGeometry\.tabHeight/);
    assert.match(header,/anchors\.topMargin: HeaderGeometry\.tabsToRule/);
    assert.match(header,/height: HeaderGeometry\.ruleHeight/);
    assert.match(header,/HeaderGeometry\.buttonWidth\(/);
    for(const label of ["OVERVIEW","NEWS","WATCH","RADIO","CREATORS","SERVICES"])
        assert.ok(header.includes('label:"'+label+'"'),label);
    assert.match(media,/onRouteRequested: function\(path\)/);
    assert.match(navigator,/onRouteRequested: function\(path\) \{ browser\.chooseRoute\(path\); \}/);
    assert.match(workspace,/onRouteRequested: function\(path\) \{ surface\.routeRequested\(path\); \}/);
    assert.match(hub,/property bool embeddedHeader: false/);
    assert.match(hub,/visible: !stationNewsHub\.embeddedHeader/);
    assert.match(media,/embeddedHeader: true/);
    assert.equal((media.match(/StationRadio\s*\{/g)||[]).length,2);
    assert.equal((media.match(/StationNewsHub\s*\{/g)||[]).length,2);
});

test("M1 SERVICES adds only one read-only route and does not start NEWS or MPD providers",()=>{
    assert.equal(p.kindForRoute("media/services/health"),"services");
    assert.equal(p.kindForRoute("media/services/fake"),"");
    assert.equal(p.kindForRoute("media/news/full"),"news");
    assert.equal(p.kindForRoute("media/radio/full"),"radio");
    assert.equal(Object.keys(p.ROUTES).length,20);
    assert.match(navigation,/\{id:"services",label:"SERVICES",children:/);
    assert.match(navigation,/\{id:"health",label:"MEDIA DIAGNOSTICS \/\/ DASHBOARD"\}/);
    assert.match(media,/StationMediaServicesPane\s*\{/);
    assert.match(media,/mediaPane\.kind === "services"/);
    assert.match(services,/NOT MOUNTED ON SERVICES/);
    assert.match(services,/Catalog\.channels\.length/);
    assert.match(services,/Object\.keys\(MediaPolicy\.ROUTES\)\.length/);
    assert.doesNotMatch(services,/HeadlessMediaController|FileView\s*\{|Process\s*\{|XMLHttpRequest|StationDiscovery\s*\{|StationRadio\s*\{|StationNewsHub\s*\{/);
    assert.equal(cat.channels.length,18);
});
