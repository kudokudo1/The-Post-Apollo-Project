import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,statSync,rmSync}
  from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";

const writer=fileURLToPath(new URL("../../scripts/finance/write_transaction.mjs",import.meta.url));
const register=fileURLToPath(new URL("./fixtures/write_cli_register.mjs",import.meta.url));
const syncId="fictional-sync-123";
const sourceKey=createHash("sha256")
  .update("http://127.0.0.1:5006\0"+syncId).digest("hex");
const accountId="fictional-123";
function fixture(transactions=[]) {
  const home=mkdtempSync(join(tmpdir(),"financew-cli-fictional-"));
  const config=join(home,".config","financew");
  mkdirSync(config,{recursive:true,mode:0o700});
  for (const [name,value] of [
    ["transaction-writes-enabled","FINANCEW_TRANSACTION_WRITES_APPROVED"],
    ["actual-server-url","http://127.0.0.1:5006"],
    ["actual-password","fictional-password"],
    ["actual-sync-id",syncId]
  ]) writeFileSync(join(config,name),value+"\n",{mode:0o600});
  const ledger=join(home,"fictional-ledger.json");
  writeFileSync(ledger,JSON.stringify({
    accounts:[{id:accountId,offbudget:false,closed:false}],
    transactions,events:[]
  }),{mode:0o600});
  return {home,ledger,journal:join(home,".local","state","financew","operations")};
}
function command(overrides={}) {return {
  action:"create",requestId:"c".repeat(32),sourceKey,accountId,
  month:"2026-10",date:"2026-10-22",description:"Fake Test Shop",
  amountCents:-400,...overrides
};}
function run(f,cmd,failStage="") {
  return spawnSync(process.execPath,["--import",register,writer],{
    input:JSON.stringify(cmd)+"\n",encoding:"utf8",timeout:15000,
    env:{...process.env,HOME:f.home,ACTUAL_SERVER_URL:"",
      ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID:"",ACTUAL_SYNC_ID_FILE:"",
      FINANCEW_FAKE_LEDGER_PATH:f.ledger,FINANCEW_FAKE_FAIL_STAGE:failStage}
  });
}
function data(f) {return JSON.parse(readFileSync(f.ledger,"utf8"));}
function cleanup(f) {rmSync(f.home,{recursive:true,force:true});}
function journal(f,id) {return join(f.journal,id+".json");}

test("fictional create commits once, writes a private receipt, and rejects repeats",()=>{
  const f=fixture();
  try {
    const cmd=command();
    const result=run(f,cmd);
    assert.equal(result.status,0,result.stderr+result.stdout);
    assert.match(result.stdout,/FINANCEW_TRANSACTION_RESULT committed/);
    assert.deepEqual(data(f).events,["add","sync"]);
    assert.equal(data(f).transactions.length,1);
    assert.equal(JSON.parse(readFileSync(journal(f,cmd.requestId),"utf8")).status,"committed");
    assert.equal(statSync(journal(f,cmd.requestId)).mode & 0o077,0);
    assert.ok(!readFileSync(journal(f,cmd.requestId),"utf8").includes(cmd.description));
    assert.ok(!result.stdout.includes(cmd.description));
    const duplicate=run(f,command({requestId:"d".repeat(32)}));
    assert.notEqual(duplicate.status,0);
    assert.match(duplicate.stdout,/blocked:possible-duplicate/);
    assert.equal(data(f).transactions.length,1);
    assert.deepEqual(data(f).events,["add","sync"]);
    const second=run(f,command({requestId:"e".repeat(32),date:"2026-10-24",amountCents:-200}));
    assert.equal(second.status,0,second.stderr+second.stdout);
    assert.match(second.stdout,/FINANCEW_TRANSACTION_RESULT committed/);
    assert.equal(data(f).transactions.length,2);
    assert.deepEqual(data(f).events,["add","sync","add","sync"]);
  } finally {cleanup(f);}
});

test("a changed source key blocks before importing Actual or recording a mutation",()=>{
  const f=fixture();
  try {
    const result=run(f,command({sourceKey:"a".repeat(64)}));
    assert.notEqual(result.status,0);
    assert.match(result.stdout,/blocked:budget-source-changed/);
    assert.deepEqual(data(f).events,[]);
    assert.equal(data(f).transactions.length,0);
  } finally {cleanup(f);}
});

test("post-mutation sync failure is uncertain and later writes fail closed",()=>{
  const f=fixture();
  try {
    const cmd=command();
    const result=run(f,cmd,"sync");
    assert.match(result.stdout,/FINANCEW_TRANSACTION_RESULT uncertain/);
    assert.deepEqual(data(f).events,["add","sync"]);
    assert.equal(data(f).transactions.length,1);
    assert.equal(JSON.parse(readFileSync(journal(f,cmd.requestId),"utf8")).status,"attempted");
    const retry=run(f,command({requestId:"d".repeat(32),date:"2026-10-23",amountCents:-500}));
    assert.notEqual(retry.status,0);
    assert.match(retry.stdout,/blocked:recovery-needed/);
    assert.deepEqual(data(f).events,["add","sync"]);
    assert.equal(data(f).transactions.length,1);
  } finally {cleanup(f);}
});

test("fictional edit preserves payee and changes only date and amount",()=>{
  const existing={id:"transaction-123",account:accountId,date:"2026-10-22",
    amount:-400,payee:"Fictional Original"};
  const f=fixture([existing]);
  try {
    const cmd=command({action:"update",transactionId:existing.id,
      original:{date:existing.date,amountCents:existing.amount},
      date:"2026-10-23",amountCents:-600});
    const result=run(f,cmd);
    assert.equal(result.status,0,result.stderr+result.stdout);
    assert.match(result.stdout,/FINANCEW_TRANSACTION_RESULT committed/);
    assert.deepEqual(data(f).events,["update","sync"]);
    assert.deepEqual(data(f).transactions,[{...existing,date:"2026-10-23",amount:-600}]);
  } finally {cleanup(f);}
});

test("old imported transaction cannot be edited",()=>{
  const existing={id:"transaction-123",account:accountId,date:"2026-10-22",
    amount:-400,imported_id:"external-bank-123"};
  const f=fixture([existing]);
  try {
    const cmd=command({action:"update",transactionId:existing.id,
      original:{date:existing.date,amountCents:existing.amount}});
    const result=run(f,cmd);
    assert.notEqual(result.status,0);
    assert.match(result.stdout,/blocked:unsupported-complex-transaction/);
    assert.deepEqual(data(f).events,[]);
    assert.deepEqual(data(f).transactions,[existing]);
  } finally {cleanup(f);}
});

test("a stale lock remains intact and prevents mutation",()=>{
  const f=fixture();
  try {
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,".write-lock"),"crash",{mode:0o600});
    const result=run(f,command());
    assert.notEqual(result.status,0);
    assert.match(result.stdout,/blocked:write-in-progress-or-recovery-needed/);
    assert.equal(readFileSync(join(f.journal,".write-lock"),"utf8"),"crash");
    assert.deepEqual(data(f).events,[]);
  } finally {cleanup(f);}
});
