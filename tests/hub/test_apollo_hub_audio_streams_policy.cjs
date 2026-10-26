#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubAudioStreamsPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const p=vm.createContext({});
vm.runInContext(src,p,{filename:"ApolloHubAudioStreamsPolicy.js"});
function stream(index,props={},muted=false,vol="35%") {
    return {index,mute:muted,
            volume:{"front-left":{value_percent:vol},
                    "front-right":{value_percent:vol}},
            properties:{"application.name":"Audio App",
                        "application.process.id":"5678",
                        "application.id":"org.test.App",
                        "media.name":"Demo playback",
                        ...props},
            environment:"DO NOT PROJECT",argv:["secret"]};
}
const first=stream(21);
const id=p.identity(first);
assert.ok(id.length>10);
assert.equal(p.identity(stream(-1)),"");
assert.equal(p.identity({index:2,properties:{}}),"");
assert.equal(p.findExact([first],21,id).index,21);
assert.equal(p.findExact([first],22,id),null);
assert.equal(p.findExact([first],21,"wrong"),null);
assert.equal(p.findExact([stream(21,{"media.name":"changed"})],21,id),null);
assert.equal(p.findExact([first],21,""),null);
assert.equal(p.findExact([first],21,"x".repeat(769)),null);
let s=p.snapshot([first],1,false,"");
assert.equal(s.state,"ready");
assert.equal(s.generation,1);
assert.equal(s.total,1);
assert.equal(s.shown,1);
assert.equal(s.items[0].index,21);
assert.equal(s.items[0].label,"Audio App");
assert.equal(s.items[0].media,"Demo playback");
assert.equal(s.items[0].volumePercent,35);
assert.equal(s.items[0].muted,false);
for (const forbidden of ["argv","environment","properties","pids","raw","sinkInput"])
    assert.equal(forbidden in s.items[0],false,forbidden);
assert.equal(p.snapshot([first],0,false,"").state,"unavailable");
assert.equal(p.snapshot([],1,false,"").state,"empty");
assert.equal(p.snapshot(null,0,true,"").state,"refreshing");
assert.equal(p.snapshot([first],1,true,"").state,"refreshing");
assert.equal(p.snapshot([first],1,false,"permission denied").state,"error");
assert.equal(p.snapshot([first],1,false,"permission denied").shown,0);
s=p.snapshot([first,first],1,false,"");
assert.equal(s.shown,1);
s=p.snapshot(Array.from({length:19},(_,i)=>stream(i+20)),1,false,"");
assert.equal(s.total,19);
assert.equal(s.shown,16);
assert.equal(s.truncated,true);
s=p.snapshot([stream(32,{"application.name":"Bad\u0000 Name"},
    true,"105%")],2,false,"");
assert.equal(s.items[0].label,"Bad  Name");
assert.equal(s.items[0].volumePercent,105);
assert.equal(s.items[0].muted,true);
assert.equal(p.volume({volume:{foo:{value_percent:"not-a-volume"}}}),-1);
console.log("Hub Team 6 stream evidence projection contracts passed");
