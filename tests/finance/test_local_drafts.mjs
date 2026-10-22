import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {mkdtempSync,readFileSync,writeFileSync,chmodSync,statSync,rmSync,
  mkdirSync,symlinkSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";

const cli=fileURLToPath(new URL("../../scripts/finance/local_drafts.mjs",import.meta.url));
const keyA="a".repeat(64),keyB="b".repeat(64),month="2026-10";
function setup() {
  const home=mkdtempSync(join(tmpdir(),"financew-local-drafts-"));
  return {home,dir:join(home,".local","state","financew","drafts"),
    index:join(home,".local","state","financew","drafts","index.json")};
}
function invoke(f,cmd) {
  return spawnSync(process.execPath,[cli],{
    encoding:"utf8",input:JSON.stringify(cmd)+"\n",timeout:10000,
    env:{...process.env,HOME:f.home,ACTUAL_SERVER_URL:"",
      ACTUAL_SYNC_ID:"",ACTUAL_PASSWORD_FILE:"",ACTUAL_SYNC_ID_FILE:""}
  });
}
function result(f,cmd) {
  const r=invoke(f,cmd);
  assert.equal(r.status,0,r.stderr);
  assert.equal(r.stderr,"");
  const lines=r.stdout.split("\n").filter(Boolean);
  assert.equal(lines.length,1);
  assert.ok(lines[0].startsWith("FINANCEW_DRAFT_RESULT "));
  return JSON.parse(lines[0].slice("FINANCEW_DRAFT_RESULT ".length));
}
function draft(sourceKey=keyA) {return {
  sourceKey,month,accountId:"fictional-account-1",
  dateText:"",payeeText:"Unfinished fictional item",
  amountText:"",direction:"expense"
};}
function cleanup(f) {rmSync(f.home,{recursive:true,force:true});}

test("save, reload, update and delete unfinished drafts without Actual authorization",()=>{
  const f=setup();
  try {
    const start=result(f,{action:"list",sourceKey:keyA,month});
    assert.deepEqual(start,{revision:0,drafts:[]});
    const saved=result(f,{action:"upsert",sourceKey:keyA,month,
      expectedRevision:0,draft:draft()});
    assert.equal(saved.revision,1);
    assert.equal(saved.drafts.length,1);
    assert.equal(saved.drafts[0].payeeText,"Unfinished fictional item");
    assert.equal(saved.drafts[0].amountText,"");
    assert.equal(statSync(f.index).mode & 0o077,0);
    assert.equal(statSync(f.dir).mode & 0o077,0);
    const id=saved.drafts[0].id;
    assert.ok(/^[0-9a-f-]{36}$/.test(id));
    assert.deepEqual(result(f,{action:"list",sourceKey:keyA,month}),saved);
    const changed=result(f,{action:"upsert",sourceKey:keyA,month,id,
      expectedRevision:1,draft:{...draft(),payeeText:"After reboot",amountText:"8.40"}});
    assert.equal(changed.revision,2);
    assert.equal(changed.drafts.length,1);
    assert.equal(changed.drafts[0].id,id);
    assert.equal(changed.drafts[0].amountText,"8.40");
    const deleted=result(f,{action:"delete",sourceKey:keyA,month,id,
      expectedRevision:2});
    assert.equal(deleted.revision,3);
    assert.deepEqual(deleted.drafts,[]);
    assert.deepEqual(JSON.parse(readFileSync(f.index,"utf8")).drafts,[]);
  } finally {cleanup(f);}
});

test("drafts are isolated by source and month, refusing cross-context delete",()=>{
  const f=setup();
  try {
    const first=result(f,{action:"upsert",sourceKey:keyA,month,
      expectedRevision:0,draft:draft()});
    const id=first.drafts[0].id;
    assert.deepEqual(result(f,{action:"list",sourceKey:keyB,month}).drafts,[]);
    assert.deepEqual(result(f,{action:"list",sourceKey:keyA,month:"2026-11"}).drafts,[]);
    const wrong=invoke(f,{action:"delete",sourceKey:keyB,month,
      expectedRevision:1,id});
    assert.equal(wrong.status,1);
    assert.match(wrong.stderr,/FINANCEW_DRAFT_ERROR draft-not-found/);
    assert.equal(result(f,{action:"list",sourceKey:keyA,month}).drafts.length,1);
  } finally {cleanup(f);}
});

test("stale revision and malformed record never overwrite saved data",()=>{
  const f=setup();
  try {
    result(f,{action:"upsert",sourceKey:keyA,month,
      expectedRevision:0,draft:draft()});
    const stale=invoke(f,{action:"upsert",sourceKey:keyA,month,
      expectedRevision:0,draft:draft()});
    assert.equal(stale.status,1);
    assert.match(stale.stderr,/FINANCEW_DRAFT_ERROR stale-index/);
    const bad=invoke(f,{action:"upsert",sourceKey:keyA,month,
      expectedRevision:1,draft:{...draft(),payeeText:"invalid\nsecret"}});
    assert.equal(bad.status,1);
    assert.match(bad.stderr,/FINANCEW_DRAFT_ERROR invalid-draft/);
    assert.equal(result(f,{action:"list",sourceKey:keyA,month}).drafts.length,1);
  } finally {cleanup(f);}
});

test("unsafe permissions or symlink storage refuse without following target",()=>{
  const f=setup();
  try {
    result(f,{action:"upsert",sourceKey:keyA,month,
      expectedRevision:0,draft:draft()});
    chmodSync(f.index,0o644);
    const bad=invoke(f,{action:"list",sourceKey:keyA,month});
    assert.equal(bad.status,1);
    assert.match(bad.stderr,/FINANCEW_DRAFT_ERROR unsafe-index/);
    rmSync(f.index);
    const elsewhere=join(f.home,"external.json");
    writeFileSync(elsewhere,JSON.stringify({private:true}),{mode:0o600});
    symlinkSync(elsewhere,f.index);
    const linked=invoke(f,{action:"list",sourceKey:keyA,month});
    assert.equal(linked.status,1);
    assert.match(linked.stderr,/FINANCEW_DRAFT_ERROR unsafe-index/);
    assert.equal(JSON.parse(readFileSync(elsewhere,"utf8")).private,true);
  } finally {cleanup(f);}
});

test("malformed JSON refuses without erasing or reinitializing existing storage",()=>{
  const f=setup();
  try {
    mkdirSync(f.dir,{recursive:true,mode:0o700});
    writeFileSync(f.index,"{bad-json",{mode:0o600});
    const r=invoke(f,{action:"upsert",sourceKey:keyA,month,
      expectedRevision:0,draft:draft()});
    assert.equal(r.status,1);
    assert.match(r.stderr,/FINANCEW_DRAFT_ERROR corrupt-index/);
    assert.equal(readFileSync(f.index,"utf8"),"{bad-json");
  } finally {cleanup(f);}
});
