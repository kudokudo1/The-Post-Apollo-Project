#!/usr/bin/env node
// D17c separately permitted funding writer. NOT wired into Quickshell.
// No permit creation, no automatic retry, no argv secrets. Existing-account
// opening balances are intentionally unsupported pending bank reconciliation.
// Shares FinanceW's operation ledger and exclusive .write-lock with D9/D12.
import {readFile,writeFile,readdir,lstat,mkdir,open,mkdtemp,rm,chmod}
  from "node:fs/promises";
import {homedir,tmpdir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {readActualServerURL} from "./source_config.mjs";
import {FundingRefusal,validateFundingCommand,executeFunding}
  from "./funding_guard.mjs";

const config=join(homedir(),".config","financew");
const journalDir=join(homedir(),".local","state","financew","operations");
const fail=code=>{throw new FundingRefusal(code);};
function code(error){
  return error instanceof FundingRefusal?error.code:"operation-failed";
}
async function privateFile(path){
  let info;
  try{info=await lstat(path);}catch{fail("private-file-unavailable");}
  if(!info.isFile() || (info.mode & 0o077)!==0)
    fail("unsafe-private-file");
  return (await readFile(path,"utf8")).trim();
}
async function commandFromStdin(){
  let raw="";
  for await(const chunk of process.stdin){
    raw+=chunk.toString("utf8");
    if(raw.length>4096)fail("input-too-large");
    if(raw.includes("\n"))break;
  }
  const parts=raw.split("\n");
  if(parts.length!==2 || parts[1]!=="")fail("invalid-input-frame");
  let parsed;
  try{parsed=JSON.parse(parts[0]);}catch{fail("invalid-json");}
  return validateFundingCommand(parsed);
}
async function fsyncDirectory(path){
  const handle=await open(path,"r");
  try{await handle.sync();}finally{await handle.close();}
}
async function run(){
  // Only the operator may create this mode-0600 exact-marker local file.
  let permit;
  try{permit=await privateFile(join(config,"funding-writes-enabled"));}
  catch{fail("writes-disabled");}
  if(permit!=="FINANCEW_FUNDING_WRITES_APPROVED")
    fail("writes-disabled");
  const command=await commandFromStdin();
  await mkdir(journalDir,{recursive:true,mode:0o700});
  const info=await lstat(journalDir);
  if(!info.isDirectory() || (info.mode & 0o077)!==0)
    fail("unsafe-journal-directory");
  const lockPath=join(journalDir,".write-lock");
  let lock;
  try{lock=await open(lockPath,"wx",0o600);}
  catch{fail("write-in-progress-or-recovery-needed");}
  let working=null,api=null,attempted=false;
  try{
    const serverURL=await readActualServerURL();
    if(serverURL!=="http://127.0.0.1:5006")
      fail("unsupported-write-server");
    const password=await privateFile(join(config,"actual-password"));
    const syncId=await privateFile(join(config,"actual-sync-id"));
    if(!/^[a-zA-Z0-9-]{8,80}$/.test(syncId))fail("invalid-sync-id");
    const key=createHash("sha256").update(serverURL+"\0"+syncId).digest("hex");
    if(command.sourceKey!==key)fail("budget-source-changed");

    const names=await readdir(journalDir);
    // All D9/D12 and D17c unresolved attempts block every subsequent funding
    // write, including requests using new IDs or new calendar dates.
    for(const name of names){
      if(!name.endsWith(".json"))continue;
      let record;
      try{record=JSON.parse(await privateFile(join(journalDir,name)));}
      catch{fail("recovery-needed");}
      if(!record || record.status!=="committed")fail("recovery-needed");
    }
    const journalName="funding-"+command.requestId+".json";
    if(names.includes(journalName))fail("operation-already-attempted");
    const journalPath=join(journalDir,journalName);
    const digest=createHash("sha256").update(JSON.stringify(command)).digest("hex");

    const recordAttempt=async()=>{
      let file;
      try{file=await open(journalPath,"wx",0o600);}
      catch{fail("operation-already-attempted");}
      try{
        await file.writeFile(JSON.stringify({
          version:1,status:"attempted",
          hash:digest,action:"funding:"+command.mode,
          attemptedAt:new Date().toISOString()
        })+"\n");
        await file.sync();
        await fsyncDirectory(journalDir);
        attempted=true;
      }finally{await file.close();}
    };

    working=await mkdtemp(join(tmpdir(),"financew-funding-"));
    await chmod(working,0o700);
    api=await import("@actual-app/api");
    await api.init({dataDir:working,serverURL,password});
    const encPath=process.env.ACTUAL_ENCRYPTION_PASSWORD_FILE;
    const encryptionPassword=encPath?await privateFile(encPath):null;
    await api.downloadBudget(syncId,encryptionPassword
      ? {password:encryptionPassword}:undefined);
    const result=await executeFunding({api,input:command,recordAttempt});

    // Journal contains only a digest/action/status, never account names,
    // source credentials, transaction descriptions or raw amounts.
    await writeFile(journalPath,JSON.stringify({
      version:1,status:"committed",
      hash:digest,action:"funding:"+command.mode,
      completedAt:new Date().toISOString()
    })+"\n",{mode:0o600});
    const receipt=await open(journalPath,"r");
    try{await receipt.sync();}finally{await receipt.close();}
    await fsyncDirectory(journalDir);
    return result.status;
  }catch(error){
    if(attempted)return "uncertain";
    throw error;
  }finally{
    if(api){try{await api.shutdown();}catch{/* NEVER retry */}}
    if(working)await rm(working,{recursive:true,force:true});
    if(lock){await lock.close();await rm(lockPath,{force:true});}
  }
}
try{
  const result=await run();
  process.stdout.write("FINANCEW_FUNDING_RESULT "+result+"\n");
}catch(error){
  process.stdout.write("FINANCEW_FUNDING_RESULT blocked:"+code(error)+"\n");
  process.exitCode=1;
}
