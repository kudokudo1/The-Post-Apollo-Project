#!/usr/bin/env node
"use strict";
// Proxy 1 / M10m: pure legacy -> unified v2 migration oracle.
// stdin is a caller-supplied legacy JSON string; stdout is a synthetic
// candidate. NO file writes, backup creation, Quickshell or remote access.
const fs=require("node:fs");
const vm=require("node:vm");
function load(file) {
    const source=fs.readFileSync(file,"utf8").replace(/^\.pragma library\s*$/m,"");
    const ctx=vm.createContext({JSON,Array,Object,Number,String,RegExp,Math,Date});
    vm.runInContext(source,ctx,{filename:file});
    return ctx;
}
const legacy=load("services/hub/ApolloHubTodoPolicy.js");
const journal=load("services/projects/OfflineOperationJournal.js");
const migrator=load("services/projects/LegacyMigrationDryRun.js");
const model=load("services/projects/UnifiedProjectModelV2.js");
const readBridge=load("services/projects/UnifiedStorageReadBridge.js");

function convert(raw) {
    if(typeof raw!=="string" || raw.length<1 || raw.length>1048576)
        return {ok:false,reason:"INVALID_SOURCE_LENGTH"};
    try {
        JSON.parse(raw);
        // M10d's existing legacy parser permits duplicate JSON object keys.
        // Reject those first instead of allowing JSON.parse to silently
        // discard earlier values (including escaped spelling of a key).
        if(model.hasDuplicateKeys(raw))
            return {ok:false,reason:"DUPLICATE_LEGACY_JSON_KEY"};
    } catch(e) {
        return {ok:false,reason:"INVALID_OR_DEEPLY_NESTED_JSON"};
    }
    const dry=migrator.plan(raw,legacy,journal);
    if(!dry.ok) return {ok:false,reason:"M10D_"+dry.reason};
    const v2=model.upgradeBaselineV1(dry.candidate,journal);
    if(!v2.ok) return {ok:false,reason:"M10H_"+v2.reason};
    const recheck=model.verify(v2.document);
    if(!recheck.ok) return {ok:false,reason:"CANDIDATE_"+recheck.reason};
    const projection=model.legacyReadProjection(v2.document,journal);
    if(!projection.ok)
        return {ok:false,reason:"READ_PROJECTION_"+projection.reason};
    const compat=readBridge.preview(projection.candidate,journal,legacy);
    if(!compat.ok || JSON.stringify(compat.compatibilityDocument)
            !==JSON.stringify(dry.compatibilityV3))
        return {ok:false,reason:"LEGACY_PARITY_FAILED"};
    return {ok:true,sourceVersion:dry.sourceVersion,
        counts:{projects:dry.counts.projects,tasks:dry.counts.tasks},
        candidate:v2.document,compatibilityV3:dry.compatibilityV3,
        writeReady:false,migrationPerformed:false,remoteWriteAuthorized:false};
}
try {
    const input=fs.readFileSync(0,"utf8");
    const result=convert(input);
    process.stdout.write(JSON.stringify(result)+"\n");
} catch(e) {
    process.stdout.write(JSON.stringify({ok:false,reason:"MIGRATION_ORACLE_FAILED"})+"\n");
}
