"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root,p), "utf8");
function load(p,env) {
    vm.runInNewContext(read(p).replace(/^\.pragma library\s*$/m, "")
        .replace(/^\.import ".+" as \w+\s*$/gm, ""),env,{filename:p});
}
const Resource={};load("services/favorites/FavoritesResourcePolicy.js",Resource);
const Default={Resource};load("services/favorites/FavoritesDefaultPolicy.js",Default);
const Collections={Resource,Default};
load("services/favorites/FavoritesCollectionsPolicy.js",Collections);
const Adapters={Policy:Resource};
load("services/favorites/FavoritesReadOnlyAdapters.js",Adapters);
const WeatherRules={};load("services/weather/WeatherHomeFavoritesPolicy.js",WeatherRules);
const WeatherHome={WeatherRules,Adapters};
load("services/favorites/FavoritesWeatherHomeProjection.js",WeatherHome);
const Notifications={Adapters};
load("services/favorites/FavoritesNotificationsProjection.js",Notifications);
const Radio={Adapters};load("services/favorites/FavoritesRadioProjection.js",Radio);
const Hospital={Adapters};
load("services/favorites/FavoritesHospitalProjection.js",Hospital);
const Hub={Resource,Default,Collections,Adapters,WeatherHome,
    NotificationsProjection:Notifications,RadioProjection:Radio,
    HospitalProjection:Hospital};
load("services/favorites/FavoritesManagementPolicy.js",Hub);
const OwnerNavigation={};
load("services/favorites/FavoritesOwnerNavigationPolicy.js",OwnerNavigation);
const key=(provider,kind,id)=>Resource.identityKey(provider,kind,id);

test("owner-readonly starred alarms have exact IDs but no private note/tone/audio",()=>{
    const saved=[
        {id:7,name:"Morning",favorite:true,note:"PRIVATE DIAGNOSIS",
            hour:7,minute:45,soundId:"user-secret"},
        {id:8,name:"Unstarred",favorite:false,note:"hidden"},
        {id:9,name:"Evening",favorite:true},
        {id:10,name:"bad\nlabel",favorite:true},
        {id:11,name:"New",favorite:"true"}
    ];
    const out=Adapters.clockAlarms(saved);
    assert.equal(out.items.length,2);
    assert.equal(out.items[0].key,key("clock-alarm","alarm","7"));
    assert.equal(out.items[0].label,"ALARM // Morning");
    assert.equal(out.items[1].label,"ALARM // Evening");
    assert.equal(out.invalidCount,1);
    assert(!JSON.stringify(out).includes("PRIVATE DIAGNOSIS"));
    assert(!JSON.stringify(out).includes("user-secret"));
    assert(!JSON.stringify(out).includes("Unstarred"));
});

test("Angel number stars reuse original default-store identity",()=>{
    const angel=key("angel","number","1122");
    const other=key("finance","instrument","NYSE:AAA");
    const result=Adapters.angelNumbers([other,angel,
        "fav1:local:angel:number:bad",key("angel","number","000")]);
    assert.deepEqual(JSON.parse(JSON.stringify(result.items.map(x=>x.resourceId))),
        ["1122","000"]);
    assert.equal(result.invalidCount,1);
    assert.equal(result.items[0].label,"ANGEL // 1122");
    assert.equal(result.items[0].key,angel);
});

test("CPU++ lists owner-owned alarms and existing zones/Angel, without double stores",()=>{
    const number=key("angel","number","222");
    const alarms=[{id:31,name:"Wake up",favorite:true,note:"secret side data"}];
    const rows=Hub.list(["UTC"],[],[number],[],
        null,null,null,null,null,null,null,alarms).rows;
    const tz=rows.find(x=>x.provider==="time"&&x.kind==="timezone");
    const angel=rows.find(x=>x.provider==="angel"&&x.kind==="number");
    const alarm=rows.find(x=>x.provider==="clock-alarm");
    assert(tz);assert(angel);assert(alarm);
    assert.equal(tz.category,"CLOCK");
    assert.equal(alarm.key,key("clock-alarm","alarm","31"));
    assert.equal(alarm.category,"CLOCK");
    assert.equal(alarm.menu,"ALARMS");
    assert.equal(alarm.readOnly,true);
    assert.equal(alarm.favoriteType,"SAVED ALARM");
    assert.equal(angel.isFavorite,true);
    assert.equal(angel.category,"NEW");
    assert(!JSON.stringify(rows).includes("secret side data"));
    assert.deepEqual(JSON.parse(JSON.stringify(OwnerNavigation.plan(alarm))),
                     {ok:true,owner:"clock",view:"alarm"});
    assert.deepEqual(JSON.parse(JSON.stringify(OwnerNavigation.plan(angel))),
                     {ok:true,owner:"clock",view:"angel"});
    assert.equal(OwnerNavigation.plan({...alarm,isFavorite:false}).ok,false);
    assert.equal(OwnerNavigation.plan({...angel,key:"bad"}).ok,false);
});

test("Clock ALL FAVS reuses worlds and original providers, with no new favorite writer",()=>{
    const catalog=read("services/favorites/FavoritesUnifiedCatalog.qml");
    const time=read("widgets/TimeW.qml");
    const preview=read("components/FavoritesUnifiedPreview.qml");
    const shell=read("shell.qml");
    const angel=read("widgets/AngelPane.qml");
    const cpu=read("widgets/CpuPlusW.qml");
    const management=read("services/favorites/FavoritesManagementPolicy.js");
    const cpuPane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
    for(const token of ["worldSource: TimeSettings",
        "alarmSource: AlarmManagerService",
        "angelDefaultSource: FavoritesDefaultStore",
        "model: TimeSettings.worldFavoriteZones",
        "snapshot: unifiedFavoritesCatalog.snapshot"]) assert(time.includes(token),token);
    for(const token of ["Adapters.clockAlarms", "Adapters.angelNumbers",
        '["time", "clock-alarm", "angel", "places", "appcontrol"]'])
        assert(catalog.includes(token),token);
    assert(preview.includes("contentWidth: groupSummaries.implicitWidth"));
    assert(management.includes("Adapters.clockAlarms(alarmSnapshot)"));
    assert(cpu.includes("AlarmManagerService.document.alarms)"));
    assert(cpuPane.includes("id: angelOpenButton"));
    assert(cpuPane.includes("pane.defaultOwner.togglePinned(pane.selectedResource.key)"));
    assert(cpuPane.includes("pane.defaultOwner.setFavorite(item.key,false)"));
    assert(angel.includes("function openFavoriteJournal()"));
    assert(time.includes("function openFavoriteView(view)"));
    assert(shell.includes('owner==="clock" && (view==="alarm" || view==="angel")'));
    for(const forbidden of ["FileView {", "Process {", "Qt.openUrlExternally",
        "execDetached(", "setFavorite(", "toggleFavorite("]) {
        assert(!catalog.includes(forbidden),"catalog may not act: "+forbidden);
    }
    assert(!management.includes("alarmFile.setText"));
});
