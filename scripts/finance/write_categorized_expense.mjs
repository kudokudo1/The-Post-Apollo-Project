#!/usr/bin/env node
// Simple M3b: DORMANT categorized-expense writer. Not connected to FinanceW.
// One addTransactions create includes category ID; readback must prove exact ID.
// A post-attempt failure stays UNCERTAIN and blocks every FinanceW writer.
// Separate operator permit; never provision it here. No argv secrets or retry.
import {readdir,open,mkdtemp,rm,chmod} from "node:fs/promises";
import {homedir,tmpdir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {openTrustedDirectory,readTrustedPrivateFile,readPrivateEntry,dirEntryPath}
  from "./categorized_expense_file_trust.mjs";
import {validateCategorizedExpenseCommand,executeCategorizedExpense,CategorizedExpenseRefusal}
  from "./categorized_expense_guard.mjs";

const config=join(homedir(),".config","financew");
const journalDir=join(homedir(),".local","state","financew","operations");
function refusal(code){throw new CategorizedExpenseRefusal(code);}
function errorCode(error){
  return error instanceof CategorizedExpenseRefusal?error.code:"operation-failed";
}
async function privateFile(path) {
  // No pathname lstat/readFile split: open each parent without following
  // symlinks, then fstat/read the exact private descriptor.
  return readTrustedPrivateFile(path);
}
async function readCommand(){
  let data="";
  for await(const chunk of process.stdin) {
    data+=chunk.toString("utf8");
    if(data.length>4096)refusal("input-too-large");
  }
  // Exactly one bounded JSON line; no hidden trailing command accepted.
  if(!data.endsWith("\n") || data.indexOf("\n")!==data.length-1
      || data.includes("\r"))refusal("invalid-input-frame");
  let command;
  try{command=JSON.parse(data.slice(0,-1));}catch{refusal("invalid-json");}
  return validateCategorizedExpenseCommand(command);
}
async function fsyncDirectory(dir){
  // The directory was opened and verified before the shared lock. Sync
  // this same descriptor rather than re-resolving a mutable pathname.
  await dir.sync();
}
async function run(){
  // This file is NEVER created by widget, CI, README or installation.
  // Protected envelope moves require a separate, explicit authorization.
  let permit;
  try{permit=await privateFile(join(config,"categorized-expense-writes-enabled"));}
  catch{refusal("writes-disabled");}
  if(permit!=="FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED")
    refusal("writes-disabled");
  const command=await readCommand();
  let journal;
  try{journal=await openTrustedDirectory(journalDir,{
    create:true,privateLeaf:true
  });}
  catch{refusal("unsafe-journal-directory");}
  const lockPath=dirEntryPath(journal,".write-lock");
  let lock;
  try{lock=await open(lockPath,"wx",0o600);}
  catch{
    await journal.close();
    refusal("write-in-progress-or-recovery-needed");
  }
  let api,working,attempted=false,attemptedFile=null;
  try{
    // The read-only source_config module allows environment overrides and
    // pathname reads. This financial writer instead requires a trusted
    // private config file and a fixed loopback endpoint.
    const serverURL=await privateFile(join(config,"actual-server-url"));
    if(serverURL!=="http://127.0.0.1:5006")
      refusal("unsupported-write-server");
    const password=await privateFile(join(config,"actual-password"));
    const syncId=await privateFile(join(config,"actual-sync-id"));
    if(!/^[a-zA-Z0-9-]{8,80}$/.test(syncId))refusal("invalid-sync-id");
    const expectedKey=createHash("sha256")
      .update(serverURL+"\0"+syncId).digest("hex");
    if(command.sourceKey!==expectedKey)refusal("budget-source-changed");

    // Includes D9 transaction and M2b envelope-move journals. One unresolved operation anywhere
    // blocks every FinanceW write; no automatic lock or journal cleanup.
    const priorNames=await readdir("/proc/self/fd/"+journal.fd);
    for(const filename of priorNames){
      if(!filename.endsWith(".json"))continue;
      let entry;
      try{entry=JSON.parse(await readPrivateEntry(journal,filename));}
      catch{refusal("recovery-needed");}
      if(!entry || entry.status!=="committed")refusal("recovery-needed");
    }
    const journalName="categorized-expense-"+command.requestId+".json";
    // Request IDs are one-use across this shared finance journal, including
    // earlier transaction, allocation, funding, category and move actions.
    // Never replay even a previously committed command.
    if(priorNames.includes(journalName)
        || priorNames.some(name=>name.endsWith("-"+command.requestId+".json"))
        || priorNames.includes(command.requestId+".json"))
      refusal("operation-already-attempted");
    const path=dirEntryPath(journal,journalName);
    const digest=createHash("sha256").update(JSON.stringify(command)).digest("hex");
    const recordAttempt=async()=>{
      try{attemptedFile=await open(path,"wx",0o600);}
      catch{refusal("operation-already-attempted");}
      await attemptedFile.writeFile(JSON.stringify({
        version:1,status:"attempted",hash:digest,
        action:"transaction:create-categorized-expense",attemptedAt:new Date().toISOString()
      })+"\n");
      await attemptedFile.sync();
      // Persist this exact directory entry before any Actual mutation.
      await fsyncDirectory(journal);
      attempted=true;
    };
    working=await mkdtemp(join(tmpdir(),"financew-categorized-expense-"));
    await chmod(working,0o700);
    api=await import("@actual-app/api");
    await api.init({dataDir:working,serverURL,password});
    const encPath=process.env.ACTUAL_ENCRYPTION_PASSWORD_FILE;
    const encryptionPassword=encPath?await privateFile(encPath):null;
    await api.downloadBudget(syncId,encryptionPassword
      ? {password:encryptionPassword}:undefined);
    const result=await executeCategorizedExpense({
      api,input:command,recordAttempt
    });
    const record={version:1,status:"committed",hash:digest,
      action:"transaction:create-categorized-expense",completedAt:new Date().toISOString()};
    // Commit using the SAME descriptor as ATTEMPTED, never reopen the
    // journal by name after an external Actual write.
    const receipt=Buffer.from(JSON.stringify(record)+"\n","utf8");
    await attemptedFile.truncate(0);
    let written=0;
    while(written<receipt.length){
      const {bytesWritten}=await attemptedFile.write(
        receipt,written,receipt.length-written,written);
      if(bytesWritten<=0)throw Error("journal-commit-incomplete");
      written+=bytesWritten;
    }
    await attemptedFile.sync();
    await fsyncDirectory(journal);
    return result.status;
  }catch(error){
    // Only an explicit persisted attempted journal gives an uncertain outcome.
    // A half-created/corrupt journal still fail-closes all later writers.
    if(attempted)return "uncertain";
    throw error;
  }finally{
    if(api){try{await api.shutdown();}catch{/* no retries */}}
    if(working)await rm(working,{recursive:true,force:true});
    if(attemptedFile)await attemptedFile.close();
    if(lock)await lock.close();
    await rm(lockPath,{force:true});
    await journal.close();
  }
}
try{
  const outcome=await run();
  process.stdout.write("FINANCEW_CATEGORIZED_EXPENSE_RESULT "+outcome+"\n");
}catch(error){
  process.stdout.write("FINANCEW_CATEGORIZED_EXPENSE_RESULT blocked:"+errorCode(error)+"\n");
  process.exitCode=1;
}
