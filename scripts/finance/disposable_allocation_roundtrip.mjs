#!/usr/bin/env node
// D12b: real Actual engine, isolated fictional budget, CI ONLY.
// This is an integration test for allocation_guard.mjs with an injected
// recordAttempt spy. It is NOT a production writer and has no local activation.
import assert from "node:assert/strict";
import {spawn,spawnSync} from "node:child_process";
import {createConnection} from "node:net";
import {existsSync} from "node:fs";
import {mkdtemp,mkdir,rm,chmod,writeFile,readFile,stat} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
import * as api from "@actual-app/api";
import {takeOpeningHistory} from "./opening_history.mjs";
import {takeReadOnlySnapshot} from "./actual_readonly.mjs";
import {executeAllocation,preflightAllocation,AllocationRefusal}
  from "./allocation_guard.mjs";
import {executeRehearsal,preflightRehearsal,inspectUncertainIncome,
  FundingRehearsalRefusal}
  from "../../tests/finance/fixtures/funding_disposable_rehearsal.mjs";

if(process.env.GITHUB_ACTIONS!=="true" || process.env.CI!=="true"
    || process.env.FINANCEW_DISPOSABLE_TEST!=="yes")
  throw new Error("CI-only-disposable-test");

const here=dirname(fileURLToPath(import.meta.url));
const binary=join(here,"node_modules",".bin","actual-server");
const writer=join(here,"write_allocation.mjs");
const fundingWriter=join(here,"write_funding.mjs");
const categoryWriter=join(here,"write_category.mjs");
const host="http://127.0.0.1:5006";
const password="FICTIONAL-ONLY-D12-TEST-2026";
const date=new Date().toISOString().slice(0,7)+"-01";
const month=date.slice(0,7);
let stage="preflight";
let server=null;
let temporary=null;
let active=false;
let engine=null;

const nap=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function checkEmptyPort(){
  return new Promise((resolve,reject)=>{
    const socket=createConnection({host:"127.0.0.1",port:5006});
    socket.once("connect",()=>{
      socket.destroy();reject(new Error("port-occupied"));
    });
    socket.once("error",e=>{
      socket.destroy();
      e.code==="ECONNREFUSED" ? resolve() : reject(new Error("port-unavailable"));
    });
  });
}
async function bootstrapServer(){
  assert.ok(existsSync(binary),"pinned-real-server-missing");
  await checkEmptyPort();
  const serverDir=join(temporary,"server");
  await mkdir(serverDir,{mode:0o700});
  server=spawn(binary,[],{
    cwd:serverDir,stdio:"ignore",
    env:{PATH:process.env.PATH,HOME:temporary,ACTUAL_DATA_DIR:serverDir,
      ACTUAL_HOSTNAME:"127.0.0.1",ACTUAL_PORT:"5006",
      ACTUAL_SERVER_FILES:join(serverDir,"server-files"),
      ACTUAL_USER_FILES:join(serverDir,"user-files")}
  });
  let ready=false;
  for(let i=0;i<150;i++){
    if(server.exitCode!==null)throw new Error("server-exited");
    try{
      const response=await fetch(host+"/account/needs-bootstrap",
        {signal:AbortSignal.timeout(1000)});
      if(response.ok){
        const info=await response.json();
        assert.equal(info.status,"ok");
        assert.equal(info.data?.bootstrapped,false);
        ready=true;break;
      }
    }catch(e){if(e.name==="AssertionError")throw e;}
    await nap(200);
  }
  if(!ready)throw new Error("server-start-timeout");
  const response=await fetch(host+"/account/bootstrap",{
    method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({password}),signal:AbortSignal.timeout(8000)});
  assert.equal(response.ok,true);
  const status=await response.json();
  assert.equal(status.status,"ok");
}
async function startClient(label){
  await mkdir(join(temporary,label),{recursive:true,mode:0o700});
  engine=await api.init({dataDir:join(temporary,label),
    serverURL:host,password});
  active=true;
}
async function endClient(){
  if(active){active=false;await api.shutdown();engine=null;}
}
function findCategory(budget,id){
  return budget?.categoryGroups?.filter(group=>group && !group.is_income
    && Array.isArray(group.categories)).flatMap(group=>group.categories)
    .filter(cat=>cat && cat.id===id) || [];
}
function redactError(e){
  const code=e instanceof AllocationRefusal?e.code:"other";
  return code.replace(/[^a-z-]/g,"");
}
async function main(){
  temporary=await mkdtemp(join(tmpdir(),"financew-d12b-fictional-"));
  await chmod(temporary,0o700);
  stage="server";
  await bootstrapServer();

  stage="fictional-budget";
  await startClient("initial");
  let accountId,groupId,categoryId;
  await api.runImport("D12 FICTIONAL Allocation Budget",async()=>{
    accountId=await api.createAccount({name:"FICTIONAL Checking",offbudget:false});
    groupId=await api.createCategoryGroup({name:"FICTIONAL Expenses",hidden:false});
    categoryId=await api.createCategory({name:"FICTIONAL Food",group_id:groupId,
      is_income:false,hidden:false});
  });
  assert.ok(typeof accountId==="string" && accountId.length>4);
  assert.ok(typeof groupId==="string" && groupId.length>4);
  assert.ok(typeof categoryId==="string" && categoryId.length>4);
  stage="d14-empty-budget-snapshot";
  const unfunded=await takeReadOnlySnapshot(api,month);
  assert.equal(unfunded.readOnly,true);
  assert.equal(unfunded.funding.openingBalancesVerified,false);
  assert.equal(unfunded.incomeReview.readOnly,true);
  assert.equal(unfunded.incomeReview.candidateCount,0);
  stage="fictional-income-category";
  // Actual's available-to-budget calculation uses the income category
  // subtotal, not every unclassified positive account transaction.
  const initialMonth=await api.getBudgetMonth(month);
  const incomeGroups=initialMonth.categoryGroups
    .filter(group=>group && group.is_income && Array.isArray(group.categories));
  assert.equal(incomeGroups.length,1,"fictional-income-group-required");
  let incomeCategoryId=incomeGroups[0].categories[0]?.id;
  if(!incomeCategoryId) {
    incomeCategoryId=await api.createCategory({name:"FICTIONAL Income",
      group_id:incomeGroups[0].id,is_income:true,hidden:false});
  }
  assert.equal(typeof incomeCategoryId,"string");
  stage="fictional-income";
  const acknowledgment=await api.addTransactions(accountId,[{
    id:"a1111111-aaaa-4aaa-8aaa-aaaaaaaaaaaa",date,amount:10000,
    category:incomeCategoryId,payee_name:"FICTIONAL INCOME",cleared:false
  },{
    id:"b2222222-bbbb-4bbb-8bbb-bbbbbbbbbbbb",date,amount:200,
    payee_name:"FICTIONAL UNCLASSIFIED RECEIPT",cleared:false
  }],{runTransfers:false,learnCategories:false});
  assert.equal(acknowledgment,"ok");
  await api.sync();

  stage="upload";
  assert.equal(typeof engine?.send,"function");
  const upload=await engine.send("upload-budget");
  assert.equal(upload?.error,undefined);
  const remote=await engine.send("get-remote-files");
  assert.ok(Array.isArray(remote) && remote.length===1);
  const syncId=remote[0]?.groupId;
  assert.ok(typeof syncId==="string" && syncId.length>8);
  await endClient();

  stage="fresh-preflight";
  await startClient("independent");
  await api.downloadBudget(syncId);
  stage="d15-real-opening-history";
  const historical=await takeOpeningHistory(api,month);
  assert.equal(historical.kind,"financew-opening-history");
  assert.equal(historical.openingBalancesVerified,false);
  assert.equal(historical.accounts.length,1);
  assert.ok(historical.accounts[0].transactionCount>=1);
  stage="fresh-preflight";
  stage="fresh-budget-month";
  const before=await api.getBudgetMonth(month);
  stage="d14-funded-budget-snapshot";
  const funded=await takeReadOnlySnapshot(api,month);
  assert.equal(funded.funding.toBudgetCents,funded.toBudgetCents);
  assert.equal(funded.funding.openingBalancesVerified,false);
  assert.equal(funded.incomeReview.readOnly,true);
  assert.equal(funded.incomeReview.candidateCount,
    funded.funding.positiveUncategorizedCount);
  assert.equal(funded.incomeReview.candidateCount,1);
  assert.equal(funded.incomeReview.candidates[0].amountCents,200);
  assert.equal(funded.incomeReview.categoriesOverflow,false);
  assert.ok(funded.incomeReview.incomeCategories.some(x=>x.id===incomeCategoryId));
  stage="fresh-category-presence";
  assert.equal(findCategory(before,categoryId).length,1);
  const category=findCategory(before,categoryId)[0];
  stage="fresh-to-budget";
  assert.ok(Number.isSafeInteger(before.toBudget));
  stage="fresh-category-budgeted";
  assert.ok(Number.isSafeInteger(category.budgeted));
  stage="fresh-category-balance";
  assert.ok(Number.isSafeInteger(category.balance));
  // Never assume initial envelope state or amount available. Derive the
  // safe increase from actual real-engine values in the fictional budget.
  const capacity=Math.min(before.toBudget,99999999999-category.budgeted);
  stage="fresh-income-capacity";
  assert.ok(capacity>=100,"fictional-income-unavailable");
  const delta=Math.min(1000,capacity);
  const target=category.budgeted+delta;
  const command={
    action:"set-amount",requestId:"b".repeat(32),
    sourceKey:createHash("sha256").update(host+"\0"+syncId).digest("hex"),
    month,categoryId,
    expectedBudgetedCents:category.budgeted,
    expectedAvailableCents:category.balance,
    expectedToBudgetCents:before.toBudget,
    targetBudgetedCents:target
  };
  assert.equal(preflightAllocation(command,before).delta,delta);

  stage="stale-preflight-refusal";
  let records=0,mutations=0;
  const facade={
    getBudgetMonth:m=>api.getBudgetMonth(m),
    async setBudgetAmount(m,id,value){
      mutations++;
      return api.setBudgetAmount(m,id,value);
    },
    sync:()=>api.sync()
  };
  await assert.rejects(()=>executeAllocation({
    api:facade,input:{...command,expectedToBudgetCents:before.toBudget-1},
    recordAttempt:async()=>{records++;}
  }),err=>err instanceof AllocationRefusal && err.code==="stale-budget");
  assert.equal(mutations,0);
  assert.equal(records,0);

  stage="real-set-budget-amount";
  const result=await executeAllocation({
    api:facade,input:command,recordAttempt:async()=>{records++;}
  });
  assert.deepEqual(result,{status:"committed"});
  assert.equal(mutations,1);
  assert.equal(records,1);
  await endClient();

  stage="independent-fresh-readback";
  await startClient("verify");
  await api.downloadBudget(syncId);
  const after=await api.getBudgetMonth(month);
  const rows=findCategory(after,categoryId);
  assert.equal(rows.length,1);
  assert.equal(rows[0].budgeted,target);
  assert.equal(rows[0].balance,category.balance+delta);
  assert.equal(after.toBudget,before.toBudget-delta);

  // D12c: end the test API session. Run the actual production Node writer
  // in its own process against this disposable loopback server and budget.
  await endClient();
  stage="real-writer-private-config";
  const writerHome=join(temporary,"fictional-writer-home");
  const config=join(writerHome,".config","financew");
  await mkdir(config,{recursive:true,mode:0o700});
  for(const [name,value] of [
    ["actual-server-url",host],
    ["actual-password",password],
    ["actual-sync-id",syncId]
  ])await writeFile(join(config,name),value+"\n",{mode:0o600,flag:"wx"});
  const writerDelta=Math.min(100,after.toBudget);
  assert.ok(writerDelta>=1,"fictional-writer-funds-unavailable");
  const newTarget=rows[0].budgeted+writerDelta;
  const writerCommand={
    ...command,requestId:"d".repeat(32),
    expectedBudgetedCents:rows[0].budgeted,
    expectedAvailableCents:rows[0].balance,
    expectedToBudgetCents:after.toBudget,
    targetBudgetedCents:newTarget
  };
  const executeWriter=()=>{
    return spawnSync(process.execPath,[writer],{
      encoding:"utf8",timeout:45000,
      input:JSON.stringify(writerCommand)+"\n",
      env:{...process.env,HOME:writerHome,ACTUAL_SERVER_URL:"",
        ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID:"",
        ACTUAL_SYNC_ID_FILE:"",ACTUAL_ENCRYPTION_PASSWORD_FILE:""}
    });
  };
  stage="real-writer-gate-refusal";
  const locked=executeWriter();
  assert.equal(locked.error,undefined);
  assert.equal(locked.status,1);
  assert.equal(locked.stdout.trim(),
    "FINANCEW_ALLOCATION_RESULT blocked:writes-disabled");
  const journal=join(writerHome,".local","state","financew","operations",
    "allocation-"+writerCommand.requestId+".json");
  assert.equal(existsSync(journal),false);

  stage="real-writer-commit";
  await writeFile(join(config,"allocation-writes-enabled"),
    "FINANCEW_ALLOCATION_WRITES_APPROVED\n",{mode:0o600,flag:"wx"});
  const saved=executeWriter();
  assert.equal(saved.error,undefined);
  const savedToken=/FINANCEW_ALLOCATION_RESULT ([a-z0-9:-]+)/.exec(saved.stdout)?.[1]
    || "no-result";
  if(saved.status!==0 || savedToken!=="committed")
    throw new Error("writer-"+savedToken);
  const receipt=JSON.parse(await readFile(journal,"utf8"));
  assert.equal(receipt.status,"committed");
  assert.equal((await stat(journal)).mode & 0o077,0);
  assert.equal((await readFile(journal,"utf8")).includes(categoryId),false);
  stage="real-writer-repeat-refusal";
  const duplicate=executeWriter();
  assert.equal(duplicate.status,1);
  assert.match(duplicate.stdout,
    /FINANCEW_ALLOCATION_RESULT blocked:operation-already-attempted/);

  stage="real-writer-fresh-client-readback";
  await startClient("after-cli");
  await api.downloadBudget(syncId);
  const confirmed=await api.getBudgetMonth(month);
  const updated=findCategory(confirmed,categoryId);
  assert.equal(updated.length,1);
  assert.equal(updated[0].budgeted,newTarget);
  assert.equal(updated[0].balance,rows[0].balance+writerDelta);
  assert.equal(confirmed.toBudget,after.toBudget-writerDelta);
  // D17b: real pinned Actual engine, fictional funding ONLY. These routines
  // are isolated test fixtures; no FinanceW runtime import or real permit.
  stage="d17b-disposable-existing-opening-refusal";
  const sourceKey=createHash("sha256").update(host+"\0"+syncId).digest("hex");
  let fundingAttempts=0;
  const incomePlan={
    mode:"income",requestId:"e".repeat(32),sourceKey,accountId,month,date,
    amountCents:347,categoryId:incomeCategoryId,
    description:"D17 FICTIONAL INCOME REHEARSAL"
  };
  await assert.rejects(()=>preflightRehearsal({api,input:{
    ...incomePlan,mode:"existing-account-opening"
  },expectedSourceKey:sourceKey}),
    error=>error instanceof FundingRehearsalRefusal
      && error.code==="existing-opening-requires-bank-reconciliation");
  stage="d17b-disposable-income-preflight";
  await preflightRehearsal({api,input:incomePlan,expectedSourceKey:sourceKey});
  await assert.rejects(()=>preflightRehearsal({api,input:incomePlan,
    expectedSourceKey:"0".repeat(64)}),
    error=>error instanceof FundingRehearsalRefusal
      && error.code==="budget-source-changed");
  stage="d17b-disposable-income";
  const incomeResult=await executeRehearsal({api,input:incomePlan,
    expectedSourceKey:sourceKey,recordAttempt:async()=>{fundingAttempts++;}});
  assert.equal(incomeResult.status,"committed");
  assert.equal(fundingAttempts,1);
  assert.equal((await inspectUncertainIncome({api,input:incomePlan})).status,"observed");
  await assert.rejects(()=>preflightRehearsal({api,input:{
    ...incomePlan,requestId:"f".repeat(32)
  },expectedSourceKey:sourceKey}),
    error=>error instanceof FundingRehearsalRefusal
      && error.code==="possible-duplicate-income");
  stage="d17b-disposable-new-account";
  const openingPlan={
    mode:"new-account-opening",requestId:"c".repeat(32),sourceKey,
    accountName:"D17 FICTIONAL New Account",amountCents:5555
  };
  const openingResult=await executeRehearsal({api,input:openingPlan,
    expectedSourceKey:sourceKey,recordAttempt:async()=>{fundingAttempts++;}});
  assert.equal(openingResult.status,"committed");
  assert.equal(fundingAttempts,2);
  await assert.rejects(()=>preflightRehearsal({api,input:{
    ...openingPlan,requestId:"1".repeat(32)
  },expectedSourceKey:sourceKey}),
    error=>error instanceof FundingRehearsalRefusal
      && error.code==="possible-existing-account");
  stage="d17b-disposable-independent-readback";
  await endClient();
  await startClient("d17b-independent");
  await api.downloadBudget(syncId);
  const verifyIncome=await api.getTransactions(accountId,month+"-01",month+"-31");
  assert.equal(verifyIncome.filter(r=>r.id===incomeResult.transactionId
    && r.amount===347 && r.category===incomeCategoryId).length,1);
  const verifyAccounts=await api.getAccounts();
  assert.equal(verifyAccounts.filter(a=>a.id===openingResult.accountId).length,1);
  assert.equal(await api.getAccountBalance(openingResult.accountId),5555);
  // D17c production CLI is only exercised against this disposable
  // server/budget. The permit is made inside the disposable temporary HOME.
  await endClient();
  const writerIncome={
    mode:"income",requestId:"2".repeat(32),sourceKey,
    accountId,month,date,amountCents:912,categoryId:incomeCategoryId,
    description:"D17C FICTIONAL Income"
  };
  const writerOpening={
    mode:"new-account-opening",requestId:"3".repeat(32),sourceKey,
    accountName:"D17C FICTIONAL New Account",amountCents:6500
  };
  const runFunding=cmd=>spawnSync(process.execPath,[fundingWriter],{
    encoding:"utf8",timeout:45000,
    input:JSON.stringify(cmd)+"\n",
    env:{...process.env,HOME:writerHome,ACTUAL_SERVER_URL:"",
      ACTUAL_SYNC_ID:"",ACTUAL_PASSWORD_FILE:"",
      ACTUAL_SYNC_ID_FILE:"",ACTUAL_ENCRYPTION_PASSWORD_FILE:""}
  });
  const receiptPath=cmd=>join(writerHome,".local","state","financew",
    "operations","funding-"+cmd.requestId+".json");
  stage="d17c-permit-missing";
  const refused=runFunding(writerIncome);
  assert.equal(refused.status,1);
  assert.equal(refused.stdout.trim(),"FINANCEW_FUNDING_RESULT blocked:writes-disabled");
  assert.equal(existsSync(receiptPath(writerIncome)),false);
  stage="d17c-fictional-operator-permit";
  await writeFile(join(config,"funding-writes-enabled"),
    "FINANCEW_FUNDING_WRITES_APPROVED\n",{mode:0o600,flag:"wx"});
  stage="d17c-production-income-commit";
  const committed=runFunding(writerIncome);
  assert.equal(committed.error,undefined);
  const incomeStatus=/FINANCEW_FUNDING_RESULT ([a-z0-9:-]+)/.exec(committed.stdout)?.[1] || "missing-status";
  if(committed.status!==0 || incomeStatus!=="committed")
    throw new Error("funding-income-"+incomeStatus+"-exit-"+committed.status);
  const incomeReceipt=JSON.parse(await readFile(receiptPath(writerIncome),"utf8"));
  assert.equal(incomeReceipt.status,"committed");
  assert.equal((await stat(receiptPath(writerIncome))).mode & 0o077,0);
  assert.equal((await readFile(receiptPath(writerIncome),"utf8")).includes(writerIncome.description),false);
  stage="d17c-income-replay-refusal";
  const replay=runFunding(writerIncome);
  assert.equal(replay.status,1);
  assert.match(replay.stdout,/FINANCEW_FUNDING_RESULT blocked:operation-already-attempted/);
  stage="d17c-production-new-account";
  const accountSave=runFunding(writerOpening);
  assert.equal(accountSave.error,undefined);
  const openingStatus=/FINANCEW_FUNDING_RESULT ([a-z0-9:-]+)/.exec(accountSave.stdout)?.[1] || "missing-status";
  if(accountSave.status!==0 || openingStatus!=="committed")
    throw new Error("funding-opening-"+openingStatus+"-exit-"+accountSave.status);
  assert.equal(JSON.parse(await readFile(receiptPath(writerOpening),"utf8")).status,"committed");
  stage="d17c-recovery-blocks-other-modes";
  const unresolved=join(writerHome,".local","state","financew","operations",
    "simulated-unresolved.json");
  await writeFile(unresolved,JSON.stringify({version:1,status:"attempted"})+"\n",
    {mode:0o600,flag:"wx"});
  const blocked=runFunding({...writerIncome,requestId:"4".repeat(32),amountCents:313});
  assert.equal(blocked.status,1);
  assert.match(blocked.stdout,/FINANCEW_FUNDING_RESULT blocked:recovery-needed/);
  await rm(unresolved);
  stage="d17c-independent-readback";
  await startClient("d17c-readback");
  await api.downloadBudget(syncId);
  const incomeRows=await api.getTransactions(accountId,month+"-01",month+"-31");
  assert.equal(incomeRows.filter(t=>t.amount===912
    && t.category===incomeCategoryId
    && t.imported_id==="financew-funding-"+writerIncome.requestId).length,1);
  const allAccounts=await api.getAccounts();
  const created=allAccounts.filter(a=>a.name===writerOpening.accountName);
  assert.equal(created.length,1);
  assert.equal(await api.getAccountBalance(created[0].id),6500);

  // M2: production category create/rename writer against this disposable
  // fictional Actual server, with independently authenticated readback.
  await endClient();
  const runCategory=cmd=>spawnSync(process.execPath,[categoryWriter],{
    encoding:"utf8",timeout:45000,input:JSON.stringify(cmd)+"\\n",
    env:{...process.env,HOME:writerHome,ACTUAL_SERVER_URL:"",
      ACTUAL_SYNC_ID:"",ACTUAL_PASSWORD_FILE:"",
      ACTUAL_SYNC_ID_FILE:"",ACTUAL_ENCRYPTION_PASSWORD_FILE:""}
  });
  const categoryNew={
    mode:"create",requestId:"5".repeat(32),sourceKey,month,
    groupId,categoryId:"",expectedName:"",
    proposedName:"M2 FICTIONAL Utilities"
  };
  stage="m2-category-permit-absent";
  const catLocked=runCategory(categoryNew);
  assert.equal(catLocked.status,1);
  assert.equal(catLocked.stdout.trim(),
    "FINANCEW_CATEGORY_RESULT blocked:writes-disabled");
  stage="m2-category-disposable-permit";
  await writeFile(join(config,"category-writes-enabled"),
    "FINANCEW_CATEGORY_WRITES_APPROVED\\n",{mode:0o600,flag:"wx"});
  stage="m2-category-create";
  const catCreated=runCategory(categoryNew);
  assert.equal(catCreated.error,undefined);
  if(catCreated.status!==0 || catCreated.stdout.trim()!=="FINANCEW_CATEGORY_RESULT committed")
    throw new Error("category-create-test-refused");
  const catRename={
    mode:"rename",requestId:"6".repeat(32),sourceKey,month,
    groupId,categoryId,expectedName:"FICTIONAL Food",
    proposedName:"M2 FICTIONAL Food"
  };
  stage="m2-category-rename";
  const catRenamed=runCategory(catRename);
  assert.equal(catRenamed.error,undefined);
  if(catRenamed.status!==0 || catRenamed.stdout.trim()!=="FINANCEW_CATEGORY_RESULT committed")
    throw new Error("category-rename-test-refused");
  const catReceiptPath=cmd=>join(writerHome,".local","state","financew",
    "operations","category-"+cmd.requestId+".json");
  assert.equal(JSON.parse(await readFile(catReceiptPath(categoryNew),"utf8")).status,"committed");
  assert.equal(JSON.parse(await readFile(catReceiptPath(catRename),"utf8")).status,"committed");
  assert.equal((await stat(catReceiptPath(categoryNew))).mode & 0o077,0);
  assert.ok(!(await readFile(catReceiptPath(categoryNew),"utf8")).includes("Utilities"));
  stage="m2-category-replay-refusal";
  const catReplay=runCategory(categoryNew);
  assert.equal(catReplay.status,1);
  assert.match(catReplay.stdout,/FINANCEW_CATEGORY_RESULT blocked:operation-already-attempted/);
  stage="m2-category-independent-readback";
  await startClient("m2-category-readback");
  await api.downloadBudget(syncId);
  const catAfter=await api.getCategories();
  assert.equal(catAfter.filter(c=>c.name===categoryNew.proposedName
    && c.group_id===groupId).length,1);
  assert.equal(catAfter.filter(c=>c.id===categoryId
    && c.name===catRename.proposedName && c.group_id===groupId).length,1);
  stage="pass";
  process.stdout.write("FINANCEW_M2_DISPOSABLE_PASS category-create/rename/locked/replay/readback\\n");
  process.stdout.write("FINANCEW_D17C_DISPOSABLE_PASS locked/income/opening/replay/recovery/readback\n");
  process.stdout.write("FINANCEW_D17B_DISPOSABLE_PASS income/opening/replay/reconciliation/readback\n");
  process.stdout.write("FINANCEW_D12B_D12C_DISPOSABLE_PASS real-server/gate/allocation/replay/readback\n");
}
try{await main();}
catch(e){
  process.stderr.write("FINANCEW_D12B_DISPOSABLE_FAIL stage="+stage
    +" code="+redactError(e)+" class="+(e?.name||"Error").replace(/[^a-zA-Z]/g,"")
    +" detail="+(/^[a-z0-9:-]{1,75}$/.test(e?.message||"") ? e.message : "redacted")+"\n");
  process.exitCode=1;
}finally{
  try{await endClient();}catch{}
  if(server){
    if(server.exitCode===null)server.kill("SIGTERM");
    for(let n=0;n<50 && server.exitCode===null;n++)await nap(100);
    if(server.exitCode===null)server.kill("SIGKILL");
  }
  if(temporary)await rm(temporary,{recursive:true,force:true});
}
