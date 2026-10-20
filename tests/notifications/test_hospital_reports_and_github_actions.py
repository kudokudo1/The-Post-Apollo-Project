#!/usr/bin/env python3
"""Contract tests for passive Hospital report and GitHub action notifications."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HP = ROOT / "services/notifications/HospitalReportArrivalPolicy.js"
HQ = ROOT / "services/notifications/HospitalReportArrivalNotificationProducer.qml"
GP = ROOT / "services/notifications/GitHubActionNotificationPolicy.js"
GQ = ROOT / "services/notifications/GitHubActionNotificationProducer.qml"
HOSPITAL = ROOT / "widgets/HospitalW.qml"
GIT = ROOT / "widgets/GitW.qml"
QM = ROOT / "services/notifications/qmldir"
WF = ROOT / ".github/workflows/notification-policy-contracts.yml"
HOSPITAL_SOURCE = ROOT / "services/hospital/HospitalRoomReportService.qml"
ISSUE_SOURCE = ROOT / "services/github/GitHubIssueLifecycleService.qml"
REVIEW_SOURCE = ROOT / "services/github/GitHubPullRequestReviewThreadLifecycleService.qml"

hq = HQ.read_text()
gq = GQ.read_text()
h = HOSPITAL.read_text()
g = GIT.read_text()
qm = QM.read_text()
assert "HospitalReportArrivalNotificationProducer {" in h
assert "reportService: roomReportService" in h
assert "roomId: root.selectedRoomTeam" in h
assert "repository: roomService.repository" in h
assert "GitHubActionNotificationProducer {" in g
assert "issueLifecycle: githubIssueLifecycleService" in g
assert "reviewLifecycle: githubPullRequestReviewThreadLifecycleService" in g
assert "HospitalReportArrivalNotificationProducer 1.0 HospitalReportArrivalNotificationProducer.qml" in qm
assert "GitHubActionNotificationProducer 1.0 GitHubActionNotificationProducer.qml" in qm
assert "test_hospital_reports_and_github_actions.py" in WF.read_text()
assert "signal reportsRefreshed()" in HOSPITAL_SOURCE.read_text()
assert "signal mutationFinished(" in ISSUE_SOURCE.read_text()
assert "signal mutationFinished(" in REVIEW_SOURCE.read_text()
assert '\"sourceId\": \"hospital\"' in hq
assert '\"sourceId\": \"github\"' in gq
assert "onReportsRefreshed()" in hq
assert gq.count("function onMutationFinished(") == 2
for name, source in [("Hospital", hq), ("Git", gq)]:
    for forbidden in ["Process {", "Timer {", "systemctl", "git push",
                      "gh issue", "gh pr", "readFile", "execDetached",
                      "setAssignmentStatus", "writeReport", "body:",
                      "query(", "poll("]:
        assert forbidden not in source, (name, forbidden)

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
function load(path) {
 const contents=fs.readFileSync(path,'utf8').replace(/^\s*\.pragma library\s*$/m,'');
 const ctx={String,Number,Boolean,Array,Object,isFinite};
 vm.runInNewContext(contents,ctx,{filename:path});
 return ctx;
}
function extract(qml,name) {
 const p=qml.indexOf('function '+name+'(');assert(p>=0,name);
 const open=qml.indexOf('{',p);let depth=0,end=-1;
 for(let i=open;i<qml.length;i++){
  if(qml[i]==='{')depth++;
  else if(qml[i]==='}'&&--depth===0){end=i+1;break;}
 }
 assert(end>open);return qml.slice(p,end);
}
const H=load(process.argv[1]),G=load(process.argv[3]);
const R1=[{id:'a',body:'SENSITIVE REPORT TEXT'}];
let state=H.initial();
function report(room,rows) {
 const next=H.advance(state,room,rows);state=next.state;
 return next.addedCount;
}
assert.strictEqual(report('R-A',R1),0,'baseline is silent');
assert.strictEqual(report('R-A',R1),0,'repeat is silent');
assert.strictEqual(report('R-A',[{id:'a'},{id:'b'}]),1);
assert.strictEqual(report('R-A',[{id:'a'},{id:'b'}]),0);
assert.strictEqual(report('R-B',[{id:'x'}]),0,'switch Room first baseline silent');
assert.strictEqual(report('R-A',[{id:'a'},{id:'b'},{id:'c'}]),1);
assert.strictEqual(report('R-A','not a list'),0);
assert.strictEqual(report('',[{id:'oops'}]),0);
assert.strictEqual(report('R-A',[{noId:'oops'}]),0);

assert.strictEqual(G.issue(true,true,'create',{repository:'a/b',issue:{number:2,url:'u',state:'OPEN'}}).outcome,'VERIFIED');
assert.strictEqual(G.issue(true,true,'close',{repository:'a/b',issue:{number:2,url:'u',state:'OPEN'}}).outcome,'UNVERIFIED',
 'GitHub close state mismatch cannot claim verified');
assert.strictEqual(G.issue(true,true,'close',{repository:'a/b',issue:{number:2,url:'u',state:'CLOSED'}}).outcome,'VERIFIED');
assert.strictEqual(G.issue(false,false,'edit',{repository:'a/b'},'a/b',5).outcome,'FAILED');
assert.strictEqual(G.issue(true,false,'labels',{repository:'a/b'},'a/b',5).outcome,'UNVERIFIED');
assert.strictEqual(G.issue(true,true,'assignees',{repository:'a/b',issue:{number:3,url:'u'}}).outcome,'UNVERIFIED',
 'generic identity readback cannot verify assignment changes');
assert.strictEqual(G.issue(true,true,'delete',{repository:'a/b',issue:{number:2,url:'u'}}),null);
assert.strictEqual(G.issue(true,true,'edit',{repository:'bad name',issue:{number:2,url:'u'}}),null);
assert.strictEqual(G.issue(true,true,'edit',{repository:'a/b',issue:{number:-3,url:'u'}}).outcome,'UNVERIFIED');
assert.strictEqual(G.review(true,true,'resolve',{repository:'a/b',thread:{id:'t',isResolved:true}},'a/b',9).outcome,'VERIFIED');
assert.strictEqual(G.review(true,true,'resolve',{repository:'a/b',thread:{id:'t',isResolved:false}},'a/b',9).outcome,'UNVERIFIED');
assert.strictEqual(G.review(true,true,'unresolve',{repository:'a/b',thread:{id:'t',isResolved:false}},'a/b',9).outcome,'VERIFIED');
assert.strictEqual(G.review(true,true,'reply',{repository:'a/b',thread:{id:'t'},createdReplyNodeId:'r'},'a/b',9).outcome,'VERIFIED');
assert.strictEqual(G.review(true,true,'reply',{repository:'a/b',thread:{id:'t'}},'a/b',9).outcome,'UNVERIFIED');
assert.strictEqual(G.review(false,false,'reply',{},'a/b',9).outcome,'FAILED');
assert.strictEqual(G.review(true,true,'reply',{},'a/b',0),null);
assert.strictEqual(G.review(true,true,'unknown',{},'a/b',9),null);

const history=[];
const notifications={historyReady:true,pushRich:x=>history.push(x)};
const qmlH=fs.readFileSync(process.argv[2],'utf8');
const reportService={roomId:'R-A',reports:[{id:'one',body:'DO NOT STORE'}],lastError:''};
const runH={ReportPolicy:H,NotificationsService:notifications,Date,
 producer:{roomId:'R-A',repository:'company/repo',
           reportService,seenByRoom:H.initial()}};
vm.runInNewContext(extract(qmlH,'receive'),runH);
runH.receive();
assert.strictEqual(history.length,0,'initial Hospital read cannot notify');
reportService.reports=[{id:'one',body:'private'},{id:'two',body:'secret'}];
runH.receive();
assert.strictEqual(history.length,1);
assert(history[0].title.includes('NEW ROOM REPORT'));
assert.strictEqual(history[0].context.reportCount,1);
assert(history[0].sourceId==='hospital');
assert(!JSON.stringify(history).includes('secret'));
runH.receive();
assert.strictEqual(history.length,1,'repeat reports not published twice');
reportService.lastError='PX stdout error with secret token';
reportService.reports.push({id:'three',body:'MORE SECRET'});
runH.receive();
assert.strictEqual(history.length,1,'failed refresh cannot claim new report');
reportService.lastError='';
runH.receive();
assert.strictEqual(history.length,2);
runH.producer.roomId='R-B';reportService.roomId='R-B';
reportService.reports=[{id:'zzz',body:'secret'}];
runH.receive();assert.strictEqual(history.length,2,'Room switch baseline');

const qmlG=fs.readFileSync(process.argv[4],'utf8');
const runG={ActionsPolicy:G,NotificationsService:notifications,Date,
 producer:{issueLifecycle:{pendingRepository:'a/b',pendingEvidenceTarget:'3'},
 reviewLifecycle:{repository:'a/b',pullRequestNumber:9}}};
vm.runInNewContext(['publish','issueFinished','reviewFinished']
 .map(x=>extract(qmlG,x)).join('\n'),runG);
runG.producer.publish=runG.publish;
runG.issueFinished(true,true,'close',{repository:'a/b',issue:{
 number:3,url:'https://github.com/a/b/issues/3',state:'CLOSED',
 body:'SENSITIVE ISSUE BODY'}});
assert.strictEqual(history.length,3);
assert(history[2].title.includes('ISSUE CLOSE VERIFIED'));
assert.strictEqual(history[2].context.issueNumber,3);
runG.issueFinished(true,false,'edit',{repository:'a/b',error:'TOKEN=SECRET'});
assert.strictEqual(history.length,4);
assert(history[3].title.includes('UNVERIFIED'));
runG.reviewFinished(true,true,'resolve',{repository:'a/b',thread:{
 id:'thread',isResolved:true,comments:{nodes:[{body:'HIDDEN REVIEW'}]}}});
assert.strictEqual(history.length,5);
assert(history[4].title.includes('PR REVIEW THREAD RESOLVE VERIFIED'));
assert.strictEqual(history[4].context.pullRequestNumber,9);
runG.reviewFinished(false,false,'reply',{});
assert.strictEqual(history.length,6);
assert(history[5].title.includes('FAILED'));
assert(history.every(x=>!JSON.stringify(x).includes('SENSITIVE')));
assert(history.every(x=>!JSON.stringify(x).includes('TOKEN=SECRET')));
assert(history.every(x=>!JSON.stringify(x).includes('HIDDEN REVIEW')));
console.log('Hospital report arrival and GitHub mutation producer execution: PASS');
"""
subprocess.run(["node", "-e", NODE, str(HP), str(HQ), str(GP), str(GQ)], check=True)
print("Hospital Room reports and GitHub issue/review contracts: PASS")
