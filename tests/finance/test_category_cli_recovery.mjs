import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,statSync,existsSync,rmSync}
  from "node:fs";
import {join} from "node:path";
import {tmpdir} from "node:os";
import {fileURLToPath} from "node:url";

const writer=fileURLToPath(new URL("../../scripts/finance/write_category.mjs",import.meta.url));
const register=fileURLToPath(new URL("./fixtures/category_cli_register.mjs",import.meta.url));
const sourceKey=createHash("sha256")
  .update("http://127.0.0.1:5006\0fictional-sync-123").digest("hex");
const base={mode:"create",requestId:"a".repeat(32),sourceKey,
  month:"2026-10",groupId:"fictional-needs",
  categoryId:"",expectedName:"",proposedName:"Groceries"};
const rename={...base,mode:"rename",categoryId:"fictional-rent",
  expectedName:"Rent",proposedName:"Housing"};

function setup({permit=true,transactionPermit=false}={}){
  const home=mkdtempSync(join(tmpdir(),"financew-category-fictional-"));
  const config=join(home,".config","financew");
  mkdirSync(config,{recursive:true,mode:0o700});
  for(const [name,value] of [
    ["actual-server-url","http://127.0.0.1:5006"],
    ["actual-password","fictional-password"],
    ["actual-sync-id","fictional-sync-123"],
    ...(permit?[["category-writes-enabled","FINANCEW_CATEGORY_WRITES_APPROVED"]]:[]),
    ...(transactionPermit?[["transaction-writes-enabled","FINANCEW_TRANSACTION_WRITES_APPROVED"]]:[])
  ])writeFileSync(join(config,name),value+"\n",{mode:0o600});
  const ledger=join(home,"fictional-category-ledger.json");
  writeFileSync(ledger,JSON.stringify({
    groups:[{id:"fictional-needs",name:"Needs",is_income:false},
      {id:"fictional-income",name:"Income",is_income:true}],
    categories:[{id:"fictional-rent",group_id:"fictional-needs",name:"Rent"},
      {id:"fictional-income-cat",group_id:"fictional-income",name:"Income",is_income:true}],
    events:[]
  }),{mode:0o600});
  return {home,config,ledger,journal:join(home,".local","state","financew","operations")};
}
function invoke(f,input=base,failStage=""){
  return spawnSync(process.execPath,["--import",register,writer],{
    encoding:"utf8",timeout:15000,input:JSON.stringify(input)+"\n",
    env:{...process.env,HOME:f.home,FINANCEW_FAKE_LEDGER_PATH:f.ledger,
      FINANCEW_FAKE_FAIL_STAGE:failStage,
      ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID:"",ACTUAL_SYNC_ID_FILE:"",
      ACTUAL_SERVER_URL:""}
  });
}
const state=f=>JSON.parse(readFileSync(f.ledger,"utf8"));
const receipt=(f,id)=>join(f.journal,"category-"+id+".json");
const cleanup=f=>rmSync(f.home,{recursive:true,force:true});
function outcome(response,value,exitCode=0){
  assert.equal(response.status,exitCode,response.stdout+" "+response.stderr);
  assert.match(response.stdout,new RegExp("FINANCEW_CATEGORY_RESULT "+value+"\\n"));
  assert.equal(response.stderr,"");
}
test("category writer requires its own permit, not a transaction permit",()=>{
  const f=setup({permit:false,transactionPermit:true});
  try {
    outcome(invoke(f),"blocked:writes-disabled",1);
    assert.deepEqual(state(f).events,[]);
    assert.equal(existsSync(f.journal),false);
  }finally{cleanup(f);}
});
test("one create, private receipt, replay denial and unrelated rename",()=>{
  const f=setup();
  try{
    outcome(invoke(f),"committed");
    assert.deepEqual(state(f).events,["create","sync"]);
    const saved=JSON.parse(readFileSync(receipt(f,base.requestId),"utf8"));
    assert.equal(saved.status,"committed");
    assert.equal(saved.action,"category:create");
    assert.equal(statSync(receipt(f,base.requestId)).mode & 0o077,0);
    assert.ok(!readFileSync(receipt(f,base.requestId),"utf8").includes("Groceries"));
    outcome(invoke(f),"blocked:operation-already-attempted",1);
    const next={...rename,requestId:"b".repeat(32)};
    outcome(invoke(f,next),"committed");
    assert.deepEqual(state(f).events,["create","sync","update","sync"]);
    assert.equal(state(f).categories.find(x=>x.id==="fictional-rent").name,"Housing");
  }finally{cleanup(f);}
});
test("stale category, same-group duplicate and wrong source refuse before attempt",()=>{
  const f=setup();
  try{
    for(const cmd of [
      {...rename,expectedName:"Stale"},
      {...base,proposedName:"RENT"},
      {...base,sourceKey:"f".repeat(64)}
    ]) {
      const response=invoke(f,cmd);
      assert.equal(response.status,1);
    }
    assert.deepEqual(state(f).events,[]);
    assert.equal(existsSync(receipt(f,base.requestId)),false);
  }finally{cleanup(f);}
});
test("other FinanceW uncertainty journal blocks category changes",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,"allocation-uncertain.json"),
      JSON.stringify({version:1,status:"attempted"})+"\n",{mode:0o600});
    outcome(invoke(f),"blocked:recovery-needed",1);
    assert.deepEqual(state(f).events,[]);
  }finally{cleanup(f);}
});
test("stale global lock is preserved, never cleared by category CLI",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    const path=join(f.journal,".write-lock");
    writeFileSync(path,"manual-recovery-needed",{mode:0o600});
    outcome(invoke(f),"blocked:write-in-progress-or-recovery-needed",1);
    assert.equal(readFileSync(path,"utf8"),"manual-recovery-needed");
  }finally{cleanup(f);}
});
test("post-mutation sync failure stays uncertain and blocks another request",()=>{
  const f=setup();
  try{
    outcome(invoke(f,base,"sync"),"uncertain");
    assert.deepEqual(state(f).events,["create","sync"]);
    const attempt=JSON.parse(readFileSync(receipt(f,base.requestId),"utf8"));
    assert.equal(attempt.status,"attempted");
    outcome(invoke(f,{...rename,requestId:"b".repeat(32)}),"blocked:recovery-needed",1);
    assert.deepEqual(state(f).events,["create","sync"]);
  }finally{cleanup(f);}
});
test("malformed or unsafe permit is rejected with no attempts",()=>{
  const f=setup();
  try{
    writeFileSync(join(f.config,"category-writes-enabled"),"INCORRECT\n",{mode:0o600});
    outcome(invoke(f),"blocked:writes-disabled",1);
    assert.deepEqual(state(f).events,[]);
  }finally{cleanup(f);}
});
