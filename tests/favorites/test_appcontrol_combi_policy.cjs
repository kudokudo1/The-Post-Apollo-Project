"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const root = path.resolve(__dirname, "../..");
const liveHost = fs.readFileSync(path.join(root,"widgets/AppControlW.qml"),"utf8");
const host = fs.readFileSync(path.join(root,"tests/favorites/fixtures/AppControlFavoritesDonorBeforeC4.js.txt"),"utf8");
const source = fs.readFileSync(path.join(root,
    "services/favorites/FavoritesAppControlCombiPolicy.js"),"utf8");
const policy = {};
vm.runInNewContext(source.replace(/^\.pragma library\s*$/m,""),policy);

function body(name) {
    const found = new RegExp("(^|\\n)[ \\t]*function\\s+" + name +
        "\\s*\\(").exec(host);
    assert.ok(found, "host donor function missing: " + name);
    const start = host.indexOf("function",found.index);
    const open = host.indexOf("{",start);
    let depth=0;
    for(let i=open;i<host.length;i++){
        if(host[i]==="{") depth++;
        else if(host[i]==="}"){
            depth--;
            if(depth===0) return host.slice(start,i+1);
        }
    }
    throw new Error("unbalanced donor "+name);
}
const donor = new Function([
    body("favoriteSourceItem"),
    body("combiSearchTextForRecord"),
    body("prepareCombiRecord"),
    "return {favoriteSourceItem,combiSearchTextForRecord,prepareCombiRecord};"
].join("\n"))();

function copy(v) {return JSON.parse(JSON.stringify(v));}
function plain(v) {return copy(v);}

test("source item and search text preserve exact AppControl donor behavior",()=>{
    const inputs=[
        null, {},
        {id:"normal",name:"Named",genericName:"Generic",keywords:"Alpha"},
        {name:"Wrapper",_favoriteRecord:true,_sourceItem:{
            comm:"example",args:"--private argument",commandText:"echo example",
            appName:"X",windowName:"Window",tabTitle:"A",category:"B",
            role:"C",metric:"D",pid:4321
        }},
        {name:"Untyped",_favoriteRecord:true,_sourceItem:null},
        {name:"Odd",pid:0,args:["--foo","--bar"],comment:42}
    ];
    for(const original of inputs){
        const a=copy(original),b=copy(original);
        assert.equal(policy.searchText(a),donor.combiSearchTextForRecord(b));
        assert.deepEqual(plain(policy.sourceItem(a)),
                         plain(donor.favoriteSourceItem(b)));
        const x=policy.prepare(a),y=donor.prepareCombiRecord(b);
        assert.equal(x===null,y===null);
        assert.deepEqual(plain(x),plain(y));
    }
});

test("static catalog preserves donor unique key, sort and signature",()=>{
    const records=[
        {_favoriteKey:"run:one",name:"Zed",_sourceModeIndex:3},
        {_favoriteKey:"run:one",name:"Duplicate",_sourceModeIndex:3},
        {id:"org.app.A",name:"Alpha",_sourceModeIndex:1},
        {id:"metric:1",name:"CPU",_sourceModeIndex:8},
        {id:"mode:6:Fan",name:"Fan",_sourceModeIndex:6},
        null,
        {name:"",_sourceModeIndex:1},
        {name:"By Name",_sourceModeIndex:0},
        {id:"__proto__",name:"Reserved",_sourceModeIndex:0}
    ];
    const prepared=copy(records);
    const result=policy.buildStatic(prepared);
    const expected=[];
    const seen=({});
    for(const row of copy(records)){
        const p=donor.prepareCombiRecord(row);
        if(!p)continue;
        const key=String(p._favoriteKey || p.id || p.name || "");
        if(!key||seen[key])continue;
        seen[key]=true;
        expected.push(p);
    }
    expected.sort((a,b)=>{
        const d=Number(a._sourceModeIndex||0)-Number(b._sourceModeIndex||0);
        return d||String(a.name||"").localeCompare(String(b.name||""));
    });
    const signature=JSON.stringify(expected.map(entry=>[
        Number(entry._sourceModeIndex||-1),
        String(entry.id||entry._favoriteKey||""),
        String(entry.name||"")
    ]));
    assert.deepEqual(plain(result.rows),plain(expected));
    assert.equal(result.signature,signature);
    assert.equal(result.rows.filter(x=>x._favoriteKey==="run:one").length,1);
    assert.equal(result.rows.some(x=>x.id==="__proto__"),false);
});

test("private local COMBI search fields never enter the universal catalog",()=>{
    assert.doesNotMatch(source,/\bQuickshell\b|\bexecDetached\s*\(|\bwriteAdapter\s*\(/);
    assert.doesNotMatch(source,/\bFavoritesStore\b|\bFavoritesDefaultStore\b/);
    const row={name:"Calculator",_favoriteRecord:true,
        _sourceItem:{commandText:"secret --token=not-for-cpu",pid:12}};
    const result=policy.buildStatic([row]);
    assert.equal(result.rows.length,1);
    assert.match(result.rows[0]._combiSearchText,/secret/);
    // Scope check: no global projection import should reference this
    // private search field or local policy.
    for(const p of [
        "services/favorites/FavoritesUnifiedCatalog.qml",
        "services/favorites/FavoritesManagementPolicy.js"
    ]) {
        const universal=fs.readFileSync(path.join(root,p),"utf8");
        assert.doesNotMatch(universal,/_combiSearchText|FavoritesAppControlCombiPolicy/);
    }
});

test("linear pin partition keeps source order, does not execute callbacks",()=>{
    const rows=[
        {id:"a"},{id:"b"},{id:"c",execute:()=>{throw Error("unexpected");}},
        {id:"d"},{id:"e"}
    ];
    const result=policy.partitionPinned(rows,r=>r.id==="b"||r.id==="d");
    assert.deepEqual(plain(result.map(r=>r.id)),["b","d","a","c","e"]);
    assert.equal(rows[0].id,"a");
    assert.equal(rows[2].id,"c");
});


// Test the actual AppControl donor implementation, not merely a hand-written
// copy of the desired result transformation.
function donorTaskCatalog(tasks, identityFor, recordFor) {
    const factory = new Function(
        "taskRows", "taskPersistentIdentity", "favoriteRecordForTaskIdentity",
        "prepareCombiRecord", [
            "let combiTaskCatalog = [];",
            "let combiTaskIdentitySignature = '';",
            "const selectedModeIndex = -1;",
            "const favoritesModeIndex = 0;",
            "const favoritesScopeMode = 0;",
            "const favoritesScopeCombi = 1;",
            body("rebuildCombiTaskCatalog"),
            "rebuildCombiTaskCatalog();",
            "return {rows:combiTaskCatalog,signature:combiTaskIdentitySignature};"
        ].join("\n")
    );
    return factory(tasks,identityFor,recordFor,donor.prepareCombiRecord);
}

test("task COMBI catalog preserves exact donor identities and row structure",()=>{
    const cases=[
        [],
        [{comm:"firefox",name:"Firefox"}],
        [
            {comm:"sshd",name:"SSH"},
            {comm:"firefox",name:"Firefox",pid:1},
            {comm:"sshd",name:"Duplicate",pid:99},
            {comm:"quickshell",name:"Quickshell",pid:4},
            {comm:"__proto__",name:"Reserved prototype"}
        ]
    ];
    const identityFor=task=>task&&task.comm||"";
    const recordFor=(identity,task)=>({
        _favoriteRecord:true,
        _sourceItem:task,
        id:"task|"+encodeURIComponent(identity),
        _favoriteKey:"task|"+encodeURIComponent(identity),
        _sourceModeIndex:7,
        name:task.name,
        label:task.name
    });
    for(const rows of cases){
        const expected=donorTaskCatalog(copy(rows),identityFor,recordFor);
        const actual=policy.buildTasks(copy(rows),identityFor,recordFor);
        assert.deepEqual(plain(actual.rows),plain(expected.rows));
        assert.equal(actual.signature,expected.signature);
        assert.ok(!actual.rows.some(x=>x._favoriteKey==="task|__proto__"));
    }
});

function donorVisibleRows(rows,settings) {
    const start=host.indexOf("const visibleRows = rows.filter(function(entry) {",
        host.indexOf("id: favoriteResults"));
    assert.ok(start>=0,"missing AppControl donor visible-row projection");
    const end=host.indexOf("return visibleRows;",start);
    assert.ok(end>start,"missing donor return");
    const donorBody=host.slice(start,end+"return visibleRows;".length);
    const controller={
        favoritesFilterMode:settings.filterMode,
        favoritesFilterAll:settings.filterAll,
        favoriteEntryMatchesCopiedSubmodes:settings.matchesCopiedSubmode,
        favoriteSourceItem:donor.favoriteSourceItem,
        favoritesModeIndex:0,
        isFavoriteItem:settings.isFavorite
    };
    return new Function("rows","query","inCombi","appControlWindow",donorBody)(
        rows,settings.query,settings.inCombi,controller);
}

test("visible Favorites/COMBI search and filter match donor in all scopes",()=>{
    const rows=[
        {_sourceModeIndex:3,name:"Terminal",args:"--hidden",_combiSearchText:"terminal --hidden",starred:false},
        {_sourceModeIndex:1,name:"Alpha",genericName:"Browser",starred:true},
        {_sourceModeIndex:7,name:"Quickshell",_favoriteRecord:true,
            _sourceItem:{args:"--foo",pid:123,metric:"CPU"},starred:false},
        {_sourceModeIndex:3,name:"Editor",_combiSearchText:"editor notes",starred:true},
        {_sourceModeIndex:1,name:"Hidden",visible:false,starred:true},
        {_sourceModeIndex:8,name:"CPU",metric:"mem",starred:false}
    ];
    const cases=[
        {query:"",inCombi:true,filterMode:-1,filterAll:-1},
        {query:"",inCombi:false,filterMode:-1,filterAll:-1},
        {query:"terminal",inCombi:true,filterMode:-1,filterAll:-1},
        {query:"--foo",inCombi:false,filterMode:-1,filterAll:-1},
        {query:"",inCombi:true,filterMode:3,filterAll:-1},
        {query:"browser",inCombi:false,filterMode:1,filterAll:-1},
        {query:"cpu",inCombi:true,filterMode:7,filterAll:-1}
    ];
    for(const c of cases){
        const options={
            ...c,
            matchesCopiedSubmode:row=>row.visible!==false,
            isFavorite:row=>row.starred===true
        };
        const expected=donorVisibleRows(copy(rows),options);
        const actual=policy.visibleRows(copy(rows),options);
        assert.deepEqual(plain(actual),plain(expected),JSON.stringify(c));
    }
});

test("new local projections do not own actions or enter universal Favorites",()=>{
    const source=fs.readFileSync(path.join(root,
        "services/favorites/FavoritesAppControlCombiPolicy.js"),"utf8");
    assert.doesNotMatch(source,/Quickshell\.Io|Process\s*\{|execDetached\s*\(|kill\s*\(/);
    assert.doesNotMatch(source,/^\\s*(?:import|\\.import)[^\\n]*(?:FavoritesService|FavoritesStore|FavoritesUnifiedCatalog)/m);
    const universal=fs.readFileSync(path.join(root,
        "services/favorites/FavoritesUnifiedCatalog.qml"),"utf8");
    assert.doesNotMatch(universal,/FavoritesAppControlCombiPolicy|_combiSearchText/);
});


test("live host delegates extracted Combi policy without replacing independent baseline",()=>{
    for(const call of ["FavoriteCombi.searchText(record)","FavoriteCombi.prepare(record)","FavoriteCombi.buildStatic(records)","FavoriteCombi.buildTasks(taskRows","FavoriteCombi.visibleRows(rows,"]) assert.ok(liveHost.includes(call),call);
 });

test("C7 local starred and COMBI catalogs preserve original records and lazy task reads",()=>{
    const original=new Function(body("localCatalogBeforeC7")+"\nreturn localCatalogBeforeC7;")();
    function setup(keys,preferred,metrics) {
        const reads={tasks:0,apps:0,windows:0,thermal:0,fan:0,system:0,membership:0,cached:0};
        const apps=[{id:"app:one"},{id:"app:two"},{id:"app:three"},{id:"app:one"}];
        const windows=[{id:"window:one"},{id:"window:two"}];
        const tasks=[{identity:"fox",pid:1},{identity:"fox",pid:2},{identity:"cat",pid:3}];
        const thermal=[{id:"thermal:one"},{id:"thermal:two",watch:true}];
        const fan=[{id:"fan:one",watch:true}];
        const system=[{id:"system:one",watch:true}];
        const cached=[{id:"cached"},{id:"cached"},{id:"__proto__"},{id:"cache2"},null];
        const membership={favoriteKeys:keys,favoriteDetailActionKeys:preferred,favoriteTaskMetricKeys:metrics};
        const record=(key,entry,mode)=>({_favoriteKey:key,_sourceItem:entry,_sourceModeIndex:mode,name:key});
        const owner={appsModeIndex:1,thermalModeIndex:6,systemModeIndex:8,windowsModeIndex:2,
            appEntryKey:e=>e.id,
            isFavoriteItem:e=>keys.includes(e.id),
            favoriteRecordForApp:e=>record(e.id,e,1),
            runFavoriteDataFromKey:k=>k.startsWith("run:")&&k.length>4?{commandText:k.slice(4),prefixMode:0}:null,
            favoriteRecordForRunCommand:(c,p)=>record("run:"+c,{commandText:c,prefixMode:p},3),
            hiddenCommandRecord:c=>({id:"hidden:"+c}),
            monitorEntryHasBoxFavorite:e=>!!e.watch,
            favoriteRecordForModeItem:(e,m)=>record(e.id,e,m),
            taskIdentityFromFavoriteKey:k=>k.startsWith("task|")?k.slice(5):"",
            taskMetricFavoriteData:k=>k.startsWith("taskmetric|")?{identity:k.split("|")[1]}:null,
            taskIdentity:e=>e.identity,
            favoriteRecordForTaskIdentity:(i,e)=>record("task|"+i,e,7)};
        const read=(name,rows)=>()=>{reads[name]++;return rows;};
        const sources={thermalRows:read("thermal",thermal),fanRows:read("fan",fan),
            systemRows:read("system",system),cachedRows:read("cached",cached),
            membership:read("membership",membership),apps:read("apps",apps),
            windows:read("windows",windows),taskRows:read("tasks",tasks)};
        const old={...owner,
            get thermalRows(){return sources.thermalRows();},get fanRows(){return sources.fanRows();},
            get systemRows(){return sources.systemRows();},get taskRows(){return sources.taskRows();},
            get combiStaticCatalog(){return sources.cachedRows();},combiTaskCatalog:[],
            firstFavoriteTaskRows:new Function("taskPersistentIdentity",body("firstFavoriteTaskRows")+"\nreturn firstFavoriteTaskRows;")(owner.taskIdentity)};
        return {reads,owner,sources,old,membership,
            desktop:{applications:{get values(){return sources.apps();}}},
            windows:{get values(){return sources.windows();}}};
    }
    for(const [keys,preferred,metrics] of [
        [[],[],[]],
        [["app:one","run:ls","hidden:cat","thermal:one","window:one"],["app|app%3Atwo|launch","run|run%3Aecho|kitty","app|hidden%3Anvim|launch","app|%ZZ|launch"],[]],
        [["task|fox","task|absent","task|fox"],[],["taskmetric|cat|cpu","taskmetric|fox|mem"]],
        [["task|__proto__"],["unknown|x|foo","app|bad"],["malformed"]]
    ]) for(const inCombi of [true,false]) {
        const a=setup(keys,preferred,metrics),b=setup(keys,preferred,metrics);
        const expected=original(inCombi,a.old,a.membership,a.desktop,a.windows);
        const actual=policy.buildLocalCatalog(inCombi,b.sources,b.owner);
        assert.deepEqual(plain(actual),plain(expected));
        for(const name of ["tasks","apps","windows","thermal","fan","system","cached"])
            assert.equal(b.reads[name],a.reads[name],name);
        assert.equal(b.reads.membership,inCombi?0:1);
    }
    assert.ok(liveHost.includes("FavoriteCombi.buildLocalCatalog(inCombi,"));
    assert.match(liveHost,/taskRows: function\(\) \{ return appControlWindow\.taskRows; \}/);
});
