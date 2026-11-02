#!/usr/bin/env node
/* M12n: reducer + QML-source boundary checks. DOES NOT run native Quickshell. */
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname,"../..");
const fix = path.join(root,"tests/tasks/fixtures");
const reducerSource = fs.readFileSync(
    path.join(fix,"TaskNativeTicketLogicM12n.js"),"utf8")
    .replace(/^\.pragma library\s*/, "");
const context = vm.createContext({});
vm.runInContext(reducerSource,context,{timeout:1000});
const {begin,arm,observe} = context;

function start() {
    const ticket = begin(1,0,0,0);
    assert.equal(ticket.state,"QUEUED");
    const armed = arm(ticket,"m12i-native-stage-3");
    assert.equal(armed.state,"RESERVING");
    return armed;
}

function native(extra={}) {
    return Object.assign({
        counter:0,receipts:0,epoch:0,phase:"JSON_ACTIVE",
        fileState:"RESERVING",pendingStage:"m12i-native-stage-3",
        status:"SYNTHETIC_HOST_READY",connected:true
    },extra);
}

test("ticket creation and arm require the exact synthetic native stage shape",()=>{
    assert.equal(begin(1,-1,0,0),null);
    assert.equal(begin(1,0,0,-1),null);
    assert.equal(begin(1,0,0,0).ticketId,"m12n-native-ticket-000001");
    assert.equal(arm(begin(1,0,0,0),"m12n-guess"),null);
    assert.equal(arm(begin(1,0,0,0),"m12i-native-stage-3").state,"RESERVING");
});

test("native file callback alone cannot confirm a ticket",()=>{
    let t=start();
    t=observe(t,native({fileState:"SAVING"}));
    assert.equal(t.state,"WRITING");
    t=observe(t,native({fileState:"VERIFYING"}));
    assert.equal(t.state,"VERIFYING");
    t=observe(t,native({fileState:"SETTLING"}));
    assert.equal(t.state,"SETTLING");
    assert.notEqual(t.state,"CONFIRMED");
});

test("receipt status alone with unchanged counters never confirms",()=>{
    let t=start();
    t=observe(t,native({
        fileState:"READY",pendingStage:"",
        status:"TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED"
    }));
    assert.equal(t.state,"RESERVING");
    assert.notEqual(t.state,"CONFIRMED");
});

test("confirmed only after matching increment and host status plus READY",()=>{
    let t=start();
    t=observe(t,native({fileState:"SAVING"}));
    t=observe(t,native({fileState:"VERIFYING"}));
    // The real M12i QML executes counter++ then settledCount++ and these
    // send separate property-change notifications.
    t=observe(t,native({fileState:"SETTLING",counter:1,receipts:0}));
    assert.equal(t.state,"SETTLING");
    t=observe(t,native({fileState:"SETTLING",counter:1,receipts:1,
        status:"TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED"}));
    assert.equal(t.state,"SETTLING");
    t=observe(t,native({fileState:"READY",pendingStage:"",counter:1,receipts:1,
        status:"TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED"}));
    assert.equal(t.state,"CONFIRMED");
    assert.equal(observe(t,native({phase:"RECOVERY_REVIEW",connected:false})).state,
                 "CONFIRMED");
});

test("wrong stage or changed owner epoch forces review",()=>{
    assert.equal(observe(start(),native({pendingStage:"m12i-native-stage-4"})).reason,
                 "DIFFERENT_STAGE_OBSERVED");
    assert.equal(observe(start(),native({epoch:1})).reason,
                 "UNEXPECTED_OWNER_EPOCH");
});

test("receipt without matching counter and impossible overadvance fail closed",()=>{
    assert.equal(observe(start(),native({counter:0,receipts:1})).state,
                 "REVIEW_REQUIRED");
    assert.equal(observe(start(),native({counter:2,receipts:2})).reason,
                 "UNEXPECTED_COUNTER_OR_RECEIPTS");
    assert.equal(observe(start(),native({counter:-1})).reason,
                 "INVALID_NATIVE_OBSERVATION");
});

test("native host exit, failed load or stop before settlement need review",()=>{
    assert.equal(observe(start(),native({phase:"RECOVERY_REVIEW"})).state,
                 "REVIEW_REQUIRED");
    assert.equal(observe(start(),native({
        fileState:"RECOVERY_REVIEW",connected:false,
        status:"HOST_EXITED_REVIEW_REQUIRED"
    })).reason,"NATIVE_RECOVERY_REVIEW");
    assert.equal(observe(start(),native({status:"STOPPED / FUTURE OWNER MUST REVIEW"}))
                 .state,"REVIEW_REQUIRED");
});

test("missing native owner or unexpected file state never certifies write",()=>{
    assert.equal(observe(start(),native({connected:false})).reason,
                 "NATIVE_OWNER_UNAVAILABLE");
    assert.equal(observe(start(),native({fileState:"UNRECOGNIZED"})).reason,
                 "UNEXPECTED_NATIVE_FILE_STATE");
});

test("session-local terminal state cannot be rewritten by a late signal",()=>{
    const bad=observe(start(),native({phase:"RECOVERY_REVIEW"}));
    const good=observe(bad,native({
        fileState:"READY",counter:1,receipts:1,pendingStage:"",
        status:"TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED"
    }));
    assert.equal(good.state,"REVIEW_REQUIRED");
});

test("M12n reuses exactly one existing M12i native FileView and one process",()=>{
    const harness=fs.readFileSync(path.join(root,"TaskNativeTicketHarnessM12n.qml"),"utf8");
    const adapter=fs.readFileSync(path.join(fix,"TaskNativeTicketAdapterM12n.qml"),"utf8");
    const nativeLab=fs.readFileSync(path.join(fix,"TaskNativeReceiptLabM12i.qml"),"utf8");
    assert.equal((harness.match(/TaskNativeReceiptLabM12i\s*\{/g)||[]).length,1);
    assert.equal((harness.match(/TaskNativeTicketAdapterM12n\s*\{/g)||[]).length,1);
    assert.equal((nativeLab.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((nativeLab.match(/\bProcess\s*\{/g)||[]).length,1);
    assert.equal((adapter.match(/\bFileView\s*\{/g)||[]).length,0);
    assert.equal((adapter.match(/\bProcess\s*\{/g)||[]).length,0);
    assert.equal((harness.match(/\bFileView\s*\{/g)||[]).length,0);
    assert.match(adapter,/nativeLab\.increment\(\)/);
    assert.match(adapter,/TicketLogic\.observe\(/);
    assert.match(adapter,/onSettledCountChanged/);
    assert.match(adapter,/onFileStateChanged/);
    assert.match(adapter,/outOfBandReceipts/);
    assert.match(nativeLab,/TaskNativeReceiptHostM12i\.py/);
    assert.match(nativeLab,/Qt\.callLater/);
    for (const raw of [harness,adapter]) {
        assert.doesNotMatch(raw,/Quickshell\.dataDir/);
        assert.doesNotMatch(raw,/apollo-hub-todo-v1\.json/);
        assert.doesNotMatch(raw,/\bexec\s*\(/);
    }
});

test("M12n never adds a production writer or makes legacy boolean durable",()=>{
    const store=fs.readFileSync(path.join(root,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(root,"shell.qml"),"utf8");
    assert.match(store,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/return stage\(TodoPolicy\./g)||[]).length,9);
    assert.doesNotMatch(shell+store,/TaskNativeTicketHarnessM12n|TaskNativeTicketAdapterM12n/);
    assert.match(store,/return true;/);
});

test("all four live consumer surfaces still use legacy boolean; no premature production adaptation",()=>{
    const expected={
        "widgets/hub/ApolloHubTodoMini.qml":["addTask","renameTask","setTaskDone","removeTask"],
        "widgets/tasks/TaskDetailsPane.qml":["updateTaskDetails"],
        "widgets/tasks/TaskPlannerSchedulePane.qml":["addTask","updateTaskDetails"],
        "widgets/tasks/TaskProjectsPane.qml":["createProject","renameProject","deleteProject","assignTaskProject"]
    };
    for (const [relative, methods] of Object.entries(expected)) {
        const source=fs.readFileSync(path.join(root,relative),"utf8");
        for (const method of methods) {
            assert.match(source,new RegExp("todoStore\\."+method+"\\("),relative);
        }
        assert.doesNotMatch(source,/ticketId|TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED/);
    }
});
