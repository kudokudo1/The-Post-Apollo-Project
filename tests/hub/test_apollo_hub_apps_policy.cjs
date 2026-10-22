#!/usr/bin/env node
"use strict";
// Exercise the actual QML JS catalog policy with synthetic desktop entries.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const script = fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubAppsPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(script, p, {filename:"ApolloHubAppsPolicy.js"});

const app = (id,name,extra={}) => ({id,name,icon:"sample-icon",
    genericName:"Utility",...extra});
const samples = [
    app("org.example.Zeta.desktop","Zeta"),
    app("org.example.Alpha.desktop","Alpha"),
    app("org.example.Brave.desktop","Brave Browser",{genericName:"Web Browser"}),
    app("org.example.BraveBeta.desktop","Brave Browser"),
    app("org.example.Hidden.desktop","Hidden App",{noDisplay:true}),
    app("org.example.Alpha.desktop","Duplicate alpha"),
    app("","Nameless ID"),
    app("org.example.NoName.desktop",""),
    app("org.example.Invalid.desktop",123),
    null,
    {id:"bad.desktop",name:"Ignore me",noDisplay:true}
];
let result=p.snapshot(samples,"");
assert.equal(result.state,"ready");
assert.equal(result.source,"desktop-entries");
assert.equal(result.installedCount,4);
assert.equal(result.matchCount,4);
assert.equal(result.shownCount,4);
assert.equal(result.truncated,false);
assert.equal(result.items.length,4);
assert.equal(result.items[0].name,"Alpha");
assert.equal(result.items[1].name,"Brave Browser");
assert.equal(result.items[2].name,"Brave Browser");
assert.equal(result.items[3].name,"Zeta");
assert.equal(result.items[1].id,"org.example.Brave.desktop");
assert.equal(result.items[2].id,"org.example.BraveBeta.desktop");
assert.equal(result.items[1].genericName,"Web Browser");

// Quickshell ObjectModel.values is a QML list: indexed and length-bearing,
// but Array.isArray() is not reliable for Qt-backed sequences. Reproduce its
// JavaScript-facing shape without requiring the Qt runtime in this test.
const qtList = Object.assign({length:samples.length}, samples);
assert.equal(Array.isArray(qtList),false);
assert.equal(p.collectionLength(qtList),samples.length);
const qtResult = p.snapshot(qtList,"");
assert.equal(qtResult.state,"ready");
assert.equal(qtResult.installedCount,result.installedCount);
assert.equal(qtResult.matchCount,result.matchCount);
assert.deepEqual(Array.from(qtResult.items, entry=>entry.id),
                 Array.from(result.items, entry=>entry.id));
assert.equal(p.snapshot(Object.assign({length:0})).state,"empty");
assert.equal(p.snapshot(Object.assign({length:2}, [samples[0],samples[1]]),
                        "Alpha").matchCount,1);
for (const badList of [
    {length:-1}, {length:NaN}, {length:Infinity}, {length:1.5},
    {length:"2"}, {length:50001}, {}, {0:samples[0]},
    "not a list"
]) {
    assert.equal(p.snapshot(badList).state,"unavailable");
}

const matched=p.snapshot(samples,"  WEB  ");
assert.equal(matched.query,"web");
assert.equal(matched.installedCount,4);
assert.equal(matched.matchCount,1);
assert.equal(matched.items[0].name,"Brave Browser");
assert.equal(p.snapshot(samples,"example.brave").matchCount,2);
assert.equal(p.snapshot(samples,"zeta").matchCount,1);
assert.equal(p.snapshot(samples,"not-installed").matchCount,0);
assert.equal(p.snapshot(samples,"not-installed").state,"ready");
assert.equal(p.snapshot([]).state,"empty");
assert.equal(p.snapshot([]).installedCount,0);
assert.equal(p.snapshot(null).state,"unavailable");
assert.equal(p.snapshot({values:samples}).state,"unavailable");
assert.equal(p.snapshot(undefined).shownCount,0);

const huge=Array.from({length:28},(_,i)=>app("app-"+i,
    "Utility "+String(i).padStart(2,"0")));
const limited=p.snapshot(huge);
assert.equal(limited.installedCount,28);
assert.equal(limited.matchCount,28);
assert.equal(limited.shownCount,24);
assert.equal(limited.items.length,24);
assert.equal(limited.truncated,true);
assert.equal(limited.items[0].name,"Utility 00");
assert.equal(limited.items[23].name,"Utility 23");
assert.equal(p.snapshot(huge,"Utility 0").matchCount,10);

const sensitive=p.snapshot([
    app("safe.desktop","Safe App",{
        icon:"\tname\n",genericName:"Long".repeat(100),
        execString:"/home/user/private/launch --password SECRET",
        command:["sh","-c","rm -rf important"],
        workingDirectory:"/home/user/private",
        runInTerminal:true,
        actions:[{execute(){throw Error("must never execute");}}],
        execute(){throw Error("must never launch");}
    })
]);
assert.equal(sensitive.state,"ready");
assert.equal(sensitive.items[0].icon,"name");
assert.equal(sensitive.items[0].genericName.length,120);
const serialized=JSON.stringify(sensitive);
for(const forbidden of ["SECRET","private","rm -rf","command",
                        "workingDirectory","execString","runInTerminal","actions"])
    assert.equal(serialized.includes(forbidden),false,forbidden);
assert.equal(sensitive.items[0].id,"safe.desktop");
assert.equal(p.snapshot([app("a","A")],"<".repeat(100)).query.length,80);
assert.equal(p.snapshot([app("a","A")],null).query,"");
assert.equal(p.snapshot([app("a","A")],{}).query,"");

console.log("ApolloHub B6 native application catalog policy behavior tests passed");
