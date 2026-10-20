#!/usr/bin/env python3
"""Hospital notifications only from recorded certification transitions."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"services/notifications/HospitalCertificationNotificationPolicy.js"
VIEW=ROOT/"widgets/HospitalW.qml"
COORD=ROOT/"services/hospital/HospitalCertificationCoordinator.qml"
CERT=ROOT/"services/hospital/HospitalCertificationService.qml"
SERVICE=ROOT/"services/notifications/NotificationsService.qml"

view=VIEW.read_text()
coord=COORD.read_text()
cert=CERT.read_text()
assert 'import "../services/notifications/HospitalCertificationNotificationPolicy.js" as CertificationNotificationPolicy' in view
assert "target: certificationCoordinator" in view
assert "function onCertificationChanged(previousState, nextState, eventType)" in view
assert "CertificationNotificationPolicy.classify(" in view
assert "root.publishRoomOutcome(" in view
assert 'target: roomService' in view
assert '"integration-refused"' in view
assert '"post-op-clean"' in view
assert "function publishRoomOutcome(title, description, severity, eventType)" in view
assert "if (!room || !patient)" in view
assert "NotificationsService.pushRich({" in view
assert '"sourceId": "hospital"' in view
assert "function pushRich(notification)" in SERVICE.read_text()
assert "certification.certificationChanged(" not in view
assert "certificationChanged(previousState, state, eventType);" in cert
assert 'recordTransition(' in cert
for kind in ['"CANDIDATE_VERIFIED"', '"CERTIFICATION_GRANTED"',
             '"CERTIFICATION_BLOCKED"', '"CERTIFICATION_REOPENED"']:
    assert kind in cert
for banned in ["Quickshell.execDetached", "operationJournal", "packet", "rawReason",
               "certificationBlocked(reason)", "reason ||", "stderr"]:
    assert banned not in view[view.index("    // Certification events are emitted"):view.index("    Connections {\n        target: roomService\n\n        function onIntegrationFailed")], banned

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const policy={String};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8')
  .replace(/^\s*\.pragma library\s*$/m,''),policy);
const classify=policy.classify;
assert.strictEqual(classify('IDLE','CANDIDATE','CANDIDATE_CREATED'),null);
assert.strictEqual(classify('VERIFIED','ARMED','CERTIFICATION_ARMED'),null);
assert.strictEqual(classify('INTEGRATING','POST_OP','POST_OP_STARTED'),null);
assert.strictEqual(classify('POST_OP','IN_MAIN','POST_OP_VERIFIED'),null,
  'existing post-op notification owns integration outcomes');
assert.strictEqual(classify('VERIFIED','VERIFIED','CANDIDATE_VERIFIED'),null);
assert.strictEqual(classify('BLOCKED','BLOCKED','CERTIFICATION_BLOCKED'),null);
assert.strictEqual(classify('CANDIDATE','VERIFIED','CERTIFICATION_GRANTED'),null);
assert.strictEqual(classify('CANDIDATE','CERTIFIED','CERTIFICATION_GRANTED'),null);
assert.strictEqual(classify('CANDIDATE','BLOCKED','unexpected'),null);
assert.strictEqual(classify('CANDIDATE','VERIFIED','CANDIDATE_VERIFIED').kind,'candidate-verified');
assert.strictEqual(classify('VERIFIED','CERTIFIED','CERTIFICATION_GRANTED').kind,'certification-granted');
assert.strictEqual(classify('VERIFIED','BLOCKED','CERTIFICATION_BLOCKED').severity,'warning');
assert.strictEqual(classify('BLOCKED','REOPENED','CERTIFICATION_REOPENED').kind,'certification-reopened');
assert(!JSON.stringify(classify('VERIFIED','BLOCKED','CERTIFICATION_BLOCKED')).includes('stderr'));

const view=fs.readFileSync(process.argv[2],'utf8');
const at=view.indexOf('function onCertificationChanged(previousState, nextState, eventType)');
assert(at>=0);
const open=view.indexOf('{',at);
let depth=0,end=-1;
for(let i=open;i<view.length;i++){
 if(view[i]==='{')depth++;
 else if(view[i]==='}' && --depth===0){end=i+1;break;}
}
assert(end>open);
const events=[];
const runtime={
 CertificationNotificationPolicy:policy,
 root:{publishRoomOutcome:(...args)=>events.push(args)}
};
vm.runInNewContext('('+view.slice(at,end)+')',runtime)('CANDIDATE','VERIFIED','CANDIDATE_VERIFIED');
assert.strictEqual(events.length,1);
assert.strictEqual(events[0][0],'ROOM EVIDENCE VERIFIED');
assert.strictEqual(events[0][3],'candidate-verified');
assert.strictEqual(events[0][2],'normal');
vm.runInNewContext('('+view.slice(at,end)+')',runtime)('VERIFIED','BLOCKED','CERTIFICATION_BLOCKED');
assert.strictEqual(events.length,2);
assert.strictEqual(events[1][2],'warning');
vm.runInNewContext('('+view.slice(at,end)+')',runtime)('POST_OP','IN_MAIN','POST_OP_VERIFIED');
assert.strictEqual(events.length,2);
console.log('Hospital certification recorded-event producer: PASS');
"""
subprocess.run(["node","-e",NODE,str(POLICY),str(VIEW)],check=True)
print("Hospital certification lifecycle notification contracts: PASS")
