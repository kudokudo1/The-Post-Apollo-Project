"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = path => fs.readFileSync(require("node:path").join(root,path),"utf8");
const clean = src => src.replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import ".+" as \w+\s*$/gm,"");
const resource = {};
vm.runInNewContext(clean(read("services/favorites/FavoritesResourcePolicy.js")), resource);
const plans = {};
vm.runInNewContext(clean(read("services/favorites/FavoritesClockExactItemPolicy.js")), plans);
const angels = {};
vm.runInNewContext(clean(read("services/time/AngelObservationPolicy.js")), angels);
const key = (p,k,id) => resource.identityKey(p,k,id);
const plain = obj => JSON.parse(JSON.stringify(obj));
function alarmRow(id="31") {
    return {provider:"clock-alarm",owner:"clock-alarm",category:"CLOCK",
        menu:"ALARMS",kind:"alarm",resourceId:id,
        key:key("clock-alarm","alarm",id),readOnly:true,isFavorite:true};
}
function angelRow(id="0022") {
    return {provider:"angel",owner:"angel",category:"NEW",
        kind:"number",resourceId:id,key:key("angel","number",id),
        readOnly:false,isFavorite:true,isPinned:false};
}
function method(source,name) {
    const marker = "function "+name+"(";
    const start = source.indexOf(marker);
    assert(start >= 0, name+" missing");
    const open = source.indexOf("{",start+marker.length);
    assert(open >= 0);
    let depth=0;
    for(let pos=open;pos<source.length;pos++) {
        if(source[pos]==="{") depth++;
        else if(source[pos]==="}") {
            depth--;
            if(depth===0) return source.slice(open+1,pos);
        }
    }
    throw Error("unbalanced method "+name);
}

test("exact item plans accept canonical starred IDs without transferring other metadata",()=>{
    assert.deepEqual(plain(plans.plan(alarmRow())),
        {ok:true,kind:"alarm",id:"31",reason:""});
    assert.deepEqual(plain(plans.plan(angelRow())),
        {ok:true,kind:"angel",id:"0022",reason:""});
    const alarm=plans.plan(alarmRow()),angel=plans.plan(angelRow());
    assert(!JSON.stringify(alarm).includes("fav1:"));
    assert(!JSON.stringify(angel).includes("fav1:"));
});

test("canonical input gating refuses stale, forged and unrelated favorites",()=>{
    const original=alarmRow();
    const a=angelRow();
    const invalid=[
        null,{},[],"alarm",
        {...original,key:"fav1:local:clock-alarm:alarm:0031"},
        {...original,resourceId:"99"},
        {...original,readOnly:false},
        {...original,isFavorite:false},
        {...original,owner:"weather-home"},
        {...original,category:"NEW"},
        {...original,menu:"OTHER"},
        {...original,key:"fav1:local:clock-alarm:alarm:9999999999999999",
            resourceId:"9999999999999999"},
        {...original,key:"fav1:local:clock-alarm:alarm:1%2Fhome",resourceId:"1/home"},
        {...a,key:"fav1:local:angel:number:123456789",resourceId:"123456789"},
        {...a,key:"fav1:local:angel:number:2%F",resourceId:"2%F"},
        {...a,key:"fav1:local:angel:number:444",resourceId:"222"},
        {...a,isFavorite:false,isPinned:true},
        {...a,provider:"appcontrol"},
        {provider:"time",owner:"time",category:"CLOCK",kind:"timezone",
            resourceId:"UTC",key:key("time","timezone","UTC"),
            readOnly:false,isFavorite:true}
    ];
    for(const row of invalid) assert.equal(plans.plan(row).ok,false,
        "rejected "+JSON.stringify(row));
});

function timeHarness() {
    const alarms = new Map([[31,{id:31,favorite:true,name:"Wake"}]]);
    const store={storageState:"ready",pendingDocument:null,queuedDocument:null,
        document:{favorites:[key("angel","number","0022")]}};
    const service={storageState:"ready",pendingDocument:null,queuedDocument:null,
        findAlarm(id){return alarms.get(id)||null;}};
    const selection={selected:0,blocked:false,choose(id){
        if(this.blocked)return false;this.selected=id;return true;}};
    const angel={selected:"",blocked:false,openFavoriteNumber(id){
        if(this.blocked)return false;this.selected=id;return true;}};
    const env={AlarmManagerService:service,FavoritesDefaultStore:store,
        alarmPlaceholderPane:selection,angelPane:angel,
        toolsView:"stopwatch",menuOpen:false,mode:-1,
        chooseMode(i){this.mode=i;}};
    vm.runInNewContext("function openFavoriteClockItem(kind,id) {"+
        method(read("widgets/TimeW.qml"),"openFavoriteClockItem")+"}",env);
    return {env,alarms,store,service,selection,angel};
}

test("real TimeW owner code opens exact saved alarm without ringing or writing",()=>{
    const h=timeHarness();
    assert.equal(h.env.openFavoriteClockItem("alarm","31"),true);
    assert.equal(h.selection.selected,31);
    assert.equal(h.env.toolsView,"alarm");
    assert.equal(h.env.mode,2);
    assert.equal(h.env.menuOpen,true);
    assert.equal(h.service.findAlarm(31).favorite,true);
});

test("real TimeW owner code refuses missing, unstarrred, busy and unsaved-note alarm",()=>{
    for(const scenario of [
        h=>h.alarms.get(31).favorite=false,
        h=>h.service.storageState="saving",
        h=>h.service.pendingDocument={},
        h=>h.service.queuedDocument={},
        h=>h.selection.blocked=true
    ]) {
        const h=timeHarness();scenario(h);
        assert.equal(h.env.openFavoriteClockItem("alarm","31"),false);
        assert.equal(h.env.mode,-1);
        assert.equal(h.env.menuOpen,false);
    }
    const h=timeHarness();
    for(const id of ["31/../../","0031","", "31.0","9999999999999999"]) {
        assert.equal(h.env.openFavoriteClockItem("alarm",id),false);
    }
    assert.equal(h.env.openFavoriteClockItem("alarm","32"),false);
    assert.equal(h.env.mode,-1);
});

test("real TimeW owner code checks confirmed Angel membership and keeps leading zeros",()=>{
    const h=timeHarness();
    assert.equal(h.env.openFavoriteClockItem("angel","0022"),true);
    assert.equal(h.angel.selected,"0022");
    assert.equal(h.env.mode,4);
    assert.equal(h.env.menuOpen,true);
    for(const mutate of [
        q=>q.store.document.favorites=[],
        q=>q.store.storageState="saving",
        q=>q.store.pendingDocument={},
        q=>q.store.queuedDocument={},
        q=>q.angel.blocked=true
    ]) {
        const q=timeHarness();mutate(q);
        assert.equal(q.env.openFavoriteClockItem("angel","0022"),false);
        assert.equal(q.env.mode,-1);
        assert.equal(q.env.menuOpen,false);
    }
    const q=timeHarness();
    assert.equal(q.env.openFavoriteClockItem("angel","222"),false);
    assert.equal(q.env.openFavoriteClockItem("angel","0x22"),false);
    assert.equal(q.env.openFavoriteClockItem("appcontrol","0022"),false);
});

test("real AngelPane code preserves ongoing notes and uncommitted Meaning edits",()=>{
    const store={storageState:"ready",pendingDocument:null,queuedDocument:null,
        document:{favorites:[key("angel","number","0022")]}};
    function harness() {
        const env={AngelPolicy:angels,FavoritesDefaultStore:store,
            editingText:false,editingNoteId:"",noteInFlightId:"",
            reviewingDraft:false,activeView:"journal",meaningSelection:"",
            selectedId:"a1",pendingDeleteId:"a2",angelMeaningPane:{digits:""}};
        vm.runInNewContext("function openFavoriteNumber(digits) {"+
            method(read("widgets/AngelPane.qml"),"openFavoriteNumber")+"}",env);
        return env;
    }
    const h=harness();
    assert.equal(h.openFavoriteNumber("0022"),true);
    assert.equal(h.meaningSelection,"0022");
    assert.equal(h.activeView,"meaning");
    assert.equal(h.selectedId,"");
    assert.equal(h.pendingDeleteId,"");
    for(const mutate of [
        x=>x.editingText=true,
        x=>x.editingNoteId="a1",
        x=>x.noteInFlightId="a1",
        x=>x.reviewingDraft=true,
        x=>{x.activeView="meaning";x.meaningSelection="111";x.angelMeaningPane.digits="222";},
        x=>x.FavoritesDefaultStore.document={favorites:[]}
    ]) {
        const q=harness();mutate(q);
        assert.equal(q.openFavoriteNumber("0022"),false);
        assert.equal(q.activeView,mutate===null?"meaning":q.activeView);
    }
    assert.equal(harness().openFavoriteNumber("22%2F"),false);
    assert.equal(harness().openFavoriteNumber("123456789"),false);
});

test("UI request chain remains separate from generic U7a and timezone controls",()=>{
    const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
    const cpu=read("widgets/CpuPlusW.qml");
    const shell=read("shell.qml");
    const time=read("widgets/TimeW.qml");
    const angel=read("widgets/AngelPane.qml");
    const owner=read("services/favorites/FavoritesOwnerNavigationPolicy.js");
    assert.match(pane,/ClockItem\.plan\(pane\.selectedResource\)/);
    assert.match(pane,/signal clockItemRequested\(string kind, string id\)/);
    assert.match(pane,/pane\.clockItemRequested\(clock\.kind,clock\.id\)/);
    assert.match(pane,/pane\.clockItemRequested\(item\.kind,item\.id\)/);
    assert.match(pane,/pane\.defaultOwner\.togglePinned\(pane\.selectedResource\.key\)/);
    assert.match(pane,/pane\.defaultOwner\.setFavorite\(item\.key,false\)/);
    assert.match(cpu,/signal favoriteClockItemRequested\(string kind,string id\)/);
    assert.match(cpu,/cpuPlusWindow\.favoriteClockItemRequested\(kind,id\)/);
    assert.match(shell,/function openApolloFavoriteClockItem\(kind,id\)/);
    assert.match(shell,/if\(shellRoot\.openApolloFavoriteClockItem\(kind,id\)\)\s*cpuPlusWindow\.close\(\)/);
    assert.match(time,/function openFavoriteClockItem\(kind, id\)/);
    assert.match(angel,/function openFavoriteNumber\(digits\)/);
    // Existing U7a generic owner opening still forwards ONLY fixed views.
    assert.doesNotMatch(owner,/\.resourceId|\.command|\.streamUrl|\.url/);
    assert.match(time,/model: TimeSettings\.worldFavoriteZones/);
    assert.match(time,/TimeSettings\.toggleWorldFavorite\(/);
    const newOwnerBody=method(time,"openFavoriteClockItem");
    for(const banned of ["saveAlarm(", "toggleFavorite(", "execDetached(",
        "Process {","FileView {","pushRich(", "snoozeAlarm(", "stopAlarm("])
        assert(!newOwnerBody.includes(banned));
});
