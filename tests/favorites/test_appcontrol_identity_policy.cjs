"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname,"../..");
const liveHost = fs.readFileSync(path.join(root,"widgets/AppControlW.qml"),"utf8");
const host = fs.readFileSync(path.join(root,"tests/favorites/fixtures/AppControlFavoritesDonorBeforeC4.js.txt"),"utf8");
const hunter = fs.readFileSync(path.join(root,
    "widgets/appcontrol/HunterOperationController.qml"),"utf8");
const source = fs.readFileSync(path.join(root,
    "services/favorites/FavoritesAppControlIdentityPolicy.js"),"utf8");
const adapter = {};
vm.runInNewContext(source.replace(/^\.pragma library\s*$/m,""),adapter);

function donorFunction(name) {
    const found=new RegExp("(^|\\n)[ \\t]*function\\s+"+name+"\\s*\\(").exec(host);
    assert.ok(found,"missing donor "+name);
    const start=host.indexOf("function",found.index);
    const open=host.indexOf("{",start);
    let depth=0;
    for(let i=open;i<host.length;i++) {
        if(host[i]==="{")depth++;
        else if(host[i]==="}") {
            depth--;
            if(!depth)return host.slice(start,i+1);
        }
    }
    throw Error("unbalanced donor "+name);
}
const donorNames=[
    "favoriteSourceItem","taskPersistentIdentity","taskFavoriteKey",
    "taskIdentityFromFavoriteKey","taskMetricFavoriteKey",
    "taskMetricFavoriteData","monitorBoxFavoriteKey",
    "monitorEntryHasBoxFavorite"
];
function donor(mode, keys) {
    return new Function("mode","keys",[
        "const thermalModeIndex=6,systemModeIndex=8;",
        "const selectedControlModeIndex=()=>mode;",
        "const favoriteStore={favoriteMonitorBoxKeys:keys};",
        ...donorNames.map(donorFunction),
        "return {"+donorNames.join(",")+"};"
    ].join("\n"))(mode,keys);
}
function plain(value) {return value==null?value:JSON.parse(JSON.stringify(value));}

test("process identity matches actual donor, including wrapper and args fallback",()=>{
    const inputs=[
        null,{}, {comm:" Firefox ",name:"Other",args:"/bin/anything"},
        {name:"Chromium",pid:4312},{label:"  Firefox Nightly  "},
        {args:" /opt/bin/FIREFOX --private-window "},
        {_favoriteRecord:true,_sourceItem:{comm:"THUNDERBIRD",pid:54}},
        {_favoriteRecord:true,_sourceItem:null,args:" /bin/OTHER --args"},
        {_favoriteRecord:true,_sourceItem:{name:" SYSTEM "}},
        {args:"/usr/bin/kitty"}, {args:"  /tmp/FILE "},
        {args:"a b"},{comm:"%2F| invalid?"}
    ];
    for(const x of inputs) {
        const d=donor(6,[]);
        assert.equal(adapter.taskIdentity(x),d.taskPersistentIdentity(x));
        assert.equal(adapter.taskKey(x),d.taskFavoriteKey(x));
    }
});

test("task key parsing preserves legacy delimiters and invalid escapes",()=>{
    const values=[
        null,"","task|firefox","task|firefox%20nightly","task|foo%7Cbar",
        "task|","task|%ZZ","task|abc|def","mode:7:fox","taskmetric|firefox|cpu"
    ];
    const d=donor(6,[]);
    for(const value of values)
        assert.equal(adapter.taskIdentityFromKey(value),
            d.taskIdentityFromFavoriteKey(value));
});

test("process metric watch keys and decoding match donor",()=>{
    const entries=[{comm:"FIREFOX"},{args:"/bin/SOME-TOOL --foo"},null,{}];
    const metrics=["cpu"," MeM ","rss","threads","",null,"cpu|peak","%"];
    const d=donor(6,[]);
    for(const entry of entries)for(const metric of metrics)
        assert.equal(adapter.taskMetricKey(entry,metric),
            d.taskMetricFavoriteKey(entry,metric));
    for(const key of [
        "taskmetric|firefox|cpu",
        "taskmetric|firefox|cpu%7Cpeak",
        "taskmetric|firefox|cpu|tail",
        "taskmetric|", "taskmetric|firefox", "taskmetric|%ZZ|cpu",
        "taskmetric|x|%ZZ","task|firefox"
    ])
        assert.deepEqual(plain(adapter.taskMetricData(key)),
            plain(d.taskMetricFavoriteData(key)));
});

test("monitor watch keys match thermal and system donor modes",()=>{
    const modes=[[6,"thermal"],[8,"system"],[2,""]];
    const cases=[
        [{id:"sensor:1"},"temperature"],
        [{id:"CPU 0"},"avg load"],
        [{id:19},"rpm"],[{id:"a|b"},"v|2"],
        [{id:"%"},"cpu"],[null,"watts"],[{},null],
        [{id:"drive:/root"},"temp"],[{id:0},"mem"]
    ];
    for(const [mode,kind] of modes) {
        const d=donor(mode,[]);
        for(const [entry,box] of cases)
            assert.equal(adapter.monitorBoxKey(entry,box,kind),
                d.monitorBoxFavoriteKey(entry,box));
    }
});

test("monitor favorite detection matches donor prefix and scan order",()=>{
    const cases=[
        [{id:"thermal:sensor1"},6,"thermal",["watchbox|thermal|thermal%3Asensor1|temperature"]],
        [{id:"thermal:sensor1"},8,"system",["watchbox|thermal|thermal%3Asensor1|temperature"]],
        [{id:"system:cpu"},8,"system",["watchbox|system|system%3Acpu|frequency"]],
        [{id:"system:cpu"},8,"system",["watchbox|system|system%3Acpu"]],
        [{id:"system:cpu"},8,"system",["other","watchbox|system|system%3Acpu|load"]],
        [{id:0},8,"system",["watchbox|system|0|load"]],
        [null,8,"system",[]]
    ];
    for(const [entry,mode,kind,keys] of cases) {
        const d=donor(mode,keys);
        assert.equal(adapter.hasMonitorBoxFavorite(entry,kind,keys),
            d.monitorEntryHasBoxFavorite(entry,mode));
    }
});

test("HUNTER retains same process favorite key and final recheck",()=>{
    assert.match(hunter,/const identity = String\(target\.identity \|\| ""\)\.trim\(\)\.toLowerCase\(\)/);
    assert.match(hunter,/const key = "task\|" \+ encodeURIComponent\(identity\)/);
    assert.match(hunter,/favoriteStoreObject\.favoriteKeys\.indexOf\(key\) !== -1/);
    assert.match(hunter,/if \(targetIsFavorite\(target\)\)/);
    const d=donor(6,[]);
    for(const entry of [{comm:"FIREFOX"},{comm:"firefox nightly"},{args:"/usr/bin/kitty --foo"}]) {
        const identity=d.taskPersistentIdentity(entry);
        assert.equal(adapter.taskKey(entry),"task|"+encodeURIComponent(identity));
    }
});

test("adapter is pure and never assumes provider execution or storage",()=>{
    assert.doesNotMatch(source,/^\s*\.import\b|\bexecDetached\s*\(|\bwriteAdapter\s*\(|\bProcess\s*\{|target\.pid/mi);
    assert.doesNotMatch(source,/FavoritesStore\.favoriteKeys\s*=|favoritesService\.toggle/i);
    assert.doesNotMatch(source,/\bkill\s*\(|\bspawn\s*\(|\bfilesystem\b.*\bstat\s*\(/i);
});


test("live host delegates extracted Identity policy without replacing independent baseline",()=>{
    for(const call of ["FavoriteIdentity.sourceItem(entry)","FavoriteIdentity.taskIdentity(entry)","FavoriteIdentity.taskKey(entry)","FavoriteIdentity.taskIdentityFromKey(key)","FavoriteIdentity.taskMetricKey(entry, metricId)","FavoriteIdentity.taskMetricData(key)","FavoriteIdentity.monitorBoxKey(entry, boxId, modeName)","FavoriteIdentity.hasMonitorBoxFavorite(entry, modeName,"]) assert.ok(liveHost.includes(call),call);
 });

test("C5 generic favorite keys preserve original mode and provider identity",()=>{
    const modeIds={apps:1,run:3,thermal:6,system:8,kill:7};
    const appKey=e=>e.id||"";
    const command=e=>e.commandText;
    const prefix=e=>e.prefix;
    const runKey=(c,p)=>"run:"+p+":"+encodeURIComponent(c);
    const original=new Function("appEntryKey","runCommandText","runPrefixModeForEntry","runFavoriteKey","taskFavoriteKey",[
        "const appsModeIndex=1,runModeIndex=3,thermalModeIndex=6,systemModeIndex=8,killModeIndex=7;",
        donorFunction("favoriteKeyFor"),"return favoriteKeyFor;"
    ].join("\n"))(appKey,command,prefix,runKey,adapter.taskKey);
    for(const mode of [1,3,6,8,7,2,0]) for(const entry of [
        null,{}, {id:"CPU | 0",name:"Example",commandText:"echo private",prefix:2},
        {_taskRecord:true,comm:"FIREFOX"},{_favoriteRecord:true,_favoriteKey:"preserved"},
        {label:"a:b|c"}, {id:0,name:""}, {_favoriteRecord:true,_favoriteKey:"",name:"fallback"}
    ]) assert.equal(adapter.keyFor(entry,mode,modeIds,appKey,e=>runKey(command(e),prefix(e))),original(entry,mode));
    assert.ok(liveHost.includes("FavoriteIdentity.keyFor(entry, modeIndex,"));
});

test("C6 preferred action identity matches original donor and preserves lazy provider calls",()=>{
    const names=["detailFavoriteContextKey","detailActionStableId","detailFavoriteKeyFor"];
    const entries=[null,{id:"x|y"}, {_hiddenCommand:true,id:"hidden:foo"},
        {_favoriteRecord:true,_sourceItem:{id:"wrapped %",_hiddenCommand:true}},
        {_favoriteRecord:true,_sourceItem:null,id:"fallback"}];
    const actions=[{name:"Open | private"},{_appControlBuiltin:"custom"},{},null,{name:"Open | private"}];
    for(const entry of entries) for(const kind of ["app","run","other"]) {
        let donorReads=0,policyReads=0;
        const isApp=()=>kind==="app",isRun=()=>kind==="run";
        const appKey=e=>e.id||"",runKey=e=>"run:"+encodeURIComponent(e.id||"");
        const old=new Function("selectedResult","selectedResultIsApplication","selectedResultIsRun","favoriteSourceItem","appEntryKey","favoriteKeyFor","appDesktopActions",[
            "const runModeIndex=3;",...names.map(donorFunction),"return {"+names.join(",")+"};"
        ].join("\n"))(()=>entry,isApp,isRun,adapter.sourceItem,appKey,runKey,()=>{donorReads++;return actions;});
        const context=()=>adapter.detailContextKey(entry,isApp,isRun,appKey,runKey);
        const action=(i,provided)=>adapter.detailActionId(entry,i,provided,isRun,isApp,()=>{policyReads++;return actions;});
        assert.equal(context(),old.detailFavoriteContextKey());
        for(const i of [-3,-1,0,1,2,3,4,5,6,7,8,9,10,11,1.5,"1"]) {
            for(const provided of [undefined,[],actions]) {
                assert.equal(action(i,provided),old.detailActionStableId(i,provided));
                assert.equal(policyReads,donorReads,"desktop action discovery must remain lazy");
            }
            assert.equal(adapter.detailKey(context(),action(i)),old.detailFavoriteKeyFor(i));
            assert.equal(policyReads,donorReads);
        }
    }
    assert.ok(liveHost.includes("FavoriteIdentity.detailContextKey(selectedResult(),"));
    assert.ok(liveHost.includes("FavoriteIdentity.detailActionId(selectedResult(),"));
    assert.ok(liveHost.includes("FavoriteIdentity.detailKey(context, actionId)"));
});

test("C10 residual membership and preferred selection match immutable donors",()=>{
    for(const keys of [[],["task|"],["task|fox","system|cpu"],["thermal|"],[null,7,"other"],["task|%ZZ"]])
    for(const metricKeys of [[],["taskmetric|fox|cpu"],["taskmetric|a%7Cb|rss"],["invalid"]])
    for(const monitorKeys of [[],["invalid"]]) {
        const store={favoriteKeys:keys,favoriteTaskMetricKeys:metricKeys,favoriteMonitorBoxKeys:monitorKeys};
        const old=new Function("favoriteStore","taskPersistentIdentity",[
            ...["taskHasMetricFavorite","hasTaskFavorites","hasMonitorFavorites"].map(donorFunction),
            "return {taskHasMetricFavorite,hasTaskFavorites,hasMonitorFavorites};"
        ].join("\n"))(store,adapter.taskIdentity);
        let reads=0;
        const readKeys=()=>{reads++;return keys;};
        assert.equal(adapter.hasTaskFavorites(metricKeys,readKeys),old.hasTaskFavorites());
        assert.equal(reads,metricKeys.length?0:1);
        reads=0;
        assert.equal(adapter.hasMonitorFavorites(monitorKeys,readKeys),old.hasMonitorFavorites());
        assert.equal(reads,monitorKeys.length?0:1);
        for(const entry of [null,{}, {comm:"FOX"}, {comm:"a|b"}, {name:"other"}]){
            let metricReads=0;
            const identity=adapter.taskIdentity(entry);
            assert.equal(adapter.hasTaskMetricFavorite(identity,()=>{metricReads++;return metricKeys;}),
                old.taskHasMetricFavorite(entry));
            assert.equal(metricReads,identity?1:0);
        }
    }
    for(const context of ["","app|x","run|x"])
    for(const keys of [[],["app|other|launch"],["app|x|duplicate"],["run|x|duplicate","app|x|last"],["app|x|missing"]])
    for(const count of [undefined,0,2,4]) {
        const actions=["first","duplicate","duplicate","last"];
        let expectedReads=[],actualReads=[];
        const old=new Function("detailFavoriteContextKey","favoriteStore","detailActionCount","selectedResult","selectedResultIsApplication","appDesktopActions","favoriteSourceItem","detailActionStableId",
            donorFunction("favoriteDetailActionIndex")+"\nreturn favoriteDetailActionIndex;")(
                ()=>context,{favoriteDetailActionKeys:keys},()=>{expectedReads.push("count");return 4;},
                ()=>({}),()=>true,()=>{expectedReads.push("actions");return actions;},e=>e,
                (i,a)=>{expectedReads.push(i);return a[i]||"";});
        const result=adapter.preferredActionIndex(context,keys,count,
            ()=>{actualReads.push("count");return 4;},()=>{actualReads.push("actions");return actions;},
            (i,a)=>{actualReads.push(i);return a[i]||"";});
        assert.equal(result,old(count));
        assert.deepEqual(actualReads,expectedReads);
    }
    for(const name of ["hasTaskMetricFavorite","hasTaskFavorites","hasMonitorFavorites","preferredActionIndex"])
        assert.ok(liveHost.includes("FavoriteIdentity."+name+"("),name);
});
