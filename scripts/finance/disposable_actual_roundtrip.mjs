#!/usr/bin/env node
// D9: REAL Actual sync-server/API, FICTIONAL isolated runner budget ONLY.
// Deliberately refuses execution outside a GitHub Actions opt-in test job.
// It does not connect to any service other than its own 127.0.0.1:5006.
import assert from "node:assert/strict";
import {spawn,spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {createConnection} from "node:net";
import {existsSync} from "node:fs";
import {mkdtemp,mkdir,writeFile,readFile,rm,chmod} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import * as api from "@actual-app/api";

if (process.env.GITHUB_ACTIONS !== "true"
    || process.env.CI !== "true"
    || process.env.FINANCEW_DISPOSABLE_TEST !== "yes")
  throw new Error("CI-only-disposable-test");

const here=dirname(fileURLToPath(import.meta.url));
const writer=join(here,"write_transaction.mjs");
const reader=join(here,"read_budget.mjs");
const binary=join(here,"node_modules",".bin","actual-server");
const serverURL="http://127.0.0.1:5006";
const password="FICTIONAL-RUNNER-PASSWORD-ONLY-12345";
const month="2026-10";
const day=month+"-22";
const editedDay=month+"-23";
const description="FICTIONAL FinanceW Test Cafe";
let stage="preflight";
let server=null;
let apiActive=false;
let temporary=null;

function sleep(ms) {return new Promise(resolve=>setTimeout(resolve,ms));}

function assertPortFree() {
  return new Promise((resolve,reject)=>{
    const socket=createConnection({host:"127.0.0.1",port:5006});
    socket.once("connect",()=>{
      socket.destroy();
      reject(new Error("port-5006-already-occupied"));
    });
    socket.once("error",err=>{
      socket.destroy();
      if(err.code==="ECONNREFUSED") resolve();
      else reject(new Error("port-check-refused"));
    });
  });
}

async function waitForServer() {
  for (let attempt=0;attempt<150;attempt++) {
    if (server.exitCode !== null)
      throw new Error("disposable-server-exited");
    try {
      const response=await fetch(serverURL+"/account/needs-bootstrap",
        {signal:AbortSignal.timeout(1200)});
      if (response.ok) {
        const result=await response.json();
        assert.equal(result.status,"ok");
        assert.equal(result.data?.bootstrapped,false);
        return;
      }
    } catch (error) {
      if (error.name==="AssertionError") throw error;
    }
    await sleep(200);
  }
  throw new Error("disposable-server-start-timeout");
}

async function createFixtureServer(home) {
  if (!existsSync(binary)) throw new Error("pinned-actual-server-not-installed");
  await assertPortFree();
  const serverData=join(home,"server");
  await mkdir(serverData,{recursive:true,mode:0o700});
  server=spawn(binary,[],{
    cwd:serverData,stdio:"ignore",env:{
      ...process.env,
      ACTUAL_DATA_DIR:serverData,
      ACTUAL_HOSTNAME:"127.0.0.1",
      ACTUAL_PORT:"5006",
      ACTUAL_SERVER_FILES:join(serverData,"server-files"),
      ACTUAL_USER_FILES:join(serverData,"user-files")
    }
  });
  await waitForServer();
  const response=await fetch(serverURL+"/account/bootstrap",{
    method:"POST",
    headers:{"content-type":"application/json"},
    body:JSON.stringify({password}),
    signal:AbortSignal.timeout(8000)
  });
  const result=await response.json();
  assert.equal(response.ok,true);
  assert.equal(result.status,"ok");
}

async function writePrivate(path,value) {
  await writeFile(path,value+"\n",{mode:0o600,flag:"wx"});
}

function runWriter(home,cmd) {
  return spawnSync(process.execPath,[writer],{
    input:JSON.stringify(cmd)+"\n",encoding:"utf8",timeout:45000,
    env:{...process.env,HOME:home,
      ACTUAL_SERVER_URL:"",ACTUAL_SYNC_ID:"",
      ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID_FILE:"",
      FINANCEW_DISPOSABLE_TEST:"yes"}
  });
}
function assertOutcome(result,expected,code=0) {
  assert.equal(result.error,undefined,"Writer process error");
  const observed=/FINANCEW_TRANSACTION_RESULT ([a-z0-9:-]+)/.exec(result.stdout)?.[1]
    || "no-status";
  if (result.status !== code || observed !== expected)
    throw new Error("writer-"+observed);
  assert.equal(result.stderr.includes(description),false);
}

async function startApi(folder) {
  await mkdir(folder,{recursive:true,mode:0o700});
  await api.init({dataDir:folder,serverURL,password});
  apiActive=true;
}
async function endApi() {
  if (apiActive) {
    apiActive=false;
    await api.shutdown();
  }
}

async function run() {
  temporary=await mkdtemp(join(tmpdir(),"financew-disposable-actual-"));
  await chmod(temporary,0o700);
  const home=join(temporary,"fictional-home");
  const config=join(home,".config","financew");
  await mkdir(config,{recursive:true,mode:0o700});

  stage="isolated-server";
  await createFixtureServer(temporary);

  stage="create-fictional-budget";
  await startApi(join(temporary,"client-initial"));
  let accountId;
  await api.runImport("FinanceW D9 Fictional Budget",async()=>{
    accountId=await api.createAccount({
      name:"FICTIONAL Checking",offbudget:false
    });
  });
  assert.equal(typeof accountId,"string");
  await api.sync();
  const budgets=await api.getBudgets();
  const id=budgets.find(x=>typeof x.cloudFileId==="string"
                           && x.cloudFileId.length>8)?.cloudFileId;
  assert.ok(id,"Fictional upload lacked a Sync ID");
  await endApi();

  stage="private-test-credentials";
  await writePrivate(join(config,"transaction-writes-enabled"),
    "FINANCEW_TRANSACTION_WRITES_APPROVED");
  await writePrivate(join(config,"actual-server-url"),serverURL);
  await writePrivate(join(config,"actual-password"),password);
  await writePrivate(join(config,"actual-sync-id"),id);
  const sourceKey=createHash("sha256")
    .update(serverURL+"\0"+id).digest("hex");

  stage="real-create";
  const created={
    action:"create",requestId:"a".repeat(32),
    sourceKey,accountId,month,date:day,
    description,amountCents:-400
  };
  assertOutcome(runWriter(home,created),"committed");
  const firstJournal=join(home,".local","state","financew","operations",
    created.requestId+".json");
  assert.equal(JSON.parse(await readFile(firstJournal,"utf8")).status,
    "committed");

  stage="fresh-client-readback";
  await startApi(join(temporary,"client-verify-1"));
  await api.downloadBudget(id);
  let rows=await api.getTransactions(accountId,month+"-01",month+"-31");
  assert.equal(rows.filter(x=>x.amount===-400 && x.date===day).length,1);
  const transactionId=rows.find(x=>x.amount===-400 && x.date===day)?.id;
  assert.ok(transactionId);
  await endApi();

  stage="duplicate-refusal";
  assertOutcome(runWriter(home,{
    ...created,requestId:"b".repeat(32)
  }),"blocked:possible-duplicate",1);

  stage="real-edit";
  assertOutcome(runWriter(home,{
    ...created,action:"update",requestId:"c".repeat(32),
    transactionId,
    original:{date:day,amountCents:-400},
    date:editedDay,amountCents:-600
  }),"committed");

  stage="fresh-readonly-probe";
  const probe=spawnSync(process.execPath,[reader],{
    encoding:"utf8",timeout:45000,
    env:{...process.env,HOME:home,ACTUAL_SERVER_URL:"",
      ACTUAL_SYNC_ID:"",ACTUAL_SYNC_ID_FILE:"",
      ACTUAL_PASSWORD_FILE:"",FINANCEW_MONTH:month}
  });
  assert.equal(probe.error,undefined);
  assert.equal(probe.status,0,"Fresh read-only probe failed");
  const snapshotLine=probe.stdout.split("\n")
    .find(x=>x.startsWith('{"schemaVersion":'));
  assert.ok(snapshotLine,"No authenticated snapshot");
  const snap=JSON.parse(snapshotLine);
  assert.equal(snap.sourceKey,sourceKey);
  assert.ok(snap.accounts.some(x=>x.id===accountId && x.balanceCents===-600));
  assert.ok(snap.transactions.some(x=>x.id===transactionId
    && x.date===editedDay && x.amountCents===-600));
  assert.equal(snap.transactions.filter(x=>x.id===transactionId).length,1);

  stage="passed";
  process.stdout.write(
    "FINANCEW_DISPOSABLE_ACTUAL_PASS create/edit/sync/fresh-read/duplicate/receipt\n");
}

try {
  await run();
} catch (error) {
  // Real money never enters this test; only the stage and error class
  // are emitted, not payloads, credential contents or budget details.
  process.stderr.write("FINANCEW_DISPOSABLE_ACTUAL_FAIL stage="+stage
    +" class="+(error?.code || error?.name || "Error")
    +" detail="+(/^[a-z0-9:-]+$/.test(error?.message || "")
      ? error.message : "none")+"\n");
  process.exitCode=1;
} finally {
  try {await endApi();} catch {}
  if (server) {
    const running=server.exitCode===null;
    if (running) server.kill("SIGTERM");
    for(let i=0;i<50 && server.exitCode===null;i++) await sleep(100);
    if (server.exitCode===null) server.kill("SIGKILL");
  }
  if (temporary) await rm(temporary,{recursive:true,force:true});
}
