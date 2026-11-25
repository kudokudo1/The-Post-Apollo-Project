import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const P=vm.createContext({});
vm.runInContext(readFileSync(new URL("../../widgets/FinanceBankingBackupControlsPolicy.js",import.meta.url),"utf8"),P);
const row={backupId:"backup-"+"a".repeat(32)+".json",createdUtc:"2026-11-24T12:00:00Z",
    sourceRevision:7,sha256:"b".repeat(64),accountCount:2,entryCount:10,
    connected:false,bankVerified:false,encrypted:false};
const ctx={enabled:true,active:true,busy:false,ready:true,dirty:false,localSaved:true,revision:7};
const create=P.createCandidate(ctx);
assert.equal(JSON.stringify(create),JSON.stringify({action:"create",expectedRevision:7,confirmBackup:true}));
for(const changes of [{enabled:false},{active:false},{busy:true},{ready:false},{dirty:true},
    {localSaved:false},{revision:0},{revision:7.5},{revision:2147483647}])
    assert.equal(P.createCandidate({...ctx,...changes}),null);
const del=P.deleteCandidate(ctx,row);
assert.equal(del.backupId,row.backupId);
assert.equal(del.expectedBackupSha256,row.sha256);
assert.equal(P.deleteCandidate(ctx,{...row,encrypted:true}),null);
assert.equal(P.deleteCandidate(ctx,{...row,backupId:"../manual-session.json"}),null);
assert.equal(P.sameRequest(del,{...del,expectedBackupSha256:"d".repeat(64)}),false);
assert.equal(P.sameRequest(create,{...create,expectedRevision:8}),false);
assert.equal(P.sameRequest(create,del),false);
assert.equal(P.sameRequest(create,{...create}),true);
for(const request of [{action:"restore"},{action:"import"},{action:"create",expectedRevision:7},
    {...create,extra:true},{...del,confirmDelete:false}])
    assert.equal(P.validRequest(request),false);
const base={source:"LOCAL_OPERATOR_BANKING_BACKUP",connected:false,bankVerified:false,encrypted:false};
const frame=(v)=>"FINANCEW_BANKING_BACKUP_RESULT "+JSON.stringify({...base,...v})+"\n";
const list={action:"list"};
assert.equal(P.accept(frame({action:"list",backups:[row]}),0,list).rows.length,1);
assert.equal(P.accept(frame({action:"list",backups:[row,row]}),0,list),null);
assert.equal(P.accept(frame({action:"list",backups:[{...row,entryCount:301}]}),0,list),null);
assert.equal(P.accept(frame({action:"list",backups:[row],session:{}}),0,list),null);
assert.equal(P.accept(frame({action:"create",backup:row}),0,create).backup.backupId,row.backupId);
assert.equal(P.accept(frame({action:"create",backup:{...row,sourceRevision:8}}),0,create),null);
assert.equal(P.accept(frame({action:"create",backup:row}),1,create),null);
assert.equal(P.accept(frame({action:"delete",backupId:row.backupId,deleted:true}),0,del).backupId,row.backupId);
assert.equal(P.accept(frame({action:"delete",backupId:"backup-"+"c".repeat(32)+".json",deleted:true}),0,del),null);
assert.equal(P.accept(frame({action:"list",backups:[row]}),0,create),null);
assert.equal(P.accept(frame({action:"list",backups:[]})+"unexpected\n",0,list),null);

const root=new URL("../../",import.meta.url);
const read=path=>readFileSync(new URL(path,root),"utf8");
const candidate=read("widgets/FinanceBankingBackupControlsCandidate.qml");
const service=read("services/finance/FinanceBankingBackupCandidateService.qml");
for(const expected of ["property bool reviewEnabled: false","onSavedRevisionChanged: discardContext()",
    "onDirtyChanged: discardContext()","onSelectedIdChanged: discardContext()","Policy.sameRequest(armed,request)",
    "CONFIRM CREATE BACKUP","CONFIRM DELETE BACKUP","CANCEL CONFIRMATION","panel.invalidate()",
    "RESULT NOT CONFIRMED // REFRESH BEFORE ANY NEW ACTION"])
    assert.ok(candidate.includes(expected),expected);
for(const expected of ["property bool allowed: false","!Policy.validRequest(request)",
    "pending=JSON.parse(JSON.stringify(request))","banking_manual_archive.py",
    "Policy.accept(service.output,code,service.pending)","discarded=true","retired=true","interval: 35000"])
    assert.ok(service.includes(expected),expected);
assert.ok(!service.includes("Component.onCompleted"));
assert.ok(!service.includes("banking_manual_portable.py"));
assert.ok(!service.includes("banking_manual_recovery.py"));
for(const path of ["widgets/FinanceBankingAccountsPane.qml","widgets/FinanceBankingManualStorageControls.qml",
    "services/finance/FinanceBankingManualStore.qml","widgets/FinanceBankingPane.qml"])
    assert.ok(!read(path).includes("FinanceBankingBackupControlsCandidate"),path);
console.log("M4s1 PASS: guarded backup requests, stale-confirmation cancellation, exact receipts and detached candidate contract");
