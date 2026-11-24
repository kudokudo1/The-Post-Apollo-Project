#!/usr/bin/env node
// FinanceW Simple M3d4 // deterministic process SIGKILL at two checkpoints.
// CI-ONLY; tests a REAL 26.10.0 Actual server and fictional temp budget.
// The real CLI is invoked with a TEST-ONLY ESM loader that pauses its guard.
// Neither production source nor the operator's host/files/permits are edited.
import assert from "node:assert/strict";
import {spawn,spawnSync} from "node:child_process";
import {createConnection} from "node:net";
import {createHash} from "node:crypto";
import {existsSync} from "node:fs";
import {mkdtemp,mkdir,readFile,writeFile,rm,stat,unlink,chmod}
  from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import * as api from "@actual-app/api";

if(process.env.GITHUB_ACTIONS!=="true" || process.env.CI!=="true"
    || process.env.FINANCEW_DISPOSABLE_TEST!=="yes")
  throw new Error("CI-only-disposable-test");

const here=dirname(fileURLToPath(import.meta.url));
const binary=join(here,"node_modules",".bin","actual-server");
const writer=join(here,"write_categorized_expense.mjs");
const legacyWriter=join(here,"write_transaction.mjs");
const loader=join(here,"../../tests/finance/fixtures/simple_m3d4_sigkill_loader.mjs");
const serverURL="http://127.0.0.1:5006";
const password="M3D4-FICTIONAL-CI-ONLY-2026";
const month=new Date().toISOString().slice(0,7);
const date=month+"-01";
let stage="preflight",root=null,server=null,clientActive=false,engine=null;
const nap=ms=>new Promise(resolve=>setTimeout(resolve,ms));

async function portFree(){
  await new Promise((resolve,reject)=>{
    const socket=createConnection({host:"127.0.0.1",port:5006});
    socket.once("connect",()=>{
      socket.destroy();reject(new Error("port-5006-occupied"));
    });
    socket.once("error",e=>{
      socket.destroy();
      e.code==="ECONNREFUSED"?resolve():reject(new Error("port-unavailable"));
    });
  });
}
async function createServer(){
  assert.ok(existsSync(binary),"pinned-actual-server-not-installed");
  await portFree();
  const dir=join(root,"server");
  await mkdir(dir,{recursive:true,mode:0o700});
  server=spawn(binary,[],{
    cwd:dir,stdio:"ignore",env:{...process.env,HOME:root,
      ACTUAL_DATA_DIR:dir,ACTUAL_HOSTNAME:"127.0.0.1",ACTUAL_PORT:"5006",
      ACTUAL_SERVER_FILES:join(dir,"server-files"),
      ACTUAL_USER_FILES:join(dir,"user-files")}
  });
  let online=false;
  for(let i=0;i<150;i++){
    if(server.exitCode!==null)throw new Error("server-exited");
    try{
      const response=await fetch(serverURL+"/account/needs-bootstrap",
        {signal:AbortSignal.timeout(1200)});
      if(response.ok){
        const result=await response.json();
        assert.equal(result.status,"ok");
        assert.equal(result.data?.bootstrapped,false);
        online=true;break;
      }
    }catch(e){if(e.name==="AssertionError")throw e;}
    await nap(200);
  }
  if(!online)throw new Error("disposable-server-start-timeout");
  const response=await fetch(serverURL+"/account/bootstrap",{
    method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({password}),signal:AbortSignal.timeout(8000)
  });
  assert.equal(response.ok,true);
  assert.equal((await response.json()).status,"ok");
}
async function startClient(name){
  const dir=join(root,name);
  await mkdir(dir,{recursive:true,mode:0o700});
  engine=await api.init({dataDir:dir,serverURL,password});
  clientActive=true;
}
async function endClient(){
  if(clientActive){
    clientActive=false;
    await api.shutdown();
    engine=null;
  }
}
async function putPrivate(path,value){
  await writeFile(path,value+"\n",{flag:"wx",mode:0o600});
}
async function createHome(label,syncId){
  const home=join(root,label);
  const config=join(home,".config","financew");
  await mkdir(config,{recursive:true,mode:0o700});
  await putPrivate(join(config,"actual-server-url"),serverURL);
  await putPrivate(join(config,"actual-password"),password);
  await putPrivate(join(config,"actual-sync-id"),syncId);
  // ONLY the disposable CI HOME is permitted. No live operator permit.
  await putPrivate(join(config,"categorized-expense-writes-enabled"),
    "FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED");
  return {home,config,journalDir:join(home,".local","state","financew","operations"),
    barrier:join(home,"m3d4-barrier")};
}
function targetCategory(budget,categoryId){
  const found=[];
  for(const group of budget?.categoryGroups||[]){
    if(group && group.is_income===false && Array.isArray(group.categories))
      for(const row of group.categories){
        if(row?.id===categoryId)found.push(row);
      }
  }
  assert.equal(found.length,1,"unique-real-category");
  return found[0];
}
function makeCommand({budget,accountId,categoryId,sourceKey,requestId,amount}){
  const cat=targetCategory(budget,categoryId);
  for(const field of ["budgeted","balance","spent"])
    assert.equal(Number.isSafeInteger(cat[field]),true);
  assert.equal(Number.isSafeInteger(budget.toBudget),true);
  return {
    action:"create-categorized-expense",requestId,sourceKey,
    accountId,month,date,
    description:"M3D4 FICTIONAL FOOD",amountCents:amount,categoryId,
    expectedCategoryBudgetedCents:cat.budgeted,
    expectedCategoryAvailableCents:cat.balance,
    expectedCategorySpentCents:cat.spent,
    expectedToBudgetCents:budget.toBudget
  };
}
async function waitBarrier(child,path,point){
  for(let i=0;i<600;i++){
    if(existsSync(path)){
      assert.equal((await readFile(path,"utf8")).trim(),point);
      assert.equal(child.exitCode,null,"child-exited-before-SIGKILL");
      assert.equal(child.signalCode,null,"child-already-signaled");
      return;
    }
    if(child.exitCode!==null || child.signalCode!==null)
      throw new Error("writer-exited-before-checkpoint");
    await nap(100);
  }
  throw new Error("writer-checkpoint-timeout");
}
async function invokeAndKill({point,command,fixture}){
  const child=spawn(process.execPath,
    ["--experimental-loader",loader,writer],{
      stdio:["pipe","ignore","ignore"],env:{...process.env,
        HOME:fixture.home,NODE_OPTIONS:"",
        ACTUAL_SERVER_URL:"",ACTUAL_SYNC_ID:"",ACTUAL_SYNC_ID_FILE:"",
        ACTUAL_PASSWORD_FILE:"",ACTUAL_ENCRYPTION_PASSWORD_FILE:"",
        FINANCEW_M3D4_POINT:point,FINANCEW_M3D4_BARRIER:fixture.barrier}
    });
  const exited=new Promise((resolve,reject)=>{
    child.once("error",reject);
    child.once("exit",(code,signal)=>resolve({code,signal}));
  });
  child.stdin.end(JSON.stringify(command)+"\n");
  try{
    await waitBarrier(child,fixture.barrier,point);
    const journal=join(fixture.journalDir,
      "categorized-expense-"+command.requestId+".json");
    const lock=join(fixture.journalDir,".write-lock");
    assert.equal(existsSync(lock),true,"held-shared-lock-required");
    assert.equal(existsSync(journal),true,"attempted-journal-required");
    const receipt=JSON.parse(await readFile(journal,"utf8"));
    assert.equal(receipt.status,"attempted");
    assert.equal(receipt.action,"transaction:create-categorized-expense");
    assert.equal((await stat(journal)).mode&0o077,0);
    assert.equal((await stat(lock)).mode&0o077,0);
    // The loader's barrier appears only AFTER recordAttempt has durably
    // fsynced both the journal and its directory (or after a real add).
    assert.equal(child.kill("SIGKILL"),true);
    const outcome=await exited;
    assert.equal(outcome.signal,"SIGKILL");
    assert.equal(existsSync(journal),true,"SIGKILL-preserved-attempted-journal");
    assert.equal(JSON.parse(await readFile(journal,"utf8")).status,"attempted");
    assert.equal(existsSync(lock),true,"SIGKILL-preserved-stale-lock");
    return {journal,lock};
  }finally{
    if(child.exitCode===null && child.signalCode===null){
      child.kill("SIGKILL");
      await exited.catch(()=>{});
    }
  }
}
function invokePlain(path,home,cmd){
  return spawnSync(process.execPath,[path],{
    input:JSON.stringify(cmd)+"\n",encoding:"utf8",timeout:45000,
    env:{...process.env,HOME:home,NODE_OPTIONS:"",
      ACTUAL_SERVER_URL:"",ACTUAL_SYNC_ID:"",ACTUAL_SYNC_ID_FILE:"",
      ACTUAL_PASSWORD_FILE:"",ACTUAL_ENCRYPTION_PASSWORD_FILE:""}
  });
}
function expectBlocked(result,prefix,reason){
  assert.equal(result.error,undefined,"subsequent-process-error");
  assert.equal(result.status,1,"unsafe-write-after-kill");
  assert.equal(result.stdout.trim(),prefix+" blocked:"+reason);
}
async function exerciseRecovery({fixture,command,markers,sourceKey,accountId}){
  const different={...command,requestId:"f".repeat(32),amountCents:-211};
  const catResult="FINANCEW_CATEGORIZED_EXPENSE_RESULT";
  const legacyResult="FINANCEW_TRANSACTION_RESULT";
  // A killed process does not execute its finally{}: stale lock must refuse.
  expectBlocked(invokePlain(writer,fixture.home,different),
    catResult,"write-in-progress-or-recovery-needed");
  assert.equal(existsSync(join(fixture.journalDir,
    "categorized-expense-"+different.requestId+".json")),false);
  // Artificial disposal of ONLY the stale lock in CI temporary HOME probes
  // the independent journal gate. NEVER do this to a live finance directory.
  await unlink(markers.lock);
  assert.equal(existsSync(markers.journal),true,"original-journal-retained");
  expectBlocked(invokePlain(writer,fixture.home,different),
    catResult,"recovery-needed");
  await putPrivate(join(fixture.config,"transaction-writes-enabled"),
    "FINANCEW_TRANSACTION_WRITES_APPROVED");
  const legacy={
    action:"create",requestId:"e".repeat(32),sourceKey,accountId,month,date,
    description:"M3D4 FICTIONAL OTHER",amountCents:-376
  };
  expectBlocked(invokePlain(legacyWriter,fixture.home,legacy),
    legacyResult,"recovery-needed");
  assert.equal(JSON.parse(await readFile(markers.journal,"utf8")).status,"attempted");
}
async function main(){
  root=await mkdtemp(join(tmpdir(),"financew-m3d4-sigkill-fictional-"));
  await chmod(root,0o700);
  stage="disposable-server";
  await createServer();

  stage="create-fictional-budget";
  await startClient("initial");
  let accountId,groupId,categoryId;
  await api.runImport("M3D4 FICTIONAL Kill Budget",async()=>{
    accountId=await api.createAccount({
      name:"M3D4 FICTIONAL Checking",offbudget:false});
    groupId=await api.createCategoryGroup({
      name:"M3D4 FICTIONAL Expenses",hidden:false});
    categoryId=await api.createCategory({
      name:"M3D4 FICTIONAL Food",group_id:groupId,
      is_income:false,hidden:false});
  });
  for(const id of [accountId,groupId,categoryId])
    assert.ok(typeof id==="string" && id.length>4);
  await api.sync();
  assert.equal(typeof engine?.send,"function");
  assert.equal((await engine.send("upload-budget"))?.error,undefined);
  const files=await engine.send("get-remote-files");
  assert.ok(Array.isArray(files) && files.length===1);
  const syncId=files[0]?.groupId;
  assert.ok(typeof syncId==="string" && syncId.length>8);
  await endClient();
  const sourceKey=createHash("sha256")
    .update(serverURL+"\0"+syncId).digest("hex");

  for(const [point,requestId,amount] of [
    ["after-attempt","a".repeat(32),-1250],
    ["after-add","b".repeat(32),-837]
  ]){
    stage=point+"-fresh-preflight";
    await startClient("fresh-"+point);
    await api.downloadBudget(syncId);
    const budget=await api.getBudgetMonth(month);
    const command=makeCommand({budget,accountId,categoryId,sourceKey,
      requestId,amount});
    await endClient();

    const fixture=await createHome("home-"+point,syncId);
    stage=point+"-process-SIGKILL";
    const markers=await invokeAndKill({point,command,fixture});
    stage=point+"-recovery-refusals";
    await exerciseRecovery({fixture,command,markers,sourceKey,accountId});

    stage=point+"-independent-readback";
    await startClient("verify-"+point);
    await api.downloadBudget(syncId);
    const rows=await api.getTransactions(accountId,month+"-01",month+"-31");
    const matches=rows.filter(x=>x.imported_id==="financew-cat-"+requestId);
    // Before mutation: no remote transaction. After add but before sync:
    // whether the transaction is present is NOT a claim of commit.
    if(point==="after-attempt")assert.equal(matches.length,0);
    else assert.ok(matches.length<=1);
    await endClient();
  }
  stage="PASS";
  process.stdout.write("FINANCEW_M3D4_SIGKILL_PASS "+
    "after-attempt/after-add/stale-lock/attempted-journal/"+
    "cross-writer-recovery/no-auto-retry\n");
}
try{
  await main();
}catch(error){
  process.stderr.write("FINANCEW_M3D4_SIGKILL_FAIL stage="+stage+
    " class="+(error?.code||error?.name||"Error")+
    " detail="+String(error?.message||"none")
      .replaceAll(password,"[redacted]")
      .replace(/[^A-Za-z0-9 ():._-]/g,"?").slice(0,120)+"\n");
  process.exitCode=1;
}finally{
  try{await endClient();}catch{}
  if(server){
    if(server.exitCode===null)server.kill("SIGTERM");
    for(let i=0;i<50&&server.exitCode===null;i++)await nap(100);
    if(server.exitCode===null)server.kill("SIGKILL");
  }
  if(root)await rm(root,{recursive:true,force:true});
}
