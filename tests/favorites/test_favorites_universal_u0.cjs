"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = file => fs.readFileSync(path.join(root,file),"utf8");
const policySource = read("services/favorites/FavoritesResourcePolicy.js");
const adaptersSource = read("services/favorites/FavoritesReadOnlyAdapters.js");
const policy = {};
vm.runInNewContext(policySource.replace(/^\.pragma library\s*$/m,""),policy);
const adapters = {Policy:policy};
vm.runInNewContext(adaptersSource
    .replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import "FavoritesResourcePolicy\.js" as Policy\s*$/m,""),adapters);
const plain = x => JSON.parse(JSON.stringify(x));

function norm(provider,kind,resourceId,capabilities,label) {
    const candidate = {provider,kind,resourceId,capabilities};
    if (label !== undefined) candidate.label = label;
    return policy.normalize(candidate);
}

test("stable, domain-separated identities do not collide", () => {
    assert.equal(policy.SCHEMA,"post-apollo.favorites.resource.v1");
    const colon = norm("appcontrol","item","run|a:b",["favorite"]);
    const pipe = norm("appcontrol","item","run|a|b",["favorite"]);
    const zone = norm("time","timezone","America/New_York",["favorite"]);
    assert.equal(colon.ok,true);
    assert.equal(pipe.ok,true);
    assert.match(colon.record.key,/^fav1:local:appcontrol:item:/);
    assert.notEqual(colon.record.key,pipe.record.key);
    assert.notEqual(colon.record.key,zone.record.key);
    assert.equal(colon.record.key,policy.identityKey("appcontrol","item","run|a:b"));
    assert.equal(norm("appcontrol","task-watch","run|a:b",["watch"]).ok,true);
});

test("scope, namespace, ID and label validation fail closed", () => {
    for (const provider of ["", "AppControl","../app","a/b","a:b","a".repeat(49)]) {
        assert.equal(norm(provider,"item","one",["favorite"]).ok,false,provider);
    }
    for (const id of [""," bad","bad ","x\nz","x\u0000z","\ud800",
                       "x".repeat(policy.MAX_ID_LENGTH+1)]) {
        assert.equal(norm("time","timezone",id,["favorite"]).ok,false,JSON.stringify(id));
    }
    assert.equal(policy.normalize({
        provider:"time",kind:"zone",resourceId:"UTC",scope:"organization",
        capabilities:["favorite"]
    }).reason,"UNSUPPORTED_SCOPE");
    assert.equal(policy.normalize({
        provider:"time",kind:"zone",resourceId:"UTC",capabilities:["favorite"],
        label:"x".repeat(121)
    }).reason,"INVALID_LABEL");
    assert.equal(policy.normalize([]).ok,false);
});

test("capabilities are explicit, bounded, unique and non-executable", () => {
    const valid = norm("weather-home","card","sky|next-hours",["favorite","pin"]);
    assert.deepEqual(plain(valid.record.capabilities),["favorite","pin"]);
    for (const caps of [["favorite","favorite"],["make-payment"],["WATCH"],
                         [null],"favorite",policy.CAPABILITIES.concat(["extra"])]) {
        assert.equal(norm("time","timezone","UTC",caps).ok,false);
    }
    const malicious = policy.normalize({
        provider:"hospital",kind:"activity",resourceId:"room:123",
        label:"Activity",capabilities:["favorite"],
        available:true,verified:true,authorization:"admin",secret:"SHOULD_NOT_LEAK",
        action:()=>{throw new Error("never called");},
        pid:1,command:"sudo reboot"
    });
    assert.equal(malicious.ok,true);
    assert.deepEqual(Object.keys(plain(malicious.record)).sort(),[
        "availability","capabilities","key","kind","label","provider",
        "resourceId","schema","scope"
    ]);
    assert.equal(malicious.record.availability,"unresolved");
    assert.equal(JSON.stringify(malicious.record).includes("SHOULD_NOT_LEAK"),false);
    assert.equal(JSON.stringify(malicious.record).includes("sudo reboot"),false);
});

test("multi-source merge rejects invalid entries and collisions without writing", () => {
    const app=norm("appcontrol","item","app|foo",["favorite"]).record;
    const wx=norm("weather-home","card","sky|foo",["pin"]).record;
    const merged=policy.mergeSnapshots([[app],[wx]]);
    assert.equal(merged.ok,true);
    assert.equal(merged.items.length,2);
    assert.equal(policy.mergeSnapshots([[app],[app]]).reason,"DUPLICATE_IDENTITY");
    assert.equal(policy.mergeSnapshots([[app],null]).reason,"INVALID_SNAPSHOTS");
    assert.equal(policy.mergeSnapshots([[app],[{bad:1}]]).ok,false);
    // The merge normalizes records again and does not forward extraneous data.
    const extra={...plain(app),staleValue:42,available:true};
    assert.equal(policy.mergeSnapshots([[extra]]).items[0].availability,"unresolved");
});

test("AppControl's four old lists project without changing the donor file", () => {
    const old={
        favoriteKeys:["app|foo","task|python"],
        favoriteDetailActionKeys:["app|foo|open"],
        favoriteMonitorBoxKeys:["watchbox|system|cpu"],
        favoriteTaskMetricKeys:["taskmetric|python|mem"]
    };
    const copy=plain(old);
    const projected=adapters.appControl(old);
    assert.equal(projected.invalidCount,0);
    assert.deepEqual(plain(old),copy);
    assert.deepEqual(plain(projected.items.map(x=>x.kind)),[
        "item","item","preferred-action","monitor-watch","task-watch"
    ]);
    assert.equal(projected.items[1].capabilities.includes("protect"),false);
    assert.equal(projected.items.every(x=>x.availability==="unresolved"),true);
});

test("Weather HOME projects stable IDs but no sensor samples", () => {
    const original={
        schema:"post-apollo.weather-home-favorites.v1",
        panelRoutes:["home/auto","home/health"],
        cardKeys:["sky|next-hours","space|geomagnetic"],
        liveValues:{temperature:"1000 C"}
    };
    const items=adapters.weatherHome(original).items;
    assert.equal(items.length,4);
    assert.deepEqual(plain(items[0].capabilities),["favorite","rotate"]);
    assert.deepEqual(plain(items[2].capabilities),["favorite","pin"]);
    assert.equal(JSON.stringify(items).includes("1000 C"),false);
});

test("World Clock and saved Places preserve stable identity and labels", () => {
    const clock=adapters.worldClock({zones:["UTC","America/New_York"]});
    const places=adapters.places([{id:7,place:{
        label:"Temporary destination",latitude:38.9,longitude:-77.0
    }}]);
    assert.equal(clock.invalidCount,0);
    assert.equal(places.invalidCount,0);
    assert.equal(places.items[0].resourceId,"7");
    assert.equal(places.items[0].label,"Temporary destination");
    assert.equal(places.items[0].capabilities.includes("recall"),true);
    assert.equal(JSON.stringify(places).includes("38.9"),false);
    assert.equal(policy.mergeSnapshots([clock.items,places.items]).ok,true);
});

test("Notifications and Hospital remain scoped to source and event identities", () => {
    const notices=adapters.notifications([
        {appKey:"org.mozilla.firefox",source:"Firefox",sourceId:"firefox"}
    ]);
    const events=adapters.hospital(["reception:event-18"]);
    assert.equal(notices.items[0].kind,"source");
    assert.equal(events.items[0].kind,"activity");
    assert.equal(events.items[0].capabilities.includes("protect"),false);
    assert.equal(policy.mergeSnapshots([notices.items,events.items]).ok,true);
});

test("RADIO UUID favorite and recent combine without stream URLs or autoplay", () => {
    const id="123e4567-e89b-42d3-a456-000000000001";
    const station={ref:{source:"radio-browser",kind:"station",id},
        title:"Public Station",streamHost:"example.invalid",
        playback:{playing:true}};
    const radio=adapters.radio([station],[station]);
    assert.equal(radio.invalidCount,0);
    assert.equal(radio.items.length,1);
    assert.deepEqual(plain(radio.items[0].capabilities),["favorite","recall","recent"]);
    assert.equal(JSON.stringify(radio).includes("example.invalid"),false);
    assert.equal(adapters.radio([station,{ref:{source:"other",id},title:"Bad"}],[])
        .invalidCount,1);
});

test("invalid legacy rows surface counts rather than inventing identifiers", () => {
    assert.equal(adapters.appControl({favoriteKeys:[],favoriteDetailActionKeys:[],
        favoriteMonitorBoxKeys:[],favoriteTaskMetricKeys:[{}]}).invalidCount,1);
    assert.equal(adapters.worldClock({zones:["UTC",null]}).invalidCount,1);
    assert.equal(adapters.places([{id:-1,place:{label:"bad"}}]).invalidCount,1);
    assert.equal(adapters.notifications([{noKey:true}]).invalidCount,1);
    assert.equal(adapters.hospital(null).invalidCount,1);
});

test("U0 contracts are passive and legacy writers are unchanged", () => {
    for (const source of [policySource,adaptersSource]) {
        assert.doesNotMatch(source,/Quickshell\.Io|FileView\s*\{|writeAdapter\(|setText\(|execDetached|Process\s*\{|signal\s*\(/);
    }
    const store=read("services/favorites/FavoritesStore.qml");
    assert.match(store,/\/appcontrol-favorites\.json/);
    assert.match(store,/property list<string> favoriteKeys:/);
    const weather=read("services/weather/WeatherHomeFavoritesStore.qml");
    assert.match(weather,/\/weather-home-favorites-v1\.json/);
    const time=read("services/time/TimeSettings.qml");
    assert.match(time,/\/time-world-favorites-v1\.json/);
});
