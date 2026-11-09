"use strict";
// U7b-J // Read-only exact SYSTEM row / METRIC WATCH navigation.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const Resource={};
vm.runInNewContext(read("services/favorites/FavoritesResourcePolicy.js")
    .replace(/^\.pragma library\s*$/m,""),Resource);
const Watch={Resource};
vm.runInNewContext(read("services/favorites/FavoritesSystemWatchSelectionPolicy.js")
    .replace(/^\.pragma library\s*$/m,"")
    .replace(/^\.import ".+" as \w+\s*$/gm,""),Watch);
const app=read("widgets/AppControlW.qml");
const systemId="system:gpu:CARD0", diskId="system:disk:nvme0n1";
const raw=(id,box)=>Watch.rawFor(id,box);
function row(id,box) {
    const kind=box?"monitor-watch":"item",key=Resource.identityKey("appcontrol",kind,raw(id,box));
    return {owner:"appcontrol",provider:"appcontrol",kind,category:"CPU++",
        menu:"SYSTEM",favoriteType:box?"METRIC WATCH":"FAVORITE",
        readOnly:true,isFavorite:true,resolved:true,key};
}
function live(id) {return {_systemRecord:true,id,name:id.split(":").at(-1)};}
function fixture() {
    const scroll=[],deferred=[],scope={
        menuOpen:false,selectedModeIndex:1,systemModeIndex:8,appsModeIndex:1,
        thermalModeIndex:6,selectedResultIndex:-1,hoveredResultIndex:-1,
        detailFocused:false,pendingFavoriteSelection:null,favoriteNavigationNotice:"",
        savedSystemWatchSourceId:"",savedSystemWatchBoxId:"",
        systemRows:[],systemResults:{values:[]},searchInput:{text:"dummy"},
        SystemWatchSelection:Watch,
        Qt:{callLater(fn){deferred.push(fn);}},
        ListView:{Contain:"Contain"},
        resultList:{positionViewAtIndex(i,where){scroll.push(i+":"+where);}},
        switchMode(mode){scope.selectedModeIndex=mode;},
        resetDetailActionSelection(){}
    };
    const start=app.indexOf("    function clearFavoriteNavigation() {");
    const end=app.indexOf("    function rememberCurrentAppSelection() {",start);
    assert.ok(start>=0 && end>start);
    vm.runInContext(app.slice(start,end),vm.createContext(scope));
    return {scope,scroll,deferred};
}
test("METRIC WATCH resolves chip/device-qualified SYSTEM source and exact saved box",()=>{
    const target=row(systemId,"metric");
    assert.equal(Watch.plan(target).ok,true);
    const token=Watch.plan(target).token;
    assert.match(token,/^w-[0-9a-f]{16}$/);
    assert.equal(Watch.resolveVisible(token,[live(diskId),live(systemId)]).sourceId,systemId);
    const f=fixture(),s=f.scope;
    s.systemRows=[live(diskId),live(systemId)];
    s.systemResults.values=[live(diskId),live(systemId)];
    assert.equal(s.selectSavedSystemWatch(token),true);
    assert.equal(s.menuOpen,true);
    assert.equal(s.selectedModeIndex,s.systemModeIndex);
    assert.equal(s.selectedResultIndex,1);
    assert.equal(s.savedSystemWatchBoxId,"metric");
    assert.equal(s.savedSystemWatchSourceId,systemId);
    assert.equal(s.favoriteNavigationNotice,"");
    while(f.deferred.length)f.deferred.shift()();
    assert.deepEqual(f.scroll,["1:Contain"]);
    assert.equal(Watch.plan(row(systemId,"utilization")).token!==token,true);
});
test("non-core saved SYSTEM component is selectable without device action",()=>{
    const target=row(diskId,"");
    const p=Watch.plan(target),f=fixture(),s=f.scope;
    assert.equal(p.ok,true);
    assert.match(p.token,/^s-[0-9a-f]{16}$/);
    s.systemRows=[live(diskId)];s.systemResults.values=[live(diskId)];
    assert.equal(s.selectSavedSystemWatch(p.token),true);
    assert.equal(s.selectedResultIndex,0);
    assert.equal(s.savedSystemWatchBoxId,"");
    assert.equal(s.savedSystemWatchSourceId,diskId);
});
test("missing or duplicate sources open SYSTEM but never select arbitrary item",()=>{
    const token=Watch.plan(row(systemId,"utilization")).token;
    let f=fixture(),s=f.scope;
    assert.equal(s.selectSavedSystemWatch(token),true);
    assert.equal(s.selectedModeIndex,8);
    assert.equal(s.selectedResultIndex,-1);
    assert.match(s.favoriteNavigationNotice,/SYSTEM IS OPEN/);
    s.systemRows=[live(systemId)];s.systemResults.values=[live(systemId)];
    assert.equal(s.tryResumeFavoriteSelection(),true);
    assert.equal(s.selectedResultIndex,0);
    assert.equal(s.savedSystemWatchBoxId,"utilization");
    assert.equal(s.favoriteNavigationNotice,"");
    f=fixture();s=f.scope;
    s.systemRows=[live(systemId),live(systemId)];
    s.systemResults.values=[live(systemId),live(systemId)];
    assert.equal(s.selectSavedSystemWatch(token),true);
    assert.equal(s.selectedResultIndex,-1);
    assert.match(s.favoriteNavigationNotice,/AMBIGUOUS/);
});
test("malformed resource identities, labels masquerading as IDs and unsafe box types are refused",()=>{
    for(const id of ["","system:","system:../private","system:disk:/dev/sda",
                     "system:net:;reboot","system:gpu:ID with spaces","thermal:chip:SENSOR 13"]) {
        assert.equal(Watch.validSourceId(id),false,id);
    }
    for(const box of ["kill","reboot","set-power","../metric","",null]) {
        if(box==="")continue;
        assert.equal(Watch.plan({...row(systemId,"metric"),
            key:Resource.identityKey("appcontrol","monitor-watch",
                "watchbox|system|"+encodeURIComponent(systemId)+"|"+encodeURIComponent(String(box)))}).ok,false);
    }
    for(const edited of [
        {...row(systemId,"metric"),readOnly:false},
        {...row(systemId,"metric"),resolved:false},
        {...row(systemId,"metric"),category:"APP CTRL"},
        {...row(systemId,"metric"),kind:"task-watch"},
        {...row(systemId,"metric"),favoriteType:"FAVORITE"},
        {...row(systemId,"metric"),menu:"KILL"},
        {...row(systemId,"metric"),isFavorite:false},
        {...row(systemId,"metric"),key:"fav1:local:appcontrol:monitor-watch:run%3Areboot"}
    ])assert.equal(Watch.plan(edited).ok,false,JSON.stringify(edited));
    assert.equal(Watch.validToken("w-0000000000000000;kill"),false);
    assert.equal(Watch.resolveVisible("bad",[live(systemId)]).ok,false);
});
test("CPU++, shell and AppControl transmit only opaque view tokens and visual box focus",()=>{
    const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
    const cpu=read("widgets/CpuPlusW.qml");
    const shell=read("shell.qml");
    const visual=read("widgets/appcontrol/SystemMonitorView.qml");
    assert.match(pane,/SystemWatchSelection\.plan\(pane\.selectedResource\)/);
    assert.match(pane,/pane\.systemWatchSelectionRequested\(pane\.systemWatchSelection\.token\)/);
    assert.match(cpu,/favoriteSystemWatchSelectionRequested\(token\)/);
    assert.match(shell,/SystemWatchSelection\.validToken\(token\)/);
    assert.match(shell,/appControlWindow\.selectSavedSystemWatch\(token\)/);
    assert.match(shell,/requestControlKeyboard\("appcontrol","favorites-system-watch"\)/);
    const start=app.indexOf("    function selectSavedSystemWatch(token) {");
    const end=app.indexOf("    // U7b-G // A saved FAVORITE",start);
    assert.ok(start>=0&&end>start);
    const owner=app.slice(start,end);
    assert.match(owner,/switchMode\(systemModeIndex,false\)/);
    assert.match(owner,/SystemWatchSelection\.resolveVisible\(/);
    assert.match(owner,/savedSystemWatchBoxId=current\.boxId/);
    assert.match(visual,/controller\.savedSystemWatchBoxId === "metric"/);
    assert.match(visual,/controller\.savedSystemWatchBoxId === "utilization"/);
    for(const forbidden of ["execDetached(","writeControl(","launchApplication(",
                           "killProcess(","toggleMonitorBoxFavorite(","setDesiredFanPercent("])
        assert.equal(owner.includes(forbidden),false,forbidden);
});
