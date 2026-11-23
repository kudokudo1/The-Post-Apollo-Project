import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,statSync,existsSync,rmSync,chmodSync}
  from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";

const writer=fileURLToPath(new URL("../../scripts/finance/write_envelope_move.mjs",
  import.meta.url));
const singleWriter=fileURLToPath(new URL("../../scripts/finance/write_allocation.mjs",
  import.meta.url));
const register=fileURLToPath(new URL("./fixtures/envelope_move_cli_register.mjs",
  import.meta.url));
const existingRegister=fileURLToPath(new URL("./fixtures/write_cli_register.mjs",
  import.meta.url));
const fromId="fictional-groceries",toId="fictional-fuel",month="2026-11";
const sourceKey=createHash("sha256")
  .update("http://127.0.0.1:5006\0fictional-sync-123").digest("hex");

function setup({gate=true,allocationGate=false}={}) {
  const home=mkdtempSync(join(tmpdir(),"financew-m2b-fictional-"));
  const config=join(home,".config","financew");
  mkdirSync(config,{recursive:true,mode:0o700});
  const values=[
    ["actual-server-url","http://127.0.0.1:5006"],
    ["actual-password","fictional-password"],
    ["actual-sync-id","fictional-sync-123"],
    ...(gate?[["envelope-moves-enabled","FINANCEW_ENVELOPE_MOVES_APPROVED"]]:[]),
    ...(allocationGate?[["allocation-writes-enabled","FINANCEW_ALLOCATION_WRITES_APPROVED"]]:[])
  ];
  for(const [name,value] of values)
    writeFileSync(join(config,name),value+"\n",{mode:0o600});
  const ledger=join(home,"fictional-ledger.json");
  writeFileSync(ledger,JSON.stringify({
    events:[],budget:{toBudget:4000,
      categoryGroups:[{is_income:false,categories:[
        {id:fromId,budgeted:20000,balance:14000},
        {id:toId,budgeted:5000,balance:2500}
      ]}]}
  }),{mode:0o600});
  return {home,ledger,journal:join(home,".local","state","financew","operations")};
}
function cmd(overrides={}) {
  return {action:"move-envelope",requestId:"a".repeat(32),sourceKey,month,
    fromCategoryId:fromId,toCategoryId:toId,moveCents:2550,
    expectedFromBudgetedCents:20000,expectedFromAvailableCents:14000,
    expectedToBudgetedCents:5000,expectedToAvailableCents:2500,
    expectedToBudgetCents:4000,...overrides};
}
function invoke(f,command,options={}) {
  return spawnSync(process.execPath,["--import",
    options.singleWriter?existingRegister:register,
    options.singleWriter?singleWriter:writer],{
    encoding:"utf8",timeout:15000,
    input:options.rawInput ?? JSON.stringify(command)+"\n",
    env:{...process.env,HOME:f.home,ACTUAL_SERVER_URL:"",
      ACTUAL_SYNC_ID:"",ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID_FILE:"",
      FINANCEW_FAKE_LEDGER_PATH:f.ledger,
      FINANCEW_FAKE_FAIL_STAGE:options.failStage||""}
  });
}
function data(f){return JSON.parse(readFileSync(f.ledger,"utf8"));}
function journal(f,id="a".repeat(32)){
  return join(f.journal,"envelope-move-"+id+".json");
}
function cleanup(f){rmSync(f.home,{recursive:true,force:true});}
function outcome(r,token,code=0){
  assert.equal(r.status,code,
    JSON.stringify({stdout:r.stdout,stderr:r.stderr,signal:r.signal}));
  assert.match(r.stdout,new RegExp("FINANCEW_ENVELOPE_MOVE_RESULT "+
    token.replaceAll(":","\\:")+"\\n"));
  assert.equal(r.stderr,"");
}

test("paired moves require an independent permit, not the old allocation gate",()=>{
  const f=setup({gate:false,allocationGate:true});
  try{
    outcome(invoke(f,cmd()),"blocked:writes-disabled",1);
    assert.deepEqual(data(f).events,[]);
    assert.equal(existsSync(f.journal),false);
  }finally{cleanup(f);}
});

test("fixture writes exactly two categories once with private committed receipt",()=>{
  const f=setup();
  try{
    outcome(invoke(f,cmd()),"committed");
    assert.deepEqual(data(f).events,
      ["set-allocation","set-allocation","sync"]);
    const b=data(f).budget;
    assert.equal(b.toBudget,4000);
    assert.equal(b.categoryGroups[0].categories[0].budgeted,17450);
    assert.equal(b.categoryGroups[0].categories[0].balance,11450);
    assert.equal(b.categoryGroups[0].categories[1].budgeted,7550);
    assert.equal(b.categoryGroups[0].categories[1].balance,5050);
    const path=journal(f),record=JSON.parse(readFileSync(path,"utf8"));
    assert.equal(record.status,"committed");
    assert.equal(record.action,"allocation:move-envelope");
    assert.equal(statSync(path).mode & 0o077,0);
    for(const forbidden of [fromId,toId,sourceKey,
                            "moveCents","fromCategoryId","toCategoryId",
                            "expectedFromBudgetedCents"]) {
      assert.ok(!readFileSync(path,"utf8").includes(forbidden),forbidden);
    }
    outcome(invoke(f,cmd()),"blocked:operation-already-attempted",1);
    assert.deepEqual(data(f).events,
      ["set-allocation","set-allocation","sync"]);
    outcome(invoke(f,cmd({
      requestId:"b".repeat(32),moveCents:100,
      expectedFromBudgetedCents:17450,expectedFromAvailableCents:11450,
      expectedToBudgetedCents:7550,expectedToAvailableCents:5050
    })),"committed");
    assert.equal(data(f).budget.toBudget,4000);
  }finally{cleanup(f);}
});

test("source mismatch, stale budget and malformed input never attempt moves",()=>{
  const f=setup();
  try{
    outcome(invoke(f,cmd({sourceKey:"f".repeat(64)})),
      "blocked:budget-source-changed",1);
    outcome(invoke(f,cmd({expectedFromAvailableCents:1})),
      "blocked:stale-budget",1);
    outcome(invoke(f,cmd(),{rawInput:JSON.stringify(cmd())+
      "\n"+JSON.stringify(cmd())+"\n"}),
      "blocked:invalid-input-frame",1);
    assert.deepEqual(data(f).events,[]);
    assert.equal(existsSync(journal(f)),false);
  }finally{cleanup(f);}
});

test("pre-existing shared lock is respected and never removed",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    const lock=join(f.journal,".write-lock");
    writeFileSync(lock,"unrecovered prior crash\n",{mode:0o600});
    outcome(invoke(f,cmd()),
      "blocked:write-in-progress-or-recovery-needed",1);
    assert.equal(readFileSync(lock,"utf8"),"unrecovered prior crash\n");
    assert.deepEqual(data(f).events,[]);
  }finally{cleanup(f);}
});

test("an unrelated UNRESOLVED journal blocks envelope movement",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,"allocation-"+"c".repeat(32)+".json"),
      '{"version":1,"status":"attempted"}\n',{mode:0o600});
    outcome(invoke(f,cmd()),"blocked:recovery-needed",1);
    assert.deepEqual(data(f).events,[]);
  }finally{cleanup(f);}
});

test("first-only mutation interruption leaves attempted journal and blocks all writers",()=>{
  const f=setup({allocationGate:true});
  try{
    outcome(invoke(f,cmd(),{failStage:"before-second-set"}),"uncertain");
    assert.deepEqual(data(f).events,["set-allocation"]);
    assert.equal(data(f).budget.toBudget,6550);
    assert.equal(data(f).budget.categoryGroups[0].categories[0].budgeted,17450);
    assert.equal(data(f).budget.categoryGroups[0].categories[1].budgeted,5000);
    assert.equal(JSON.parse(readFileSync(journal(f),"utf8")).status,"attempted");

    outcome(invoke(f,cmd({requestId:"b".repeat(32)})),
      "blocked:recovery-needed",1);
    const legacyCmd={action:"set-amount",requestId:"c".repeat(32),
      sourceKey,month,categoryId:toId,
      expectedBudgetedCents:5000,expectedAvailableCents:2500,
      expectedToBudgetCents:6550,targetBudgetedCents:6000};
    const old=invoke(f,legacyCmd,{singleWriter:true});
    assert.equal(old.status,1);
    assert.match(old.stdout,/FINANCEW_ALLOCATION_RESULT blocked:recovery-needed/);
    assert.deepEqual(data(f).events,["set-allocation"]);
  }finally{cleanup(f);}
});

test("sync failure and verification mismatch remain uncertain, not committed",()=>{
  for(const stage of ["sync","readback-mismatch"]) {
    const f=setup();
    try{
      outcome(invoke(f,cmd(),{failStage:stage}),"uncertain");
      assert.equal(JSON.parse(readFileSync(journal(f),"utf8")).status,
        "attempted");
      assert.deepEqual(data(f).events,
        ["set-allocation","set-allocation","sync"]);
      outcome(invoke(f,cmd({requestId:"d".repeat(32)})),
        "blocked:recovery-needed",1);
    }finally{cleanup(f);}
  }
});

test("committed request IDs are single use across transaction and allocation journals",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,"allocation-"+"a".repeat(32)+".json"),
      '{"version":1,"status":"committed"}\n',{mode:0o600});
    outcome(invoke(f,cmd()),"blocked:operation-already-attempted",1);
    assert.deepEqual(data(f).events,[]);
  }finally{cleanup(f);}
});

test("false or unsafe permit refuses before creating a ledger journal",()=>{
  const f=setup();
  try{
    const file=join(f.home,".config","financew","envelope-moves-enabled");
    writeFileSync(file,"NOT_APPROVED\n",{mode:0o600});
    outcome(invoke(f,cmd()),"blocked:writes-disabled",1);
    assert.equal(existsSync(f.journal),false);
    assert.deepEqual(data(f).events,[]);
  }finally{cleanup(f);}
});

test("world-readable permit and oversized framed input refuse before mutation",()=>{
  const f=setup();
  try{
    const permit=join(f.home,".config","financew","envelope-moves-enabled");
    chmodSync(permit,0o644);
    outcome(invoke(f,cmd()),"blocked:writes-disabled",1);
    assert.equal(existsSync(f.journal),false);
    assert.deepEqual(data(f).events,[]);
    chmodSync(permit,0o600);
    outcome(invoke(f,cmd(),{rawInput:"x".repeat(4100)+"\n"}),
      "blocked:input-too-large",1);
    assert.equal(existsSync(journal(f)),false);
    assert.deepEqual(data(f).events,[]);
  }finally{cleanup(f);}
});
