#!/usr/bin/env python3
"""Read-only Git journal completion/failure notification integration."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"services/notifications/LocalGitJournalNotificationPolicy.js"
PRODUCER=ROOT/"services/notifications/LocalGitJournalNotificationProducer.qml"
VIEW=ROOT/"widgets/GitW.qml"
JOURNAL=ROOT/"services/git/GitOperationJournalService.qml"
QM=ROOT/"services/notifications/qmldir"
SERVICE=ROOT/"services/notifications/NotificationsService.qml"

src=PRODUCER.read_text()
view=VIEW.read_text()
journal=JOURNAL.read_text()
assert "LocalGitJournalNotificationProducer {" in view
assert "operationJournal: operationJournalService" in view
assert "LocalGitJournalNotificationProducer 1.0 LocalGitJournalNotificationProducer.qml" in QM.read_text()
assert "signal operationFinished(string operationId, bool success, var record)" in journal
assert "operationFinished(operationId, true, cloneValue(record));" in journal
assert "operationFinished(operationId, false, cloneValue(record));" in journal
assert "function onOperationFinished(operationId, success, record)" in src
assert "producer.receive(operationId, success, record)" in src
assert '"sourceId": "git-local-journal"' in src
assert '"origin": "apollo"' in src and '"domain": "git"' in src
assert '"verification": "journal outcome only"' in src
assert "function pushRich(notification)" in SERVICE.read_text()
for forbidden in ["Process {", "Timer {", "Quickshell.execDetached",
                  "operationJournal.completeOperation(", "operationJournal.failOperation(",
                  "gitService.refresh(", "recoveryService.execute(", "terminal", "record.detail",
                  "record.before", "record.after", "record.metadata"]:
    assert forbidden not in src, forbidden

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const policy={String};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8')
  .replace(/^\s*\.pragma library\s*$/m,''),policy);
const rec=(status='COMPLETE',overrides={})=>({
  id:'op-abc',status,kind:'CONTROL/PULL',
  repository:'/home/tester/private/Projects/sample-repo',
  detail:'SECRET TOKEN 123',metadata:{password:'NO'},
  before:{branch:'very_private'},after:{branch:'super_secret'},
  ...overrides
});
const payload=policy.payload;
assert.strictEqual(payload('',true,rec()),null);
assert.strictEqual(payload('op-mismatch',true,rec()),null);
assert.strictEqual(payload('op-abc',true,rec('RUNNING')),null);
assert.strictEqual(payload('op-abc',true,rec('FAILED')),null);
assert.strictEqual(payload('op-abc',false,rec('COMPLETE')),null);
assert.strictEqual(payload('op-abc',false,rec('FAILED')).status,'FAILED');
assert.strictEqual(payload('op-abc',true,rec()).repository,'sample-repo');
const info=payload('op-abc',true,rec());
assert(info.message.includes('journal recorded'));
assert(!JSON.stringify(info).includes('/home/tester'));
assert(!JSON.stringify(info).includes('SECRET'));
assert(!JSON.stringify(info).includes('password'));
assert(!JSON.stringify(info).includes('private'));
assert.strictEqual(payload('op-abc',true,rec('COMPLETE',{repository:''})),null);
assert.strictEqual(payload('op-abc',true,rec('COMPLETE',{kind:''})),null);

const qml=fs.readFileSync(process.argv[2],'utf8');
const at=qml.indexOf('function receive(');
assert(at>0);
const open=qml.indexOf('{',at);let depth=0,end=-1;
for(let i=open;i<qml.length;i++){
 if(qml[i]==='{')depth++;
 else if(qml[i]==='}' && --depth===0){end=i+1;break;}
}
assert(end>open);
const emitted=[];
const runtime={
 String,JournalPolicy:policy,
 NotificationsService:{
  notifications:{get count(){return emitted.length;},get:i=>emitted[i]},
  pushRich:notification=>emitted.push(notification)
 }
};
vm.runInNewContext(qml.slice(at,end),runtime);
runtime.receive('op-abc',true,rec());
runtime.receive('op-abc',true,rec());
assert.strictEqual(emitted.length,1,'one journal event per ID');
assert.strictEqual(emitted[0].severity,'normal');
assert.strictEqual(emitted[0].context.verification,'journal outcome only');
assert.strictEqual(emitted[0].context.origin,'apollo');
assert.strictEqual(emitted[0].context.domain,'git');
assert.strictEqual(emitted[0].context.repositoryName,'sample-repo');
runtime.receive('op-def',false,rec('FAILED',{id:'op-def',kind:'CONTROL/PUSH'}));
assert.strictEqual(emitted.length,2);
assert.strictEqual(emitted[1].severity,'warning');
assert(emitted[1].title.includes('FAILED'));
assert(!JSON.stringify(emitted).includes('SECRET TOKEN'));
assert(!JSON.stringify(emitted).includes('/home/tester'));
console.log('Git journal completion/failure real QML producer: PASS');
"""
subprocess.run(["node","-e",NODE,str(POLICY),str(PRODUCER)],check=True)
print("Local Git journal notification contracts: PASS")
