#!/usr/bin/env node
// D15: explicit on-demand historical Actual inspection. Reads transaction
// history in a disposable API cache, never changes source budget or permits.
import {readFile,stat,mkdtemp,rm,chmod} from "node:fs/promises";
import {homedir,tmpdir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {takeOpeningHistory} from "./opening_history.mjs";
import {validMonth} from "./actual_readonly.mjs";
import {readActualServerURL} from "./source_config.mjs";

async function privateSecret(envName,fallback){
  const file=process.env[envName] || fallback;
  if(!file)throw Error("missing-secret-file");
  const info=await stat(file);
  if(!info.isFile() || (info.mode & 0o077)!==0)throw Error("unsafe-secret-file");
  const value=(await readFile(file,"utf8")).replace(/[\r\n]+$/,"");
  if(!value)throw Error("empty-secret-file");
  return value;
}
async function run(){
  const month=process.env.FINANCEW_HISTORY_MONTH;
  if(!validMonth(month))throw Error("invalid-history-month");
  const serverURL=await readActualServerURL();
  const syncId=await privateSecret("ACTUAL_SYNC_ID_FILE",
    join(homedir(),".config","financew","actual-sync-id"));
  if(!/^[a-zA-Z0-9-]{8,80}$/.test(syncId))throw Error("invalid-sync-id");
  const password=await privateSecret("ACTUAL_PASSWORD_FILE",
    join(homedir(),".config","financew","actual-password"));
  const encryptionPassword=process.env.ACTUAL_ENCRYPTION_PASSWORD_FILE
    ? await privateSecret("ACTUAL_ENCRYPTION_PASSWORD_FILE",null):null;
  const folder=await mkdtemp(join(tmpdir(),"financew-history-"));
  await chmod(folder,0o700);
  let api;
  try{
    api=await import("@actual-app/api");
    await api.init({dataDir:folder,serverURL,password});
    await api.downloadBudget(syncId,encryptionPassword
      ? {password:encryptionPassword}:undefined);
    const result=await takeOpeningHistory(api,month);
    result.sourceKey=createHash("sha256")
      .update(serverURL+"\0"+syncId).digest("hex");
    process.stdout.write(JSON.stringify(result)+"\n");
  }finally{
    if(api){try{await api.shutdown();}catch{}}
    await rm(folder,{recursive:true,force:true});
  }
}
run().catch(error=>{
  // Never emit credentials, account or transaction details in error logs.
  const code=error?.message==="history-scan-limit"?"history-scan-limit"
    : error?.message==="invalid-history-month"?"invalid-history-month"
    : "history-read-failed";
  process.stderr.write("FINANCEW_OPENING_HISTORY_ERROR "+code+"\n");
  process.exitCode=1;
});
