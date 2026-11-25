// Execute the actual QML custody functions in a deterministic event queue.
// Publication is a spy; native Process behavior still requires native tests.
const fs=require("node:fs"), vm=require("node:vm"), assert=require("node:assert/strict");
const source=fs.readFileSync("services/git/GitService.qml","utf8");
function between(a,b) {
 const start=source.indexOf(a), end=source.indexOf(b,start+1);
 assert.ok(start>=0 && end>start,a);
 return source.slice(start,end);
}
const custody=between("    function refreshContextChanged()", "    property string refreshRepoPath:");
const parser=between("    function consumeRefreshLine(line)", "    function publishCompletedRefresh()");
function fixture() {
 const callbacks=[];
 const c=vm.createContext({refreshing:true,refreshFinalizing:false,refreshDoneSeen:false,
   refreshDuplicateDone:false,refreshExitSeen:false,refreshExitCode:-1,refreshExitStatus:-1,
   refreshRepoEpoch:1,repoSelectionEpoch:1,refreshRepoPath:"repo-a",repoPath:"repo-a",
   refreshPending:false,refreshProcess:{running:true},available:true,lastError:"",
   refreshDiagOutcome:"READING",refreshDiagTimedOut:false,refreshDiagStarted:Date.now()-7000,
   refreshDiagDoneMs:-1,refreshDiagLateDone:0,refreshDiagOverlap:false,
   refreshDiagLastFailure:null,refreshDiagMarks:[],refreshDiagAttempt:1,
   topologyRevision:8,syncAfterRefreshStartedMs:10,published:0,followups:0,failed:[],
   Qt:{callLater:f=>callbacks.push(f)},refreshWatchdog:{stop(){}},
   rememberRefreshFailure(code){c.failed.push(code);c.refreshDiagOutcome=code;},
   publishCompletedRefresh(){c.published++;c.refreshing=false;c.available=true;c.refreshDiagOutcome="PUBLISHED";},
   refresh(){c.followups++;}
 });
 vm.runInContext(custody+"\n"+parser,c);
 const flush=()=>{let n=0;while(callbacks.length){assert.ok(++n<20);callbacks.shift()();}};
 const done=()=>c.consumeRefreshLine("DONE\t");
 const exit=(code=0,status=0)=>{c.refreshProcess.running=false;c.noteRefreshExit(code,status);flush();};
 return {c,flush,done,exit};
}
{
 const {c,done,exit}=fixture();
 c.refreshSoftDeadline();
 assert.equal(c.refreshing,true);assert.equal(c.available,true);assert.equal(c.lastError,"");
 assert.equal(c.refreshDiagOutcome,"READING // SLOW");assert.equal(c.failed.length,0);
 done();assert.equal(c.published,0);assert.equal(c.refreshing,true);
 exit();assert.equal(c.published,1);assert.equal(c.refreshDiagLateDone,1);
 assert.equal(c.refreshing,false);assert.equal(c.failed.length,0);
}
{
 const {c,done,flush}=fixture();
 c.noteRefreshExit(0,0); // exit callback precedes runningChanged
 done();flush();assert.equal(c.published,0);
 c.refreshProcess.running=false;c.refreshRunningChanged();flush();
 assert.equal(c.published,1);
}
for(const [label,prepare,code,status,expected] of [
 ["missing DONE",f=>{},0,0,"INVALID COMPLETION MARKER"],
 ["duplicate DONE",f=>{f.done();f.done()},0,0,"INVALID COMPLETION MARKER"],
 ["data after DONE",f=>{f.done();f.c.consumeRefreshLine("HEAD\tx")},0,0,"INVALID COMPLETION MARKER"],
 ["nonzero despite DONE",f=>f.done(),1,0,"CHILD NONZERO EXIT"],
 ["crash despite DONE",f=>f.done(),0,1,"CHILD NONZERO EXIT"],
 ["timeout",f=>{},124,0,"GIT READ TIMEOUT"],
 ["killed",f=>{},137,0,"READ KILLED // TIMEOUT OR SIGNAL"],
 ["stderr",f=>{f.done();f.c.lastError="stderr"},0,0,"READ ERROR"],
 ["repo switch away and back",f=>{f.done();f.c.repoSelectionEpoch++},0,0,"STALE REPOSITORY RESULT"]
]) {
 const f=fixture();prepare(f);f.exit(code,status);
 assert.equal(f.c.published,0,label);assert.equal(f.c.failed[0],expected,label);
 assert.equal(f.c.available,false,label);assert.equal(f.c.refreshing,false,label);
 assert.equal(f.c.topologyRevision,9,label);
 assert.equal(f.c.followups,label==="repo switch away and back"?1:0,label);
}
{
 const {c,flush}=fixture();c.refreshProcess.running=false;c.refreshSoftDeadline();flush();
 assert.equal(c.failed[0],"CHILD DID NOT START");assert.equal(c.refreshing,false);
}
{
 const {c,done,exit}=fixture();c.refreshPending=true;exit(124);
 assert.equal(c.followups,1);done();assert.equal(c.published,0);
}
assert.match(source,/readonly property bool refreshReadBusy: refreshing \|\| refreshFinalizing \|\| refreshProcess\.running/);
assert.match(source,/if \(refreshReadBusy\) \{\s*if \(refreshContextChanged\(\)\) refreshPending=true;/);
assert.match(source,/exec \/usr\/bin\/timeout --kill-after=2s 45s bash -c "\$BASH_EXECUTION_STRING"/);
console.log("Git read terminal custody: slow, exit ordering, failure, stale epoch and retry fixtures PASS");
