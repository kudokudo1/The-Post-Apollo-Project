#!/usr/bin/env node
// FinanceW Simple M3d3 // CI-ONLY real Actual 26.10.0, FICTIONAL budget.
// Rehearses the unmodified dormant M3b CLI, never the user's host or budget.
// No production UI integration, operator permit, or recovery-marker cleanup.
import assert from "node:assert/strict";
import {spawn,spawnSync} from "node:child_process";
import {createConnection} from "node:net";
import {createHash} from "node:crypto";
import {existsSync} from "node:fs";
import {mkdtemp,mkdir,writeFile,readFile,open,stat,rm,chmod}
  from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import * as api from "@actual-app/api";
import {takeReadOnlySnapshot} from "./actual_readonly.mjs";
import {executeCategorizedExpense} from "./categorized_expense_guard.mjs";

if(process.env.GITHUB_ACTIONS!=="true"
    ||process.env.CI!=="true"
    ||process.env.FINANCEW_DISPOSABLE_TEST!=="yes")
  throw Error("CI-only-disposable-test");

const here=dirname(fileURLToPath(import.meta.url));
const binary=join(here,"node_modules",".bin","actual-server");
const writer=join(here,"write_categorized_expense.mjs");
const oldWriter=join(here,"write_transaction.mjs");
const host="http://127.0.0.1:5006";
const password="FICTIONAL-M3D3-ONLY-CI-2026";
const date=new Date().toISOString().slice(0,7)+"-01";
const month=date.slice(0,7);
const description="M3D3 FICTIONAL GROCERIES";
let stage="preflight", server=null,temporary=null,clientActive=false,engine=null;
let home="",config="",journalDir="";
const nap=ms=>new Promise(resolve=>setTimeout(resolve,ms));

async function assertPortFree(){
  await new Promise((resolve,reject)=>{
    const socket=createConnection({host:"127.0.0.1",port:5006});
    socket.once("connect",()=>{
      socket.destroy();reject(Error("port-occupied"));
    });
    socket.once("error",e=>{
      socket.destroy();
      e.code==="ECONNREFUSED"?resolve():reject(Error("port-unavailable"));
    });
  });
}
async function startServer(){
  assert.ok(existsSync(binary),"pinned-actual-server-missing");
  await assertPortFree();
  const dir=join(temporary,"server");
  await mkdir(dir,{recursive:true,mode:0o700});
  server=spawn(binary,[],{
    cwd:dir,stdio:"ignore",
    env:{...process.env,HOME:temporary,ACTUAL_DATA_DIR:dir,
      ACTUAL_HOSTNAME:"127.0.0.1",ACTUAL_PORT:"5006",
      ACTUAL_SERVER_FILES:join(dir,"server-files"),
      ACTUAL_USER_FILES:join(dir,"user-files")}
  });
  let ready=false;
  for(let i=0;i<150;i++){
    if(server.exitCode!==null)throw Error("disposable-server-exited");
    try{
      const response=await fetch(host+"/account/needs-bootstrap",
        {signal:AbortSignal.timeout(1000)});
      if(response.ok){
        const result=await response.json();
        assert.equal(result.status,"ok");
        assert.equal(result.data?.bootstrapped,false);
        ready=true;break;
      }
    }catch(e){if(e.name==="AssertionError")throw e;}
    await nap(200);
  }
  if(!ready)throw Error("disposable-server-timeout");
  const response=await fetch(host+"/account/bootstrap",{
    method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({password}),signal:AbortSignal.timeout(8000)
  });
  assert.equal(response.ok,true);
  const result=await response.json();
  assert.equal(result.status,"ok");
}
async function startClient(name){
  const dir=join(temporary,name);
  await mkdir(dir,{recursive:true,mode:0o700});
  engine=await api.init({dataDir:dir,serverURL:host,password});
  clientActive=true;
}
async function endClient(){
  if(clientActive){clientActive=false;await api.shutdown();engine=null;}
}
async function privateFile(name,value){
  await writeFile(join(config,name),value+"\n",{mode:0o600,flag:"wx"});
}
function invoke(target,command){
  return spawnSync(process.execPath,[target],{
    input:JSON.stringify(command)+"\n",
    encoding:"utf8",timeout:60000,
    env:{...process.env,HOME:home,ACTUAL_SERVER_URL:"",
      ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID:"",
      ACTUAL_SYNC_ID_FILE:"",ACTUAL_ENCRYPTION_PASSWORD_FILE:""}
  });
}
function outcome(result,prefix,expected,exitCode){
  assert.equal(result.error,undefined,"writer-process-error");
  assert.equal(result.status,exitCode,"unexpected-writer-exit");
  const status=new RegExp("^"+prefix+" (committed|uncertain|blocked:[a-z0-9-]+)$","m")
    .exec(result.stdout)?.[1];
  assert.equal(status,expected,"unexpected-writer-status");
  assert.equal(result.stderr.includes(password),false);
  assert.equal(result.stderr.includes(description),false);
  return status;
}
function findCategory(budget,categoryId){
  const matches=[];
  for(const group of budget?.categoryGroups||[]){
    if(group && Array.isArray(group.categories) && !group.is_income)
      for(const item of group.categories)
        if(item?.id===categoryId)matches.push({group,item});
  }
  assert.equal(matches.length,1,"unique-expense-category-required");
  return matches[0];
}
function commandFrom(budget,accountId,categoryId,sourceKey,requestId,amount){
  const {item}=findCategory(budget,categoryId);
  for(const key of ["budgeted","balance","spent"])
    assert.equal(Number.isSafeInteger(item[key]),true,"real-category-"+key);
  assert.equal(Number.isSafeInteger(budget.toBudget),true);
  return {
    action:"create-categorized-expense",requestId,sourceKey,accountId,
    month,date,description,amountCents:amount,categoryId,
    expectedCategoryBudgetedCents:item.budgeted,
    expectedCategoryAvailableCents:item.balance,
    expectedCategorySpentCents:item.spent,
    expectedToBudgetCents:budget.toBudget
  };
}
function receipt(id){
  return join(journalDir,"categorized-expense-"+id+".json");
}
async function stageAttempt(command){
  await mkdir(journalDir,{recursive:true,mode:0o700});
  const path=receipt(command.requestId);
  const file=await open(path,"wx",0o600);
  try{
    await file.writeFile(JSON.stringify({
      version:1,status:"attempted",action:"transaction:create-categorized-expense",
      hash:createHash("sha256").update(JSON.stringify(command)).digest("hex"),
      attemptedAt:new Date().toISOString()
    })+"\n");
    await file.sync();
  }finally{await file.close();}
  const directory=await open(journalDir,"r");
  try{await directory.sync();}finally{await directory.close();}
}
async function main(){
  temporary=await mkdtemp(join(tmpdir(),"financew-m3d3-fictional-"));
  await chmod(temporary,0o700);
  home=join(temporary,"writer-home");
  config=join(home,".config","financew");
  journalDir=join(home,".local","state","financew","operations");
  await mkdir(config,{recursive:true,mode:0o700});

  stage="disposable-server";
  await startServer();
  stage="fictional-budget-create";
  await startClient("initial");
  let accountId,groupId,categoryId;
  await api.runImport("M3D3 FICTIONAL Category Budget",async()=>{
    accountId=await api.createAccount({name:"M3D3 FICTIONAL Checking",offbudget:false});
    groupId=await api.createCategoryGroup({name:"M3D3 FICTIONAL Expenses",hidden:false});
    categoryId=await api.createCategory({name:"M3D3 FICTIONAL Groceries",
      group_id:groupId,is_income:false,hidden:false});
  });
  for(const value of [accountId,groupId,categoryId])
    assert.ok(typeof value==="string" && value.length>4);
  await api.sync();
  assert.equal(typeof engine?.send,"function");
  const uploaded=await engine.send("upload-budget");
  assert.equal(uploaded?.error,undefined);
  const remote=await engine.send("get-remote-files");
  assert.ok(Array.isArray(remote) && remote.length===1,"unique-fixture-required");
  const syncId=remote[0]?.groupId;
  assert.ok(typeof syncId==="string" && syncId.length>8);
  await endClient();

  const sourceKey=createHash("sha256").update(host+"\0"+syncId).digest("hex");
  for(const [name,value] of [
    ["actual-server-url",host],
    ["actual-password",password],
    ["actual-sync-id",syncId]
  ])await privateFile(name,value);

  stage="independent-preflight";
  await startClient("preflight");
  await api.downloadBudget(syncId);
  const raw=await api.getBudgetMonth(month);
  const {group,item}=findCategory(raw,categoryId);
  assert.equal(group.is_income,false,"expense-group-required");
  const snapshot=await takeReadOnlySnapshot(api,month);
  assert.equal(snapshot.readOnly,true);
  const projectedGroup=snapshot.categoryGroups.filter(g=>g.id===groupId);
  const projectedCat=snapshot.categories.filter(c=>c.id===categoryId);
  assert.equal(projectedGroup.length,1);
  assert.equal(projectedCat.length,1);
  assert.equal(projectedGroup[0].isIncome,false);
  const visibilityKnown=projectedGroup[0].hidden===false
    &&projectedCat[0].hidden===false;
  assert.ok(projectedGroup[0].hidden===false||projectedGroup[0].hidden===null);
  assert.ok(projectedCat[0].hidden===false||projectedCat[0].hidden===null);
  assert.equal(typeof item.name,"string");
  assert.deepEqual(await api.getTransactions(accountId,month+"-01",month+"-31"),[]);
  const baseCommand=commandFrom(raw,accountId,categoryId,sourceKey,
    "a".repeat(32),-1250);
  await endClient();

  stage="operator-permit-off";
  outcome(invoke(writer,baseCommand),"FINANCEW_CATEGORIZED_EXPENSE_RESULT",
    "blocked:writes-disabled",1);
  assert.equal(existsSync(journalDir),false);
  stage="test-home-permit-on";
  await privateFile("categorized-expense-writes-enabled",
    "FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED");
  stage="source-mismatch-refusal";
  outcome(invoke(writer,{...baseCommand,sourceKey:"b".repeat(64)}),
    "FINANCEW_CATEGORIZED_EXPENSE_RESULT","blocked:budget-source-changed",1);
  assert.equal(existsSync(receipt(baseCommand.requestId)),false);
  stage="stale-budget-refusal";
  outcome(invoke(writer,{...baseCommand,expectedCategoryAvailableCents:
    baseCommand.expectedCategoryAvailableCents+1}),
    "FINANCEW_CATEGORIZED_EXPENSE_RESULT","blocked:stale-budget",1);
  assert.equal(existsSync(receipt(baseCommand.requestId)),false);

  stage="real-production-cli-create";
  outcome(invoke(writer,baseCommand),"FINANCEW_CATEGORIZED_EXPENSE_RESULT",
    "committed",0);
  const receiptPath=receipt(baseCommand.requestId);
  const receiptBody=await readFile(receiptPath,"utf8");
  const savedReceipt=JSON.parse(receiptBody);
  assert.equal(savedReceipt.status,"committed");
  assert.equal(savedReceipt.action,"transaction:create-categorized-expense");
  assert.equal((await stat(receiptPath)).mode&0o077,0);
  for(const secret of [password,sourceKey,accountId,categoryId,description])
    assert.equal(receiptBody.includes(secret),false,"private-receipt-leak");

  stage="same-request-replay";
  outcome(invoke(writer,baseCommand),"FINANCEW_CATEGORIZED_EXPENSE_RESULT",
    "blocked:operation-already-attempted",1);

  stage="independent-fresh-readback";
  await startClient("fresh-readback");
  await api.downloadBudget(syncId);
  const rows=await api.getTransactions(accountId,month+"-01",month+"-31");
  const importedId="financew-cat-"+baseCommand.requestId;
  const matches=rows.filter(t=>t.imported_id===importedId);
  assert.equal(matches.length,1,"exactly-one-imported-transaction");
  const found=matches[0];
  assert.equal(found.account,accountId);
  assert.equal(found.category,categoryId,"category-persists");
  assert.equal(found.amount,baseCommand.amountCents);
  assert.equal(found.date,date);
  assert.equal(found.payee_name===description||typeof found.payee==="string",true);
  assert.equal(rows.filter(t=>t.id===found.id).length,1);
  const after=await api.getBudgetMonth(month);
  assert.equal(findCategory(after,categoryId).item.id,categoryId);
  const duplicateCommand=commandFrom(after,accountId,categoryId,sourceKey,
    "b".repeat(32),baseCommand.amountCents);
  await endClient();

  stage="same-day-amount-duplicate";
  outcome(invoke(writer,duplicateCommand),"FINANCEW_CATEGORIZED_EXPENSE_RESULT",
    "blocked:possible-duplicate",1);
  assert.equal(existsSync(receipt(duplicateCommand.requestId)),false);

  // Inject one post-attempt sync failure around the REAL Actual engine.
  // This is a disposable policy seam, not a production CLI fault injection.
  stage="injected-uncertain-real-api";
  await startClient("uncertain-client");
  await api.downloadBudget(syncId);
  const current=await api.getBudgetMonth(month);
  const uncertain=commandFrom(current,accountId,categoryId,sourceKey,
    "c".repeat(32),-837);
  let adds=0,syncs=0,attempts=0;
  const facade={
    getAccounts:()=>api.getAccounts(),
    getBudgetMonth:m=>api.getBudgetMonth(m),
    getTransactions:(id,start,end)=>api.getTransactions(id,start,end),
    async addTransactions(...args){
      adds++;
      return api.addTransactions(...args);
    },
    async sync(){
      syncs++;
      throw Error("injected-disposable-post-add-sync-uncertain");
    }
  };
  await assert.rejects(
    ()=>executeCategorizedExpense({
      api:facade,input:uncertain,
      recordAttempt:async()=>{
        attempts++;
        await stageAttempt(uncertain);
      }
    }),/injected-disposable-post-add-sync-uncertain/);
  assert.equal(attempts,1,"attempt-must-precede-real-Actual-add");
  assert.equal(adds,1,"no-automatic-add-retry");
  assert.equal(syncs,1,"no-automatic-sync-retry");
  assert.equal(JSON.parse(await readFile(receipt(uncertain.requestId),"utf8")).status,
    "attempted");
  await endClient();

  stage="unresolved-journal-refuses-all-future-writes";
  const subsequent={...duplicateCommand,requestId:"d".repeat(32),
    amountCents:-941};
  outcome(invoke(writer,subsequent),"FINANCEW_CATEGORIZED_EXPENSE_RESULT",
    "blocked:recovery-needed",1);
  assert.equal(existsSync(receipt(subsequent.requestId)),false);
  // Shared journal prevents the old D9 writer from bypassing an unknown M3b
  // transaction even when D9 has its own independent private test permit.
  await privateFile("transaction-writes-enabled",
    "FINANCEW_TRANSACTION_WRITES_APPROVED");
  outcome(invoke(oldWriter,{
    action:"create",requestId:"e".repeat(32),sourceKey,accountId,
    month,date,description:"M3D3 FICTIONAL SECOND EXPENSE",amountCents:-211
  }),"FINANCEW_TRANSACTION_RESULT","blocked:recovery-needed",1);

  stage="pass";
  process.stdout.write("FINANCEW_M3D3_DISPOSABLE_PASS "+
    "real-cli-create/category-persist/fresh-readback/lock/replay/"+
    "duplicate/stale/uncertain-no-retry/cross-writer-recovery "+
    "visibility="+(visibilityKnown?"known":"unknown")+"\n");
}
try{
  await main();
}catch(error){
  process.stderr.write("FINANCEW_M3D3_DISPOSABLE_FAIL stage="+stage
    +" class="+(error?.code||error?.name||"Error")
    +" detail="+String(error?.message||"none")
      .replaceAll(password,"[redacted]")
      .replaceAll(description,"[redacted]")
      .replace(/[^A-Za-z0-9 ().:_-]/g,"?").slice(0,160)+"\n");
  process.exitCode=1;
}finally{
  try{await endClient();}catch{}
  if(server){
    if(server.exitCode===null)server.kill("SIGTERM");
    for(let i=0;i<50&&server.exitCode===null;i++)await nap(100);
    if(server.exitCode===null)server.kill("SIGKILL");
  }
  if(temporary)await rm(temporary,{recursive:true,force:true});
}
