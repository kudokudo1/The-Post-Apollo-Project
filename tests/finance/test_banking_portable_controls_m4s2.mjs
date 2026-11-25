import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const root=new URL("../../",import.meta.url);
const read=p=>readFileSync(new URL(p,root),"utf8");
const P=vm.createContext({});
vm.runInContext(read("widgets/FinanceBankingPortableControlsPolicy.js"),P);
const id="banking-"+"a".repeat(32)+".sealed.json";
const pw="fictional-test-password";
const ctx={enabled:true,active:true,busy:false,ready:true,dirty:false,localSaved:true,revision:7};
const exp=P.candidate(ctx,"export","");
const prev=P.candidate(ctx,"preview",id);
assert.equal(exp.expectedRevision,7);
assert.equal(prev.portableId,id);
for(const change of [{enabled:false},{active:false},{busy:true},{ready:false},{dirty:true},{localSaved:false},{revision:0},{revision:2147483646}])
    assert.equal(P.candidate({...ctx,...change},"export",""),null);
for(const change of [{enabled:false},{active:false},{busy:true}])
    assert.equal(P.candidate({...ctx,...change},"preview",id),null);
for(const bad of ["../"+id,id+"\n",id+"x",id.toUpperCase(),""])
    assert.equal(P.candidate(ctx,"preview",bad),null);
for(const bad of ["short","x".repeat(1025),"x".repeat(12)+"\n","\ud800"+"x".repeat(12),"😀".repeat(11),"😀".repeat(257)])
    assert.equal(P.frame(exp,bad),null);
assert.ok(P.frame(exp,"😀".repeat(12)));
assert.ok(P.frame(exp,"😀".repeat(256)));
assert.equal(P.sameIntent(exp,{...exp,expectedRevision:8}),false);
assert.equal(P.sameIntent(prev,{...prev,portableId:id.replace(/a{32}/,"b".repeat(32))}),false);
assert.equal(P.sameIntent(exp,exp),true);
assert.equal(P.sameIntent(exp,prev),false);
assert.equal(P.frame({action:"import"},pw),null);
assert.equal(P.frame({action:"prepare",confirmPrepare:true},pw),null);
assert.equal(P.frame({...exp,password:pw},pw),null);
assert.equal(P.frame({...exp,confirmExport:false},pw),null);
assert.equal(JSON.parse(P.frame(exp,pw)).password,pw);
assert.ok(!JSON.stringify(exp).includes(pw));
const base={source:"LOCAL_OPERATOR_BANKING_PORTABLE",connected:false,bankVerified:false,
    portableId:id,sha256:"b".repeat(64),sourceRevision:7};
const exported={...base,action:"export",encrypted:true};
const preview={...base,action:"preview",accountCount:2,entryCount:300,
    ciphertextAuthenticated:true,originAuthenticated:false};
const frame=v=>"FINANCEW_BANKING_PORTABLE_RESULT "+JSON.stringify(v)+"\n";
assert.equal(P.accept(frame(exported),0,exp).portableId,id);
assert.equal(P.accept(frame(preview),0,prev).entryCount,300);
for(const change of [{sourceRevision:8},{encrypted:false},{connected:true},{bankVerified:true},
    {sha256:"z".repeat(64)},{password:pw},{session:{}}])
    assert.equal(P.accept(frame({...exported,...change}),0,exp),null);
for(const change of [{accountCount:0},{entryCount:301},{originAuthenticated:true},{ciphertextAuthenticated:false},
    {portableId:id.replace(/a{32}/,"b".repeat(32))},{sourceRevision:0},{session:{}}])
    assert.equal(P.accept(frame({...preview,...change}),0,prev),null);
assert.equal(P.accept(frame(exported),1,exp),null);
assert.equal(P.accept(frame(exported)+"extra\n",0,exp),null);
assert.equal(P.accept(frame(preview),0,exp),null);
const panel=read("widgets/FinanceBankingPortableControlsCandidate.qml");
const service=read("services/finance/FinanceBankingPortableCandidateService.qml");
for(const token of ["property bool reviewEnabled: false","TextInput.Password","Qt.ImhSensitiveData",
    "Policy.sameIntent(armed,intent)","secret.text=\"\"","onSavedRevisionChanged: clearSensitive()",
    "onAvailableChanged: clearSensitive()","maximumLength: 53","maximumLength: 1025"])
    assert.ok(panel.includes(token),token);
for(const token of ["property bool allowed: false","Policy.frame(intent,password)",
    "pending=JSON.parse(JSON.stringify(intent))","banking_manual_portable.py",
    "worker.write(service.discarded ?","service.frame=\"\"","Policy.accept(service.output,code,service.pending)","discarded=true","retired=true","interval: 35000"])
    assert.ok(service.includes(token),token);
assert.ok(!service.includes("Component.onCompleted"));
assert.ok(!service.includes("banking_manual_archive.py"));
for(const path of ["widgets/FinanceW.qml","widgets/FinanceBankingPane.qml","widgets/FinanceBankingAccountsPane.qml",
    "widgets/FinanceBankingManualStorageControls.qml","widgets/FinanceBankingBackupControlsCandidate.qml"])
    assert.ok(!read(path).includes("FinanceBankingPortableControlsCandidate"),path);
console.log("M4s2 PASS: export/preview intent, passphrase limits, metadata receipt binding, no live mount");
