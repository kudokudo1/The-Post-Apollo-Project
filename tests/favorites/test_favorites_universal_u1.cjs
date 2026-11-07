"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname,"../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const res={};
vm.runInNewContext(read("services/favorites/FavoritesResourcePolicy.js")
    .replace(/^\.pragma library\s*$/m,""),res);
const policy={Resource:res};
vm.runInNewContext(read("services/favorites/FavoritesDefaultPolicy.js")
    .replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import "FavoritesResourcePolicy\.js" as Resource\s*$/m,""),policy);
const copy=x=>JSON.parse(JSON.stringify(x));
function key(provider="finance",kind="instrument",id="NASDAQ:EXAMPLE") {
    return res.identityKey(provider,kind,id);
}

test("default schema stores only memberships and revision",()=>{
    const doc=copy(policy.empty());
    assert.deepEqual(doc,{schema:"post-apollo.favorites.default.v1",
        version:1,revision:0,favorites:[],pins:[]});
    assert.equal(policy.parse(JSON.stringify(doc)).ok,true);
    assert.equal(policy.checkKey(key()).ok,true);
    assert.equal(policy.checkKey(key("a","b","c")).ok,true);
    assert.equal(policy.checkKey(key("finance","instrument","😺")).ok,true);
    assert.equal(policy.checkKey(key("finance","instrument","x".repeat(2048))).ok,true);
});

test("encoded keys must round-trip canonically; no unscoped or malformed IDs",()=>{
    for(const bad of ["","app|foo","fav1:local:finance:instrument:",
        "fav1:local:finance:instrument:thing:more",
        "fav1:local:finance:instrument:%2f",
        "fav1:local:finance:instrument:%G1",
        "fav1:local:finance:instrument:%ED%A0%80",
        "fav1:organization:finance:instrument:a",
        "fav1:local:Finance:instrument:a",
        "fav1:local:finance:instrument:a\nb",
        key("finance","instrument","x".repeat(2048))+"junk",
        {}]) {
        assert.equal(policy.checkKey(bad).ok,false,String(bad).slice(0,100));
    }
    for(const provider of ["appcontrol","weather-home","radio","time",
                            "places","notifications","hospital"]) {
        assert.equal(policy.checkKey(key(provider,"item","abc")).reason,
            "EXTERNAL_OWNER",provider);
    }
});

test("favorites and pins are independent, bounded, ordered and immutable",()=>{
    const initial=policy.empty();
    const a=key("finance","instrument","A");
    const b=key("finance","instrument","B");
    const first=policy.setFeature(initial,"favorite",a,true);
    assert.equal(first.ok,true);
    assert.equal(first.document.revision,1);
    assert.deepEqual(copy(first.document.favorites),[a]);
    assert.deepEqual(copy(initial.favorites),[]);
    const second=policy.setFeature(first.document,"pin",a,true);
    assert.deepEqual(copy(second.document.favorites),[a]);
    assert.deepEqual(copy(second.document.pins),[a]);
    const third=policy.setFeature(second.document,"favorite",b,true);
    assert.deepEqual(copy(third.document.favorites),[b,a]);
    const last=policy.toggleFeature(third.document,"favorite",a);
    assert.equal(last.document.favorites.includes(a),false);
    assert.equal(last.document.pins.includes(a),true,
        "unfavorite must not implicitly unpin");
    assert.equal(policy.setFeature(last.document,"pin",a,true).changed,false);
    assert.equal(policy.setFeature(last.document,"watch",a,true).reason,"INVALID_FEATURE");
    assert.equal(policy.setFeature(last.document,"pin",a,"true").reason,"INVALID_FEATURE");
});

test("existing or corrupted source fails closed without rewriting",()=>{
    const initial=policy.empty();
    const good=policy.setFeature(initial,"favorite",key(),true);
    const raw=JSON.stringify(good.document);
    assert.deepEqual(copy(policy.parse(raw).document),copy(good.document));
    for(const bad of [
        "", "{invalid", "[]", "null",
        JSON.stringify({...initial,version:9}),
        JSON.stringify({...initial,schema:"post-apollo.weather-home-favorites.v1"}),
        JSON.stringify({...initial,revision:-1}),
        JSON.stringify({...initial,revision:1.5}),
        JSON.stringify({...initial,favorites:"invalid"}),
        JSON.stringify({...initial,pins:[key(),key()]}),
        JSON.stringify({...initial,favorites:[key("time","timezone","UTC")]}),
        JSON.stringify({...initial,unknownField:true}),
        "x".repeat(policy.MAX_DOCUMENT_CHARS+1)
    ]) {
        assert.equal(policy.parse(bad).ok,false,bad.slice(0,60));
    }
    assert.equal(policy.parse(JSON.stringify({...initial,version:9})).reason,
        "UNSUPPORTED_VERSION");
    assert.equal(policy.parse(JSON.stringify({...initial,unknownField:1})).reason,
        "UNSUPPORTED_FIELDS");
    assert.deepEqual(copy(initial.favorites),[]);
});

test("capacity and revision limit refuse rather than evict favorites",()=>{
    const initial=policy.empty();
    const fullPins=Array.from({length:policy.MAX_PINS},(_,i)=>key("finance","card","p"+i));
    const full={
        ...initial,
        pins:fullPins
    };
    const attempt=policy.setFeature(full,"pin",key("finance","card","overflow"),true);
    assert.equal(attempt.reason,"MEMBERSHIP_FULL");
    assert.equal(fullPins.length,policy.MAX_PINS);
    assert.equal(policy.setFeature(full,"pin",fullPins[0],false).ok,true);
    assert.equal(policy.setFeature({
        ...initial,revision:Number.MAX_SAFE_INTEGER-1
    },"favorite",key(),true).reason,"REVISION_LIMIT");
});

test("two write candidates computed from latest draft do not lose rapid taps",()=>{
    const start=policy.empty();
    const a=key("finance","instrument","a");
    const first=policy.toggleFeature(start,"favorite",a).document;
    const second=policy.toggleFeature(first,"pin",a).document;
    const third=policy.toggleFeature(second,"favorite",a).document;
    const fourth=policy.toggleFeature(third,"favorite",a).document;
    assert.equal(fourth.revision,4);
    assert.equal(policy.contains(fourth,"favorite",a),true);
    assert.equal(policy.contains(fourth,"pin",a),true);
    assert.equal(start.revision,0);
    assert.equal(first.revision,1);
});

test("UI is gated on capability, key ownership and loaded store state",()=>{
    const control=read("components/FavoritesToggleButton.qml");
    assert.match(control,/Resource\.normalize\(resource\)/);
    assert.match(control,/normalizedResource\.record\.capabilities\.indexOf\(feature\) >= 0/);
    assert.match(control,/store\.canEdit && store\.acceptsKey\(resourceKey\)/);
    assert.match(control,/onLeftClicked:/);
    assert.match(control,/store\.toggleFavorite\(resourceKey\)/);
    assert.match(control,/store\.togglePinned\(resourceKey\)/);
    assert.match(control,/selected: feature === "pin"/);
    assert.match(read("components/qmldir"),
        /FavoritesToggleButton 1\.0 FavoritesToggleButton\.qml/);
});

test("store serializes atomic writes, respects errors and does not pre-write empty files",()=>{
    const src=read("services/favorites/FavoritesDefaultStore.qml");
    assert.match(src,/pragma Singleton/);
    assert.match(src,/favorites-default-v1\.json/);
    assert.match(src,/atomicWrites: true/);
    assert.match(src,/watchChanges: false/);
    assert.match(src,/root\.storageState = "empty"/);
    assert.match(src,/root\.storageState = "error"/);
    assert.match(src,/storageState = result\.reason === "UNSUPPORTED_VERSION"/);
    assert.match(src,/property var pendingDocument: null/);
    assert.match(src,/property var queuedDocument: null/);
    assert.match(src,/queuedDocument !== null \? queuedDocument/);
    assert.match(src,/if \(pendingDocument !== null\)/);
    assert.match(src,/queuedDocument = result\.document/);
    assert.match(src,/writeDispatchTimer\.start\(\)/);
    assert.match(src,/id: writeDispatchTimer/);
    assert.match(src,/root\.startWrite\(waiting\)/);
    assert.match(src,/root\.favoritesSaved\(saved\.revision\)/);
    assert.match(src,/root\.favoritesSaveFailed\(root\.errorCode\)/);
    assert.match(read("services/favorites/qmldir"),
        /singleton FavoritesDefaultStore 1\.0 FavoritesDefaultStore\.qml/);
    assert.doesNotMatch(src,/execDetached|Process\s*\{|restart\(|setTimeout|onFileChanged/);
    const dispatch=src.split("function startWrite(next)")[1].split("function requestFeature")[0];
    assert.doesNotMatch(dispatch,/preferencesFile\.setText/);
    const harness=read("scripts/favorites/verify_default_store_fedora_u1.sh");
    assert.match(harness,/phase=\$phase contained failure marker/);
});

test("no existing favorites owners, data or authority are read or rewritten",()=>{
    const own=read("services/favorites/FavoritesDefaultStore.qml");
    const p=read("services/favorites/FavoritesDefaultPolicy.js");
    const ui=read("components/FavoritesToggleButton.qml");
    for(const file of [own,p,ui]) {
        assert.doesNotMatch(file,/appcontrol-favorites\.json|weather-home-favorites-v1\.json|notification-favorites\.json|hospital-reception\.json|time-world-favorites-v1\.json|places-v1\.json|weather-radio-memory\.json/);
        assert.doesNotMatch(file,/ProcessControl|HunterExecutor|clearNotificationsForSource|kill -TERM|systemctl reboot/);
    }
    assert.match(read("services/favorites/FavoritesStore.qml"),
        /appcontrol-favorites\.json/);
    assert.match(read("services/weather/WeatherHomeFavoritesStore.qml"),
        /weather-home-favorites-v1\.json/);
});
