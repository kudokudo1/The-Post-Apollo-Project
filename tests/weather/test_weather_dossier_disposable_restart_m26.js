#!/usr/bin/env node
"use strict";

// M26-A: real temporary filesystem bytes + M25 QML JavaScript callbacks.
// The Quickshell FileView engine is mocked, NOT run; native acceptance is separate.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const readSource = rel => fs.readFileSync(path.join(root, rel), "utf8");
const qmlFile = readSource("services/weather/WeatherDossierArchiveStore.qml");
const storagePolicyPath = "services/weather/WeatherDossierArchivePolicy.js";
const codecPath = "widgets/weather/StationDossierSerializationPolicy.js";

function loadLibrary(rel) {
    const sandbox = {Date, Number, String, Math, Object, Array, JSON,
        isFinite, isNaN};
    vm.runInNewContext(
        readSource(rel).replace(/^\.pragma library\s*/m, ""), sandbox
    );
    return sandbox;
}
const archivePolicy = loadLibrary(storagePolicyPath);
const codec = loadLibrary(codecPath);
const capturePolicy = loadLibrary(
    "widgets/weather/StationDossierCapturePolicy.js"
);
const previewPolicy = loadLibrary(
    "widgets/weather/StationDossierPreviewPolicy.js"
);

// Extract and run the *actual* embedded JavaScript method/handler bodies,
// rather than a rewritten simulation of the store's state transitions.
function balancedEnd(code, braceIndex) {
    let depth = 0, quote = "", escaped = false;
    for (let i=braceIndex; i<code.length; i++) {
        const c=code[i];
        if (quote) {
            if (escaped) {escaped=false; continue;}
            if (c === "\\") {escaped=true; continue;}
            if (c === quote) quote="";
        } else if (c === "'" || c === '"' || c === "\`") {
            quote=c;
        } else if (c === "{") {
            depth++;
        } else if (c === "}") {
            depth--;
            if (depth===0) return i+1;
        }
    }
    throw new Error("QML block is not balanced");
}
function method(name) {
    const rx = new RegExp("    function " + name + "\\s*\\([^)]*\\)\\s*\\{");
    const match=rx.exec(qmlFile);
    assert.ok(match, "missing real store method: " + name);
    const start=match.index + 4;
    const open=qmlFile.indexOf("{",match.index);
    return qmlFile.slice(start,balancedEnd(qmlFile,open));
}
function callback(label, args) {
    const rx = new RegExp("\\b" + label + ":\\s*\\{");
    const match=rx.exec(qmlFile);
    assert.ok(match, "missing QML callback: " + label);
    const start=qmlFile.indexOf("{", match.index);
    return "function("+(args||"")+") "+qmlFile.slice(
        start,balancedEnd(qmlFile,start)
    );
}
function namedCallback(label) {
    const rx = new RegExp("\\b" + label + ":\\s*function\\(([^)]*)\\)\\s*\\{");
    const match=rx.exec(qmlFile);
    assert.ok(match, "missing QML function callback: " + label);
    const open=qmlFile.indexOf("{", match.index);
    return "function("+match[1]+") "+qmlFile.slice(
        open,balancedEnd(qmlFile,open)
    );
}

function stagedFor(eventId, now) {
    const selected={
        sourceId:"gdacs",sourceLabel:"GDACS",id:eventId,
        title:"Observed flood "+eventId,typeLabel:"FLOOD",
        latitude:-33.81,longitude:151.24,timeMs:now-7200000
    };
    const preview=previewPolicy.preview(selected,[],{
        available:true,covered:true,usingCache:false,
        frameLabel:"-5M",timeMs:now-300000,receivedAtMs:now-60000
    },null,null,[],[],now-1000);
    assert.equal(preview.ok,true);
    const staged=capturePolicy.stage(preview,now,true);
    assert.equal(staged.ok,true);
    return staged;
}

// All filesystem operations below are constrained to this disposable
// temporary directory. Never resolve against Quickshell.dataDir or HOME.
const temp=fs.mkdtempSync(path.join(os.tmpdir(),"weather-m26-dossier-"));
const filepath=path.join(temp,"weather-dossier-archive-v1.json");
const events=[];
let temporaryFiles=0;
function createRuntime() {
    const archive={
        storageState:"loading",errorCode:"",lastResultCode:"",
        lastSourceId:"",lastEventId:"",lastSequence:0,
        document:archivePolicy.empty(),pendingDocument:null,
        dossierSaved:(source,event,sequence) =>
            events.push({source,event,sequence})
    };
    const file={
        pending:"",
        text:()=>fs.readFileSync(filepath,"utf8"),
        setText(value) {this.pending=value;}
    };
    const env={dossierArchive:archive,archiveFile:file,
        DossierPolicy:archivePolicy,DossierCodec:codec,
        FileViewError:{FileNotFound:"FileNotFound"},
        Date,Number,String,Math,Object,Array,JSON,isFinite,isNaN};
    for(const key of [
        "storageState","errorCode","lastResultCode","lastSourceId",
        "lastEventId","lastSequence","document","pendingDocument"
    ]) {
        Object.defineProperty(env,key,{
            get:()=>archive[key],set:value=>{archive[key]=value;},
            configurable:true
        });
    }
    vm.createContext(env);
    for(const name of ["capture","acceptLoaded","eventCount","latest"]) {
        archive[name]=vm.runInContext("("+method(name)+")",env);
    }
    const load=vm.runInContext(
        "(function(){ dossierArchive.acceptLoaded(archiveFile.text()); })",env
    );
    const loadFailed=vm.runInContext(
        "("+namedCallback("onLoadFailed")+")",env
    );
    const saved=vm.runInContext("("+callback("onSaved")+")",env);
    const saveFailed=vm.runInContext(
        "("+namedCallback("onSaveFailed")+")",env
    );
    function start() {
        if(fs.existsSync(filepath))load();
        else loadFailed("FileNotFound");
    }
    function commit() {
        assert.equal(archive.storageState,"saving");
        assert.ok(file.pending);
        const scratch=filepath+".pending-"+(++temporaryFiles);
        fs.writeFileSync(scratch,file.pending,"utf8");
        fs.renameSync(scratch,filepath);
        file.pending="";
        saved();
    }
    return {archive,file,start,commit,loadFailed,saveFailed};
}
try {
    assert.equal(fs.existsSync(filepath),false);
    const now=Date.UTC(2026,10,2,21,30,0);
    const first=stagedFor("FL:200",now);
    const second=stagedFor("FL:201",now+5000);
    const initial=createRuntime();
    // A new store is not allowed to write before its load decision.
    assert.equal(initial.archive.capture(first,now),false);
    assert.equal(initial.archive.lastResultCode,"ARCHIVE_LOADING");
    assert.equal(fs.existsSync(filepath),false);
    initial.start();
    assert.equal(initial.archive.storageState,"empty");
    assert.equal(fs.existsSync(filepath),false);

    assert.equal(initial.archive.capture(first,now),true);
    assert.equal(initial.archive.storageState,"saving");
    assert.equal(initial.archive.lastResultCode,"SAVING");
    assert.equal(fs.existsSync(filepath),false,
        "capturing only queues FileView text until save");
    assert.equal(initial.archive.capture(second,now+5000),false);
    assert.equal(initial.archive.lastResultCode,"ARCHIVE_BUSY");
    assert.equal(events.length,0);
    initial.commit();
    assert.equal(initial.archive.storageState,"ready");
    assert.equal(initial.archive.lastResultCode,"SAVED");
    assert.equal(events.length,1);
    assert.equal(events[0].event,"FL:200");
    assert.equal(initial.archive.eventCount("gdacs","FL:200"),1);

    const savedBytes=fs.readFileSync(filepath,"utf8");
    assert.equal(archivePolicy.parse(savedBytes,codec).ok,true);
    assert.equal(fs.readdirSync(temp).length,1);
    const rebooted=createRuntime();
    assert.equal(rebooted.archive.document.entries.length,0);
    rebooted.start();
    assert.equal(rebooted.archive.storageState,"ready");
    assert.equal(rebooted.archive.eventCount("gdacs","FL:200"),1);
    assert.equal(rebooted.archive.latest("gdacs","FL:200").sequence,1);
    assert.equal(fs.readFileSync(filepath,"utf8"),savedBytes);
    assert.equal(events.length,1,
        "loading old records must never emit a new save");

    assert.equal(rebooted.archive.capture(second,now+5000),true);
    rebooted.commit();
    assert.equal(rebooted.archive.eventCount("gdacs","FL:201"),1);
    assert.equal(rebooted.archive.eventCount("gdacs","FL:200"),1);
    assert.equal(events.length,2);
    const twoRecords=fs.readFileSync(filepath,"utf8");
    const loadedAfterSecond=createRuntime();
    loadedAfterSecond.start();
    assert.equal(loadedAfterSecond.archive.document.revision,2);
    assert.equal(loadedAfterSecond.archive.document.entries.length,2);

    // On uncertain save failure, never claim success or retry blindly.
    assert.equal(loadedAfterSecond.archive.capture(first,now+10000),true);
    loadedAfterSecond.saveFailed("synthetic IO failure");
    assert.equal(loadedAfterSecond.archive.storageState,"error");
    assert.equal(loadedAfterSecond.archive.lastResultCode,"FILE_SAVE_FAILED");
    assert.equal(loadedAfterSecond.archive.pendingDocument,null);
    assert.equal(loadedAfterSecond.archive.capture(first,now+11000),false);
    assert.equal(fs.readFileSync(filepath,"utf8"),twoRecords);
    assert.equal(events.length,2);

    // Existing malformed file must remain byte-for-byte unchanged.
    for(const bad of [
        "{bad-json","",JSON.stringify({
            schema:archivePolicy.SCHEMA,version:999,revision:0,entries:[]
        })
    ]) {
        fs.writeFileSync(filepath,bad,"utf8");
        const corrupt=createRuntime();
        corrupt.start();
        assert.ok(["error","unsupported"].includes(corrupt.archive.storageState));
        assert.equal(corrupt.archive.capture(first,now+15000),false);
        assert.equal(fs.readFileSync(filepath,"utf8"),bad);
        assert.equal(events.length,2);
    }

    // An unexpected FileView load error must not initialize a fresh archive.
    const unreadable=createRuntime();
    unreadable.loadFailed("PermissionDenied");
    assert.equal(unreadable.archive.storageState,"error");
    assert.equal(unreadable.archive.capture(first,now+20000),false);

    assert.equal(qmlFile.includes("atomicWrites: true"),true);
    assert.equal(qmlFile.includes("watchChanges: false"),true);
    assert.equal((qmlFile.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal(qmlFile.includes(
        'Quickshell.dataDir + "/weather-dossier-archive-v1.json"'),true);
    console.log("Weather M26 disposable filesystem and M25 QML callback: PASS");
} finally {
    fs.rmSync(temp,{recursive:true,force:true});
}
