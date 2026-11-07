"use strict";
/* M15a: no caller can promote read-only local structure into a save receipt. */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
const code=read("widgets/tasks/TaskLocalSourceInspectPolicyM15a.js");
const state=vm.createContext({});
vm.runInContext(code.replace(/^\.pragma library\s*/,""),state,{timeout:1000});
const P=state;
const DENIED=[
    "writerAuthenticated","savedAcknowledged","sourceRevisionVerified",
    "encryptedDraftRecoveryEnabled","writeAuthorized","restoreAuthorized",
    "draftClearAuthorized","keyReleaseAuthorized"
];
function sample(status="SOURCE_STRUCTURALLY_READABLE"){
    const yes=status==="SOURCE_STRUCTURALLY_READABLE";
    const msg={
        protocol:1,kind:"TASKS_LOCAL_SOURCE_CHECK_M15A",status,
        sourcePresent:yes || status==="SOURCE_PERMISSION_REVIEW",
        taskCount:yes?3:null,projectCount:yes?1:null,
        readOnly:true
    };
    for(const flag of DENIED)msg[flag]=false;
    return msg;
}
function noPower(out){
    for(const flag of [
       "writeAuthorized","savedAcknowledged","canReplay","canRestore",
       "canClearDraft","canReleaseKey","sourceRevisionVerified"
    ])assert.equal(out[flag],false,flag);
    assert.equal(out.draftDisposition,"KEEP UNSAVED DRAFT");
    assert.equal(out.lastConfirmedDisplay,"KEEP LAST CONFIRMED VIEW");
    assert.match(out.proof,/NOT AUTHENTICATED/);
    for(const forbidden of [
        "sourcePath","taskTitle","taskId","sourceHash","rawSource",
        "keyringItem","draftText","receipt"
    ])assert.equal(Object.hasOwn(out,forbidden),false,forbidden);
}
test("initial state and in-flight state never claim a save",()=>{
    for(const output of [P.notChecked(),P.checking(),P.stale(),P.unverified()])
        noPower(output);
    assert.match(P.notChecked().title,/NOT CHECKED/);
    assert.match(P.checking().title,/CHECKING/);
    assert.match(P.stale().title,/RECHECK REQUIRED/);
    assert.match(P.unverified().title,/RESULT UNVERIFIED/);
});
test("local structural check yields counts but not durable receipt or recovery",()=>{
    const info=P.view(sample());
    assert.match(info.title,/STRUCTURE READABLE/);
    assert.equal(info.state,"SOURCE_STRUCTURALLY_READABLE");
    assert.match(info.countLabel,/TASKS 3/);
    assert.match(info.countLabel,/PROJECTS 1/);
    assert.match(info.explanation,/not a full policy-parity audit/);
    noPower(info);
});
test("all expected source refusal states have finite authored explanations",()=>{
    for(const status of Object.keys(P.STATUS)){
        const info=P.view(sample(status));
        assert.equal(info.state,status);
        assert.ok(info.explanation.length>50);
        assert.ok(!info.countLabel.includes("TASKS 3"),status);
        noPower(info);
    }
});
test("forged source trust, save ACK or extra raw source fields fail closed",()=>{
    const x=sample();
    const mutated=[
        null,{},[],true,1,
        {...x,status:"SAVE_CONFIRMED"},
        {...x,taskCount:2.5},
        {...x,taskCount:201},
        {...x,projectCount:31},
        {...x,taskCount:"3"},
        {...x,sourcePresent:false},
        {...x,readOnly:false},
        {...x,protocol:2},
        {...x,kind:"ANOTHER_HOST"},
        {...x,taskTitle:"PRIVATE_MEDICAL_NOTE"},
        {...x,sourceHash:"b".repeat(64)},
        {...x,taskId:"t1"},
        {...x,approvedByOperator:true},
        {...x,rawSource:"PRIVATE_SOURCE"},
        {...x,taskCount:null},
        {...x,writerAuthenticated:true},
        {...x,savedAcknowledged:true},
        {...x,sourceRevisionVerified:true},
        {...x,encryptedDraftRecoveryEnabled:true},
        {...x,writeAuthorized:true},
        {...x,restoreAuthorized:true},
        {...x,draftClearAuthorized:true},
        {...x,keyReleaseAuthorized:true},
        {...sample("SOURCE_MISSING"),sourcePresent:true},
        {...sample("SOURCE_PERMISSION_REVIEW"),sourcePresent:false},
    ];
    for(const v of mutated){
        const res=P.view(v);
        assert.equal(res.state,"REFUSED");
        noPower(res);
        assert.ok(!JSON.stringify(res).includes("PRIVATE_"));
    }
});
test("only click launches read-only Python on the canonical singleton source",()=>{
    const qml=read("widgets/tasks/TaskLocalSourceInspectPaneM15a.qml");
    const parent=read("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    const store=read("services/hub/ApolloHubTodoStore.qml");
    assert.match(parent,/TaskLocalSourceInspectPaneM15a\s*\{/);
    assert.equal((parent.match(/TaskLocalSourceInspectPaneM15a\s*\{/g)||[]).length,1);
    assert.match(parent,/sourcePath: ApolloHubTodoStore\.storagePath/);
    assert.match(parent,/saveRequestCount: ApolloHubTodoStore\.nativeSaveRequestsM14a/);
    assert.match(parent,/saveInProgress: ApolloHubTodoStore\.storageState === "saving"/);
    assert.ok(parent.indexOf("LOCAL EDITORS // UNSAVED CONTENT STATUS") <
              parent.indexOf("TaskLocalSourceInspectPaneM15a"));
    assert.ok(parent.indexOf("TaskLocalSourceInspectPaneM15a") <
              parent.indexOf("TaskRecoveryReviewPaneM13z"));
    assert.match(qml,/label: sourceCheck\.busy \? "CHECKING SOURCE\.\.\." : "CHECK LOCAL SOURCE"/);
    assert.match(qml,/onLeftClicked: sourceCheck\.inspect\(\)/);
    assert.match(qml,/inspector\.exec\(\[/);
    assert.match(qml,/Quickshell\.shellPath\("services\/hub\/TaskLocalSourceInspectM15a\.py"\)/);
    assert.match(qml,/--source", sourcePath/);
    assert.match(qml,/onSaveRequestCountChanged/);
    assert.match(qml,/SourcePolicy\.stale\(\)/);
    assert.match(qml,/sourceCheck\.saveInProgress/);
    assert.equal((qml.match(/\bProcess\s*\{/g)||[]).length,1);
    assert.equal((qml.match(/\bFileView\s*\{/g)||[]).length,0);
    assert.doesNotMatch(qml,/Component\.onCompleted|ConnectionsBroker|secret-tool|localStorage/);
    assert.doesNotMatch(qml,/\.setText\(|\.reload\(|\.write\(|Qt\.openUrlExternally/);
    assert.match(store,/readonly property bool encryptedRecoveryEnabled: false/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
});
test("no mutation of shared Connections and no new encryption grants",()=>{
    const broker=read("services/connections/ConnectionsBroker.qml");
    const host=read("services/hub/TaskLocalSourceInspectM15a.py");
    const qml=read("widgets/tasks/TaskLocalSourceInspectPaneM15a.qml");
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
    for(const line of ["os.replace(", "os.rename(", "os.unlink(", "os.chmod(",
                        "os.chown(", "subprocess.Popen","TaskEncryptedDraft"])
        assert.equal(host.includes(line),false,line);
    assert.match(qml,/readonly property bool encryptedRecoveryEnabled: false/);
    assert.match(qml,/readonly property bool trustedSourceOwnerVerified: false/);
    assert.match(qml,/readonly property bool savedUserEditAcknowledged: false/);
    assert.match(qml,/readonly property bool canClearDraft: false/);
    assert.match(qml,/readonly property bool canWriteTaskSource: false/);
});
