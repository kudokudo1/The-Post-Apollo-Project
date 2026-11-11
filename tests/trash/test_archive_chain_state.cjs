"use strict";
// Synthetic evaluation of the actual QML read-only audit UI functions.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const qml = fs.readFileSync(
    path.join(__dirname,"../../modules/Trash.qml"),"utf8");

function method(name) {
    const start = qml.indexOf("    function "+name+"(");
    assert.notEqual(start,-1,"missing "+name);
    const open = qml.indexOf("{",start);
    let depth=0;
    for(let i=open;i<qml.length;i++) {
        if(qml[i]==="{")depth++;
        if(qml[i]==="}")depth--;
        if(depth===0)return qml.slice(start,i+1);
    }
    throw new Error("unclosed "+name);
}
const source = ["auditArchiveChain","consumeArchiveChain"].map(method).join("\n");

function make(overrides={}) {
    const calls=[];
    const ctx={
        menuOpen:true,activeMode:"archive",archiveChainBusy:false,
        archiveChainReport:null,archiveChainState:"NOT AUDITED",
        snapshotBusy:false,archiveV2Busy:false,researchBusy:false,busy:false,
        Quickshell:{
            dataDir:"/synthetic/quickshell",
            shellPath(name){return "/trusted/"+name;}
        },
        archiveChainProcess:{exec(args){calls.push(args);}},
        calls,...overrides
    };
    vm.createContext(ctx);
    vm.runInContext(source,ctx);
    return ctx;
}
function complete(ctx,r) {
    ctx.raw=JSON.stringify(r);
    vm.runInContext("consumeArchiveChain(raw)",ctx);
}
const clean={
    ok:true,kind:"archive-v2-chain-audit",readOnly:true,
    state:"CHAIN_CONSISTENT",snapshotCount:8,receiptCount:6,
    legacyCount:2,sourceCount:3,payloadVerified:false,
    authentication:"UNSIGNED_LOCAL",completeness:"DATABASE_LOCAL_ONLY"
};

test("operator-triggered action runs exact read-only audit, not Burn or Restore",()=>{
    const ctx=make();
    assert.equal(vm.runInContext("auditArchiveChain()",ctx),true);
    assert.equal(ctx.archiveChainBusy,true);
    assert.equal(ctx.archiveChainReport,null);
    assert.equal(ctx.archiveChainState,"AUDITING // READ ONLY");
    assert.equal(ctx.calls.length,1);
    assert.equal(ctx.calls[0].join(" "),
        "python3 -I -B /trusted/scripts/trash/archive_v2_chain_audit.py audit /synthetic/quickshell");
    assert.equal(ctx.calls[0].some(x=>/burn|restore|remove|migrate/.test(x)),false);
    assert.equal(vm.runInContext("auditArchiveChain()",ctx),false);
});

test("complete unsigned chain report is visible but never claims payload authenticity",()=>{
    const ctx=make();
    vm.runInContext("auditArchiveChain()",ctx);
    complete(ctx,clean);
    assert.equal(ctx.archiveChainBusy,false);
    assert.equal(ctx.archiveChainState,"LOCAL CHAIN CONSISTENT // UNSIGNED");
    assert.equal(ctx.archiveChainReport.receiptCount,6);
    assert.equal(ctx.archiveChainReport.legacyCount,2);
    assert.equal(ctx.archiveChainReport.payloadVerified,false);
    assert.equal(ctx.archiveChainReport.authentication,"UNSIGNED_LOCAL");
    assert.equal(ctx.calls.length,1);
});

test("rejected or fabricated response cannot mark Archive verified",()=>{
    const ctx=make();
    for (const item of [
        {ok:false,error:"ARCHIVE_CHAIN_LINK_INVALID"},
        {...clean,payloadVerified:true},
        {...clean,authentication:"SIGNED"},
        {...clean,snapshotCount:999},
        {...clean,receiptCount:0},
        {...clean,state:"AUDIT_PARTIAL"},
        {...clean,sourceCount:999},
        {...clean,completeness:"EXTERNAL_AUTHORITY"}
    ]) {
        vm.runInContext("auditArchiveChain()",ctx);
        complete(ctx,item);
        assert.equal(ctx.archiveChainReport,null);
        assert.match(ctx.archiveChainState,/^FAILED/);
    }
});

test("cannot audit outside Archive or while another storage process is busy",()=>{
    for(const patch of [
        {menuOpen:false},{activeMode:"trash"},{snapshotBusy:true},
        {archiveV2Busy:true},{researchBusy:true},{busy:true}
    ]) {
        const ctx=make(patch);
        assert.equal(vm.runInContext("auditArchiveChain()",ctx),false);
        assert.equal(ctx.calls.length,0);
    }
});

test("legacy-only and not-installed states remain explicitly unsigned and limited",()=>{
    const ctx=make();
    vm.runInContext("auditArchiveChain()",ctx);
    complete(ctx,{...clean,state:"LEGACY_ONLY",snapshotCount:1,
        receiptCount:0,legacyCount:1,sourceCount:1});
    assert.equal(ctx.archiveChainState,"LEGACY ONLY // NO RECEIPTS");
    vm.runInContext("auditArchiveChain()",ctx);
    complete(ctx,{...clean,state:"NOT_INSTALLED",snapshotCount:0,
        receiptCount:0,legacyCount:0,sourceCount:0});
    assert.equal(ctx.archiveChainState,"NO ARCHIVE DATABASE");
});

test("visible status and button are embedded in Archive without an extra window",()=>{
    assert.ok(qml.includes('label: trashLauncher.archiveChainBusy'));
    assert.ok(qml.includes('"VERIFY CHAIN"'));
    assert.ok(qml.includes('id: archiveChainProcess'));
    assert.ok(qml.includes('id: archiveChainAuditStatus'));
    assert.ok(qml.includes('" SOURCES // PAYLOAD NOT CHECKED"'));
    assert.ok(qml.includes('archiveChainReport = null;'));
    assert.ok(qml.includes('archiveChainState = "NOT AUDITED";'));
    const start = qml.indexOf("id: archiveChainAuditStatus");
    const end = qml.indexOf("id: archiveSearch",start);
    assert.ok(start > 0 && end > start);
    const statusArea=qml.slice(start,end);
    assert.equal(statusArea.includes("onLeftClicked:"),false);
    assert.equal(statusArea.includes("Process {"),false);
    assert.equal(qml.includes("function restoreArchiveV2"),false);
});
