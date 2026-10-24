#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const source=fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubProcessesPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const p=vm.createContext({});
vm.runInContext(source,p,{filename:"ApolloHubProcessesPolicy.js"});
const row=(pid,name,extra={})=>({pid,comm:name,state:"S",cpu:5,mem:2,
    args:"SECRET ARGS",user:"PRIVATE USER",...extra});
let a=p.snapshot([row(12,"browser"),row(13,"other")],false,"");
assert.equal(a.state,"ready");
assert.equal(a.total,2);
assert.equal(a.shown,2);
assert.equal(a.items[0].pid,12);
assert.equal(a.items[0].name,"browser");
assert.equal(a.items[0].stopped,false);
assert.equal("args" in a.items[0],false);
assert.equal("user" in a.items[0],false);
assert.equal("execute" in a.items[0],false);
a=p.snapshot([row(12,"browser",{state:"T",cpu:145,mem:200})],false,"");
assert.equal(a.items[0].stopped,true);
assert.equal(a.items[0].cpu,100);
assert.equal(a.items[0].memoryPercent,100);
a=p.snapshot([row(1,"init"),row(-1,"bad"),row(9,""),
    row(10,"a\u0000b"),row(10,"duplicate"),row(11,"valid")],false,"");
assert.equal(a.total,2);
assert.equal(a.items[0].name,"a b");
a=p.snapshot(Array.from({length:40},(_,i)=>row(i+2,"app-"+i)),false,"");
assert.equal(a.total,40);
assert.equal(a.shown,24);
assert.equal(a.truncated,true);
a=p.snapshot([row(22,"app")],true,"");
assert.equal(a.state,"refreshing");
assert.equal(a.shown,1);
a=p.snapshot([row(22,"app")],false,"permission denied");
assert.equal(a.state,"error");
assert.equal(a.shown,0);
a=p.snapshot(null,false,"");
assert.equal(a.state,"unavailable");
a=p.snapshot([],true,"");
assert.equal(a.state,"refreshing");
a=p.snapshot([],false,"");
assert.equal(a.state,"empty");
console.log("Hub owner-process projection contracts passed");
