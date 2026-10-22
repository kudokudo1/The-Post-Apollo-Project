import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,statSync,existsSync,rmSync}
  from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";

const writer=fileURLToPath(new URL("../../scripts/finance/write_allocation.mjs",import.meta.url));
const transactionWriter=fileURLToPath(new URL("../../scripts/finance/write_transaction.mjs",import.meta.url));
const register=fileURLToPath(new URL("./fixtures/write_cli_register.mjs",import.meta.url));
const month="2026-10",categoryId="fictional-cat-1";
const sourceKey=createHash("sha256")
  .update("http://127.0.0.1:5006\0fictional-sync-123").digest("hex");
function setup({allocationGate=true,transactionGate=false}={}){
  const home=mkdtempSync(join(tmpdir(),"financew-d12c-fictional-"));
  const config=join(home,".config","financew");
  mkdirSync(config,{recursive:true,mode:0o700});
  for(const [name,value] of [
    ["actual-server-url","http://127.0.0.1:5006"],
    ["actual-password","fictional-password"],
    ["actual-sync-id","fictional-sync-123"],
    ...(allocationGate?[["allocation-writes-enabled","FINANCEW_ALLOCATION_WRITES_APPROVED"]]:[]),
    ...(transactionGate?[["transaction-writes-enabled","FINANCEW_TRANSACTION_WRITES_APPROVED"]]:[])
  ])writeFileSync(join(config,name),value+"\n",{mode:0o600});
  const ledger=join(home,"fictional-ledger.json");
  writeFileSync(ledger,JSON.stringify({accounts:[{id:"fictional-123",offbudget:false,closed:false}],
    transactions:[],events:[],budget:{toBudget:30000,
      categoryGroups:[{is_income:false,categories:[{
        id:categoryId,budgeted:20000,balance:8000
      }]}]}}),{mode:0o600});
  return {home,ledger,journal:join(home,".local","state","financew","operations")};
}
function command(overrides={}){return{
  action:"set-amount",requestId:"a".repeat(32),sourceKey,month,categoryId,
  expectedBudgetedCents:20000,expectedAvailableCents:8000,
  expectedToBudgetCents:30000,targetBudgetedCents:25000,...overrides
};}
function invoke(f,cmd,options={}){
  return spawnSync(process.execPath,["--import",register,
    options.transaction?transactionWriter:writer],{
    encoding:"utf8",timeout:15000,input:JSON.stringify(cmd)+"\n",
    env:{...process.env,HOME:f.home,ACTUAL_SERVER_URL:"",
      ACTUAL_SYNC_ID:"",ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID_FILE:"",
      FINANCEW_FAKE_LEDGER_PATH:f.ledger,
      FINANCEW_FAKE_FAIL_STAGE:options.failStage||""}
  });
}
function budget(f){return JSON.parse(readFileSync(f.ledger,"utf8"));}
function journal(f,id){return join(f.journal,"allocation-"+id+".json");}
function cleanup(f){rmSync(f.home,{recursive:true,force:true});}
function assertOutcome(r,token,code=0){
  assert.equal(r.status,code,JSON.stringify({stdout:r.stdout,stderr:r.stderr}));
  assert.match(r.stdout,new RegExp("FINANCEW_ALLOCATION_RESULT "+token+"\\n"));
  assert.equal(r.stderr,"");
}

test("operator allocation authorization is independent of transaction authorization",()=>{
  const f=setup({allocationGate:false,transactionGate:true});
  try{
    assertOutcome(invoke(f,command()),"blocked:writes-disabled",1);
    assert.deepEqual(budget(f).events,[]);
    assert.equal(existsSync(f.journal),false);
  }finally{cleanup(f);}
});

test("fictional allocation commits once with durable private receipt, then another valid allocation",()=>{
  const f=setup();
  try{
    const first=invoke(f,command());
    assertOutcome(first,"committed");
    assert.deepEqual(budget(f).events,["set-allocation","sync"]);
    const current=budget(f).budget;
    assert.equal(current.toBudget,25000);
    assert.equal(current.categoryGroups[0].categories[0].balance,13000);
    const path=journal(f,"a".repeat(32));
    const receipt=JSON.parse(readFileSync(path,"utf8"));
    assert.equal(receipt.status,"committed");
    assert.equal(receipt.action,"allocation:set-amount");
    assert.equal(statSync(path).mode & 0o077,0);
    assert.ok(!readFileSync(path,"utf8").includes(categoryId));
    const repeated=invoke(f,command());
    assertOutcome(repeated,"blocked:operation-already-attempted",1);
    const second=invoke(f,command({requestId:"b".repeat(32),
      expectedBudgetedCents:25000,expectedAvailableCents:13000,
      expectedToBudgetCents:25000,targetBudgetedCents:26000}));
    assertOutcome(second,"committed");
    assert.deepEqual(budget(f).events,["set-allocation","sync","set-allocation","sync"]);
    assert.equal(budget(f).budget.toBudget,24000);
  }finally{cleanup(f);}
});

test("source mismatch is refused before actual API mutation or attempt",()=>{
  const f=setup();
  try{
    assertOutcome(invoke(f,command({sourceKey:"f".repeat(64)})),
      "blocked:budget-source-changed",1);
    assert.deepEqual(budget(f).events,[]);
    assert.equal(existsSync(journal(f,"a".repeat(32))),false);
  }finally{cleanup(f);}
});

test("stale expected category amounts refuse without a journal or mutation",()=>{
  const f=setup();
  try{
    assertOutcome(invoke(f,command({expectedToBudgetCents:29999})),
      "blocked:stale-budget",1);
    assert.deepEqual(budget(f).events,[]);
    assert.equal(existsSync(journal(f,"a".repeat(32))),false);
  }finally{cleanup(f);}
});

test("shared transaction journal with unresolved status blocks allocation saving",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,"d".repeat(32)+".json"),
      JSON.stringify({version:1,status:"attempted",hash:"x"})+"\n",{mode:0o600});
    assertOutcome(invoke(f,command()),"blocked:recovery-needed",1);
    assert.deepEqual(budget(f).events,[]);
  }finally{cleanup(f);}
});

test("stale shared write lock is preserved and blocks allocation",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    const lock=join(f.journal,".write-lock");
    writeFileSync(lock,"requires-manual-recovery",{mode:0o600});
    assertOutcome(invoke(f,command()),
      "blocked:write-in-progress-or-recovery-needed",1);
    assert.equal(readFileSync(lock,"utf8"),"requires-manual-recovery");
    assert.deepEqual(budget(f).events,[]);
  }finally{cleanup(f);}
});

test("post-allocation sync failure is uncertain; both finance writers block later attempts",()=>{
  const f=setup({transactionGate:true});
  try{
    assertOutcome(invoke(f,command(),{failStage:"allocation-sync"}),"uncertain");
    assert.deepEqual(budget(f).events,["set-allocation","sync"]);
    const receipt=JSON.parse(readFileSync(journal(f,"a".repeat(32)),"utf8"));
    assert.equal(receipt.status,"attempted");
    assertOutcome(invoke(f,command({requestId:"b".repeat(32),
      expectedBudgetedCents:25000,expectedAvailableCents:13000,
      expectedToBudgetCents:25000,targetBudgetedCents:26000})),
      "blocked:recovery-needed",1);
    const tx={action:"create",requestId:"c".repeat(32),sourceKey,
      accountId:"fictional-123",month,date:"2026-10-22",
      description:"fictional",amountCents:-100};
    const blocked=invoke(f,tx,{transaction:true});
    assert.equal(blocked.status,1);
    assert.match(blocked.stdout,/FINANCEW_TRANSACTION_RESULT blocked:recovery-needed/);
    assert.deepEqual(budget(f).events,["set-allocation","sync"]);
  }finally{cleanup(f);}
});

test("malformed input and false permission never invoke Actual",()=>{
  const f=setup();
  try{
    const permit=join(f.home,".config","financew","allocation-writes-enabled");
    writeFileSync(permit,"WRONG PERMISSION\n",{mode:0o600});
    assertOutcome(invoke(f,command()),"blocked:writes-disabled",1);
    assert.deepEqual(budget(f).events,[]);
  }finally{cleanup(f);}
});
