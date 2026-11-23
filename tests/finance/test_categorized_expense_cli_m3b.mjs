import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,statSync,
        existsSync,rmSync,chmodSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";

const writer=fileURLToPath(new URL("../../scripts/finance/write_categorized_expense.mjs",import.meta.url));
const legacyWriter=fileURLToPath(new URL("../../scripts/finance/write_transaction.mjs",import.meta.url));
const register=fileURLToPath(new URL("./fixtures/categorized_expense_cli_register.mjs",import.meta.url));
const legacyRegister=fileURLToPath(new URL("./fixtures/write_cli_register.mjs",import.meta.url));
const sourceKey=createHash("sha256")
  .update("http://127.0.0.1:5006\0fictional-sync-123").digest("hex");
function setup({gate=true,oldGate=false}={}){
  const home=mkdtempSync(join(tmpdir(),"financew-m3b-fictional-"));
  const config=join(home,".config","financew");
  mkdirSync(config,{recursive:true,mode:0o700});
  const entries=[
    ["actual-server-url","http://127.0.0.1:5006"],
    ["actual-password","fictional-password"],
    ["actual-sync-id","fictional-sync-123"],
    ...(gate?[["categorized-expense-writes-enabled",
               "FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED"]]:[]),
    ...(oldGate?[["transaction-writes-enabled",
                  "FINANCEW_TRANSACTION_WRITES_APPROVED"]]:[])
  ];
  for(const [name,data] of entries)
    writeFileSync(join(config,name),data+"\n",{mode:0o600});
  const ledger=join(home,"fictional-ledger.json");
  writeFileSync(ledger,JSON.stringify({
    events:[],accounts:[{id:"fictional-checking",offbudget:false,closed:false}],
    budget:{toBudget:12000,categoryGroups:[
      {is_income:false,categories:[
        {id:"fictional-groceries",name:"Groceries",budgeted:10000,
         balance:7500,spent:-2500}
      ]},
      {is_income:true,categories:[
        {id:"fictional-income",name:"Income",budgeted:0,balance:0,spent:0}
      ]}
    ]},
    transactions:[]
  }),{mode:0o600});
  return {home,ledger,config,journal:join(home,".local","state","financew","operations")};
}
function cmd(override={}){
  return {action:"create-categorized-expense",requestId:"a".repeat(32),
    sourceKey,accountId:"fictional-checking",month:"2026-11",
    date:"2026-11-23",description:"Fictional Groceries",amountCents:-1250,
    categoryId:"fictional-groceries",expectedCategoryBudgetedCents:10000,
    expectedCategoryAvailableCents:7500,expectedCategorySpentCents:-2500,
    expectedToBudgetCents:12000,...override};
}
function invoke(f,command,options={}){
  return spawnSync(process.execPath,["--import",
    options.oldWriter?legacyRegister:register,
    options.oldWriter?legacyWriter:writer],{
    encoding:"utf8",timeout:15000,
    input:options.rawInput??JSON.stringify(command)+"\n",
    env:{...process.env,HOME:f.home,ACTUAL_SERVER_URL:"",
      ACTUAL_SYNC_ID:"",ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID_FILE:"",
      FINANCEW_FAKE_LEDGER_PATH:f.ledger,
      FINANCEW_FAKE_FAIL_STAGE:options.failStage||""}
  });
}
function receipt(f,id="a".repeat(32)){
  return join(f.journal,"categorized-expense-"+id+".json");
}
function data(f){return JSON.parse(readFileSync(f.ledger,"utf8"));}
function cleanup(f){rmSync(f.home,{recursive:true,force:true});}
function outcome(r,status,code=0){
  assert.equal(r.status,code,JSON.stringify({status:r.status,stdout:r.stdout,stderr:r.stderr,signal:r.signal}));
  assert.equal(r.stdout,"FINANCEW_CATEGORIZED_EXPENSE_RESULT "+status+"\n");
  assert.equal(r.stderr,"");
}
test("new category write gate is independent of the old transaction permit",()=>{
  const f=setup({gate:false,oldGate:true});
  try {
    outcome(invoke(f,cmd()),"blocked:writes-disabled",1);
    assert.equal(data(f).transactions.length,0);
    assert.equal(existsSync(f.journal),false);
  } finally {cleanup(f);}
});
test("fictional categorized expense writes one category-bound record and private receipt",()=>{
  const f=setup();
  try {
    outcome(invoke(f,cmd()),"committed");
    const d=data(f);
    assert.equal(d.transactions.length,1);
    assert.equal(d.transactions[0].category,"fictional-groceries");
    assert.equal(d.transactions[0].account,"fictional-checking");
    assert.equal(d.transactions[0].amount,-1250);
    assert.equal(d.transactions[0].imported_id,"financew-cat-"+cmd().requestId);
    assert.deepEqual(d.events,[
      "accounts","budget","transactions","add","sync","transactions","budget"]);
    const path=receipt(f);
    const body=readFileSync(path,"utf8"),rec=JSON.parse(body);
    assert.equal(rec.status,"committed");
    assert.equal(rec.action,"transaction:create-categorized-expense");
    assert.equal(statSync(path).mode & 0o077,0);
    for(const secret of ["fictional-groceries","fictional-checking",
                         "expectedCategoryAvailableCents",sourceKey,
                         "Fictional Groceries"])
      assert.equal(body.includes(secret),false,secret);
    outcome(invoke(f,cmd()),"blocked:operation-already-attempted",1);
    assert.equal(data(f).transactions.length,1);
  }finally{cleanup(f);}
});
test("bad source, wrong amounts, invalid frame or locked journal cannot write",()=>{
  const f=setup();
  try {
    outcome(invoke(f,cmd({sourceKey:"e".repeat(64)})),
      "blocked:budget-source-changed",1);
    outcome(invoke(f,cmd({expectedCategoryAvailableCents:7400})),
      "blocked:stale-budget",1);
    outcome(invoke(f,cmd(),{rawInput:JSON.stringify(cmd())+"\n"+
      JSON.stringify(cmd())+"\n"}),"blocked:invalid-input-frame",1);
    outcome(invoke(f,cmd(),{rawInput:"x".repeat(4100)+"\n"}),
      "blocked:input-too-large",1);
    assert.equal(data(f).transactions.length,0);
    assert.equal(existsSync(receipt(f)),false);
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,".write-lock"),"unresolved\n",{mode:0o600});
    outcome(invoke(f,cmd()),"blocked:write-in-progress-or-recovery-needed",1);
    assert.equal(readFileSync(join(f.journal,".write-lock"),"utf8"),"unresolved\n");
  }finally{cleanup(f);}
});
test("world-readable permit and malicious control characters fail closed",()=>{
  const f=setup();
  try {
    chmodSync(join(f.config,"categorized-expense-writes-enabled"),0o644);
    outcome(invoke(f,cmd()),"blocked:writes-disabled",1);
    chmodSync(join(f.config,"categorized-expense-writes-enabled"),0o600);
    outcome(invoke(f,cmd(),{rawInput:JSON.stringify(cmd())+"\r\n"}),
      "blocked:invalid-input-frame",1);
    assert.equal(data(f).transactions.length,0);
    assert.equal(existsSync(receipt(f)),false);
  }finally{cleanup(f);}
});
test("any existing unresolved FinanceW journal blocks categorized creation",()=>{
  const f=setup();
  try {
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,"allocation-"+"b".repeat(32)+".json"),
      '{"version":1,"status":"attempted"}\n',{mode:0o600});
    outcome(invoke(f,cmd()),"blocked:recovery-needed",1);
    assert.equal(data(f).transactions.length,0);
    assert.equal(existsSync(receipt(f)),false);
  }finally{cleanup(f);}
});
test("separate writers cannot reuse an already committed request ID",()=>{
  const f=setup();
  try {
    mkdirSync(f.journal,{recursive:true,mode:0o700});
    writeFileSync(join(f.journal,"allocation-"+"a".repeat(32)+".json"),
      '{"version":1,"status":"committed"}\n',{mode:0o600});
    outcome(invoke(f,cmd()),"blocked:operation-already-attempted",1);
    assert.equal(data(f).transactions.length,0);
  }finally{cleanup(f);}
});
test("uncertain post-attempt outcomes retain durable journal; no retry or rollback",()=>{
  for(const failure of ["before-add","sync","bad-ack",
                        "wrong-category","wrong-readback-category"]){
    const f=setup({oldGate:true});
    try {
      outcome(invoke(f,cmd(),{failStage:failure}),"uncertain");
      assert.equal(JSON.parse(readFileSync(receipt(f),"utf8")).status,"attempted");
      outcome(invoke(f,cmd({requestId:"b".repeat(32)})),
        "blocked:recovery-needed",1);
      // The existing transaction writer must honor the same unresolved
      // finance journal, even though it uses a different permission.
      const oldCmd={action:"create",requestId:"c".repeat(32),
        sourceKey,accountId:"fictional-checking",month:"2026-11",
        date:"2026-11-24",description:"Another fictional expense",amountCents:-500};
      const old=invoke(f,oldCmd,{oldWriter:true});
      assert.equal(old.status,1);
      assert.equal(old.stdout,
        "FINANCEW_TRANSACTION_RESULT blocked:recovery-needed\n");
      const d=data(f);
      assert.ok(d.transactions.length<=1);
      assert.ok(d.transactions.every(x=>x.category!=="fictional-income"));
    } finally {cleanup(f);}
  }
});
