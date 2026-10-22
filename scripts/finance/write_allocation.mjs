#!/usr/bin/env node
// D12c: guarded category allocation writer. NOT connected to Quickshell.
// Separate operator permit from transaction-writes-enabled. No argv secrets,
// no retry, shared global finance operation lock and recovery journal with D9.
import {readFile,writeFile,readdir,lstat,mkdir,open,mkdtemp,rm,chmod}
  from "node:fs/promises";
import {homedir,tmpdir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {readActualServerURL} from "./source_config.mjs";
import {validateAllocationCommand,executeAllocation,AllocationRefusal}
  from "./allocation_guard.mjs";

const config=join(homedir(),".config","financew");
const journalDir=join(homedir(),".local","state","financew","operations");
function refusal(code){throw new AllocationRefusal(code);}
function errorCode(error){
  return error instanceof AllocationRefusal?error.code:"operation-failed";
}
async function privateFile(path) {
  let info;
  try {info=await lstat(path);} catch {refusal("private-file-unavailable");}
  if(!info.isFile() || (info.mode & 0o077)!==0)
    refusal("unsafe-private-file");
  return (await readFile(path,"utf8")).trim();
}
async function readCommand(){
  let data="";
  for await(const chunk of process.stdin) {
    data+=chunk.toString("utf8");
    if(data.length>4096)refusal("input-too-large");
    if(data.includes("\n"))break;
  }
  const parts=data.split("\n");
  if(parts.length!==2 || parts[1]!=="")refusal("invalid-input-frame");
  let command;
  try{command=JSON.parse(parts[0]);}catch{refusal("invalid-json");}
  return validateAllocationCommand(command);
}
async function fsyncDirectory(path){
  const dir=await open(path,"r");
  try{await dir.sync();}finally{await dir.close();}
}
async function run(){
  // This file is NEVER created by the widget, tests or installation.
  // The operator must separately authorize budget allocation writes.
  let permit;
  try{permit=await privateFile(join(config,"allocation-writes-enabled"));}
  catch{refusal("writes-disabled");}
  if(permit!=="FINANCEW_ALLOCATION_WRITES_APPROVED")
    refusal("writes-disabled");
  const command=await readCommand();
  await mkdir(journalDir,{recursive:true,mode:0o700});
  const info=await lstat(journalDir);
  if(!info.isDirectory() || (info.mode & 0o077)!==0)
    refusal("unsafe-journal-directory");
  const lockPath=join(journalDir,".write-lock");
  let lock;
  try{lock=await open(lockPath,"wx",0o600);}
  catch{refusal("write-in-progress-or-recovery-needed");}
  let api,working,attempted=false;
  try{
    const serverURL=await readActualServerURL();
    if(serverURL!=="http://127.0.0.1:5006")
      refusal("unsupported-write-server");
    const password=await privateFile(join(config,"actual-password"));
    const syncId=await privateFile(join(config,"actual-sync-id"));
    if(!/^[a-zA-Z0-9-]{8,80}$/.test(syncId))refusal("invalid-sync-id");
    const expectedKey=createHash("sha256")
      .update(serverURL+"\0"+syncId).digest("hex");
    if(command.sourceKey!==expectedKey)refusal("budget-source-changed");

    // Includes D9 transaction journals. One unresolved operation anywhere
    // blocks every FinanceW write; no automatic lock or journal cleanup.
    for(const filename of await readdir(journalDir)){
      if(!filename.endsWith(".json"))continue;
      let entry;
      try{entry=JSON.parse(await privateFile(join(journalDir,filename)));}
      catch{refusal("recovery-needed");}
      if(!entry || entry.status!=="committed")refusal("recovery-needed");
    }
    const path=join(journalDir,"allocation-"+command.requestId+".json");
    const digest=createHash("sha256").update(JSON.stringify(command)).digest("hex");
    const recordAttempt=async()=>{
      let file;
      try{file=await open(path,"wx",0o600);}
      catch{refusal("operation-already-attempted");}
      try{
        await file.writeFile(JSON.stringify({
          version:1,status:"attempted",hash:digest,
          action:"allocation:set-amount",attemptedAt:new Date().toISOString()
        })+"\n");
        await file.sync();
        // Persist directory entry before invoking any Actual mutation.
        await fsyncDirectory(journalDir);
        attempted=true;
      }finally{await file.close();}
    };
    working=await mkdtemp(join(tmpdir(),"financew-allocation-"));
    await chmod(working,0o700);
    api=await import("@actual-app/api");
    await api.init({dataDir:working,serverURL,password});
    const encPath=process.env.ACTUAL_ENCRYPTION_PASSWORD_FILE;
    const encryptionPassword=encPath?await privateFile(encPath):null;
    await api.downloadBudget(syncId,encryptionPassword
      ? {password:encryptionPassword}:undefined);
    const result=await executeAllocation({
      api,input:command,recordAttempt
    });
    const record={version:1,status:"committed",hash:digest,
      action:"allocation:set-amount",completedAt:new Date().toISOString()};
    await writeFile(path,JSON.stringify(record)+"\n",{mode:0o600});
    const receipt=await open(path,"r");
    try{await receipt.sync();}finally{await receipt.close();}
    await fsyncDirectory(journalDir);
    return result.status;
  }catch(error){
    // Only an explicit persisted attempted journal gives an uncertain outcome.
    // A half-created/corrupt journal still fail-closes all later writers.
    if(attempted)return "uncertain";
    throw error;
  }finally{
    if(api){try{await api.shutdown();}catch{/* no retries */}}
    if(working)await rm(working,{recursive:true,force:true});
    if(lock)await lock.close();
    await rm(lockPath,{force:true});
  }
}
try{
  const outcome=await run();
  process.stdout.write("FINANCEW_ALLOCATION_RESULT "+outcome+"\n");
}catch(error){
  process.stdout.write("FINANCEW_ALLOCATION_RESULT blocked:"+errorCode(error)+"\n");
  process.exitCode=1;
}
