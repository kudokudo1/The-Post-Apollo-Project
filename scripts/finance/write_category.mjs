#!/usr/bin/env node
// FinanceW Categories M2: DISCONNECTED guarded Actual writer.
// Not called by Quickshell and NEVER provisions operator authorization.
// Shares the FinanceW D9/D12/D17 global lock and recovery journal.
import {readFile,writeFile,readdir,lstat,mkdir,open,mkdtemp,rm,chmod}
  from "node:fs/promises";
import {homedir,tmpdir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {readActualServerURL} from "./source_config.mjs";
import {CategoryRefusal,validateCategoryCommand,executeCategory}
  from "./category_guard.mjs";

const config=join(homedir(),".config","financew");
const journalDir=join(homedir(),".local","state","financew","operations");
const refuse=code=>{throw new CategoryRefusal(code);};
const errorCode=error=>error instanceof CategoryRefusal
  ? error.code : "operation-failed";

async function privateFile(path) {
  let info;
  try{info=await lstat(path);}catch{refuse("private-file-unavailable");}
  if(!info.isFile() || (info.mode & 0o077)!==0)
    refuse("unsafe-private-file");
  return (await readFile(path,"utf8")).trim();
}
async function commandFromStdin() {
  let raw="";
  for await (const chunk of process.stdin) {
    raw+=chunk.toString("utf8");
    if(raw.length>4096)refuse("input-too-large");
    if(raw.includes("\n"))break;
  }
  const parts=raw.split("\n");
  if(parts.length!==2 || parts[1]!=="")refuse("invalid-input-frame");
  let input;
  try{input=JSON.parse(parts[0]);}catch{refuse("invalid-json");}
  return validateCategoryCommand(input);
}
async function fsyncDirectory(path) {
  const handle=await open(path,"r");
  try{await handle.sync();}finally{await handle.close();}
}
async function run() {
  // Only operator-provisioned, mode-0600, exact-marker permits are accepted.
  let permit;
  try{permit=await privateFile(join(config,"category-writes-enabled"));}
  catch{refuse("writes-disabled");}
  if(permit!=="FINANCEW_CATEGORY_WRITES_APPROVED")
    refuse("writes-disabled");
  const command=await commandFromStdin();
  await mkdir(journalDir,{recursive:true,mode:0o700});
  const dirInfo=await lstat(journalDir);
  if(!dirInfo.isDirectory() || (dirInfo.mode & 0o077)!==0)
    refuse("unsafe-journal-directory");
  const lockPath=join(journalDir,".write-lock");
  let lock;
  try{lock=await open(lockPath,"wx",0o600);}
  catch{refuse("write-in-progress-or-recovery-needed");}
  let api=null,working=null,attempted=false;
  try {
    const serverURL=await readActualServerURL();
    if(serverURL!=="http://127.0.0.1:5006")
      refuse("unsupported-write-server");
    const password=await privateFile(join(config,"actual-password"));
    const syncId=await privateFile(join(config,"actual-sync-id"));
    if(!/^[A-Za-z0-9-]{8,80}$/.test(syncId))
      refuse("invalid-sync-id");
    const sourceKey=createHash("sha256")
      .update(serverURL+"\0"+syncId).digest("hex");
    if(command.sourceKey!==sourceKey)refuse("budget-source-changed");

    const names=await readdir(journalDir);
    // Uncertain transaction, funding, allocation or category operations
    // block every subsequent financial write. Never clean up on startup.
    for(const filename of names) {
      if(!filename.endsWith(".json"))continue;
      let entry;
      try{entry=JSON.parse(await privateFile(join(journalDir,filename)));}
      catch{refuse("recovery-needed");}
      if(!entry || entry.status!=="committed")refuse("recovery-needed");
    }
    const journalName="category-"+command.requestId+".json";
    if(names.includes(journalName))refuse("operation-already-attempted");
    const path=join(journalDir,journalName);
    const hash=createHash("sha256").update(JSON.stringify(command)).digest("hex");
    const recordAttempt=async()=>{
      let file;
      try{file=await open(path,"wx",0o600);}
      catch{refuse("operation-already-attempted");}
      try {
        await file.writeFile(JSON.stringify({
          version:1,status:"attempted",hash,
          action:"category:"+command.mode,
          attemptedAt:new Date().toISOString()
        })+"\n");
        await file.sync();
        await fsyncDirectory(journalDir);
        attempted=true;
      }finally{await file.close();}
    };

    working=await mkdtemp(join(tmpdir(),"financew-category-"));
    await chmod(working,0o700);
    api=await import("@actual-app/api");
    await api.init({dataDir:working,serverURL,password});
    const encryptionPath=process.env.ACTUAL_ENCRYPTION_PASSWORD_FILE;
    const encryptionPassword=encryptionPath
      ? await privateFile(encryptionPath) : null;
    await api.downloadBudget(syncId,encryptionPassword
      ? {password:encryptionPassword}:undefined);
    const result=await executeCategory({api,input:command,recordAttempt});
    await writeFile(path,JSON.stringify({
      version:1,status:"committed",hash,
      action:"category:"+command.mode,
      completedAt:new Date().toISOString()
    })+"\n",{mode:0o600});
    const receipt=await open(path,"r");
    try{await receipt.sync();}finally{await receipt.close();}
    await fsyncDirectory(journalDir);
    return result.status;
  }catch(error){
    if(attempted)return "uncertain";
    throw error;
  }finally{
    if(api){try{await api.shutdown();}catch{/* Never retry */}}
    if(working)await rm(working,{recursive:true,force:true});
    if(lock){await lock.close();await rm(lockPath,{force:true});}
  }
}
try{
  const status=await run();
  process.stdout.write("FINANCEW_CATEGORY_RESULT "+status+"\n");
}catch(error){
  process.stdout.write("FINANCEW_CATEGORY_RESULT blocked:"+errorCode(error)+"\n");
  process.exitCode=1;
}
