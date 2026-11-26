"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const root = path.resolve(__dirname, "../..");
const host = fs.readFileSync(path.join(root,"widgets/AppControlW.qml"),"utf8");
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
    const seen=Object.create(null);
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
    assert.equal(result.rows.find(x=>x.id==="__proto__").name,"Reserved");
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
