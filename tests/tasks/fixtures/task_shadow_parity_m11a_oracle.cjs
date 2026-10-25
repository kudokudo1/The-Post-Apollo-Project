#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),vm=require("node:vm");
const input=JSON.parse(fs.readFileSync(0,"utf8"));
function library(path) {
    const s=fs.readFileSync(path,"utf8").replace(/^\.pragma library\s*$/m,"");
    const ctx=vm.createContext({Date,Math,Number,String,Array,Object,RegExp,JSON});
    vm.runInContext(s,ctx,{filename:path});
    return ctx;
}
const parity=library("services/projects/TaskSqliteShadowParityM11a.js");
const policy=library("services/hub/ApolloHubTodoPolicy.js");
const r=parity.compare(input.legacy,input.sqlite,policy);
process.stdout.write(JSON.stringify({
    status:r.status,matched:r.matched,blockers:r.blockers,
    writeReady:r.writeReady,activate:r.activate,
    restore:r.restore,sqliteWriterAuthorized:r.sqliteWriterAuthorized,
    snapshotWritable:r.snapshot===null ? null : r.snapshot.writable,
    total:r.total===undefined ? null : r.total,
    remaining:r.remaining===undefined ? null : r.remaining,
    completed:r.completed===undefined ? null : r.completed
})+"\n");
