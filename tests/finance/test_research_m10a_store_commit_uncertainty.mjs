import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {spawn,spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {run,Refusal} from "../../scripts/finance/research_investigation_store.mjs";

// M10a: fault injection only in freshly-created disposable directories.
// No XDG_HOME, no user data and no production research writer.
const root=fs.mkdtempSync(path.join(os.tmpdir(),"research-m10a-"));
fs.chmodSync(root,0o700);
const when=code=>e=>e instanceof Refusal && e.message===code;
const stamp="2026-11-25T12:00:00.000Z";
const cmd=(revision,id)=>({action:"create",expectedRevision:revision,
  id,title:"Disposable "+id,question:"What is documented?",timestamp:stamp});
const withPatched=(method,replacement,body)=>{
  const original=fs[method];
  fs[method]=function(...args){return replacement(original,args);}
  try {return body();} finally {fs[method]=original;}
};
function checkLock(dir) {
  const name=path.join(dir,"investigations.lock");
  assert.ok(fs.existsSync(name),"ambiguous commit must preserve lock");
  assert.ok(fs.lstatSync(name).isFile());
  assert.equal(fs.lstatSync(name).mode&0o077,0);
  return name;
}
function tryWrite(dir,expected) {
  assert.throws(()=>run(cmd(expected,"blocked"),dir),when("WRITE_BUSY"));
}
try {
  // Normal, non-ambiguous operation persists and releases its own lock.
  const normal=path.join(root,"normal");
  assert.equal(run(cmd(0,"initial"),normal).revision,1);
  assert.equal(fs.existsSync(path.join(normal,"investigations.lock")),false);
  assert.equal(run({action:"list"},normal).revision,1);
  assert.throws(()=>run(cmd(0,"stale"),normal),when("STALE_REVISION"));
  assert.equal(fs.existsSync(path.join(normal,"investigations.lock")),false);

  // Commit may have completed, but the directory fsync fails after rename.
  // Keep the durable lock even when a new revision can be read.
  const post=path.join(root,"post-rename");
  let dirSyncs=0;
  assert.throws(()=>withPatched("fsyncSync",(real,[fd])=>{
    if(fs.fstatSync(fd).isDirectory() && ++dirSyncs===2)
      throw new Error("DISPOSABLE_DIR_FSYNC_FAILURE");
    return real.call(fs,fd);
  },()=>run(cmd(0,"post"),post)),when("COMMIT_OUTCOME_UNKNOWN"));
  assert.equal(dirSyncs,2);
  checkLock(post);
  assert.equal(run({action:"list"},post).revision,1);
  tryWrite(post,1);
  console.log("M10A_CHECK // POST_RENAME_UNKNOWN_RETAINS_LOCK");

  // rename itself can fail without establishing whether it committed.
  // Conservative behavior keeps a stranded lock and forbids retry.
  const rename=path.join(root,"rename");
  assert.throws(()=>withPatched("renameSync",(_real,_args)=>{
    throw new Error("DISPOSABLE_UNKNOWN_RENAME");
  },()=>run(cmd(0,"rename"),rename)),when("COMMIT_OUTCOME_UNKNOWN"));
  checkLock(rename);
  assert.equal(run({action:"list"},rename).revision,0);
  tryWrite(rename,0);
  console.log("M10A_CHECK // RENAME_AMBIGUITY_RETAINS_LOCK");

  // Failure before entering the rename window is safe to clean up:
  // no data has been committed, and the next controlled action may proceed.
  const pre=path.join(root,"pre-rename");
  let regularSyncs=0;
  assert.throws(()=>withPatched("fsyncSync",(real,[fd])=>{
    if(fs.fstatSync(fd).isFile() && ++regularSyncs===2)
      throw new Error("DISPOSABLE_PRECOMMIT_TEMP_FSYNC_FAILURE");
    return real.call(fs,fd);
  },()=>run(cmd(0,"pre"),pre)),/DISPOSABLE_PRECOMMIT_TEMP_FSYNC_FAILURE/);
  assert.equal(regularSyncs,2);
  assert.equal(fs.existsSync(path.join(pre,"investigations.lock")),false);
  assert.equal(run({action:"list"},pre).revision,0);
  assert.equal(run(cmd(0,"recovered"),pre).revision,1);
  console.log("M10A_CHECK // PRECOMMIT_FAILURE_SAFE_TO_RELEASE");

  // Untrusted replacement of the lock must not be unlinked as our lock.
  const swap=path.join(root,"swapped-lock");
  assert.throws(()=>withPatched("renameSync",(real,args)=>{
    const result=real.apply(fs,args);
    const lock=path.join(swap,"investigations.lock");
    fs.unlinkSync(lock);
    fs.writeFileSync(lock,"REPLACED",{mode:0o600,flag:"wx"});
    return result;
  },()=>run(cmd(0,"swapped"),swap)),when("UNSAFE_LOCK"));
  assert.equal(fs.readFileSync(checkLock(swap),"utf8"),"REPLACED");
  assert.equal(run({action:"list"},swap).revision,1);
  console.log("M10A_CHECK // REPLACED_LOCK_NEVER_DELETED");

  // Reject a symlinked parent BEFORE creating any data directories in
  // the other location. The old recursive mkdir followed this symlink.
  const outside=path.join(root,"outside");
  fs.mkdirSync(outside,{mode:0o700});
  const redirect=path.join(root,"redirect");
  fs.symlinkSync(outside,redirect,"dir");
  assert.throws(()=>run(cmd(0,"escape"),
    path.join(redirect,"created","research")),when("UNSAFE_DIRECTORY"));
  assert.equal(fs.existsSync(path.join(outside,"created")),false);
  assert.throws(()=>run({action:"list"},
    path.join(redirect,"created","research")),when("UNSAFE_DIRECTORY"));
  console.log("M10A_CHECK // ANCESTOR_SYMLINK_CANNOT_CREATE_STORE");

  // Refuse other private files hardlinked into Research storage, even if
  // their owner and 0600 mode would otherwise look normal.
  const hard=path.join(root,"hardlink");
  fs.mkdirSync(hard,{mode:0o700});
  const borrowed=path.join(root,"borrowed.json");
  fs.writeFileSync(borrowed,'{"schemaVersion":1,"revision":0,"investigations":[]}\\n',
    {mode:0o600});
  fs.linkSync(borrowed,path.join(hard,"investigations.json"));
  assert.throws(()=>run({action:"list"},hard),when("UNSAFE_FILE"));
  assert.equal(fs.readFileSync(borrowed,"utf8"),
    fs.readFileSync(path.join(hard,"investigations.json"),"utf8"));
  console.log("M10A_CHECK // HARDLINK_STORE_REFUSED");

  // Replacing the file after lstat but before O_NOFOLLOW open must not
  // substitute a different private inode in a read-only snapshot.
  const race=path.join(root,"inode-race");
  run(cmd(0,"original"),race);
  const file=path.join(race,"investigations.json");
  const replacement=path.join(race,"replacement.json");
  fs.copyFileSync(file,replacement);
  assert.throws(()=>withPatched("openSync",(real,args)=>{
    if(args[0]===file) fs.renameSync(replacement,file);
    return real.apply(fs,args);
  },()=>run({action:"list"},race)),when("UNSAFE_FILE"));
  assert.equal(run({action:"list"},race).revision,1);
  console.log("M10A_CHECK // PREOPEN_INODE_SWAP_REFUSED");

  // A child must finish on one newline-terminated frame even when its
  // parent leaves stdin open. Unlike old readFileSync(0), this does not
  // wait for Quickshell to close the transport.
  const script=fileURLToPath(new URL(
    "../../scripts/finance/research_investigation_store.mjs",import.meta.url));
  const env={...process.env,XDG_DATA_HOME:path.join(root,"isolated-xdg")};
  const child=spawn(process.execPath,[script],{stdio:["pipe","pipe","pipe"],env});
  let out="",err="",timer;
  child.stdout.setEncoding("utf8");child.stderr.setEncoding("utf8");
  child.stdout.on("data",x=>out+=x);child.stderr.on("data",x=>err+=x);
  const done=new Promise((resolve,reject)=>{
    child.on("close",resolve);child.on("error",reject);
  });
  child.stdin.write('{"action":"list"}\n');
  const code=await Promise.race([done,new Promise((_,reject)=>{
    timer=setTimeout(()=>{child.kill("SIGKILL");reject(Error("CHILD_WAITED_FOR_EOF"));},3000);
  })]);
  clearTimeout(timer);child.stdin.destroy();
  assert.equal(code,0,err);
  assert.equal(err,"");
  assert.match(out,/^FINANCE_RESEARCH_STORE_RESULT \{"schemaVersion":1,"revision":0,/);
  assert.equal(fs.existsSync(env.XDG_DATA_HOME),false);
  console.log("M10A_CHECK // ONE_FRAME_COMPLETES_WITHOUT_EOF");

  const double=spawnSync(process.execPath,[script],{
    input:'{"action":"list"}\n{"action":"list"}\n',encoding:"utf8",env,timeout:3000
  });
  assert.equal(double.status,1);
  assert.equal(double.stdout,"");
  assert.match(double.stderr,/FINANCE_RESEARCH_STORE_ERROR INVALID_INPUT_FRAME/);
  const huge=spawnSync(process.execPath,[script],{
    input:"x".repeat(9000)+"\n",encoding:"utf8",env,timeout:3000
  });
  assert.equal(huge.status,1);
  assert.equal(huge.stdout,"");
  assert.match(huge.stderr,/FINANCE_RESEARCH_STORE_ERROR INVALID_INPUT_FRAME/);
  assert.equal(fs.existsSync(env.XDG_DATA_HOME),false);
  console.log("M10A_CHECK // OVERSIZE_AND_MULTIFRAME_REJECTED");

  console.log("Finance Research M10a failure-boundary and bounded-frame tests: PASS");
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
