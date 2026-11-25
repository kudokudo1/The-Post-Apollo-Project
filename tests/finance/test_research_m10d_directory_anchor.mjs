import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {openResearchDirectoryAnchor,ResearchAnchorRefusal} from "../../scripts/finance/research_directory_anchor.mjs";

// All files in private ephemeral OS temp. No real XDG or user's files.
const root=fs.mkdtempSync(path.join(os.tmpdir(),"finance-research-m10d-"));
fs.chmodSync(root,0o700);
const when=code=>e=>e instanceof ResearchAnchorRefusal && e.message===code;
const mk=(p)=>fs.mkdirSync(p,{mode:0o700});
const file=(dir,content)=>fs.writeFileSync(path.join(dir,"investigations.json"),content,{mode:0o600});
try {
  const original=path.join(root,"original");mk(original);
  const store=path.join(original,"research");mk(store);
  const secret='{"schemaVersion":1,"revision":8,"private":"DO NOT DISPLAY"}\n';
  file(store,secret);
  const anchor=openResearchDirectoryAnchor(store);
  assert.equal(anchor.readOnly,true);
  assert.equal(anchor.canWrite,false);
  assert.equal(anchor.canUnlock,false);
  assert.equal(anchor.canRetry,false);
  assert.deepEqual(anchor.readFile("investigations.json"),secret);
  assert.equal(anchor.readFile("investigations.lock"),null);
  const identity=anchor.directoryIdentity;
  assert.ok(Number.isSafeInteger(identity.inode));
  assert.throws(()=>anchor.readFile("../../outside"),when("INVALID_READ_REQUEST"));
  assert.throws(()=>anchor.readFile("arbitrary.txt"),when("INVALID_READ_REQUEST"));
  assert.throws(()=>anchor.readFile("investigations.json",500001),when("INVALID_READ_REQUEST"));
  console.log("M10D_CHECK // PINNED_READ_ONLY_STORE_IDENTITY");

  // After acquiring a real dir handle, moving an ancestor and replacing
  // its old path with a symlink must not redirect reads into the decoy.
  const outside=path.join(root,"outside");mk(outside);
  const evilStore=path.join(outside,"research");mk(evilStore);
  file(evilStore,"EVIL DATA\n");
  const moved=path.join(root,"moved");
  fs.renameSync(original,moved);
  fs.symlinkSync(outside,original,"dir");
  assert.deepEqual(anchor.directoryIdentity,identity);
  assert.equal(anchor.readFile("investigations.json"),secret);
  assert.throws(()=>openResearchDirectoryAnchor(store),
    when("STORAGE_PATH_UNAVAILABLE"));
  anchor.close();anchor.close();
  assert.throws(()=>anchor.readFile("investigations.json"),when("ANCHOR_CLOSED"));
  console.log("M10D_CHECK // ANCESTOR_SWAP_CANNOT_REDIRECT_PINNED_READ");

  // Prove the same defense while an ancestor replacement occurs DURING
  // descriptor traversal, before opening the final research component.
  const mid=path.join(root,"mid");mk(mid);
  const midStore=path.join(mid,"research");mk(midStore);
  file(midStore,"ORIGINAL MID\n");
  const decoy=path.join(root,"decoy");mk(decoy);
  const decoyStore=path.join(decoy,"research");mk(decoyStore);
  file(decoyStore,"DECOY MID\n");
  const relocated=path.join(root,"relocated");
  const originalOpen=fs.openSync;
  let swapped=false;
  fs.openSync=function(p,...args) {
    if (!swapped && typeof p==="string"
        && /^\/proc\/self\/fd\/\d+\/research$/.test(p)) {
      swapped=true;
      fs.renameSync(mid,relocated);
      fs.symlinkSync(decoy,mid,"dir");
    }
    return originalOpen.call(fs,p,...args);
  };
  let racing;
  try {racing=openResearchDirectoryAnchor(midStore);}
  finally {fs.openSync=originalOpen;}
  assert.equal(swapped,true);
  assert.equal(racing.readFile("investigations.json"),"ORIGINAL MID\n");
  racing.close();
  assert.throws(()=>openResearchDirectoryAnchor(midStore),
    when("STORAGE_PATH_UNAVAILABLE"));
  console.log("M10D_CHECK // LIVE_ANCESTOR_RENAME_RESOLVES_PINNED_DIR");

  // Reader is hard-fail on a file symlink or hardlink, irrespective of mode.
  const locked=path.join(root,"locked");mk(locked);
  const target=path.join(root,"target");
  fs.writeFileSync(target,"PRIVATE\n",{mode:0o600});
  fs.symlinkSync(target,path.join(locked,"investigations.json"));
  const linked=openResearchDirectoryAnchor(locked);
  assert.throws(()=>linked.readFile("investigations.json"),
    when("UNSAFE_STORAGE_FILE"));
  fs.unlinkSync(path.join(locked,"investigations.json"));
  fs.linkSync(target,path.join(locked,"investigations.json"));
  assert.throws(()=>linked.readFile("investigations.json"),
    when("UNSAFE_STORAGE_FILE"));
  linked.close();
  assert.equal(fs.readFileSync(target,"utf8"),"PRIVATE\n");
  console.log("M10D_CHECK // FILE_SYMLINK_AND_HARDLINK_REFUSED");

  const oversized=path.join(root,"oversized");mk(oversized);
  file(oversized,"A".repeat(20));
  const limited=openResearchDirectoryAnchor(oversized);
  assert.throws(()=>limited.readFile("investigations.json",19),
    when("STORAGE_FILE_LIMIT"));
  assert.equal(limited.readFile("investigations.json",20).length,20);
  limited.close();
  console.log("M10D_CHECK // STRICT_READ_LIMIT");

  const absent=path.join(root,"absent");
  assert.throws(()=>openResearchDirectoryAnchor(absent),
    when("STORAGE_PATH_UNAVAILABLE"));
  assert.equal(fs.existsSync(absent),false);
  assert.throws(()=>openResearchDirectoryAnchor("/"),
    when("INVALID_STORAGE_PATH"));
  console.log("M10D_CHECK // READ_ONLY_NEVER_CREATES_DIRECTORY");

  console.log("Finance Research M10d directory descriptor isolated native probe: PASS");
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
