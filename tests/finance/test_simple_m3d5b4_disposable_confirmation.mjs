import assert from "node:assert/strict";
import {test} from "node:test";
import {spawnSync} from "node:child_process";
import {mkdtemp,rm,mkdir,readdir,readFile,writeFile,chmod,symlink,stat}
  from "node:fs/promises";
import {join} from "node:path";
import {tmpdir} from "node:os";
import {fileURLToPath} from "node:url";
const child=fileURLToPath(new URL(
  "./fixtures/simple_m3d5b4_child.mjs",import.meta.url));
function run(root,opts={},env={}){
  const p=spawnSync(process.execPath,[child],{
    input:JSON.stringify({sandboxRoot:root,...opts})+"\n",
    encoding:"utf8",timeout:20000,
    env:{...process.env,HOME:root,FINANCEW_DISPOSABLE_TEST:"yes",...env}
  });
  assert.equal(p.stderr,"",p.stderr);
  assert.ok(p.status===0 || p.status===47,"exit "+p.status);
  const parsed=JSON.parse(p.stdout.trim());
  return {...parsed,exitCode:p.status};
}
async function fixture(fn){
  const root=await mkdtemp(join(tmpdir(),"financew-m3d5b4-fixture-"));
  await chmod(root,0o700);
  try{await fn(root);}finally{await rm(root,{force:true,recursive:true});}
}
function isNoWrite(x){
  assert.equal(x.canSave,false);
  assert.equal(x.writeAllowed,false);
  assert.equal(x.dispatched,false);
  assert.equal("requestId" in x,false);
  assert.equal("command" in x,false);
  assert.equal("inputFrame" in x,false);
}
test("confirmed request ID survives child exit; public receipt never contains request ID",async()=>{
  await fixture(async root=>{
    const first=run(root),{receiptId}=first.staged;
    assert.equal(first.sealed.ok,true,JSON.stringify(first.sealed));
    assert.equal(first.staged.ok,true);
    assert.equal(first.sealed.receiptId,receiptId);
    assert.match(receiptId,/^[0-9a-f]{32}$/);
    assert.match(first.staged.confirmationPrompt,/^CONFIRM CATEGORY [0-9a-f]{16}$/);
    for(const x of [first.staged,first.sealed])isNoWrite(x);
    assert.equal(first.dispatch.reason,"production-dispatch-hard-hold");
    const path=join(root,"holds","hold-"+receiptId+".json");
    const rec=JSON.parse(await readFile(path,"utf8"));
    assert.equal(rec.state,"confirmed-held-no-dispatch");
    assert.match(rec.requestId,/^[0-9a-f]{32}$/);
    assert.notEqual(rec.requestId,receiptId);
    assert.match(rec.digest,/^[0-9a-f]{64}$/);
    assert.equal((await stat(path)).mode&0o077,0);
    const raw=await readFile(path,"utf8");
    for(const forbidden of ["Imaginary Groceries","fictional-checking",
      "groceries","amountCents","description"])
      assert.equal(raw.includes(forbidden),false,forbidden);
    const after=run(root,{mode:"inspect",receiptId});
    assert.equal(after.ok,true,JSON.stringify(after));
    assert.equal(after.reason,"durable-receipt-observed-no-dispatch");
    isNoWrite(after);
    assert.equal((await readdir(join(root,"holds"))).length,1);
  });
});
test("crash after confirmed record fsync but before ACK retains inspectable identity",async()=>{
  await fixture(async root=>{
    const lost=run(root,{mode:"crash-after-seal"});
    assert.equal(lost.exitCode,47);
    const receiptId=lost.staged.receiptId;
    assert.equal(lost.staged.ok,true);
    const recovered=run(root,{mode:"inspect",receiptId});
    assert.equal(recovered.ok,true,JSON.stringify(recovered));
    assert.equal(recovered.reason,"durable-receipt-observed-no-dispatch");
    isNoWrite(recovered);
    assert.equal((await readdir(join(root,"holds"))).length,1);
  });
});
test("two separately confirmed identical purchases are allowed, not globally body-deduplicated",async()=>{
  await fixture(async root=>{
    const first=run(root),second=run(root);
    assert.equal(first.sealed.ok,true);
    assert.equal(second.sealed.ok,true);
    assert.notEqual(first.sealed.receiptId,second.sealed.receiptId);
    const names=await readdir(join(root,"holds"));
    assert.equal(names.length,2);
    for(const receiptId of [first.sealed.receiptId,second.sealed.receiptId]){
      const inspect=run(root,{mode:"inspect",receiptId});
      assert.equal(inspect.ok,true);
      isNoWrite(inspect);
    }
  });
});
test("double confirmation in one process can durably seal only one receipt",async()=>{
  await fixture(async root=>{
    const out=run(root,{mode:"double"});
    assert.equal(out.results.filter(x=>x.ok).length,1,JSON.stringify(out));
    assert.equal(out.results.filter(x=>!x.ok).length,1);
    assert.equal(out.dispatch.reason,"production-dispatch-hard-hold");
    assert.equal((await readdir(join(root,"holds"))).length,1);
  });
});
test("cancel and wrong confirmation cannot create a durable receipt",async()=>{
  for(const mode of ["cancel","wrong"]){
    await fixture(async root=>{
      const x=run(root,{mode});
      assert.equal(x.staged.ok,true);
      if(mode==="cancel")assert.equal(x.canceled.ok,true);
      else assert.equal(x.denied.reason,"confirmation-mismatch");
      assert.equal(x.after.ok,false);
      await assert.rejects(readdir(join(root,"holds")),{code:"ENOENT"});
    });
  }
});
test("stale amount/category/visibility/budget/source changes fail before any write",async()=>{
  for(const modify of ["amount","category","hidden","budget","source"]){
    await fixture(async root=>{
      const x=run(root,{modify});
      assert.equal(x.staged.ok,true);
      assert.equal(x.sealed.ok,false,JSON.stringify(x));
      await assert.rejects(readdir(join(root,"holds")),{code:"ENOENT"});
    });
  }
});
test("read 5007 cannot be treated as writer 5006 and forged source witness refuses",async()=>{
  await fixture(async root=>{
    for(const override of [
      {readerEndpoint:"http://127.0.0.1:5007"},
      {writerEndpoint:"http://localhost:5006"},
      {writerSourceKey:"a".repeat(64)}
    ]){
      const x=run(root,{override});
      assert.equal(x.ok,false,JSON.stringify(x));
      await assert.rejects(readdir(join(root,"holds")),{code:"ENOENT"});
    }
  });
});
test("fixture gating requires exact private HOME and explicit test flag",async()=>{
  await fixture(async root=>{
    for(const env of [
      {FINANCEW_DISPOSABLE_TEST:"no"},
      {HOME:tmpdir()}
    ]){
      const x=run(root,{},env);
      assert.equal(x.ok,false);
      assert.equal(x.reason,"disposable-fixture-required");
    }
    const x=run(root+"/../anything");
    assert.equal(x.ok,false);
    assert.equal(x.reason,"disposable-fixture-required");
    await assert.rejects(readdir(join(root,"holds")),{code:"ENOENT"});
  });
});
test("untrusted custody symlink, writable directory and existing lock refuse",async()=>{
  await fixture(async root=>{
    const holds=join(root,"holds");
    const other=join(root,"other");
    await mkdir(other,{mode:0o700});
    await symlink(other,holds);
    assert.equal(run(root).sealed.reason,"untrusted-disposable-custody");
    await rm(holds);
    await mkdir(holds,{mode:0o770});
    assert.equal(run(root).sealed.reason,"untrusted-disposable-custody");
    await chmod(holds,0o700);
    await writeFile(join(holds,".confirmation-lock"),"stale\n",{mode:0o600});
    assert.equal(run(root).sealed.reason,
      "confirmation-in-progress-or-recovery-required");
  });
});
test("tampered existing receipt refuses recovery and leaves lock for manual investigation",async()=>{
  for(const variant of ["world-readable","symlink","unknown-entry"]){
    await fixture(async root=>{
      const first=run(root);
      assert.equal(first.sealed.ok,true);
      const holds=join(root,"holds");
      const name="hold-"+first.sealed.receiptId+".json";
      const file=join(holds,name);
      if(variant==="world-readable")await chmod(file,0o644);
      else if(variant==="symlink"){
        const contents=await readFile(file);
        await rm(file);
        await writeFile(join(root,"external"),contents,{mode:0o600});
        await symlink(join(root,"external"),file);
      }else await writeFile(join(holds,"surprise"),"unknown\n",{mode:0o600});
      const recovered=run(root,{mode:"inspect",receiptId:first.sealed.receiptId});
      assert.equal(recovered.ok,false,JSON.stringify(recovered));
      const another=run(root);
      assert.equal(another.sealed.ok,false);
      assert.ok((await readdir(holds)).includes(".confirmation-lock"));
    });
  }
});
test("valid receipt with changed current review cannot recover as matching",async()=>{
  for(const modify of ["amount","category","hidden","budget","source"]){
    await fixture(async root=>{
      const x=run(root);
      assert.equal(x.sealed.ok,true);
      const observed=run(root,{
        mode:"inspect",receiptId:x.sealed.receiptId,modify
      });
      assert.equal(observed.ok,false,JSON.stringify(observed));
      isNoWrite(observed);
    });
  }
});
test("nonexistent receipt is blocked and never created or retried",async()=>{
  await fixture(async root=>{
    const x=run(root);
    assert.equal(x.sealed.ok,true);
    const wrong=run(root,{mode:"inspect",receiptId:"f".repeat(32)});
    assert.equal(wrong.ok,false);
    assert.equal(wrong.reason,"receipt-not-found");
    isNoWrite(wrong);
    assert.equal((await readdir(join(root,"holds"))).length,1);
  });
});

test("cancel racing a started seal cannot erase or reinterpret durable custody",async()=>{
  await fixture(async root=>{
    const x=run(root,{mode:"cancel-race"});
    assert.equal(x.staged.ok,true);
    assert.equal(x.cancel.ok,false);
    assert.equal(x.cancel.reason,"in-flight-custody-recovery-required");
    assert.equal(x.result.ok,true,JSON.stringify(x));
    const inspection=run(root,{mode:"inspect",receiptId:x.staged.receiptId});
    assert.equal(inspection.ok,true);
    isNoWrite(inspection);
    assert.equal((await readdir(join(root,"holds"))).length,1);
  });
});
test("tampered sealed private request ID or digest cannot pass restart inspection",async()=>{
  for(const variant of ["requestId","digest"]){
    await fixture(async root=>{
      const x=run(root);
      assert.equal(x.sealed.ok,true);
      const file=join(root,"holds","hold-"+x.sealed.receiptId+".json");
      const record=JSON.parse(await readFile(file,"utf8"));
      record[variant]=(variant==="requestId"?"f".repeat(32):"d".repeat(64));
      await writeFile(file,JSON.stringify(record)+"\n",{mode:0o600});
      const inspected=run(root,{mode:"inspect",receiptId:x.sealed.receiptId});
      assert.equal(inspected.ok,false);
      assert.equal(inspected.reason,"receipt-financial-details-changed");
      isNoWrite(inspected);
    });
  }
});
