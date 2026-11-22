import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,
  statSync,existsSync,rmSync,chmodSync} from "node:fs";
import {join} from "node:path";
import {tmpdir} from "node:os";
import {fileURLToPath} from "node:url";

const writer=fileURLToPath(new URL("../../scripts/finance/write_category_group.mjs",import.meta.url));
const register=fileURLToPath(new URL("./fixtures/category_cli_register.mjs",import.meta.url));
const sourceKey=createHash("sha256")
  .update("http://127.0.0.1:5006\0fictional-sync-123").digest("hex");
const create={mode:"create",requestId:"a".repeat(32),sourceKey,month:"2026-11",
  groupId:"",expectedName:"",proposedName:"Household"};
const rename={...create,mode:"rename",groupId:"fictional-needs",
  expectedName:"Needs",proposedName:"Essentials"};
const permitName="category-group-writes-enabled";
function setup({permit=true,categoryPermit=false}={}){
  const home=mkdtempSync(join(tmpdir(),"financew-group-fictional-"));
  const config=join(home,".config","financew");
  mkdirSync(config,{recursive:true,mode:0o700});
  for(const [name,value] of [
    ["actual-server-url","http://127.0.0.1:5006"],
    ["actual-password","fictional-password"],
    ["actual-sync-id","fictional-sync-123"],
    ...(permit?[[permitName,"FINANCEW_CATEGORY_GROUP_WRITES_APPROVED"]]:[]),
    ...(categoryPermit?[["category-writes-enabled","FINANCEW_CATEGORY_WRITES_APPROVED"]]:[])
  ])writeFileSync(join(config,name),value+"\n",{mode:0o600});
  const ledger=join(home,"fictional-ledger.json");
  writeFileSync(ledger,JSON.stringify({
    groups:[{id:"fictional-needs",name:"Needs",is_income:false},
      {id:"fictional-income",name:"Income",is_income:true}],
    categories:[],events:[]
  }),{mode:0o600});
  return {home,config,ledger,journal:join(home,".local","state","financew","operations")};
}
function invoke(f,cmd=create,failStage=""){
  return spawnSync(process.execPath,["--import",register,writer],{
    encoding:"utf8",timeout:15000,input:JSON.stringify(cmd)+"\n",
    env:{...process.env,HOME:f.home,FINANCEW_FAKE_LEDGER_PATH:f.ledger,
      FINANCEW_FAKE_FAIL_STAGE:failStage,ACTUAL_SERVER_URL:"",
      ACTUAL_SYNC_ID:"",ACTUAL_SYNC_ID_FILE:"",ACTUAL_PASSWORD_FILE:"",
      ACTUAL_ENCRYPTION_PASSWORD_FILE:""}
  });
}
const state=f=>JSON.parse(readFileSync(f.ledger,"utf8"));
const receipt=(f,id)=>join(f.journal,"category-group-"+id+".json");
function outcome(result,value,exit=0){
  assert.equal(result.status,exit,result.stdout+" / "+result.stderr);
  assert.match(result.stdout,new RegExp("FINANCEW_CATEGORY_GROUP_RESULT "+value+"\\n"));
  assert.equal(result.stderr,"");
}
const cleanup=f=>rmSync(f.home,{recursive:true,force:true});

test("M5 independent authorization cannot inherit category-name permit",()=>{
  const f=setup({permit:false,categoryPermit:true});
  try{
    outcome(invoke(f),"blocked:writes-disabled",1);
    assert.deepEqual(state(f).events,[]);
    assert.equal(existsSync(f.journal),false);
  }finally{cleanup(f);}
});
test("M5 group create/rename commit with distinct one-shot receipts",()=>{
  const f=setup();
  try{
    outcome(invoke(f),"committed");
    assert.deepEqual(state(f).events,["group-create","sync"]);
    const saved=JSON.parse(readFileSync(receipt(f,create.requestId),"utf8"));
    assert.equal(saved.status,"committed");
    assert.equal(saved.action,"category-group:create");
    assert.equal(statSync(receipt(f,create.requestId)).mode & 0o077,0);
    assert.equal(readFileSync(receipt(f,create.requestId),"utf8").includes("Household"),false);
    outcome(invoke(f),"blocked:operation-already-attempted",1);
    outcome(invoke(f,{...rename,requestId:"b".repeat(32)}),"committed");
    assert.deepEqual(state(f).events,["group-create","sync","group-rename","sync"]);
    assert.equal(state(f).groups.find(g=>g.id==="fictional-needs").name,"Essentials");
  }finally{cleanup(f);}
});
test("M5 wrong source, duplicate and stale group fail before mutation",()=>{
  const f=setup();
  try{
    for(const cmd of [
      {...create,sourceKey:"f".repeat(64)},
      {...create,proposedName:"NEEDS"},
      {...rename,expectedName:"Outdated"},
      {...rename,groupId:"fictional-income",expectedName:"Income"}
    ]){
      assert.equal(invoke(f,cmd).status,1);
    }
    assert.deepEqual(state(f).events,[]);
    assert.equal(existsSync(receipt(f,create.requestId)),false);
  }finally{cleanup(f);}
});
test("M5 global recovery journal of another writer blocks group write",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,"funding-uncertain.json"),
      '{"status":"attempted"}\n',{mode:0o600});
    outcome(invoke(f),"blocked:recovery-needed",1);
    assert.deepEqual(state(f).events,[]);
  }finally{cleanup(f);}
});
test("M5 shared lock is not removed if already held",()=>{
  const f=setup();
  try{
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    const lock=join(f.journal,".write-lock");
    writeFileSync(lock,"protected",{mode:0o600});
    outcome(invoke(f),"blocked:write-in-progress-or-recovery-needed",1);
    assert.equal(readFileSync(lock,"utf8"),"protected");
    assert.deepEqual(state(f).events,[]);
  }finally{cleanup(f);}
});
test("M5 interrupted sync leaves attempted receipt and blocks future write",()=>{
  const f=setup();
  try{
    outcome(invoke(f,create,"sync"),"uncertain");
    assert.deepEqual(state(f).events,["group-create","sync"]);
    assert.equal(JSON.parse(readFileSync(receipt(f,create.requestId),"utf8")).status,
      "attempted");
    outcome(invoke(f,{...rename,requestId:"b".repeat(32)}),
      "blocked:recovery-needed",1);
    assert.deepEqual(state(f).events,["group-create","sync"]);
  }finally{cleanup(f);}
});
test("M5 incorrect permit and unsafe mode refuse",()=>{
  const f=setup();
  try{
    const path=join(f.config,permitName);
    writeFileSync(path,"WRONG\n",{mode:0o600});
    outcome(invoke(f),"blocked:writes-disabled",1);
    writeFileSync(path,"FINANCEW_CATEGORY_GROUP_WRITES_APPROVED\n");
    chmodSync(path,0o644);
    outcome(invoke(f),"blocked:writes-disabled",1);
    assert.deepEqual(state(f).events,[]);
  }finally{cleanup(f);}
});
