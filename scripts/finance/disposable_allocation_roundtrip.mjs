#!/usr/bin/env node
// D12b: real Actual engine, isolated fictional budget, CI ONLY.
// This is an integration test for allocation_guard.mjs with an injected
// recordAttempt spy. It is NOT a production writer and has no local activation.
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {createConnection} from "node:net";
import {existsSync} from "node:fs";
import {mkdtemp,mkdir,rm,chmod} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
import * as api from "@actual-app/api";
import {executeAllocation,preflightAllocation,AllocationRefusal}
  from "./allocation_guard.mjs";

if(process.env.GITHUB_ACTIONS!=="true" || process.env.CI!=="true"
    || process.env.FINANCEW_DISPOSABLE_TEST!=="yes")
  throw new Error("CI-only-disposable-test");

const here=dirname(fileURLToPath(import.meta.url));
const binary=join(here,"node_modules",".bin","actual-server");
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
  stage="fictional-income";
  const acknowledgment=await api.addTransactions(accountId,[{
    id:"a1111111-aaaa-4aaa-8aaa-aaaaaaaaaaaa",date,amount:10000,
    payee_name:"FICTIONAL INCOME",cleared:false
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
  const before=await api.getBudgetMonth(month);
  assert.equal(findCategory(before,categoryId).length,1);
  const category=findCategory(before,categoryId)[0];
  assert.ok(Number.isSafeInteger(before.toBudget));
  assert.ok(Number.isSafeInteger(category.budgeted));
  assert.ok(Number.isSafeInteger(category.balance));
  // Never assume initial envelope state or amount available. Derive the
  // safe increase from actual real-engine values in the fictional budget.
  const capacity=Math.min(before.toBudget,99999999999-category.budgeted);
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
  stage="pass";
  process.stdout.write("FINANCEW_D12B_DISPOSABLE_PASS allocated/synced/readback/stale-guard\n");
}
try{await main();}
catch(e){
  process.stderr.write("FINANCEW_D12B_DISPOSABLE_FAIL stage="+stage
    +" code="+redactError(e)+" class="+(e?.name||"Error").replace(/[^a-zA-Z]/g,"")+"\n");
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
