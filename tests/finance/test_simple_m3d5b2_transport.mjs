import assert from "node:assert/strict";
import {test} from "node:test";
import {spawn,spawnSync} from "node:child_process";
import {mkdtemp,rm,readFile,readdir,writeFile,chmod,mkdir,symlink,stat}
  from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";
import {inspectM3d5b2StdinFrame,inspectM3d5b2WriterOutcome}
  from "../../scripts/finance/simple_m3d5b2_disposable_transport.mjs";
const child=fileURLToPath(new URL(
  "./fixtures/simple_m3d5b2_transport_child.mjs",import.meta.url));
function cmd(id="a".repeat(32),amount=-1250){
  return {
    action:"create-categorized-expense",requestId:id,
    sourceKey:"b".repeat(64),accountId:"checking-1234",
    month:"2026-11",date:"2026-11-25",
    description:"Fictional Test Market",amountCents:amount,
    categoryId:"groceries-1234",
    expectedCategoryBudgetedCents:10000,
    expectedCategoryAvailableCents:7500,
    expectedCategorySpentCents:-2500,expectedToBudgetCents:12000
  };
}
async function fixture(fn){
  const root=await mkdtemp(join(tmpdir(),"financew-m3d5b2-fixture-"));
  await chmod(root,0o700);
  try{await fn(root);}finally{await rm(root,{recursive:true,force:true});}
}
function childAttempt(root,command,{env={}}={}){
  const proc=spawnSync(process.execPath,[child],{
    input:JSON.stringify({sandboxRoot:root,command})+"\n",
    encoding:"utf8",timeout:20000,
    env:{...process.env,HOME:root,FINANCEW_DISPOSABLE_TEST:"yes",...env}
  });
  assert.equal(proc.status,0,proc.stderr);
  assert.equal(proc.stderr,"");
  return JSON.parse(proc.stdout);
}
test("one bounded stdin JSON line follows M3b grammar; never dispatched",()=>{
  const frame=JSON.stringify(cmd())+"\n";
  const out=inspectM3d5b2StdinFrame(frame);
  assert.equal(out.ok,true);
  assert.equal(out.dispatched,false);
  assert.equal(out.canSave,false);
  assert.equal(out.writeAllowed,false);
  assert.match(out.frameHash,/^[0-9a-f]{64}$/);
  assert.equal("command" in out,false);
  for(const malformed of [
    frame+"\n",frame+"\r\n",frame.slice(0,-1),
    frame+JSON.stringify(cmd("b".repeat(32)))+"\n",
    JSON.stringify({...cmd(),requestId:"bad"})+"\n",
    "x".repeat(4097)+"\n"
  ])assert.equal(inspectM3d5b2StdinFrame(malformed).ok,false);
});
test("fixed stdout grammar never infers a successful write from exit status",()=>{
  const parse=inspectM3d5b2WriterOutcome;
  assert.deepEqual(parse({stdout:"FINANCEW_CATEGORIZED_EXPENSE_RESULT committed\n",exitCode:0}),
    {state:"committed",canRetry:false});
  assert.deepEqual(parse({stdout:"FINANCEW_CATEGORIZED_EXPENSE_RESULT committed\n",exitCode:1}),
    {state:"uncertain",canRetry:false});
  assert.deepEqual(parse({stdout:"",exitCode:0}),
    {state:"uncertain",canRetry:false});
  assert.deepEqual(parse({stdout:"FINANCEW_CATEGORIZED_EXPENSE_RESULT uncertain\n",exitCode:0}),
    {state:"uncertain",canRetry:false});
  assert.deepEqual(parse({stdout:"FINANCEW_CATEGORIZED_EXPENSE_RESULT blocked:recovery-needed\n",exitCode:1}),
    {state:"blocked",canRetry:false,reason:"recovery-needed"});
  assert.equal(parse({stdout:"FINANCEW_CATEGORIZED_EXPENSE_RESULT blocked:recovery-needed\n",exitCode:0}).state,"uncertain");
  for(const stdout of [
    "FINANCEW_CATEGORIZED_EXPENSE_RESULT committed\n".repeat(2),
    "error: sync-id=test\n",
    "FINANCEW_CATEGORIZED_EXPENSE_RESULT committed extra\n"
  ])assert.equal(parse({stdout,exitCode:0}).state,"uncertain");
});
test("writer acknowledgment requires exactly one complete LF-terminated line",()=>{
  const parse=inspectM3d5b2WriterOutcome;
  const ok="FINANCEW_CATEGORIZED_EXPENSE_RESULT committed\n";
  const malformed=[
    {name:"extra trailing newline",stdout:ok+"\n"},
    {name:"multiple extra blank lines",stdout:ok+"\n\n"},
    {name:"missing final newline",stdout:ok.slice(0,-1)},
    {name:"leading newline",stdout:"\n"+ok},
    {name:"leading blank lines",stdout:"\n\n"+ok},
    {name:"CRLF",stdout:ok.slice(0,-1)+"\r\n"},
    {name:"bare CR",stdout:ok.slice(0,-1)+"\r"},
    {name:"extra trailing text",stdout:ok+"extra\n"},
    {name:"extra leading text",stdout:"extra\n"+ok},
    {name:"leading spaces",stdout:" "+ok},
    {name:"trailing spaces",stdout:ok.slice(0,-1)+" \n"},
    {name:"trailing tab",stdout:ok.slice(0,-1)+"\t\n"},
    {name:"embedded NUL",stdout:ok.slice(0,-1)+"\0\n"},
    {name:"Unicode line separator",stdout:ok.slice(0,-1)+"\u2028\n"},
    {name:"Unicode paragraph separator",stdout:ok.slice(0,-1)+"\u2029\n"},
    {name:"double status",stdout:ok+ok}
  ];
  assert.deepEqual(parse({stdout:ok,exitCode:0}),
    {state:"committed",canRetry:false});
  for(const {name,stdout} of malformed)
    assert.deepEqual(parse({stdout,exitCode:0}),
      {state:"uncertain",canRetry:false},name);
  for(const exitCode of [null,1,2,-1,"0",undefined])
    assert.deepEqual(parse({stdout:ok,exitCode}),
      {state:"uncertain",canRetry:false},"committed exit "+String(exitCode));
});
test("blocked result also requires exact LF frame and positive exit code",()=>{
  const parse=inspectM3d5b2WriterOutcome;
  const blocked="FINANCEW_CATEGORIZED_EXPENSE_RESULT blocked:recovery-needed\n";
  assert.deepEqual(parse({stdout:blocked,exitCode:1}),
    {state:"blocked",canRetry:false,reason:"recovery-needed"});
  for(const exitCode of [0,-1,null,undefined,"1"])
    assert.deepEqual(parse({stdout:blocked,exitCode}),
      {state:"uncertain",canRetry:false},"blocked exit "+String(exitCode));
  for(const stdout of [
    blocked+"\n",blocked.slice(0,-1),"\n"+blocked,
    blocked.slice(0,-1)+"\r\n",blocked+"other\n"
  ])
    assert.deepEqual(parse({stdout,exitCode:1}),
      {state:"uncertain",canRetry:false});
});
test("durable intent survives process exit; same ID or same transaction refused after restart",async()=>{
  await fixture(async root=>{
    const first=childAttempt(root,cmd());
    assert.equal(first.ok,true,JSON.stringify(first));
    assert.equal(first.dispatched,false);
    assert.equal(first.state,"sealed-dry-run");
    assert.match(first.fingerprint,/^[0-9a-f]{64}$/);
    const directory=join(root,"reservations");
    let names=await readdir(directory);
    assert.equal(names.length,1);
    assert.equal(names[0],"intent-"+first.fingerprint+".json");
    const contents=await readFile(join(directory,names[0]),"utf8");
    const receipt=JSON.parse(contents);
    assert.equal(receipt.requestId,"a".repeat(32));
    assert.equal(receipt.state,"sealed-dry-run");
    assert.equal(contents.includes("Fictional Test Market"),false);
    assert.equal(contents.includes("checking-1234"),false);
    assert.equal((await stat(join(directory,names[0]))).mode & 0o077,0);
    const same=childAttempt(root,cmd());
    assert.equal(same.reason,"replay-or-duplicate-intent");
    const newIdSameIntent=childAttempt(root,cmd("c".repeat(32)));
    assert.equal(newIdSameIntent.reason,"replay-or-duplicate-intent");
    const sameIdOtherAmount=childAttempt(root,cmd("a".repeat(32),-1550));
    assert.equal(sameIdOtherAmount.reason,"replay-or-duplicate-intent");
    const newExpense=childAttempt(root,cmd("d".repeat(32),-1550));
    assert.equal(newExpense.ok,true);
    names=await readdir(directory);
    assert.equal(names.length,2);
  });
});
test("disposable test root and exact child HOME both required",async()=>{
  await fixture(async root=>{
    assert.equal(childAttempt(root,cmd(),{
      env:{FINANCEW_DISPOSABLE_TEST:"no"}
    }).reason,"disposable-fixture-required");
    assert.equal(childAttempt(root,cmd(),{
      env:{HOME:tmpdir()}
    }).reason,"disposable-fixture-required");
    assert.equal(childAttempt(root+"/../anything",cmd()).reason,
      "disposable-fixture-required");
    await assert.rejects(readdir(join(root,"reservations")),{code:"ENOENT"});
  });
});
test("untrusted reservation directory, symlink and tampered journal fail closed",async()=>{
  await fixture(async root=>{
    const dir=join(root,"reservations");
    const other=join(root,"other");
    await mkdir(other,{mode:0o700});
    await symlink(other,dir);
    assert.equal(childAttempt(root,cmd()).reason,
      "untrusted-reservation-directory");
    await rm(dir);
    await mkdir(dir,{mode:0o770});
    assert.equal(childAttempt(root,cmd()).reason,
      "untrusted-reservation-directory");
    await chmod(dir,0o700);
    await writeFile(join(dir,"orphan"),"unknown\n",{mode:0o600});
    assert.equal(childAttempt(root,cmd()).reason,
      "unrecognized-reservation-entry");
    assert.ok((await readdir(dir)).includes(".reservation-lock"),
      "uncertain reservation leaves durable lock for recovery");
  });
});
test("existing reservation lock prevents concurrent or restarted admission",async()=>{
  await fixture(async root=>{
    const dir=join(root,"reservations");
    await mkdir(dir,{mode:0o700});
    await writeFile(join(dir,".reservation-lock"),"stale\n",{mode:0o600});
    assert.equal(childAttempt(root,cmd()).reason,
      "reservation-locked-recovery-required");
    assert.equal(childAttempt(root,cmd("c".repeat(32))).reason,
      "reservation-locked-recovery-required");
    assert.deepEqual((await readdir(dir)),[".reservation-lock"]);
  });
});

function childAttemptAsync(root,command){
  return new Promise((resolve,reject)=>{
    const env={...process.env,HOME:root,FINANCEW_DISPOSABLE_TEST:"yes"};
    const proc=spawn(process.execPath,[child],{env,stdio:["pipe","pipe","pipe"]});
    let stdout="",stderr="";
    proc.stdout.on("data",chunk=>stdout+=chunk);
    proc.stderr.on("data",chunk=>stderr+=chunk);
    proc.on("error",reject);
    proc.on("close",code=>{
      if(code!==0 || stderr)return reject(Error(stderr||"child exit "+code));
      try{resolve(JSON.parse(stdout));}catch(e){reject(e);}
    });
    proc.stdin.end(JSON.stringify({sandboxRoot:root,command})+"\n");
  });
}
test("two truly concurrent separate processes admit at most one identical intent",async()=>{
  await fixture(async root=>{
    const [a,b]=await Promise.all([
      childAttemptAsync(root,cmd()),
      childAttemptAsync(root,cmd())
    ]);
    assert.equal([a,b].filter(x=>x.ok).length,1,JSON.stringify([a,b]));
    assert.equal([a,b].filter(x=>!x.ok).length,1);
    assert.ok([a,b].some(x=>[
      "reservation-locked-recovery-required",
      "replay-or-duplicate-intent"
    ].includes(x.reason)));
    assert.equal((await readdir(join(root,"reservations"))).length,1);
  });
});
test("symlinked and world-readable sealed receipts never count as trusted",async()=>{
  for(const kind of ["symlink","world-readable"]){
    await fixture(async root=>{
      const first=childAttempt(root,cmd());
      assert.equal(first.ok,true);
      const receipt=join(root,"reservations","intent-"+first.fingerprint+".json");
      if(kind==="symlink"){
        const original=await readFile(receipt,"utf8");
        await rm(receipt);
        await writeFile(join(root,"outside"),original,{mode:0o600});
        await symlink(join(root,"outside"),receipt);
      }else await chmod(receipt,0o644);
      const second=childAttempt(root,cmd("c".repeat(32),-1550));
      assert.equal(second.reason,"untrusted-reservation-entry");
      assert.ok((await readdir(join(root,"reservations"))).includes(
        ".reservation-lock"));
    });
  }
});
