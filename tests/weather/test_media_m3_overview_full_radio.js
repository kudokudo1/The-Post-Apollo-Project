"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const media=read("widgets/weather/StationMediaSubjectPane.qml");
const radio=read("widgets/weather/StationRadio.qml");
const header=read("widgets/weather/StationMediaHeader.qml");
const news=read("widgets/weather/StationNewsHub.qml");
const navigationSource=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const routeSource=read("widgets/weather/StationMediaSubjectPanelPolicy.js");
const nav=vm.createContext({});
const route=vm.createContext({});
vm.runInContext(navigationSource.replace(/^\.pragma library\s*$/m,""),nav);
vm.runInContext(routeSource.replace(/^\.pragma library\s*$/m,""),route);
const plain=x=>JSON.parse(JSON.stringify(x));

test("M3 MEDIA bottom rail exposes the existing SERVICES route as sixth mode",()=>{
    const modes=plain(nav.tabsFor("media/overview"));
    assert.equal(modes.length,6);
    assert.deepEqual(modes.map(x=>x.key),
        ["overview","news","watch","radio","creators","services"]);
    assert.deepEqual(modes[5],
        {key:"services",label:"SERVICES",path:"media/services/health"});
    assert.equal(nav.selectedGroup("media/services/health"),"services");
    assert.equal(route.kindForRoute(modes[5].path),"services");
    const workspace=read("widgets/weather/StationWorkspaceSurface.qml");
    assert.match(workspace,/model: surface\.activeTabs/);
    assert.match(workspace,/onTriggered: surface\.routeRequested\(modelData\.path\)/);
});

test("M3 OVERVIEW keeps the original NEWS bay first, with the full real RADIO below",()=>{
    assert.match(media,/id: overviewComponent/);
    assert.match(media,/id: mediaOverview/);
    assert.match(media,/id: overviewScroll/);
    assert.match(media,/objectName: "media-m3-overview-scroll"/);
    assert.match(media,/flickableDirection: Flickable\.VerticalFlick/);
    assert.match(media,/contentHeight: reportsBay\.height \+ 8 \+ overviewRadioBay\.height/);
    assert.match(media,/id: reportsBay/);
    assert.match(media,/objectName: "media-m3-news-top-bay"/);
    assert.match(media,/height: Math\.max\(0,\(mediaOverview\.height - 8\) \/ 2\)/);
    assert.match(media,/id: overviewRadioBay/);
    assert.match(media,/anchors\.top: reportsBay\.bottom/);
    assert.match(media,/height: Math\.max\(360, mediaOverview\.height - reportsBay\.height - 8\)/);
    assert.match(media,/id: overviewRadio/);
    assert.match(media,/objectName: "media-m3-overview-full-radio"/);
    assert.match(media,/subjectRoute: "media\/radio\/full"/);
    assert.match(media,/embeddedHeader: false/);
    assert.equal((media.match(/StationRadio\s*\{/g)||[]).length,2);
    assert.equal((media.match(/StationNewsHub\s*\{/g)||[]).length,2);
    assert.match(media,/readonly property var favoritesBridgeSnapshot:\s*overviewRadio\.favoritesBridgeSnapshot/);
    assert.doesNotMatch(media,/subjectRoute: "media\/overview"\s*\n\s*\}/);
    assert.match(radio,/readonly property bool compactOverview: subjectRoute === "media\/overview"/);
    assert.equal(route.radioGroupVisible("media/radio/full","search"),true);
    assert.equal(route.radioGroupVisible("media/radio/full","saved"),true);
    assert.equal(route.radioGroupVisible("media/radio/full","directory"),true);
    assert.equal(route.radioGroupVisible("media/radio/full","transport"),true);
});

test("M3 NEWS remains first in OVERVIEW and its fixed contextual filters act on the mounted NEWS hub",()=>{
    assert.match(header,/activeMode === "news" \|\| activeMode === "overview" \? Catalog\.sections/);
    assert.match(header,/mediaHeader\.activeMode==="news" \|\| mediaHeader\.activeMode==="overview"/);
    assert.match(header,/mediaHeader\.newsSectionRequested\(modelData\)/);
    assert.match(media,/readonly property var overviewNews: overviewNewsHub/);
    assert.match(media,/kind==="overview" \? mediaLoader\.item\.overviewNews : null/);
    assert.match(media,/onNewsSectionRequested: function\(section\)/);
    assert.match(media,/loadedNews\.selectSection\(section\)/);
    assert.match(media,/if \(kind==="news" && subjectRoute!=="media\/news\/full"\)/);
    assert.ok(media.includes('subjectRoute: "media/news/reports"'));
    assert.ok(media.includes("overviewChannelFilters: true"));
    assert.ok(media.includes('section: "REPORTS"'));
    assert.ok(news.includes("property bool overviewChannelFilters: false"));
    assert.match(news,/function selectSection\(nextSection\)/);
    assert.match(news,/stationNewsHub\.closeViewer\(\)/);
    assert.match(media,/const bay = overviewNewsHub\.playerViewportRect/);
    assert.match(media,/overviewNewsHub\.mapToItem\(/);
});

test("M3 isolated native check does not activate provider actions and radio controls remain the original owner",()=>{
    assert.match(media,/property bool providerActivationAllowed: true/);
    assert.equal((media.match(/stationOpen: mediaPane\.visible && mediaPane\.providerActivationAllowed/g)||[]).length,4);
    for(const s of [
        "StationRadioSavedStrips {",
        'id: fixedSearch',
        'id: fixedTransport',
        'id: radioScroll',
        'onClicked: stationRadio.loadSelection()',
        'onClicked: stationRadio.playbackAction("play")',
        'onClicked: stationRadio.toggleHighlightedFavorite()',
        'radioClient: "weather-radio"'
    ])assert.ok(radio.includes(s),s);
    assert.equal((media.match(/StationMediaHeader\s*\{/g)||[]).length,1);
    assert.equal((media.match(/StationMediaServicesPane\s*\{/g)||[]).length,1);
});
