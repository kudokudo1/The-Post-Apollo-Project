#!/usr/bin/env node
"use strict";
// M10k Python/JS shape parity oracle. Reads synthetic JSON docs on stdin,
// NEVER writes files or connects to SQLite, Quickshell or GitHub.
const fs=require("node:fs"),vm=require("node:vm");
const src=fs.readFileSync("services/projects/UnifiedProjectModelV2.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const ctx=vm.createContext({JSON,Array,Object,Number,String,RegExp,Math});
vm.runInContext(src,ctx,{filename:"UnifiedProjectModelV2.js"});
const input=fs.readFileSync(0,"utf8");
if(input.length>4*1048576) throw Error("OVERSIZED_PARITY_BATCH");
const examples=JSON.parse(input);
if(!Array.isArray(examples) || examples.length>500) throw Error("INVALID_PARITY_BATCH");
const result=examples.map(x=>ctx.verify(x).ok===true);
process.stdout.write(JSON.stringify(result)+"\n");
