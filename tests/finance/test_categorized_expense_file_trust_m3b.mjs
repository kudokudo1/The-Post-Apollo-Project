import {test} from "node:test";
import assert from "node:assert/strict";
import {mkdtemp,mkdir,writeFile,rename,symlink,rm,chmod,link}
  from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {
  openTrustedDirectory,readPrivateEntry,readTrustedPrivateFile,
  FinanceFileTrustRefusal
} from "../../scripts/finance/categorized_expense_file_trust.mjs";

async function fixture(){
  const home=await mkdtemp(join(tmpdir(),"financew-m3b-filetrust-fictional-"));
  const config=join(home,".config","financew");
  await mkdir(config,{recursive:true,mode:0o700});
  await writeFile(join(config,"permit"),"original-private\n",{mode:0o600});
  return {home,config};
}
test("private file reads reject symlinked leaf and parent",async()=>{
  const f=await fixture();
  try {
    assert.equal(await readTrustedPrivateFile(join(f.config,"permit")),
      "original-private");
    const old=join(f.config,"permit");
    await rename(old,join(f.config,"real-permit"));
    await symlink("real-permit",old);
    await assert.rejects(readTrustedPrivateFile(old));
    await rename(f.config,f.config+"-real");
    await symlink("financew-real",f.config);
    await assert.rejects(readTrustedPrivateFile(join(f.config,"real-permit")));
  }finally{await rm(f.home,{recursive:true,force:true});}
});
test("verified directory descriptor stays on original inode after path swap",async()=>{
  const f=await fixture();
  const dir=await openTrustedDirectory(f.config,{privateLeaf:true});
  try{
    await rename(f.config,f.config+"-old");
    await mkdir(f.config,{mode:0o700});
    await writeFile(join(f.config,"permit"),"replacement-private\n",{mode:0o600});
    assert.equal(await readPrivateEntry(dir,"permit"),"original-private");
    assert.equal(await readTrustedPrivateFile(join(f.config,"permit")),
      "replacement-private");
  }finally{await dir.close();await rm(f.home,{recursive:true,force:true});}
});
test("world-readable files, hardlinks and unsafe parent permissions fail closed",async()=>{
  const f=await fixture();
  try{
    await chmod(join(f.config,"permit"),0o644);
    await assert.rejects(readTrustedPrivateFile(join(f.config,"permit")),
      e=>e instanceof FinanceFileTrustRefusal && e.code==="unsafe-private-file");
    await chmod(join(f.config,"permit"),0o600);
    await link(join(f.config,"permit"),join(f.config,"duplicate-link"));
    await assert.rejects(readTrustedPrivateFile(join(f.config,"permit")),
      e=>e instanceof FinanceFileTrustRefusal && e.code==="unsafe-private-file");
    await rm(join(f.config,"duplicate-link"));
    await chmod(join(f.home,".config"),0o770);
    await assert.rejects(readTrustedPrivateFile(join(f.config,"permit")),
      e=>e instanceof FinanceFileTrustRefusal && e.code==="untrusted-directory");
    await chmod(join(f.home,".config"),0o700);
    assert.equal(await readTrustedPrivateFile(join(f.config,"permit")),
      "original-private");
  }finally{await rm(f.home,{recursive:true,force:true});}
});
test("journal directory refuses every symlink component, even when creating",async()=>{
  const f=await fixture();
  try{
    const local=join(f.home,".local");
    const other=join(f.home,"other");
    await mkdir(other,{mode:0o700});
    await symlink(other,local);
    await assert.rejects(openTrustedDirectory(
      join(local,"state","financew","operations"),{
        create:true,privateLeaf:true
      }));
    // Never wrote into the linked tree by accident.
    await assert.rejects(readTrustedPrivateFile(join(other,"state","permit")));
  }finally{await rm(f.home,{recursive:true,force:true});}
});
