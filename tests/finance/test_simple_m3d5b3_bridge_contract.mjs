import assert from "node:assert/strict";
import {test} from "node:test";
import {mkdtemp,mkdir,writeFile,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {normalizeSnapshot} from "../../scripts/finance/actual_readonly.mjs";
import {prepareOfflineCategorizedReview}
  from "../../scripts/finance/simple_m3d2_offline_review.mjs";
import {createM3d5bNonActivatedController}
  from "../../scripts/finance/simple_m3d5b_protected_controller.mjs";
import {
  inspectM3d5b3PreDispatch,inspectM3d5b3SourceCompatibility,
  classifyM3d5b3SyntheticRecovery
} from "../../scripts/finance/simple_m3d5b3_bridge_contract.mjs";

const url="http://127.0.0.1:5006",syncId="fictional-source-sync-9876";
const sourceKey=createHash("sha256").update(url+"\0"+syncId).digest("hex");
const shape={
  readerEndpoint:url,writerEndpoint:url,writerSourceKey:sourceKey
};
function makeView(){
  const month="2026-11";
  const snapshot=normalizeSnapshot({
    month,budget:{toBudget:12000,categoryGroups:[
      {id:"needs",name:"Needs",is_income:false,hidden:false,categories:[
        {id:"groceries",name:"Groceries",hidden:false,
          budgeted:10000,balance:7500,spent:-2500}
      ]}
    ]},
    accounts:[{id:"fictional-checking",name:"Checking",offbudget:false,closed:false}],
    balances:new Map([["fictional-checking",42000]]),
    transactionSets:new Map([["fictional-checking",[]]]),payees:[]
  });
  snapshot.sourceKey=sourceKey;
  const candidate={action:"create",editing:false,direction:"expense",
    sourceKey,month,accountId:"fictional-checking",
    date:"2026-11-25",description:"Fictional Groceries",amountCents:-1250};
  const proposal={ok:true,readOnly:true,writeAllowed:false,
    savesToActual:false,sourceKey,month,accountId:"fictional-checking",
    date:"2026-11-25",description:"Fictional Groceries",
    expenseAmountCents:-1250,categoryId:"groceries",
    categoryName:"Groceries",groupId:"needs",groupName:"Needs",
    availableBeforeCents:7500,spentBeforeCents:-2500,
    estimatedAvailableAfterCents:6250,estimatedSpentAfterCents:-3750,
    estimatedOverspent:false,toBudgetAfterCents:null};
  return {snapshot,candidate,proposal,selectedCategoryId:"groceries"};
}
const confirmation=()=>({
  ok:true,canSave:false,writeAllowed:false,
  phase:"confirmed-but-dispatch-disabled",
  reason:"request-identity-issued-and-discarded",
  fingerprint:"a".repeat(64)
});
function args(){
  const view=makeView();
  return {view,previousReview:prepareOfflineCategorizedReview(view),
    controllerConfirmation:confirmation(),...shape};
}
function hold(x,reason=null){
  assert.equal(x.ok,false,JSON.stringify(x));
  assert.equal(x.canSave,false);
  assert.equal(x.writeAllowed,false);
  assert.equal(x.dispatchAllowed,false);
  assert.equal(x.requestIssued,false);
  assert.equal(x.canRetry,false);
  if(reason!==null)assert.equal(x.reason,reason);
  assert.equal("requestId" in x,false);
  assert.equal("command" in x,false);
  assert.equal("inputFrame" in x,false);
}
test("even matching reviewed details and confirmation cannot invent durable M3b request ID",()=>{
  const result=inspectM3d5b3PreDispatch(args());
  hold(result,"durable-request-id-not-exported");
  assert.equal(result.reviewMatched,true);
});
test("read-only 5007 is never aliased to protected 5006, even when keys match",()=>{
  const candidate=args();
  candidate.readerEndpoint="http://127.0.0.1:5007";
  hold(inspectM3d5b3PreDispatch(candidate),"read-write-endpoint-mismatch");
  candidate.readerEndpoint=url;
  candidate.writerEndpoint="http://localhost:5006";
  hold(inspectM3d5b3PreDispatch(candidate),"read-write-endpoint-mismatch");
  candidate.readerEndpoint="http://localhost:5006";
  hold(inspectM3d5b3PreDispatch(candidate),"protected-writer-endpoint-unapproved");
  const x=inspectM3d5b3SourceCompatibility({
    readerEndpoint:url,writerEndpoint:url,readerSourceKey:sourceKey,
    writerSourceKey:"b".repeat(64)
  });
  hold(x,"read-write-source-mismatch");
  hold(inspectM3d5b3SourceCompatibility({
    readerSourceKey:sourceKey,writerSourceKey:sourceKey
  }),"explicit-endpoint-witness-required");
});
test("selection, visible group, exact budget and in-place amount changes deny stale review",()=>{
  for(const change of [
    x=>x.selectedCategoryId="other",
    x=>x.snapshot.categoryGroups[0].hidden=null,
    x=>x.snapshot.categories[0].hidden=true,
    x=>x.snapshot.categories[0].availableCents=6500,
    x=>x.snapshot.toBudgetCents=9000,
    x=>x.candidate.amountCents=-1000,
    x=>x.candidate.description="changed",
    x=>x.candidate.month="2026-12",
    x=>x.proposal.categoryId="elsewhere",
    x=>x.snapshot.sourceKey="f".repeat(64)
  ]){
    const item=args();change(item.view);
    const result=inspectM3d5b3PreDispatch(item);
    assert.equal(result.ok,false);
    assert.equal(result.dispatchAllowed,false);
    assert.equal(result.canRetry,false);
    assert.notEqual(result.reason,"durable-request-id-not-exported",
      "recheck must fail before custody gate");
  }
});
test("missing, forged or executable confirmation cannot be interpreted as authority",()=>{
  for(const forged of [
    undefined,{},false,
    {...confirmation(),canSave:true},
    {...confirmation(),phase:"committed"},
    {...confirmation(),fingerprint:"bad"},
    {...confirmation(),requestId:"a".repeat(32)},
    {...confirmation(),command:{action:"create-categorized-expense"}},
    {...confirmation(),previewFields:{}},
    {...confirmation(),writeAllowed:true}
  ]){
    const candidate=args();candidate.controllerConfirmation=forged;
    const result=inspectM3d5b3PreDispatch(candidate);
    hold(result);
    assert.notEqual(result.reason,"durable-request-id-not-exported");
  }
});
test("real M3d5b1 confirmation receipt still cannot act as durable transport authority",async()=>{
  const root=await mkdtemp(join(tmpdir(),"financew-m3d5b3-readonly-"));
  const configDir=join(root,".config","financew");
  const journalDir=join(root,".local","state","financew","operations");
  try{
    await mkdir(configDir,{recursive:true,mode:0o700});
    await writeFile(join(configDir,"actual-server-url"),url+"\n",{mode:0o600});
    await writeFile(join(configDir,"actual-sync-id"),syncId+"\n",{mode:0o600});
    const controller=createM3d5bNonActivatedController({configDir,journalDir});
    const view=makeView();
    const previousReview=prepareOfflineCategorizedReview(view);
    assert.equal(previousReview.ok,true);
    const armed=await controller.stage(view);
    assert.equal(armed.ok,true,JSON.stringify(armed));
    const confirmed=await controller.confirm({
      confirmationText:armed.confirmationPrompt,current:view
    });
    assert.equal(confirmed.ok,true,JSON.stringify(confirmed));
    hold(inspectM3d5b3PreDispatch({
      view,previousReview,controllerConfirmation:confirmed,...shape
    }),"durable-request-id-not-exported");
    assert.equal(controller.dispatch().reason,"production-dispatch-hard-hold");
  }finally{await rm(root,{recursive:true,force:true});}
});
test("synthetic recovery trace cannot become an Actual commit or auto-retry",()=>{
  const cases=[
    {phase:"before-reservation",journal:"absent",state:"not-dispatched"},
    {phase:"sealed-dry-run",journal:"sealed",state:"not-dispatched"},
    {phase:"writer-attempted",journal:"attempted",state:"uncertain"},
    {phase:"writer-attempted",journal:"committed",state:"uncertain"},
    {phase:"writer-exited",journal:"corrupt",state:"uncertain"},
    {phase:"writer-exited",journal:"absent",state:"uncertain"},
    {phase:"writer-exited",journal:"committed",state:"uncertain"},
    {phase:"writer-exited",journal:"committed",failure:"timeout",state:"uncertain"},
    {phase:"writer-exited",journal:"committed",failure:"process-crash",state:"uncertain"}
  ];
  for(const item of cases){
    const result=classifyM3d5b3SyntheticRecovery(item);
    assert.equal(result.state,item.state,JSON.stringify(item));
    assert.equal(result.syntheticOnly,true);
    assert.equal(result.productionWrite,false);
    assert.equal(result.dispatchAllowed,false);
    assert.equal(result.canRetry,false);
    assert.equal("committed" in result,false);
  }
  const evidence=classifyM3d5b3SyntheticRecovery({
    phase:"writer-exited",journal:"committed",readback:"matching",
    stdout:"FINANCEW_CATEGORIZED_EXPENSE_RESULT committed\n",exitCode:0
  });
  assert.equal(evidence.state,"synthetic-evidence-consistent");
  assert.equal(evidence.syntheticOnly,true);
  assert.equal(evidence.productionWrite,false);
  assert.equal(evidence.canRetry,false);
  for(const stdout of [
    "FINANCEW_CATEGORIZED_EXPENSE_RESULT committed\n\n",
    "FINANCEW_CATEGORIZED_EXPENSE_RESULT committed",
    "FINANCEW_CATEGORIZED_EXPENSE_RESULT blocked:recovery-needed\n",
    "\nFINANCEW_CATEGORIZED_EXPENSE_RESULT committed\n"
  ]){
    const x=classifyM3d5b3SyntheticRecovery({
      phase:"writer-exited",journal:"committed",readback:"matching",stdout,
      exitCode:0
    });
    assert.equal(x.state,"uncertain");
    assert.equal(x.canRetry,false);
  }
});
test("identical purchase content is not itself treated as a permanent forbidden retry",()=>{
  // Unlike M3d5b2's test fixture global body fingerprint, a future live
  // transport must distinguish same purchase details in distinct
  // confirmed intents while still preventing replay of one intent ID.
  const first=args(),second=args();
  hold(inspectM3d5b3PreDispatch(first),"durable-request-id-not-exported");
  hold(inspectM3d5b3PreDispatch(second),"durable-request-id-not-exported");
});
