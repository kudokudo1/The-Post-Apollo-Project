import assert from "node:assert/strict";
import {test} from "node:test";
import {mkdtemp,mkdir,writeFile,readFile,readdir,chmod,symlink,rename,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {normalizeSnapshot} from "../../scripts/finance/actual_readonly.mjs";
import {
  createM3d5bNonActivatedController,
  inspectM3d5bSourceBinding,inspectM3d5bSharedRecovery
} from "../../scripts/finance/simple_m3d5b_protected_controller.mjs";

const actual="http://127.0.0.1:5006";
const syncId="fictional-actual-sync-12345";
function sourceKey(url=actual){
  return createHash("sha256").update(url+"\0"+syncId).digest("hex");
}
function payload(key=sourceKey()){
  const month="2026-11";
  const snapshot=normalizeSnapshot({
    month,budget:{toBudget:12000,categoryGroups:[
      {id:"needs",name:"Needs",is_income:false,hidden:false,categories:[
        {id:"groceries",name:"Groceries",hidden:false,
          budgeted:10000,balance:7500,spent:-2500},
        {id:"gas",name:"Gas",hidden:false,
          budgeted:2000,balance:1800,spent:-200}
      ]}
    ]},
    accounts:[{id:"fictional-checking",name:"Checking",offbudget:false,closed:false}],
    balances:new Map([["fictional-checking",42000]]),
    transactionSets:new Map([["fictional-checking",[]]]),
    payees:[]
  });
  snapshot.sourceKey=key;
  const candidate={action:"create",editing:false,direction:"expense",
    sourceKey:key,month,accountId:"fictional-checking",
    date:"2026-11-23",description:"Fictional Groceries",amountCents:-1250};
  const proposal={
    ok:true,readOnly:true,writeAllowed:false,savesToActual:false,
    sourceKey:key,month,accountId:"fictional-checking",date:"2026-11-23",
    description:"Fictional Groceries",expenseAmountCents:-1250,
    categoryId:"groceries",categoryName:"Groceries",groupId:"needs",
    groupName:"Needs",availableBeforeCents:7500,spentBeforeCents:-2500,
    estimatedAvailableAfterCents:6250,estimatedSpentAfterCents:-3750,
    estimatedOverspent:false,toBudgetAfterCents:null
  };
  return {snapshot,candidate,proposal,selectedCategoryId:"groceries"};
}
async function fixture(){
  // Only this test's private temp HOME; no user's Actual server, passwords,
  // real transactions, journal, permit or host settings are touched.
  const home=await mkdtemp(join(tmpdir(),"financew-m3d5b-fictional-"));
  const configDir=join(home,".config","financew");
  const journalDir=join(home,".local","state","financew","operations");
  await mkdir(configDir,{recursive:true,mode:0o700});
  await writeFile(join(configDir,"actual-server-url"),actual+"\n",{mode:0o600});
  await writeFile(join(configDir,"actual-sync-id"),syncId+"\n",{mode:0o600});
  const options={configDir,journalDir};
  return {home,configDir,journalDir,options,
    controller:()=>createM3d5bNonActivatedController(options)};
}
async function within(fn) {
  const f=await fixture();
  try{await fn(f);}finally{await rm(f.home,{recursive:true,force:true});}
}
test("explicit two-step confirmation is one-use, cannot dispatch, and logs no command",async()=>{
  await within(async f=>{
    const c=f.controller(),v=payload();
    assert.deepEqual(Object.keys(c).sort(),[
      "cancel","confirm","dispatch","stage","status"].sort());
    assert.equal(c.status().productionDispatch,"HARD-HOLD");
    assert.equal(c.dispatch().reason,"production-dispatch-hard-hold");
    const first=await c.stage(v);
    assert.equal(first.ok,true,JSON.stringify(first));
    assert.equal(first.canSave,false);
    assert.equal(first.writeAllowed,false);
    assert.match(first.confirmationPrompt,/^CONFIRM CATEGORY [0-9a-f]{16}$/);
    assert.equal(await c.stage(v).then(x=>x.ok),false);
    const saved=await c.confirm({
      confirmationText:first.confirmationPrompt,current:v});
    assert.equal(saved.ok,true,JSON.stringify(saved));
    assert.equal(saved.canSave,false);
    assert.equal(saved.writeAllowed,false);
    assert.equal(saved.phase,"confirmed-but-dispatch-disabled");
    assert.match(saved.fingerprint,/^[a-f0-9]{64}$/);
    assert.equal("requestId" in saved,false);
    assert.equal("action" in saved,false);
    assert.equal("command" in saved,false);
    assert.equal("previewFields" in saved,false);
    assert.equal(c.dispatch().reason,"production-dispatch-hard-hold");
    assert.equal((await c.confirm({
      confirmationText:first.confirmationPrompt,current:v})).reason,
      "confirmation-not-armed");
    assert.equal((await c.stage(v)).reason,"controller-not-idle");
    await assert.rejects(readdir(f.journalDir),{code:"ENOENT"});
    const entries=await readdir(f.configDir);
    assert.deepEqual(entries.sort(),["actual-server-url","actual-sync-id"]);
  });
});
test("read-only source identity refuses 5007 default, malformed URL, and changed key",async()=>{
  await within(async f=>{
    assert.equal((await inspectM3d5bSourceBinding({
      sourceKey:sourceKey(),configDir:f.configDir})).ok,true);
    const c=f.controller();
    assert.equal((await c.stage(payload(sourceKey(
      "http://127.0.0.1:5007")))).reason,"read-write-source-mismatch");
    assert.equal(c.dispatch().reason,"production-dispatch-hard-hold");
    await writeFile(join(f.configDir,"actual-server-url"),
      "http://127.0.0.1:5007\n",{mode:0o600});
    const t=f.controller();
    assert.equal((await t.stage(payload(sourceKey(
      "http://127.0.0.1:5007")))).reason,"read-write-endpoint-not-aligned");
    await writeFile(join(f.configDir,"actual-server-url"),
      "http://localhost:5006\n",{mode:0o600});
    assert.equal((await f.controller().stage(payload())).ok,false);
    await writeFile(join(f.configDir,"actual-server-url"),actual+"\n",{mode:0o600});
    assert.equal((await f.controller().stage(payload())).ok,true);
  });
});
test("untrusted private source configuration, symlinked file, chmod and missing sync ID refuse",async()=>{
  await within(async f=>{
    const path=join(f.configDir,"actual-sync-id");
    await chmod(path,0o644);
    assert.equal((await f.controller().stage(payload())).reason,
      "source-files-untrusted-or-unavailable");
    await chmod(path,0o600);
    await rename(path,path+"-real");
    await symlink("actual-sync-id-real",path);
    assert.equal((await f.controller().stage(payload())).reason,
      "source-files-untrusted-or-unavailable");
    await rm(path);
    assert.equal((await f.controller().stage(payload())).reason,
      "source-files-untrusted-or-unavailable");
    await rename(path+"-real",path);
    await chmod(f.configDir,0o770);
    assert.equal((await f.controller().stage(payload())).reason,
      "source-files-untrusted-or-unavailable");
  });
});
test("outstanding lock and uncommitted cross-writer journal block review",async()=>{
  await within(async f=>{
    assert.equal((await inspectM3d5bSharedRecovery({
      journalDir:f.journalDir})).ok,true);
    await mkdir(f.journalDir,{recursive:true,mode:0o700});
    await writeFile(join(f.journalDir,".write-lock"),"pending\n",{mode:0o600});
    assert.equal((await f.controller().stage(payload())).reason,"write-lock-present");
    await rm(join(f.journalDir,".write-lock"));
    const entry=join(f.journalDir,"allocation-"+"a".repeat(32)+".json");
    await writeFile(entry,'{"version":1,"status":"attempted"}\n',{mode:0o600});
    assert.equal((await f.controller().stage(payload())).reason,
      "unresolved-finance-operation");
    await writeFile(entry,'{"version":1,"status":"committed"}\n',{mode:0o600});
    assert.equal((await f.controller().stage(payload())).ok,true);
    await chmod(entry,0o644);
    assert.equal((await f.controller().stage(payload())).reason,
      "untrusted-or-unresolved-journal");
    await chmod(entry,0o600);
    await writeFile(join(f.journalDir,"unexpected-entry"),"data\n",{mode:0o600});
    assert.equal((await f.controller().stage(payload())).reason,
      "unrecognized-journal-entry");
  });
});
test("any changed amount, source, visibility, picker, category or month prevents confirmation",async()=>{
  const mutations=[
    x=>{x.candidate.amountCents=-1300;},
    x=>{x.proposal.estimatedAvailableAfterCents=6000;},
    x=>{x.selectedCategoryId="gas";},
    x=>{x.snapshot.categories[0].hidden=true;},
    x=>{x.snapshot.categoryGroups[0].hidden=null;},
    x=>{x.snapshot.toBudgetCents=11500;},
    x=>{x.snapshot.month="2026-12";},
    x=>{x.candidate.accountId="somewhere-else";},
    x=>{x.candidate.date="2026-11-24";},
    x=>{x.candidate.description="Different";},
    x=>{x.snapshot.sourceKey="b".repeat(64);}
  ];
  for(const change of mutations){
    await within(async f=>{
      const c=f.controller(),v=payload();
      const first=await c.stage(v);
      assert.equal(first.ok,true);
      // Mutate in place; do not depend on a Qt change signal.
      change(v);
      const result=await c.confirm({
        confirmationText:first.confirmationPrompt,current:v});
      assert.equal(result.ok,false,JSON.stringify(result));
      assert.equal(result.canSave,false);
      assert.equal(c.dispatch().reason,"production-dispatch-hard-hold");
    });
  }
});
test("wrong phrase consumes confirmation; no retry with same or another phrase",async()=>{
  await within(async f=>{
    const c=f.controller(),v=payload();
    const first=await c.stage(v);
    assert.equal((await c.confirm({confirmationText:"YES",current:v})).reason,
      "confirmation-mismatch");
    assert.equal((await c.confirm({
      confirmationText:first.confirmationPrompt,current:v})).reason,
      "confirmation-not-armed");
    assert.equal((await c.stage(v)).reason,"controller-not-idle");
  });
});
test("two concurrent confirmations mint at most one sealed intent",async()=>{
  await within(async f=>{
    const c=f.controller(),v=payload(),first=await c.stage(v);
    const [one,two]=await Promise.all([
      c.confirm({confirmationText:first.confirmationPrompt,current:v}),
      c.confirm({confirmationText:first.confirmationPrompt,current:v})
    ]);
    assert.equal([one,two].filter(x=>x.ok).length,1);
    assert.equal([one,two].filter(x=>!x.ok).length,1);
    assert.equal(c.dispatch().reason,"production-dispatch-hard-hold");
  });
});
test("cancel prevents older in-flight stage or confirmation from rearming",async()=>{
  await within(async f=>{
    const c=f.controller(),v=payload(),staged=c.stage(v);
    c.cancel();
    assert.equal((await staged).ok,false);
    assert.equal(c.status().phase,"canceled");
    const next=f.controller();
    const ready=await next.stage(v);
    assert.equal(ready.ok,true);
    const confirming=next.confirm({
      confirmationText:ready.confirmationPrompt,current:v});
    next.cancel();
    assert.equal((await confirming).ok,false);
    assert.equal(next.status().phase,"canceled");
  });
});
test("source identity changes after review and a newly appeared recovery lock abort confirm",async()=>{
  await within(async f=>{
    const c=f.controller(),v=payload(),first=await c.stage(v);
    await writeFile(join(f.configDir,"actual-server-url"),
      "http://127.0.0.1:5007\n",{mode:0o600});
    assert.equal((await c.confirm({
      confirmationText:first.confirmationPrompt,current:v})).reason,
      "read-write-endpoint-not-aligned");
    await writeFile(join(f.configDir,"actual-server-url"),actual+"\n",{mode:0o600});
    const second=f.controller(),phase=await second.stage(v);
    await mkdir(f.journalDir,{recursive:true,mode:0o700});
    await writeFile(join(f.journalDir,".write-lock"),"pending\n",{mode:0o600});
    assert.equal((await second.confirm({
      confirmationText:phase.confirmationPrompt,current:v})).reason,
      "write-lock-present");
  });
});
